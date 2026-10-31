"""Prespecified synthetic signal-control summaries; no fitting or RNG."""
from collections import Counter, defaultdict
from itertools import product
from numbers import Real

from astropy import units as u
import numpy as np
from scipy.stats import beta


SECTIONS = ('noiseless', 'noisy', 'null')
ARMS = ('baseline', 'corrected')
SCENES = ('isolated', 'modeled', 'omitted')
STATUSES = ('fit_completed', 'fit_failed', 'preparation_failed')
SECTION_COUNTS = {'noiseless': 192, 'noisy': 384, 'null': 64}
QUALIFICATION = ('Synthetic development controls conditional on declared geometry, masks, diagonal variance and truth models; '
    'exact binomial intervals are descriptive within fixed strata, with paired noise across conditions; not population certification, detection, '
    'false-positive rate, physical PSF validation or a basis to open the old assessment.')


def _number(value, name, *, nonnegative=False):
    if (isinstance(value, (bool, np.bool_, u.Quantity)) or not isinstance(value, Real)
            or not np.isfinite(value) or (nonnegative and value < 0)):
        raise ValueError(name+' must be finite numeric in declared units')
    try:
        converted = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(name+' is numerically unrepresentable') from exc
    if not np.isfinite(converted) or (value != 0 and converted == 0):
        raise ValueError(name+' is numerically unrepresentable')
    return converted


def _key(value):
    if not isinstance(value, (tuple, list)) or len(value) != 8:
        raise ValueError('key must identify section, geometry, truth, phase, scene, flux, draw and arm')
    key = tuple(value)
    if any(not isinstance(x, str) or not x.strip() for x in key):raise ValueError('key fields must be nonempty strings')
    section, _, _, _, scene, _, _, arm = key
    if section not in SECTIONS or arm not in ARMS or scene not in SCENES:
        raise ValueError('unknown section, scene or arm')
    if section == 'null' and scene != 'isolated':raise ValueError('null scene must be isolated')
    return key


def clopper_pearson(successes, planned):
    """Two-sided 95% exact interval for a fixed Bernoulli stratum."""
    if (type(successes) is not int or type(planned) is not int or planned < 1
            or not 0 <= successes <= planned):
        raise ValueError('invalid exact interval counts')
    lower = 0. if successes == 0 else float(beta.ppf(.025, successes, planned-successes+1))
    upper = 1. if successes == planned else float(beta.ppf(.975, successes+1, planned-successes))
    if not np.isfinite([lower, upper]).all():raise ValueError('unrepresentable exact interval')
    return [lower, upper]


def _completed(row, section, scene):
    support = row.get('numerical_support')
    if type(support) is not bool:raise ValueError('completed fit needs explicit numerical_support boolean')
    estimate = _number(row.get('target_flux_jy'), 'target flux Jy')
    truth = _number(row.get('true_flux_jy'), 'true flux Jy', nonnegative=True)
    if section == 'null':
        if truth != 0 or row.get('position_native_error') is not None or row.get('distance_to_companion_native') is not None:
            raise ValueError('null has zero flux and no target/companion position truth')
        return {'numerical_support': support, 'target_flux_jy': estimate, 'true_flux_jy': truth,
                'position_native_error': None, 'radial_error_native_px': None, 'flux_ratio': None,
                'distance_to_companion_native': None, 'identity': None}
    if truth <= 0:raise ValueError('source-present truth flux must be positive')
    p = row.get('position_native_error')
    if not isinstance(p, (tuple, list, np.ndarray)) or len(p) != 2:
        raise ValueError('position error needs two native-pixel coordinates')
    dx, dy = (_number(v, 'position error native pixels') for v in p)
    radial = float(np.hypot(dx, dy));ratio = estimate/truth
    if not np.isfinite(radial) or not np.isfinite(ratio):raise ValueError('unrepresentable error or flux ratio')
    distance = row.get('distance_to_companion_native')
    if scene == 'isolated':
        if distance is not None:raise ValueError('isolated scene has no companion truth')
    elif distance is not None:
        distance = _number(distance, 'companion distance native pixels', nonnegative=True)
    near_target = radial <= .5;near_companion = distance is not None and distance <= .5
    identity = ('ambiguous' if near_target and near_companion else 'target' if near_target else
                'companion' if near_companion else 'unknown' if scene != 'isolated' and distance is None else 'elsewhere')
    return {'numerical_support': support, 'target_flux_jy': estimate, 'true_flux_jy': truth,
            'position_native_error': [dx, dy], 'radial_error_native_px': radial, 'flux_ratio': ratio,
            'distance_to_companion_native': distance, 'identity': identity}


