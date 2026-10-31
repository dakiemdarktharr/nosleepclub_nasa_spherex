"""Conditional heldout residual diagnostics for a joint translation frame.

Pure algebra on caller-supplied common-frame offsets and their full covariance.
No image loading, catalogue query, variance floor, or covariance fitting occurs.
"""
from dataclasses import dataclass

import astropy.units as u
import numpy as np
from scipy.linalg import solve_triangular

from .joint_reference_frame import _ids, _quantity, solve_joint_translation


@dataclass(frozen=True)
class ReferenceFrameDiagnostics:
    reference_frame: object
    calibration_indices: tuple
    heldout_indices: tuple
    residuals: u.Quantity
    covariance: u.Quantity
    residual_map: np.ndarray
    chi2: float
    dof: int
    marginal_mahalanobis2: np.ndarray
    provenance: str
    qualification: str


def _covariance(value, size, name, *, require_positive_definite):
    """Check symmetry and definiteness on a dimensionless relative scale.

    Zero-variance coordinates are allowed only for PSD inputs and must have
    exactly zero covariances; positive-definite matrices require positive diagonal.
    Small negative eigenvalues within roundoff tolerance are accepted only for
    the PSD input check. No eigenvalue is clipped or covariance floor added.
    """
    C = _quantity(value, u.pix**2, name)
    if C.shape != (size, size):
        raise ValueError(name + ' must have shape 2N x 2N')
    diagonal = np.diag(C)
    if np.any(diagonal < 0) or (require_positive_definite and np.any(diagonal <= 0)):
        raise ValueError(name + ' has invalid diagonal')
    nonzero = diagonal > 0
    if np.any(~nonzero) and (np.any(C[~nonzero, :] != 0) or np.any(C[:, ~nonzero] != 0)):
        raise ValueError(name + ' zero variance must have zero covariance')
    sub = C[np.ix_(nonzero, nonzero)]
    std = np.sqrt(diagonal[nonzero])
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        corr = (sub / std[:, None]) / std[None, :]
    if not np.isfinite(corr).all():
        raise ValueError(name + ' correlation is not finite')
    tolerance = 64*np.finfo(float).eps*max(1, size)*max(1., float(np.max(np.abs(corr))) if corr.size else 0.)
    if corr.size and np.max(np.abs(corr-corr.T)) > tolerance:
        raise ValueError(name + ' must be symmetric')
    corr = corr/2 + corr.T/2
    if require_positive_definite:
        try:
            chol = std[:, None] * np.linalg.cholesky(corr)
        except np.linalg.LinAlgError as exc:
            raise ValueError(name + ' must be positive definite') from exc
        if not np.isfinite(chol).all():
            raise ValueError(name + ' Cholesky factor is not finite')
    else:
        if corr.size:
            eigen = np.linalg.eigvalsh(corr)
            if not np.isfinite(eigen).all() or eigen[0] < -tolerance:
                raise ValueError(name + ' must be positive semidefinite')
        chol = None
    # Symmetrize only after testing the supplied matrix, without clipping.
    return C/2+C.T/2, chol


