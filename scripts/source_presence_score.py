"""Fixed-template scores under a specified diagonal-error model.

For whitened template p, data y, and full-rank nuisance matrix B, let
q = (I - BB+)p / ||(I - BB+)p||.  The signed score is q.T y.  The
orthogonal projection is computed with an SVD, without dropping columns.
These scores are not calibrated S/N, probabilities, or confidence measures.
"""
from dataclasses import dataclass, field
from collections.abc import Sequence
from numbers import Integral, Real

import astropy.units as u
import numpy as np
from scipy.stats import beta


RELATIVE_CUTOFF = 1e-10


def _quantity(value, name, unit=None):
    if not isinstance(value, u.Quantity):
        raise ValueError(f'{name} must be a Quantity')
    raw = np.asarray(value.value)
    if raw.dtype.kind not in 'iuf' or not np.isfinite(raw).all():
        raise ValueError(f'{name} must contain finite real values')
    try:
        result = np.asarray(value.to_value(unit or value.unit), dtype=float)
    except (u.UnitConversionError, TypeError, ValueError) as exc:
        raise ValueError(f'{name} has incompatible units') from exc
    if not np.isfinite(result).all():
        raise ValueError(f'{name} conversion is not finite')
    return result


def _unit_whitened(column, error):
    """Return unit whitened vector and its norm without squaring raw scale."""
    scale = float(np.max(np.abs(column)))
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('zero or invalid column')
    min_error = float(np.min(error))
    scaled = (column / scale) * (min_error / error)
    largest = float(np.max(np.abs(scaled)))
    if not np.isfinite(largest) or largest <= 0:
        raise ValueError('whitened column is numerically unrepresentable')
    scaled /= largest
    norm = float(np.linalg.norm(scaled))
    if not np.isfinite(norm) or norm <= 0:
        raise ValueError('invalid whitened column norm')
    # Compute the physical norm in logarithms to avoid intermediate overflow.
    log_norm = np.log(scale) - np.log(min_error) + np.log(largest) + np.log(norm)
    with np.errstate(over='ignore', under='ignore'):
        physical_norm = float(np.exp(log_norm))
    if not np.isfinite(physical_norm) or physical_norm <= 0:
        raise ValueError('whitened column norm is numerically unrepresentable')
    return scaled / norm, physical_norm


@dataclass(frozen=True)
class PresenceOperator:
    """Prepared fixed geometry; norms have units of inverse Jy."""
    provenance: str
    projected_template_norm: u.Quantity
    information_fraction: np.ndarray
    nuisance_rank: int
    nuisance_condition: float
    _directions: np.ndarray = field(repr=False)
    _error: np.ndarray = field(repr=False)
    _intensity_unit: u.UnitBase = field(repr=False)

    def score(self, data):
        """Compute one signed dimensionless score per predeclared template."""
        values = _quantity(data, 'data', self._intensity_unit)
        if values.shape != self._error.shape:
            raise ValueError('data shape must match error')
        with np.errstate(over='ignore', divide='ignore', invalid='ignore'):
            whitened = values / self._error
            result = self._directions @ whitened
        if not np.isfinite(result).all():
            raise ValueError('score is numerically unrepresentable')
        return result


