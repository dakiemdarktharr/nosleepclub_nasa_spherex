"""Deterministic synthetic ePSFs: no image data, fits or random draws."""
from dataclasses import replace
import unittest
from unittest.mock import patch

import astropy.units as u
import numpy as np
from scipy.ndimage import map_coordinates, spline_filter

from scripts import moment_preserving_epsf as moment
from scripts.native_flux_template import native_flux_template


OMEGA = (6.15*u.arcsec)**2
ZERO = (0*u.pix**2, 0*u.pix**3, 0*u.pix**3)


def synthetic(asymmetric=False):
    x = (np.arange(33)-16)/5.;X, Y = np.meshgrid(x, x)
    core = np.exp(-.5*((X/.9)**2+(Y/1.05)**2))
    ring = .0001*np.exp(-((np.hypot(X, Y)-2.6)/.3)**2)
    return core*(1 + (.06*X-.03*Y if asymmetric else 0)) - ring


def frozen(raw, pos, mask):
    return native_flux_template(raw, oversampling_x=5, oversampling_y=5,
        source_xy=pos, selection_mask=mask, source_omega=OMEGA,
        source_omega_provenance='synthetic area', epsf_provenance='synthetic ePSF')


def corrected(raw, pos, mask, params=ZERO):
    return moment.MomentPreservingEPSF(raw, provenance='synthetic ePSF').render(
        pos, mask, source_omega=OMEGA, parameters=params, source_omega_provenance='synthetic area')


