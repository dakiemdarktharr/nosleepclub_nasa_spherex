"""Frozen post-hoc profile diagnosis on two previously opened calibration frames."""
import argparse
from collections import Counter
from functools import lru_cache
import json
from numbers import Integral
import os
import time

if __name__ == '__main__':
    for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                  'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[_name] = '1'

import numpy as np

from . import run_shape_point_study as points
from . import run_shape_calibration as calibration
from . import run_reference_star_study as baseline
from . import frozen_experiment as frozen
from .experiment_journal import Journal
from .science_jobs import locked, atomic
from .shape_native_inputs import prepare_shape_sample
from .moment_preserving_epsf import physical_parameters
from .profile_landscape import ResidualSampler, probe, grid


ROOT = frozen.ROOT
DESIGN = ROOT/'web/data/profile-landscape/design.json'
OUTPUT = ROOT/'data/raw/benchmark/profile-landscape'
POINT_COMMIT = '31d07ab777628aecc90af3b244e882e2e6d95b93'
FRAMES = ('2025W46_2A_0214_2', '2025W46_2A_0214_3')
FOCUS = ('5756942110218608640', '5756958431094222592')
ARMS = ('baseline', 'corrected')
STATUSES = ('profile_completed', 'profile_failed', 'preparation_failed')
RULES = {
    'version': '0.10.0-profile-landscape.1',
    'scope': 'post-hoc numerical diagnosis; no accuracy, detection or model promotion',
    'allocation': 'all 14 original training IDs by two already opened November calibration frames by 2 PSF arms by 2 fixed-weight arms',
    'planned_cells': 112, 'frames': list(FRAMES), 'psf_arms': list(ARMS), 'weight_arms': list(ARMS),
    'focus_sources': list(FOCUS),
    'focus_disclosure': 'two sources selected after their corrected calibration gate failed; local maps are diagnostic, not an unbiased effect estimate',
    'point_protocol_commit': POINT_COMMIT,
    'position_optimization': False, 'weight_update': False, 'new_psf_estimation': False,
    'linear_profile': 'unchanged signed-Jy target and neighbors, planar background; profile nuisance coefficients at fixed positions only',
    'weights': 'cross the two saved final Huber weight vectors without re-estimating either',
    'search_bound_common_px': 2.5, 'global_grid_nodes_per_axis': 51,
    'local_grid_nodes_per_axis': 21, 'local_radius_common_px': .2,
    'local_centers': 'every distinct saved near-best candidate from either old or corrected fit, only for the two disclosed focus sources',
    'probes': 'saved point and every successful final-start position from BOTH fit families; exact-position deduplication retains all origins',
    'finite_difference_steps_common_px': [.004, .002, .001],
    'residual_jacobian_scaled_rank_relative_tolerance': 1e-10,
    'cost': 'sum of squared fixed-weight standardized residuals, not half-cost',
    'sampled_delta_costs': [.1, 1., 2.3, 5.991], 'connectivity': [4, 8],
    'topology_qualification': 'relative to each sampled grid minimum; missing nodes and edges retained; neither connected components nor these levels certify basins or confidence',
    'saved_objective_replay_rtol': 1e-10, 'saved_objective_replay_atol': 1e-10,
    'derivative_qualification': 'central cost and residual derivatives at three fixed steps; full cost Hessian and Gauss-Newton matrix kept separately; no stationarity pass threshold',
    'template_cache_max_entries_per_psf_cell': 8192, 'shards': 2,
    'all_failures_retained': True, 'source_removal': False,
    'assessment_cells_opened': 0, 'prospective_fields_opened': 0,
    'random_realizations': 0, 'promotion': False,
}
SOURCES = (*points.SOURCES,
    'scripts/profile_landscape.py', 'scripts/run_profile_landscape_study.py',
    'tests/test_profile_landscape.py', 'tests/test_profile_landscape_study.py',
    'docs/PROFILE_LANDSCAPE_PROTOCOL.md',
    'web/data/shape-point-check/design.json', 'web/data/shape-point-check/calibration-gate.json',
    'web/data/shape-point-check/overview.json', 'web/data/shape-point-check/independent-audit.json',
    'web/data/shape-point-check/records.json.gz',
    'web/data/shape-correction/coefficient-seal.json',
)


