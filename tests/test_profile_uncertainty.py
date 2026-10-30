"""Independent curvature controls, including a residual-curvature counterexample."""
import unittest
import numpy as np
from scripts import profile_uncertainty as profile
from scripts import diagnose_bias as diagnostic
from tests.test_motion import synthetic_frame


class ProfileTests(unittest.TestCase):
    def test_linear_gaussian_curvature_matches_exact_information(self):
        a = np.array([[2., 1.], [-1., 3.], [.5, 2.]])
        residual = lambda p: a @ p - np.array([2., -1., 4.])
        actual = profile.hessian(residual, np.array([.3, -.2]), .002)
        np.testing.assert_allclose(actual, a.T @ a, atol=1e-8)

    def test_nonlinear_residual_term_is_not_jacobian_information(self):
        # A true local minimum with Hessian diag(2,1), while J'J=diag(4,1).
        residual = lambda p: np.array([2*p[0], p[1], p[0]**2-1])
        actual = profile.hessian(residual, np.zeros(2), .002)
        np.testing.assert_allclose(actual, [[2., 0.], [0., 1.]], atol=1e-5)
        self.assertGreater(np.linalg.norm(actual - np.diag([4., 1.])), 1.)

    def test_signal_motion_profiles_position_and_curvature(self):
        model = diagnostic.model; model.motion.WCS = model.motion.base.grid_wcs()
        anchor = np.array([31.5, 31.5]); delta = np.array([.6, .05]); fits = []
        for epoch, position in enumerate([anchor, anchor+delta]):
            frame = synthetic_frame();frame['record']['obs_id'] = str(epoch)
            frame['data'] = model.motion.render_source(frame, position, 5.) + .1
            fit = diagnostic.fit_epoch([frame], [], {str(epoch):np.empty((0,2))}, anchor)
            fits.append(fit)
            covariance = profile.covariance(fit)
            self.assertTrue(covariance['supported'])
            np.testing.assert_allclose(covariance['covariance_px2'],fit['covariance'],rtol=.01,atol=1e-7)
        true = profile.motion_likelihood(fits, anchor, delta)
        wrong = profile.motion_likelihood(fits, anchor, np.zeros(2))
        self.assertTrue(true['supported']);self.assertLess(true['delta_chi2'],1e-5)
        self.assertTrue(wrong['supported']);self.assertGreater(wrong['delta_chi2'],100.)
