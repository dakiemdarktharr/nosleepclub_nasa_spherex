"""Fixed opened geometry for a separately calibrated source-presence score.

The scorer uses original observed VARIANCE, never the oracle source-error
output of the synthetic scene generator. No data or random numbers at import.
"""
from hashlib import sha256
from numbers import Integral

import astropy.units as u
import numpy as np

from . import run_neighbor_intervention as prior
from . import run_wise_linked_study as legacy
from . import neighbor_intervention_inputs as semantic
from . import independent_scene_control as control
from . import source_presence_score as presence


I = u.MJy / u.sr
VARIANTS = ('nearest', 'bilinear')
SCENARIOS = tuple({'id': background + '_null', 'background': background, 'flux_jy': 0.}
                  for background in ('plane', 'quadratic')) + tuple(
    {'id': background + '_' + str(int(flux * 1e6)) + 'uJy', 'background': background, 'flux_jy': flux}
    for background in ('plane', 'quadratic') for flux in (.0003, .0006))
RULES = {'version': '0.10.0-source-presence.1', 'variants': list(VARIANTS),
         'scope': 'one already opened strict WISE geometry, four native frames, two per season',
         'frame_epoch_order': ['2025-11', '2025-11', '2026-04', '2026-04'],
         'grid': {'center': [31.5, 31.5], 'half_width_sky_px': 2.5, 'step_sky_px': .25,
                  'shape': [21, 21], 'order': 'y outer, x inner'},
         'nuisance': 'same full-rank free signed infrared neighbors and plane, no rank truncation',
         'score_error': 'original observed VARIANCE only, excludes generator oracle source variance',
         'statistic': 'max_variant min_season max_grid sum_two_frames positive_part(signed_score)^2',
         'search_qualification': 'fixed grid detection score, not a centroid or motion measurement',
         'scenarios': list(SCENARIOS), 'draws_per_case': 999,
         'seed_prefix': 20261101,
         'rng': 'PCG64 SeedSequence([prefix, stage(0cal/1val), scenario_index, draw, epoch_index, frame_index_within_epoch])',
         'truth_before_sky_px': [31.73, 31.31], 'truth_displacement_sky_px': [.55, .08],
         'target_sigma_xy_native': [.55, .70], 'neighbor_sigma_xy_native': [.70, .60],
         'neighbor_flux_jy': '0.00015/(1+index) in frozen retained order',
         'background_plane_mjysr': [.04, .015, -.01],
         'background_quadratic_mjysr': [.025, .020, -.015],
         'noise': 'independent empirical-scale Gaussian plus ideal target/neighbor Poisson OLS ramp; real bound gain',
         'calibration': '999 null draws per background; threshold maximum across both complete cases; accept strictly greater',
         'seal': 'learned threshold and complete calibration journal digest committed before validation',
         'validation_null_gate': 'per-case one-sided 97.5% exact upper <=0.01; failures count as false accepts',
         'validation_power_gate': '600uJy per-background one-sided 97.5% exact lower >=0.80; failures count as misses',
         '300uJy': 'report full denominator, no high-flux-domain gate',
         'all_attempts': '1998 calibration null +1998 validation null +3996 validation positive =7992',
         'qualifications': [
             'one opened geometry; independent RNG streams are not independent sky fields',
             'Gaussian PSF truth deliberately differs from fitter; not calibrated telescope PSF truth',
             'original variance may include real-source shot noise; ideal added source noise is not a detector budget',
             'threshold is conditional on these backgrounds, masks, nuisance/PSF/noise assumptions and fixed search',
             'no covariance calibration, real-sky false-alarm rate, blind-search power or scientific promotion'],
         'promotion': False}


def grid():
    center = np.asarray(RULES['grid']['center'])
    axis = np.linspace(-2.5, 2.5, 21)
    return np.asarray([center + [x, y] for y in axis for x in axis])


def validate_prepared_pair(original, item):
    if original['obs_id'] != item['obs_id']:
        raise ValueError('semantic exposure identity/order changed')
    for name in ('data', 'error'):
        if not np.array_equal(original[name], item[name]):
            raise ValueError('semantic pixel values/error changed')
    for name in ('x', 'y'):
        if not np.array_equal(original['sample'][name], item['metadata'][name]):
            raise ValueError('semantic native pixel identity/order changed')
    if original['sample']['neighbour_ids'] != item['neighbor_ids']:
        raise ValueError('semantic neighbor identity/order changed')


