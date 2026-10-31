"""Frozen synthetic blend/template/phase controls; no deferred sky outcomes."""
import argparse
from collections import Counter
import gzip
from hashlib import sha256
import itertools
import json
from numbers import Integral
import os
import time

if __name__ == '__main__':
    for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                  'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[_name] = '1'

import numpy as np

from . import run_profile_landscape_study as parent
from . import signal_control_inputs as inputs
from .signal_control_metrics import summarize_signal_control
from .experiment_journal import Journal
from .science_jobs import locked, atomic, encode


ROOT = parent.ROOT
DESIGN = ROOT/'web/data/signal-controls/design.json'
OUTPUT = ROOT/'data/raw/benchmark/signal-controls'
OBS_ID = '2025W46_2A_0214_3'
PARENT_COMMIT = '704e3efc806dddef7906b032ba917745f80442a1'
GEOMETRIES = parent.FOCUS
ARMS = ('baseline', 'corrected')
STATUSES = ('fit_completed', 'fit_failed', 'preparation_failed')
PARENT_PUBLIC = ROOT/'web/data/profile-landscape'
PARENT_PRODUCTS = ('web/data/profile-landscape/overview.json',
                   'web/data/profile-landscape/independent-audit.json',
                   'web/data/profile-landscape/records.json.gz')
PARENT_AUDIT_SOURCES = ('scripts/audit_profile_landscape.py', 'tests/test_profile_landscape_audit.py',
                        'docs/PROFILE_LANDSCAPE_AUDIT.md')
