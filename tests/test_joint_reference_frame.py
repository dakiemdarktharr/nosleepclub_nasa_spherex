"""Deterministic synthetic GLS tests; no observed frames are loaded."""
import unittest

import astropy.units as u
import numpy as np

from scripts.joint_reference_frame import solve_joint_translation


class JointReferenceTests(unittest.TestCase):
    def setUp(self):
        self.sources = ['s0', 's1', 's2', 's3'] * 2
        self.exposures = ['e1'] * 4 + ['e0'] * 4
        self.planned = ['e0', 'e1']
        self.allowed = ['s0', 's1', 's2', 's3', 'extra']
        self.y = np.array([[1., -1.], [2., -1.2], [.4, -.7], [1.3, -1.4],
                           [-.2, 3.], [.3, 2.5], [-.8, 3.2], [.1, 2.8]])
        diagonal = np.linspace(.4, 1.9, 16)
        shared = np.tile(np.array([[.4, .08], [.08, .3]]), (8, 8))
        self.C = np.diag(diagonal) + shared
        self.H = np.zeros((16, 4))
        for i, e in enumerate(self.exposures):
            j = self.planned.index(e)
            self.H[2*i:2*i+2, 2*j:2*j+2] = np.eye(2)

    def solve(self, **overrides):
        args = {'offsets': self.y*u.pix, 'covariance': self.C*u.pix**2,
                'source_ids': self.sources, 'exposure_ids': self.exposures,
                'allowed_source_ids': self.allowed, 'planned_exposures': self.planned,
                'provenance': 'fixed synthetic covariance'}
        args.update(overrides)
        return solve_joint_translation(**args)

    def test_full_gls_against_independent_normal_equations_and_influence(self):
        result = self.solve()
        precision_H = np.linalg.solve(self.C, self.H)
        expected_C = np.linalg.inv(self.H.T @ precision_H)
        expected_L = expected_C @ precision_H.T
        expected_y = expected_L @ self.y.ravel()
        np.testing.assert_allclose(result.offsets.value.ravel(), expected_y, atol=2e-13)
        np.testing.assert_allclose(result.covariance.value, expected_C, atol=2e-13)
        np.testing.assert_allclose(result.influence, expected_L, atol=2e-13)
        np.testing.assert_allclose(result.influence @ self.C @ result.influence.T, result.covariance.value, atol=2e-13)
        np.testing.assert_allclose(result.influence @ self.H, np.eye(4), atol=2e-13)
        residual = self.y.ravel() - self.H @ expected_y
        np.testing.assert_allclose(result.residuals.value.ravel(), residual, atol=2e-13)
        self.assertAlmostEqual(result.chi2, residual @ np.linalg.solve(self.C, residual), places=12)
        self.assertEqual(result.exposure_ids, ('e0', 'e1'))
        self.assertEqual(result.reference_counts, (4, 4))
        self.assertEqual(result.rank, 4);self.assertEqual(result.dof, 12)
        self.assertGreater(np.linalg.norm(result.covariance.value[:2, 2:]), .1)
        self.assertIn('conditional', result.qualification)

    def test_diagonal_limit_is_framewise_weighted_mean(self):
        variances = np.arange(1., 17.)
        result = self.solve(covariance=np.diag(variances)*u.pix**2)
        for j, exposure in enumerate(self.planned):
            indexes = [i for i, e in enumerate(self.exposures) if e == exposure]
            for axis in range(2):
                weights = 1/variances[2*np.array(indexes)+axis]
                expected = np.average(self.y[indexes, axis], weights=weights)
                self.assertAlmostEqual(result.offsets.value[j, axis], expected, places=12)
                self.assertAlmostEqual(result.covariance.value[2*j+axis, 2*j+axis], 1/sum(weights), places=12)
        np.testing.assert_allclose(result.covariance.value[:2, 2:], 0., atol=1e-14)

    def test_units_and_covariance_scales(self):
        millipixel = u.def_unit('joint_test_millipixel', .001*u.pix)
        base = self.solve()
        converted = self.solve(offsets=(self.y*u.pix).to(millipixel),
                               covariance=(self.C*u.pix**2).to(millipixel**2))
        np.testing.assert_allclose(converted.offsets.value, base.offsets.value, atol=1e-13)
        np.testing.assert_allclose(converted.covariance.value, base.covariance.value, atol=1e-13)
        for scale in (1e-14, 1e14):
            fit = self.solve(covariance=self.C*scale*u.pix**2)
            np.testing.assert_allclose(fit.offsets.value, base.offsets.value, rtol=1e-11, atol=1e-11)
            np.testing.assert_allclose(fit.covariance.value / scale, base.covariance.value, rtol=1e-11, atol=1e-11)
            np.testing.assert_allclose(fit.influence, base.influence, rtol=1e-11, atol=1e-11)

    def test_source_membership_observation_and_frame_guards(self):
        cases = [
            {'source_ids': ['heldout'] + self.sources[1:]},
            {'source_ids': ['s0', 's0'] + self.sources[2:]},
            {'source_ids': self.sources[:-1]},
            {'exposure_ids': ['unknown'] + self.exposures[1:]},
            {'planned_exposures': ['e0', 'e1', 'missing']},
            {'planned_exposures': ['e0', 'e0']},
            {'allowed_source_ids': ['s0', 's0', 's1', 's2', 's3']},
            {'min_references': 3},
            {'min_references': True},
            {'provenance': ''},
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError): self.solve(**case)
        y = self.y[:-1]*u.pix; C = self.C[:-2, :-2]*u.pix**2
        with self.assertRaisesRegex(ValueError, 'too few'):
            self.solve(offsets=y, covariance=C, source_ids=self.sources[:-1], exposure_ids=self.exposures[:-1])

    def test_wrong_units_nan_boolean_shape_and_bad_covariance(self):
        for scale in (1e-14, 1e14):
            asymmetric = self.C.copy()*scale;asymmetric[0, 1] += .1*scale
            non_spd = self.C.copy()*scale;non_spd[0, 1] = non_spd[1, 0] = 100*scale
            bad_nan = self.C.copy()*scale;bad_nan[0, 0] = np.nan
            for covariance in (asymmetric*u.pix**2, non_spd*u.pix**2, bad_nan*u.pix**2):
                with self.subTest(scale=scale), self.assertRaises(ValueError): self.solve(covariance=covariance)
        cases = [
            {'offsets': self.y}, {'covariance': self.C},
            {'offsets': self.y*u.m}, {'covariance': self.C*u.s**2},
            {'offsets': self.y[:, :1]*u.pix}, {'covariance': self.C[:-1, :-1]*u.pix**2},
            {'offsets': np.full((8, 2), np.nan)*u.pix},
            {'offsets': u.Quantity(np.ones((8, 2), dtype=bool), u.pix, dtype=bool)},
            {'covariance': u.Quantity(np.ones((16, 16), dtype=bool), u.pix**2, dtype=bool)},
            {'covariance': np.zeros((16, 16))*u.pix**2},
            {'max_condition': True}, {'max_condition': 1.}, {'rcond': 0.}, {'rcond': np.nan},
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError): self.solve(**case)

    def test_condition_and_relative_rank_guards(self):
        self.assertGreater(self.solve().condition, 1.0001)
        with self.assertRaisesRegex(ValueError, 'ill-conditioned'):
            self.solve(max_condition=1.00001)
        with self.assertRaisesRegex(ValueError, 'rank deficient'):
            self.solve(rcond=.999999)


if __name__ == '__main__': unittest.main()
