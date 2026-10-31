"""Publish audited, unpromoted fixed-weight profile diagnostics and figures."""
import argparse
from collections import Counter
from hashlib import sha256
import gzip
import json
import os

if __name__ == '__main__':
    for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                  'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[_name] = '1'

import numpy as np

from . import run_profile_landscape_study as study
from . import audit_profile_landscape as auditor
from .experiment_journal import Journal


PUBLIC = study.ROOT/'web/data/profile-landscape'
PUBLISHER_SOURCES = ('scripts/publish_profile_landscape.py', 'tests/test_profile_landscape_publication.py')


def digest(path): return sha256(path.read_bytes()).hexdigest()


def verify_audit(receipt, cell_digest, metadata, source_hashes):
    body = {k:v for k,v in receipt.items() if k != 'receipt_sha256'}
    if sha256(study.calibration.legacy.encoded(body)).hexdigest() != receipt.get('receipt_sha256'):
        raise ValueError('independent audit receipt checksum differs')
    identity = receipt.get('identity', {})
    if (receipt.get('schema') != 'profile-landscape-independent-audit-1' or receipt.get('status') != 'passed'
            or receipt.get('planned') != 112 or receipt.get('promotion') is not False
            or receipt.get('assessment_opened') is not False or receipt.get('new_position_fits') != 0
            or receipt.get('new_noise_draws') != 0 or receipt.get('failures') != []
            or identity.get('profile_commit') != auditor.COMMIT
            or identity.get('profile_journal_digest') != cell_digest
            or identity.get('source_sha256') != source_hashes
            or identity.get('baseline_journal_digest') != metadata['baseline_journal_digest']
            or identity.get('point_journal_digest') != metadata['point_journal_digest']):
        raise ValueError('audit does not authorize this exact publication')
    counts = receipt.get('counts', {})
    if (set(counts)-{'verified', 'verified_unavailable'} or sum(counts.values()) != 112
            or any(type(n) is not int or n < 0 for n in counts.values())):
        raise ValueError('audit denominator differs')


def verify_audit_cells(receipt, records, audit):
    checkpoints = audit.records(require_complete=True)
    if study.calibration.record_digest(audit, checkpoints) != receipt.get('audit_cell_digest'):
        raise ValueError('audit checkpoint journal differs from receipt')
    if {tuple(r['key']) for r in checkpoints} != {tuple(r['key']) for r in records}:
        raise ValueError('audit checkpoint keys differ')
    profile = {tuple(r['key']): r for r in records}; counts = Counter(); totals = Counter(); maxima = {}
    for checkpoint in checkpoints:
        saved = profile[tuple(checkpoint['key'])]; row = checkpoint['payload']
        expected = 'verified' if saved['payload']['status'] == 'profile_completed' else 'verified_unavailable'
        if (row['status'] != expected or row.get('profile_checksum') != saved['checksum']
                or row.get('profile_status') != saved['payload']['status']):
            raise ValueError('audit checkpoint profile binding differs')
        counts[row['status']] += 1; totals.update(row.get('checks', {}))
        for name, value in row.get('max_absolute_differences', {}).items():
            maxima[name] = max(maxima.get(name, 0.), value)
    if (dict(counts) != receipt['counts'] or dict(totals) != receipt['verification_counts']
            or maxima != receipt['max_absolute_differences']):
        raise ValueError('audit checkpoint summary differs')
    return checkpoints


def keep(path, content):
    """Idempotent publication; never replace a different existing artifact."""
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
            raise ValueError('publication already exists with different bytes: '+path.name)
    else:
        with path.open('xb') as stream: stream.write(content)


def brief_probe(diagnostic):
    return {'position_common_px': diagnostic['position'], 'cost': diagnostic.get('cost'),
        'steps': diagnostic['steps'], 'error_code': diagnostic.get('error_code')}