RULES = {
    'version': '0.10.0-signal-controls.1', 'planned': 640,
    'scope': 'post-hoc development on two already opened training-star geometries, one exposure; synthetic means replace IMAGE',
    'geometry_source_ids': list(GEOMETRIES), 'obs_id': OBS_ID,
    'section_counts': {'noiseless': 192, 'noisy': 384, 'null': 64},
    'noiseless': {'truth': ['matched', 'gaussian'], 'phases': [0, 1, 2, 3], 'scenes': ['isolated', 'modeled', 'omitted'], 'flux_ujy': [600, 1200]},
    'noisy': {'truth': ['gaussian'], 'phases': [0, 3], 'scenes': ['isolated', 'modeled', 'omitted'], 'flux_ujy': 1200, 'draws': 16},
    'null': {'target': False, 'companion': False, 'anchor_phases': [0, 3], 'draws': 8,
             'qualification': 'fitted signed flux and positive-supported outcomes only; no calibrated detector or source position truth'},
    'native_phases': list(inputs.PHASES), 'target_native': 'floor(original registered Gaia native anchor)+phase',
    'search_anchor': 'source-present: original registered Gaia common position; null only: phase-specific native anchor mapped to common, no source truth',
    'companion_offset_native_px': list(inputs.COMPANION_OFFSET), 'companion_flux_ratio': 1.,
    'scenes': {'isolated': 'target only, no fitted companion', 'modeled': 'target plus known fixed companion, fitted signed Jy',
               'omitted': 'same target+companion truth as modeled but no companion column in fitter; misspecification stress only'},
    'independent_gaussian': inputs.GAUSSIAN, 'quadrature_orders': [12, 24],
    'quadrature_guard': 'selected L1 difference <= 1e-12+1e-10*selected mass, no mask renormalization',
    'matched_truth': 'original nearest ePSF mathematical template, including signed wings/center-Omega convention; software inverse-crime control only',
    'solid_angle': 'independent Gaussian per-pixel Omega; matched and fitters frozen center Omega; ratios retained, cross-family comparison is compound',
    'plane_coefficients_mjysr': list(inputs.PLANE_COEFFICIENTS),
    'noise': {'source_poisson': False, 'original_image_added': False, 'fitter_error': 'unchanged original observed diagonal VARIANCE',
        'prefix': inputs.NOISE_PREFIX, 'algorithm': 'PCG64 SeedSequence([prefix, draw]); C-order full single-exposure image bank',
        'sharing': 'same physical native pixel/draw across geometry, phase, scene, flux and fitter arms; null uses first eight banks',
        'qualification': 'replicates independent conditional on fixed observed variance; strata are paired and not independent new fields'},
    'fitter': {'model': 'unchanged neighbor_epoch_model', 'arms': list(ARMS), 'background': 'plane',
        'shape_coefficients': 'one previously sealed vector; never re-estimated here', 'target_flux': 'signed Jy',
        'neighbor_flux': 'signed Jy, known fixed controlled position when present', 'max_irls_iterations': 20,
        'bounds_common_px': 2.5, 'start_offsets': list(parent.baseline.model.START_OFFSETS)},
    'noiseless_clean_gate': 'ALL 128 planned isolated/modeled fits: completed, numerical support, radial error<=.1 native px, flux ratio in [.9,1.1]',
    'noisy_clean_gate': 'each of 16 fixed clean strata: at least 15/16 complete+supported+positive flux with radial<=.5 native px and flux ratio [.5,1.5]; observed-sample guard only',
    'preservation_guard': 'all 64 clean noiseless pairs complete, no new numerical refusal, radial degradation<=.02 native px and absolute flux-ratio-error degradation<=.02',
    'gate_origin': 'developmental necessary effect/support budgets, not NASA mission requirements or physical accuracy certification',
    'uncertainty': 'two-sided 95% exact Clopper-Pearson for fixed noisy/null strata; mean-ratio MCSE conditional on completed draws; no total astrometric covariance',
    'power': 'with n16 even16/16 exact95% lower~.794 and15/16~.698; probability observed>=15/16 at p=.9~.515. Not powered to certify90% population recovery. Null n8 zero upper~.369.',
    'omitted_scene_promotion_gate': False, 'model_selection': False, 'shards': 2,
    'assessment_cells_opened': 0, 'prospective_fields_opened': 0, 'promotion': False,
}
SOURCES = (*parent.SOURCES, 'scripts/rotated_gaussian_control.py', 'scripts/signal_control_inputs.py',
    'scripts/signal_control_metrics.py', 'scripts/run_signal_control_study.py',
    'tests/test_rotated_gaussian_control.py', 'tests/test_signal_control_inputs.py',
    'tests/test_signal_control_metrics.py', 'tests/test_signal_control_study.py',
    'docs/SIGNAL_CONTROL_PROTOCOL.md', 'web/data/profile-landscape/design.json',
    'web/data/shape-point-check/calibration-gate.json', *PARENT_PRODUCTS, *PARENT_AUDIT_SOURCES)


def expected_keys():
    keys = []
    for g, t, p, s, f, a in itertools.product(GEOMETRIES, ('matched', 'gaussian'), range(4),
            ('isolated', 'modeled', 'omitted'), (600, 1200), ARMS):
        keys.append(('noiseless', g, t, str(p), s, str(f), '0', a))
    for g, p, s, d, a in itertools.product(GEOMETRIES, (0, 3), ('isolated', 'modeled', 'omitted'), range(16), ARMS):
        keys.append(('noisy', g, 'gaussian', str(p), s, '1200', str(d), a))
    for g, p, d, a in itertools.product(GEOMETRIES, (0, 3), range(8), ARMS):
        keys.append(('null', g, 'none', str(p), 'isolated', '0', str(d), a))
    if len(keys) != 640 or len(set(keys)) != 640 or dict(Counter(k[0] for k in keys)) != RULES['section_counts']:
        raise ValueError('synthetic-control denominator changed')
    return keys


