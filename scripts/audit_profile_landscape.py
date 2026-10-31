"""Independently audit a frozen saved profile landscape; no position optimization."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
import json
import math
import os

if __name__ == '__main__':
    for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[_key] = '1'

import astropy.units as u
import numpy as np

from . import run_profile_landscape_study as study
from .experiment_journal import Journal
from .science_jobs import atomic


COMMIT = '704e3efc806dddef7906b032ba917745f80442a1'
AUDIT_DIR = study.ROOT/'data/raw/benchmark/profile-landscape-audit'
RECEIPT = AUDIT_DIR/'audit-receipt.json'
FILES = ('scripts/audit_profile_landscape.py', 'tests/test_profile_landscape_audit.py',
         'docs/PROFILE_LANDSCAPE_AUDIT.md')
GLOBAL_INDICES = (0, 12, 25, 38, 50)
LOCAL_INDICES = (0, 10, 20)
LEVELS = (.1, 1., 2.3, 5.991)
STEPS = (.004, .002, .001)
OFFSETS = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1),
           (-1, -1), (-1, 1), (1, -1), (1, 1))
STUDY_FAILURES = ('outside_search_square', 'callback_failed', 'invalid_residual',
                  'residual_dimension_changed', 'nonfinite_cost')


def near(a, b, label, maxima, *, atol=1e-8, rtol=1e-9):
    a = np.asarray(a, dtype=float);b = np.asarray(b, dtype=float)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError(label+': nonfinite or shape mismatch')
    delta = float(np.max(np.abs(a-b))) if a.size else 0.
    maxima[label] = max(maxima.get(label, 0.), delta)
    if not np.allclose(a, b, atol=atol, rtol=rtol):raise ValueError(label+': numeric mismatch')


def independent_components(costs, levels=LEVELS):
    """Flood fill saved finite sublevel nodes without study topology code."""
    if not isinstance(costs, list) or not costs or any(not isinstance(row, list) or not row for row in costs):
        raise ValueError('invalid cost grid')
    height = len(costs);width = len(costs[0])
    if any(len(row) != width for row in costs):raise ValueError('ragged cost grid')
    for row in costs:
        for value in row:
            if value is not None and (type(value) not in (float, int) or not math.isfinite(value) or value < 0):
                raise ValueError('invalid cost node')
    finite = [float(value) for row in costs for value in row if value is not None]
    if not finite:return {'minimum_cost': None, 'valid_nodes': 0, 'missing_nodes': height*width, 'levels': []}
    minimum = min(finite);summaries = []
    for level in levels:
        for conn in (4, 8):
            neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            if conn == 8:neighbors += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            remaining = {(y, x) for y, row in enumerate(costs) for x, v in enumerate(row)
                         if v is not None and v-minimum <= level}
            groups = []
            while remaining:
                start = min(remaining);remaining.remove(start);stack = [start];count = 0;edge = False;missing = False
                while stack:
                    y, x = stack.pop();count += 1
                    edge = edge or y in (0, height-1) or x in (0, width-1)
                    for dy, dx in neighbors:
                        yy, xx = y+dy, x+dx
                        if 0 <= yy < height and 0 <= xx < width:
                            if costs[yy][xx] is None:missing = True
                            if (yy, xx) in remaining:
                                remaining.remove((yy, xx));stack.append((yy, xx))
                groups.append({'nodes': count, 'touches_grid_boundary': edge, 'touches_missing_node': missing})
            summaries.append({'delta_cost': float(level), 'connectivity': conn,
                              'component_count': len(groups), 'components': groups})
    return {'minimum_cost': minimum, 'valid_nodes': len(finite), 'missing_nodes': height*width-len(finite),
            'levels': summaries}


def residual_solver(item, weights, anchor):
    """Fixed-weight WLS via normalized independent least squares at one point."""
    data = np.asarray(item['data'], float);error = np.asarray(item['error'], float)
    bg = np.asarray(item['background_design'], float);neighbors = np.asarray(item['neighbor_design'], float)
    weights = np.asarray(weights, float);anchor = np.asarray(anchor, float)
    if (data.ndim != 1 or error.shape != data.shape or weights.shape != data.shape
            or bg.ndim != 2 or neighbors.ndim != 2 or bg.shape[0] != len(data) or neighbors.shape[0] != len(data)
            or not all(np.isfinite(x).all() for x in (data, error, bg, neighbors, weights, anchor))
            or np.any(error <= 0) or np.any(weights <= 0) or np.any(weights > 1) or anchor.shape != (2,)):
        raise ValueError('invalid fixed WLS inputs')
    white = np.sqrt(weights)/error;wy = data*white
    @lru_cache(maxsize=4096)
    def solve(x, y):
        pos = np.asarray([x, y], float)
        if np.any(np.abs(pos-anchor) > 2.5+1e-12):return {'error_code': 'outside_search_square'}
        try:
            target = np.asarray(item['renderer'](pos).to_value(u.MJy/u.sr/u.Jy), float)
            A = np.column_stack((target, bg, neighbors))*white[:, None]
            scale = np.linalg.norm(A, axis=0)
            if not np.isfinite(A).all() or not np.isfinite(scale).all() or np.any(scale <= 0):
                raise ValueError('invalid WLS design')
            X = A/scale
            coefficients, _, rank, _ = np.linalg.lstsq(X, wy, rcond=1e-10)
            if rank != X.shape[1]:raise ValueError('WLS rank deficient')
            residual = wy-X@coefficients;cost = float(residual@residual)
            if not np.isfinite(residual).all() or not np.isfinite(cost):raise ValueError('invalid WLS residual')
            return {'residual': residual, 'cost': cost}
        except Exception:
            return {'error_code': 'callback_failed'}
    return lambda position: solve(float(position[0]), float(position[1]))


def inspect_grid(grid, x_expected, y_expected, indices, solve, anchor, maxima):
    """Check every axis/node/missing flag/topology and fixed sample replays."""
    if not isinstance(grid, dict):raise ValueError('missing grid object')
    near(grid['x_common_px'], x_expected, 'grid_axis', maxima, atol=1e-12, rtol=0.)
    near(grid['y_common_px'], y_expected, 'grid_axis', maxima, atol=1e-12, rtol=0.)
    costs = grid['costs'];topology = independent_components(costs)
    if len(costs) != len(y_expected) or any(len(row) != len(x_expected) for row in costs):
        raise ValueError('grid cost dimensions differ')
    failures = grid['failures'];missing = {}
    for failure in failures:
        if (set(failure) != {'ix', 'iy', 'error_code'} or type(failure['ix']) is not int
                or type(failure['iy']) is not int or failure['error_code'] not in STUDY_FAILURES):
            raise ValueError('invalid grid failure record')
        key = (failure['iy'], failure['ix'])
        if key in missing or not (0 <= key[0] < len(y_expected) and 0 <= key[1] < len(x_expected)):
            raise ValueError('duplicate or out-of-range grid failure')
        missing[key] = failure['error_code']
    actual_missing = {(y, x) for y, row in enumerate(costs) for x, v in enumerate(row) if v is None}
    if set(missing) != actual_missing:raise ValueError('missing node mask differs from failure records')
    for y, yy in enumerate(y_expected):
        for x, xx in enumerate(x_expected):
            outside = np.any(np.abs(np.asarray([xx, yy])-anchor) > 2.5+1e-12)
            if outside != (missing.get((y, x)) == 'outside_search_square'):
                raise ValueError('outside-bound grid status differs')
    if grid['sampled_connectivity'] != topology:raise ValueError('sampled topology differs')
    checked = 0
    for iy in indices:
        for ix in indices:
            actual = solve([x_expected[ix], y_expected[iy]]);saved = costs[iy][ix]
            if saved is None:
                if actual.get('error_code') != missing[(iy, ix)]:raise ValueError('sampled missing-node replay differs')
            else:
                if 'cost' not in actual:raise ValueError('saved finite node failed independent replay')
                near(saved, actual['cost'], 'grid_cost', maxima)
            checked += 1
    return checked


def expected_origins(rows, local=False):
    grouped = {}
    for arm in ('baseline', 'corrected'):
        fit = rows[arm]['fit']
        if local:
            entries = [(m['position'], {'fit_arm': arm, 'near_best_index': i})
                       for i, m in enumerate(fit['final_mode_audit']['near_best_modes'])]
        else:
            entries = [(fit['position'], {'fit_arm': arm, 'origin': 'point'})]
            entries += [(r['position'], {'fit_arm': arm, 'origin': 'final_start_'+str(i)})
                        for i, r in enumerate(fit['final_mode_audit']['starts']) if r['success']]
        for position, origin in entries:
            xy = tuple(float(x) for x in position)
            if len(xy) != 2 or not np.isfinite(xy).all():raise ValueError('invalid saved candidate')
            grouped.setdefault(xy, []).append(origin)
    return [{'position': list(xy), 'origins': origins} for xy, origins in grouped.items()]


def independent_stencil(solve, point, h):
    p = np.asarray(point, float);items = {k: solve(p+h*np.asarray(k)) for k in OFFSETS}
    errors = sorted({v['error_code'] for v in items.values() if 'error_code' in v})
    if errors:return {'error_codes': errors}
    f = {k: v['cost'] for k, v in items.items()};r = {k: v['residual'] for k, v in items.items()}
    J = np.column_stack(((r[(1, 0)]-r[(-1, 0)])/(2*h), (r[(0, 1)]-r[(0, -1)])/(2*h)))
    gr = 2*J.T@r[(0, 0)]
    gf = np.array([(f[(1, 0)]-f[(-1, 0)])/(2*h), (f[(0, 1)]-f[(0, -1)])/(2*h)])
    mixed = (f[(1, 1)]-f[(1, -1)]-f[(-1, 1)]+f[(-1, -1)])/(4*h*h)
    H = np.array([[(f[(1, 0)]-2*f[(0, 0)]+f[(-1, 0)])/(h*h), mixed],
                  [mixed, (f[(0, 1)]-2*f[(0, 0)]+f[(0, -1)])/(h*h)]])
    GN = 2*J.T@J;norms = np.linalg.norm(J, axis=0);nz = norms > 0
    singular = np.linalg.svd(J[:, nz]/norms[nz], compute_uv=False) if np.any(nz) else np.array([])
    rank = int(np.sum(singular > 1e-10*singular[0])) if len(singular) else 0
    return {'gradient_residual': gr, 'gradient_cost': gf, 'gradient_infinity': np.max(np.abs(gf)),
            'gradient_disagreement_infinity': np.max(np.abs(gf-gr)), 'hessian_cost': H,
            'hessian_cost_eigenvalues': np.linalg.eigvalsh(H), 'gauss_newton': GN,
            'gauss_newton_eigenvalues': np.linalg.eigvalsh(GN), 'residual_jacobian_column_norms': norms,
            'residual_jacobian_scaled_rank': rank,
            'residual_jacobian_scaled_condition': float(singular[0]/singular[-1]) if rank == 2 else None}


def inspect_probe(entry, solve, maxima, *, replay, anchor=None):
    point = entry['position'];saved = entry['diagnostic'];center = solve(point) if replay else None
    if saved['position'] != point:raise ValueError('probe position identity differs')
    outside = anchor is not None and np.any(np.abs(np.asarray(point)-anchor) > 2.5+1e-12)
    if 'error_code' in saved:
        if saved['steps'] or saved['cost'] is not None or saved['error_code'] not in STUDY_FAILURES:
            raise ValueError('invalid failed probe')
        if anchor is not None and outside != (saved['error_code'] == 'outside_search_square'):
            raise ValueError('probe outside-bound classification differs')
        if replay and center.get('error_code') != saved['error_code']:raise ValueError('failed probe replay differs')
        return
    if outside:raise ValueError('outside probe reported as available')
    if (type(saved['cost']) not in (int, float) or not math.isfinite(saved['cost']) or saved['cost'] < 0):
        raise ValueError('invalid probe cost')
    if len(saved['steps']) != 3:raise ValueError('probe step denominator differs')
    if replay:
        if 'cost' not in center:raise ValueError('probe center failed independent WLS')
        near(saved['cost'], center['cost'], 'probe_cost', maxima)
    for h, row in zip(STEPS, saved['steps']):
        if row['step_common_px'] != h:raise ValueError('probe step differs')
        if 'error_codes' in row:
            if not row['error_codes'] or any(x not in (*STUDY_FAILURES, 'nonfinite_derivative') for x in row['error_codes']):
                raise ValueError('invalid stencil failure')
            if anchor is not None:
                crosses = any(np.any(np.abs(np.asarray(point)+h*np.asarray(offset)-anchor) > 2.5+1e-12) for offset in OFFSETS)
                if crosses != ('outside_search_square' in row['error_codes']):
                    raise ValueError('stencil outside-bound classification differs')
            if replay:
                expected = independent_stencil(solve, point, h)
                if expected.get('error_codes') != row['error_codes']:raise ValueError('stencil failure replay differs')
            continue
        if anchor is not None and any(np.any(np.abs(np.asarray(point)+h*np.asarray(offset)-anchor) > 2.5+1e-12) for offset in OFFSETS):
            raise ValueError('outside stencil reported as available')
        if type(row.get('residual_jacobian_scaled_rank')) is not int or row['residual_jacobian_scaled_rank'] not in (0, 1, 2):
            raise ValueError('invalid probe rank')
        fields = ('gradient_residual', 'gradient_cost', 'gradient_infinity', 'gradient_disagreement_infinity',
                  'hessian_cost', 'hessian_cost_eigenvalues', 'gauss_newton', 'gauss_newton_eigenvalues',
                  'residual_jacobian_column_norms', 'residual_jacobian_scaled_condition')
        shapes = {'gradient_residual': (2,), 'gradient_cost': (2,), 'gradient_infinity': (),
                  'gradient_disagreement_infinity': (), 'hessian_cost': (2, 2), 'hessian_cost_eigenvalues': (2,),
                  'gauss_newton': (2, 2), 'gauss_newton_eigenvalues': (2,),
                  'residual_jacobian_column_norms': (2,), 'residual_jacobian_scaled_condition': ()}
        if (row['residual_jacobian_scaled_rank'] == 2) != (row['residual_jacobian_scaled_condition'] is not None):
            raise ValueError('probe rank/condition presence differs')
        for name in fields:
            if name == 'residual_jacobian_scaled_condition' and row[name] is None:continue
            arr = np.asarray(row[name], float)
            if arr.shape != shapes[name] or not np.isfinite(arr).all():raise ValueError('nonfinite or malformed probe metric')
        if replay:
            expected = independent_stencil(solve, point, h)
            if 'error_codes' in expected:raise ValueError('stencil independently unavailable')
            if row['residual_jacobian_scaled_rank'] != expected['residual_jacobian_scaled_rank']:
                raise ValueError('residual Jacobian rank differs')
            for name in fields:
                if row[name] is None or expected[name] is None:
                    if row[name] != expected[name]:raise ValueError('condition presence differs')
                    continue
                # Cost differencing amplifies floating-point replay noise at h=.001.
                atol = 1e-3 if name in ('hessian_cost', 'hessian_cost_eigenvalues') else 1e-6
                near(row[name], expected[name], 'probe_'+name, maxima, atol=atol, rtol=1e-5)


def inspect_native(item, metadata, rows, arm, maxima):
    for fit_arm in ('baseline', 'corrected'):
        row = rows[fit_arm]
        if study.calibration.legacy.jsonable(metadata) != row['metadata']:raise ValueError('saved native metadata differs')
        sample = row['samples'][0]
        if (item['metadata']['x'] != sample['x'] or item['metadata']['y'] != sample['y']
                or item['neighbor_ids'] != sample['neighbor_ids']):raise ValueError('mask or neighbor identity differs')
        for name, field in (('data', 'data_mjysr'), ('error', 'error_mjysr'), ('background_design', 'background_design')):
            near(item[name], sample[field], 'native_'+name, maxima, atol=0., rtol=1e-12)
    expected = rows[arm]['samples'][0]
    near(item['neighbor_design'], expected['neighbor_design_per_jy'], 'native_neighbor_design', maxima, atol=0., rtol=1e-12)
    if u.Unit(item['neighbor_unit']) != u.MJy/u.sr/u.Jy or item['neighbor_unit'] != expected['neighbor_unit']:
        raise ValueError('neighbor units differ')


def inspect_diagnostics(diag, item, metadata, rows, sid, psf, weight, maxima):
    anchor = np.asarray(metadata['anchor_sky_px'], float);weights = rows[weight]['fit']['frames'][0]['weights']
    solve = residual_solver(item, weights, anchor)
    expected = expected_origins(rows);probes = diag['probes']
    if [{'position': x['position'], 'origins': x['origins']} for x in probes] != expected:
        raise ValueError('candidate origins or positions differ')
    point_positions = {tuple(rows[arm]['fit']['position']) for arm in ('baseline', 'corrected')}
    for entry in probes:
        inspect_probe(entry, solve, maxima, replay=tuple(entry['position']) in point_positions, anchor=anchor)
    bound = 2.5;axis_x = anchor[0]+np.linspace(-bound, bound, 51);axis_y = anchor[1]+np.linspace(-bound, bound, 51)
    sampled = inspect_grid(diag['global_grid'], axis_x, axis_y, GLOBAL_INDICES, solve, anchor, maxima)
    locals_expected = expected_origins(rows, local=True) if sid in study.FOCUS else []
    local_grids = diag['local_grids']
    if [{'position': x['position'], 'origins': x['origins']} for x in local_grids] != locals_expected:
        raise ValueError('focus local-grid centers or origins differ')
    for entry in local_grids:
        center = np.asarray(entry['position'])
        sampled += inspect_grid(entry['grid'], center[0]+np.linspace(-.2, .2, 21),
                                center[1]+np.linspace(-.2, .2, 21), LOCAL_INDICES, solve, anchor, maxima)
    replay = diag['saved_objective_replay']
    expected_replay = []
    if psf == weight:
        fit = rows[psf]['fit'];expected_replay = [('point', fit['position'], fit['chi2_weighted'])]
        expected_replay += [('final_start_'+str(i), r['position'], r['chi2'])
                            for i, r in enumerate(fit['final_mode_audit']['starts']) if r['success']]
    if len(replay) != len(expected_replay):raise ValueError('own objective replay denominator differs')
    for saved, (origin, pos, cost) in zip(replay, expected_replay):
        if saved['origin'] != origin or saved['position'] != pos:raise ValueError('own objective replay identity differs')
        near(saved['saved_cost'], cost, 'own_saved_cost', maxima, atol=1e-10, rtol=1e-10)
        value = solve(pos)
        if 'cost' not in value:raise ValueError('own objective independent WLS failed')
        near(saved['replayed_cost'], value['cost'], 'own_replayed_cost', maxima)
        near(saved['saved_cost'], saved['replayed_cost'], 'own_study_replay', maxima, atol=1e-10, rtol=1e-10)
        near(saved['absolute_difference'], abs(saved['replayed_cost']-saved['saved_cost']), 'own_replay_delta', maxima, atol=1e-12, rtol=1e-10)
    return {'sampled_grid_nodes': sampled, 'local_grids': len(local_grids), 'probe_points': len(probes),
            'saved_point_probes': len(point_positions), 'objective_replays': len(replay)}


def bound_input_rows(key, row, saved, corrected):
    """Verify envelope identity and both immutable source-record bindings."""
    sid, obs, psf, weight = key
    if (row.get('source_id'), row.get('obs_id'), row.get('psf_arm'), row.get('weight_arm')) != key:
        raise ValueError('profile payload identity differs')
    if (saved is None or corrected is None or row.get('baseline_checksum') != saved['checksum']
            or row.get('point_checksum') != corrected['checksum']
            or corrected['payload'].get('baseline_checksum') != saved['checksum']):
        raise ValueError('profile input checksum differs')
    rows = {'baseline': saved['payload'], 'corrected': corrected['payload']}
    statuses = {arm: data['status'] for arm, data in rows.items()}
    if row.get('input_statuses') != statuses:raise ValueError('saved input statuses differ')
    return rows, statuses


def unverified_study_failure(row):
    return {'status': 'unverified_study_failure',
            'error': 'study failed before diagnostics could be independently verified',
            'study_error': row.get('error', 'missing error')}


def run():
    if RECEIPT.exists() or RECEIPT.is_symlink():raise ValueError('audit receipt already exists')
    design = study.frozen.verify(study.DESIGN, study.RULES, study.SOURCES, COMMIT)
    context, old, point, values, metadata = study.open_inputs()
    if design['metadata'] != study.calibration.legacy.jsonable(metadata):raise ValueError('frozen profile input identity differs')
    keys = study.expected_keys(context)
    profile = Journal(study.OUTPUT/'cells', study.frozen.identity(study.DESIGN, COMMIT, study.frozen.runtime(),
                      'fixed-profile-landscape'), keys, study.STATUSES)
    records = profile.records(require_complete=True)
    profile_digest = study.calibration.record_digest(profile, records)
    source_hashes = {p: study.calibration.legacy.lab.digest(study.ROOT/p) for p in FILES}
    audit_identity = {'source_sha256': source_hashes, 'profile_commit': COMMIT,
                      'profile_journal_digest': profile_digest, 'profile_design_sha256': study.calibration.legacy.lab.digest(study.DESIGN),
                      'baseline_journal_digest': metadata['baseline_journal_digest'],
                      'point_journal_digest': metadata['point_journal_digest'], 'runtime': study.frozen.runtime()}
    audit = Journal(AUDIT_DIR/'cells', audit_identity, keys, ('verified', 'verified_unavailable', 'unverified_study_failure', 'audit_mismatch'))
    refs = {r['catalog']['source_id']:r for r in context.references};frames = {f['record']['obs_id']:f for f in context.frames}
    cache = {}
    for record in records:
        key = tuple(record['key']);sid, obs, psf, weight = key
        if audit.read(key) is not None:continue
        row = record['payload'];saved = old.read((sid, obs, 'nearest'));corrected = point.read((sid, obs))
        result = {'profile_checksum': record['checksum'], 'profile_status': row.get('status')}
        try:
            rows, statuses = bound_input_rows(key, row, saved, corrected)
            if any(value != 'fit_completed' for value in statuses.values()):
                if row['status'] != 'preparation_failed' or row.get('reused_unavailable') != {arm: value for arm, value in statuses.items() if value != 'fit_completed'}:
                    raise ValueError('saved unavailable fit was not retained')
                result.update(status='verified_unavailable', input_statuses=statuses, study_error=row['error'])
            elif row['status'] != 'profile_completed':
                result.update(unverified_study_failure(row))
            else:
                cache_key = (sid, obs, psf)
                if cache_key not in cache:
                    prepared, native_meta = study.baseline.inputs.prepare_cell(context, refs[sid], frames[obs])
                    item = (study.baseline.inputs.prepare_variant(prepared, native_meta['anchor_sky_px'], 'nearest')
                            if psf == 'baseline' else study.prepare_shape_sample(prepared, native_meta['anchor_sky_px'], study.physical_parameters(values)))
                    cache = {cache_key:(item, native_meta)}
                item, native_meta = cache[cache_key];maxima = {}
                inspect_native(item, native_meta, rows, psf, maxima)
                near(row['anchor_common_px'], native_meta['anchor_sky_px'], 'anchor', maxima, atol=1e-12, rtol=0.)
                detail = inspect_diagnostics(row['diagnostics'], item, native_meta, rows, sid, psf, weight, maxima)
                result.update(status='verified', checks=detail, max_absolute_differences=maxima)
        except Exception as exc:
            result.update(status='audit_mismatch', error=type(exc).__name__+': '+str(exc))
        audit.write(key, result)
        print('AUDIT_CELL', *key, result['status'], flush=True)
    study.assert_assessment_unopened()
    completed = audit.records(require_complete=True);counts = Counter(r['payload']['status'] for r in completed)
    failures = [{'key':r['key'], **r['payload']} for r in completed if r['payload']['status'] in ('audit_mismatch', 'unverified_study_failure')]
    unavailable = [{'key':r['key'], **r['payload']} for r in completed if r['payload']['status'] == 'verified_unavailable']
    maxima = {};checks = Counter()
    for record in completed:
        row = record['payload']
        for name, value in row.get('max_absolute_differences', {}).items():maxima[name] = max(maxima.get(name, 0.), value)
        checks.update(row.get('checks', {}))
    receipt = {'schema':'profile-landscape-independent-audit-1', 'at_utc':datetime.now(timezone.utc).isoformat(),
               'identity':audit_identity, 'audit_cell_digest':study.calibration.record_digest(audit, completed),
               'planned':len(completed), 'counts':dict(counts), 'failures':failures, 'unavailable_cells':unavailable,
               'verification_counts':dict(checks), 'max_absolute_differences':maxima,
               'status':'passed' if not failures else 'findings_or_unverified',
               'assessment_opened':False, 'new_position_fits':0, 'new_noise_draws':0, 'promotion':False,
               'qualification':'Independent fixed-position WLS and sampled-grid arithmetic only; finite grids, conditional weights, physical PSF truth, scientific accuracy and covariance coverage remain unvalidated.'}
    receipt['receipt_sha256'] = sha256(study.calibration.legacy.encoded(receipt)).hexdigest()
    atomic(RECEIPT, receipt)
    return receipt


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(run(), indent=2), flush=True)


if __name__ == '__main__':main()
