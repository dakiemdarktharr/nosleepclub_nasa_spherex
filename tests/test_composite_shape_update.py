"""Three-parameter composite linear score with fixed synthetic shared pixels."""
import copy
import unittest

import numpy as np
from scipy.linalg import eigh

from scripts import composite_shape_update as shape
from scripts import shared_pixel_covariance as shared
from scripts.moment_preserving_epsf import DEFAULT_BOUNDS


def cells(overlap=True):
    z = np.array([.2, -.15, .1]);diagonal = np.array([1., 1.5, 2.])
    rows = []
    for i in range(8):
        response = np.diag(np.sqrt(diagonal))
        obs = 'shared' if overlap else f'f{i}'
        rows.append({'key': [f's{i}', obs], 'source_id': f's{i}', 'obs_id': obs,
                     'x': [0, 1, 2], 'y': [0, 0, 0], 'error': [1., 1., 1.],
                     'shape_information_scaled': np.diag(diagonal),
                     'shape_score_scaled': diagonal*z, 'shape_score_pixel_response': response})
    return rows, z


class CompositeShapeTests(unittest.TestCase):
    def test_exact_linear_update_and_unique_pixel_covariance(self):
        rows, z = cells();registry = shared.make_registry(rows)
        result = shape.solve_update(rows, registry, maximum_scaled_sigma=2.)
        scales = np.asarray(DEFAULT_BOUNDS);F = sum((r['shape_information_scaled'] for r in rows))
        sum_score = sum((r['shape_score_scaled'] for r in rows))
        Gscaled = np.linalg.solve(F, 8*np.diag(np.sqrt([1., 1.5, 2.])))
        expected_G = scales[:, None]*Gscaled
        np.testing.assert_allclose(result.values, z*scales, atol=1e-15)
        np.testing.assert_allclose(result.scaled_information, F, atol=1e-15)
        np.testing.assert_allclose(np.linalg.solve(F, sum_score), z, atol=1e-15)
        np.testing.assert_allclose(result.pixel_influence, expected_G, atol=1e-15)
        np.testing.assert_allclose(result.covariance, expected_G @ expected_G.T, atol=1e-15)
        self.assertGreater(result.covariance[0, 0], (np.linalg.inv(F)*scales[:, None]*scales[None, :])[0, 0]*7)
        self.assertEqual(len(registry.keys), 3)
        self.assertEqual(len(result.sources), 8)
        self.assertAlmostEqual(result.max_source_information_fraction, 1/8)

    def test_generalized_source_information_fraction(self):
        rows, _ = cells(False)
        rows[0]['shape_information_scaled'] = np.diag([.3, 1.4, .7])
        rows[1]['shape_information_scaled'] = np.array([[2., .2, 0.], [.2, 1., .1], [0., .1, .5]])
        info = shape.information(rows)
        F = sum((r['shape_information_scaled'] for r in rows))
        for row in rows:
            expected = eigh(row['shape_information_scaled'], F, eigvals_only=True)[-1]
            self.assertAlmostEqual(info['source_fractions'][row['source_id']], expected, places=12)
        self.assertEqual(info['sources'], tuple(sorted(row['source_id'] for row in rows)))

    def test_source_dominance_rank_bound_and_precision_abstain(self):
        rows, _ = cells();registry = shared.make_registry(rows)
        with self.assertRaisesRegex(ValueError, 'dominates'):
            shape.solve_update(rows, registry, max_source_fraction=.124, maximum_scaled_sigma=2.)
        with self.assertRaisesRegex(ValueError, 'precision'):
            shape.solve_update(rows, registry, maximum_scaled_sigma=.5)
        with self.assertRaisesRegex(ValueError, 'too few'):
            shape.information(rows, min_sources=9)
        bad = copy.deepcopy(rows)
        for cell in bad:cell['shape_information_scaled'][2, 2] = 0.
        with self.assertRaisesRegex(ValueError, 'information'):
            shape.information(bad)
        bad = copy.deepcopy(rows)
        for cell in bad:cell['shape_score_scaled'][0] = 2*cell['shape_information_scaled'][0, 0]
        with self.assertRaisesRegex(ValueError, 'bounds'):
            shape.solve_update(bad, registry, maximum_scaled_sigma=2.)
        bad = copy.deepcopy(rows);bad[1] = copy.deepcopy(bad[0])
        with self.assertRaisesRegex(ValueError, 'unique'):
            shape.information(bad)

    def test_refuse_indefinite_or_nonsymmetric_cell_even_if_sum_is_spd(self):
        rows, _ = cells();bad = copy.deepcopy(rows)
        bad[0]['shape_information_scaled'] = np.diag([-1., 1., 2.])
        self.assertGreater(np.linalg.eigvalsh(sum(r['shape_information_scaled'] for r in bad)).min(), 0.)
        with self.assertRaises(ValueError):shape.information(bad)
        bad = copy.deepcopy(rows);bad[0]['shape_information_scaled'][0, 1] = .1
        with self.assertRaisesRegex(ValueError, 'asymmetric'):shape.information(bad)
        for scale in (1e-15, 1e15):
            for mutation in ('indefinite', 'asymmetric'):
                bad = copy.deepcopy(rows)
                for cell in bad:
                    cell['shape_information_scaled'] = cell['shape_information_scaled']*scale
                if mutation == 'indefinite':bad[0]['shape_information_scaled'][0, 0] = -scale
                else:bad[0]['shape_information_scaled'][0, 1] = .1*scale
                with self.subTest(scale=scale, mutation=mutation), self.assertRaises(ValueError):
                    shape.information(bad)

    def test_bad_controls_and_cell_identities_refused(self):
        rows, _ = cells();registry = shared.make_registry(rows)
        for kwargs in ({'min_sources': True}, {'min_sources': 0}, {'max_condition': 1.},
                       {'max_condition': np.nan}, {'max_source_fraction': -1.},
                       {'max_source_fraction': np.nan}, {'maximum_scaled_sigma': -1.},
                       {'maximum_scaled_sigma': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                shape.solve_update(rows, registry, **kwargs)
        bad = copy.deepcopy(rows);bad[0]['key'] = ['other', 'e0']
        with self.assertRaises(ValueError):shape.information(bad)


if __name__ == '__main__': unittest.main()
