"""Staged, frozen native-position check of an already sealed shape vector."""
import argparse
from collections import Counter
from hashlib import sha256
import json
import os
import subprocess
import time

if __name__ == '__main__':
    for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[_key] = '1'

import numpy as np

from . import run_shape_calibration as calibration
from . import run_reference_star_study as baseline
from . import run_wise_linked_study as legacy
from . import frozen_experiment as frozen
from .experiment_journal import Journal
from .science_jobs import atomic, locked
from .shape_native_inputs import prepare_shape_sample
from .moment_preserving_epsf import physical_parameters, numeric_parameters
from .shape_point_metrics import summarize_primary


ROOT = frozen.ROOT
DESIGN = ROOT/'web/data/shape-point-check/design.json'
COEFFICIENTS = ROOT/'web/data/shape-correction/coefficient-seal.json'
GATE = ROOT/'web/data/shape-point-check/calibration-gate.json'
OUTPUT = ROOT/'data/raw/benchmark/shape-point-check'
CALIBRATION_COMMIT = '972c8b8723326bc60e99ebd8611e1beb6efd34b3'
STATUSES = ('fit_completed', 'fit_failed', 'preparation_failed')
RULES = {
    'version': '0.10.0-shape-point-check.1',
    'scope': 'staged development on the already opened WISE reference cohort',
    'calibration_cells': 168, 'assessment_cells': 252, 'primary_assessment_cells': 56,
    'calibration': '14 old training IDs by first six chronological exposures per season',
    'primary_assessment': 'seven old heldout IDs by last four exposures per season',
    'secondary_assessment': 'all remaining reserved cells; descriptive only',
    'coefficient_selection': 'one source-balanced vector sealed before new point fitting; no refit or model choice here',
    'point_model': 'unchanged signed-Jy neighbor_epoch_model with planar background, nearest spatial ePSF and the sealed correction on target plus every neighbor',
    'max_irls_iterations': 20, 'position_bound_common_px': 2.5,
    'start_offsets': list(baseline.model.START_OFFSETS),
    'original_errors': 'unchanged observed VARIANCE; no oracle source error',
    'calibration_gate': {'all_old_numerical_cells_stay_supported': True,
        'linearization_error_p90_max_common_px': .02,
        'linearization_error_max_common_px': .05},
    'assessment_requires': 'supported calibration gate and its immutable Git commit before any assessment point fit',
    'primary_gate': {'minimum_supported_sources': 5, 'minimum_common_frames_per_source_per_season': 2,
        'no_new_numerical_refusals': True,
        'equal_source_mean_radial_improvement_min_arcsec': .05,
        'p90_radial_increase_max_arcsec': .05,
        'paired_new_rms_max_arcsec': .5, 'paired_new_p90_max_arcsec': 1.},
    'gate_interpretation': 'necessary developmental effect/support budgets, not mission requirements or an independent scientific accuracy certificate',
    'source_removal': False, 'random_draws': 0, 'new_fields': 0,
    'covariance_or_detection_promotion': False, 'promotion': False,
}
SOURCES = (*calibration.SOURCES,
    'scripts/run_shape_point_study.py', 'scripts/publish_shape_calibration.py',
    'scripts/shape_point_metrics.py', 'tests/test_shape_point_metrics.py',
    'tests/test_shape_point_study.py', 'tests/test_shape_calibration_publication.py',
    'docs/SHAPE_POINT_PROTOCOL.md',
    'web/data/shape-correction/design.json',
    'web/data/shape-correction/coefficient-seal.json',
    'web/data/shape-correction/overview.json',
    'web/data/shape-correction/calibration-records.json.gz',
)


def read_coefficients():
    seal = json.loads(COEFFICIENTS.read_text(encoding='utf-8'))
    if (seal.get('schema') != 'shape-coefficient-seal-1'
            or seal.get('status') != 'conditional_candidate'
            or seal.get('protocol_commit') != CALIBRATION_COMMIT
            or seal.get('units') != ['pix2', 'pix3', 'pix3']
            or seal.get('point_fit_evaluated') is not False or seal.get('promotion') is not False):
        raise ValueError('an unpromoted, pre-point-fit conditional coefficient seal is required')
    values = numeric_parameters(physical_parameters(seal['coefficients']))
    if seal['shape_checks']['passed'] != seal['shape_checks']['planned'] or seal['shape_checks']['passed'] < 1:
        raise ValueError('coefficient shape guards incomplete')
    return seal, values