def focus_entry(sid, obs, records, old, point):
    rows = {'baseline': old.read((sid, obs, 'nearest'))['payload'], 'corrected': point.read((sid, obs))['payload']}
    arms = []
    for psf in study.ARMS:
        for weight in study.ARMS:
            record = records[(sid, obs, psf, weight)]; cell = record['payload']
            if cell['status'] != 'profile_completed': raise ValueError('focus branch unavailable')
            diag = cell['diagnostics']; probes = {tuple(x['position']): x['diagnostic'] for x in diag['probes']}
            candidates = {}
            for fit_arm in study.ARMS:
                candidates[fit_arm] = [{'saved_delta_cost_in_own_fit': m['delta_chi2'],
                    'diagnostic': brief_probe(probes[tuple(m['position'])])}
                    for m in rows[fit_arm]['fit']['final_mode_audit']['near_best_modes']]
            topology = diag['global_grid']['sampled_connectivity']
            arms.append({'psf_arm': psf, 'weight_arm': weight, 'record_checksum': record['checksum'],
                'sampled_global_minimum_cost': topology['minimum_cost'], 'valid_nodes': topology['valid_nodes'],
                'missing_nodes': topology['missing_nodes'],
                'sampled_connectivity': topology['levels'], 'saved_candidates': candidates})
    return {'source_id': sid, 'obs_id': obs, 'arms': arms,
        'saved_near_best_counts': {arm: len(rows[arm]['fit']['final_mode_audit']['near_best_modes']) for arm in study.ARMS},
        'figure': 'profile-'+sid+'-'+obs+'.png'}


