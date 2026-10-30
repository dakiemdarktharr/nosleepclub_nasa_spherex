"""Audit saved native star fits and publish paired descriptive diagnostics."""
import argparse
from collections import Counter
import gzip
from hashlib import sha256
import json
import os

if __name__ == '__main__':
    for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                  'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[_name] = '1'

import astropy.units as u
import numpy as np

from . import run_reference_star_study as study
from . import run_wise_linked_study as legacy
from . import publish_neighbor_intervention as independent
from .experiment_journal import Journal
from .science_jobs import atomic


OUT = study.ROOT / 'web/data/reference-stars'


def mode_audit(fit, anchor):
    audit = fit['final_mode_audit'];starts = audit['starts']
    if len(starts) != 9:
        raise ValueError('missing final starts')
    independent.close(audit['point_chi2'], fit['chi2_weighted'], 'point mode cost')
    candidates = [{'position': np.asarray(fit['position']), 'chi2': fit['chi2_weighted'], 'origin': 'point'}]
    for start, offset in zip(starts, study.model.START_OFFSETS):
        independent.close(start['start'], anchor + offset, 'final starting position')
        if start['stage'] != 'final_fixed_weights' or not isinstance(start['success'], bool):
            raise ValueError('bad final start status')
        if start['success']:
            candidates.append({'position': np.asarray(start['position']), 'chi2': start['chi2'], 'origin': 'start'})
    modes = []
    for candidate in sorted(candidates, key=lambda x: x['chi2']):
        group = next((m for m in modes if np.linalg.norm(candidate['position'] - m['position']) <= .15), None)
        if group is None:
            modes.append({**candidate, 'member_count': 1})
        else:
            group['member_count'] += 1
    for m in modes:
        m['delta_chi2'] = m['chi2'] - modes[0]['chi2']
        m['position'] = m['position'].tolist()
    near = [m for m in modes if m['delta_chi2'] <= 5.991]
    independent.recursive_equal(modes, audit['modes'], 'mode clusters')
    independent.recursive_equal(near, audit['near_best_modes'], 'near mode clusters')
    improvement = fit['chi2_weighted'] - min((r['chi2'] for r in starts if r['success']), default=fit['chi2_weighted'])
    independent.close(improvement, audit['best_improvement_chi2'], 'best mode improvement')
    if (audit['all_starts_failed'] != (not any(s['success'] for s in starts))
            or audit['near_best_count'] != len(near) or audit['better_than_point'] != (improvement > 1e-4)):
        raise ValueError('mode status mismatch')


def audit_point(row, item, anchor):
    fit = row['fit'];samples = row['samples'];frames = fit['frames']
    if len(samples) != 1 or len(frames) != 1 or frames[0]['obs_id'] != item['obs_id']:
        raise ValueError('single native exposure identity changed')
    if fit['data_unit'] != 'MJy / sr' or fit['nonnegative_neighbors'] is not False:
        raise ValueError('units/constraints changed')
    expected = study.previous.descriptors([item])[0]
    independent.recursive_equal(samples[0], expected, 'reconstructed native sample')
    position = np.asarray(fit['position'])
    target = item['renderer'](position).to_value(u.MJy/u.sr/u.Jy)
    frame_audit = independent.audit_frame(samples[0], frames[0], target, False, item['obs_id'])
    independent.close(fit['weighted_residual'], frames[0]['weighted_residual'], 'total residual')
    independent.close(fit['chi2_weighted'], frame_audit['weighted_chi2'], 'total chi2')
    independent.close(fit['chi2_raw'], frame_audit['raw_chi2'], 'raw chi2')
    irls = fit['irls'];reports = fit['start_reports'];updates = reports[9:]
    if len(reports[:9]) != 9 or len(updates) != irls['iterations'] or not 2 <= len(updates) <= 20:
        raise ValueError('IRLS count changed')
    for start, offset in zip(reports[:9], study.model.START_OFFSETS):
        independent.close(start['start'], anchor + offset, 'initial starting position')
        if start['stage'] != 'initial' or not isinstance(start['success'], bool):
            raise ValueError('initial start status changed')
    successful = [r for r in reports[:9] if r['success']]
    if not successful:
        raise ValueError('completed fit has no successful start')
    last = min(successful, key=lambda x: x['chi2'])['position']
    for i, update in enumerate(updates, 1):
        if update['stage'] != 'irls_' + str(i) or update['success'] is not True:
            raise ValueError('IRLS update status changed')
        independent.close(update['start'], last, 'IRLS starting position');last = update['position']
    independent.close(last, position, 'final position')
    difference = float(np.max(np.abs(np.asarray(updates[-1]['start']) - position)))
    independent.close(difference, irls['position_max_change'], 'last position difference')
    independent.close(frame_audit['next_weight_max_difference'], irls['next_weight_max_difference'], 'last weight difference')
    converged = frame_audit['next_weight_max_difference'] <= .001 and difference <= .0001
    if irls['converged'] != converged:
        raise ValueError('convergence status changed')
    mode_audit(fit, anchor)
    replay = independent.replay_final_starts(row, [item])
    boundary = bool(np.any(np.abs(position - anchor) >= .95*2.5))
    if fit['at_boundary'] != boundary or fit['position_rank'] not in (0, 2):
        raise ValueError('boundary/rank status changed')
    reasons = []
    if boundary: reasons.append('boundary')
    if fit['position_rank'] < 2: reasons.append('position_rank')
    if not converged: reasons.append('irls_not_converged')
    if fit['final_mode_audit']['all_starts_failed']: reasons.append('final_mode_audit_failed')
    if fit['final_mode_audit']['better_than_point']: reasons.append('better_final_weight_mode')
    if fit['final_mode_audit']['near_best_count'] > 1: reasons.append('multiple_near_best_modes')
    if fit['numerical_reasons'] != reasons or fit['numerical_support'] != (not reasons):
        raise ValueError('numerical decision changed')
    independent.close(row['residual_east_north_arcsec'], study.sky_residual_arcsec(position, anchor), 'sky residual')
    return {'frame': frame_audit, 'final_start_replay': replay,
            'qualification': 'saved-point model/KKT and successful final-start objectives replayed; position Jacobian/rank not independently recomputed'}


