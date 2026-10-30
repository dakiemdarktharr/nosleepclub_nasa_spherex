"""Coverage-aware photon-weighted linear spectral functionals.

This defines a diagnostic convention, not SPHEREx's calibrated photometric
system. Signed laboratory response samples and negative measured fluxes are
retained. No interpolation crosses an unusable spectral sample or a large gap.
"""
from dataclasses import dataclass

import astropy.units as u
import numpy as np


def _moments(a, b, ra, rb):
    """Exact integrals A=∫R/λ, J=∫(λ−a)R/λ for linear R."""
    return _moments_span(a,b-a,ra,rb)


def _moments_span(a, h, ra, rb):
    """Use a span explicitly, including roots that round to a knot."""
    x=h/a
    if not np.isfinite(x) or x<=0:
        raise ValueError('response wavelength interval outside numerical range')
    L=np.log1p(x)
    if x<=.125:
        # 1-log1p(x)/x and 1/2-1/x+log1p(x)/x².
        # At x<=1/8, 20 terms leave <2e-20 absolute remainder.
        k0=0.;k1=0.;power=x
        for n in range(1,21):
            term=power if n%2 else -power
            k0+=term/(n+1);k1+=term/(n+2);power*=x
    else:
        k0=1-L/x
        k1=.5-k0/x
    dr=rb-ra
    A=ra*L+dr*k0
    J=h*(ra*k0+dr*k1)
    if not np.isfinite(A) or not np.isfinite(J):
        raise ValueError('response moment outside numerical range')
    return float(A),float(J)


@dataclass(frozen=True)
class BandpassResult:
    full_band_mean_jy: float | None
    supported_part_mean_jy: float | None
    supported_part_weights: np.ndarray
    full_signed_weight: float
    full_absolute_weight: float
    unsupported_absolute_weight: float
    unsupported_absolute_fraction: float
    negative_response_absolute_fraction: float
    support_complete: bool
    convention: str = "integral F_nu(lambda)*R(lambda)/lambda d_lambda divided by integral R(lambda)/lambda d_lambda"


def _quantity(value, unit, name):
    if not isinstance(value, u.Quantity):
        raise ValueError(name + ' requires explicit units')
    try:
        array = np.asarray(value.to_value(unit))
    except (TypeError, ValueError, u.UnitConversionError) as exc:
        raise ValueError(name + ' has incompatible units') from exc
    if array.dtype.kind not in 'fiu':
        raise ValueError(name + ' must be real')
    return np.asarray(array, float)


def _axis(value, name):
    array = _quantity(value, u.um, name)
    if array.ndim != 1 or len(array) < 2 or not np.isfinite(array).all() or np.any(array <= 0) or np.any(np.diff(array) <= 0):
        raise ValueError(name + ' must be a positive, finite, strictly increasing 1D axis')
    return array


