"""Independent positive Gaussian pixel integrals; no mask normalization.

Coordinates/widths are declared numeric native pixels, angles numeric degrees.
Flux and solid angle require Quantities. This analytic family is a stress
control, not a calibrated telescope PSF or an independent sky measurement.
"""
from functools import lru_cache
from numbers import Integral

import astropy.units as u
import numpy as np
from numpy.polynomial.legendre import leggauss

from .profile_landscape import numeric


SURFACE = u.MJy/u.sr


@lru_cache(maxsize=8)
def _nodes(order):
    nodes, weights = leggauss(order)
    x, y = np.meshgrid(nodes/2, nodes/2)
    w = np.outer(weights, weights)/4
    return x.ravel(), y.ravel(), w.ravel()


def pixel_fractions(x, y, *, source_xy, sigma_xy, angle_deg, order=24):
    x = numeric(x, 'x', 1); y = numeric(y, 'y', 1)
    p = numeric(source_xy, 'source_xy', 1); widths = numeric(sigma_xy, 'sigma_xy', 1)
    angle = numeric(angle_deg, 'angle_deg', 0)
    if (not len(x) or x.shape != y.shape or np.any(x != np.rint(x)) or np.any(y != np.rint(y))
            or len(np.unique(np.column_stack((x, y)), axis=0)) != len(x)
            or p.shape != (2,) or widths.shape != (2,) or np.any(widths < .2) or np.any(widths > 10.)
            or max(np.max(np.abs(x)), np.max(np.abs(y)), np.max(np.abs(p))) > 2**40
            or abs(float(angle)) > 360.):
        raise ValueError('invalid native pixels, center, widths or angle')
    if isinstance(order, (bool, np.bool_)) or not isinstance(order, Integral) or not 2 <= order <= 64:
        raise ValueError('quadrature order must be integer 2..64')
    qx, qy, weight = _nodes(int(order))
    dx = x[:, None]+qx-p[0]; dy = y[:, None]+qy-p[1]
    c, s = np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))
    xx = c*dx+s*dy; yy = -s*dx+c*dy
    with np.errstate(under='ignore'):
        density = np.exp(-.5*((xx/widths[0])**2+(yy/widths[1])**2))/(2*np.pi*np.prod(widths))
    fractions = density@weight
    if (not np.isfinite(fractions).all() or np.any(fractions < 0) or np.any(fractions > 1)
            or float(np.sum(fractions)) > 1+1e-11):
        raise ValueError('invalid Gaussian integrals')
    return fractions


def integrated_source(x, y, *, source_xy, sigma_xy, angle_deg, flux, pixel_omega):
    """24-node integral with a fixed 12-node numerical convergence guard."""
    if not isinstance(flux, u.Quantity) or not isinstance(pixel_omega, u.Quantity):
        raise ValueError('explicit flux Jy and pixel solid angles sr required')
    amount = numeric(flux.to_value(u.Jy), 'flux', 0)
    omega = numeric(pixel_omega.to_value(u.sr), 'pixel_omega', 1)
    if amount < 0 or len(omega) != len(x) or np.any(omega <= 0): raise ValueError('invalid flux/solid angles')
    kwargs = {'source_xy': source_xy, 'sigma_xy': sigma_xy, 'angle_deg': angle_deg}
    coarse = pixel_fractions(x, y, order=12, **kwargs); fine = pixel_fractions(x, y, order=24, **kwargs)
    l1 = float(np.sum(np.abs(coarse-fine))); total = float(np.sum(fine))
    if l1 > 1e-12+1e-10*total: raise ValueError('fixed quadrature convergence guard failed')
    value = float(amount)*fine/(1e6*omega)
    if not np.isfinite(value).all(): raise ValueError('nonfinite source brightness')
    return {'surface': value*SURFACE, 'fractions': fine,
        'metadata': {'family': 'positive rotated analytic Gaussian integrated over native pixels',
            'source_xy_native': np.asarray(source_xy, float).tolist(), 'sigma_xy_native': np.asarray(sigma_xy, float).tolist(),
            'angle_deg': float(angle_deg), 'flux_jy': float(amount), 'selected_fraction_raw': total,
            'missing_fraction': max(0., 1-total), 'quadrature_orders': [12, 24],
            'quadrature_l1_difference': l1, 'mask_renormalized': False,
            'qualification': 'independent analytic family from fitter; not telescope PSF truth'}}
