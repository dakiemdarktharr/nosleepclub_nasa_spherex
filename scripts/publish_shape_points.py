"""Publish the refused calibration checkpoint; keep assessment unopened."""
from hashlib import sha256
import gzip
import json
import os

if __name__ == '__main__':
    for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                  'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[_name] = '1'

import numpy as np

from . import run_shape_point_study as study
from .publish_reference_covariance import checked_document
from .science_jobs import atomic


COMMIT = '31d07ab777628aecc90af3b244e882e2e6d95b93'
OUT = study.ROOT/'web/data/shape-point-check'
AUDIT = study.ROOT/'data/raw/benchmark/shape-point-audit.json'


def build():
    study.frozen.verify(study.DESIGN, study.RULES, study.SOURCES, COMMIT)
    context, old, old_digest = study.calibration.open_baseline();seal, _ = study.read_coefficients()
    summary = checked_document(study.OUTPUT/'point-summary.json', 'result_sha256')
    audit = checked_document(AUDIT, 'receipt_sha256')
    gate = json.loads(study.GATE.read_text(encoding='utf-8'))
    points = study.open_journal(COMMIT, 'calibration', context)
    records = points.records(require_complete=True)
    digest = study.calibration.record_digest(points, records)
    if (summary['protocol_commit'] != COMMIT or audit['point_protocol_commit'] != COMMIT
            or digest != summary['calibration_point_digest'] or digest != audit['point_journal_digest']
            or digest != gate['calibration_point_digest'] or old_digest != audit['baseline_journal_digest']
            or gate['shape_calibration_cell_digest'] != seal['cell_digest']
            or audit['shape_calibration_cell_digest'] != seal['cell_digest']
            or audit['gate_file_sha256'] != study.legacy.lab.digest(study.GATE)
            or audit['coefficient_seal_sha256'] != study.legacy.lab.digest(study.COEFFICIENTS)):
        raise ValueError('point/audit/shape input binding differs')
    if (gate['assessment_allowed'] is not False or audit['assessment_allowed'] is not False
            or audit['assessment_records_opened'] != 0 or (study.OUTPUT/'assessment').exists()
            or summary['deferred'] != 252 or summary['recorded'] != 168
            or summary['primary']['common_completed_pairs'] != 0):
        raise ValueError('this publication requires the refused, unopened assessment checkpoint')
    for path, expected in audit['audit_source_sha256'].items():
        if study.legacy.lab.digest(study.ROOT/path) != expected:
            raise ValueError('point audit source changed')
    if audit['native_saved_points_audited'] != summary['counts']['fit_completed']:
        raise ValueError('native point audit incomplete')
    by_key = {tuple(r['key']): r['payload'] for r in records}
    failures = []
    for failure in gate['failures']:
        key = tuple(failure['key']);new = by_key[key];original = old.read((*key, 'nearest'))['payload']
        before = original['fit']['final_mode_audit'];after = new['fit']['final_mode_audit']
        modes = after['near_best_modes'];separation = 0.
        for i, a in enumerate(modes):
            for b in modes[i+1:]:
                east_north = study.baseline.sky_residual_arcsec(a['position'], b['position'])
                separation = max(separation, float(np.linalg.norm(east_north)))
        failures.append({**failure, 'baseline_near_best_count': before['near_best_count'],
            'corrected_near_best_count': after['near_best_count'],
            'corrected_mode_maximum_separation_arcsec': separation,
            'baseline_modes': before['near_best_modes'], 'corrected_modes': modes,
            'qualification': 'nine-start, fixed-weight heuristic; not an exhaustive physical-mode posterior'})
    public_gate = {k: v for k, v in gate.items() if k not in ('comparisons', 'failures')}
    public_gate.update(comparison_count=len(gate['comparisons']), failure_count=len(gate['failures']), failure_cases=failures)
    primary = summary['primary']
    old_radials = [r['baseline_radial_arcsec'] for r in primary['rows'] if r['common_completed']]
    overview = {'schema': 'shape-point-overview-1', 'protocol_commit': COMMIT,
        'design_sha256': summary['design_sha256'],
        'coefficient_seal_sha256': summary['coefficient_seal_sha256'],
        'calibration_point_digest': digest, 'assessment_digest': None,
        'calibration_gate_sha256': audit['gate_file_sha256'],
        'planned': 420, 'recorded': 168, 'deferred': 252, 'counts': summary['counts'],
        'calibration_gate': public_gate, 'primary': primary, 'source_rows': summary['source_rows'],
        'baseline_paired_rms_arcsec': float(np.linalg.norm(old_radials)/np.sqrt(len(old_radials))) if old_radials else None,
        'independent_audit': {k: audit[k] for k in ('receipt_sha256', 'native_saved_points_audited',
            'successful_final_start_objectives_audited', 'failed_final_starts_not_replayed',
            'maximum_bvls_objective_delta', 'maximum_model_delta_mjysr', 'maximum_scaled_kkt_violation', 'qualification')},
        'publisher_sha256': study.legacy.lab.digest(study.ROOT/'scripts/publish_shape_points.py'),
        'new_point_fits': summary['counts']['fit_completed']+summary['counts'].get('fit_failed', 0),
        'heldout_outcomes': 0, 'random_draws': 0, 'prospective_fields': 0,
        'promotion': False, 'qualification': summary['qualification']}
    full = {'summary': summary, 'calibration_records': records, 'independent_audit': audit,
            'calibration_failure_modes': failures,
            'deferred_assessment_keys': study.legacy.jsonable(study.allocations(context)['assessment'])}
    return overview, full, audit


def main():
    for name in ('overview.json', 'records.json.gz', 'independent-audit.json'):
        if (OUT/name).exists():
            raise ValueError('point publication already exists; refusing overwrite')
    overview, full, audit = build()
    raw = study.legacy.encoded(full);packed = gzip.compress(raw, compresslevel=9, mtime=0)
    (OUT/'records.json.gz').write_bytes(packed)
    overview['download'] = {'path': 'data/shape-point-check/records.json.gz',
        'bytes': len(packed), 'sha256': sha256(packed).hexdigest(),
        'uncompressed_bytes': len(raw), 'uncompressed_sha256': sha256(raw).hexdigest()}
    atomic(OUT/'overview.json', overview);atomic(OUT/'independent-audit.json', audit)
    print(json.dumps({'recorded': overview['recorded'], 'deferred': overview['deferred'],
        'failure_cases': overview['calibration_gate']['failure_cases'], 'download': overview['download']}, indent=2))


if __name__ == '__main__':
    main()
