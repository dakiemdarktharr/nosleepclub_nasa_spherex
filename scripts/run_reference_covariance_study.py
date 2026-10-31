"""Frozen descriptive baseline covariance diagnostics on the opened cohort.

No new point fit, corrected shape, random realization, or new field is used.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import os

if __name__ == '__main__':
    for _thread in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                    'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[_thread] = '1'

import astropy.units as u
import numpy as np

from . import frozen_experiment as frozen
from . import run_reference_star_study as baseline
from . import run_shape_calibration as shape
from . import run_wise_linked_study as legacy
from . import shared_pixel_covariance as shared
from .experiment_journal import Journal
from .profile_image_influence import centroid_and_shape_influence
from .reference_frame_diagnostics import analyze_reference_frame
from .science_jobs import atomic, locked


ROOT = frozen.ROOT
DESIGN = ROOT/'web/data/reference-covariance/design.json'
OUTPUT = ROOT/'data/raw/benchmark/reference-covariance'
RESULT = OUTPUT/'covariance-result.json'
STATUSES = ('influence_available', 'baseline_unavailable',
            'baseline_numerical_refusal', 'linearization_failed')
QUALIFICATION = ('Conditional descriptive consistency on an already opened, image-selected cohort; '
    'baseline masks, final robust weights, fixed nearest ePSF, legacy registration offsets and neighbor '
    'coordinates are conditioned on, including omission of their noise dependence. Independent catalogue '
    'sources and pixel/catalogue independence are assumed. This is not the complete joint image-estimator '
    'covariance, calibrated coverage, scientific improvement, or an astronomical detection.')
RULES = {
    'version': '0.10.0-reference-covariance.1',
    'scope': 'conditional nearest baseline, 21 already opened references and 20 exposures',
    'baseline_protocol_commit': shape.BASELINE_COMMIT,
    'planned_cells': 420, 'baseline_variant': 'nearest',
    'baseline_completed_numerical_only': True,
    'point': 'old fitted registered sky-grid point plus fixed legacy registration offset minus Gaia anchor',
    'shape': 'fixed baseline nearest ePSF; no learned shape or shape covariance',
    'influence': 'saved-point finite-difference local full nuisance tangent and old fixed Huber weights',
    'pixel_covariance': 'one original noise variable per exposure/native pixel; overlap retained',
    'catalogue_covariance': 'shared five-parameter Gaia source covariance across its epochs; different sources independent',
    'cross_model': 'pixel and catalogue errors independent conditional on legacy geometry',
    'frame': 'joint full-covariance GLS using old training IDs only, minimum four distinct training sources per exposure',
    'heldout': 'all seven old heldout IDs; cross covariance with frame retained; descriptive only',
    'guards': 'no outlier deletion, covariance floors, pseudoinverse, or chi-square rescaling',
    'point_optimization': False, 'random_realizations': False,
    'prospective_fields': False, 'promotion': False,
}
SOURCES = tuple(dict.fromkeys((*shape.SOURCES,
    'scripts/reference_frame_diagnostics.py', 'tests/test_reference_frame_diagnostics.py',
    'scripts/run_reference_covariance_study.py', 'tests/test_reference_covariance_study.py',
    'docs/REFERENCE_COVARIANCE_PROTOCOL.md')))


def planned_cells(context):
    sources = [r['catalog']['source_id'] for r in context.references]
    exposures = [f['record']['obs_id'] for f in context.frames]
    training = tuple(context.training_ids)
    if (len(sources) != 21 or len(set(sources)) != 21 or len(exposures) != 20
            or len(set(exposures)) != 20 or len(training) != 14 or len(set(training)) != 14
            or not set(training) <= set(sources)):
        raise ValueError('opened 21-source/20-exposure cohort or old allocation changed')
    keys = [(sid, obs) for sid in sources for obs in exposures]
    if len(keys) != RULES['planned_cells'] or len(set(keys)) != len(keys):
        raise ValueError('planned covariance denominator changed')
    return keys, exposures


def create_design():
    context, _, digest = shape.open_baseline()
    keys, exposures = planned_cells(context)
    return frozen.create(DESIGN, RULES, SOURCES, metadata={
        'expected_keys': keys, 'baseline_journal_digest': digest,
        'training_ids': list(context.training_ids), 'planned_exposures': exposures,
        'heldout_ids': [r['catalog']['source_id'] for r in context.references
                        if r['catalog']['source_id'] not in context.training_ids],
        'qualification': QUALIFICATION,
    })


def cell_attempt(context, reference, frame, saved):
    sid = reference['catalog']['source_id'];obs = frame['record']['obs_id']
    row = {'source_id': sid, 'obs_id': obs, 'baseline_checksum': saved['checksum']}
    payload = saved['payload']
    if payload['status'] != 'fit_completed':
        return {**row, 'status': 'baseline_unavailable', 'error': payload['error']}
    if not payload['fit']['numerical_support']:
        return {**row, 'status': 'baseline_numerical_refusal',
                'error': '; '.join(payload['fit']['numerical_reasons'])}
    try:
        prepared, metadata = baseline.inputs.prepare_cell(context, reference, frame)
        if legacy.jsonable(metadata) != payload['metadata']:
            raise ValueError('reconstructed baseline metadata changed')
        item = baseline.inputs.prepare_variant(prepared, metadata['anchor_sky_px'], 'nearest')
        n = len(item['data']);q = len(item['neighbor_ids'])
        # Required by the shared tangent helper but exactly zero here: no
        # learned shape, correction, score, or shape-covariance propagation.
        item['shape_renderer'] = lambda _: np.zeros((n, 3))
        item['neighbor_shape_design'] = np.zeros((n, q, 3))
        influence = centroid_and_shape_influence(item, payload['fit'], metadata['anchor_sky_px'])
        raw = (np.asarray(payload['fit']['position'], float)
               + np.asarray(metadata['registration_offset_px'], float)
               - np.asarray(metadata['anchor_sky_px'], float))
        if raw.shape != (2,) or not np.isfinite(raw).all():
            raise ValueError('invalid raw common-grid offset')
        return legacy.jsonable({**row, 'status': 'influence_available', 'metadata': metadata,
            'x': item['metadata']['x'], 'y': item['metadata']['y'], 'error': item['error'],
            'position_pixel_influence': influence['position_pixel_influence'],
            'position_derivative_step_common_px': influence['position_derivative_step_common_px'],
            'local_tangent_condition': influence['condition'], 'raw_offset_px': raw})
    except Exception as exc:
        return {**row, 'status': 'linearization_failed', 'error': type(exc).__name__+': '+str(exc)}


def assemble(cells, training_ids, exposures, heldout_ids):
    """Build the complete shared-pixel/catalogue covariance and diagnostics."""
    if not cells:
        raise ValueError('no usable baseline influence cells')
    registry = shared.make_registry(cells)
    pixel = shared.position_covariance(registry, cells)['pixel_only_covariance_px2']
    sources = [c['source_id'] for c in cells];obs = [c['obs_id'] for c in cells]
    jacobians = [c['metadata']['gaia_jacobian_px_per_catalog_unit'] for c in cells]
    catalogues = {}
    for c in cells:
        sid = c['source_id'];C = shared.finite(c['metadata']['gaia_covariance_catalog_units'], (5, 5), 'Gaia covariance')
        if sid in catalogues and not np.allclose(catalogues[sid], C, rtol=1e-12, atol=0.):
            raise ValueError('source Gaia covariance changed between exposures')
        catalogues[sid] = C
    catalog = shared.catalogue_covariance(sources, jacobians, catalogues)
    total = pixel + catalog
    offsets = np.asarray([c['raw_offset_px'] for c in cells], float)
    result = analyze_reference_frame(offsets*u.pix, total*u.pix**2, sources, obs,
        training_ids, exposures, provenance=QUALIFICATION, min_references=4)
    frame = result.reference_frame
    frame_index = {name: i for i, name in enumerate(frame.exposure_ids)}
    corrected = np.asarray([offsets[i]-frame.offsets.value[frame_index[obs[i]]] for i in range(len(cells))])
    if not np.allclose(corrected[list(result.heldout_indices)], result.residuals.value, rtol=1e-10, atol=1e-12):
        raise ValueError('heldout residual map disagrees with frame correction')
    marginal = {i: float(result.marginal_mahalanobis2[j]) for j, i in enumerate(result.heldout_indices)}
    rows = [{'key': list(c['key']), 'raw_offset_px': offsets[i], 'frame_corrected_offset_px': corrected[i],
             'split': 'training' if i in result.calibration_indices else 'heldout',
             'heldout_marginal_mahalanobis2': marginal.get(i)} for i, c in enumerate(cells)]
    heldout = {}
    for sid in heldout_ids:
        index = [j for j, i in enumerate(result.heldout_indices) if sources[i] == sid]
        if not index:
            heldout[sid] = {'available': 0, 'chi2': None, 'dof': 0}
            continue
        axes = [axis for j in index for axis in (2*j, 2*j+1)]
        r = result.residuals.value[index].ravel()
        block = result.covariance.value[np.ix_(axes, axes)]
        chi2 = float(r@np.linalg.solve(block, r))
        if not np.isfinite(chi2):
            raise ValueError('heldout source diagnostic is nonfinite')
        heldout[sid] = {'available': len(index), 'chi2': chi2, 'dof': len(axes)}
    return legacy.jsonable({
        'row_order': [c['key'] for c in cells], 'rows': rows,
        'pixel_covariance_px2': pixel, 'catalogue_covariance_px2': catalog,
        'total_covariance_px2': total, 'heldout_residual_covariance_px2': result.covariance.value,
        'heldout_indices': result.heldout_indices, 'calibration_indices': result.calibration_indices,
        'unique_original_pixels': len(registry.keys),
        'frame': {'exposure_ids': frame.exposure_ids, 'translation_px': frame.offsets.value,
                  'covariance_px2': frame.covariance.value, 'training_counts': frame.reference_counts,
                  'training_chi2': frame.chi2, 'training_dof': frame.dof},
        'heldout_joint': {'chi2': result.chi2, 'dof': result.dof},
        'heldout_by_source': heldout, 'qualification': QUALIFICATION,
    })


def run(commit):
    design = frozen.verify(DESIGN, RULES, SOURCES, commit)
    context, old, digest = shape.open_baseline()
    keys, exposures = planned_cells(context)
    heldout_ids = [r['catalog']['source_id'] for r in context.references
                   if r['catalog']['source_id'] not in context.training_ids]
    expected = {'expected_keys': legacy.jsonable(keys), 'baseline_journal_digest': digest,
                'training_ids': list(context.training_ids), 'planned_exposures': exposures,
                'heldout_ids': heldout_ids}
    if any(design['metadata'].get(k) != v for k, v in expected.items()):
        raise ValueError('baseline journal or planned source/exposure identities changed')
    identity = frozen.identity(DESIGN, commit, frozen.runtime(), 'baseline-reference-covariance')
    journal = Journal(OUTPUT/'cells', identity, keys, STATUSES)
    with locked(OUTPUT, '.worker.lock'):
        if RESULT.exists() or RESULT.is_symlink():
            if RESULT.is_symlink() or not RESULT.is_file():
                raise ValueError('existing covariance result is not a regular file')
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError('duplicate result JSON key')
                    result[key] = value
                return result
            def invalid_constant(_):
                raise ValueError('nonfinite result JSON value')
            existing = json.loads(RESULT.read_text(encoding='utf-8'), object_pairs_hook=unique,
                                  parse_constant=invalid_constant)
            if not isinstance(existing, dict):
                raise ValueError('invalid existing covariance result')
            body = {k: v for k, v in existing.items() if k != 'result_sha256'}
            if (existing.get('result_sha256') != sha256(legacy.encoded(body)).hexdigest()
                    or existing.get('identity') != identity
                    or existing.get('cell_digest') != shape.record_digest(journal, journal.records(require_complete=True))):
                raise ValueError('existing covariance result identity changed')
            print('RESULT_EXISTS', existing['status'], flush=True)
            return existing
        for reference in context.references:
            sid = reference['catalog']['source_id']
            for frame in context.frames:
                obs = frame['record']['obs_id']
                if journal.read((sid, obs)) is not None:
                    continue
                row = cell_attempt(context, reference, frame, old.read((sid, obs, 'nearest')))
                journal.write((sid, obs), row)
                print('CHECKPOINT', sid, obs, row['status'], flush=True)
        records = journal.records(require_complete=True)
        cells = [{**r['payload'], 'key': r['key']} for r in records if r['payload']['status'] == 'influence_available']
        source_counts = {r['catalog']['source_id']: {'planned': len(exposures), 'statuses': {}}
                         for r in context.references}
        for record in records:
            counts = source_counts[record['key'][0]]['statuses'];status = record['payload']['status']
            counts[status] = counts.get(status, 0)+1
        try:
            diagnostic = assemble(cells, context.training_ids, exposures, heldout_ids);status = 'descriptive_complete';reason = None
        except Exception as exc:
            diagnostic = None;status = 'diagnostic_unavailable';reason = type(exc).__name__+': '+str(exc)
        output = legacy.jsonable({'schema': 'reference-covariance-result-1', 'identity': identity,
            'at_utc': datetime.now(timezone.utc).isoformat(),
            'cell_digest': shape.record_digest(journal, records), 'planned': len(keys),
            'counts': dict(Counter(r['payload']['status'] for r in records)), 'source_counts': source_counts,
            'status': status, 'reason': reason, 'diagnostic': diagnostic,
            'new_point_fits': 0, 'random_draws': 0, 'prospective_fields': 0, 'promotion': False,
            'qualification': QUALIFICATION})
        output['result_sha256'] = sha256(legacy.encoded(output)).hexdigest()
        atomic(RESULT, output)
        print(json.dumps({k: output[k] for k in ('status', 'counts', 'reason')}, indent=2), flush=True)
        return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--design', action='store_true');group.add_argument('--run', action='store_true')
    parser.add_argument('--protocol-commit')
    args = parser.parse_args()
    if args.design:
        create_design();print('DESIGN_WRITTEN', legacy.relative(DESIGN), flush=True)
    elif not args.protocol_commit:
        parser.error('--run requires --protocol-commit')
    else:
        run(args.protocol_commit)


if __name__ == '__main__':
    main()