def assert_assessment_unopened():
    path = points.OUTPUT/'assessment'
    if path.exists() or path.is_symlink(): raise ValueError('assessment must remain unopened')


def expected_keys(context):
    sources = sorted(context.training_ids)
    available = {f['record']['obs_id'] for f in context.frames}
    learning = set(calibration.planned_cells(context)[1])
    if len(sources) != 14 or len(set(sources)) != 14 or not set(FRAMES) <= available & learning:
        raise ValueError('fixed training/frame allocation changed')
    keys = [(sid, obs, psf, weight) for sid in sources for obs in FRAMES for psf in ARMS for weight in ARMS]
    if len(keys) != 112 or len(set(keys)) != 112: raise ValueError('profile denominator changed')
    return keys


def open_inputs():
    assert_assessment_unopened()
    frozen.verify(points.DESIGN, points.RULES, points.SOURCES, POINT_COMMIT)
    context, old, old_digest = calibration.open_baseline()
    point = points.open_journal(POINT_COMMIT, 'calibration', context)
    records = point.records(require_complete=True)
    point_digest = calibration.record_digest(point, records)
    gate = json.loads(points.GATE.read_text(encoding='utf-8'))
    if (gate.get('assessment_allowed') is not False or gate.get('point_protocol_commit') != POINT_COMMIT
            or gate.get('calibration_point_digest') != point_digest
            or {tuple(f['key']) for f in gate.get('failures', [])} != {(sid, FRAMES[1]) for sid in FOCUS}):
        raise ValueError('original failing gate or calibration journal differs')
    seal, values = points.read_coefficients()
    metadata = {'baseline_journal_digest': old_digest, 'point_journal_digest': point_digest,
        'coefficient_seal_sha256': calibration.legacy.lab.digest(points.COEFFICIENTS),
        'expected_keys': expected_keys(context),
        'qualification': 'old and corrected calibration outcomes were already viewed; no new profile grids or derivative probes before this design'}
    if gate['coefficient_seal_sha256'] != metadata['coefficient_seal_sha256'] or gate['shape_calibration_cell_digest'] != seal['cell_digest']:
        raise ValueError('gate coefficient binding differs')
    return context, old, point, values, metadata


def create_design():
    *_, metadata = open_inputs()
    return frozen.create(DESIGN, RULES, SOURCES, metadata=metadata)


def make_problem(item):
    sample = baseline.semantic.model_samples([item])[0]
    original = sample['renderer']
    @lru_cache(maxsize=RULES['template_cache_max_entries_per_psf_cell'])
    def rendered(x, y): return original(np.asarray([x, y]))
    sample = {**sample, 'renderer': lambda p: rendered(float(p[0]), float(p[1]))}
    return baseline.model.NeighborEpochProblem([sample], data_unit='MJy/sr', nonnegative_neighbors=False)


def candidate_positions(rows):
    grouped = {}
    for arm in ARMS:
        fit = rows[arm]['fit']
        entries = [('point', fit['position'])]
        entries += [('final_start_'+str(i), r['position']) for i, r in enumerate(fit['final_mode_audit']['starts']) if r['success']]
        for origin, position in entries:
            xy = tuple(float(v) for v in position)
            if len(xy) != 2 or not np.isfinite(xy).all(): raise ValueError('saved position invalid')
            grouped.setdefault(xy, []).append({'fit_arm': arm, 'origin': origin})
    return [{'position': list(k), 'origins': v} for k, v in grouped.items()]


def local_centers(rows):
    positions = {}
    for arm in ARMS:
        for i, mode in enumerate(rows[arm]['fit']['final_mode_audit']['near_best_modes']):
            position = tuple(float(x) for x in mode['position'])
            if len(position) != 2 or not np.isfinite(position).all(): raise ValueError('saved local center invalid')
            positions.setdefault(position, []).append({'fit_arm': arm, 'near_best_index': i})
    return [{'position': list(p), 'origins': origins} for p, origins in positions.items()]