def metrics(rows):
    if not rows:
        return {'n': 0, 'rms_arcsec': None, 'median_radial_arcsec': None,
                'p90_radial_arcsec': None, 'mean_east_north_arcsec': None}
    residual = np.asarray([r['residual_east_north_arcsec'] for r in rows]);radius = np.linalg.norm(residual, axis=1)
    return {'n': len(rows), 'rms_arcsec': float(np.sqrt(np.mean(radius**2))),
            'median_radial_arcsec': float(np.median(radius)), 'p90_radial_arcsec': float(np.percentile(radius, 90)),
            'mean_east_north_arcsec': np.mean(residual, axis=0).tolist()}


def paired_summary(rows):
    keyed = {tuple(row['key']): row['payload'] for row in rows}
    pairs = sorted({key[:2] for key in keyed})
    completed = [key for key in pairs if all(keyed[key+(v,)]['status'] == 'fit_completed' for v in ('nearest', 'bilinear'))]
    supported = [key for key in completed if all(keyed[key+(v,)]['fit']['numerical_support'] for v in ('nearest', 'bilinear'))]
    arms = []
    for variant in ('nearest', 'bilinear'):
        own = [r for k, r in keyed.items() if k[2] == variant]
        done = [r for r in own if r['status'] == 'fit_completed']
        arms.append({'variant': variant, 'planned': len(own), 'completed': len(done),
                     'failed': len(own)-len(done), 'numerically_supported': sum(r['fit']['numerical_support'] for r in done),
                     'negative_target_flux': sum(r['fit']['frames'][0]['negative_target_flux'] for r in done),
                     'reasons': dict(Counter(reason for r in done for reason in r['fit']['numerical_reasons'])),
                     'all_completed': metrics(done),
                     'common_completed': metrics([keyed[k+(variant,)] for k in completed]),
                     'common_numerical': metrics([keyed[k+(variant,)] for k in supported])})
    shifts = [np.linalg.norm(np.asarray(keyed[k+('nearest',)]['residual_east_north_arcsec'])
                             - keyed[k+('bilinear',)]['residual_east_north_arcsec']) for k in completed]
    return {'planned_pairs': len(pairs), 'common_completed': len(completed), 'common_numerical': len(supported),
            'arms': arms, 'median_model_shift_arcsec': float(np.median(shifts)) if shifts else None,
            'maximum_model_shift_arcsec': float(max(shifts)) if shifts else None}


