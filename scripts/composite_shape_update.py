"""One fixed-tangent global shape update, not a nonlinear PSF likelihood fit."""
from dataclasses import dataclass
from numbers import Integral, Real

import numpy as np

from .moment_preserving_epsf import DEFAULT_BOUNDS
from .shared_pixel_covariance import add_pixel_response, finite


@dataclass(frozen=True)
class ShapeUpdate:
    values: np.ndarray
    covariance: np.ndarray
    pixel_influence: np.ndarray
    scaled_information: np.ndarray
    condition: float
    max_source_information_fraction: float
    sources: tuple
    source_fractions: dict
    qualification: str


def information(cells, *, min_sources=8, max_condition=100., rcond=1e-10):
    if isinstance(min_sources, (bool, np.bool_)) or not isinstance(min_sources, Integral) or min_sources < 3:
        raise ValueError('at least three declared calibration sources required')
    if (any(isinstance(v, (bool, np.bool_)) or not isinstance(v, Real) or not np.isfinite(v)
            for v in (max_condition, rcond)) or max_condition <= 1 or not 0 < rcond < 1):
        raise ValueError('invalid shape rank/condition thresholds')
    if not cells:
        raise ValueError('unique nonempty calibration source/exposure cells required')
    for cell in cells:
        if (not isinstance(cell.get('source_id'), str) or not cell['source_id']
                or not isinstance(cell.get('obs_id'), str) or not cell['obs_id']
                or not isinstance(cell.get('key'), (list, tuple))
                or tuple(cell['key']) != (cell['source_id'], cell['obs_id'])):
            raise ValueError('calibration key must equal its source/exposure identity')
    if len({tuple(c['key']) for c in cells}) != len(cells):
        raise ValueError('unique nonempty calibration source/exposure cells required')
    by_source = {}
    for cell in cells:
        source = cell['source_id'];F = finite(cell['shape_information_scaled'], (3, 3), 'shape information')
        if not isinstance(source, str) or not source:
            raise ValueError('source ID required')
        scale = float(np.max(np.abs(F)))
        if not np.allclose(F, F.T, rtol=0., atol=1e-12*scale):
            raise ValueError('asymmetric shape information')
        eigen_cell = np.linalg.eigvalsh((F+F.T)/2)
        if eigen_cell[0] < -1e-12*scale:
            raise ValueError('cell shape information is not positive semidefinite')
        by_source[source] = by_source.get(source, np.zeros((3, 3)))+F
    F = sum(by_source.values(), np.zeros((3, 3)));diag = np.sqrt(np.diag(F))
    if not np.isfinite(diag).all() or np.any(diag <= 0):
        raise ValueError('one or more physical shape directions have no information')
    normalized = F/diag[:, None]/diag[None, :]
    eigen = np.linalg.eigvalsh((normalized+normalized.T)/2)
    if eigen[0] <= rcond**2*eigen[-1] or eigen[-1]/eigen[0] > max_condition**2:
        raise ValueError('three-vector shape information is deficient or ill-conditioned')
    chol = np.linalg.cholesky(F)
    fractions = {}
    for source, Fs in by_source.items():
        whitened = np.linalg.solve(chol, np.linalg.solve(chol, Fs).T).T
        fractions[source] = float(np.max(np.linalg.eigvalsh((whitened+whitened.T)/2)))
    active_sources = tuple(sorted(source for source, Fs in by_source.items() if np.trace(Fs) > 0))
    if len(active_sources) < min_sources:
        raise ValueError('too few calibration sources for global shape')
    return {'matrix': F, 'condition': float(np.sqrt(eigen[-1]/eigen[0])),
            'sources': active_sources, 'source_fractions': fractions,
            'max_source_fraction': max(fractions.values())}


def solve_update(cells, registry, *, min_sources=8, max_source_fraction=.35,
                 max_condition=100., maximum_scaled_sigma=.5):
    """Estimate the entire three-vector once, with overlap-aware nominal errors.

    Duplicate physical pixels count once in noise propagation. A failed guard
    rejects the whole candidate; there is no rank reduction, clipping, zero
    fallback or search among shape families.
    """
    if (any(isinstance(v, (bool, np.bool_)) or not isinstance(v, Real) or not np.isfinite(v)
            for v in (max_source_fraction, maximum_scaled_sigma))
            or not 0 < max_source_fraction <= 1 or maximum_scaled_sigma <= 0):
        raise ValueError('invalid source dominance or precision thresholds')
    info = information(cells, min_sources=min_sources, max_condition=max_condition)
    if info['max_source_fraction'] > max_source_fraction:
        raise ValueError('one calibration source dominates a shape direction')
    F = info['matrix']
    score = sum((finite(c['shape_score_scaled'], (3,), 'shape score') for c in cells), np.zeros(3))
    response = add_pixel_response(registry, cells, response_key='shape_score_pixel_response', output_rows=3)
    Gscaled = np.linalg.solve(F, response)
    variance = (Gscaled*registry.variance[None, :])@Gscaled.T
    scaled = np.linalg.solve(F, score)
    if not np.isfinite(scaled).all() or np.any(np.abs(scaled) > 1.):
        raise ValueError('unconstrained shape update hits physical parameter bounds')
    if np.any(np.sqrt(np.diag(variance)) > maximum_scaled_sigma):
        raise ValueError('nominal shape precision insufficient at declared physical scale')
    scales = np.asarray(DEFAULT_BOUNDS)
    return ShapeUpdate(values=scaled*scales, covariance=variance*scales[:, None]*scales[None, :],
                       pixel_influence=Gscaled*scales[:, None], scaled_information=F,
                       condition=info['condition'], max_source_information_fraction=info['max_source_fraction'],
                       sources=info['sources'], source_fractions=info['source_fractions'],
                       qualification='single Gauss-Newton composite score at opened baseline points and fixed robust weights; covariance propagates declared shared pixels only, not full estimator/model uncertainty')
