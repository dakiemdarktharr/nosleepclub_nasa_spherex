"""Replay and publish the sealed conditional presence experiment.

No random stream or position fit is run here. The QR replay independently
checks the stored SVD projection and the complete detection arithmetic. The
result remains conditional on the opened geometry and synthetic scene model.
"""
import argparse
import gzip
from hashlib import sha256
import json
import os
import tempfile

if __name__ == '__main__':
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[name] = '1'

import astropy.units as u
import numpy as np
from scipy.stats import beta

from . import run_presence_study as study
from . import presence_experiment_inputs as inputs
from . import run_wise_linked_study as legacy
from . import publish_neighbor_intervention as compare
from .science_jobs import atomic


OUT = study.ROOT / 'web/data/source-presence'
RTOL = 1e-7
ATOL = 1e-9


def _array_hash(values):
    a = np.ascontiguousarray(values, dtype='<f8')
    return sha256(str(a.shape).encode('ascii') + b'|' + a.tobytes()).hexdigest()


def qr_operator(templates, error, nuisance):
    """Independent normalized QR projection in whitened pixel coordinates."""
    t = np.asarray(templates, float);e = np.asarray(error, float);b = np.asarray(nuisance, float)
    if (t.ndim != 2 or e.ndim != 1 or t.shape[1] != len(e) or b.ndim != 2
            or b.shape[0] != len(e) or not np.isfinite(t).all() or not np.isfinite(e).all()
            or not np.isfinite(b).all() or np.any(e <= 0)):
        raise ValueError('invalid QR inputs')
    whitened = b / e[:, None]
    norms = np.linalg.norm(whitened, axis=0)
    if np.any(norms <= 0) or not np.isfinite(norms).all():
        raise ValueError('invalid nuisance norms')
    normalized = whitened / norms
    singular = np.linalg.svd(normalized, compute_uv=False)
    if len(singular) != b.shape[1] or singular[-1] <= singular[0] * 1e-10:
        raise ValueError('rank deficient nuisance')
    q, _ = np.linalg.qr(normalized, mode='reduced')
    w = (t / e).T
    unprojected = np.linalg.norm(w, axis=0)
    residual = w - q @ (q.T @ w)
    residual -= q @ (q.T @ residual)
    norm = np.linalg.norm(residual, axis=0)
    if np.any(unprojected <= 0) or np.any(norm <= 1e-10 * unprojected):
        raise ValueError('source has insufficient projected information')
    return {'directions': (residual / norm).T, 'norm': norm,
            'fraction': (norm / unprojected) ** 2,
            'rank': b.shape[1], 'condition': float(singular[0] / singular[-1])}