def validate_epoch_order(geometries):
    if len(geometries) != 4 or [g['frame']['record']['epoch'] for g in geometries] != RULES['frame_epoch_order']:
        raise ValueError('expected two before frames followed by two after frames')


def build_geometry():
    frames, _ = prior.inputs.read_verified_frames()
    groups, prepared, errors = prior.prepare_configuration(frames, 'strict')
    if any(errors) or [len(group) for group in groups] != [2, 2]:
        raise ValueError('the frozen two-before/two-after geometry is required')
    gain = prior.load_gain();geometries = [];items = [];operators = []
    positions = grid();anchor = RULES['grid']['center']
    for epoch in range(2):
        nearest = semantic.prepare_semantic(prepared[epoch], anchor, background_order=1, epsf_kind='nearest')
        planned = [f['record']['obs_id'] for f in groups[epoch]]
        if ([p['obs_id'] for p in prepared[epoch]] != planned
                or [p['obs_id'] for p in nearest] != planned):
            raise ValueError('strict exposure identities/order changed')
        for old, item in zip(prepared[epoch], nearest):
            validate_prepared_pair(old, item)
        geometries.extend(prior.control_geometry(prepared[epoch], nearest, gain))
        items.extend(nearest)
        for item_index in range(2):
            bank = []
            for variant in VARIANTS:
                item = semantic.prepare_semantic([prepared[epoch][item_index]], anchor,
                                                 background_order=1, epsf_kind=variant)[0]
                validate_prepared_pair(prepared[epoch][item_index], item)
                templates = u.Quantity([item['renderer'](p).to_value(I / u.Jy) for p in positions], I / u.Jy)
                nuisance = [item['background_design'][:, j] * I for j in range(3)]
                nuisance += [item['neighbor_design'][:, j] * I / u.Jy for j in range(len(item['neighbor_ids']))]
                operator = presence.prepare_operator(templates, item['error'] * I, nuisance,
                    provenance=item['obs_id'] + '|' + variant + '|fixed 441-template grid')
                bank.append({'operator': operator, 'metadata': item['metadata'],
                             'background_design': item['background_design'],
                             'neighbor_design_per_jy': item['neighbor_design'],
                             'neighbor_ids': item['neighbor_ids'],
                             'templates_sha256': sha256(legacy.encoded(templates.value)).hexdigest()})
            operators.append(bank)
    if len({g['obs_id'] for g in geometries}) != 4:
        raise ValueError('presence geometry must contain four distinct exposures')
    validate_epoch_order(geometries)
    scenarios = [truth_scenario(geometries, s) for s in SCENARIOS]
    snapshot = {'rules': RULES, 'grid_sky_px': positions,
                'frames': [{'obs_id': geo['obs_id'], 'x': geo['x'], 'y': geo['y'],
                            'pixel_omega_sr': geo['omega'].to_value(u.sr),
                            'gain_mjysr_per_electron_rate': geo['gain'].to_value(control.GAIN),
                            'observed_error_mjysr': geo['error'],
                            'variants': [{'variant': VARIANTS[j], 'metadata': info['metadata'],
                                          'background_design': info['background_design'],
                                          'neighbor_design_per_jy': info['neighbor_design_per_jy'],
                                          'neighbor_ids': info['neighbor_ids'],
                                          'templates_sha256': info['templates_sha256'],
                                          'projected_directions': info['operator']._directions,
                                          'projected_norm_per_jy': info['operator'].projected_template_norm.to_value(1/u.Jy),
                                          'information_fraction': info['operator'].information_fraction,
                                          'nuisance_rank': info['operator'].nuisance_rank,
                                          'nuisance_condition': info['operator'].nuisance_condition}
                                         for j, info in enumerate(bank)]}
                           for geo, bank in zip(geometries, operators)],
                'truth_scenarios': scenarios,
                'observed_data_sha256': sha256(legacy.encoded([item['data'] for item in items])).hexdigest()}
    return {'geometries': geometries, 'operators': operators, 'items': items,
            'scenarios': scenarios, 'snapshot': legacy.jsonable(snapshot)}


