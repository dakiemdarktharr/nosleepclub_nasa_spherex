"""Analytic and independently integrated flux/phase/rotation controls."""
import unittest

import astropy.units as u
import numpy as np
from scipy.integrate import dblquad
from scipy.special import ndtr

from scripts.rotated_gaussian_control import pixel_fractions, integrated_source


class RotatedGaussianTests(unittest.TestCase):
    def test_axis_aligned_matches_closed_form_and_mask_is_not_renormalized(self):
        yy, xx = np.mgrid[-7:8, -7:8]; x, y = xx.ravel(), yy.ravel(); pos = [.25, .75]
        result = pixel_fractions(x, y, source_xy=pos, sigma_xy=[.55, .7], angle_deg=0.)
        exact = (ndtr((x+.5-pos[0])/.55)-ndtr((x-.5-pos[0])/.55))*(ndtr((y+.5-pos[1])/.7)-ndtr((y-.5-pos[1])/.7))
        np.testing.assert_allclose(result, exact, atol=2e-16)
        self.assertAlmostEqual(result.sum(), 1., places=12)
        mask = x < 0
        subset = pixel_fractions(x[mask], y[mask], source_xy=pos, sigma_xy=[.55, .7], angle_deg=0.)
        np.testing.assert_array_equal(subset, result[mask]); self.assertLess(subset.sum(), .5)

    def test_rotated_pixel_matches_adaptive_double_integral(self):
        x = np.asarray([-1, 0, 1]); y = np.asarray([0, 0, 1]); pos = [.25, .75]
        result = pixel_fractions(x, y, source_xy=pos, sigma_xy=[.55, .7], angle_deg=25.)
        c, s = np.cos(np.deg2rad(25)), np.sin(np.deg2rad(25))
        def density(yy, xx):
            dx, dy = xx-pos[0], yy-pos[1]
            return np.exp(-.5*(((c*dx+s*dy)/.55)**2+((-s*dx+c*dy)/.7)**2))/(2*np.pi*.55*.7)
        for ix, iy, actual in zip(x, y, result):
            expected, error = dblquad(density, ix-.5, ix+.5, lambda _: iy-.5, lambda _: iy+.5, epsabs=1e-12)
            self.assertLess(error, 1e-10); self.assertAlmostEqual(actual, expected, places=12)

    def test_flux_units_and_varying_pixel_area_conserve_selected_flux(self):
        yy, xx = np.mgrid[-5:6, -5:6]; x, y = xx.ravel(), yy.ravel()
        omega = np.linspace(8e-10, 1.2e-9, len(x))*u.sr
        result = integrated_source(x, y, source_xy=[.75, .25], sigma_xy=[.55, .7], angle_deg=25.,
                                   flux=600*u.uJy, pixel_omega=omega)
        selected = np.sum(result['surface'].to_value(u.MJy/u.sr)*1e6*omega.to_value(u.sr))
        self.assertAlmostEqual(selected, .0006*result['fractions'].sum(), places=16)
        self.assertFalse(result['metadata']['mask_renormalized'])

    def test_invalid_units_boolean_dimensions_and_duplicate_pixels_refused(self):
        base = {'source_xy': [.25, .25], 'sigma_xy': [.55, .7], 'angle_deg': 25.}
        for key, value in (('source_xy', [True, .25]), ('sigma_xy', [.1, .7]), ('angle_deg', np.nan), ('order', True)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                pixel_fractions([0, 1], [0, 1], **{**base, key: value})
        with self.assertRaises(ValueError): pixel_fractions([0, 0], [0, 0], **base)
        with self.assertRaises(ValueError): pixel_fractions([0.5], [0], **base)
        with self.assertRaises(ValueError): integrated_source([0], [0], **base, flux=1., pixel_omega=[1.]*u.sr)
        with self.assertRaises(u.UnitConversionError): integrated_source([0], [0], **base, flux=1*u.m, pixel_omega=[1.]*u.sr)


if __name__ == '__main__': unittest.main()
