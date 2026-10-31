"""Independent conditional replay of frozen synthetic controls; no optimizers."""
from collections import Counter, defaultdict
from hashlib import sha256
from functools import lru_cache
from itertools import product
import json
import os

if __name__ == '__main__':
    for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                  'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[_name] = '1'

import astropy.units as u
import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.stats import binomtest

from . import run_signal_control_study as study
from .experiment_journal import Journal
from .science_jobs import encode, atomic

COMMIT = '9894074fdacbba908b8816d3dbcac1df901731f1'
AUDIT_DIR = study.ROOT/'data/raw/benchmark/signal-controls-audit'
RECEIPT = AUDIT_DIR/'audit-receipt.json'
FILES = ('scripts/audit_signal_controls.py', 'tests/test_signal_control_audit.py',
         'docs/SIGNAL_CONTROL_AUDIT.md')


def close(actual, expected, label, *, atol=1e-9, rtol=1e-9):
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError(label+' shape or finiteness differs')
    if not np.allclose(a, b, atol=atol, rtol=rtol):
        raise ValueError(label+' differs, max absolute difference '+str(float(np.max(np.abs(a-b)))))
    return float(np.max(np.abs(a-b))) if a.size else 0.


def gaussian64(x, y, position):
    """Independent expanded covariance Gaussian integral on native pixels."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    position = np.asarray(position, float)
    if x.ndim != 1 or y.shape != x.shape or position.shape != (2,) or not np.isfinite(position).all():
        raise ValueError('invalid Gaussian geometry')
    nodes, weights = leggauss(64)
    dx = x[:, None, None] + nodes[None, :, None]/2 - position[0]
    dy = y[:, None, None] + nodes[None, None, :]/2 - position[1]
    c, s = np.cos(np.deg2rad(25.)), np.sin(np.deg2rad(25.))
    a, b = .55**2, .70**2
    vxx, vyy, vxy = c*c*a+s*s*b, s*s*a+c*c*b, c*s*(a-b)
    det = vxx*vyy-vxy*vxy
    density = np.exp(-.5*(vyy*dx*dx-2*vxy*dx*dy+vxx*dy*dy)/det)/(2*np.pi*np.sqrt(det))
    return np.sum(density*weights[None, :, None]*weights[None, None, :]/4, axis=(1, 2))


@lru_cache(maxsize=2)
def replay_bank(shape, draw):
    seed = [2026103102, draw]
    bank = np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed))).standard_normal(shape)
    canonical = np.ascontiguousarray(bank, dtype='<f8')
    return bank, sha256(str(canonical.shape).encode('ascii')+b'|'+canonical.tobytes()).hexdigest()


def solve_wls(item, data, weights, position):
    """Signed target, background and neighbor coefficients, normalized WLS."""
    data, error, w = np.asarray(data, float), np.asarray(item['error'], float), np.asarray(weights, float)
    target = item['renderer'](np.asarray(position, float)).to_value(u.MJy/u.sr/u.Jy)
    X = np.column_stack((target, item['background_design'], item['neighbor_design']))
    if (data.ndim != 1 or error.shape != data.shape or w.shape != data.shape or X.shape[0] != len(data)
            or not np.isfinite(X).all() or not np.isfinite(data).all() or not np.isfinite(error).all()
            or not np.isfinite(w).all() or np.any(error <= 0) or np.any(w <= 0) or np.any(w > 1)):
        raise ValueError('invalid WLS inputs')
    white = np.sqrt(w)/error; A = X*white[:, None]; norms = np.linalg.norm(A, axis=0)
    if np.any(norms <= 0) or not np.isfinite(norms).all(): raise ValueError('invalid WLS column norm')
    coeff, _, rank, _ = np.linalg.lstsq(A/norms, data*white, rcond=1e-10)
    if rank != X.shape[1]: raise ValueError('independent WLS rank deficient')
    coeff = coeff/norms; model = X@coeff; residual = data-model; weighted = residual*white
    return {'coefficients': coeff, 'model': model, 'residual': residual,
            'weighted_residual': weighted, 'cost': float(weighted@weighted)}


def exact_interval(k, n):
    interval = binomtest(int(k), int(n)).proportion_ci(confidence_level=.95, method='exact')
    return [float(interval.low), float(interval.high)]


def compare_tree(expected, actual, path='summary'):
    """Compare a required projected tree including exact list lengths/identities."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or not set(expected) <= set(actual): raise ValueError(path+' fields differ')
        for key, value in expected.items(): compare_tree(value, actual[key], path+'.'+key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual): raise ValueError(path+' length differs')
        for i, (a, b) in enumerate(zip(expected, actual)): compare_tree(a, b, path+'['+str(i)+']')
    elif expected is None or isinstance(expected, (bool, str)):
        if type(actual) is not type(expected) or actual != expected: raise ValueError(path+' differs')
    elif isinstance(expected, (int, float, np.number)):
        if isinstance(actual, bool) or not isinstance(actual, (int, float)): raise ValueError(path+' numeric type differs')
        close(actual, expected, path, atol=2e-12 if 'interval_95' in path else 1e-10,
              rtol=0 if 'interval_95' in path else 1e-9)
    elif actual != expected: raise ValueError(path+' differs')


