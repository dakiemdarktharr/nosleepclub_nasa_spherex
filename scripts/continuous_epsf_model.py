"""Development candidate: zero-padded target ePSF, frozen 0.9 nuisance model."""
import numpy as np
from scipy.ndimage import spline_filter
from . import ablation_model as baseline
from . import profile_uncertainty as profile

old = baseline.old
joint = baseline.joint
PAD = 16


def padded_coefficients(frame, zone, pad=PAD):
    if not isinstance(pad, int) or pad < 0:
        raise ValueError('pad must be a nonnegative integer')
    raw = np.asarray(frame['epsf_table']['EPSF'][zone], float)
    over = frame['epsf_oversampling']
    if not np.isfinite(raw).all() or not np.isfinite(over) or over <= 0 or abs(raw.sum()) < 1e-15:
        raise ValueError('invalid ePSF')
    raw = raw * over**2 / raw.sum()
    return spline_filter(np.pad(raw, pad), order=3)


def prepare(frames, catalog, xy, anchor, target_id=None, pad=PAD):
    samples = old.samples_for(frames, catalog, xy, anchor, target_id)
    output = []
    for s in samples:
        s = {**s, 'epsf': padded_coefficients(s['frame'], s['zone'], pad)}
        # The neighbour templates are frozen old ePSFs, even with padded target.
        output.append(joint.prepare(s, s['neighbours']))
    return output


def fit(frames, catalog, xy, anchor, reference, target_id=None, pad=PAD):
    anchor = np.asarray(anchor, float)
    samples = prepare(frames, catalog, xy, anchor, target_id, pad)
    result = old.solve(samples, anchor, starts=True)
    for _ in range(old.RULES['irls_iterations']):
        weighted = []
        for s in samples:
            r = joint.residual_sample(s, result.x)*s['error']/s['original_error']
            weights = np.minimum(1., old.RULES['huber_threshold']/np.maximum(np.abs(r), 1e-12))
            weighted.append(old.reweight(s, weights))
        samples = weighted
        result = old.solve(samples, anchor, starts=False, initial=result.x)
    details, chi = old.diagnostics(samples, result.x)
    covariance = np.linalg.pinv(result.jac.T@result.jac)*max(1., chi)
    singular = np.linalg.svd(result.jac, compute_uv=False)
    rank = int(np.sum(singular > singular[0]*baseline.RULES['information_svd_relative_cut'])) if len(singular) and singular[0] > 0 else 0
    weights = np.array([max(v['snr'], 0.)**2 for v in details]); times = [v['mjd'] for v in details]
    output = {'position': result.x, 'covariance': covariance, 'success': bool(result.success),
        'at_boundary': bool(np.any(np.abs(result.x-anchor) > .95*old.RULES['fit_bound_px'])),
        'reduced_chi2': float(chi), 'per_frame': details, 'samples': samples,
        'effective_mjd': float(np.average(times, weights=weights)) if weights.sum() else float(np.mean(times)),
        'information_rank': rank, 'parameter_count': 2}
    if reference is not None:
        limit = max(old.RULES['model_disagreement_floor_px'], old.RULES['model_disagreement_sigma']*
                    np.sqrt(max(np.linalg.eigvalsh(reference['covariance']+covariance).max(), 0.)))
        output['model_comparison'] = {'against':'common single-source',
            'shift_px':float(np.linalg.norm(reference['position']-result.x)), 'limit_px':float(limit)}
    output['quality'] = old.gate(output)
    if reference is None: output['quality']['reasons'].append('comparison_unavailable')
    if rank < 2 or not np.isfinite(covariance).all() or np.linalg.eigvalsh(covariance).min() <= 0:
        output['quality']['reasons'].append('singular_information')
    output['quality']['accepted'] = not output['quality']['reasons']
    if numeric_valid(output):
        try:
            output['profile'] = profile.covariance(output)
        except (ValueError, np.linalg.LinAlgError) as exc:
            output['profile'] = {'supported': False, 'reason':'profile_exception', 'detail':str(exc)}
    else:
        output['profile'] = {'supported': False, 'reason':'invalid_point_fit'}
    return output


def numeric_valid(fit):
    """Never treat a boundary or rank-deficient fit as valid inference."""
    return bool(baseline.old.bench.valid_fit(fit) and fit['information_rank'] == 2
        and np.isfinite(fit['position']).all() and np.isfinite(fit['covariance']).all()
        and np.linalg.eigvalsh(fit['covariance']).min() > 0)