def validate_native(item, metadata, rows):
    for arm in ARMS:
        row = rows[arm]
        if calibration.legacy.jsonable(metadata) != row['metadata']: raise ValueError('native metadata changed')
        sample = row['samples'][0]
        if (item['metadata']['x'] != sample['x'] or item['metadata']['y'] != sample['y']
                or list(item['neighbor_ids']) != sample['neighbor_ids']):
            raise ValueError('native mask or neighbor identity differs')
        for name, saved in (('data', sample['data_mjysr']), ('error', sample['error_mjysr']),
                            ('background_design', sample['background_design'])):
            a = np.asarray(item[name]); b = np.asarray(saved)
            if a.shape != b.shape or not np.allclose(a, b, rtol=1e-12, atol=0.):
                raise ValueError('native '+name+' differs')


def diagnose(problem, anchor, rows, source_id, psf_arm, weight_arm):
    fit = rows[weight_arm]['fit']
    if len(fit['frames']) != 1 or fit['frames'][0]['obs_id'] != problem.frames[0]['obs_id']:
        raise ValueError('saved weight exposure differs')
    problem.set_weights([fit['frames'][0]['weights']])
    sampler = ResidualSampler(lambda p: problem.profile(p)['weighted_residual'], anchor, RULES['search_bound_common_px'])
    replay = []
    if psf_arm == weight_arm:
        saved = rows[psf_arm]['fit']
        values = [('point', saved['position'], saved['chi2_weighted'])]
        values += [('final_start_'+str(i), r['position'], r['chi2'])
                   for i, r in enumerate(saved['final_mode_audit']['starts']) if r['success']]
        for origin, position, expected in values:
            result = sampler.at(position)
            if 'cost' not in result or not np.isclose(result['cost'], expected,
                    rtol=RULES['saved_objective_replay_rtol'], atol=RULES['saved_objective_replay_atol']):
                raise ValueError('own-PSF/own-weight saved objective replay failed')
            replay.append({'origin': origin, 'position': position, 'saved_cost': expected,
                           'replayed_cost': result['cost'], 'absolute_difference': abs(result['cost']-expected)})
    bound = RULES['search_bound_common_px']; count = RULES['global_grid_nodes_per_axis']
    global_map = grid(sampler, anchor[0]+np.linspace(-bound, bound, count),
        anchor[1]+np.linspace(-bound, bound, count), RULES['sampled_delta_costs'])
    probes = [{**entry, 'diagnostic': probe(sampler, entry['position'], RULES['finite_difference_steps_common_px'])}
              for entry in candidate_positions(rows)]
    local_maps = []
    if source_id in FOCUS:
        radius = RULES['local_radius_common_px']; count = RULES['local_grid_nodes_per_axis']
        for entry in local_centers(rows):
            xy = np.asarray(entry['position'])
            local_maps.append({**entry, 'grid': grid(sampler, xy[0]+np.linspace(-radius, radius, count),
                xy[1]+np.linspace(-radius, radius, count), RULES['sampled_delta_costs'])})
    return calibration.legacy.jsonable({'saved_objective_replay': replay,
        'global_grid': global_map, 'probes': probes, 'local_grids': local_maps})


def unavailable_rows(old_record, point_record):
    rows = {'baseline': old_record['payload'], 'corrected': point_record['payload']}
    failures = {arm: row['status'] for arm, row in rows.items() if row['status'] != 'fit_completed'}
    return rows, failures