def photon_weighted_bandpass(wavelength, flux, usable, response_wavelength,
                             response, *, maximum_gap, response_kind):
    """Integrate piecewise-linear samples analytically on shared knot intervals.

    response_kind must explicitly be 'signed_laboratory_measurement' or
    'nonnegative_throughput'. Missing response-weight support prevents a full
    band prediction even if its signed contribution would cancel. The partial
    mean is a different linear functional, never a completed-band estimate.

    Returned partial weights allow propagation of a separately justified full
    spectral covariance. No error is calculated from unverified independent
    sample assumptions. max-gap is a caller-declared physical sampling limit.
    The signed total and supported signed weight each must exceed one percent
    of the full absolute weight to report their respective normalized means.
    """
    wave = _axis(wavelength, 'wavelength')
    rwave = _axis(response_wavelength, 'response_wavelength')
    values = _quantity(flux, u.Jy, 'flux')
    transmission = _quantity(response, u.dimensionless_unscaled, 'response')
    mask = np.asarray(usable)
    if values.shape != wave.shape or mask.shape != wave.shape or mask.dtype != np.dtype(bool):
        raise ValueError('flux and boolean usable must match wavelength')
    if np.any(~np.isfinite(values[mask])):
        raise ValueError('usable flux must be finite')
    if transmission.shape != rwave.shape or not np.isfinite(transmission).all():
        raise ValueError('response must be finite and match its axis')
    if response_kind not in ('signed_laboratory_measurement', 'nonnegative_throughput'):
        raise ValueError('declare the response interpretation')
    if response_kind == 'nonnegative_throughput' and np.any(transmission < 0):
        raise ValueError('physical throughput cannot be negative')
    gap = _quantity(maximum_gap, u.um, 'maximum_gap')
    if gap.shape != () or not np.isfinite(gap) or gap <= 0:
        raise ValueError('maximum_gap must be a positive scalar')

    # Normalize before interpolation/moments to avoid overflow in response
    # arithmetic; the original scale is restored only in reported integrals.
    response_scale=float(np.max(np.abs(transmission)))
    if response_scale==0:raise ValueError('response has no stable positive normalization')
    rnorm=transmission/response_scale
    if np.any((transmission!=0)&(rnorm==0)):
        raise ValueError('response dynamic range outside numerical range')
    # Include zero crossings for absolute and negative response integrals.
    crossings = []
    for a, b, ra, rb in zip(rwave[:-1], rwave[1:], rnorm[:-1], rnorm[1:]):
        if (ra<0<rb) or (rb<0<ra):
            frac=abs(ra)/(abs(ra)+abs(rb))
            crossings.append(a+frac*(b-a))
    knots = np.unique(np.r_[rwave, wave[(wave > rwave[0]) & (wave < rwave[-1])], crossings])
    coefficients = np.zeros(len(wave), dtype=float)
    signed_total = absolute_total = missing = negative = supported_signed = 0.
    has_missing_weight = False
    for a, b in zip(knots[:-1], knots[1:]):
        midpoint = a+(b-a)/2
        ra,rb=np.interp([a,b],rwave,rnorm)
        signed,J=_moments(a,b,ra,rb)
        if (ra<0<rb) or (rb<0<ra):
            # A rounded root can fall just outside a subinterval. Split its
            # residual sign change, even though it is usually only an ulp.
            frac=abs(ra)/(abs(ra)+abs(rb));h=b-a
            h1=h*frac;h2=h*(1-frac)
            if h1<=0 or h2<=0:raise ValueError('unresolvable response zero crossing')
            first,_=_moments_span(a,h1,ra,0.)
            second,_=_moments_span(a+h1,h2,0.,rb)
            if first==0 or second==0:
                raise ValueError('response sign lobe outside numerical range')
            absolute=abs(first)+abs(second)
            negative_piece=(abs(first) if ra<0 else 0.)+(abs(second) if rb<0 else 0.)
        else:
            absolute=abs(signed)
            negative_piece=absolute if ra<0 or rb<0 else 0.
        if absolute==0 and (ra!=0 or rb!=0):
            raise ValueError('response interval outside numerical range')
        signed_total += signed
        absolute_total += absolute
        negative += negative_piece
        index = int(np.searchsorted(wave, midpoint, side='right') - 1)
        valid = (0 <= index < len(wave) - 1 and mask[index] and mask[index + 1]
                 and wave[index + 1] - wave[index] <= float(gap))
        if valid:
            span=wave[index + 1]-wave[index]
            right=(a-wave[index])/span*signed+J/span
            left=signed-right
            coefficients[index] += left
            coefficients[index + 1] += right
            supported_signed += signed
        else:
            missing += absolute
            has_missing_weight |= absolute>0
    if not np.isfinite([signed_total, absolute_total, missing, negative, supported_signed]).all() or not np.isfinite(coefficients).all() or absolute_total <= 0 or signed_total <= .01 * absolute_total:
        raise ValueError('response has no stable positive normalization')
    complete = not has_missing_weight
    partial = None
    if supported_signed > .01 * absolute_total:
        coefficients /= supported_signed
        # Invalid flux is not evaluated: zero coefficient times NaN is NaN.
        partial = float(coefficients[mask] @ values[mask])
        if not np.isfinite(partial) or not np.isfinite(coefficients).all():
            raise ValueError('spectral functional outside numerical range')
    else:
        coefficients[:] = 0.
    with np.errstate(over='ignore',under='ignore',invalid='ignore'):
        scaled=np.asarray([signed_total,absolute_total,missing],float)*response_scale
    if not np.isfinite(scaled).all() or scaled[0]<=0 or scaled[1]<=0 or (missing>0 and scaled[2]==0):
        raise ValueError('response normalization outside numerical range')
    return BandpassResult(
        partial if complete else None, partial, coefficients, *map(float,scaled), missing / absolute_total,
        negative / absolute_total, complete)