def verify_parent_products(context, upstream):
    """Bind the observed profile product and all independently audited cells."""
    overview = json.loads((PARENT_PUBLIC/'overview.json').read_text(encoding='utf-8'))
    receipt = json.loads((PARENT_PUBLIC/'independent-audit.json').read_text(encoding='utf-8'))
    body = {k: v for k, v in receipt.items() if k != 'receipt_sha256'}
    if receipt.get('receipt_sha256') != sha256(parent.calibration.legacy.encoded(body)).hexdigest():
        raise ValueError('parent audit receipt checksum differs')
    identity = receipt.get('identity', {})
    source_hashes = {p: parent.calibration.legacy.lab.digest(ROOT/p) for p in PARENT_AUDIT_SOURCES}
    if (receipt.get('schema') != 'profile-landscape-independent-audit-1' or receipt.get('status') != 'passed'
            or receipt.get('planned') != 112 or receipt.get('counts') != {'verified': 96, 'verified_unavailable': 16}
            or receipt.get('failures') != [] or receipt.get('promotion') is not False
            or receipt.get('assessment_opened') is not False or identity.get('profile_commit') != PARENT_COMMIT
            or identity.get('source_sha256') != source_hashes
            or identity.get('baseline_journal_digest') != upstream['baseline_journal_digest']
            or identity.get('point_journal_digest') != upstream['point_journal_digest']
            or identity.get('profile_design_sha256') != parent.calibration.legacy.lab.digest(parent.DESIGN)):
        raise ValueError('parent audit identity, source or outcome differs')
    if (overview.get('protocol_commit') != PARENT_COMMIT or overview.get('status') != 'audited_diagnostic_only'
            or overview.get('planned') != 112 or overview.get('counts') != {'profile_completed': 96, 'preparation_failed': 16}
            or overview.get('cell_digest') != identity.get('profile_journal_digest')
            or overview.get('audit', {}).get('receipt_sha256') != receipt['receipt_sha256']
            or overview.get('promotion') is not False or overview.get('assessment_opened') is not False):
        raise ValueError('parent profile overview differs from independent audit')
    packed = (PARENT_PUBLIC/'records.json.gz').read_bytes();download = overview['download']
    if len(packed) != download['bytes'] or sha256(packed).hexdigest() != download['sha256']:
        raise ValueError('parent profile archive checksum differs')
    raw = gzip.decompress(packed)
    if len(raw) != download['uncompressed_bytes'] or sha256(raw).hexdigest() != download['uncompressed_sha256']:
        raise ValueError('parent profile uncompressed archive checksum differs')
    archive = json.loads(raw);expected = [list(key) for key in parent.expected_keys(context)]
    if archive.get('schema') != 'profile-landscape-records-1' or archive.get('design_sha256') != identity['profile_design_sha256']:
        raise ValueError('parent archive identity differs')
    def verify_records(header, records):
        if len(records) != 112 or [r['key'] for r in records] != expected or header.get('expected_keys') != expected:
            raise ValueError('parent archive planned keys differ')
        header_body = {k: v for k, v in header.items() if k != 'checksum'}
        if sha256(encode(header_body)).hexdigest() != header.get('checksum'):
            raise ValueError('parent archive header checksum differs')
        for row in records:
            row_body = {k: v for k, v in row.items() if k != 'checksum'}
            if (sha256(encode(row_body)).hexdigest() != row.get('checksum')
                    or row.get('identity_sha256') != header.get('identity_sha256')):
                raise ValueError('parent archive cell checksum or identity differs')
        payload = {'header_sha256': sha256(encode(header)).hexdigest(),
                   'records': [{'key': r['key'], 'checksum': r['checksum']} for r in records]}
        return sha256(parent.calibration.legacy.encoded(payload)).hexdigest()
    profile_records = archive['records'];audit_records = archive['audit_records']
    profile_digest = verify_records(archive['journal_header'], profile_records)
    audit_digest = verify_records(archive['audit_journal_header'], audit_records)
    if (archive['audit_journal_header'].get('identity') != identity
            or archive.get('cell_digest') != profile_digest or profile_digest != identity['profile_journal_digest']
            or audit_digest != receipt['audit_cell_digest']):
        raise ValueError('parent archive journal digest differs')
    for profile, audited in zip(profile_records, audit_records):
        a = audited['payload'];p = profile['payload']
        if (a.get('profile_checksum') != profile['checksum'] or a.get('profile_status') != p.get('status')
                or (p.get('status'), a.get('status')) not in (('profile_completed', 'verified'),
                                                               ('preparation_failed', 'verified_unavailable'))):
            raise ValueError('parent audit checkpoint does not match profile cell')
    return {'profile_journal_digest': profile_digest, 'audit_journal_digest': audit_digest,
            'audit_receipt_sha256': receipt['receipt_sha256'], 'archive_sha256': download['sha256']}


