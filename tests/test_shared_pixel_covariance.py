"""Deterministic overlap and shared-catalog covariance contracts."""
import copy
import unittest

import numpy as np

from scripts import shared_pixel_covariance as shared


def samples():
    one = {'obs_id': 'frame', 'x': [0, 1, 2], 'y': [0, 0, 0], 'error': [1., 2., 3.],
           'position_pixel_influence': [[1., .2, -.1], [0., .5, 1.]],
           'position_shape_response': [[1., -.5, 0.], [-.3, 0., .2]]}
    two = {'obs_id': 'frame', 'x': [1, 2, 3], 'y': [0, 0, 0], 'error': [2., 3., 4.],
           'position_pixel_influence': [[-1., .4, .3], [.4, -.2, 1.]],
           'position_shape_response': [[-.2, .7, .1], [.5, -.4, -.2]]}
    return [one, two]


class SharedPixelCovarianceTests(unittest.TestCase):
    def test_exact_dense_B_with_both_overlap_cross_terms(self):
        rows = samples();registry = shared.make_registry(rows)
        G = np.array([[.1, -.2, .3, .05], [-.1, .4, .02, -.2], [.05, .1, -.3, .1]])
        result = shared.position_covariance(registry, rows, shape_pixel_influence=G)
        A = np.array([[1., .2, -.1, 0.], [0., .5, 1., 0.],
                      [0., -1., .4, .3], [0., .4, -.2, 1.]])
        R = np.vstack([r['position_shape_response'] for r in rows])
        C = np.diag([1., 4., 9., 16.]);B = A+R@G
        expected = B@C@B.T
        direct = A@C@A.T;shape = R@G@C@G.T@R.T
        left = A@C@G.T@R.T;right = R@G@C@A.T
        np.testing.assert_allclose(result['covariance_px2'], expected, atol=1e-13)
        np.testing.assert_allclose(result['pixel_only_covariance_px2'], direct, atol=1e-13)
        np.testing.assert_allclose(result['shape_covariance_physical_units'], G@C@G.T, atol=1e-13)
        np.testing.assert_allclose(result['position_shape_covariance'], A@C@G.T, atol=1e-13)
        np.testing.assert_allclose(expected, direct+shape+left+right, atol=1e-13)
        self.assertGreater(left.max(), 0.);self.assertLess(left.min(), 0.)
        self.assertGreater(abs(direct[0, 2]), 0.)  # same pixels induce cross-source covariance
        self.assertEqual(len(registry.keys), 4)

    def test_same_pixel_response_sums_and_negative_cross_covariance(self):
        rows = samples();registry = shared.make_registry(rows)
        records = [{**rows[0], 'response': [[1., 2., -1.]]},
                   {**rows[1], 'response': [[-3., .5, 1.]]}]
        response = shared.add_pixel_response(registry, records, response_key='response', output_rows=1)
        np.testing.assert_array_equal(response, [[1., -1., -.5, 1.]])
        result = shared.position_covariance(registry, rows)
        self.assertLess(result['covariance_px2'][0, 2], 0.)

    def test_pixel_registry_refuses_ambiguous_or_invalid_inputs(self):
        rows = samples()
        for mutate in ('duplicate', 'negative_coordinate', 'fractional_coordinate', 'obs_id', 'variance', 'nonpositive', 'nan'):
            bad = copy.deepcopy(rows)
            if mutate == 'duplicate': bad[0]['x'][1] = bad[0]['x'][0]
            if mutate == 'negative_coordinate': bad[0]['x'][0] = -1
            if mutate == 'fractional_coordinate': bad[0]['x'][0] = .5
            if mutate == 'obs_id': bad[0]['obs_id'] = ''
            if mutate == 'variance': bad[1]['error'][0] = 2.1
            if mutate == 'nonpositive': bad[0]['error'][0] = -1.
            if mutate == 'nan': bad[0]['error'][0] = np.nan
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): shared.make_registry(bad)
        registry = shared.make_registry(rows)
        for method in ('response', 'position'):
            bad = copy.deepcopy(rows);bad[0]['error'][0] = -1.
            bad[0]['response'] = np.ones((1, 3));bad[1]['response'] = np.ones((1, 3))
            with self.subTest(method=method), self.assertRaises(ValueError):
                if method == 'response': shared.add_pixel_response(registry, bad, response_key='response', output_rows=1)
                else: shared.position_covariance(registry, bad)

    def test_shared_gaia_parameters_cross_time_not_cross_star(self):
        C1 = np.diag([1., 2., 3., 4., 5.]);C2 = np.diag([2., 3., 4., 5., 6.])
        j1 = np.array([[1., 0., 1., 2., 0.], [0., 1., -1., 0., 2.]])
        j2 = np.array([[1., 0., -1., 3., 0.], [0., 1., .5, 0., 3.]])
        j3 = np.array([[1., 0., 0., 4., 0.], [0., 1., 0., 0., 4.]])
        result = shared.catalogue_covariance(['a', 'b', 'a'], [j1, j3, j2], {'a': C1, 'b': C2})
        np.testing.assert_allclose(result[:2, 4:6], j1@C1@j2.T)
        np.testing.assert_allclose(result[:2, 2:4], 0.)
        np.testing.assert_allclose(result[2:4, 2:4], j3@C2@j3.T)
        self.assertGreater(np.linalg.norm(result[:2, 4:]), 0.)
        self.assertGreaterEqual(np.linalg.eigvalsh(result).min(), -1e-12)
        for ids, cov in [(['a', '', 'a'], {'a': C1, '': C2}), (['a', 'b', 'a'], {'a': C1}),
                         (['a', 'b', 'a'], {'a': np.zeros((5, 5)), 'b': C2})]:
            with self.subTest(ids=ids), self.assertRaises((ValueError, np.linalg.LinAlgError)):
                shared.catalogue_covariance(ids, [j1, j3, j2], cov)


if __name__ == '__main__': unittest.main()