def build(commit):
    study.frozen.verify(study.DESIGN, study.RULES, study.SOURCES, commit)
    header = json.loads((study.OUTPUT / 'header.json').read_text(encoding='utf-8'))
    expected_identity = study.frozen.identity(study.DESIGN, commit, study.frozen.runtime(), 'real-reference-stars')
    if header['identity'] != expected_identity:
        raise ValueError('journal design/section/commit/runtime identity differs')
    context = study.inputs.read_context()
    journal = Journal(study.OUTPUT, header['identity'], study.expected_keys(context),
                      ('fit_completed', 'fit_failed', 'preparation_failed'))
    records = journal.records(require_complete=True)
    by_key = {tuple(r['key']): r for r in records};audits = []
    for reference in context.references:
        sid = reference['catalog']['source_id']
        for frame in context.frames:
            obs = frame['record']['obs_id'];pair = [by_key[(sid, obs, v)] for v in study.RULES['epsf_variants']]
            try:
                prepared, metadata = study.inputs.prepare_cell(context, reference, frame)
                preparation_error = None
            except Exception as exc:
                preparation_error = type(exc).__name__ + ': ' + str(exc)
            for record in pair:
                row = record['payload'];variant = record['key'][2]
                if preparation_error:
                    if row['status'] != 'preparation_failed' or row['error'] != preparation_error:
                        raise ValueError('common preparation failure replay differs')
                    continue
                independent.recursive_equal(metadata, row['metadata'], 'source/frame metadata')
                try:
                    item = study.inputs.prepare_variant(prepared, metadata['anchor_sky_px'], variant)
                    variant_error = None
                except Exception as exc:
                    variant_error = type(exc).__name__ + ': ' + str(exc)
                if row['status'] == 'preparation_failed':
                    if variant_error != row['error']:
                        raise ValueError('variant preparation failure replay differs')
                elif variant_error:
                    raise ValueError('saved fit cannot reconstruct its variant')
                elif row['status'] == 'fit_completed':
                    audits.append({'key': record['key'], **audit_point(row, item, np.asarray(metadata['anchor_sky_px']))})
                else:
                    independent.recursive_equal(row['samples'], study.previous.descriptors([item]), 'failed fit input sample')
            if all(r['payload']['status'] == 'fit_completed' for r in pair):
                a, b = [r['payload']['samples'][0] for r in pair]
                for key in ('x', 'y', 'data_mjysr', 'error_mjysr', 'background_design', 'neighbor_ids'):
                    independent.recursive_equal(a[key], b[key], 'paired invariant ' + key)
    digest = sha256(legacy.encoded({'header_sha256': legacy.lab.digest(journal.directory / 'header.json'),
                                  'records': [{'key': r['key'], 'checksum': r['checksum']} for r in records]})).hexdigest()
    source_rows = []
    for reference in context.references:
        sid = reference['catalog']['source_id'];subset = [r for r in records if r['key'][0] == sid]
        source_rows.append({'source_id': sid, 'legacy_split': reference['split'],
                            'bp_rp': reference['catalog'].get('bp_rp'),
                            'g_mag': reference['catalog'].get('phot_g_mean_mag'), **paired_summary(subset)})
    frame_rows = [{'obs_id': f['record']['obs_id'], 'epoch': f['record']['epoch'],
                   'mjd_midpoint_utc': f['mjd'],
                   **paired_summary([r for r in records if r['key'][1] == f['record']['obs_id']])} for f in context.frames]
    overview = {'schema': 'reference-star-overview-1', 'protocol_commit': commit,
                'design_sha256': legacy.lab.digest(study.DESIGN), 'journal_digest': digest,
                'counts': journal.counts(), 'summary': paired_summary(records), 'sources': source_rows, 'frames': frame_rows,
                'failure_reasons': dict(Counter(r['payload']['error'] for r in records if r['payload']['status'] != 'fit_completed')),
                'sources_with_completed_pair': sum(s['common_completed'] > 0 for s in source_rows),
                'audit_source_sha256': legacy.lab.digest(study.ROOT / 'scripts/publish_reference_stars.py'),
                'data_role': 'measured native image residuals versus propagated Gaia, opened image-selected field',
                'audit_coverage': {'completed_saved_points': len(audits),
                                   'preparation_failures': 'replayed without positional fitting',
                                   'fit_failures': 'inputs/checksums retained; optimizer failure trajectories not rerun'},
                'qualification': ['21 previously image-selected stars, not unseen validation',
                    'self excluded from old training registration; shared/upstream WCS dependence remains',
                    'not 840 independent measurements; no confidence interval or PSF correction learned',
                    'nearest/bilinear difference is sensitivity; residual includes catalogue/registration/model effects',
                    'no calibrated uncertainty, source-presence validation or scientific promotion'], 'promotion': False}
    full = {'overview': overview, 'header': header, 'records': records, 'audits': audits,
            'gaia_catalog_cross_time_only': [study.inputs.source_catalog_cross_time(context, r) for r in context.references]}
    return overview, full


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--protocol-commit', required=True)
    args = parser.parse_args();overview, full = build(args.protocol_commit)
    OUT.mkdir(parents=True, exist_ok=True)
    raw = legacy.encoded(full);packed = gzip.compress(raw, compresslevel=9, mtime=0)
    path = OUT / 'records.json.gz';path.write_bytes(packed)
    overview['download'] = {'path': 'data/reference-stars/records.json.gz', 'sha256': sha256(packed).hexdigest(),
                            'bytes': len(packed), 'uncompressed_sha256': sha256(raw).hexdigest(), 'uncompressed_bytes': len(raw)}
    atomic(OUT / 'overview.json', overview)
    print(json.dumps({'counts': overview['counts'], 'summary': overview['summary'], 'download': overview['download']}, indent=2))


if __name__ == '__main__':
    main()