def _describe(values, noisy):
    if not values:
        return {'n': 0, 'mean_dx_dy_native_px': None, 'mean_radial_native_px': None,
                'rms_radial_native_px': None, 'p90_radial_native_px': None, 'max_radial_native_px': None,
                'mean_flux_ratio': None, 'mean_flux_ratio_bias': None, 'flux_ratio_mcse': None, 'identity_counts': {}}
    xy = np.asarray([v['xy'] for v in values]); rad = np.asarray([v['rad'] for v in values]); ratio = np.asarray([v['ratio'] for v in values])
    return {'n': len(values), 'mean_dx_dy_native_px': xy.mean(axis=0).tolist(),
            'mean_radial_native_px': float(rad.mean()), 'rms_radial_native_px': float(np.sqrt(np.mean(rad**2))),
            'p90_radial_native_px': float(np.percentile(rad, 90)), 'max_radial_native_px': float(rad.max()),
            'mean_flux_ratio': float(ratio.mean()), 'mean_flux_ratio_bias': float(ratio.mean()-1),
            'flux_ratio_mcse': float(np.std(ratio, ddof=1)/np.sqrt(len(values))) if noisy and len(values)>1 else None,
            'identity_counts': dict(Counter(v['identity'] for v in values))}


def verify_metrics(records, keys, summary):
    """Recompute every planned stratum, pair and primary guard without study metrics."""
    keys = [tuple(k) for k in keys]
    if len(keys) != 640 or len(set(keys)) != 640 or Counter(k[0] for k in keys) != {'noiseless':192,'noisy':384,'null':64}:
        raise ValueError('planned denominator differs')
    indexed = {tuple(r['key']): r['payload'] for r in records}
    if len(indexed) != len(records) or set(indexed) != set(keys): raise ValueError('missing or duplicate record')
    values = {}; groups = defaultdict(list)
    for key in keys:
        row = indexed[key]; section, _, _, _, scene, flux, _, _ = key
        status = row.get('status')
        if status not in study.STATUSES: raise ValueError('invalid terminal status')
        value = None
        if status == 'fit_completed':
            if type(row.get('numerical_support')) is not bool: raise ValueError('invalid support')
            estimate = float(row['target_flux_jy']); truth = float(row['true_flux_jy'])
            if not np.isfinite([estimate, truth]).all() or truth != int(flux)*1e-6: raise ValueError('flux identity differs')
            if section == 'null':
                if truth != 0 or row['position_native_error'] is not None or row['distance_to_companion_native'] is not None: raise ValueError('invalid null truth')
                value = {'support': row['numerical_support'], 'flux': estimate, 'truth': truth}
            else:
                xy = np.asarray(row['position_native_error'], float); rad = float(np.linalg.norm(xy)); d = row['distance_to_companion_native']
                if xy.shape != (2,) or not np.isfinite(xy).all() or truth <= 0: raise ValueError('invalid native error')
                if scene == 'isolated' and d is not None: raise ValueError('isolated companion truth')
                if d is not None and (not np.isfinite(d) or d < 0): raise ValueError('invalid companion distance')
                near_t, near_c = rad <= .5, d is not None and d <= .5
                identity = 'ambiguous' if near_t and near_c else 'target' if near_t else 'companion' if near_c else 'unknown' if scene != 'isolated' and d is None else 'elsewhere'
                value = {'support': row['numerical_support'], 'flux': estimate, 'truth': truth, 'xy': xy.tolist(),
                         'rad': rad, 'ratio': estimate/truth, 'distance': d, 'identity': identity}
        elif not isinstance(row.get('error'), str) or not row['error'].strip(): raise ValueError('failure has no reason')
        values[key] = value; groups[key[:6]+key[7:]].append(key)
    result = {'planned': 640, 'section_counts': dict(Counter(k[0] for k in keys)),
              'status_counts': dict(Counter(indexed[k]['status'] for k in keys)), 'strata': [], 'null_strata': [],
              'noisy_clean_gates': [], 'old_assessment_blocked': True, 'promotion': False}
    for group in sorted(groups):
        section,g,t,p,scene,flux,arm = group; items = groups[group]; done = [values[k] for k in items if values[k] is not None]
        label = dict(zip(('section','geometry','truth','phase','scene','flux','arm'),group))
        base = {**label, 'planned': len(items), 'status_counts': dict(Counter(indexed[k]['status'] for k in items))}
        if section == 'null':
            if len(items) != 8: raise ValueError('null denominator differs')
            count = sum(v['support'] and v['flux'] > 0 for v in done)
            result['null_strata'].append({**base, 'positive_supported': count, 'positive_supported_interval_95': exact_interval(count,8)})
        else:
            result['strata'].append({**base, 'numerical_supported': sum(v['support'] for v in done),
                'all_completed': _describe(done, section=='noisy'),
                'supported_completed': _describe([v for v in done if v['support']], section=='noisy')})
            if section == 'noisy' and scene != 'omitted':
                if len(items) != 16: raise ValueError('noisy denominator differs')
                count = sum(v['support'] and v['flux'] > 0 and v['rad'] <= .5 and .5 <= v['ratio'] <= 1.5 for v in done)
                result['noisy_clean_gates'].append({**label, 'planned': 16, 'success': count,
                    'exact_interval_95': exact_interval(count,16), 'observed_sample_gate_passed': count >= 15})
    clean = [k for k in keys if k[0]=='noiseless' and k[4] in ('isolated','modeled')]
    rows = [{'key':list(k), 'passed': bool((v:=values[k]) is not None and v['support'] and v['rad']<=.1 and .9<=v['ratio']<=1.1)} for k in clean]
    result['noiseless_clean_gate'] = {'planned':len(rows), 'passed_count':sum(r['passed'] for r in rows), 'passed':all(r['passed'] for r in rows), 'rows':rows}
    result['noisy_clean_all_gates_passed'] = all(g['observed_sample_gate_passed'] for g in result['noisy_clean_gates'])
    pairs = []
    for base in sorted({k[:-1] for k in keys}):
        ka,kb = (*base,'baseline'),(*base,'corrected'); a,b = values[ka],values[kb]; both = a is not None and b is not None
        pair = {'key_without_arm':list(base), 'baseline_status':indexed[ka]['status'], 'corrected_status':indexed[kb]['status'],
                'both_completed':both, 'delta_position_native_px':None, 'delta_flux_ratio':None,
                'delta_radial_native_px':None, 'delta_abs_flux_ratio_error':None,
                'new_numerical_refusal':bool(a is not None and a['support'] and (b is None or not b['support']))}
        if both and base[0] != 'null':
            pair.update(delta_position_native_px=(np.asarray(b['xy'])-a['xy']).tolist(), delta_flux_ratio=b['ratio']-a['ratio'],
                        delta_radial_native_px=b['rad']-a['rad'], delta_abs_flux_ratio_error=abs(b['ratio']-1)-abs(a['ratio']-1))
        pairs.append(pair)
    guard = [{'key_without_arm':p['key_without_arm'], 'passed':bool(p['both_completed'] and not p['new_numerical_refusal']
             and p['delta_radial_native_px'] <= .02 and p['delta_abs_flux_ratio_error'] <= .02)} for p in pairs
             if p['key_without_arm'][0]=='noiseless' and p['key_without_arm'][4] in ('isolated','modeled')]
    result['noiseless_preservation_guard'] = {'planned_pairs':len(guard), 'passed_count':sum(r['passed'] for r in guard), 'passed':all(r['passed'] for r in guard), 'rows':guard}
    pairgroups = defaultdict(list)
    for pair in pairs: pairgroups[tuple(pair['key_without_arm'][:6])].append(pair)
    strata = []
    for group, ps in sorted(pairgroups.items()):
        valid = [p for p in ps if p['both_completed']]; present = [p for p in valid if p['delta_radial_native_px'] is not None]
        mean = lambda name: float(np.mean([p[name] for p in present])) if present else None
        strata.append({**dict(zip(('section','geometry','truth','phase','scene','flux'),group)), 'planned_pairs':len(ps),
            'both_completed':len(valid), 'missing_pairs':len(ps)-len(valid),
            'mean_delta_position_native_px':np.mean([p['delta_position_native_px'] for p in present],axis=0).tolist() if present else None,
            'mean_delta_flux_ratio':mean('delta_flux_ratio'), 'mean_delta_radial_native_px':mean('delta_radial_native_px'),
            'mean_delta_abs_flux_ratio_error':mean('delta_abs_flux_ratio_error')})
    result['paired'] = {'planned':len(pairs), 'both_completed':sum(p['both_completed'] for p in pairs),
                        'missing':sum(not p['both_completed'] for p in pairs), 'rows':pairs, 'strata':strata}
    result['records'] = []
    for key in keys:
        row = indexed[key]; v = values[key]; projected = None
        if v is not None:
            projected = {'numerical_support':v['support'], 'target_flux_jy':v['flux'], 'true_flux_jy':v['truth'],
                'position_native_error':v.get('xy'), 'radial_error_native_px':v.get('rad'), 'flux_ratio':v.get('ratio'),
                'distance_to_companion_native':v.get('distance'), 'identity':v.get('identity')}
        result['records'].append({'key':list(key), 'status':row['status'], 'error':row.get('error') if v is None else None, 'values':projected})
    compare_tree(result, summary)
    return {'strata':len(result['strata']), 'null_strata':len(result['null_strata']), 'pairs':len(pairs),
            'noiseless_clean':len(rows), 'noisy_gates':len(result['noisy_clean_gates']), 'preservation':len(guard)}