def truth_scenario(geometries, scenario):
    records = []
    for frame_index, geo in enumerate(geometries):
        epoch = frame_index // 2
        truth = np.asarray(RULES['truth_before_sky_px']) + epoch * np.asarray(RULES['truth_displacement_sky_px'])
        sources = []
        if scenario['flux_jy'] > 0:
            sources.append({'native_xy': prior.inputs.native_position(geo['frame'], truth),
                            'flux': scenario['flux_jy'] * u.Jy, 'sigma_xy': RULES['target_sigma_xy_native']})
        sources.extend({'native_xy': n['native_xy'], 'flux': .00015 / (1+i) * u.Jy,
                        'sigma_xy': RULES['neighbor_sigma_xy_native']}
                       for i, n in enumerate(geo['neighbors']))
        expected = control.expected_scene(sources, geo['x'], geo['y'], geo['omega'])
        b = geo['background'];background = b @ np.asarray(RULES['background_plane_mjysr'])
        if scenario['background'] == 'quadratic':
            background += np.column_stack((b[:, 1]**2, b[:, 1]*b[:, 2], b[:, 2]**2)) @ np.asarray(RULES['background_quadratic_mjysr'])
        records.append({'obs_id': geo['obs_id'], 'expected_source_mjysr': expected['expected_source'].value,
                        'background_mjysr': background, 'per_source': expected['per_source']})
    return legacy.jsonable({'scenario': scenario, 'frames': records})


def score_data(context, data):
    if len(data) != 4:
        raise ValueError('four frame vectors required')
    scores = np.asarray([[context['operators'][i][v]['operator'].score(data[i] * I)
                          for i in range(4)] for v in range(2)])
    summary = presence.paired_presence_statistic(scores)
    positive = np.maximum(scores, 0.)**2
    winners = []
    for variant in range(2):
        for epoch in range(2):
            season = positive[variant, epoch*2:epoch*2+2].sum(axis=0)
            winner = int(np.argmax(season))
            winners.append({'variant': VARIANTS[variant], 'epoch': ['before', 'after'][epoch],
                            'grid_index': winner, 'grid_sky_px': grid()[winner].tolist(),
                            'signed_frame_scores': scores[variant, epoch*2:epoch*2+2, winner].tolist()})
    return legacy.jsonable({**summary, 'winners': winners})


def realize(context, stage, scenario_index, draw):
    if stage not in ('calibration', 'validation'):
        raise ValueError('unknown stage')
    if (isinstance(scenario_index, bool) or not isinstance(scenario_index, Integral)
            or scenario_index not in range(len(SCENARIOS))
            or isinstance(draw, bool) or not isinstance(draw, Integral) or draw not in range(RULES['draws_per_case'])):
        raise ValueError('invalid scenario index or draw')
    if len(context['geometries']) != 4 or len(context['scenarios']) != len(SCENARIOS):
        raise ValueError('exactly four ordered geometries and all scenarios required')
    validate_epoch_order(context['geometries'])
    expected_frames = context['scenarios'][scenario_index]['frames']
    identities = [g['obs_id'] for g in context['geometries']]
    if len(set(identities)) != 4 or [f['obs_id'] for f in expected_frames] != identities:
        raise ValueError('scenario frame identity/order mismatch')
    scenario = SCENARIOS[scenario_index]
    if stage == 'calibration' and scenario['flux_jy'] != 0:
        raise ValueError('calibration is null-only')
    stage_index = 0 if stage == 'calibration' else 1
    data = [];records = []
    for frame_index, (geo, expected) in enumerate(zip(context['geometries'], expected_frames)):
        seed = [RULES['seed_prefix'], stage_index, scenario_index, draw, frame_index//2, frame_index%2]
        rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed)))
        realization = control.draw_scene(np.asarray(expected['expected_source_mjysr']) * I,
            np.asarray(expected['background_mjysr']) * I, geo['error'] * I, geo['gain'],
            geo['frame']['image_header'], rng,
            gain_provenance={'source': prior.gain_paths.URL, 'sha256': prior.gain_binding.GAIN_SHA256,
                             'orientation': 'conditional public R6 binding'},
            source_provenance={'source': 'fixed independent Gaussian-family conditional presence scene',
                               'scenario': scenario['id'], 'seed': seed})
        # Oracle realization['error'] is deliberately NOT passed to any scorer.
        values = realization['data'].to_value(I);data.append(values)
        records.append({'obs_id': geo['obs_id'], 'seed': seed, 'data_mjysr': values.tolist(),
                        'provenance': realization['provenance']})
    return data, {'frames': records, 'realization_sha256': sha256(legacy.encoded(data)).hexdigest()}
