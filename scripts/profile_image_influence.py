"""Conditional fixed-weight image influence and shape-score linearization.

All coordinates use the caller's common sky grid; physical shape parameters
use native pixel²/pixel³. These matrices omit nonlinear curvature and changes
in robust weights, masks, catalogue neighbors and upstream calibration.
"""
from numbers import Real

import numpy as np
import astropy.units as u

from .moment_preserving_epsf import DEFAULT_BOUNDS, PARAMETER_UNITS


def _array(value, shape, name):
    if isinstance(value, u.Quantity):
        raise ValueError(name + ' must use declared numeric units')
    if any(isinstance(v, (bool, np.bool_)) for v in np.asarray(value, dtype=object).ravel()):
        raise ValueError(name + ' cannot contain booleans')
    a = np.asarray(value)
    if a.shape != shape or a.dtype.kind not in 'iuf' or not np.isfinite(a).all():
        raise ValueError('invalid ' + name)
    return a.astype(float)


def centroid_and_shape_influence(item, fit, anchor, *, step=.002, bound=2.5,
                                 rcond=1e-10, max_condition=1e8):
    """Linearize a saved one-frame fit without refitting any point or weight.

    ``shape_renderer(p)`` returns N x 3 intensity/Jy per numeric physical shape
    parameter. ``neighbor_shape_design`` has N x Q x 3 with the same units.
    The full-position/linear-nuisance tangent span is retained, with no dropped
    columns. A composite shape score must account for overlapping input pixels.
    """
    for value in (step, bound, rcond, max_condition):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) or not np.isfinite(value):
            raise ValueError('finite real derivative/rank/condition controls required')
    if not 0 < step < bound or not 0 < rcond < 1 or max_condition <= 1:
        raise ValueError('invalid derivative/rank/condition controls')
    if len(fit['frames']) != 1 or fit['frames'][0]['obs_id'] != item['obs_id']:
        raise ValueError('exactly one matching native exposure required')
    if fit['data_unit'] != 'MJy / sr' or fit['nonnegative_neighbors'] is not False:
        raise ValueError('unconstrained physical Jy fit required')
    n = len(item['data']);q = len(item['neighbor_ids']);frame = fit['frames'][0]
    if u.Unit(item['neighbor_unit']) != u.MJy/u.sr/u.Jy:
        raise ValueError('physical neighbor unit scale mismatch')
    p = _array(fit['position'], (2,), 'position');anchor = _array(anchor, (2,), 'anchor')
    if np.any(np.abs(p-anchor) > bound):
        raise ValueError('point outside declared position bounds')
    error = _array(item['error'], (n,), 'error');weights = _array(frame['weights'], (n,), 'weights')
    if not np.allclose(_array(frame['error'], (n,), 'saved error'), error, rtol=1e-12, atol=0.):
        raise ValueError('saved original error changed')
    if np.any(error <= 0) or np.any(weights <= 0) or np.any(weights > 1):
        raise ValueError('positive original errors and final weights <=1 required')
    if frame['neighbor_ids'] != item['neighbor_ids']:
        raise ValueError('neighbor identity changed')
    target = np.asarray(item['renderer'](p).to_value(u.MJy/u.sr/u.Jy), float)
    target = _array(target, (n,), 'target template')
    flux = frame['target_flux_jy'];nflux = _array(frame['neighbor_flux_jy'], (q,), 'neighbor fluxes')
    if isinstance(flux, (bool, np.bool_)) or not np.isfinite(flux):
        raise ValueError('finite signed target flux required')
    derivatives = []
    for axis in range(2):
        a = p.copy();b = p.copy()
        a[axis] = max(anchor[axis]-bound, p[axis]-step)
        b[axis] = min(anchor[axis]+bound, p[axis]+step)
        if b[axis] <= a[axis]:
            raise ValueError('unresolved position derivative')
        da = item['renderer'](a).to_value(u.MJy/u.sr/u.Jy)
        db = item['renderer'](b).to_value(u.MJy/u.sr/u.Jy)
        derivatives.append(float(flux)*(db-da)/(b[axis]-a[axis]))
    background = np.asarray(item['background_design'])
    neighbor = _array(item['neighbor_design'], (n, q), 'neighbor design')
    if background.ndim != 2 or background.shape[0] != n or background.dtype.kind not in 'iuf' or not np.isfinite(background).all():
        raise ValueError('invalid background design')
    background = background.astype(float)
    J = np.column_stack((*derivatives, target, background, neighbor))
    white = np.sqrt(weights)/error
    A = J*white[:, None];scales = np.linalg.norm(A, axis=0)
    if not np.isfinite(scales).all() or np.any(scales <= 0):
        raise ValueError('zero/invalid full local derivative column')
    U, singular, Vt = np.linalg.svd(A/scales, full_matrices=False)
    if len(singular) != A.shape[1] or singular[-1] <= rcond*singular[0]:
        raise ValueError('full position/nuisance tangent is rank deficient')
    condition = float(singular[0]/singular[-1])
    if condition > max_condition:
        raise ValueError('full position/nuisance tangent is ill-conditioned')
    influence = ((Vt.T/singular)@U.T*white[None, :])/scales[:, None]
    position_influence = influence[:2]
    ds = _array(item['shape_renderer'](p), (n, 3), 'source shape directions')
    dn = _array(item['neighbor_shape_design'], (n, q, 3), 'neighbor shape directions')
    shape_model = float(flux)*ds + np.einsum('nqj,q->nj', dn, nflux)
    physical_scales = np.asarray(DEFAULT_BOUNDS)
    shape_white = shape_model*white[:, None]*physical_scales[None, :]
    projected = shape_white-U@(U.T@shape_white)
    projected -= U@(U.T@projected)
    residual = _array(frame['residual'], (n,), 'saved residual')
    data = _array(item['data'], (n,), 'data')
    beta = _array(frame['background_coefficients'], (background.shape[1],), 'background coefficients')
    model = float(flux)*target + background@beta + neighbor@nflux
    if not np.allclose(data-model, residual, rtol=1e-8, atol=1e-11):
        raise ValueError('saved model/residual differs from reconstructed physical sample')
    rw = residual*white
    return {'position_pixel_influence': position_influence,
            'position_covariance_px2_nominal': (position_influence*error[None, :]**2)@position_influence.T,
            'position_shape_response': -position_influence@shape_model,
            'shape_model_derivative': shape_model,
            'shape_information_scaled': projected.T@projected,
            'shape_score_scaled': projected.T@rw,
            'shape_score_pixel_response': projected.T*white[None, :],
            'shape_parameter_scales': physical_scales,
            'shape_parameter_units': [str(v) for v in PARAMETER_UNITS],
            'condition': condition, 'rank': len(singular),
            'position_derivative_step_common_px': step,
            'qualification': 'fixed final robust weights and Gauss-Newton tangent only; full nonlinear/weight/selection/systematics uncertainty not calibrated'}