def analyze_reference_frame(offsets, covariance, source_ids, exposure_ids,
                            allowed_training_ids, planned_exposures, *, provenance,
                            min_references=4):
    """Fit calibration-only translations and propagate full heldout residuals.

    Offsets are N x 2 quantities in one common pixel frame; covariance is the
    full 2N x 2N matrix in pixel², in row-major x,y order. Every non-training
    source is held out. Rows must be unique by source/exposure, and each planned
    frame must have at least four distinct calibration sources. A positive
    semidefinite full input covariance is accepted only if both the calibration
    covariance and full heldout residual covariance are positive definite.
    Returned chi² values are nominal descriptive consistency diagnostics only.
    """
    if not isinstance(provenance, str) or not provenance.strip():
        raise ValueError('nonempty provenance is required')
    y = _quantity(offsets, u.pix, 'offsets')
    if y.ndim != 2 or y.shape[1] != 2 or not len(y):
        raise ValueError('offsets must be nonempty N x 2')
    n = len(y)
    sources = _ids(source_ids, 'source_ids')
    exposures = _ids(exposure_ids, 'exposure_ids')
    allowed = _ids(allowed_training_ids, 'allowed_training_ids')
    planned = _ids(planned_exposures, 'planned_exposures')
    if len(sources) != n or len(exposures) != n:
        raise ValueError('source and exposure IDs must match observations')
    if len(set(allowed)) != len(allowed) or len(set(planned)) != len(planned):
        raise ValueError('training and planned exposure IDs must be unique')
    if not set(exposures) <= set(planned):
        raise ValueError('observation contains an unplanned exposure')
    if len(set(zip(sources, exposures))) != n:
        raise ValueError('duplicate source/exposure observation')
    training = set(allowed)
    cal = tuple(i for i, source in enumerate(sources) if source in training)
    held = tuple(i for i, source in enumerate(sources) if source not in training)
    if not cal or not held:
        raise ValueError('calibration and heldout rows must both be nonempty')
    C, _ = _covariance(covariance, 2*n, 'input covariance', require_positive_definite=False)
    cal_xy = np.array([axis for i in cal for axis in (2*i, 2*i+1)])
    held_xy = np.array([axis for i in held for axis in (2*i, 2*i+1)])
    Ccal = C[np.ix_(cal_xy, cal_xy)]
    fit = solve_joint_translation(y[list(cal)]*u.pix, Ccal*u.pix**2,
                                  [sources[i] for i in cal], [exposures[i] for i in cal],
                                  allowed, planned, provenance=provenance,
                                  min_references=min_references)
    H = np.zeros((len(held_xy), 2*len(planned)))
    indices = {name: i for i, name in enumerate(planned)}
    for row, i in enumerate(held):
        j = indices[exposures[i]]
        H[2*row:2*row+2, 2*j:2*j+2] = np.eye(2)
    # This is S_h - H L S_c; it preserves negative cross terms as well as
    # covariances between heldout rows and across exposures.
    M = np.zeros((len(held_xy), 2*n))
    M[np.arange(len(held_xy)), held_xy] = 1.
    M[:, cal_xy] -= H @ fit.influence
    with np.errstate(over='ignore', invalid='ignore'):
        residual = M @ y.ravel()
        V = M @ C @ M.T
    if not np.isfinite(M).all() or not np.isfinite(residual).all() or not np.isfinite(V).all():
        raise ValueError('heldout propagation is numerically unrepresentable')
    V, chol = _covariance(V*u.pix**2, len(held_xy), 'heldout residual covariance', require_positive_definite=True)
    white = solve_triangular(chol, residual, lower=True)
    with np.errstate(over='ignore', invalid='ignore'):
        chi2 = float(white @ white)
    marginal = []
    for row in range(len(held)):
        block = V[2*row:2*row+2, 2*row:2*row+2]
        try:
            factor = np.linalg.cholesky(block)
            z = solve_triangular(factor, residual[2*row:2*row+2], lower=True)
            marginal.append(float(z @ z))
        except np.linalg.LinAlgError as exc:
            raise ValueError('heldout marginal covariance must be positive definite') from exc
    marginal = np.asarray(marginal)
    if not np.isfinite(chi2) or not np.isfinite(marginal).all():
        raise ValueError('heldout diagnostics are numerically unrepresentable')
    return ReferenceFrameDiagnostics(
        reference_frame=fit, calibration_indices=cal, heldout_indices=held,
        residuals=residual.reshape(-1, 2)*u.pix, covariance=V*u.pix**2,
        residual_map=M, chi2=chi2, dof=len(held_xy),
        marginal_mahalanobis2=marginal, provenance=provenance,
        qualification=('Nominal descriptive consistency conditional on fixed supplied inputs, weights, '
                       'catalogue and legacy geometry; no calibrated coverage, physical-systematics '
                       'guarantee, scientific improvement or astronomical detection is established.'))