def replay_geometry(snapshot):
    """Rebuild physical native templates from pinned inputs, without score operator."""
    frames, _ = inputs.prior.inputs.read_verified_frames()
    groups, prepared, errors = inputs.prior.prepare_configuration(frames, 'strict')
    if any(errors) or [len(g) for g in groups] != [2, 2]:
        raise ValueError('invalid strict geometry')
    compare.recursive_equal(snapshot['rules'], inputs.RULES, 'geometry rules')
    grid = inputs.grid();compare.close(snapshot['grid_sky_px'], grid, 'grid')
    gain = inputs.prior.load_gain();directions = [];geometries = [];observed = []
    for epoch in range(2):
        nearest = inputs.semantic.prepare_semantic(prepared[epoch], inputs.RULES['grid']['center'],
                                                    background_order=1, epsf_kind='nearest')
        planned = [f['record']['obs_id'] for f in groups[epoch]]
        if [v['obs_id'] for v in prepared[epoch]] != planned or [v['obs_id'] for v in nearest] != planned:
            raise ValueError('reconstructed exposure order mismatch')
        for old, item in zip(prepared[epoch], nearest): inputs.validate_prepared_pair(old, item)
        geo = inputs.prior.control_geometry(prepared[epoch], nearest, gain)
        geometries.extend(geo);observed.extend(item['data'] for item in nearest)
        for i in range(2):
            g = geo[i]; saved = snapshot['frames'][epoch*2+i]
            if saved['obs_id'] != g['obs_id']:
                raise ValueError('geometry exposure identity mismatch')
            for label, actual in [('x', g['x']), ('y', g['y']),
                    ('pixel_omega_sr', g['omega'].to_value(u.sr)),
                    ('gain_mjysr_per_electron_rate', g['gain'].to_value(inputs.control.GAIN)),
                    ('observed_error_mjysr', g['error'])]:
                compare.close(saved[label], actual, 'geometry ' + label)
            bank = []
            if len(saved['variants']) != 2:
                raise ValueError('geometry variant count mismatch')
            for v, name in enumerate(inputs.VARIANTS):
                item = inputs.semantic.prepare_semantic([prepared[epoch][i]], inputs.RULES['grid']['center'],
                                                         background_order=1, epsf_kind=name)[0]
                inputs.validate_prepared_pair(prepared[epoch][i], item)
                ref = saved['variants'][v]
                if ref['variant'] != name:
                    raise ValueError('geometry variant identity mismatch')
                compare.recursive_equal(ref['metadata'], legacy.jsonable(item['metadata']), 'variant metadata')
                compare.recursive_equal(ref['neighbor_ids'], item['neighbor_ids'], 'neighbor ids')
                compare.close(ref['background_design'], item['background_design'], 'background columns')
                compare.close(ref['neighbor_design_per_jy'], item['neighbor_design'], 'neighbor columns')
                templates = np.asarray([item['renderer'](p).to_value(inputs.I/u.Jy) for p in grid])
                if sha256(legacy.encoded(templates)).hexdigest() != ref['templates_sha256']:
                    raise ValueError('native template hash mismatch')
                nuisance = np.column_stack((item['background_design'], item['neighbor_design']))
                q = qr_operator(templates, item['error'], nuisance)
                for label, actual in [('projected_directions', q['directions']),
                        ('projected_norm_per_jy', q['norm']), ('information_fraction', q['fraction']),
                        ('nuisance_condition', q['condition'])]:
                    compare.close(ref[label], actual, label, rtol=RTOL, atol=ATOL)
                if ref['nuisance_rank'] != q['rank']:
                    raise ValueError('nuisance rank mismatch')
                bank.append({'directions': q['directions'], 'error': np.asarray(item['error'], float)})
            directions.append(bank)
    inputs.validate_epoch_order(geometries)
    if len({g['obs_id'] for g in geometries}) != 4:
        raise ValueError('duplicate exposure')
    if sha256(legacy.encoded(observed)).hexdigest() != snapshot['observed_data_sha256']:
        raise ValueError('observed data hash mismatch')
    scenarios = [inputs.truth_scenario(geometries, s) for s in inputs.SCENARIOS]
    compare.recursive_equal(snapshot['truth_scenarios'], scenarios, 'truth scenarios')
    return directions


def independent_score(data, operators, grid):
    """Replay signed scores and max/min search, without production scorer."""
    if len(data) != 4 or len(operators) != 4:
        raise ValueError('four frames required')
    grid = np.asarray(grid, float)
    scores = []
    for variant in range(2):
        series = []
        for frame in range(4):
            op = operators[frame][variant]
            y = np.asarray(data[frame], float)
            error = np.asarray(op['error'], float)
            if y.shape != error.shape or not np.isfinite(y).all() or np.any(error <= 0):
                raise ValueError('invalid saved realization')
            series.append(np.asarray(op['directions']) @ (y / error))
        scores.append(series)
    scores = np.asarray(scores)
    if scores.shape != (2, 4, len(grid)) or not np.isfinite(scores).all():
        raise ValueError('invalid replay score')
    before, after, winners = [], [], []
    for v in range(2):
        maxima = []
        for epoch in range(2):
            values = np.maximum(scores[v, 2*epoch:2*epoch+2], 0.)
            totals = (values * values).sum(axis=0)
            index = int(np.argmax(totals));maxima.append(float(totals[index]))
            winners.append({'variant': inputs.VARIANTS[v], 'epoch': ('before', 'after')[epoch],
                            'grid_index': index, 'grid_sky_px': grid[index].tolist(),
                            'signed_frame_scores': scores[v, 2*epoch:2*epoch+2, index].tolist()})
        before.append(maxima[0]);after.append(maxima[1])
    per_variant = np.minimum(before, after)
    return {'before': before, 'after': after, 'per_variant': per_variant.tolist(),
            'combined': float(max(per_variant)), 'winners': winners}