def run(commit, shard):
    if isinstance(shard, bool) or not isinstance(shard, Integral) or shard not in range(RULES['shards']):
        raise ValueError('shard must be 0 or 1')
    design = frozen.verify(DESIGN, RULES, SOURCES, commit)
    context, old, point, values, metadata = open_inputs()
    if design['metadata'] != calibration.legacy.jsonable(metadata): raise ValueError('profile input journal identity changed')
    journal = Journal(OUTPUT/'cells', frozen.identity(DESIGN, commit, frozen.runtime(), 'fixed-profile-landscape'),
                      expected_keys(context), STATUSES)
    sources = sorted(context.training_ids)[shard::RULES['shards']]
    references = {r['catalog']['source_id']: r for r in context.references}
    frames = {f['record']['obs_id']: f for f in context.frames}
    workers = OUTPUT/'workers'; workers.mkdir(exist_ok=True)
    with locked(workers, 'shard-'+str(shard)+'.lock'):
        for sid in sources:
            for obs in FRAMES:
                key = (sid, obs)
                saved = old.read((*key, 'nearest')); corrected = point.read(key)
                if saved is None or corrected is None or corrected['payload']['baseline_checksum'] != saved['checksum']:
                    raise ValueError('profile baseline/point checksum mismatch')
                rows, failures = unavailable_rows(saved, corrected)
                prepared = None; native_meta = None; preparation_error = None
                if not failures:
                    try: prepared, native_meta = baseline.inputs.prepare_cell(context, references[sid], frames[obs])
                    except Exception as exc: preparation_error = type(exc).__name__+': '+str(exc)
                for psf_arm in ARMS:
                    pending = [(sid, obs, psf_arm, w) for w in ARMS if journal.read((sid, obs, psf_arm, w)) is None]
                    if not pending: continue
                    problem = None; error = preparation_error
                    if not failures and error is None:
                        try:
                            anchor = np.asarray(native_meta['anchor_sky_px'])
                            item = (baseline.inputs.prepare_variant(prepared, anchor, 'nearest') if psf_arm == 'baseline'
                                    else prepare_shape_sample(prepared, anchor, physical_parameters(values)))
                            validate_native(item, native_meta, rows); problem = make_problem(item)
                        except Exception as exc: error = type(exc).__name__+': '+str(exc)
                    for full_key in pending:
                        started = time.monotonic(); weight_arm = full_key[-1]
                        row = {'source_id': sid, 'obs_id': obs, 'psf_arm': psf_arm, 'weight_arm': weight_arm,
                            'baseline_checksum': saved['checksum'], 'point_checksum': corrected['checksum'],
                            'input_statuses': {arm: r['status'] for arm, r in rows.items()}}
                        if failures or error:
                            row.update(status='preparation_failed', error=error or 'saved fit unavailable', reused_unavailable=failures)
                        else:
                            try: row.update(status='profile_completed', anchor_common_px=anchor.tolist(),
                                diagnostics=diagnose(problem, anchor, rows, sid, psf_arm, weight_arm))
                            except Exception as exc: row.update(status='profile_failed', error=type(exc).__name__+': '+str(exc))
                        row['elapsed_seconds'] = time.monotonic()-started
                        journal.write(full_key, row)
                        print('PROFILE', *full_key, row['status'], round(row['elapsed_seconds'], 2), flush=True)
    assert_assessment_unopened()


def summarize(commit):
    design = frozen.verify(DESIGN, RULES, SOURCES, commit)
    context, _, _, _, metadata = open_inputs()
    if design['metadata'] != calibration.legacy.jsonable(metadata): raise ValueError('profile summary identity changed')
    journal = Journal(OUTPUT/'cells', frozen.identity(DESIGN, commit, frozen.runtime(), 'fixed-profile-landscape'),
                      expected_keys(context), STATUSES)
    records = journal.records(require_complete=True)
    summary = {'schema': 'profile-landscape-summary-1', 'protocol_commit': commit,
        'design_sha256': calibration.legacy.lab.digest(DESIGN),
        'cell_digest': calibration.record_digest(journal, records),
        'planned': len(records), 'counts': dict(Counter(r['payload']['status'] for r in records)),
        'qualification': RULES['scope'], 'assessment_opened': False, 'promotion': False}
    path = OUTPUT/'summary.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != summary: raise ValueError('summary already exists with different contents')
    else: atomic(path, summary)
    print(json.dumps(summary, indent=2)); return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', action='store_true'); parser.add_argument('--commit')
    parser.add_argument('--shard', type=int); parser.add_argument('--summary', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        if args.commit or args.shard is not None or args.summary: parser.error('freeze must be separate')
        create_design(); print('FROZEN', calibration.legacy.relative(DESIGN))
    elif args.summary:
        if not args.commit or args.shard is not None: parser.error('summary needs only commit')
        summarize(args.commit)
    else:
        if not args.commit or args.shard is None: parser.error('run requires commit and shard')
        run(args.commit, args.shard)
