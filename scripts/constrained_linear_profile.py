"""Fixed-design weighted least squares with selected nonnegative amplitudes.

The caller declares the numerical units and the physical meaning of each
column. Only columns in ``nonnegative_design`` are constrained; these must be
the actual physical amplitudes, not arbitrary rotations or SVD basis vectors.
Free columns, including a target flux, remain signed. This primitive does not
provide covariance, confidence intervals, detection probabilities or SNR.
"""

import numpy as np
from astropy import units as u
from scipy.optimize import nnls


RCOND = 1e-10
KKT_TOLERANCE = 1e-8


def _array(value, name, ndim):
    if isinstance(value,u.Quantity):raise ValueError(name+' must be numeric in caller-declared units')
    a = np.asarray(value)
    if a.ndim != ndim or a.dtype.kind not in 'iuf':
        raise ValueError(name+' must be a real numeric array')
    a = np.asarray(a, dtype=float)
    if not np.isfinite(a).all():
        raise ValueError(name+' must be finite')
    return a


def _normalized_columns(matrix):
    """Scale before taking norms, preventing avoidable under/overflow."""
    if not matrix.shape[1]:
        return matrix.copy(), np.empty(0)
    maximum = np.max(np.abs(matrix), axis=0)
    if not np.isfinite(maximum).all() or np.any(maximum == 0):
        raise ValueError('design has a zero or invalid column')
    scaled = matrix/maximum
    norm = np.linalg.norm(scaled, axis=0)
    with np.errstate(over='ignore', under='ignore', invalid='ignore'):
        physical_norm = maximum*norm
    if not np.isfinite(physical_norm).all() or np.any(physical_norm <= 0):
        raise ValueError('column normalization outside numerical range')
    return scaled/norm, physical_norm


