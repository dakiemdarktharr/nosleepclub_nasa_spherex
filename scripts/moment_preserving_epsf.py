"""Three global native ePSF shape directions with fixed flux/centroid gauge.

This is a numerical correction family, not a calibrated instrument PSF. The
full finite native lattice, including outside-image pixels, defines every
normalization and moment. Selection happens only after those constraints.
"""
from dataclasses import dataclass
from numbers import Integral, Real

import astropy.units as u
import numpy as np
from scipy.ndimage import map_coordinates, spline_filter

from .native_flux_template import EPSF_SHAPE, PAD_OVERSAMPLED


PARAMETER_NAMES = ('width', 'skew_x', 'skew_y')
PARAMETER_UNITS = (u.pix**2, u.pix**3, u.pix**3)
DEFAULT_BOUNDS = (.04, .003, .003)
DELTA = .2
DERIVATIVE_STEP = .002
RCOND = 1e-10
MAX_CONDITION = 1e8
MOMENT_TOLERANCE = 1e-10
PEAK_CHANGE_LIMIT = .05
NEGATIVE_WING_LIMIT = .01


def numeric_parameters(parameters, bounds=DEFAULT_BOUNDS):
    if not isinstance(parameters, (tuple, list)) or len(parameters) != 3:
        raise ValueError('three scalar physical shape parameters required')
    if isinstance(bounds, (str, bytes, u.Quantity)):
        raise ValueError('three positive numeric bounds in declared parameter units required')
    try:
        bounds = tuple(bounds)
    except TypeError as exc:
        raise ValueError('three positive numeric bounds required') from exc
    if (len(bounds) != 3 or any(isinstance(v, (bool, np.bool_)) or not isinstance(v, Real)
                              or not np.isfinite(v) or v <= 0 for v in bounds)):
        raise ValueError('three positive finite numeric bounds required')
    values = []
    for value, unit, bound in zip(parameters, PARAMETER_UNITS, bounds):
        if not isinstance(value, u.Quantity) or np.asarray(value.value).dtype.kind not in 'iuf':
            raise ValueError('shape parameters must be physical real Quantities')
        try:
            number = np.asarray(value.to_value(unit))
        except (u.UnitConversionError, ValueError, TypeError) as exc:
            raise ValueError('incompatible shape parameter units') from exc
        if number.shape or not np.isfinite(number) or abs(float(number)) > bound:
            raise ValueError('shape parameter outside declared bounds')
        values.append(float(number))
    return np.asarray(values)


def physical_parameters(values):
    if isinstance(values, u.Quantity) or any(isinstance(v, (bool, np.bool_))
                                            for v in np.asarray(values, dtype=object).ravel()):
        raise ValueError('numeric coefficients cannot contain units or booleans')
    values = np.asarray(values)
    if values.shape != (3,) or values.dtype.kind not in 'iuf' or not np.isfinite(values).all():
        raise ValueError('three finite numeric coefficients required')
    return tuple(float(value)*unit for value, unit in zip(values, PARAMETER_UNITS))


def _position(value):
    if isinstance(value, u.Quantity):
        raise ValueError('position must be numeric in declared native pixels')
    if any(isinstance(v, (bool, np.bool_)) for v in np.asarray(value, dtype=object).ravel()):
        raise ValueError('position cannot contain booleans')
    result = np.asarray(value)
    if result.shape != (2,) or result.dtype.kind not in 'iuf' or not np.isfinite(result).all():
        raise ValueError('finite native x,y position required')
    if np.any(np.abs(result) > 2**40):
        raise ValueError('native coordinate is outside exactly resolved lattice range')
    return result.astype(float)


@dataclass(frozen=True)
class MomentBasis:
    lattice_x: np.ndarray
    lattice_y: np.ndarray
    baseline: np.ndarray
    directions: np.ndarray
    condition: float
    moment_relative_residual: np.ndarray
    baseline_first_moment_native: np.ndarray
    normalization_before: float


@dataclass(frozen=True)
class CorrectedTemplate:
    x: np.ndarray
    y: np.ndarray
    template_per_jy: u.Quantity
    normalized_selected: np.ndarray
    selected_shape_directions: np.ndarray
    lattice_x: np.ndarray
    lattice_y: np.ndarray
    normalized_lattice: np.ndarray
    metadata: dict