def check_pair_hashes(records):
    indexed = {tuple(r['key']):r['payload'] for r in records}
    def hashed(key):
        meta = indexed[key].get('realization')
        return None if meta is None else meta.get('realization_sha256')
    for key in indexed:
        if key[-1] == 'baseline':
            other = (*key[:-1], 'corrected'); a,b = hashed(key),hashed(other)
            if a is not None and b is not None and a != b: raise ValueError('paired arm realization differs')
        if key[4] == 'modeled':
            other = (*key[:4], 'omitted', *key[5:]); a,b = hashed(key),hashed(other)
            if a is not None and b is not None and a != b: raise ValueError('modeled and omitted realization differs')


def check_geometry(geometry, phase):
    inp = study.inputs; frame = geometry['frame']; original = inp.original
    native = original.native_position(frame, geometry['anchor_common'])
    target = np.floor(native)+np.asarray(((.25,.25),(.25,.75),(.75,.25),(.75,.75))[int(phase)])
    close(geometry['target_native'], target, 'phase native', atol=1e-7, rtol=0)
    close(geometry['companion_native'], target+[1.5,0], 'companion native', atol=1e-7, rtol=0)
    close(original.native_position(frame, geometry['target_common']), target, 'native/common', atol=1e-7, rtol=0)
    omega = geometry['omega'].to_value(u.sr)
    if np.any(~np.isfinite(omega)) or np.any(omega <= 0): raise ValueError('invalid pixel solid angle')
    sample = geometry['synthetic_prepared']['sample']
    background_columns = np.asarray(sample['background'], float)
    close(geometry['background'], background_columns@np.array([.04,.015,-.01]), 'plane mean')
    fractions_by_source = {}
    for label, position, scene in (('target',target,'isolated'), ('companion',target+[1.5,0],'modeled')):
        independent = gaussian64(geometry['x'], geometry['y'], position)
        fractions_by_source[label] = independent
        generated = inp.realize(geometry, 'noiseless', 'gaussian', scene, 600, 0)
        surface = generated['target'] if scene == 'isolated' else generated['companion']
        fractions = surface*(1e6*omega)/.0006
        l1 = float(np.sum(np.abs(independent-fractions)))
        if l1 > 1e-10+1e-10*float(np.sum(independent)): raise ValueError('independent Gaussian L1 differs')
    geometry['_audit_fractions'] = fractions_by_source


