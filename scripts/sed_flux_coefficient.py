"""Conditional source-flux functional, not an official SPHEREx color model.

Source F_nu is piecewise linear in wavelength; the lab response is shifted
without dilation and kept signed. The reference spectrum is explicitly
(lambda/local_center)**alpha for unit F_nu at the local center. Both means
use the diagnostic photon convention integral F_nu R/lambda / integral R/lambda.
No spectral uncertainty or calibration validity is inferred.
"""
from dataclasses import dataclass
from numbers import Real

import astropy.units as u
import numpy as np

from scripts.spectral_bandpass_v2 import photon_weighted_bandpass


@dataclass(frozen=True)
class SedFluxCoefficient:
    coefficient: u.Quantity
    source_mean: u.Quantity
    reference_mean: float
    contribution_weights: np.ndarray
    shifted_response_wavelength: u.Quantity
    shift: u.Quantity
    local_center: u.Quantity
    fiducial_center: u.Quantity
    reference_alpha: float
    reference_quadrature_relative_difference: float
    response_negative_absolute_fraction: float
    spectrum_provenance: str
    response_provenance: str
    reference_provenance: str


def _scalar_wavelength(value, name):
    if not isinstance(value, u.Quantity):
        raise ValueError(name+' requires explicit wavelength units')
    try:
        x = np.asarray(value.to_value(u.um))
    except (TypeError, ValueError, u.UnitConversionError) as exc:
        raise ValueError(name+' must have wavelength units') from exc
    if x.shape != () or x.dtype.kind not in 'fiu' or not np.isfinite(x) or x <= 0:
        raise ValueError(name+' must be a positive finite scalar')
    return float(x)


def _reference_integral(wave, response, center, alpha, nodes):
    """Integrate normalized, piecewise-linear response on each interval."""
    gx, gw = np.polynomial.legendre.leggauss(nodes)
    t = (gx+1)/2
    h = np.diff(wave)
    lam = wave[:-1, None]+h[:, None]*t
    r = response[:-1, None]*(1-t)+response[1:, None]*t
    with np.errstate(over='ignore', under='ignore', invalid='ignore', divide='ignore'):
        reference = np.exp(alpha*np.log(lam/center))
        integrand = r*reference*(h[:, None]/lam)*(gw/2)
    if (not np.isfinite(reference).all() or np.any(reference == 0)
            or not np.isfinite(integrand).all() or np.any((r != 0) & (integrand == 0))):
        raise ValueError('reference quadrature outside numerical range')
    signed = float(np.sum(integrand))
    absolute = float(np.sum(np.abs(integrand)))
    if not np.isfinite([signed, absolute]).all() or absolute <= 0:
        raise ValueError('reference response integral outside numerical range')
    return signed, absolute


def sed_flux_coefficient(wavelength, flux, usable, response_wavelength, response,
                         *, local_center, fiducial_center, reference_alpha,
                         maximum_gap, spectrum_provenance, response_provenance,
                         reference_provenance):
    """Return Jy coefficient and sample weights; refuse any missing response.

    Reference is dimensionless, normalized to one at local_center. The returned
    weights act on usable source samples in Jy; do not multiply zero weights
    by NaNs from unusable samples. A dimensionless linked-frame
    ratio, if wanted, must be formed against a separately specified common
    amplitude. Signed source samples are allowed; a positive total is required.
    Eight- and sixteen-node reference quadrature must agree to 1e-12 of an
    absolute-integral scale; this numerical check is not an error bound.
    """
    for name, value in [('spectrum_provenance', spectrum_provenance),
                        ('response_provenance', response_provenance),
                        ('reference_provenance', reference_provenance)]:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(name+' is required')
    if isinstance(reference_alpha, (bool, np.bool_)) or not isinstance(reference_alpha, Real) or not np.isfinite(reference_alpha):
        raise ValueError('reference_alpha must be finite and real')
    local = _scalar_wavelength(local_center, 'local_center')
    fiducial = _scalar_wavelength(fiducial_center, 'fiducial_center')
    if not isinstance(response_wavelength, u.Quantity):
        raise ValueError('response_wavelength requires explicit units')
    try:
        rwave = np.asarray(response_wavelength.to_value(u.um))
    except (TypeError, ValueError, u.UnitConversionError) as exc:
        raise ValueError('response_wavelength must have wavelength units') from exc
    if rwave.ndim != 1 or len(rwave) < 2 or rwave.dtype.kind not in 'iuf' or not np.isfinite(rwave).all() or np.any(rwave <= 0) or np.any(np.diff(rwave) <= 0):
        raise ValueError('response_wavelength must be positive, finite, strictly increasing')
    rwave = rwave.astype(float)
    shift = local-fiducial
    shifted = rwave+shift
    if not np.isfinite(shifted).all() or np.any(shifted <= 0) or np.any(np.diff(shifted) <= 0):
        raise ValueError('shifted response wavelength is invalid')
    result = photon_weighted_bandpass(wavelength, flux, usable, shifted*u.um, response,
                                      maximum_gap=maximum_gap, response_kind='signed_laboratory_measurement')
    if not result.support_complete:
        raise ValueError('source spectrum has missing absolute response support')
    if result.full_band_mean_jy is None or result.full_band_mean_jy <= 0:
        raise ValueError('source band mean must be positive')
    r=np.asarray(response.to_value(u.one), dtype=float)
    scale=float(np.max(np.abs(r)))
    r=r/scale
    integral8,_ = _reference_integral(shifted,r,local,float(reference_alpha),8)
    integral16,abs16 = _reference_integral(shifted,r,local,float(reference_alpha),16)
    if integral16 <= .01*abs16:
        raise ValueError('reference mean must have stable positive normalization')
    discrepancy=abs(integral8-integral16)/abs16
    if not np.isfinite(discrepancy) or discrepancy > 1e-12:
        raise ValueError('reference quadrature did not converge')
    signed_norm=result.full_signed_weight/scale
    reference_mean=integral16/signed_norm
    with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
        coefficient=result.full_band_mean_jy/reference_mean
        weights=result.supported_part_weights/reference_mean
    if (not np.isfinite(reference_mean) or reference_mean <= 0 or not np.isfinite(coefficient)
            or coefficient <= 0 or not np.isfinite(weights).all()
            or np.any((result.supported_part_weights != 0) & (weights == 0))):
        raise ValueError('coefficient outside numerical range')
    return SedFluxCoefficient(coefficient*u.Jy, result.full_band_mean_jy*u.Jy, float(reference_mean),
                              weights, shifted*u.um, shift*u.um, local*u.um, fiducial*u.um,
                              float(reference_alpha), float(discrepancy), result.negative_response_absolute_fraction,
                              spectrum_provenance, response_provenance, reference_provenance)