class MomentPreservingEPSF:
    """Reusable padded spline; width, odd-x and odd-y coefficients are global.

    The isotropic direction is (mean of four delta-shifts minus P)/delta².
    Each odd direction is a centered third source-position difference /delta³.
    All three have their discrete sum and x/y first moments removed explicitly.
    """
    def __init__(self, epsf, *, oversampling=5, provenance):
        if not isinstance(provenance, str) or not provenance.strip():
            raise ValueError('ePSF provenance required')
        if isinstance(oversampling, (bool, np.bool_)) or not isinstance(oversampling, Integral) or oversampling != 5:
            raise ValueError('only the declared 5x native ePSF family is supported')
        raw = np.asarray(epsf)
        if raw.shape != EPSF_SHAPE or raw.dtype.kind not in 'iuf' or not np.isfinite(raw).all():
            raise ValueError('finite real 33x33 ePSF required')
        raw = raw.astype(float);total = float(raw.sum());absolute = float(np.abs(raw).sum())
        if not np.isfinite([total, absolute]).all() or total <= 64*np.finfo(float).eps*absolute:
            raise ValueError('positive stable signed ePSF integral required')
        self.oversampling = int(oversampling)
        self.provenance = provenance
        self.coefficients = spline_filter(np.pad(raw/total*oversampling**2, PAD_OVERSAMPLED), order=3)
        if not np.isfinite(self.coefficients).all():
            raise ValueError('nonfinite spline coefficients')
        self.coefficients.setflags(write=False)
        self.center = (self.coefficients.shape[0]-1)/2
        self.radius = self.center/oversampling
        self.normalization_scale = max(1., absolute/total)

    def _sample(self, position, X, Y):
        values = map_coordinates(self.coefficients,
            [(Y-position[1])*self.oversampling+self.center,
             (X-position[0])*self.oversampling+self.center],
            order=3, mode='constant', cval=0., prefilter=False)
        total = float(values.sum());absolute = float(np.abs(values).sum())
        if (not np.isfinite(values).all() or not np.isfinite(total)
                or total <= 64*np.finfo(float).eps*max(absolute, self.normalization_scale)):
            raise ValueError('invalid full native lattice integral')
        return values/total, total

    def basis(self, source_xy):
        position = _position(source_xy)
        radius = self.radius + max(2*DELTA, DERIVATIVE_STEP)
        x = np.arange(int(np.floor(position[0]-radius)), int(np.ceil(position[0]+radius))+1)
        y = np.arange(int(np.floor(position[1]-radius)), int(np.ceil(position[1]+radius))+1)
        X, Y = np.meshgrid(x, y)
        baseline, integral = self._sample(position, X, Y)
        shifted = {}
        for axis in range(2):
            for multiplier in (-2, -1, 1, 2):
                offset = np.zeros(2);offset[axis] = multiplier*DELTA
                shifted[(axis, multiplier)] = self._sample(position+offset, X, Y)[0]
        width = (sum(shifted[(axis, direction)] for axis in range(2) for direction in (-1, 1))/4-baseline)/DELTA**2
        odd = [(shifted[(axis, 2)]-2*shifted[(axis, 1)]+2*shifted[(axis, -1)]-shifted[(axis, -2)])/(2*DELTA**3)
               for axis in range(2)]
        raw = np.stack((width, *odd), axis=-1)
        derivatives = []
        for axis in range(2):
            offset = np.zeros(2);offset[axis] = DERIVATIVE_STEP
            derivatives.append((self._sample(position+offset, X, Y)[0]
                                - self._sample(position-offset, X, Y)[0])/(2*DERIVATIVE_STEP))
        nuisance = np.stack((baseline, *derivatives), axis=-1).reshape(-1, 3)
        # Dimensionless row scaling prevents a coordinate convention from
        # deciding numerical rank. Column scaling retains all three moments.
        moment = np.vstack((np.ones(X.size), (X-position[0]).ravel()/radius,
                            (Y-position[1]).ravel()/radius))
        matrix = moment @ nuisance
        scales = np.linalg.norm(matrix, axis=0)
        if not np.isfinite(scales).all() or np.any(scales <= 0):
            raise ValueError('invalid moment-system column scale')
        scaled = matrix/scales
        singular = np.linalg.svd(scaled, compute_uv=False)
        if singular[-1] <= RCOND*singular[0] or singular[0]/singular[-1] > MAX_CONDITION:
            raise ValueError('deficient or ill-conditioned moment system')
        raw_vectors = raw.reshape(-1, 3)
        coefficients = np.linalg.solve(scaled, moment@raw_vectors)/scales[:, None]
        removed = nuisance@coefficients
        corrected = raw_vectors-removed
        denominator = np.abs(moment)@(np.abs(raw_vectors)+np.abs(removed))
        denominator = np.maximum(denominator, np.finfo(float).eps)
        relative = np.abs(moment@corrected)/denominator
        if not np.isfinite(corrected).all() or np.any(relative > MOMENT_TOLERANCE):
            raise ValueError('full-lattice moment constraint failed')
        first = np.array([np.sum((X-position[0])*baseline), np.sum((Y-position[1])*baseline)])
        return MomentBasis(x, y, baseline, corrected.reshape(*baseline.shape, 3),
                           float(singular[0]/singular[-1]), relative, first, integral)

    def render(self, source_xy, selection_mask, *, source_omega, parameters,
               source_omega_provenance):
        position = _position(source_xy);mask = np.asarray(selection_mask)
        if mask.ndim != 2 or mask.dtype.kind != 'b' or not mask.size or not mask.any():
            raise ValueError('nonempty native selection mask required')
        if not 0 <= position[0] <= mask.shape[1]-1 or not 0 <= position[1] <= mask.shape[0]-1:
            raise ValueError('source outside image')
        if not isinstance(source_omega_provenance, str) or not source_omega_provenance.strip():
            raise ValueError('solid-angle provenance required')
        if not isinstance(source_omega, u.Quantity) or np.asarray(source_omega.value).dtype.kind not in 'iuf':
            raise ValueError('solid angle must be an explicit real Quantity')
        try:
            omega = np.asarray(source_omega.to_value(u.sr))
        except (ValueError, TypeError, u.UnitConversionError) as exc:
            raise ValueError('invalid solid-angle units') from exc
        if omega.shape or not np.isfinite(omega) or omega <= 0:
            raise ValueError('solid angle must be positive finite scalar')
        values = numeric_parameters(parameters);basis = self.basis(position)
        correction = basis.directions@values
        peak = float(np.max(np.abs(basis.baseline)))
        if peak <= 0:
            raise ValueError('empty baseline')
        corrected = basis.baseline+correction
        peak_change = float(np.max(np.abs(correction))/peak)
        wing_change = float(max(0., basis.baseline.min()-corrected.min())/peak)
        if peak_change > PEAK_CHANGE_LIMIT+1e-12 or wing_change > NEGATIVE_WING_LIMIT+1e-12:
            raise ValueError('shape correction exceeds full-lattice physical guard')
        if not np.isclose(corrected.sum(), 1., rtol=1e-12, atol=0.):
            raise ValueError('corrected full-lattice flux changed')
        yy, xx = np.nonzero(mask)
        inside = ((xx >= basis.lattice_x[0]) & (xx <= basis.lattice_x[-1])
                  & (yy >= basis.lattice_y[0]) & (yy <= basis.lattice_y[-1]))
        selected = np.zeros(len(xx));selected_directions = np.zeros((len(xx), 3))
        ix = xx[inside]-basis.lattice_x[0];iy = yy[inside]-basis.lattice_y[0]
        selected[inside] = corrected[iy, ix]
        selected_directions[inside] = basis.directions[iy, ix]
        if not np.any(selected != 0):
            raise ValueError('selection has no nonzero source support')
        X, Y = np.meshgrid(basis.lattice_x, basis.lattice_y)
        outside = (X < 0) | (Y < 0) | (X >= mask.shape[1]) | (Y >= mask.shape[0])
        metadata = {'parameters': values.tolist(), 'parameter_units': [str(v) for v in PARAMETER_UNITS],
                    'parameter_names': list(PARAMETER_NAMES), 'delta_native_px': DELTA,
                    'derivative_step_native_px': DERIVATIVE_STEP,
                    'moment_condition': basis.condition,
                    'moment_relative_residual': basis.moment_relative_residual.tolist(),
                    'baseline_first_moment_native_px': basis.baseline_first_moment_native.tolist(),
                    'full_lattice_flux': float(corrected.sum()), 'signed_selected_fraction': float(selected.sum()),
                    'peak_change_fraction': peak_change, 'negative_wing_change_fraction': wing_change,
                    'support_truncated_by_image': bool(np.any(outside & (corrected != 0))),
                    'source_omega_sr': float(omega), 'source_omega_provenance': source_omega_provenance,
                    'epsf_provenance': self.provenance,
                    'qualification': 'preserves baseline finite-lattice flux and first moment; not calibrated instrument shape, center or masked flux'}
        return CorrectedTemplate(xx, yy, selected/(1e6*float(omega))*(u.MJy/u.sr/u.Jy), selected,
                                 selected_directions, basis.lattice_x, basis.lattice_y, corrected, metadata)
