"""One frozen, calibration-only, source-balanced ePSF score experiment.

No corrected point optimization, heldout measurement, Monte Carlo realization
or prospective sky field is evaluated. A refusal is a result, not permission
to relax a bound or retry a smaller shape family.
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

import numpy as np

from . import run_reference_star_study as baseline
from . import run_wise_linked_study as legacy
from . import frozen_experiment as frozen
from .experiment_journal import Journal
from .science_jobs import atomic, locked
from .inspect_shape_information import exposure_split
from .shape_native_inputs import prepare_shape_sample
from .moment_preserving_epsf import physical_parameters, DEFAULT_BOUNDS
from .profile_image_influence import centroid_and_shape_influence
from .shared_pixel_covariance import make_registry, add_pixel_response
from .source_balanced_shape import balance_sources, POLICY
from .composite_shape_update import information, solve_update


ROOT = frozen.ROOT
BASELINE_COMMIT = '71f63ca4bab85e9ee51c539cd46ae5bfd50c8bc2'
DESIGN = ROOT/'web/data/shape-correction/design.json'
OUTPUT = ROOT/'data/raw/benchmark/shape-calibration'
RESULT = OUTPUT/'calibration-result.json'
STATUSES = ('information_available', 'baseline_unavailable',
            'baseline_numerical_refusal', 'linearization_failed')
RULES = {
    'version': '0.10.0-shape-calibration.1',
    'scope': 'opened WISE reference cohort; calibration-only development',
    'sources': 'all 14 old training IDs; retain all 168 planned cells',
    'learning_exposures': 'first six chronological MJD-AVG exposures per season',
    'reserved': 'seven old heldout IDs and last four exposures per season; no new outcomes here',
    'baseline_variant': 'nearest', 'baseline_protocol_commit': BASELINE_COMMIT,
    'planned_cells': 168, 'baseline_completed_numerical_only_for_score': True,
    'shape_names': ['width', 'skew_x', 'skew_y'],
    'shape_units': ['pix2', 'pix3', 'pix3'], 'physical_bounds': list(DEFAULT_BOUNDS),
    'shape_family': 'one global width and two odd-third-difference directions with discrete moment gauge',
    'source_balance': POLICY,
    'minimum_sources': 8, 'minimum_distinct_sources_per_season': 4,
    'maximum_source_fraction': .35, 'maximum_information_condition': 100.,
    'maximum_scaled_standard_error': .5,
    'linearization': 'one composite score at old fitted points with old final Huber weights; full nuisance tangent projected out',
    'noise': 'one variable per original exposure/native pixel; shared stamp contributions summed before covariance',
    'uncertainty': 'conditional on baseline points, weights, balance, masks, catalogue and official calibrations; not coverage-calibrated',
    'guard': 'whole three-vector refused if any declared guard fails; no clipping, rank reduction or zero fallback',
    'shape_checks': 'if coefficient guards pass, render target at old anchor and fitted point plus all neighbors in every usable learning cell; require every peak/wing/moment guard',
    'point_optimization': False, 'random_realizations': False,
    'heldout_evaluation': False, 'prospective_fields': False,
    'promotion': False,
}
SOURCES = (
    'scripts/run_shape_calibration.py', 'scripts/source_balanced_shape.py',
    'scripts/moment_preserving_epsf.py', 'scripts/shape_native_inputs.py',
    'scripts/profile_image_influence.py', 'scripts/shared_pixel_covariance.py',
    'scripts/composite_shape_update.py', 'scripts/joint_reference_frame.py',
    'scripts/inspect_shape_information.py',
    'tests/test_moment_preserving_epsf.py', 'tests/test_shape_native_inputs.py',
    'tests/test_profile_image_influence.py', 'tests/test_shared_pixel_covariance.py',
    'tests/test_composite_shape_update.py', 'tests/test_joint_reference_frame.py',
    'tests/test_source_balanced_shape.py', 'tests/test_shape_calibration.py',
    'docs/SHAPE_CALIBRATION_PROTOCOL.md',
    'web/data/shape-correction/feasibility-unweighted.json',
)


def record_digest(journal, records):
    return sha256(legacy.encoded({
        'header_sha256': legacy.lab.digest(journal.directory/'header.json'),
        'records': [{'key': r['key'], 'checksum': r['checksum']} for r in records],
    })).hexdigest()


def open_baseline():
    frozen.verify(baseline.DESIGN, baseline.RULES, baseline.SOURCES, BASELINE_COMMIT)
    context = baseline.inputs.read_context()
    old = Journal(baseline.OUTPUT,
                  frozen.identity(baseline.DESIGN, BASELINE_COMMIT, frozen.runtime(), 'real-reference-stars'),
                  baseline.expected_keys(context), ('fit_completed', 'fit_failed', 'preparation_failed'))
    records = old.records(require_complete=True)
    return context, old, record_digest(old, records)


def planned_cells(context):
    learning, reserved = exposure_split(context)
    keys = [(r['catalog']['source_id'], f['record']['obs_id'])
            for r in context.references if r['catalog']['source_id'] in context.training_ids
            for f in context.frames if f['record']['obs_id'] in learning]
    if len(keys) != RULES['planned_cells'] or len(set(keys)) != len(keys):
        raise ValueError('calibration denominator changed')
    return keys, learning, reserved


def create_design():
    context, _, digest = open_baseline()
    keys, learning, reserved = planned_cells(context)
    return frozen.create(DESIGN, RULES, SOURCES, metadata={
        'expected_keys': keys, 'baseline_journal_digest': digest,
        'training_ids': list(context.training_ids), 'learning_exposures': learning,
        'reserved_exposures': reserved,
        'adaptation_disclosure': 'unweighted information-only preflight was viewed; source balancing was chosen before residual scores or any shape estimate were evaluated',
    })


def cell_attempt(context, reference, frame, saved):
    sid = reference['catalog']['source_id'];obs = frame['record']['obs_id']
    row = {'source_id': sid, 'obs_id': obs, 'key': [sid, obs],
           'epoch': frame['record']['epoch'], 'baseline_checksum': saved['checksum']}
    payload = saved['payload']
    if payload['status'] != 'fit_completed':
        return {**row, 'status': 'baseline_unavailable', 'error': payload['error']}
    if not payload['fit']['numerical_support']:
        return {**row, 'status': 'baseline_numerical_refusal',
                'error': '; '.join(payload['fit']['numerical_reasons'])}
    try:
        prepared, metadata = baseline.inputs.prepare_cell(context, reference, frame)
        item = prepare_shape_sample(prepared, metadata['anchor_sky_px'], physical_parameters([0., 0., 0.]))
        influence = centroid_and_shape_influence(item, payload['fit'], metadata['anchor_sky_px'])
        return legacy.jsonable({**row, 'status': 'information_available', 'metadata': metadata,
            'x': item['metadata']['x'], 'y': item['metadata']['y'], 'error': item['error'],
            'old_position': payload['fit']['position'], **influence})
    except Exception as exc:
        return {**row, 'status': 'linearization_failed', 'error': type(exc).__name__+': '+str(exc)}


def numerical_summary(cells):
    """Save the unconstrained diagnostic even when the entire candidate fails."""
    balance = balance_sources(cells)
    weighted = balance.cells
    info = information(weighted, min_sources=RULES['minimum_sources'],
                       max_condition=RULES['maximum_information_condition'])
    registry = make_registry(weighted)
    score = sum((np.asarray(c['shape_score_scaled']) for c in weighted), np.zeros(3))
    response = add_pixel_response(registry, weighted, response_key='shape_score_pixel_response', output_rows=3)
    G = np.linalg.solve(info['matrix'], response)
    cov = (G*registry.variance[None, :])@G.T
    scaled = np.linalg.solve(info['matrix'], score)
    diagnostic = legacy.jsonable({
        'source_weights': balance.source_weights, 'source_counts': balance.source_counts,
        'reference_mean_trace': balance.reference_mean_trace,
        'scaled_information': info['matrix'], 'condition': info['condition'],
        'source_information_fractions': info['source_fractions'],
        'maximum_source_fraction': info['max_source_fraction'],
        'unconstrained_scaled_values': scaled,
        'unconstrained_physical_values': scaled*np.asarray(DEFAULT_BOUNDS),
        'conditional_scaled_covariance': cov, 'conditional_scaled_standard_errors': np.sqrt(np.diag(cov)),
        'unique_original_pixels': len(registry.keys),
        'weight_uncertainty_propagated': False,
    })
    reasons = []
    if info['max_source_fraction'] > RULES['maximum_source_fraction']:
        reasons.append('source_dominance')
    if not np.isfinite(scaled).all() or np.any(np.abs(scaled) > 1):
        reasons.append('physical_parameter_bounds')
    if not np.isfinite(cov).all() or np.any(np.diag(cov) < 0) or np.any(np.sqrt(np.maximum(0., np.diag(cov))) > RULES['maximum_scaled_standard_error']):
        reasons.append('conditional_precision')
    per_season = {epoch: sorted({c['source_id'] for c in cells if c['epoch'] == epoch})
                  for epoch in ('2025-11', '2026-04')}
    diagnostic['per_season_source_ids'] = per_season
    if any(len(ids) < RULES['minimum_distinct_sources_per_season'] for ids in per_season.values()):
        reasons.append('season_source_support')
    if reasons:
        return diagnostic, reasons, None
    update = solve_update(weighted, registry, min_sources=RULES['minimum_sources'],
        max_source_fraction=RULES['maximum_source_fraction'],
        max_condition=RULES['maximum_information_condition'],
        maximum_scaled_sigma=RULES['maximum_scaled_standard_error'])
    if not np.allclose(update.values, diagnostic['unconstrained_physical_values'], rtol=1e-12, atol=1e-15):
        raise ValueError('independent wrapper/update disagreement')
    return diagnostic, [], update.values


def shape_guard(context, cells, values):
    refs = {r['catalog']['source_id']: r for r in context.references}
    frames = {f['record']['obs_id']: f for f in context.frames}
    checks = []
    for cell in cells:
        row = {'source_id': cell['source_id'], 'obs_id': cell['obs_id'], 'status': 'shape_supported'}
        try:
            prepared, metadata = baseline.inputs.prepare_cell(context, refs[cell['source_id']], frames[cell['obs_id']])
            item = prepare_shape_sample(prepared, metadata['anchor_sky_px'], physical_parameters(values))
            # The adapter checks every neighbor; the target is checked at both
            # the anchor and old saved point. This is not a new point fit.
            at_anchor = item['render_details'](metadata['anchor_sky_px'], physical_parameters(values))
            at_point = item['render_details'](cell['old_position'], physical_parameters(values))
            row.update(anchor=at_anchor.metadata, saved_point=at_point.metadata,
                       neighbors=item['metadata']['corrected_neighbors'])
        except Exception as exc:
            row.update(status='shape_refused', error=type(exc).__name__+': '+str(exc))
        checks.append(legacy.jsonable(row))
    return checks


def run(commit):
    design = frozen.verify(DESIGN, RULES, SOURCES, commit)
    context, old, digest = open_baseline()
    keys, learning, _ = planned_cells(context)
    if (design['metadata']['expected_keys'] != legacy.jsonable(keys)
            or design['metadata']['baseline_journal_digest'] != digest):
        raise ValueError('baseline records or calibration identities changed')
    identity = frozen.identity(DESIGN, commit, frozen.runtime(), 'calibration-only-shape-score')
    # Keep result outside the journal: its root accepts a fixed file inventory.
    journal = Journal(OUTPUT/'cells', identity, keys, STATUSES)
    with locked(OUTPUT, '.worker.lock'):
        if RESULT.exists():
            existing = json.loads(RESULT.read_text(encoding='utf-8'))
            body = {k: v for k, v in existing.items() if k != 'result_sha256'}
            if (existing.get('result_sha256') != sha256(legacy.encoded(body)).hexdigest()
                    or existing['identity'] != identity
                    or existing['cell_digest'] != record_digest(journal, journal.records(require_complete=True))):
                raise ValueError('existing calibration result identity changed')
            print('RESULT_EXISTS', existing['status'], flush=True)
            return existing
        for reference in context.references:
            sid = reference['catalog']['source_id']
            if sid not in context.training_ids:
                continue
            for frame in context.frames:
                obs = frame['record']['obs_id']
                if obs not in learning or journal.read((sid, obs)) is not None:
                    continue
                saved = old.read((sid, obs, 'nearest'))
                row = cell_attempt(context, reference, frame, saved)
                # Journal reserves the envelope key, not scientific identity.
                row.pop('key', None)
                journal.write((sid, obs), row)
                print('CHECKPOINT', sid, obs, row['status'], flush=True)
        records = journal.records(require_complete=True)
        cells = [{**r['payload'], 'key': r['key']} for r in records if r['payload']['status'] == 'information_available']
        reasons = [];diagnostic = {};checks = []
        try:
            diagnostic, reasons, values = numerical_summary(cells)
            if not reasons:
                checks = shape_guard(context, cells, values)
                if any(c['status'] != 'shape_supported' for c in checks):
                    reasons.append('native_shape_guard')
        except Exception as exc:
            reasons.append('calibration_unavailable: '+type(exc).__name__+': '+str(exc))
        result = legacy.jsonable({
            'schema': 'shape-calibration-result-1', 'identity': identity,
            'at_utc': datetime.now(timezone.utc).isoformat(),
            'cell_digest': record_digest(journal, records), 'planned': len(keys),
            'counts': dict(Counter(r['payload']['status'] for r in records)),
            'status': 'candidate_rejected' if reasons else 'conditional_candidate',
            'reasons': reasons, 'diagnostic': diagnostic, 'shape_checks': checks,
            'new_point_fits': 0, 'random_draws': 0, 'heldout_outcomes': 0,
            'prospective_fields': 0, 'promotion': False,
            'qualification': 'one calibration-only fixed-tangent update on opened data; model/robust-weight/source-balance/systematic uncertainty and scientific improvement remain unverified',
        })
        result['result_sha256'] = sha256(legacy.encoded(result)).hexdigest()
        atomic(RESULT, result)
        print(json.dumps({k: result[k] for k in ('status', 'counts', 'reasons', 'diagnostic')}, indent=2), flush=True)
        return result


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
