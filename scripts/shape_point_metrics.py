"""Fixed descriptive metrics for the 56 already-opened primary point cells."""
from collections import Counter
from numbers import Integral, Real

import numpy as np


QUALIFICATION = ('Developmental descriptive budgets on an already opened, image-selected cohort; '
    'not independent validation, calibrated uncertainty, scientific improvement, or a detection. '
    'All common-completed pairs are retained, including partial sources; no cell-independence '
    'confidence interval or numerical-support selection is applied.')
STATUSES = ('fit_completed', 'fit_failed', 'preparation_failed')


def _radial(record):
    value = record.get('residual_east_north_arcsec')
    array = np.asarray(value, dtype=object)
    if (array.shape != (2,) or any(isinstance(x, (bool, np.bool_)) or not isinstance(x, Real)
                                   or not np.isfinite(x) for x in array)):
        raise ValueError('completed fit requires finite two-vector residual in arcsec')
    result = float(np.hypot(float(array[0]), float(array[1])))
    if not np.isfinite(result):
        raise ValueError('radial residual is numerically unrepresentable')
    return result


def _status(record, label):
    if record is None:
        return 'missing'
    if not isinstance(record, dict) or record.get('status') not in STATUSES:
        raise ValueError(label + ' has invalid terminal status')
    if record['status'] != 'fit_completed' and (not isinstance(record.get('error'), str) or not record['error'].strip()):
        raise ValueError(label + ' failure requires a reason')
    if record['status'] == 'fit_completed':
        if not isinstance(record.get('fit'), dict) or not isinstance(record['fit'].get('numerical_support'), bool):
            raise ValueError(label + ' requires explicit numerical support')
        _radial(record)
    return record['status']


