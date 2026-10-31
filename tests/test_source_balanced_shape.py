"""Independent deterministic checks of source weighting and shared pixels."""
import copy
import unittest

import numpy as np

from scripts import composite_shape_update as shape
from scripts import shared_pixel_covariance as shared
from scripts import source_balanced_shape as balance
from scripts.moment_preserving_epsf import DEFAULT_BOUNDS


def synthetic_cells():
    # Unequal brightness and exposure counts, with two overlapping pixels per
    # exposure. Values are deterministic and do not use astronomical data.
    cells = []
    for source, strength, exposures in [('a', 1., 2), ('b', 3., 1), ('c', 7., 2)]:
        for j in range(exposures):
            obs = f'e{j}'
            index = len(cells) + 1
            F = strength * np.array([[2., .2, 0.], [.2, 1.5, .1], [0., .1, 1.]])
            score = strength * np.array([.03 * index, -.02, .01])
            response = strength * np.array([[.2, .1], [-.1, .3], [.05, -.2]])
            cells.append({'key': [source, obs], 'source_id': source, 'obs_id': obs,
                          'x': [0, 1], 'y': [0, 0], 'error': [1., 2.],
                          'shape_information_scaled': F, 'shape_score_scaled': score,
                          'shape_score_pixel_response': response})
    return cells


class SourceBalanceTests(unittest.TestCase):
    def test_weighted_equations_and_overlap_covariance(self):
        cells = synthetic_cells()
        result = balance.balance_sources(cells)
        # The traces are proportional to 1, 3, 7; per-exposure means make
        # the reference 3 even though source counts differ.
        weights = {'a': 3., 'b': 1., 'c': 3. / 7.}
        self.assertEqual(result.source_counts, {'a': 2, 'b': 1, 'c': 2})
        for source in weights:
            self.assertAlmostEqual(result.source_weights[source], weights[source])
        F = sum((weights[c['source_id']] * c['shape_information_scaled'] for c in cells), np.zeros((3, 3)))
        score = sum((weights[c['source_id']] * c['shape_score_scaled'] for c in cells), np.zeros(3))
        # Registry order is e0 pixel 0, e0 pixel 1, e1 pixel 0, e1 pixel 1.
        response = np.zeros((3, 4))
        for cell in cells:
            offset = 0 if cell['obs_id'] == 'e0' else 2
            response[:, offset:offset + 2] += weights[cell['source_id']] * cell['shape_score_pixel_response']
        registry = shared.make_registry(cells)
        update = shape.solve_update(result.cells, registry, min_sources=3,
                                    max_source_fraction=1., maximum_scaled_sigma=100.)
        scales = np.asarray(DEFAULT_BOUNDS)
        G = scales[:, None] * np.linalg.solve(F, response)
        expected_cov = G @ np.diag([1., 4., 1., 4.]) @ G.T
        np.testing.assert_allclose(update.scaled_information, F, rtol=1e-13)
        np.testing.assert_allclose(update.values, scales * np.linalg.solve(F, score), rtol=1e-13)
        np.testing.assert_allclose(update.pixel_influence, G, rtol=1e-13)
        np.testing.assert_allclose(update.covariance, expected_cov, rtol=1e-13)
        self.assertEqual(len(registry.keys), 4)
        self.assertGreater(np.linalg.norm(expected_cov - scales[:, None] * np.linalg.inv(F) * scales[None, :]), 1e-5)

        positions = [{**cells[0], 'position_pixel_influence': [[.2, -.1], [.4, .3]],
                      'position_shape_response': [[.3, -.1, .2], [.1, .2, -.3]]},
                     {**cells[-1], 'position_pixel_influence': [[-.3, .2], [.1, .5]],
                      'position_shape_response': [[-.2, .3, .1], [.4, -.1, .2]]}]
        A = np.array([[.2, -.1, 0., 0.], [.4, .3, 0., 0.],
                      [0., 0., -.3, .2], [0., 0., .1, .5]])
        R = np.vstack([p['position_shape_response'] for p in positions])
        B = A + R @ G
        position = shared.position_covariance(registry, positions, shape_pixel_influence=update.pixel_influence)
        np.testing.assert_allclose(position['covariance_px2'], B @ np.diag([1., 4., 1., 4.]) @ B.T, rtol=1e-13, atol=1e-15)
        self.assertGreater(np.linalg.norm(A @ np.diag([1., 4., 1., 4.]) @ G.T), 0.)

        # A global multiplier of all balancing weights changes neither solve
        # nor the pixel sandwich covariance; exposure ordering also cannot.
        scaled = copy.deepcopy(result.cells)
        for cell in scaled:
            for name in ('shape_information_scaled', 'shape_score_scaled', 'shape_score_pixel_response'):
                cell[name] *= 13.
        other = shape.solve_update(tuple(reversed(scaled)), registry, min_sources=3,
                                   max_source_fraction=1., maximum_scaled_sigma=100.)
        np.testing.assert_allclose(other.values, update.values, rtol=1e-13)
        np.testing.assert_allclose(other.covariance, update.covariance, rtol=1e-13)
        reordered = balance.balance_sources(list(reversed(cells)))
        self.assertEqual(reordered.source_counts, result.source_counts)
        for source in weights:
            self.assertAlmostEqual(reordered.source_weights[source], result.source_weights[source])

    def test_weights_do_not_depend_on_scores_and_feasibility_scrubs_them(self):
        cells = synthetic_cells()
        original = balance.balance_sources(cells)
        altered = copy.deepcopy(cells)
        for i, cell in enumerate(altered):
            cell['shape_score_scaled'] = np.array([1e5 * i, -2., 9.])
            cell['shape_score_pixel_response'] *= -7.
        self.assertEqual(balance.balance_sources(altered).source_weights, original.source_weights)
        feasibility = balance.balance_sources(altered, include_scores=False)
        for cell in feasibility.cells:
            self.assertNotIn('shape_score_scaled', cell)
            self.assertNotIn('shape_score_pixel_response', cell)

    def test_bad_inputs_and_unrepresentable_products_refused(self):
        cells = synthetic_cells()
        for mutation in ('indefinite', 'asymmetric', 'zero', 'identity', 'null_key', 'duplicate', 'sum_overflow'):
            bad = copy.deepcopy(cells)
            if mutation == 'indefinite': bad[0]['shape_information_scaled'] = np.diag([-1., 1., 1.])
            if mutation == 'asymmetric': bad[0]['shape_information_scaled'][0, 1] += 1.
            if mutation == 'zero':
                for cell in bad:
                    if cell['source_id'] == 'a': cell['shape_information_scaled'] = np.zeros((3, 3))
            if mutation == 'identity': bad[0]['key'] = ['wrong', 'e0']
            if mutation == 'null_key': bad[0]['key'] = None
            if mutation == 'duplicate': bad[1] = copy.deepcopy(bad[0])
            if mutation == 'sum_overflow':
                for cell in bad:
                    if cell['source_id'] == 'a': cell['shape_information_scaled'] = np.eye(3)*1e308
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                balance.balance_sources(bad)
        for field in ('shape_score_scaled', 'shape_score_pixel_response'):
            bad = copy.deepcopy(cells)
            for cell in bad:
                if cell['source_id'] == 'a': cell['shape_information_scaled'] *= 1e-307
            bad[0][field] = np.full_like(bad[0][field], 100.)
            with self.subTest(field=field), np.errstate(over='ignore', invalid='ignore'), self.assertRaises(ValueError):
                balance.balance_sources(bad)


if __name__ == '__main__': unittest.main()