def allocations(context):
    keys, learning, reserved = calibration.planned_cells(context)
    training = set(context.training_ids)
    assessment = [(r['catalog']['source_id'], f['record']['obs_id']) for r in context.references
                  for f in context.frames if (r['catalog']['source_id'], f['record']['obs_id']) not in set(keys)]
    primary = [(sid, obs) for sid, obs in assessment if sid not in training and obs in reserved]
    if (len(keys), len(assessment), len(primary)) != (168, 252, 56):
        raise ValueError('shape position-study denominator changed')
    if len(set(keys+assessment)) != 420 or set(keys) & set(assessment):
        raise ValueError('overlapping or duplicate stage allocation')
    return {'calibration': keys, 'assessment': assessment, 'primary': primary}


def create_design():
    context, _, digest = calibration.open_baseline();seal, _ = read_coefficients()
    return frozen.create(DESIGN, RULES, SOURCES, metadata={
        'expected_keys': allocations(context), 'baseline_journal_digest': digest,
        'coefficient_seal_sha256': legacy.lab.digest(COEFFICIENTS),
        'shape_calibration_cell_digest': seal['cell_digest'],
        'qualification': 'all stars/exposures have old opened outcomes; corrected point outcomes have not yet been evaluated',
    })


def attempt(context, reference, frame, saved, values):
    started = time.monotonic();payload = saved['payload'];stage = 'preparation'
    row = {'source_id': reference['catalog']['source_id'], 'obs_id': frame['record']['obs_id'],
           'epoch': frame['record']['epoch'], 'baseline_checksum': saved['checksum'],
           'baseline_status': payload['status'], 'shape_coefficients': values.tolist()}
    if payload['status'] != 'fit_completed':
        return {**row, 'status': 'preparation_failed', 'failure_stage': 'reused_baseline_unavailable',
                'error': payload['error'], 'elapsed_seconds': time.monotonic()-started}
    try:
        prepared, metadata = baseline.inputs.prepare_cell(context, reference, frame)
        item = prepare_shape_sample(prepared, metadata['anchor_sky_px'], physical_parameters(values))
        row.update(metadata=metadata, samples=baseline.previous.descriptors([item]))
        stage = 'fit'
        fit = baseline.model.fit_epoch(baseline.semantic.model_samples([item]), metadata['anchor_sky_px'],
            data_unit='MJy/sr', nonnegative_neighbors=False, max_irls_iterations=RULES['max_irls_iterations'])
        if [f['obs_id'] for f in fit['frames']] != [frame['record']['obs_id']]:
            raise ValueError('corrected fit exposure differs from planned identity')
        row.update(status='fit_completed', fit=fit,
            baseline_numerical_support=payload['fit']['numerical_support'],
            baseline_position=payload['fit']['position'],
            baseline_residual_east_north_arcsec=payload['residual_east_north_arcsec'],
            residual_east_north_arcsec=baseline.sky_residual_arcsec(fit['position'], metadata['anchor_sky_px']),
            position_change_common_px=np.asarray(fit['position'])-np.asarray(payload['fit']['position']))
    except Exception as exc:
        row.update(status='fit_failed' if stage == 'fit' else 'preparation_failed',
                   failure_stage=stage, error=type(exc).__name__+': '+str(exc),
                   start_reports=legacy.jsonable(getattr(exc, 'start_reports', [])))
    row['elapsed_seconds'] = time.monotonic()-started
    return legacy.jsonable(row)


def open_journal(commit, stage, context):
    if stage not in ('calibration', 'assessment'):
        raise ValueError('explicit calibration or assessment stage required')
    return Journal(OUTPUT/stage,
        frozen.identity(DESIGN, commit, frozen.runtime(), 'shape-positions-'+stage),
        allocations(context)[stage], STATUSES)


def verify_assessment_gate(commit, protocol_commit, context):
    if not isinstance(commit, str) or len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('committed calibration gate required before assessment')
    blob = subprocess.check_output(['git', 'show', commit+':'+legacy.relative(GATE)], cwd=ROOT, stderr=subprocess.DEVNULL)
    if sha256(blob).hexdigest() != legacy.lab.digest(GATE):
        raise ValueError('calibration gate Git bytes differ')
    gate = json.loads(blob)
    seal, _ = read_coefficients()
    if (gate['point_protocol_commit'] != protocol_commit or gate['assessment_allowed'] is not True
            or gate['coefficient_seal_sha256'] != legacy.lab.digest(COEFFICIENTS)
            or gate.get('shape_calibration_cell_digest') != seal['cell_digest']):
        raise ValueError('calibration gate does not permit assessment')
    journal = open_journal(protocol_commit, 'calibration', context)
    if gate['calibration_point_digest'] != calibration.record_digest(journal, journal.records(require_complete=True)):
        raise ValueError('calibration position records differ from sealed gate')
    return gate


