"""Full-covariance joint reference-frame translations, in common-frame pixels.

For observation i of exposure e(i), y_i = delta_e(i) + error_i.  Rows are
ordered x,y for each observation, and the supplied covariance covers *all*
rows, including any cross-exposure/source terms constructed by the caller.
The returned formal covariance is conditional on that supplied matrix: this
module does not estimate covariance, calibrate coverage, or validate the sky.
"""
from dataclasses import dataclass
from numbers import Integral, Real

import astropy.units as u
import numpy as np
from scipy.linalg import solve_triangular


@dataclass(frozen=True)
class JointReferenceFrame:
    exposure_ids: tuple
    offsets: u.Quantity
    covariance: u.Quantity
    influence: np.ndarray
    residuals: u.Quantity
    chi2: float
    dof: int
    condition: float
    rank: int
    reference_counts: tuple
    provenance: str
    qualification: str


def _quantity(value, unit, name):
    if not isinstance(value, u.Quantity):
        raise ValueError(name + ' must be an explicit Quantity')
    raw = np.asarray(value.value)
    if raw.dtype.kind not in 'iuf' or not np.isfinite(raw).all():
        raise ValueError(name + ' must have finite real values')
    try:
        result = np.asarray(value.to_value(unit), dtype=float)
    except (u.UnitConversionError, ValueError, TypeError) as exc:
        raise ValueError(name + ' has incompatible units') from exc
    if not np.isfinite(result).all():
        raise ValueError(name + ' conversion is not finite')
    return result


def _ids(values, name):
    if isinstance(values, (str, bytes)):
        raise ValueError(name + ' must be a sequence of IDs')
    try:
        ids = tuple(values)
    except TypeError as exc:
        raise ValueError(name + ' must be a sequence of IDs') from exc
    if not ids or any(not isinstance(x, str) or not x.strip() for x in ids):
        raise ValueError(name + ' must contain nonempty string IDs')
    return ids


def solve_joint_translation(offsets, covariance, source_ids, exposure_ids,
                            allowed_source_ids, planned_exposures, *, provenance,
                            min_references=4, max_condition=1e8, rcond=1e-10):
    """Solve all declared translations by Cholesky-whitened full GLS.

    ``offsets`` is N x 2 pixel Quantity in ONE declared common coordinate frame;
    ``covariance`` is 2N x 2N pixel²
    Quantity. ``source_ids`` and ``exposure_ids`` identify each row, while
    ``planned_exposures`` determines output order. Only allowed calibration IDs
    are accepted, each observation pair is unique, and every planned exposure
    requires at least four distinct references. The covariance must be strictly
    positive definite; there is no pseudoinverse, floor, or chi² inflation.
    ``influence`` maps the flattened x,y input offsets to flattened output
    translations in the same pixel units.
    """
    if not isinstance(provenance, str) or not provenance.strip():
        raise ValueError('nonempty provenance is required')
    if (isinstance(min_references, (bool, np.bool_)) or not isinstance(min_references, Integral)
            or min_references < 4):
        raise ValueError('minimum reference count must be an integer >= 4')
    for value, name in ((max_condition, 'max_condition'), (rcond, 'rcond')):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) or not np.isfinite(value):
            raise ValueError(name + ' must be finite')
    if max_condition <= 1 or not 0 < rcond < 1:
        raise ValueError('invalid condition or rank threshold')
    y = _quantity(offsets, u.pix, 'offsets')
    if y.ndim != 2 or y.shape[1] != 2 or not y.shape[0]:
        raise ValueError('offsets must be a nonempty N x 2 array')
    n = len(y)
    sources = _ids(source_ids, 'source_ids'); exposures = _ids(exposure_ids, 'exposure_ids')
    allowed = _ids(allowed_source_ids, 'allowed_source_ids'); planned = _ids(planned_exposures, 'planned_exposures')
    if len(sources) != n or len(exposures) != n:
        raise ValueError('source and exposure IDs must match observations')
    if len(set(allowed)) != len(allowed) or len(set(planned)) != len(planned):
        raise ValueError('allowed IDs and planned exposure IDs must be unique')
    if not set(sources) <= set(allowed):
        raise ValueError('observation contains a non-calibration source')
    if not set(exposures) <= set(planned):
        raise ValueError('observation contains an unplanned exposure')
    if len(set(zip(sources, exposures))) != n:
        raise ValueError('duplicate source/exposure observation')
    counts = tuple(sum(exp == name for exp in exposures) for name in planned)
    if any(count < min_references for count in counts):
        raise ValueError('missing planned exposure or too few distinct references')
    C = _quantity(covariance, u.pix**2, 'covariance')
    size = 2*n
    if C.shape != (size, size):
        raise ValueError('covariance must have shape 2N x 2N')
    diag = np.diag(C)
    if np.any(diag <= 0):
        raise ValueError('covariance diagonal must be positive')
    std = np.sqrt(diag)
    with np.errstate(over='ignore', divide='ignore', invalid='ignore'):
        corr = (C / std[:, None]) / std[None, :]
    if not np.isfinite(corr).all():
        raise ValueError('covariance correlation must be finite')
    tolerance = 64 * np.finfo(float).eps * size * float(np.max(np.abs(corr)))
    if np.max(np.abs(corr-corr.T)) > tolerance:
        raise ValueError('covariance must be symmetric')
    corr = (corr + corr.T) * .5
    try:
        chol = std[:, None] * np.linalg.cholesky(corr)
    except np.linalg.LinAlgError as exc:
        raise ValueError('covariance must be positive definite') from exc
    H = np.zeros((size, 2*len(planned)))
    index = {name: i for i, name in enumerate(planned)}
    for i, exposure in enumerate(exposures):
        j = index[exposure]
        H[2*i:2*i+2, 2*j:2*j+2] = np.eye(2)
    A = solve_triangular(chol, H, lower=True)
    scales = np.linalg.norm(A, axis=0)
    if not np.isfinite(scales).all() or np.any(scales <= 0):
        raise ValueError('invalid design column scale')
    U, singular, Vt = np.linalg.svd(A/scales, full_matrices=False)
    if (len(singular) != H.shape[1] or not np.isfinite(singular).all()
            or singular[-1] <= rcond * singular[0]):
        raise ValueError('joint translation design is rank deficient')
    condition = float(singular[0]/singular[-1])
    if condition > max_condition:
        raise ValueError('joint translation design is ill-conditioned')
    # The normalized SVD is inverted only after strict full-rank checks.
    gain = ((Vt.T/singular) @ U.T @ solve_triangular(chol, np.eye(size), lower=True)) / scales[:, None]
    beta = gain @ y.ravel()
    parameter_covariance = ((Vt.T/singular**2) @ Vt) / np.outer(scales, scales)
    residual = y.ravel() - H @ beta
    white_residual = solve_triangular(chol, residual, lower=True)
    chi2 = float(white_residual @ white_residual)
    if not np.isfinite(beta).all() or not np.isfinite(parameter_covariance).all() or not np.isfinite(chi2):
        raise ValueError('joint solution is numerically unrepresentable')
    return JointReferenceFrame(exposure_ids=planned, offsets=beta.reshape(-1, 2)*u.pix,
        covariance=parameter_covariance*u.pix**2, influence=gain, residuals=residual.reshape(-1, 2)*u.pix,
        chi2=chi2, dof=size-H.shape[1], condition=condition, rank=len(singular), reference_counts=counts,
        provenance=provenance,
        qualification='Formal nominal GLS conditional on the full supplied covariance; no covariance or coverage calibration, physical-systematics guarantee, or detection claim.')