def _metrics(completed, *, noisy):
    if not completed:
        return {'n': 0, 'mean_dx_dy_native_px': None, 'mean_radial_native_px': None,
                'rms_radial_native_px': None, 'p90_radial_native_px': None, 'max_radial_native_px': None,
                'mean_flux_ratio': None, 'mean_flux_ratio_bias': None, 'flux_ratio_mcse': None,
                'identity_counts': {}}
    positions = np.asarray([r['position_native_error'] for r in completed]);radii = np.asarray([r['radial_error_native_px'] for r in completed])
    ratio = np.asarray([r['flux_ratio'] for r in completed]);n = len(completed)
    with np.errstate(over='ignore', invalid='ignore'):
        rms = float(np.linalg.norm(radii)/np.sqrt(n));mean = np.mean(positions, axis=0)
        mean_radius = float(np.mean(radii));mean_ratio = float(np.mean(ratio))
        mcse = float(np.std(ratio, ddof=1)/np.sqrt(n)) if noisy and n > 1 else None
    result = {'n': n, 'mean_dx_dy_native_px': mean.tolist(), 'mean_radial_native_px': mean_radius,
              'rms_radial_native_px': rms, 'p90_radial_native_px': float(np.quantile(radii, .9)),
              'max_radial_native_px': float(np.max(radii)), 'mean_flux_ratio': mean_ratio,
              'mean_flux_ratio_bias': mean_ratio-1., 'flux_ratio_mcse': mcse,
              'identity_counts': dict(Counter(r['identity'] for r in completed))}
    values = [*result['mean_dx_dy_native_px'], mean_radius, rms, result['p90_radial_native_px'],
              result['max_radial_native_px'], mean_ratio, result['mean_flux_ratio_bias']]
    if mcse is not None:values.append(mcse)
    if not np.isfinite(values).all():raise ValueError('summary metric is numerically unrepresentable')
    return result