def figure(entry, records, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
    fig, axes = plt.subplots(2, 2, figsize=(10.8, 9), layout='constrained')
    image = None
    for axis, arm in zip(axes.flat, entry['arms']):
        cell = records[(entry['source_id'], entry['obs_id'], arm['psf_arm'], arm['weight_arm'])]['payload']
        diag = cell['diagnostics']; grid = diag['global_grid']; anchor = np.asarray(cell['anchor_common_px'])
        costs = np.asarray([[np.nan if x is None else x for x in row] for row in grid['costs']])
        delta = costs-arm['sampled_global_minimum_cost']
        # Color clipping is display-only; all original numeric costs stay in the archive.
        image = axis.imshow(delta, origin='lower', extent=(-2.55, 2.55, -2.55, 2.55),
                            cmap='cividis', vmin=0, vmax=6, interpolation='nearest')
        for fit_arm, marker, color in (('baseline', 'x', '#d14900'), ('corrected', '+', '#ffffff')):
            for candidate in arm['saved_candidates'][fit_arm]:
                p = np.asarray(candidate['diagnostic']['position_common_px'])-anchor
                axis.plot(p[0], p[1], marker=marker, color=color, markersize=10, markeredgewidth=1.8, linestyle='none')
        axis.set(xlim=(-2.5, 2.5), ylim=(-2.5, 2.5), xlabel='x - Gaia anchor [common pixel]',
                 ylabel='y - Gaia anchor [common pixel]',
                 title=f"PSF: {arm['psf_arm']} | weights: {arm['weight_arm']}")
    fig.colorbar(image, ax=axes, label='F - sampled grid minimum (colors capped at 6)', shrink=.85)
    fig.suptitle('Gaia '+entry['source_id']+'\n'+entry['obs_id']+' | fixed-weight diagnostic, no confidence region', fontsize=12)
    fig.legend(handles=[Line2D([], [], marker='x', color='#d14900', linestyle='none', label='Saved baseline candidates'),
                        Line2D([], [], marker='+', color='#666666', linestyle='none', label='Saved corrected candidates (white on map)')],
               loc='outside lower center', ncols=2, frameon=False)
    from io import BytesIO
    stream = BytesIO();fig.savefig(stream, format='png', dpi=130, metadata={'Software': 'NoSleepClub profile diagnostic'})
    plt.close(fig);keep(path, stream.getvalue())


def run():
    design = study.frozen.verify(study.DESIGN, study.RULES, study.SOURCES, auditor.COMMIT)
    context, old, point, _, metadata = study.open_inputs()
    if design['metadata'] != study.calibration.legacy.jsonable(metadata): raise ValueError('publication input identity changed')
    journal = Journal(study.OUTPUT/'cells', study.frozen.identity(study.DESIGN, auditor.COMMIT,
        study.frozen.runtime(), 'fixed-profile-landscape'), study.expected_keys(context), study.STATUSES)
    records = journal.records(require_complete=True); cell_digest = study.calibration.record_digest(journal, records)
    receipt = json.loads(auditor.RECEIPT.read_text(encoding='utf-8'))
    verify_audit(receipt, cell_digest, metadata, {p:digest(study.ROOT/p) for p in auditor.FILES})
    if receipt['identity']['profile_design_sha256'] != digest(study.DESIGN): raise ValueError('audited design differs')
    audit = Journal(auditor.AUDIT_DIR/'cells', receipt['identity'], study.expected_keys(context),
        ('verified', 'verified_unavailable', 'unverified_study_failure', 'audit_mismatch'))
    audit_records = verify_audit_cells(receipt, records, audit)
    summary = json.loads((study.OUTPUT/'summary.json').read_text(encoding='utf-8'))
    counts = dict(Counter(r['payload']['status'] for r in records))
    if summary['cell_digest'] != cell_digest or summary['counts'] != counts or summary['planned'] != 112:
        raise ValueError('complete study summary differs')
    if (counts.get('profile_completed', 0) != receipt['counts'].get('verified', 0)
            or counts.get('preparation_failed', 0) != receipt['counts'].get('verified_unavailable', 0)
            or set(counts)-{'profile_completed', 'preparation_failed'}):
        raise ValueError('study and audit status correspondence differs')
    public_records = {'schema': 'profile-landscape-records-1', 'design_sha256': digest(study.DESIGN),
        'journal_header': json.loads((journal.directory/'header.json').read_text(encoding='utf-8')),
        'cell_digest': cell_digest, 'records': records,
        'audit_journal_header': json.loads((audit.directory/'header.json').read_text(encoding='utf-8')),
        'audit_records': audit_records}
    raw = study.calibration.legacy.encoded(public_records); compressed = gzip.compress(raw, mtime=0)
    indexed = {tuple(r['key']):r for r in records}
    focus = [focus_entry(sid, obs, indexed, old, point) for sid in study.FOCUS for obs in study.FRAMES]
    sources = [{'source_id': sid, 'planned': 8,
                'counts': dict(Counter(r['payload']['status'] for r in records if r['key'][0] == sid))}
               for sid in sorted(context.training_ids)]
    PUBLIC.mkdir(parents=True, exist_ok=True)
    for entry in focus: figure(entry, indexed, PUBLIC/entry['figure'])
    overview = {'schema': 'profile-landscape-overview-1', 'protocol_commit': auditor.COMMIT,
        'design_sha256': digest(study.DESIGN), 'cell_digest': cell_digest,
        'status': 'audited_diagnostic_only', 'planned': 112, 'counts': counts,
        'sources': sources, 'frames': list(study.FRAMES), 'focus': focus,
        'audit': {k:receipt[k] for k in ('receipt_sha256', 'counts', 'verification_counts', 'max_absolute_differences')},
        'audit_source_sha256': receipt['identity']['source_sha256'],
        'publisher_source_sha256': {p:digest(study.ROOT/p) for p in PUBLISHER_SOURCES},
        'download': {'path': 'data/profile-landscape/records.json.gz', 'bytes': len(compressed),
                     'sha256': sha256(compressed).hexdigest(), 'uncompressed_bytes': len(raw), 'uncompressed_sha256': sha256(raw).hexdigest()},
        'figures': {entry['figure']: {'sha256': digest(PUBLIC/entry['figure']),
            'source_id': entry['source_id'], 'obs_id': entry['obs_id'],
            'record_checksums': [a['record_checksum'] for a in entry['arms']],
            'display': '0.1-common-pixel grid; colors capped at delta F=6 only in figure, relative to each arm grid minimum'} for entry in focus},
        'original_calibration_gate_passed': False, 'assessment_opened': False,
        'prospective_fields_opened': 0, 'promotion': False,
        'qualification': 'Post-hoc opened-field conditional profile diagnosis; sampled topology and curvature do not certify optical truth, source validity, accuracy or coverage.'}
    keep(PUBLIC/'records.json.gz', compressed)
    keep(PUBLIC/'independent-audit.json', study.calibration.legacy.encoded(receipt))
    keep(PUBLIC/'overview.json', study.calibration.legacy.encoded(overview))
    study.assert_assessment_unopened()
    print(json.dumps({k:overview[k] for k in ('planned', 'counts', 'download')}, indent=2))
    return overview


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();run()