def open_inputs():
    parent.assert_assessment_unopened()
    parent.frozen.verify(parent.DESIGN, parent.RULES, parent.SOURCES, PARENT_COMMIT)
    context, _, _, coefficients, metadata = parent.open_inputs()
    if not set(GEOMETRIES) <= set(context.training_ids) or OBS_ID not in {f['record']['obs_id'] for f in context.frames}:
        raise ValueError('controls must use the two fixed old training geometries/exposure')
    parent_products = verify_parent_products(context, metadata)
    return context, coefficients, {'upstream': metadata, 'parent_products': parent_products,
        'expected_keys': expected_keys(), 'parent_protocol_commit': PARENT_COMMIT,
        'qualification': 'old focus outcomes viewed; new injected scenes/noise/fit outcomes not evaluated before protocol freeze'}


def create_design():
    _, _, metadata = open_inputs()
    return parent.frozen.create(DESIGN, RULES, SOURCES, metadata=metadata)


def attempt(geometry, realized, key):
    section, sid, truth, phase, scene, flux, draw, arm = key
    search_anchor = geometry['target_common'] if section == 'null' else geometry['anchor_common']
    started = time.monotonic(); row = {'section': section, 'geometry_source_id': sid, 'obs_id': OBS_ID,
        'truth_family': truth, 'phase_index': int(phase), 'scene': scene, 'flux_ujy': int(flux),
        'draw': int(draw), 'arm': arm, 'true_flux_jy': int(flux)*1e-6,
        'realization': realized['metadata'], 'geometry_metadata': geometry['original_metadata'],
        'search_anchor_common': np.asarray(search_anchor).tolist()}
    stage = 'preparation'
    try:
        item = inputs.fit_item(geometry, realized, scene, arm)
        row['samples'] = parent.baseline.previous.descriptors([item])
        stage = 'fit'
        fit = parent.baseline.model.fit_epoch(parent.baseline.semantic.model_samples([item]), search_anchor,
            data_unit='MJy/sr', nonnegative_neighbors=False, max_irls_iterations=20)
        if len(fit['frames']) != 1 or fit['frames'][0]['obs_id'] != OBS_ID: raise ValueError('fit exposure identity changed')
        position_native = inputs.original.native_position(geometry['frame'], fit['position'])
        error = position_native-geometry['target_native'] if section != 'null' else None
        distance = float(np.linalg.norm(position_native-geometry['companion_native'])) if scene != 'isolated' else None
        row.update(status='fit_completed', fit=fit, numerical_support=bool(fit['numerical_support']),
            position_native=position_native.tolist(), position_native_error=None if error is None else error.tolist(),
            distance_to_companion_native=distance, target_flux_jy=float(fit['frames'][0]['target_flux_jy']))
    except Exception as exc:
        row.update(status='fit_failed' if stage == 'fit' else 'preparation_failed', failure_stage=stage,
            error=type(exc).__name__+': '+str(exc), start_reports=parent.calibration.legacy.jsonable(getattr(exc, 'start_reports', [])))
    row['elapsed_seconds'] = time.monotonic()-started
    return parent.calibration.legacy.jsonable(row)