def run(commit, stage, gate_commit=None):
    design = frozen.verify(DESIGN, RULES, SOURCES, commit)
    context, old, digest = calibration.open_baseline();_, values = read_coefficients()
    if (design['metadata']['expected_keys'] != legacy.jsonable(allocations(context))
            or design['metadata']['baseline_journal_digest'] != digest):
        raise ValueError('point-study identities or baseline changed')
    if stage == 'assessment':
        verify_assessment_gate(gate_commit, commit, context)
    journal = open_journal(commit, stage, context);planned = set(allocations(context)[stage])
    worker_root = OUTPUT/'workers';worker_root.mkdir(exist_ok=True)
    with locked(worker_root, stage+'.lock'):
        for reference in context.references:
            sid = reference['catalog']['source_id']
            for frame in context.frames:
                obs = frame['record']['obs_id'];key = (sid, obs)
                if key not in planned or journal.read(key) is not None:
                    continue
                row = attempt(context, reference, frame, old.read((*key, 'nearest')), values)
                journal.write(key, row)
                print('CHECKPOINT', stage, sid, obs, row['status'], round(row['elapsed_seconds'], 2), flush=True)
    records = journal.records(require_complete=True)
    print('STAGE_COMPLETE', stage, dict(Counter(r['payload']['status'] for r in records)), flush=True)


def calibration_gate(commit):
    design = frozen.verify(DESIGN, RULES, SOURCES, commit)
    context, _, digest = calibration.open_baseline();seal, values = read_coefficients()
    if (design['metadata'].get('expected_keys') != legacy.jsonable(allocations(context))
            or design['metadata'].get('baseline_journal_digest') != digest
            or design['metadata'].get('coefficient_seal_sha256') != legacy.lab.digest(COEFFICIENTS)
            or design['metadata'].get('shape_calibration_cell_digest') != seal['cell_digest']):
        raise ValueError('calibration gate baseline/design or coefficient identity changed')
    points = open_journal(commit, 'calibration', context);point_records = points.records(require_complete=True)
    cal_keys, _, _ = calibration.planned_cells(context)
    cal_identity = frozen.identity(calibration.DESIGN, CALIBRATION_COMMIT, frozen.runtime(), 'calibration-only-shape-score')
    score_journal = Journal(calibration.OUTPUT/'cells', cal_identity, cal_keys, calibration.STATUSES)
    score_records = score_journal.records(require_complete=True)
    score_digest = calibration.record_digest(score_journal, score_records)
    if score_digest != seal['cell_digest']:
        raise ValueError('shape calibration score digest differs from sealed coefficients')
    comparisons = [];failures = []
    for record in score_records:
        cell = record['payload']
        if cell['status'] != 'information_available':
            continue
        key = tuple(record['key']);new = points.read(key)['payload']
        if new['status'] != 'fit_completed' or not new['fit']['numerical_support']:
            failures.append({'key': list(key), 'reason': new.get('error', new.get('fit', {}).get('numerical_reasons'))})
            continue
        predicted = np.asarray(cell['position_shape_response'])@values
        actual = np.asarray(new['position_change_common_px'])
        comparisons.append({'key': list(key), 'predicted_change_common_px': predicted.tolist(),
                            'actual_change_common_px': actual.tolist(),
                            'linearization_error_common_px': float(np.linalg.norm(actual-predicted))})
    errors = [c['linearization_error_common_px'] for c in comparisons]
    p90 = float(np.quantile(errors, .9)) if errors else None
    largest = max(errors) if errors else None
    reasons = []
    if failures or len(comparisons) != sum(r['payload']['status'] == 'information_available' for r in score_records):
        reasons.append('old_numerical_cell_no_longer_supported')
    if p90 is None or p90 > RULES['calibration_gate']['linearization_error_p90_max_common_px']:
        reasons.append('linearization_p90')
    if largest is None or largest > RULES['calibration_gate']['linearization_error_max_common_px']:
        reasons.append('linearization_maximum')
    gate = {'schema': 'shape-position-calibration-gate-1', 'point_protocol_commit': commit,
        'coefficient_seal_sha256': legacy.lab.digest(COEFFICIENTS),
        'calibration_point_digest': calibration.record_digest(points, point_records),
        'shape_calibration_cell_digest': score_digest,
        'planned': len(point_records), 'counts': dict(Counter(r['payload']['status'] for r in point_records)),
        'comparisons': comparisons, 'failures': failures,
        'linearization_error_p90_common_px': p90, 'linearization_error_max_common_px': largest,
        'reasons': reasons, 'assessment_allowed': not reasons,
        'qualification': 'conditional numerical adequacy only; no evidence yet of heldout position accuracy', 'promotion': False}
    if GATE.exists():
        if json.loads(GATE.read_text(encoding='utf-8')) != gate:
            raise ValueError('calibration gate already exists with different content')
    else:
        atomic(GATE, gate)
    print(json.dumps({k: gate[k] for k in ('planned', 'counts', 'assessment_allowed', 'reasons',
        'linearization_error_p90_common_px', 'linearization_error_max_common_px')}, indent=2))
    return gate


