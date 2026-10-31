"""Audit saved corrected calibration points; never optimize positions or open assessment."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
import subprocess

if __name__ == '__main__':
    for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                  'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[_name] = '1'

import astropy.units as u
import numpy as np

from . import run_shape_point_study as study
from . import publish_reference_stars as point_auditor
from .experiment_journal import Journal
from .science_jobs import atomic


COMMIT = '31d07ab777628aecc90af3b244e882e2e6d95b93'
RECEIPT = study.ROOT/'data/raw/benchmark/shape-point-audit.json'
AUDIT_SOURCES = ('scripts/audit_shape_points.py', 'tests/test_shape_point_audit.py',
                 'scripts/publish_reference_stars.py', 'scripts/publish_neighbor_intervention.py')
EXPECTED_FAILURES = {
    ('5756942110218608640', '2025W46_2A_0214_3'),
    ('5756958431094222592', '2025W46_2A_0214_3'),
}


def assert_close(a, b, name, *, rtol=1e-10, atol=1e-12):
    a = np.asarray(a, float);b = np.asarray(b, float)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all() or not np.allclose(a, b, rtol=rtol, atol=atol):
        raise ValueError('audit mismatch: '+name)


def reconstruct_gate(score_records, point_records, baseline_records, values):
    """Recompute every fixed-response comparison from saved fit positions."""
    values = np.asarray(values, float)
    if values.shape != (3,) or not np.isfinite(values).all():raise ValueError('invalid sealed coefficients')
    comparisons = [];failures = [];seen = set()
    for record in score_records:
        key = tuple(record['key'])
        if key in seen:raise ValueError('duplicate shape-score key')
        seen.add(key);cell = record['payload']
        if cell['status'] != 'information_available':continue
        if key not in point_records or key not in baseline_records:raise ValueError('missing comparison record')
        point = point_records[key];baseline = baseline_records[key]
        if baseline['status'] != 'fit_completed' or baseline['fit']['numerical_support'] is not True:
            raise ValueError('information cell lacks a supported old point')
        if point['status'] != 'fit_completed' or point['fit']['numerical_support'] is not True:
            failures.append({'key': list(key), 'reason': point.get('error', point.get('fit', {}).get('numerical_reasons'))})
            continue
        response = np.asarray(cell['position_shape_response'], float)
        if response.shape != (2, 3) or not np.isfinite(response).all():raise ValueError('invalid position response')
        predicted = response@values
        actual = np.asarray(point['fit']['position'], float)-np.asarray(baseline['fit']['position'], float)
        assert_close(actual, point['position_change_common_px'], 'stored fitted-point change')
        comparisons.append({'key': list(key), 'predicted_change_common_px': predicted.tolist(),
                            'actual_change_common_px': actual.tolist(),
                            'linearization_error_common_px': float(np.linalg.norm(actual-predicted))})
    errors = [r['linearization_error_common_px'] for r in comparisons]
    return {'comparisons': comparisons, 'failures': failures,
            'p90': float(np.quantile(errors, .9)) if errors else None,
            'max': float(max(errors)) if errors else None}


def verify_gate(gate, calculated):
    if gate.get('assessment_allowed') is not False or gate.get('promotion') is not False:
        raise ValueError('expected unpromoted failing calibration gate')
    if gate.get('reasons') != ['old_numerical_cell_no_longer_supported']:
        raise ValueError('unexpected calibration gate failure reasons')
    if gate.get('failures') != calculated['failures']:
        raise ValueError('saved calibration gate failure list differs')
    actual = gate['comparisons'];expected = calculated['comparisons']
    if len(actual) != len(expected) or [r['key'] for r in actual] != [r['key'] for r in expected]:
        raise ValueError('saved calibration gate comparison keys differ')
    for saved, recomputed in zip(actual, expected):
        for name in ('predicted_change_common_px', 'actual_change_common_px', 'linearization_error_common_px'):
            assert_close(saved[name], recomputed[name], name)
    assert_close(gate['linearization_error_p90_common_px'], calculated['p90'], 'p90')
    assert_close(gate['linearization_error_max_common_px'], calculated['max'], 'maximum')
    if (calculated['p90'] > study.RULES['calibration_gate']['linearization_error_p90_max_common_px']
            or calculated['max'] > study.RULES['calibration_gate']['linearization_error_max_common_px']):
        raise ValueError('linearization thresholds differ from gate')


def audit_native(row, old, item, metadata):
    """Audit a saved position and final-start profiles; no position fitting."""
    if study.legacy.jsonable(metadata) != old['metadata'] or study.legacy.jsonable(metadata) != row['metadata']:
        raise ValueError('reconstructed baseline/point metadata changed')
    sample = old['samples'][0]
    if (sample['x'] != item['metadata']['x'] or sample['y'] != item['metadata']['y']
            or sample['neighbor_ids'] != item['neighbor_ids']):
        raise ValueError('baseline mask or neighbor identity differs')
    for name, expected in (('data', sample['data_mjysr']), ('error', sample['error_mjysr']),
                           ('background_design', sample['background_design'])):
        assert_close(item[name], expected, 'unchanged '+name, rtol=1e-12, atol=0.)
    if row['baseline_numerical_support'] != old['fit']['numerical_support']:
        raise ValueError('old numerical support differs')
    assert_close(row['baseline_position'], old['fit']['position'], 'old position')
    assert_close(row['baseline_residual_east_north_arcsec'], old['residual_east_north_arcsec'], 'old residual')
    assert_close(row['position_change_common_px'], np.asarray(row['fit']['position'])-old['fit']['position'], 'position change')
    result = point_auditor.audit_point(row, item, np.asarray(metadata['anchor_sky_px']))
    frame = row['fit']['frames'][0]
    target = item['renderer'](row['fit']['position']).to_value(u.MJy/u.sr/u.Jy)
    model = (frame['target_flux_jy']*target+item['background_design']@np.asarray(frame['background_coefficients'])
             + item['neighbor_design']@np.asarray(frame['neighbor_flux_jy']))
    delta = float(np.max(np.abs(model-np.asarray(frame['model']))))
    return {'successful_final_starts': result['final_start_replay']['successful_start_count'],
            'failed_final_starts': result['final_start_replay']['failed_start_count'],
            'maximum_bvls_objective_delta': result['final_start_replay']['max_absolute_difference'],
            'maximum_model_delta_mjysr': delta,
            'maximum_scaled_kkt_violation': result['frame']['max_scaled_kkt_violation']}


def run():
    if (study.OUTPUT/'assessment').exists() or (study.OUTPUT/'assessment').is_symlink():
        raise ValueError('assessment directory exists; refusing calibration-only audit')
    if RECEIPT.exists() or RECEIPT.is_symlink():raise ValueError('audit receipt already exists')
    design = study.frozen.verify(study.DESIGN, study.RULES, study.SOURCES, COMMIT)
    for path in AUDIT_SOURCES[2:]:
        blob = subprocess.check_output(['git', 'show', COMMIT+':'+path], cwd=study.ROOT, stderr=subprocess.DEVNULL)
        if sha256(blob).hexdigest() != study.legacy.lab.digest(study.ROOT/path):
            raise ValueError('saved-point audit helper differs from committed version: '+path)
    context, old, old_digest = study.calibration.open_baseline();seal, values = study.read_coefficients()
    allocation = study.allocations(context);seal_sha = study.legacy.lab.digest(study.COEFFICIENTS)
    meta = design['metadata']
    if (meta['expected_keys'] != study.legacy.jsonable(allocation) or meta['baseline_journal_digest'] != old_digest
            or meta['coefficient_seal_sha256'] != seal_sha or meta['shape_calibration_cell_digest'] != seal['cell_digest']):
        raise ValueError('frozen point design identity differs')
    points = study.open_journal(COMMIT, 'calibration', context);records = points.records(require_complete=True)
    point_digest = study.calibration.record_digest(points, records)
    cal_keys, _, _ = study.calibration.planned_cells(context)
    identity = study.frozen.identity(study.calibration.DESIGN, study.CALIBRATION_COMMIT,
                                     study.frozen.runtime(), 'calibration-only-shape-score')
    score = Journal(study.calibration.OUTPUT/'cells', identity, cal_keys, study.calibration.STATUSES)
    score_records = score.records(require_complete=True)
    score_digest = study.calibration.record_digest(score, score_records)
    gate = json.loads(study.GATE.read_text(encoding='utf-8'))
    if (score_digest != seal['cell_digest'] or gate['shape_calibration_cell_digest'] != score_digest
            or gate['point_protocol_commit'] != COMMIT or gate['coefficient_seal_sha256'] != seal_sha
            or gate['calibration_point_digest'] != point_digest or gate['planned'] != 168):
        raise ValueError('saved gate, journals or seal identity differs')
    baseline_rows = {};point_rows = {};counts = Counter()
    for record in records:
        key = tuple(record['key']);row = record['payload'];saved = old.read((*key, 'nearest'));prior = saved['payload']
        if (row['source_id'], row['obs_id']) != key or row['baseline_checksum'] != saved['checksum']:
            raise ValueError('point source/exposure or baseline checksum differs')
        if row['baseline_status'] != prior['status'] or row['shape_coefficients'] != values.tolist():
            raise ValueError('baseline status or fixed coefficients differ')
        if prior['status'] != 'fit_completed' and (row['status'] != 'preparation_failed'
                or row['failure_stage'] != 'reused_baseline_unavailable' or row['error'] != prior['error']):
            raise ValueError('old terminal failure not retained')
        baseline_rows[key] = prior;point_rows[key] = row;counts[row['status']] += 1
    if dict(counts) != gate['counts'] or set(point_rows) != set(cal_keys):
        raise ValueError('calibration planned keys or counts differ')
    reconstructed = reconstruct_gate(score_records, point_rows, baseline_rows, values)
    verify_gate(gate, reconstructed)
    if ({tuple(f['key']) for f in reconstructed['failures']} != EXPECTED_FAILURES
            or any(f['reason'] != ['multiple_near_best_modes'] for f in reconstructed['failures'])
            or len(reconstructed['comparisons']) != 143):
        raise ValueError('actual failed-cell keys, reasons or comparison denominator differ')
    refs = {r['catalog']['source_id']: r for r in context.references}
    frames = {f['record']['obs_id']: f for f in context.frames}
    native = [];failure_rows = []
    for key, row in point_rows.items():
        if row['status'] != 'fit_completed':
            failure_rows.append({'key': list(key), 'status': row['status'], 'reason': row['error']})
            continue
        sid, obs = key;prepared, metadata = study.baseline.inputs.prepare_cell(context, refs[sid], frames[obs])
        item = study.prepare_shape_sample(prepared, metadata['anchor_sky_px'], study.physical_parameters(values))
        native.append(audit_native(row, baseline_rows[key], item, metadata))
        if len(native) % 20 == 0:print('SAVED_POINTS_AUDITED', len(native), flush=True)
    if (study.OUTPUT/'assessment').exists() or (study.OUTPUT/'assessment').is_symlink():
        raise ValueError('assessment directory appeared during audit')
    result = {'schema': 'shape-point-independent-audit-1', 'at_utc': datetime.now(timezone.utc).isoformat(),
        'point_protocol_commit': COMMIT, 'shape_calibration_commit': study.CALIBRATION_COMMIT,
        'runtime': study.frozen.runtime(), 'baseline_journal_digest': old_digest,
        'point_journal_digest': point_digest, 'shape_calibration_cell_digest': score_digest,
        'point_design_sha256': study.legacy.lab.digest(study.DESIGN),
        'coefficient_seal_sha256': seal_sha, 'gate_file_sha256': study.legacy.lab.digest(study.GATE),
        'audit_source_sha256': {p: study.legacy.lab.digest(study.ROOT/p) for p in AUDIT_SOURCES},
        'planned': len(records), 'counts': dict(counts), 'native_saved_points_audited': len(native),
        'successful_final_start_objectives_audited': sum(r['successful_final_starts'] for r in native),
        'failed_final_starts_not_replayed': sum(r['failed_final_starts'] for r in native),
        'maximum_bvls_objective_delta': max((r['maximum_bvls_objective_delta'] for r in native if r['maximum_bvls_objective_delta'] is not None), default=None),
        'maximum_model_delta_mjysr': max((r['maximum_model_delta_mjysr'] for r in native), default=None),
        'maximum_scaled_kkt_violation': max((r['maximum_scaled_kkt_violation'] for r in native), default=None),
        'terminal_failures': failure_rows, 'gate_failures': reconstructed['failures'],
        'linearization_comparisons': len(reconstructed['comparisons']),
        'linearization_error_p90_common_px': reconstructed['p90'], 'linearization_error_max_common_px': reconstructed['max'],
        'assessment_allowed': False, 'assessment_records_opened': 0, 'new_position_fits': 0, 'random_draws': 0,
        'promotion': False,
        'qualification': 'Saved native inputs/model/IRLS/mode clusters and fixed-position BVLS replay only; position Jacobian and rank were not independently derived. No independent physical PSF truth, source validity, coverage, scientific improvement or detection is established.'}
    result['receipt_sha256'] = sha256(study.legacy.encoded(result)).hexdigest()
    atomic(RECEIPT, result)
    return result


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(run(), indent=2), flush=True)


if __name__ == '__main__':main()