def prepare_operator(templates, error, nuisance_columns, *, provenance):
    """Prepare K fixed templates and a full-rank, freely fitted nuisance span.

    The diagonal errors are assumed, not validated as a noise model.  Template
    norms are in 1/Jy; information fraction is the squared projected/unprojected
    norm ratio.  No detection threshold or positional search is supplied.
    """
    if not isinstance(provenance, str) or not provenance.strip():
        raise ValueError('nonempty provenance required')
    if not isinstance(error, u.Quantity):
        raise ValueError('error must be a Quantity')
    intensity = error.unit
    if not intensity.is_equivalent(u.MJy / u.sr):
        raise ValueError('error must have surface-brightness units')
    errors = _quantity(error, 'error')
    if errors.ndim != 1 or not errors.size or np.any(errors <= 0):
        raise ValueError('error must be a nonempty positive vector')
    sources = _quantity(templates, 'templates', intensity / u.Jy)
    if sources.ndim != 2 or sources.shape[1] != errors.size or not sources.shape[0]:
        raise ValueError('templates must have shape K by N')
    if isinstance(nuisance_columns, u.Quantity) or not isinstance(nuisance_columns, Sequence):
        raise ValueError('nuisance_columns must be a sequence of Quantities')
    cols = []
    for column in nuisance_columns:
        if not isinstance(column, u.Quantity):
            raise ValueError('nuisance column must be a Quantity')
        if column.unit.is_equivalent(intensity):
            values = _quantity(column, 'nuisance column', intensity)
        elif column.unit.is_equivalent(intensity / u.Jy):
            values = _quantity(column, 'nuisance column', intensity / u.Jy)
        else:
            raise ValueError('nuisance column has incompatible units')
        if values.shape != errors.shape:
            raise ValueError('nuisance column shape must match error')
        cols.append(_unit_whitened(values, errors)[0])
    if cols:
        basis, singular, _ = np.linalg.svd(np.column_stack(cols), full_matrices=False)
        if len(singular) != len(cols) or singular[-1] <= RELATIVE_CUTOFF * singular[0]:
            raise ValueError('nuisance columns are rank deficient')
        condition = float(singular[0] / singular[-1])
    else:
        basis = np.empty((errors.size, 0))
        condition = 1.0
    directions, norms, fractions = [], [], []
    for source in sources:
        direction, norm = _unit_whitened(source, errors)
        projected = direction - basis @ (basis.T @ direction)
        # Remove roundoff parallel to the nuisance span once more.
        projected -= basis @ (basis.T @ projected)
        fraction_norm = float(np.linalg.norm(projected))
        if not np.isfinite(fraction_norm) or fraction_norm <= RELATIVE_CUTOFF:
            raise ValueError('source template has insufficient projected norm')
        projected_norm = norm * fraction_norm
        if not np.isfinite(projected_norm) or projected_norm <= 0:
            raise ValueError('projected norm is numerically unrepresentable')
        directions.append(projected / fraction_norm)
        norms.append(projected_norm)
        fractions.append(fraction_norm ** 2)
    return PresenceOperator(provenance, np.asarray(norms) / u.Jy,
                            np.asarray(fractions), len(cols), condition,
                            np.asarray(directions), errors.copy(), intensity)


def paired_presence_statistic(scores):
    """Max over variants of min over seasons of max over K of positive score².

    Two before frames precede two after frames.  Positive-part squaring defines
    the one-sided alternative; it does not filter fitted positions or draws.
    """
    if isinstance(scores, u.Quantity):
        raise ValueError('scores must be unitless numeric values')
    a = np.asarray(scores)
    if a.dtype.kind not in 'iuf' or a.ndim != 3 or a.shape[1] != 4 or not a.shape[0] or not a.shape[2] or not np.isfinite(a).all():
        raise ValueError('scores must be a finite numeric V by 4 by K array')
    a = a.astype(float)
    with np.errstate(over='ignore', invalid='ignore'):
        squared = np.maximum(a, 0.) ** 2
        before = np.max(np.sum(squared[:, :2, :], axis=1), axis=1)
        after = np.max(np.sum(squared[:, 2:, :], axis=1), axis=1)
    if not np.isfinite(before).all() or not np.isfinite(after).all():
        raise ValueError('statistic is numerically unrepresentable')
    per_variant = np.minimum(before, after)
    return {'before': before, 'after': after, 'per_variant': per_variant,
            'combined': float(np.max(per_variant))}


def binomial_upper(k, n, confidence=.975):
    """Exact one-sided Clopper-Pearson upper bound; None for zero trials."""
    if any(isinstance(x, (bool, np.bool_)) or not isinstance(x, Integral) for x in (k, n)) or n < 0 or k < 0 or k > n:
        raise ValueError('require integer 0 <= k <= n')
    if isinstance(confidence, (bool, np.bool_)) or not isinstance(confidence, Real) or not np.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError('confidence must be between zero and one')
    if n == 0:
        return None
    return 1.0 if k == n else float(beta.ppf(confidence, k + 1, n - k))


def binomial_lower(k, n, confidence=.975):
    """Exact one-sided lower bound, with the same input validation as upper."""
    binomial_upper(k, n, confidence)  # validate original integers before subtraction
    upper_complement = binomial_upper(n - k, n, confidence)
    return None if upper_complement is None else float(1. - upper_complement)