def summarize(commit, gate_commit=None):
    design = frozen.verify(DESIGN, RULES, SOURCES, commit)
    context, old, digest = calibration.open_baseline();seal, _ = read_coefficients()
    allocation = allocations(context)
    if (design['metadata']['expected_keys'] != legacy.jsonable(allocation)
            or design['metadata']['baseline_journal_digest'] != digest):
        raise ValueError('summary baseline or allocation changed')
    gate = json.loads(GATE.read_text(encoding='utf-8'))
    if (gate['point_protocol_commit'] != commit or gate['shape_calibration_cell_digest'] != seal['cell_digest']
            or gate['coefficient_seal_sha256'] != legacy.lab.digest(COEFFICIENTS)):
        raise ValueError('summary calibration gate identity changed')
    cal_journal = open_journal(commit, 'calibration', context)
    cal_records = cal_journal.records(require_complete=True)
    if calibration.record_digest(cal_journal, cal_records) != gate['calibration_point_digest']:
        raise ValueError('summary calibration point records changed')
    assessment_records = [];assessment_digest = None
    if gate['assessment_allowed']:
        verify_assessment_gate(gate_commit, commit, context)
        assessment = open_journal(commit, 'assessment', context)
        assessment_records = assessment.records(require_complete=True)
        assessment_digest = calibration.record_digest(assessment, assessment_records)
    combined = {tuple(r['key']): r['payload'] for r in (*cal_records, *assessment_records)}
    old_primary = {key: old.read((*key, 'nearest'))['payload'] for key in allocation['primary']}
    epochs = {f['record']['obs_id']: f['record']['epoch'] for f in context.frames}
    primary = summarize_primary(allocation['primary'], combined, old_primary, epochs, RULES['primary_gate'])
    sources = []
    for reference in context.references:
        sid = reference['catalog']['source_id']
        counts = Counter(combined.get((sid, f['record']['obs_id']), {}).get('status', 'not_evaluated') for f in context.frames)
        sources.append({'source_id': sid, 'legacy_split': reference['split'], 'planned': 20, 'counts': dict(counts)})
    result = {'schema': 'shape-position-summary-1', 'protocol_commit': commit,
        'design_sha256': legacy.lab.digest(DESIGN), 'coefficient_seal_sha256': legacy.lab.digest(COEFFICIENTS),
        'calibration_point_digest': gate['calibration_point_digest'], 'assessment_digest': assessment_digest,
        'calibration_gate': gate, 'primary': primary, 'source_rows': sources,
        'planned': 420, 'recorded': len(combined), 'deferred': 420-len(combined),
        'counts': dict(Counter(r['status'] for r in combined.values())),
        'qualification': 'all opened development data; a passing developmental gate does not certify scientific accuracy, calibrated covariance or detection',
        'promotion': False}
    result['result_sha256'] = sha256(legacy.encoded(result)).hexdigest()
    path = OUTPUT/'point-summary.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != result:
            raise ValueError('point summary exists with different terminal outcomes')
    else:
        atomic(path, result)
    print(json.dumps({'planned': 420, 'recorded': len(combined), 'deferred': 420-len(combined),
        'primary_gates': primary['gates'], 'primary_improvement_arcsec': primary['equal_source_mean_radial_improvement_arcsec']}, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--design', action='store_true');group.add_argument('--run', action='store_true')
    group.add_argument('--calibration-gate', action='store_true')
    group.add_argument('--summary', action='store_true')
    parser.add_argument('--protocol-commit');parser.add_argument('--gate-commit')
    parser.add_argument('--stage', choices=('calibration', 'assessment'))
    args = parser.parse_args()
    if args.design:
        create_design();print('DESIGN_WRITTEN', legacy.relative(DESIGN))
    elif not args.protocol_commit:
        parser.error('explicit --protocol-commit required')
    elif args.calibration_gate:
        calibration_gate(args.protocol_commit)
    elif args.summary:
        summarize(args.protocol_commit, args.gate_commit)
    elif args.stage is None:
        parser.error('--run requires --stage')
    else:
        run(args.protocol_commit, args.stage, args.gate_commit)


if __name__ == '__main__':
    main()