def check_scene(geometry, key, realized, payload):
    section, sid, truth, phase, scene, flux, draw, arm = key
    meta = realized['metadata']; amount = int(flux)*1e-6
    if meta['original_image_added'] is not False or meta['target_flux_jy'] != amount: raise ValueError('scene provenance or flux differs')
    close(realized['mean'], geometry['background']+realized['target']+realized['companion'], 'synthetic mean')
    if scene == 'isolated': close(realized['companion'], np.zeros_like(realized['companion']), 'isolated companion')
    if section == 'null':
        if meta['target_native_xy'] is not None or meta['companion_native_xy'] is not None: raise ValueError('null has invented source truth')
        close(realized['target'], np.zeros_like(realized['target']), 'null target')
    else:
        close(meta['target_native_xy'], geometry['target_native'], 'source native position', atol=1e-7, rtol=0)
        if truth == 'gaussian':
            factor = amount/(1e6*geometry['omega'].to_value(u.sr))
            close(realized['target'], factor*geometry['_audit_fractions']['target'], 'independent Gaussian target')
            if scene != 'isolated': close(realized['companion'], factor*geometry['_audit_fractions']['companion'], 'independent Gaussian companion')
        else:
            base = study.inputs.model_for(geometry,'baseline',False)
            target = amount*base['renderer'](geometry['target_common']).to_value(u.MJy/u.sr/u.Jy)
            close(realized['target'], target, 'matched baseline target')
            if scene != 'isolated':
                neighbor = study.inputs.model_for(geometry,'baseline',True)['neighbor_design'][:,0]*amount
                close(realized['companion'], neighbor, 'matched baseline companion')
    if section == 'noiseless': z = np.zeros(len(geometry['x'])); expected_seed = None; bank_hash = None
    else:
        seed = [2026103102, int(draw)]; expected_seed = seed
        bank, bank_hash = replay_bank(tuple(geometry['frame']['data'].shape), int(draw))
        z = bank[geometry['y'], geometry['x']]
    if meta['seed'] != expected_seed or meta['whole_exposure_noise_bank_sha256'] != bank_hash: raise ValueError('seed or physical-pixel bank differs')
    close(realized['data'], realized['mean']+geometry['error']*z, 'independent noise reconstruction')
    if study.inputs.array_digest(realized['data']) != meta['realization_sha256']: raise ValueError('realization digest differs')
    if 'realization' in payload: compare_tree(meta, payload['realization'], 'saved realization')
    if 'geometry_metadata' in payload:
        compare_tree(study.parent.calibration.legacy.jsonable(geometry['original_metadata']),
                     payload['geometry_metadata'], 'saved geometry')
    if 'search_anchor_common' in payload:
        anchor = geometry['target_common'] if section == 'null' else geometry['anchor_common']
        close(payload['search_anchor_common'], anchor, 'search anchor', atol=1e-7, rtol=0)


