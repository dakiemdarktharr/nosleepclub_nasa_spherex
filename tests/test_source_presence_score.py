import unittest

import astropy.units as u
import numpy as np
from scipy.stats import beta

from scripts.source_presence_score import (
    binomial_lower, binomial_upper, paired_presence_statistic, prepare_operator,
)


I = u.MJy / u.sr


class PresenceTests(unittest.TestCase):
    def setUp(self):
        self.error = np.array([.5, 1., 2., .7, 1.5, .9]) * I
        self.templates = np.array([[.2, .4, 1., 2., .3, .1],
                                   [1., .2, .1, .3, .6, .7]]) * I / u.Jy
        self.background = np.ones(6) * I
        self.neighbor = np.array([.1, .5, .2, .7, .4, 1.]) * I / u.Jy
        self.data = np.array([1.2, -.2, .4, 2., -.8, 1.1]) * I

    def operator(self):
        return prepare_operator(self.templates, self.error,
                                [self.background, self.neighbor], provenance='test')

    def test_against_independent_joint_weighted_least_squares(self):
        op = self.operator()
        err = self.error.value
        y = self.data.value / err
        b = np.column_stack([self.background.value / err, self.neighbor.value / err])
        for i, template in enumerate(self.templates.value):
            p = template / err
            design = np.column_stack([b, p])
            coeff = np.linalg.lstsq(design, y, rcond=None)[0][-1]
            # Inverse information of the source coefficient in the full model.
            information = 1. / np.linalg.inv(design.T @ design)[-1, -1]
            self.assertAlmostEqual(op.score(self.data)[i], coeff * np.sqrt(information), places=11)
            self.assertAlmostEqual(op.projected_template_norm[i].value, np.sqrt(information), places=11)
            self.assertAlmostEqual(op.information_fraction[i], information / (p @ p), places=11)
        self.assertEqual(op.nuisance_rank, 2)
        self.assertGreaterEqual(op.nuisance_condition, 1.)

    def test_negative_and_conversion_including_jy_mjy(self):
        op = self.operator()
        pure = -2. * u.Jy * self.templates[0] + 3. * self.background
        self.assertLess(op.score(pure)[0], 0.)
        converted = prepare_operator(self.templates.to((u.Jy / u.sr) / u.mJy),
            self.error.to(u.Jy / u.sr),
            [self.background.to(u.Jy / u.sr), self.neighbor.to((u.Jy / u.sr) / u.mJy)],
            provenance='converted')
        np.testing.assert_allclose(op.score(self.data), converted.score(self.data.to(u.Jy / u.sr)), rtol=1e-12)
        np.testing.assert_allclose(op.projected_template_norm.value, converted.projected_template_norm.value, rtol=1e-12)

    def test_nuisance_scale_invariance_and_empty_nuisance(self):
        base = self.operator()
        for factor in (1e-180, 1e-100, 1., 1e100, 1e120):
            with self.subTest(factor=factor):
                op = prepare_operator(self.templates, self.error,
                    [self.background * factor, self.neighbor / factor], provenance='scale')
                np.testing.assert_allclose(op.score(self.data), base.score(self.data), rtol=2e-13, atol=2e-13)
                np.testing.assert_allclose(op.information_fraction, base.information_fraction, rtol=2e-13)
        empty = prepare_operator(self.templates, self.error, [], provenance='none')
        self.assertEqual(empty.nuisance_rank, 0)
        np.testing.assert_allclose(empty.information_fraction, [1., 1.], atol=1e-14)

    def test_reject_bad_inputs(self):
        bad_cases = [
            (self.templates.value, self.error, [self.background]),
            (self.templates, self.error.value, [self.background]),
            (self.templates, np.zeros(6) * I, [self.background]),
            (self.templates, np.array([1, 1, 1, 1, 1, np.nan]) * I, []),
            (np.zeros((1, 6)) * I / u.Jy, self.error, []),
            (self.background[None, :] / u.Jy, self.error, [self.background]),
            (self.templates[:, :5], self.error, []),
            (self.templates, self.error, [np.zeros(6) * I]),
            (self.templates, self.error, [self.background, self.background * 2]),
            (self.templates, self.error, [np.ones(6)]),
            (self.templates, self.error, [np.ones(5) * I]),
            (self.templates, self.error, [np.ones(6) * u.m]),
            (u.Quantity(np.ones((1, 6), dtype=bool), I / u.Jy, dtype=bool), self.error, []),
            (self.templates, u.Quantity(np.ones(6, dtype=bool), I, dtype=bool), []),
            (self.templates, self.error, [u.Quantity(np.ones(6, dtype=bool), I, dtype=bool)]),
            (np.ones((1, 6)) * u.m / u.Jy, np.ones(6) * u.m, []),
            (np.ones((1, 6)) * u.Hz / u.Jy, np.ones(6) * u.Hz, []),
        ]
        for templates, error, nuisance in bad_cases:
            with self.subTest(templates=templates, error=error, nuisance=nuisance):
                with self.assertRaises(ValueError):
                    prepare_operator(templates, error, nuisance, provenance='test')
        op = self.operator()
        for data in (self.data.value, self.data[:5], np.ones(6) * u.m,
                     np.array([1, 1, 1, 1, 1, np.nan]) * I,
                     u.Quantity(np.ones(6, dtype=bool), I, dtype=bool)):
            with self.assertRaises(ValueError):
                op.score(data)
        with self.assertRaises(ValueError):
            prepare_operator(self.templates, self.error, [], provenance=' ')

    def test_relative_near_collinearity_refused(self):
        b = self.background.value
        variation = np.array([-1., 1., 0., 0., 0., 0.])
        with self.assertRaisesRegex(ValueError, 'rank deficient'):
            prepare_operator(self.templates, self.error,
                [b * I, (b + 1e-12 * variation) * I], provenance='rank')
        with self.assertRaisesRegex(ValueError, 'projected norm'):
            prepare_operator(((b + 1e-12 * variation) * I / u.Jy)[None, :],
                self.error, [b * I], provenance='rank')

    def test_aggregate_rule_and_invalid_inputs(self):
        scores = np.array([[[1, -8], [2, 3], [0, 1], [-1, 2]],
                           [[2, -1], [1, -1], [4, -1], [0, -1]]])
        result = paired_presence_statistic(scores)
        np.testing.assert_array_equal(result['before'], [9, 5])
        np.testing.assert_array_equal(result['after'], [5, 16])
        np.testing.assert_array_equal(result['per_variant'], [5, 5])
        self.assertEqual(result['combined'], 5.)
        for bad in (np.zeros((2, 3, 1)), np.zeros((0, 4, 1)), np.ones((1, 4, 1), dtype=bool),
                    np.full((1, 4, 1), np.inf), np.array([[['x']]*4]),
                    np.ones((1, 4, 1)) * u.Jy):
            with self.assertRaises(ValueError):
                paired_presence_statistic(bad)

    def test_exact_binomial_upper(self):
        self.assertIsNone(binomial_upper(0, 0))
        self.assertEqual(binomial_upper(5, 5), 1.)
        self.assertAlmostEqual(binomial_upper(0, 999), 1 - .025 ** (1 / 999), places=14)
        self.assertAlmostEqual(binomial_upper(4, 999), beta.ppf(.975, 5, 995), places=14)
        for k, n, confidence in [(-1, 3, .95), (4, 3, .95), (0, -1, .95),
                                  (True, 3, .95), (1., 3, .95), (0, 3, 1), (0, 3, True)]:
            with self.assertRaises(ValueError):
                binomial_upper(k, n, confidence)

    def test_exact_binomial_lower_and_boolean_rejection(self):
        self.assertIsNone(binomial_lower(0, 0))
        self.assertEqual(binomial_lower(0, 999), 0.)
        self.assertAlmostEqual(binomial_lower(999, 999), .025 ** (1 / 999), places=14)
        self.assertAlmostEqual(binomial_lower(850, 999), beta.ppf(.025, 850, 150), places=14)
        for k, n in [(True, 3), (1., 3), (-1, 3), (4, 3)]:
            with self.assertRaises(ValueError):
                binomial_lower(k, n)


if __name__ == '__main__':
    unittest.main()