def summarize_primary(primary_keys, point_records, baseline_records, epoch_by_obs, rules):
    """Summarize fixed primary pairs and declared gates without model selection.

    Record mappings contain journal payloads keyed by (source ID, exposure ID).
    Missing point or old records remain explicit and prevent acceptance. Baseline
    and corrected residual vectors are east/north arcseconds. The return is
    strict JSON-compatible Python values, with undefined metrics represented by
    None rather than NaN or an invented fallback.
    """
    try:
        original_keys = tuple(primary_keys)
        if any(not isinstance(k, (list, tuple)) for k in original_keys):
            raise ValueError('key must be a source/exposure pair')
        keys = tuple(tuple(k) for k in original_keys)
    except (TypeError, ValueError) as exc:
        raise ValueError('primary keys must be source/exposure pairs') from exc
    if (len(keys) != 56 or len(set(keys)) != 56
            or any(len(k) != 2 or any(not isinstance(s, str) or not s.strip() for s in k) for k in keys)):
        raise ValueError('56 unique nonempty source/exposure primary keys required')
    if not isinstance(point_records, dict) or not isinstance(baseline_records, dict) or not isinstance(epoch_by_obs, dict):
        raise ValueError('record and epoch mappings required')
    sources = sorted({k[0] for k in keys})
    if len(sources) != 7 or len({k[1] for k in keys}) != 8:
        raise ValueError('seven primary sources and eight shared exposures required')
    try:
        epochs = {epoch_by_obs[obs] for _, obs in keys}
    except KeyError as exc:
        raise ValueError('epoch missing for planned exposure') from exc
    if len(epochs) != 2 or any(not isinstance(e, str) or not e.strip() for e in epochs):
        raise ValueError('exactly two nonempty season IDs required')
    epochs = sorted(epochs)
    for source in sources:
        own = [k for k in keys if k[0] == source]
        if len(own) != 8 or any(sum(epoch_by_obs[obs] == epoch for _, obs in own) != 4 for epoch in epochs):
            raise ValueError('each source requires four planned observations per season')
    support_name = 'minimum_supported_sources';frames_name = 'minimum_common_frames_per_source_per_season'
    if not isinstance(rules, dict):
        raise ValueError('explicit primary gate rules required')
    for name in (support_name, frames_name):
        value = rules.get(name)
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value < 1:
            raise ValueError('invalid count gate: '+name)
    names = ('equal_source_mean_radial_improvement_min_arcsec', 'p90_radial_increase_max_arcsec',
             'paired_new_rms_max_arcsec', 'paired_new_p90_max_arcsec')
    for name in names:
        value = rules.get(name)
        if (isinstance(value, (bool, np.bool_)) or not isinstance(value, Real)
                or not np.isfinite(value) or value < 0):
            raise ValueError('invalid numerical gate: '+name)
    if rules.get('no_new_numerical_refusals') is not True:
        raise ValueError('no-new-numerical-refusals guard must be explicit')
    by_source = {source: [] for source in sources}
    status_old = Counter();status_new = Counter();all_rows = [];new_refusals = 0
    for key in keys:
        source, obs = key;old = baseline_records.get(key);new = point_records.get(key)
        old_status = _status(old, 'baseline record');new_status = _status(new, 'point record')
        status_old[old_status] += 1;status_new[new_status] += 1
        old_support = old['fit']['numerical_support'] if old_status == 'fit_completed' else None
        new_support = new['fit']['numerical_support'] if new_status == 'fit_completed' else None
        new_refusal = old_support is True and (new_status != 'fit_completed' or new_support is not True)
        new_refusals += int(new_refusal)
        paired = old_status == 'fit_completed' and new_status == 'fit_completed'
        old_r = _radial(old) if paired else None;new_r = _radial(new) if paired else None
        row = {'key': list(key), 'season': epoch_by_obs[obs], 'baseline_status': old_status,
               'point_status': new_status, 'baseline_error': old['error'] if old_status in ('fit_failed', 'preparation_failed') else None,
               'point_error': new['error'] if new_status in ('fit_failed', 'preparation_failed') else None,
               'baseline_numerical_support': old_support,
               'point_numerical_support': new_support, 'new_numerical_refusal': new_refusal,
               'common_completed': paired, 'baseline_radial_arcsec': old_r, 'point_radial_arcsec': new_r,
               'baseline_residual_arcsec': [float(x) for x in old['residual_east_north_arcsec']] if paired else None,
               'point_residual_arcsec': [float(x) for x in new['residual_east_north_arcsec']] if paired else None}
        all_rows.append(row)
        if paired:
            by_source[source].append(row)
    old_all = [row['baseline_radial_arcsec'] for row in all_rows if row['common_completed']]
    new_all = [row['point_radial_arcsec'] for row in all_rows if row['common_completed']]
    source_rows = [];old_means = [];new_means = [];supported_count = 0
    for source in sources:
        rows = by_source[source];per_season = {epoch: sum(r['season'] == epoch for r in rows) for epoch in epochs}
        supported = all(v >= rules[frames_name] for v in per_season.values())
        supported_count += int(supported)
        old_mean = float(np.mean([r['baseline_radial_arcsec'] for r in rows])) if rows else None
        new_mean = float(np.mean([r['point_radial_arcsec'] for r in rows])) if rows else None
        if rows:
            old_means.append(old_mean);new_means.append(new_mean)
        source_rows.append({'source_id': source, 'planned': 8, 'pair_count': len(rows),
                            'pair_count_by_season': per_season, 'support_gate_met': supported,
                            'paired_keys': [r['key'] for r in rows],
                            'baseline_residual_vectors_arcsec': [r['baseline_residual_arcsec'] for r in rows],
                            'point_residual_vectors_arcsec': [r['point_residual_arcsec'] for r in rows],
                            'baseline_mean_radial_arcsec': old_mean, 'point_mean_radial_arcsec': new_mean,
                            'mean_improvement_arcsec': old_mean-new_mean if rows else None})
    old_equal = float(np.mean(old_means)) if old_means else None
    new_equal = float(np.mean(new_means)) if new_means else None
    improvement = old_equal-new_equal if old_means else None
    old_p90 = float(np.quantile(old_all, .9)) if old_all else None
    new_p90 = float(np.quantile(new_all, .9)) if new_all else None
    new_rms = float(np.linalg.norm(new_all)/np.sqrt(len(new_all))) if new_all else None
    p90_change = new_p90-old_p90 if new_all else None
    computed = [x for x in (old_equal, new_equal, improvement, old_p90, new_p90, new_rms, p90_change) if x is not None]
    if not np.isfinite(computed).all():
        raise ValueError('primary metrics are numerically unrepresentable')
    gates = {
        'all_planned_records_available': status_old['missing'] == 0 and status_new['missing'] == 0,
        'source_season_support': supported_count >= rules[support_name],
        'no_new_numerical_refusals': new_refusals == 0,
        'equal_source_improvement': improvement is not None and improvement >= rules[names[0]],
        'pooled_p90_increase': p90_change is not None and p90_change <= rules[names[1]],
        'paired_new_rms': new_rms is not None and new_rms <= rules[names[2]],
        'paired_new_p90': new_p90 is not None and new_p90 <= rules[names[3]],
    }
    return {'planned': 56, 'source_count': 7, 'baseline_status_counts': dict(status_old),
            'point_status_counts': dict(status_new), 'common_completed_pairs': len(old_all),
            'paired_source_count': len(old_means), 'supported_source_count': supported_count,
            'new_numerical_refusals': new_refusals, 'source_rows': source_rows, 'rows': all_rows,
            'equal_source_baseline_mean_radial_arcsec': old_equal,
            'equal_source_point_mean_radial_arcsec': new_equal,
            'equal_source_mean_radial_improvement_arcsec': improvement,
            'pooled_baseline_p90_radial_arcsec': old_p90, 'pooled_point_p90_radial_arcsec': new_p90,
            'pooled_p90_increase_arcsec': p90_change, 'paired_point_rms_radial_arcsec': new_rms,
            'gates': gates, 'developmental_gates_passed': all(gates.values()),
            'promotion': False, 'qualification': QUALIFICATION}