def check_fit(geometry, key, realized, row, item=None):
    if item is None: item = study.inputs.fit_item(geometry, realized, key[4], key[7])
    saved = row['samples']
    if len(saved) != 1: raise ValueError('saved sample denominator differs')
    s = saved[0]; expected_neighbors = [study.inputs.COMPANION_ID] if key[4]=='modeled' else []
    if s['neighbor_ids'] != expected_neighbors or s['neighbor_unit'] != item['neighbor_unit']:
        raise ValueError('neighbor identity or units differ')
    for name, target in (('data_mjysr',realized['data']), ('error_mjysr',geometry['error']),
                         ('background_design',item['background_design']), ('neighbor_design_per_jy',item['neighbor_design'])):
        close(s[name], target, 'saved '+name)
    if s['x'] != geometry['x'].tolist() or s['y'] != geometry['y'].tolist(): raise ValueError('native pixels differ')
    if row['status'] != 'fit_completed': return {'objective_available':False, 'successful_final_starts':0}
    fit = row['fit']; frame = fit['frames'][0]
    if len(fit['frames']) != 1 or frame['obs_id'] != study.OBS_ID or type(fit['numerical_support']) is not bool:
        raise ValueError('fit frame identity differs')
    if (row['numerical_support'] != fit['numerical_support'] or fit['nonnegative_neighbors'] is not False
            or fit['data_unit'] != str(u.MJy/u.sr)):
        raise ValueError('fit support, signed coefficients or units differ')
    weights = np.asarray(frame['weights'], float)
    result = solve_wls(item, realized['data'], weights, fit['position'])
    nbg = np.asarray(item['background_design']).shape[1]; c = result['coefficients']
    close(c[0], frame['target_flux_jy'], 'target flux', atol=1e-10, rtol=1e-8)
    close(c[1:1+nbg], frame['background_coefficients'], 'background coefficients')
    close(c[1+nbg:], frame['neighbor_flux_jy'], 'neighbor flux', atol=1e-10, rtol=1e-8)
    for name in ('model','residual','weighted_residual'): close(result[name], frame[name], name)
    close(result['cost'], frame['chi2_weighted'], 'frame weighted cost', atol=1e-8, rtol=1e-9)
    close(result['cost'], fit['chi2_weighted'], 'total weighted cost', atol=1e-8, rtol=1e-9)
    close(frame['target_flux_jy'], row['target_flux_jy'], 'row target flux', atol=1e-10, rtol=1e-8)
    native = study.inputs.original.native_position(geometry['frame'], fit['position'])
    close(row['position_native'], native, 'saved native position', atol=1e-7, rtol=0)
    if key[0] == 'null':
        if row['position_native_error'] is not None or row['distance_to_companion_native'] is not None: raise ValueError('null position truth')
    else:
        close(row['position_native_error'], native-geometry['target_native'], 'native error', atol=1e-7, rtol=0)
        if key[4] != 'isolated': close(row['distance_to_companion_native'], np.linalg.norm(native-geometry['companion_native']), 'companion distance', atol=1e-7, rtol=0)
    starts = fit['final_mode_audit']['starts']
    if len(starts) != 9: raise ValueError('final start denominator differs')
    successes = 0
    anchor = geometry['target_common'] if key[0] == 'null' else geometry['anchor_common']
    for start, offset in zip(starts, study.parent.baseline.model.START_OFFSETS):
        if start.get('stage') != 'final_fixed_weights' or type(start.get('success')) is not bool: raise ValueError('invalid final start')
        close(start['start'], np.asarray(anchor)+np.asarray(offset), 'final start anchor', atol=1e-7, rtol=0)
        if start['success']:
            value = solve_wls(item, realized['data'], weights, start['position'])['cost']
            close(value, start['chi2'], 'final start cost', atol=1e-8, rtol=1e-9); successes += 1
    return {'objective_available':True, 'successful_final_starts':successes}