def summarize_signal_control(records, expected_keys):
    """Summarize exactly the caller's 640 unique planned terminal envelopes.

    Each envelope is {'key': eight strings, 'payload': terminal payload}; completed
    payload fields are numeric native-pixel/Jy values with explicit names. The
    caller owns the frozen factorial identity and must pass all planned keys.
    """
    keys = [_key(key) for key in expected_keys]
    if len(keys) != 640 or len(set(keys)) != 640:raise ValueError('640 unique expected keys required')
    if Counter(k[0] for k in keys) != SECTION_COUNTS:raise ValueError('unexpected section denominators')
    geometries = sorted({k[1] for k in keys})
    if len(geometries) != 2:raise ValueError('two geometries required')
    required = {
        *(('noiseless', g, t, p, s, f, '0', a)
          for g, t, p, s, f, a in product(geometries, ('matched', 'gaussian'), ('0', '1', '2', '3'),
                                            ('isolated', 'modeled', 'omitted'), ('600', '1200'), ARMS)),
        *(('noisy', g, 'gaussian', p, s, '1200', str(d), a)
          for g, p, s, d, a in product(geometries, ('0', '3'), ('isolated', 'modeled', 'omitted'), range(16), ARMS)),
        *(('null', g, 'none', p, 'isolated', '0', str(d), a)
          for g, p, d, a in product(geometries, ('0', '3'), range(8), ARMS)),
    }
    if set(keys) != required:raise ValueError('expected keys differ from declared 640-cell factorial')
    expected = set(keys);indexed = {}
    for record in records:
        if not isinstance(record, dict) or 'key' not in record or 'payload' not in record:
            raise ValueError('record envelope required')
        key = _key(record['key']);payload = record['payload']
        if key not in expected or key in indexed:raise ValueError('unknown or duplicate record key')
        if not isinstance(payload, dict) or payload.get('status') not in STATUSES:
            raise ValueError('invalid terminal status')
        if payload['status'] == 'fit_completed':
            values = _completed(payload, key[0], key[4])
            if not np.isclose(values['true_flux_jy'], int(key[5])*1e-6, rtol=1e-12, atol=0.):
                raise ValueError('truth flux differs from planned microjansky key')
        else:
            if not isinstance(payload.get('error'), str) or not payload['error'].strip():raise ValueError('terminal failure requires reason')
            values = None
        indexed[key] = {'status': payload['status'], 'error': payload.get('error') if values is None else None, 'values': values}
    if set(indexed) != expected:raise ValueError('all expected terminal records required')
    # Every planned realization must have both model arms, regardless of failure.
    base_keys = {k[:-1] for k in keys}
    if any({(*base, arm) for arm in ARMS} - expected for base in base_keys):
        raise ValueError('expected paired arm is missing')
    groups = defaultdict(list)
    for key in keys:
        section, geometry, truth, phase, scene, flux, draw, arm = key
        groups[(section, geometry, truth, phase, scene, flux, arm)].append((key, indexed[key]))
    rows = [];noise_gates = [];null_rows = []
    for group in sorted(groups):
        section, geometry, truth, phase, scene, flux, arm = group;items = groups[group]
        label = {'section': section, 'geometry': geometry, 'truth': truth, 'phase': phase,
                 'scene': scene, 'flux': flux, 'arm': arm}
        counts = dict(Counter(item['status'] for _, item in items))
        complete = [item['values'] for _, item in items if item['values'] is not None]
        if section == 'null':
            if len(items) != 8:raise ValueError('null stratum must have eight planned realizations')
            positive = sum(r['numerical_support'] and r['target_flux_jy'] > 0 for r in complete)
            null_rows.append({**label, 'planned': len(items), 'status_counts': counts,
                'positive_supported': int(positive), 'positive_supported_interval_95': clopper_pearson(int(positive), len(items))})
            continue
        metrics = _metrics(complete, noisy=(section == 'noisy'))
        rows.append({**label, 'planned': len(items), 'status_counts': counts,
                     'numerical_supported': sum(r['numerical_support'] for r in complete),
                     'all_completed': metrics,
                     'supported_completed': _metrics([r for r in complete if r['numerical_support']], noisy=(section == 'noisy'))})
        if section == 'noisy':
            if len(items) != 16:raise ValueError('noisy stratum must have sixteen planned realizations')
            if scene in ('isolated', 'modeled'):
                success = sum(r['numerical_support'] and r['target_flux_jy'] > 0 and r['radial_error_native_px'] <= .5
                              and .5 <= r['flux_ratio'] <= 1.5 for r in complete)
                noise_gates.append({**label, 'planned': 16, 'success': int(success),
                    'exact_interval_95': clopper_pearson(int(success), 16),
                    'observed_sample_gate_passed': success >= 15})
    clean = [k for k in keys if k[0] == 'noiseless' and k[4] in ('isolated', 'modeled')]
    if not clean or not noise_gates or not null_rows:raise ValueError('required clean/noisy/null strata absent')
    noisel_good = []
    for key in clean:
        r = indexed[key]['values']
        ok = bool(r is not None and r['numerical_support'] and r['radial_error_native_px'] <= .1 and .9 <= r['flux_ratio'] <= 1.1)
        noisel_good.append({'key': list(key), 'passed': ok})
    paired = [];guard_rows = []
    for base in sorted(base_keys):
        left = indexed[(*base, 'baseline')];right = indexed[(*base, 'corrected')]
        a, b = left['values'], right['values'];available = a is not None and b is not None
        if available and a['true_flux_jy'] != b['true_flux_jy']:raise ValueError('paired truth flux differs')
        p = {'key_without_arm': list(base), 'baseline_status': left['status'], 'corrected_status': right['status'],
             'both_completed': available, 'delta_position_native_px': None, 'delta_flux_ratio': None,
             'delta_radial_native_px': None, 'delta_abs_flux_ratio_error': None,
             'new_numerical_refusal': bool(a is not None and a['numerical_support'] and (b is None or not b['numerical_support']))}
        if available and base[0] != 'null':
            p['delta_position_native_px'] = (np.asarray(b['position_native_error'])-a['position_native_error']).tolist()
            p['delta_flux_ratio'] = b['flux_ratio']-a['flux_ratio']
            p['delta_radial_native_px'] = b['radial_error_native_px']-a['radial_error_native_px']
            p['delta_abs_flux_ratio_error'] = abs(b['flux_ratio']-1.)-abs(a['flux_ratio']-1.)
            if not np.isfinite([*p['delta_position_native_px'], p['delta_flux_ratio'],
                                p['delta_radial_native_px'], p['delta_abs_flux_ratio_error']]).all():
                raise ValueError('paired comparison is numerically unrepresentable')
        paired.append(p)
        if base[0] == 'noiseless' and base[4] in ('isolated', 'modeled'):
            ok = bool(available and not p['new_numerical_refusal'] and p['delta_radial_native_px'] <= .02
                      and p['delta_abs_flux_ratio_error'] <= .02)
            guard_rows.append({'key_without_arm': list(base), 'passed': ok})
    pair_groups = defaultdict(list)
    for pair in paired:
        key = pair['key_without_arm']
        pair_groups[tuple(key[:6])].append(pair)  # draw is excluded; arm is already paired
    paired_strata = []
    for group, pairs in sorted(pair_groups.items()):
        valid = [p for p in pairs if p['both_completed']]
        position = [p['delta_radial_native_px'] for p in valid if p['delta_radial_native_px'] is not None]
        flux = [p['delta_abs_flux_ratio_error'] for p in valid if p['delta_abs_flux_ratio_error'] is not None]
        vectors = [p['delta_position_native_px'] for p in valid if p['delta_position_native_px'] is not None]
        ratios = [p['delta_flux_ratio'] for p in valid if p['delta_flux_ratio'] is not None]
        mean_vector = np.mean(vectors, axis=0).tolist() if vectors else None
        mean_ratio = float(np.mean(ratios)) if ratios else None
        mean_position = float(np.mean(position)) if position else None
        mean_flux = float(np.mean(flux)) if flux else None
        numeric = ([*mean_vector] if mean_vector is not None else []) + [x for x in (mean_ratio, mean_position, mean_flux) if x is not None]
        if not np.isfinite(numeric).all():raise ValueError('paired stratum is numerically unrepresentable')
        paired_strata.append({'section': group[0], 'geometry': group[1], 'truth': group[2], 'phase': group[3],
            'scene': group[4], 'flux': group[5], 'planned_pairs': len(pairs), 'both_completed': len(valid),
            'missing_pairs': len(pairs)-len(valid),
            'mean_delta_position_native_px': mean_vector, 'mean_delta_flux_ratio': mean_ratio,
            'mean_delta_radial_native_px': mean_position, 'mean_delta_abs_flux_ratio_error': mean_flux})
    per_record = [{'key': list(k), **indexed[k]} for k in keys]
    return {'schema': 'signal-control-metrics-1', 'planned': 640,
        'section_counts': dict(Counter(k[0] for k in keys)),
        'status_counts': dict(Counter(indexed[k]['status'] for k in keys)),
        'records': per_record, 'strata': rows, 'null_strata': null_rows,
        'noiseless_clean_gate': {'planned': len(clean), 'passed_count': sum(r['passed'] for r in noisel_good),
                                 'passed': all(r['passed'] for r in noisel_good), 'rows': noisel_good},
        'noisy_clean_gates': noise_gates, 'noisy_clean_all_gates_passed': all(r['observed_sample_gate_passed'] for r in noise_gates),
        'paired': {'planned': len(paired), 'both_completed': sum(r['both_completed'] for r in paired),
                   'missing': sum(not r['both_completed'] for r in paired), 'strata': paired_strata, 'rows': paired},
        'noiseless_preservation_guard': {'planned_pairs': len(guard_rows), 'passed_count': sum(r['passed'] for r in guard_rows),
                                         'passed': bool(guard_rows) and all(r['passed'] for r in guard_rows), 'rows': guard_rows},
        'old_assessment_blocked': True, 'promotion': False, 'qualification': QUALIFICATION}