def audit_record(record, snapshot, operators, threshold):
    stage, scenario_id, draw_text = record['key'];row = record['payload']
    scenarios = inputs.SCENARIOS
    index = next((i for i, s in enumerate(scenarios) if s['id'] == scenario_id), None)
    if index is None or row.get('scenario_index') != index or row.get('draw') != int(draw_text):
        raise ValueError('record scenario/draw identity mismatch')
    compare.recursive_equal(row['scenario'], scenarios[index], 'record scenario')
    if stage == 'calibration' and index >= 2:
        raise ValueError('positive case in calibration')
    realization = row.get('realization')
    if realization is None:
        if row['status'] != 'score_failed': raise ValueError('completed record lacks realization')
        return False
    frames = realization['frames']
    if len(frames) != 4: raise ValueError('realization frame count mismatch')
    data = []
    for i, item in enumerate(frames):
        seed = [inputs.RULES['seed_prefix'], 0 if stage == 'calibration' else 1,
                index, int(draw_text), i//2, i%2]
        expected = snapshot['truth_scenarios'][index]['frames'][i]
        if item['obs_id'] != snapshot['frames'][i]['obs_id'] or item['seed'] != seed:
            raise ValueError('realization exposure or seed mismatch')
        prov = item['provenance'];source = prov['source_provenance']
        if (source.get('scenario') != scenario_id or source.get('seed') != seed
                or source.get('source') != 'fixed independent Gaussian-family conditional presence scene'
                or prov['rng_bit_generator'] != 'PCG64' or prov['pixels'] != len(item['data_mjysr'])
                or prov['background_values_sha256'] != _array_hash(expected['background_mjysr'])
                or prov['background_error_values_sha256'] != _array_hash(snapshot['frames'][i]['observed_error_mjysr'])):
            raise ValueError('scene provenance mismatch')
        gain_provenance = {'source': inputs.prior.gain_paths.URL,
                           'sha256': inputs.prior.gain_binding.GAIN_SHA256,
                           'orientation': 'conditional public R6 binding'}
        ramp = prov['source_ramp']
        mask = np.ones((1, len(item['data_mjysr'])), dtype='u1')
        mask_hash = sha256(str(mask.shape).encode('ascii') + b'|' + mask.tobytes()).hexdigest()
        if (prov['gain_provenance'] != gain_provenance or ramp['gain_provenance'] != gain_provenance
                or ramp['source_provenance'] != source
                or ramp['source_values_sha256'] != _array_hash([expected['expected_source_mjysr']])
                or ramp['gain_values_sha256'] != _array_hash([snapshot['frames'][i]['gain_mjysr_per_electron_rate']])
                or ramp['valid_mask_sha256'] != mask_hash or ramp['shape'] != list(mask.shape)
                or ramp['valid_pixels'] != len(item['data_mjysr'])
                or ramp['rng_bit_generator'] != 'PCG64'
                or ramp['rng_state_before'] != prov['rng_state_before']):
            raise ValueError('source and gain provenance mismatch')
        data.append(item['data_mjysr'])
    if sha256(legacy.encoded(data)).hexdigest() != realization['realization_sha256']:
        raise ValueError('realization data hash mismatch')
    replay = independent_score(data, operators, snapshot['grid_sky_px'])
    if row['status'] == 'score_failed':
        # The original failure remains a failure for every denominator and gate.
        return True
    compare.recursive_equal(row['score'], replay, 'independent score')
    if stage == 'validation':
        decision = row['score']['combined'] > threshold
        if row.get('accepted') is not decision:
            raise ValueError('strict threshold decision mismatch')
    return True


def case_summaries(records, threshold):
    n = inputs.RULES['draws_per_case'];output = []
    for scenario in inputs.SCENARIOS:
        rows = [r['payload'] for r in records if r['key'][1] == scenario['id']]
        if len(rows) != n: raise ValueError('validation case denominator changed')
        done = [r for r in rows if r['status'] == 'score_completed']
        failed = len(rows) - len(done)
        accepted = sum(r['accepted'] is True for r in done)
        null = scenario['flux_jy'] == 0
        successes = accepted + failed if null else accepted
        bound = (1. if successes == n else float(beta.ppf(.975, successes+1, n-successes))) if null else (
                0. if successes == 0 else float(beta.ppf(.025, successes, n-successes+1)))
        gate = bound <= .01 if null else (bound >= .8 if scenario['flux_jy'] == .0006 else None)
        output.append({'scenario': scenario['id'], 'role': 'null' if null else 'positive',
                       'flux_ujy': scenario['flux_jy'] * 1e6, 'background': scenario['background'],
                       'planned': n, 'completed': len(done), 'failed': failed, 'accepted': accepted,
                       'conservative_events': successes, 'false_accept_upper': bound if null else None,
                       'power_lower': None if null else bound,
                       'one_sided_confidence': .975, 'gate_pass': gate})
    return output


def build(commit, threshold_commit):
    study.frozen.verify(study.DESIGN, study.RULES, study.SOURCES, commit)
    for path in (study.GEOMETRY, study.THRESHOLD, study.OUTPUT/'calibration'/'header.json',
                 study.OUTPUT/'validation'/'header.json'):
        if not path.is_file() or path.is_symlink():
            raise ValueError('required completed study artifact missing')
    threshold = study.verify_threshold(commit, threshold_commit)
    snapshot = json.loads(study.GEOMETRY.read_text(encoding='utf-8'))
    geometry_sha = legacy.lab.digest(study.GEOMETRY);runtime = study.frozen.runtime()
    cal = study.open_journal(commit, runtime, 'calibration', geometry_sha)
    val = study.open_journal(commit, runtime, 'validation', geometry_sha, threshold, threshold_commit)
    calibration = cal.records(require_complete=True);validation = val.records(require_complete=True)
    operators = replay_geometry(snapshot)
    replayed = sum(audit_record(row, snapshot, operators, threshold['threshold'])
                   for row in calibration + validation)
    cases = case_summaries(validation, threshold['threshold'])
    cal_counts, val_counts = cal.counts(), val.counts()
    validation_digest = sha256(legacy.encoded({
        'header_sha256': legacy.lab.digest(val.directory/'header.json'),
        'records': [{'key': r['key'], 'checksum': r['checksum']} for r in validation]})).hexdigest()
    def stage_counts(counts):
        return {'planned': counts['expected'], 'completed': counts['statuses']['score_completed'],
                'failed': counts['statuses']['score_failed'], 'recorded': counts['recorded'],
                'missing': counts['missing']}
    overview = {'schema': 'source-presence-overview-1', 'protocol_commit': commit,
                'threshold_commit': threshold_commit,
                'threshold': {**threshold, 'value': threshold['threshold'], 'threshold_commit': threshold_commit},
                'geometry_sha256': geometry_sha, 'validation_journal_sha256': validation_digest,
                'audit_source_sha256': legacy.lab.digest(study.ROOT/'scripts/publish_presence_study.py'),
                'calibration': stage_counts(cal_counts),
                'validation': stage_counts(val_counts), 'cases': cases,
                'audit_counts': {'records': len(calibration) + len(validation),
                                 'saved_realizations_replayed': replayed,
                                 'failures_without_realization': len(calibration) + len(validation) - replayed},
                'conditional_gates_passed': all(c['gate_pass'] is not False for c in cases),
                'qualification': inputs.RULES['qualifications'], 'promotion': False,
                'audit_qualification': 'QR template projection and saved-data score replay; does not regenerate or prove noise draws'}
    full = {'overview': overview, 'geometry': snapshot,
            'calibration_header': json.loads((cal.directory/'header.json').read_text(encoding='utf8')),
            'validation_header': json.loads((val.directory/'header.json').read_text(encoding='utf8')),
            'calibration_records': calibration, 'validation_records': validation}
    return overview, full


def publish(overview, full, output=OUT):
    output.mkdir(parents=True, exist_ok=True)
    raw = legacy.encoded(full);packed = gzip.compress(raw, compresslevel=9, mtime=0)
    target = output/'records.json.gz'
    fd, temp = tempfile.mkstemp(prefix='.records.', suffix='.tmp', dir=output)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(packed);stream.flush();os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        if os.path.exists(temp): os.unlink(temp)
    result = dict(overview)
    result['download'] = {'path': 'data/source-presence/records.json.gz', 'sha256': sha256(packed).hexdigest(),
                          'bytes': len(packed), 'uncompressed_sha256': sha256(raw).hexdigest(),
                          'uncompressed_bytes': len(raw)}
    atomic(output/'overview.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol-commit', required=True)
    parser.add_argument('--threshold-commit', required=True)
    args = parser.parse_args()
    overview, full = build(args.protocol_commit, args.threshold_commit)
    print(json.dumps(publish(overview, full), indent=2))


if __name__ == '__main__': main()