class ReplayedPreparation(Exception):
    """Only an exact original preparation failure at the same stage."""


def replay_preparation(row, stage, operation):
    try:
        return operation()
    except Exception as exc:
        message = type(exc).__name__+': '+str(exc)
        if (row.get('status') == 'preparation_failed' and row.get('failure_stage') == stage
                and row.get('error') == message):
            raise ReplayedPreparation(message) from exc
        raise


def run():
    study.parent.assert_assessment_unopened()
    design = study.parent.frozen.verify(study.DESIGN, study.RULES, study.SOURCES, COMMIT)
    context, coefficients, metadata = study.open_inputs()
    if design['metadata'] != study.parent.calibration.legacy.jsonable(metadata): raise ValueError('frozen input metadata differs')
    journal = study.open_journal(COMMIT); records = journal.records(require_complete=True)
    digest = study.parent.calibration.record_digest(journal, records)
    summary_path = study.OUTPUT/'summary.json'; summary = json.loads(summary_path.read_text(encoding='utf-8'))
    if (summary.get('protocol_commit') != COMMIT or summary.get('cell_digest') != digest
            or summary.get('design_sha256') != study.parent.calibration.legacy.lab.digest(study.DESIGN)
            or summary.get('assessment_opened') is not False or summary.get('promotion') is not False):
        raise ValueError('summary source identity differs')
    global_findings = []; metric_counts = None
    try:
        metric_counts = verify_metrics(records, study.expected_keys(), summary['metrics'])
    except Exception as exc:
        global_findings.append({'key':None, 'status':'audit_mismatch', 'error':'summary: '+type(exc).__name__+': '+str(exc)})
    try:
        check_pair_hashes(records)
    except Exception as exc:
        global_findings.append({'key':None, 'status':'audit_mismatch', 'error':'paired images: '+type(exc).__name__+': '+str(exc)})
    identity = {'protocol_commit':COMMIT, 'design_sha256':study.parent.calibration.legacy.lab.digest(study.DESIGN),
        'study_cell_digest':digest, 'summary_sha256':study.parent.calibration.legacy.lab.digest(summary_path),
        'upstream':study.parent.calibration.legacy.jsonable(metadata),
        'source_sha256':{p:study.parent.calibration.legacy.lab.digest(study.ROOT/p) for p in FILES},
        'runtime':study.parent.frozen.runtime()}
    audit = Journal(AUDIT_DIR/'cells', identity, study.expected_keys(), ('verified','input_checked_unavailable','unverified_failure','audit_mismatch'))
    geometries = {}; realizations = {}
    for envelope in records:
        key = tuple(envelope['key']); row = envelope['payload']
        if audit.read(key) is not None: continue
        try:
            gkey = key[1], key[3]
            if gkey not in geometries:
                geometry = replay_preparation(row, 'geometry_or_realization', lambda:
                    study.inputs.prepare_geometry(context, key[1], study.OBS_ID, int(key[3]), coefficients))
                check_geometry(geometry, key[3]); geometries[gkey] = geometry
            geometry = geometries[gkey]; group = key[:-1]
            if group not in realizations:
                realizations[group] = replay_preparation(row, 'geometry_or_realization', lambda:
                    study.inputs.realize(geometry,key[0],key[2],key[4],int(key[5]),int(key[6])))
            if row.get('status') == 'preparation_failed' and row.get('failure_stage') == 'geometry_or_realization':
                raise ValueError('original geometry or realization failure did not reproduce')
            realized = realizations[group]; check_scene(geometry,key,realized,row)
            item = replay_preparation(row, 'preparation', lambda: study.inputs.fit_item(geometry, realized, key[4], key[7]))
            replay_preparation(row, 'preparation', lambda: study.parent.baseline.previous.descriptors([item]))
            if row.get('status') == 'preparation_failed':
                raise ValueError('original model preparation failure did not reproduce')
            detail = check_fit(geometry,key,realized,row,item) if 'samples' in row else {'objective_available':False,'successful_final_starts':0}
            if row['status']=='fit_completed' and not detail['objective_available']: raise ValueError('completed fit lacks saved samples')
            status = 'verified' if detail['objective_available'] else 'input_checked_unavailable'
            payload = {'status':status, 'study_checksum':envelope['checksum'], 'study_status':row['status'],
                       'study_error':row.get('error'), **detail}
        except ReplayedPreparation as exc:
            payload = {'status':'input_checked_unavailable', 'study_checksum':envelope['checksum'],
                       'study_status':row['status'], 'study_error':row.get('error'),
                       'replayed_preparation_error':str(exc), 'replayed_failure_stage':row['failure_stage'],
                       'objective_available':False, 'successful_final_starts':0}
        except Exception as exc:
            status = 'unverified_failure' if row['status'] != 'fit_completed' else 'audit_mismatch'
            payload = {'status':status, 'error':type(exc).__name__+': '+str(exc), 'study_checksum':envelope['checksum'],
                       'study_status':row['status'], 'study_error':row.get('error'), 'objective_available':False,
                       'successful_final_starts':0}
        audit.write(key,payload)
        print('AUDIT',*key,payload['status'],flush=True)
    checks = audit.records(require_complete=True); counts = dict(Counter(r['payload']['status'] for r in checks))
    failures = global_findings + [{'key':r['key'], 'status':r['payload']['status'], 'error':r['payload'].get('error')} for r in checks
                                  if r['payload']['status'] in ('unverified_failure','audit_mismatch')]
    receipt = {'schema':'signal-control-independent-audit-1', 'status':'passed' if not failures else 'failed',
        'identity':identity, 'planned':640, 'counts':counts, 'metric_checks':metric_counts,
        'objective_checked':sum(r['payload']['objective_available'] for r in checks),
        'successful_final_starts_checked':sum(r['payload']['successful_final_starts'] for r in checks),
        'failures':failures, 'audit_checkpoint_digest':study.parent.calibration.record_digest(audit,checks),
        'assessment_opened':False, 'promotion':False,
        'qualification':'Conditional saved-point WLS and synthetic replay; no optimizer proof, physical PSF truth, calibrated coverage, detection or assessment promotion. Matched truth is inverse crime.'}
    receipt['receipt_sha256'] = sha256(study.parent.calibration.legacy.encoded(receipt)).hexdigest()
    path = RECEIPT
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != receipt: raise ValueError('immutable audit receipt differs')
    else: atomic(path,receipt)
    study.parent.assert_assessment_unopened()
    return receipt


if __name__ == '__main__':
    result = run()
    print(json.dumps({'status':result['status'], 'counts':result['counts'], 'receipt_sha256':result['receipt_sha256']}))
