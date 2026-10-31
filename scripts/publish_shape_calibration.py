"""Audit saved calibration algebra and seal a conditional shape candidate.

No random stream, point optimizer or heldout outcome is evaluated here. The
audit independently aggregates saved pixel responses, not optical PSF truth.
"""
import argparse
from collections import Counter
from hashlib import sha256
import gzip
import json
import os
from statistics import median

if __name__ == '__main__':
    for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[_key] = '1'

import numpy as np

from . import run_shape_calibration as study
from .experiment_journal import Journal
from .science_jobs import atomic


OUT = study.ROOT/'web/data/shape-correction'


def close(actual, expected, label, rtol=2e-9, atol=1e-10):
    if not np.allclose(actual, expected, rtol=rtol, atol=atol):
        raise ValueError('saved calibration algebra differs: '+label)


def audit_arrays(cells, old_rows):
    """Independent response sums, pixel identity and fixed-weight equations."""
    by_source = {};counts = {};seen = set();pixels = {};responses = []
    max_score_gap = 0.
    for cell in cells:
        key = (cell['source_id'], cell['obs_id'])
        if key in seen or key not in old_rows:
            raise ValueError('duplicate or missing baseline cell')
        seen.add(key);old = old_rows[key]
        sample = old['samples'][0];frame = old['fit']['frames'][0]
        if frame['obs_id'] != key[1] or cell['baseline_checksum'] != old['_checksum']:
            raise ValueError('baseline identity differs')
        if cell['x'] != sample['x'] or cell['y'] != sample['y']:
            raise ValueError('native pixel identity differs')
        error = np.asarray(cell['error']);weights = np.asarray(frame['weights'])
        if not np.array_equal(error, np.asarray(sample['error_mjysr'])) or not np.array_equal(error, frame['error']):
            raise ValueError('original pixel error differs')
        if np.any(error <= 0) or np.any(weights <= 0) or np.any(weights > 1):
            raise ValueError('invalid original errors or fixed weights')
        R = np.asarray(cell['shape_score_pixel_response']);white = np.sqrt(weights)/error
        P = R/white[None, :]
        F = P@P.T;score = R@np.asarray(frame['residual'])
        close(F, cell['shape_information_scaled'], 'per-cell information')
        close(score, cell['shape_score_scaled'], 'per-cell residual score')
        # A correctly projected response annihilates the fitted nuisance model.
        data_score = R@np.asarray(sample['data_mjysr'])
        close(data_score, score, 'projected data score', atol=1e-8)
        max_score_gap = max(max_score_gap, float(np.max(np.abs(data_score-score))))
        sid = key[0];by_source[sid] = by_source.get(sid, np.zeros((3, 3)))+F
        counts[sid] = counts.get(sid, 0)+1
        native_keys = [(key[1], int(x), int(y)) for x, y in zip(cell['x'], cell['y'])]
        if len(native_keys) != len(set(native_keys)):
            raise ValueError('duplicate native pixel in one cell')
        for native, sigma in zip(native_keys, error):
            if native in pixels:
                close(pixels[native], sigma**2, 'same physical variance', rtol=1e-12, atol=0.)
            pixels[native] = sigma**2
        responses.append((sid, F, score, R, native_keys))
    if not responses:
        raise ValueError('no information cells')
    means = {sid: float(np.trace(F))/counts[sid] for sid, F in by_source.items()}
    reference = median(means.values());weights = {sid: reference/v for sid, v in means.items()}
    ordered = sorted(pixels);index = {key: i for i, key in enumerate(ordered)}
    F = np.zeros((3, 3));score = np.zeros(3);response = np.zeros((3, len(ordered)))
    for sid, Fi, si, Ri, native_keys in responses:
        w = weights[sid];F += w*Fi;score += w*si
        for col, key in enumerate(native_keys):
            response[:, index[key]] += w*Ri[:, col]
    G = np.linalg.solve(F, response);scaled = np.linalg.solve(F, score)
    variance = np.asarray([pixels[key] for key in ordered])
    cov = (G*variance[None, :])@G.T
    return {'scaled_values': scaled, 'scaled_covariance': cov, 'information': F,
            'source_weights': weights, 'source_counts': counts,
            'unique_pixels': len(ordered), 'maximum_projected_data_score_gap': max_score_gap}