class MomentPreservingTests(unittest.TestCase):
    def test_theta_zero_matches_frozen_renderer_on_phases_edges_and_masks(self):
        for asymmetric in (False, True):
            raw = synthetic(asymmetric)
            for pos in ((20., 20.), (20.001, 20.999), (20.5, 20.5), (.01, .99)):
                full = np.ones((41, 41), dtype=bool)
                hole = full.copy();hole[::3, ::2] = False
                small = np.zeros_like(full)
                xx, yy = map(int, pos)
                small[max(0, yy-1):yy+2, max(0, xx-1):xx+2] = True
                for mask in (full, hole, small):
                    with self.subTest(asymmetric=asymmetric, pos=pos, mask=int(mask.sum())):
                        old = frozen(raw, pos, mask);new = corrected(raw, pos, mask)
                        np.testing.assert_array_equal(new.x, old.x);np.testing.assert_array_equal(new.y, old.y)
                        np.testing.assert_allclose(new.normalized_selected, old.normalized_selected, rtol=2e-13, atol=2e-15)
                        np.testing.assert_allclose(new.template_per_jy.to_value(u.MJy/u.sr/u.Jy),
                                                   old.template_per_jy.to_value(u.MJy/u.sr/u.Jy), rtol=2e-13, atol=1e-13)
                        self.assertEqual(new.metadata['support_truncated_by_image'], old.support_truncated_by_image)

    def test_corrected_full_lattice_flux_and_both_first_moments(self):
        params = (.01*u.pix**2, .0002*u.pix**3, -.0002*u.pix**3)
        for raw in (synthetic(), synthetic(True)):
            model = moment.MomentPreservingEPSF(raw, provenance='test')
            for pos in ((20.0, 20.), (20.001, 20.999), (20.999, 20.001), (.1, .9)):
                with self.subTest(pos=pos):
                    basis = model.basis(pos);X, Y = np.meshgrid(basis.lattice_x, basis.lattice_y)
                    weights = [np.ones_like(X), X-pos[0], Y-pos[1]]
                    for v in range(3):
                        for w in weights:
                            contribution = w*basis.directions[:, :, v]
                            self.assertLessEqual(abs(np.sum(contribution)), 5e-12 * max(1., np.sum(abs(contribution))))
                    result = model.render(pos, np.ones((41, 41), bool), source_omega=OMEGA,
                                          parameters=params, source_omega_provenance='test')
                    for w in weights:
                        self.assertAlmostEqual(float(np.sum(w*result.normalized_lattice)),
                                               float(np.sum(w*basis.baseline)), delta=3e-13)
                    self.assertGreaterEqual(result.metadata['peak_change_fraction'], 0.)
                    self.assertLessEqual(result.metadata['peak_change_fraction'], moment.PEAK_CHANGE_LIMIT)
                    self.assertLessEqual(result.metadata['negative_wing_change_fraction'], moment.NEGATIVE_WING_LIMIT)

    def test_holey_mask_does_not_renormalize_and_keeps_signed_wings(self):
        raw = synthetic(True);pos = (20.2, 20.7);full = np.ones((41, 41), bool)
        hole = full.copy();hole[19:22, 19:22] = False
        params = (.01*u.pix**2, 0*u.pix**3, 0*u.pix**3)
        a = corrected(raw, pos, full, params);b = corrected(raw, pos, hole, params)
        np.testing.assert_allclose(a.normalized_lattice, b.normalized_lattice, atol=0, rtol=0)
        np.testing.assert_allclose(b.normalized_selected, a.normalized_selected[hole.ravel()], atol=0, rtol=0)
        self.assertLess(b.metadata['signed_selected_fraction'], a.metadata['signed_selected_fraction'])
        self.assertLess(a.normalized_lattice.min(), 0.)

    def test_width_and_odd_stencils_against_independent_direct_sampling(self):
        raw = synthetic(True);pos = np.array([20.37, 20.81]);model = moment.MomentPreservingEPSF(raw, provenance='test')
        basis = model.basis(pos);X, Y = np.meshgrid(basis.lattice_x, basis.lattice_y)
        coeff = spline_filter(np.pad(raw/raw.sum()*25, 16), order=3);center = (coeff.shape[0]-1)/2
        def sample(p):
            result = map_coordinates(coeff, [(Y-p[1])*5+center, (X-p[0])*5+center],
                                     order=3, mode='constant', cval=0., prefilter=False)
            return result/result.sum()
        h = .2;dx = np.array([h, 0.]);dy = np.array([0., h]);base = sample(pos)
        raw_dirs = np.stack([(sample(pos+dx)+sample(pos-dx)+sample(pos+dy)+sample(pos-dy)-4*base)/(4*h*h),
            (sample(pos+2*dx)-2*sample(pos+dx)+2*sample(pos-dx)-sample(pos-2*dx))/(2*h**3),
            (sample(pos+2*dy)-2*sample(pos+dy)+2*sample(pos-dy)-sample(pos-2*dy))/(2*h**3)], axis=-1).reshape(-1, 3)
        step = .002;ex = np.array([step, 0.]);ey = np.array([0., step])
        nuisance = np.column_stack([base.ravel(), ((sample(pos+ex)-sample(pos-ex))/(2*step)).ravel(),
                                   ((sample(pos+ey)-sample(pos-ey))/(2*step)).ravel()])
        moments = np.vstack([np.ones(X.size), (X-pos[0]).ravel(), (Y-pos[1]).ravel()])
        expected = raw_dirs - nuisance @ np.linalg.solve(moments @ nuisance, moments @ raw_dirs)
        np.testing.assert_allclose(basis.directions.reshape(-1, 3), expected, rtol=3e-11, atol=3e-12)
        for index in (1, 2):
            self.assertGreater(np.linalg.norm(expected[:, index]), .01)
            self.assertGreater(float(expected[:, index] @ basis.directions.reshape(-1, 3)[:, index]), 0.)

    def test_parameter_units_bounds_values_and_bad_bounds(self):
        valid = (.04*u.pix**2, -.003*u.pix**3, .003*u.pix**3)
        np.testing.assert_allclose(moment.numeric_parameters(valid), [.04, -.003, .003])
        millipixel = u.def_unit('epsf_test_millipixel', .001*u.pix)
        converted = tuple(value.to(millipixel**power) for value, power in zip(valid, (2, 3, 3)))
        np.testing.assert_allclose(moment.numeric_parameters(converted), [.04, -.003, .003])
        self.assertEqual(len(moment.physical_parameters([.01, .002, -.002])), 3)
        for params in ((.04, 0*u.pix**3, 0*u.pix**3), (0*u.m**2, 0*u.pix**3, 0*u.pix**3),
                       (.041*u.pix**2, 0*u.pix**3, 0*u.pix**3), (np.nan*u.pix**2, 0*u.pix**3, 0*u.pix**3),
                       (u.Quantity(True, u.pix**2, dtype=bool), 0*u.pix**3, 0*u.pix**3),
                       (np.ones(2)*u.pix**2, 0*u.pix**3, 0*u.pix**3), (0*u.pix**2,)):
            with self.subTest(params=params), self.assertRaises(ValueError): moment.numeric_parameters(params)
        for bounds in ((.04, .003), (.04, .003, .003, .1), (.04, np.nan, .003),
                       (.04, -1., .003), (.04, True, .003), (.04, 0., .003)):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError): moment.numeric_parameters(ZERO, bounds=bounds)
        for values in ([True, 0, 0], [0., np.nan, 0.], [0., 0.], [0., 0., np.inf]):
            with self.subTest(values=values), self.assertRaises(ValueError): moment.physical_parameters(values)

    def test_reject_peak_and_negative_wing_change_without_clipping(self):
        model = moment.MomentPreservingEPSF(synthetic(), provenance='test');pos = (20.3, 20.7)
        basis = model.basis(pos);peak = abs(basis.baseline).max()
        params = (.04*u.pix**2, 0*u.pix**3, 0*u.pix**3)
        for change in ('peak', 'wing'):
            directions = np.zeros_like(basis.directions)
            index = np.unravel_index(np.argmin(basis.baseline) if change == 'wing' else np.argmax(basis.baseline), basis.baseline.shape)
            directions[index+(0,)] = (-.02 if change == 'wing' else .06)*peak/.04
            fake = replace(basis, directions=directions)
            with self.subTest(change=change), patch.object(model, 'basis', return_value=fake):
                with self.assertRaisesRegex(ValueError, 'full-lattice physical guard'):
                    model.render(pos, np.ones((41, 41), bool), source_omega=OMEGA,
                                 parameters=params, source_omega_provenance='test')

    def test_reject_invalid_physical_inputs(self):
        raw = synthetic();mask = np.ones((41, 41), bool);model = moment.MomentPreservingEPSF(raw, provenance='test')
        for bad in (np.ones((32,33)), np.zeros((33,33)), np.full((33,33), np.nan)):
            with self.assertRaises(ValueError): moment.MomentPreservingEPSF(bad, provenance='test')
        for pos, badmask, omega in [((-1., 20.), mask, OMEGA), ((np.nan, 2.), mask, OMEGA),
                                    ([True, 20], mask, OMEGA),
                                    ((20., 20.), mask.astype(int), OMEGA), ((20., 20.), mask, 1*u.m),
                                    ((20., 20.), mask, 0*u.sr)]:
            with self.assertRaises(ValueError):
                model.render(pos, badmask, source_omega=omega, parameters=ZERO, source_omega_provenance='test')


if __name__ == '__main__': unittest.main()