def profile_linear(data, error, free_design, nonnegative_design, weights=None):
    """Profile a mixed free/nonnegative linear model using diagonal errors.

    ``data`` and ``error`` are 1D numeric arrays; both designs are (n,p)/(n,q)
    numeric arrays, including shape (n,0) when empty. Optional weights are
    finite numbers in (0,1], applied to the squared standardized residuals.
    Columns and coefficients use caller-defined units. Full column rank and a
    1e-10 minimum relative singular value after column scaling are required.
    Free coefficients are never clipped, even when negative. The result records
    scaled first-order optimality diagnostics, not an uncertainty estimate.
    """
    y = _array(data, 'data', 1)
    e = _array(error, 'error', 1)
    free = _array(free_design, 'free_design', 2)
    constrained = _array(nonnegative_design, 'nonnegative_design', 2)
    if not len(y) or e.shape != y.shape or np.any(e <= 0) or free.shape[0] != len(y) or constrained.shape[0] != len(y):
        raise ValueError('incompatible shapes or nonpositive error')
    weight = np.ones_like(y) if weights is None else _array(weights, 'weights', 1)
    if weight.shape != y.shape or np.any(weight <= 0) or np.any(weight > 1):
        raise ValueError('weights must match data and lie in (0,1]')
    p, q = free.shape[1], constrained.shape[1]
    if p+q > len(y):
        raise ValueError('design has more columns than observations')
    with np.errstate(over='ignore', under='ignore', invalid='ignore', divide='ignore'):
        whiten = np.sqrt(weight)/e
        wy = y*whiten
        design = np.column_stack((free, constrained))*whiten[:, None]
    if not np.isfinite(whiten).all() or np.any(whiten<=0) or not np.isfinite(wy).all() or not np.isfinite(design).all():
        raise ValueError('whitened inputs outside numerical range')
    if np.any((y!=0)&(wy==0)) or np.any((np.column_stack((free,constrained))!=0)&(design==0)):
        raise ValueError('whitened inputs underflow')
    X, norms = _normalized_columns(design)
    if p+q:
        try:
            singular = np.linalg.svd(X, compute_uv=False)
        except np.linalg.LinAlgError as exc:
            raise ValueError('design SVD failed') from exc
        if len(singular)!=p+q or not np.isfinite(singular).all() or singular[-1] <= RCOND*singular[0]:
            raise ValueError('design rank deficient or poorly conditioned')
        condition = float(singular[0]/singular[-1])
    else:
        condition = None
    if p:
        try:
            U, s, Vh = np.linalg.svd(X[:, :p], full_matrices=False)
        except np.linalg.LinAlgError as exc:
            raise ValueError('free design SVD failed') from exc
        if len(s)!=p or s[-1] <= RCOND*s[0]:
            raise ValueError('free design rank deficient or poorly conditioned')
    else:
        U=np.empty((len(y),0));s=np.empty(0);Vh=np.empty((0,0))
    N=X[:, p:]
    projected_y=wy-U@(U.T@wy)
    projected_N=N-U@(U.T@N)
    data_scale=float(np.max(np.abs(wy)))
    theta_neighbors=np.zeros(q)
    if q and data_scale:
        projected_unit, projected_norms = _normalized_columns(projected_N)
        try:
            # Scale both the right side and projected columns; scipy returns
            # exact zero at the active bound, not a clipped signed solution.
            alpha, _ = nnls(projected_unit, projected_y/data_scale)
        except (RuntimeError, ValueError, np.linalg.LinAlgError) as exc:
            raise ValueError('NNLS failed') from exc
        with np.errstate(over='ignore', under='ignore', invalid='ignore', divide='ignore'):
            theta_neighbors=(alpha/projected_norms)*data_scale
        if not np.isfinite(theta_neighbors).all() or np.any((alpha>0)&(theta_neighbors==0)):
            raise ValueError('neighbor solution outside numerical range')
    rhs=wy-N@theta_neighbors
    theta_free=Vh.T@((U.T@rhs)/s) if p else np.empty(0)
    theta=np.r_[theta_free,theta_neighbors]
    with np.errstate(over='ignore', under='ignore', invalid='ignore', divide='ignore'):
        coefficients=theta/norms
    if (not np.isfinite(coefficients).all() or np.any((theta!=0)&(coefficients==0))
            or np.any(coefficients[p:]<0)):
        raise ValueError('coefficients outside numerical range')
    with np.errstate(over='ignore', under='ignore', invalid='ignore'):
        predicted=free@coefficients[:p]+constrained@coefficients[p:]
        residual=y-predicted
        weighted_residual=residual*whiten
    if not np.isfinite(predicted).all() or not np.isfinite(residual).all() or not np.isfinite(weighted_residual).all():
        raise ValueError('model or residual outside numerical range')
    chi2=float(weighted_residual@weighted_residual)
    if not np.isfinite(chi2):raise ValueError('chi-square outside numerical range')
    # Residual is data-model, so a bound column's gradient X^T r must be <= 0.
    # Divide by max|whitened data| for unit- and positive column-scale invariance.
    residual_scale=weighted_residual/data_scale if data_scale else weighted_residual
    gradient=X.T@residual_scale
    active=theta_neighbors==0
    free_violation=float(np.max(np.abs(gradient[:p]))) if p else 0.
    bound_violation=float(np.max(np.maximum(gradient[p:][active],0.))) if np.any(active) else 0.
    interior_violation=float(np.max(np.abs(gradient[p:][~active]))) if np.any(~active) else 0.
    neighbor_scale=max(data_scale,float(np.max(theta_neighbors)) if q else 0.)
    complementarity=float(np.max(np.abs((theta_neighbors/neighbor_scale)*gradient[p:]))) if q and neighbor_scale else 0.
    if not np.isfinite(gradient).all() or max(free_violation,bound_violation,interior_violation,complementarity)>KKT_TOLERANCE:
        raise ValueError('NNLS KKT check failed')
    return {'free_coefficients':coefficients[:p], 'nonnegative_coefficients':coefficients[p:],
            'model':predicted,'residual':residual,'weighted_residual':weighted_residual,
            'chi2':chi2,'active_mask':active,'rank':p+q,'scaled_condition':condition,
            'column_norms':norms,'scaled_gradient_free':gradient[:p],
            'scaled_gradient_nonnegative':gradient[p:],
            'scaled_free_stationarity_violation':free_violation,
            'scaled_bound_dual_violation':bound_violation,
            'scaled_interior_stationarity_violation':interior_violation,
            'scaled_complementarity_violation':complementarity,
            'gradient_convention':'column-normalized X.T @ weighted(data-model) / max(abs(weighted data))',
            'kkt_tolerance':KKT_TOLERANCE}