def build(commit):
    study.frozen.verify(study.DESIGN, study.RULES, study.SOURCES, commit)
    context, old, old_digest = study.open_baseline()
    result = json.loads(study.RESULT.read_text(encoding='utf-8'))
    body = {k: v for k, v in result.items() if k != 'result_sha256'}
    if result['result_sha256'] != sha256(study.legacy.encoded(body)).hexdigest():
        raise ValueError('calibration result checksum differs')
    identity = study.frozen.identity(study.DESIGN, commit, study.frozen.runtime(), 'calibration-only-shape-score')
    if result['identity'] != identity:
        raise ValueError('calibration identity differs')
    keys, _, _ = study.planned_cells(context)
    journal = Journal(study.OUTPUT/'cells', identity, keys, study.STATUSES)
    records = journal.records(require_complete=True)
    if result['cell_digest'] != study.record_digest(journal, records):
        raise ValueError('calibration cell digest differs')
    cells = [{**r['payload'], 'key': r['key']} for r in records if r['payload']['status'] == 'information_available']
    originals = {}
    for cell in cells:
        key = (cell['source_id'], cell['obs_id']);saved = old.read((*key, 'nearest'))
        originals[key] = {**saved['payload'], '_checksum': saved['checksum']}
    audit = audit_arrays(cells, originals)
    d = result['diagnostic']
    close(audit['scaled_values'], d['unconstrained_scaled_values'], 'composite estimate')
    close(audit['scaled_covariance'], d['conditional_scaled_covariance'], 'composite covariance')
    close(audit['information'], d['scaled_information'], 'composite information')
    for sid, value in audit['source_weights'].items():
        close(value, d['source_weights'][sid], 'source weight')
    if audit['source_counts'] != d['source_counts'] or audit['unique_pixels'] != d['unique_original_pixels']:
        raise ValueError('source/pixel denominator differs')
    if result['status'] == 'conditional_candidate' and (
            result['reasons'] or len(result['shape_checks']) != len(cells)
            or any(c['status'] != 'shape_supported' for c in result['shape_checks'])):
        raise ValueError('conditional candidate lacks all shape guards')
    overview = {
        'schema': 'shape-calibration-overview-1', 'protocol_commit': commit,
        'design_sha256': study.legacy.lab.digest(study.DESIGN),
        'baseline_protocol_commit': study.BASELINE_COMMIT, 'baseline_journal_digest': old_digest,
        'result_sha256': result['result_sha256'], 'result_file_sha256': study.legacy.lab.digest(study.RESULT),
        'cell_digest': result['cell_digest'], 'status': result['status'], 'reasons': result['reasons'],
        'planned': result['planned'], 'counts': result['counts'],
        'coefficients': d['unconstrained_physical_values'], 'units': study.RULES['shape_units'],
        'parameter_names': study.RULES['shape_names'], 'bounds': list(study.DEFAULT_BOUNDS),
        'conditional_standard_errors': (np.sqrt(np.diag(audit['scaled_covariance']))*np.asarray(study.DEFAULT_BOUNDS)).tolist(),
        'condition': d['condition'], 'maximum_source_fraction': d['maximum_source_fraction'],
        'shape_checks': {'planned': len(cells), 'passed': sum(c['status'] == 'shape_supported' for c in result['shape_checks'])},
        'sources': [{'source_id': sid, 'planned': 12, 'information_available': d['source_counts'].get(sid, 0),
                     'weight': d['source_weights'].get(sid)} for sid in context.training_ids],
        'audit': {'saved_cells': len(cells), 'unique_original_pixels': audit['unique_pixels'],
                  'maximum_projected_data_score_gap': audit['maximum_projected_data_score_gap'],
                  'scope': 'independent algebra on saved responses; raw optical truth, noise draws and positions not refitted'},
        'audit_source_sha256': study.legacy.lab.digest(study.ROOT/'scripts/publish_shape_calibration.py'),
        'new_point_fits': 0, 'heldout_outcomes': 0, 'random_draws': 0, 'prospective_fields': 0,
        'promotion': False,
        'qualification': result['qualification'],
    }
    scales = np.asarray(study.DEFAULT_BOUNDS)
    seal = {'schema': 'shape-coefficient-seal-1', 'protocol_commit': commit,
        'design_sha256': overview['design_sha256'], 'status': result['status'],
        'result_sha256': result['result_sha256'], 'cell_digest': result['cell_digest'],
        'coefficients': overview['coefficients'], 'units': overview['units'],
        'conditional_covariance': (audit['scaled_covariance']*scales[:, None]*scales[None, :]).tolist(),
        'bounds': overview['bounds'], 'shape_checks': overview['shape_checks'],
        'point_fit_evaluated': False, 'promotion': False, 'qualification': result['qualification']}
    return study.legacy.jsonable(overview), seal, {'calibration_result': result, 'records': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--protocol-commit', required=True)
    args = parser.parse_args();overview, seal, full = build(args.protocol_commit)
    for name in ('overview.json', 'coefficient-seal.json', 'calibration-records.json.gz'):
        if (OUT/name).exists():
            raise ValueError('calibration publication exists; do not overwrite a viewed product')
    raw = study.legacy.encoded(full);packed = gzip.compress(raw, compresslevel=9, mtime=0)
    (OUT/'calibration-records.json.gz').write_bytes(packed)
    overview['download'] = {'path': 'data/shape-correction/calibration-records.json.gz',
        'bytes': len(packed), 'sha256': sha256(packed).hexdigest(),
        'uncompressed_bytes': len(raw), 'uncompressed_sha256': sha256(raw).hexdigest()}
    atomic(OUT/'overview.json', overview);atomic(OUT/'coefficient-seal.json', seal)
    print(json.dumps({'status': overview['status'], 'planned': overview['planned'],
                      'counts': overview['counts'], 'coefficients': overview['coefficients'],
                      'audit': overview['audit'], 'download': overview['download']}, indent=2))


if __name__ == '__main__':
    main()
