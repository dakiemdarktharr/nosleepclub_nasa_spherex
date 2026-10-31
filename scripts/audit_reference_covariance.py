"""Independent audit of saved baseline covariance, without point optimization."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import time

if __name__ == '__main__':
    for _thread in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                    'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[_thread] = '1'

import astropy.units as u
import numpy as np
from scipy.linalg import solve_triangular

from . import run_reference_covariance_study as study
from .experiment_journal import Journal
from .science_jobs import atomic

COMMIT = 'b42515e3a4ac95df5e786d47f5ff18ad706b937b'
RECEIPT = study.ROOT/'data/raw/benchmark/reference-covariance-audit.json'
AUDIT_FILES = ('scripts/audit_reference_covariance.py', 'tests/test_reference_covariance_audit.py')


def compare(actual, expected, label, maxima, *, rtol=2e-9, atol=2e-12):
    a = np.asarray(actual, float);b = np.asarray(expected, float)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError(label+': shape or finite-value mismatch')
    delta = np.abs(a-b)
    maxima[label] = float(np.max(delta)) if delta.size else 0.
    if not np.allclose(a, b, rtol=rtol, atol=atol):
        raise ValueError(label+': mismatch, maximum absolute difference '+str(maxima[label]))


def assemble_independently(cells, training, exposures):
    """Explicit per-pixel outer products, source Gaia blocks and dense GLS."""
    n = len(cells);size = 2*n
    if not n or len({tuple(c['key']) for c in cells}) != n:
        raise ValueError('unique nonempty cells required')
    pixel_entries = {};gaia = {};jac = [];ids = []
    for i, c in enumerate(cells):
        sid, obs = c['key'];ids.append((sid, obs))
        if c['source_id'] != sid or c['obs_id'] != obs:
            raise ValueError('cell key and source/exposure identity differ')
        xs, ys, errors = c['x'], c['y'], np.asarray(c['error'], float)
        A = np.asarray(c['position_pixel_influence'], float)
        if (len(xs) != len(ys) or A.shape != (2, len(xs)) or errors.shape != (len(xs),)
                or np.any(errors <= 0) or not np.isfinite(A).all() or not np.isfinite(errors).all()):
            raise ValueError('invalid saved pixel influence')
        own = set()
        for j, (x, y) in enumerate(zip(xs, ys)):
            if isinstance(x, bool) or isinstance(y, bool) or not isinstance(x, int) or not isinstance(y, int) or x < 0 or y < 0:
                raise ValueError('native coordinate must be a nonnegative integer')
            key = (obs, x, y)
            if key in own:raise ValueError('duplicate native pixel within cell')
            own.add(key);variance = float(errors[j]**2)
            if not np.isfinite(variance) or variance <= 0:raise ValueError('invalid original variance')
            if key not in pixel_entries:pixel_entries[key] = [variance, []]
            if not np.isclose(pixel_entries[key][0], variance, rtol=1e-12, atol=0):
                raise ValueError('same pixel has inconsistent variance')
            pixel_entries[key][1].append((i, A[:, j]))
        meta = c['metadata'];C5 = np.asarray(meta['gaia_covariance_catalog_units'], float)
        J = np.asarray(meta['gaia_jacobian_px_per_catalog_unit'], float)
        if C5.shape != (5, 5) or J.shape != (2, 5) or not np.isfinite(C5).all() or not np.isfinite(J).all():
            raise ValueError('invalid Gaia block')
        if sid in gaia and not np.allclose(gaia[sid], C5, rtol=1e-12, atol=0):
            raise ValueError('Gaia source covariance changed')
        gaia[sid] = C5;jac.append(J)
    pixel = np.zeros((size, size))
    for variance, entries in pixel_entries.values():
        for i, left in entries:
            for j, right in entries:
                pixel[2*i:2*i+2, 2*j:2*j+2] += variance*np.outer(left, right)
    cat = np.zeros_like(pixel)
    for i, (sid, _) in enumerate(ids):
        for j, (other, _) in enumerate(ids):
            if sid == other:cat[2*i:2*i+2, 2*j:2*j+2] = jac[i]@gaia[sid]@jac[j].T
    C = pixel+cat
    ci = [i for i, (sid, _) in enumerate(ids) if sid in training]
    hi = [i for i, (sid, _) in enumerate(ids) if sid not in training]
    if not ci or not hi or len(set(exposures)) != len(exposures):raise ValueError('invalid split or exposures')
    def axes(rows):return np.array([axis for i in rows for axis in (2*i, 2*i+1)])
    ca = axes(ci);ha = axes(hi);index = {e: j for j, e in enumerate(exposures)}
    if any(e not in index for _, e in ids):raise ValueError('unknown exposure')
    def design(rows):
        H = np.zeros((2*len(rows), 2*len(exposures)))
        for j, i in enumerate(rows):
            k = index[ids[i][1]];H[2*j:2*j+2, 2*k:2*k+2] = np.eye(2)
        return H
    hc = design(ci);hh = design(hi);Ccc = C[np.ix_(ca, ca)]
    inverse_h = np.linalg.solve(Ccc, hc)
    normal = hc.T@inverse_h
    covariance = np.linalg.solve(normal, np.eye(len(normal)))
    L = np.linalg.solve(normal, inverse_h.T)
    offsets = np.asarray([c['raw_offset_px'] for c in cells], float).ravel()
    beta = L@offsets[ca];training_residual = offsets[ca]-hc@beta
    M = np.zeros((len(ha), size));M[np.arange(len(ha)), ha] = 1.;M[:, ca] -= hh@L
    residual = M@offsets;V = M@C@M.T
    marginal = [float(residual[j:j+2]@np.linalg.solve(V[j:j+2, j:j+2], residual[j:j+2]))
                for j in range(0, len(ha), 2)]
    return {'pixel': pixel, 'catalogue': cat, 'total': C, 'unique_pixels': len(pixel_entries),
            'calibration_indices': ci, 'heldout_indices': hi, 'beta': beta, 'frame_covariance': covariance,
            'training_chi2': float(training_residual@np.linalg.solve(Ccc, training_residual)),
            'training_dof': len(ca)-len(beta), 'heldout_chi2': float(residual@np.linalg.solve(V, residual)),
            'heldout_dof': len(ha), 'residual': residual, 'heldout_covariance': V,
            'marginal': np.asarray(marginal), 'linear_map': M}


def audit_native(item, metadata, saved, cell, maxima):
    """Independently reconstruct local influence by column-normalized QR."""
    payload = saved['payload'];fit = payload['fit'];frame = fit['frames'][0];old = payload['samples'][0]
    if metadata != payload['metadata'] or frame['obs_id'] != cell['obs_id']:
        raise ValueError('native old metadata or exposure differs')
    if (item['metadata']['x'] != cell['x'] or item['metadata']['y'] != cell['y']
            or item['metadata']['x'] != old['x'] or item['metadata']['y'] != old['y']
            or item['neighbor_ids'] != old['neighbor_ids'] or item['neighbor_ids'] != frame['neighbor_ids']):
        raise ValueError('native mask, order or neighbor IDs differ')
    if item['neighbor_unit'] != old['neighbor_unit'] or fit['data_unit'] != 'MJy / sr':
        raise ValueError('native physical units differ')
    for actual, expected, label in ((item['data'], old['data_mjysr'], 'native_data'),
            (item['error'], old['error_mjysr'], 'native_error'), (item['error'], frame['error'], 'frame_error'),
            (item['error'], cell['error'], 'saved_error'), (item['background_design'], old['background_design'], 'background'),
            (item['neighbor_design'], old['neighbor_design_per_jy'], 'neighbor_design')):
        local = {};compare(actual, expected, label, local, rtol=1e-12, atol=0.)
        maxima[label] = max(maxima.get(label, 0.), local[label])
    pos = np.asarray(fit['position'], float);anchor = np.asarray(metadata['anchor_sky_px'], float)
    target = item['renderer'](pos).to_value(u.MJy/u.sr/u.Jy)
    flux = frame['target_flux_jy'];derivatives = []
    for axis in range(2):
        left = pos.copy();right = pos.copy()
        left[axis] = max(anchor[axis]-2.5, pos[axis]-.002)
        right[axis] = min(anchor[axis]+2.5, pos[axis]+.002)
        if right[axis] <= left[axis]:raise ValueError('invalid derivative step')
        derivatives.append(flux*(item['renderer'](right).to_value(u.MJy/u.sr/u.Jy)
                            -item['renderer'](left).to_value(u.MJy/u.sr/u.Jy))/(right[axis]-left[axis]))
    J = np.column_stack((*derivatives, target, item['background_design'], item['neighbor_design']))
    model = (flux*target + item['background_design']@np.asarray(frame['background_coefficients'])
             + item['neighbor_design']@np.asarray(frame['neighbor_flux_jy']))
    local = {};compare(np.asarray(item['data'])-model, frame['residual'], 'model_residual', local, rtol=1e-8, atol=1e-11)
    maxima['model_residual'] = max(maxima.get('model_residual', 0.), local['model_residual'])
    weights = np.asarray(frame['weights'], float);err = np.asarray(item['error'], float)
    if np.any(weights <= 0) or np.any(weights > 1):raise ValueError('invalid fixed weights')
    white = np.sqrt(weights)/err;weighted = J*white[:, None]
    scale = np.linalg.norm(weighted, axis=0)
    if not np.isfinite(scale).all() or np.any(scale <= 0):raise ValueError('invalid QR column scale')
    Q, R = np.linalg.qr(weighted/scale, mode='reduced')
    if np.linalg.matrix_rank(R) != R.shape[0]:raise ValueError('rank-deficient QR tangent')
    influence = (solve_triangular(R, Q.T, lower=False)*white[None, :])/scale[:, None]
    local = {};compare(influence[:2], cell['position_pixel_influence'], 'position_influence', local, rtol=2e-8, atol=2e-10)
    maxima['position_influence'] = max(maxima.get('position_influence', 0.), local['position_influence'])


def run(native_limit=None, write_receipt=True):
    started = time.monotonic()
    design = study.frozen.verify(study.DESIGN, study.RULES, study.SOURCES, COMMIT)
    context, old, old_digest = study.shape.open_baseline()
    keys, exposures = study.planned_cells(context)
    heldout = [r['catalog']['source_id'] for r in context.references if r['catalog']['source_id'] not in context.training_ids]
    expected = {'expected_keys': study.legacy.jsonable(keys), 'baseline_journal_digest': old_digest,
                'training_ids': list(context.training_ids), 'planned_exposures': exposures, 'heldout_ids': heldout}
    if any(design['metadata'].get(k) != v for k, v in expected.items()):raise ValueError('frozen cohort identity mismatch')
    identity = study.frozen.identity(study.DESIGN, COMMIT, study.frozen.runtime(), 'baseline-reference-covariance')
    journal = Journal(study.OUTPUT/'cells', identity, keys, study.STATUSES)
    records = journal.records(require_complete=True)
    def unique(pairs):
        d = {}
        for k, v in pairs:
            if k in d:raise ValueError('duplicate result JSON field')
            d[k] = v
        return d
    result = json.loads(study.RESULT.read_text(encoding='utf-8'), object_pairs_hook=unique,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    digest = study.shape.record_digest(journal, records)
    body = {k:v for k, v in result.items() if k != 'result_sha256'}
    if (result.get('result_sha256') != sha256(study.legacy.encoded(body)).hexdigest()
            or result.get('identity') != identity or result.get('cell_digest') != digest
            or result.get('planned') != 420 or result.get('status') != 'descriptive_complete'):
        raise ValueError('result checksum, journal, status or identity mismatch')
    counts = Counter();per_source = {r['catalog']['source_id']: Counter() for r in context.references}
    cells = [];saved_by_key = {}
    for record in records:
        sid, obs = record['key'];cell = record['payload'];saved = old.read((sid, obs, 'nearest'))
        if cell['source_id'] != sid or cell['obs_id'] != obs or cell['baseline_checksum'] != saved['checksum']:
            raise ValueError('source/exposure/baseline checksum differs')
        old_payload = saved['payload'];status = cell['status']
        expected_status = ('baseline_unavailable' if old_payload['status'] != 'fit_completed' else
            'baseline_numerical_refusal' if not old_payload['fit']['numerical_support'] else None)
        if expected_status is not None and status != expected_status:raise ValueError('old refusal status differs')
        if expected_status is None and status not in ('influence_available', 'linearization_failed'):
            raise ValueError('new influence status inconsistent with old baseline')
        counts[status] += 1;per_source[sid][status] += 1
        if status == 'influence_available':
            meta = old_payload['metadata'];sample = old_payload['samples'][0];fit = old_payload['fit']
            if (cell['metadata'] != meta or cell['x'] != sample['x'] or cell['y'] != sample['y']
                    or cell['error'] != sample['error_mjysr'] or cell['error'] != fit['frames'][0]['error']):
                raise ValueError('saved baseline geometry, mask or errors differ')
            expected_raw = (np.asarray(fit['position'])+np.asarray(meta['registration_offset_px'])
                            -np.asarray(meta['anchor_sky_px']))
            if not np.allclose(cell['raw_offset_px'], expected_raw, rtol=1e-12, atol=1e-12):
                raise ValueError('saved raw offset disagrees with baseline registration addback')
            cells.append({**cell, 'key': record['key']});saved_by_key[(sid, obs)] = saved
    if dict(counts) != result['counts'] or set(result['source_counts']) != set(per_source):
        raise ValueError('result source or terminal counts differ')
    for sid, counts_for_source in per_source.items():
        if result['source_counts'][sid] != {'planned': 20, 'statuses': dict(counts_for_source)}:
            raise ValueError('per-source denominator differs')
    diagnostic = result['diagnostic'];maxima = {}
    if diagnostic['row_order'] != [c['key'] for c in cells]:raise ValueError('result row order differs')
    assembled = assemble_independently(cells, set(context.training_ids), exposures)
    if diagnostic['unique_original_pixels'] != assembled['unique_pixels']:
        raise ValueError('unique pixel count differs')
    for label, saved_name, calc_name in (
        ('pixel_covariance', 'pixel_covariance_px2', 'pixel'), ('catalogue_covariance', 'catalogue_covariance_px2', 'catalogue'),
        ('total_covariance', 'total_covariance_px2', 'total'), ('heldout_covariance', 'heldout_residual_covariance_px2', 'heldout_covariance')):
        compare(diagnostic[saved_name], assembled[calc_name], label, maxima)
    if (diagnostic['calibration_indices'] != assembled['calibration_indices']
            or diagnostic['heldout_indices'] != assembled['heldout_indices']):raise ValueError('split differs')
    frame = diagnostic['frame']
    if frame['exposure_ids'] != exposures:raise ValueError('frame exposure order differs')
    expected_frame_counts = [sum(c['source_id'] in context.training_ids and c['obs_id'] == exp for c in cells) for exp in exposures]
    if frame['training_counts'] != expected_frame_counts:raise ValueError('frame training counts differ')
    compare(frame['translation_px'], assembled['beta'].reshape(-1, 2), 'translation', maxima)
    compare(frame['covariance_px2'], assembled['frame_covariance'], 'frame_covariance', maxima)
    compare(frame['training_chi2'], assembled['training_chi2'], 'training_chi2', maxima)
    compare(diagnostic['heldout_joint']['chi2'], assembled['heldout_chi2'], 'heldout_chi2', maxima)
    if frame['training_dof'] != assembled['training_dof'] or diagnostic['heldout_joint']['dof'] != assembled['heldout_dof']:
        raise ValueError('degrees of freedom differ')
    raw = np.asarray([c['raw_offset_px'] for c in cells]);observed = diagnostic['rows']
    compare([r['raw_offset_px'] for r in observed], raw, 'raw_offsets', maxima)
    idx = {obs: i for i, obs in enumerate(exposures)}
    corrected = raw-np.asarray([assembled['beta'].reshape(-1, 2)[idx[c['obs_id']]] for c in cells])
    compare([r['frame_corrected_offset_px'] for r in observed], corrected, 'corrected_offsets', maxima)
    compare([observed[i]['heldout_marginal_mahalanobis2'] for i in assembled['heldout_indices']], assembled['marginal'], 'heldout_marginal', maxima)
    if [r['key'] for r in observed] != [c['key'] for c in cells]:raise ValueError('offset rows differ')
    if set(diagnostic['heldout_by_source']) != set(heldout):raise ValueError('heldout source table differs')
    source_max = {}
    for sid in heldout:
        selected = [j for j, i in enumerate(assembled['heldout_indices']) if cells[i]['source_id'] == sid]
        output = diagnostic['heldout_by_source'][sid]
        if output['available'] != len(selected) or output['dof'] != 2*len(selected):
            raise ValueError('heldout source denominator differs')
        if selected:
            ax = [a for j in selected for a in (2*j, 2*j+1)]
            residual = assembled['residual'][ax];V = assembled['heldout_covariance'][np.ix_(ax, ax)]
            local = {};compare(output['chi2'], residual@np.linalg.solve(V, residual), 'source_chi2', local)
            source_max[sid] = local['source_chi2']
        elif output['chi2'] is not None:
            raise ValueError('empty heldout source has nonempty chi-square')
    maxima['heldout_source_chi2'] = max(source_max.values(), default=0.)
    if native_limit is None:native_limit = len(cells)
    if isinstance(native_limit, bool) or not isinstance(native_limit, int) or not 0 <= native_limit <= len(cells):
        raise ValueError('invalid native audit limit')
    refs = {r['catalog']['source_id']:r for r in context.references};frames = {f['record']['obs_id']:f for f in context.frames}
    native_maxima = {}
    for i, cell in enumerate(cells[:native_limit]):
        sid, obs = cell['key'];prepared, metadata = study.baseline.inputs.prepare_cell(context, refs[sid], frames[obs])
        item = study.baseline.inputs.prepare_variant(prepared, metadata['anchor_sky_px'], 'nearest')
        audit_native(item, metadata, saved_by_key[(sid, obs)], cell, native_maxima)
        if (i+1) % 20 == 0:print('NATIVE_AUDITED', i+1, '/', native_limit, flush=True)
    receipt = {'schema': 'reference-covariance-independent-audit-1', 'at_utc': datetime.now(timezone.utc).isoformat(),
        'frozen_protocol_commit': COMMIT, 'runtime': study.frozen.runtime(),
        'audit_source_sha256': {p: study.legacy.lab.digest(study.ROOT/p) for p in AUDIT_FILES},
        'result_file_sha256': study.legacy.lab.digest(study.RESULT), 'result_sha256': result['result_sha256'],
        'baseline_journal_digest': old_digest, 'cell_digest': digest, 'planned': len(records),
        'counts': dict(counts), 'per_source_counts': {sid: dict(c) for sid, c in per_source.items()},
        'unique_original_pixels': assembled['unique_pixels'], 'max_absolute_differences': maxima,
        'native_available': len(cells), 'native_audited': native_limit, 'native_max_absolute_differences': native_maxima,
        'training_chi2': assembled['training_chi2'], 'training_dof': assembled['training_dof'],
        'heldout_chi2': assembled['heldout_chi2'], 'heldout_dof': assembled['heldout_dof'],
        'elapsed_seconds': time.monotonic()-started, 'new_point_fits': 0, 'random_draws': 0,
        'qualification': 'independent numerical reconstruction conditional on fixed saved geometry, weights, ePSF and catalogue; not a covariance-coverage or scientific accuracy validation'}
    if write_receipt:
        if RECEIPT.exists():raise ValueError('audit receipt already exists; refusing overwrite')
        receipt['receipt_sha256'] = sha256(study.legacy.encoded(receipt)).hexdigest()
        atomic(RECEIPT, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-limit', type=int, default=None)
    parser.add_argument('--dry-run', action='store_true', help='perform checks without writing a receipt')
    args = parser.parse_args()
    print(json.dumps(run(args.native_limit, write_receipt=not args.dry_run), indent=2), flush=True)


if __name__ == '__main__':main()