def open_journal(commit):
    return Journal(OUTPUT/'cells', parent.frozen.identity(DESIGN, commit, parent.frozen.runtime(),
        'synthetic-native-signal-controls'), expected_keys(), STATUSES)


def run(commit, shard):
    if isinstance(shard, bool) or not isinstance(shard, Integral) or shard not in (0, 1): raise ValueError('shard must be0 or1')
    design = parent.frozen.verify(DESIGN, RULES, SOURCES, commit)
    context, coefficients, metadata = open_inputs()
    if design['metadata'] != parent.calibration.legacy.jsonable(metadata): raise ValueError('control input identity changed')
    journal = open_journal(commit); selected = GEOMETRIES[shard]
    groups = list(dict.fromkeys(k[:-1] for k in expected_keys() if k[1] == selected))
    cache = {}; worker = OUTPUT/'workers'; worker.mkdir(exist_ok=True)
    with locked(worker, 'shard-'+str(shard)+'.lock'):
        for group in groups:
            pending = [(*group, arm) for arm in ARMS if journal.read((*group, arm)) is None]
            if not pending: continue
            section, sid, truth, phase, scene, flux, draw = group
            geometry_key = (sid, phase)
            if geometry_key not in cache:
                try: cache[geometry_key] = (inputs.prepare_geometry(context, sid, OBS_ID, int(phase), coefficients), None)
                except Exception as exc: cache[geometry_key] = (None, type(exc).__name__+': '+str(exc))
            geometry, error = cache[geometry_key]; realized = None
            if error is None:
                try: realized = inputs.realize(geometry, section, truth, scene, int(flux), int(draw))
                except Exception as exc: error = type(exc).__name__+': '+str(exc)
            for key in pending:
                row = (attempt(geometry, realized, key) if error is None else
                       {'status': 'preparation_failed', 'error': error, 'failure_stage': 'geometry_or_realization',
                        'geometry_source_id': sid, 'obs_id': OBS_ID, 'true_flux_jy': int(flux)*1e-6})
                journal.write(key, row)
                print('CONTROL', *key, row['status'], round(row.get('elapsed_seconds', 0.), 2), flush=True)
    parent.assert_assessment_unopened()


def summarize(commit):
    design = parent.frozen.verify(DESIGN, RULES, SOURCES, commit)
    _, _, metadata = open_inputs()
    if design['metadata'] != parent.calibration.legacy.jsonable(metadata): raise ValueError('summary input identity differs')
    journal = open_journal(commit); records = journal.records(require_complete=True)
    summary = {'schema': 'signal-control-study-summary-1', 'protocol_commit': commit,
        'design_sha256': parent.calibration.legacy.lab.digest(DESIGN),
        'cell_digest': parent.calibration.record_digest(journal, records),
        'metrics': summarize_signal_control(records, expected_keys()),
        'assessment_opened': False, 'promotion': False}
    path = OUTPUT/'summary.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != summary: raise ValueError('summary already exists with different content')
    else: atomic(path, summary)
    print(json.dumps({'planned': summary['metrics']['planned'], 'status_counts': summary['metrics']['status_counts'],
        'noiseless_clean': summary['metrics']['noiseless_clean_gate']['passed_count'],
        'noisy_clean_passed': sum(r['observed_sample_gate_passed'] for r in summary['metrics']['noisy_clean_gates']),
        'preservation': summary['metrics']['noiseless_preservation_guard']['passed_count']}, indent=2))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', action='store_true'); parser.add_argument('--commit')
    parser.add_argument('--shard', type=int); parser.add_argument('--summary', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        if args.commit or args.shard is not None or args.summary: parser.error('freeze must be separate')
        create_design(); print('FROZEN', parent.calibration.legacy.relative(DESIGN))
    elif args.summary:
        if not args.commit or args.shard is not None: parser.error('summary requires commit only')
        summarize(args.commit)
    else:
        if not args.commit or args.shard is None: parser.error('run needs committed protocol and shard')
        run(args.commit, args.shard)
