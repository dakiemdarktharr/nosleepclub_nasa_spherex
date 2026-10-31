"""Analytic profiles test derivatives, sampled topology and refusal semantics."""
import unittest

import numpy as np
from astropy import units as u

from scripts.profile_landscape import ResidualSampler, probe, grid, components


class LandscapeTests(unittest.TestCase):
    def test_quadratic_residual_gradient_and_hessian(self):
        M = np.asarray([[2., .4], [.1, 1.3], [1., -.2]])
        offset = np.asarray([.3, -.2, .5]); p = np.asarray([.25, -.4])
        sampler = ResidualSampler(lambda x: M@x-offset, [0., 0.], 2.5)
        result = probe(sampler, p, [.004, .002, .001])
        for row in result['steps']:
            np.testing.assert_allclose(row['gradient_cost'], 2*M.T@(M@p-offset), atol=1e-10)
            np.testing.assert_allclose(row['gradient_residual'], row['gradient_cost'], atol=1e-10)
            np.testing.assert_allclose(row['hessian_cost'], 2*M.T@M, atol=2e-8)
            np.testing.assert_allclose(row['gauss_newton'], 2*M.T@M, atol=1e-10)
            self.assertEqual(row['residual_jacobian_scaled_rank'], 2)

    def test_double_well_changes_sampled_components_at_barrier(self):
        sampler = ResidualSampler(lambda p: [p[0]**2-1, p[1]], [0., 0.], 2.)
        result = grid(sampler, np.linspace(-2, 2, 41), np.linspace(-2, 2, 41), [.1, 1.])
        self.assertEqual([r['component_count'] for r in result['sampled_connectivity']['levels']], [2, 2, 1, 1])
        saddle = probe(sampler, [0., 0.], [.002])['steps'][0]
        self.assertLess(saddle['hessian_cost_eigenvalues'][0], 0)
        self.assertGreaterEqual(saddle['gauss_newton_eigenvalues'][0], 0)

    def test_constant_cost_does_not_become_identified_minimum(self):
        sampler = ResidualSampler(lambda _: [2., -1.], [0., 0.], 2.5)
        row = probe(sampler, [0., 0.], [.002])['steps'][0]
        self.assertEqual(row['residual_jacobian_scaled_rank'], 0)
        self.assertIsNone(row['residual_jacobian_scaled_condition'])
        self.assertEqual(row['hessian_cost_eigenvalues'], [0., 0.])
        summary = grid(sampler, [-1., 0., 1.], [-1., 0., 1.], [0.])['sampled_connectivity']
        self.assertEqual(summary['levels'][0]['component_count'], 1)
        self.assertTrue(summary['levels'][0]['components'][0]['touches_grid_boundary'])

    def test_missing_nodes_retained_and_touch_reported(self):
        def residual(p):
            if p[0] == 0: raise ValueError('deliberate callback failure')
            return [1.]
        result = grid(ResidualSampler(residual, [0., 0.], 2.), [-1., 0., 1.], [-1., 0., 1.], [0.])
        self.assertEqual(len(result['failures']), 3)
        self.assertEqual(result['costs'][0], [1., None, 1.])
        for row in result['sampled_connectivity']['levels']:
            self.assertEqual(row['component_count'], 2)
            self.assertTrue(all(c['touches_missing_node'] for c in row['components']))
        self.assertEqual(components([[None, None]], [0.])['valid_nodes'], 0)

    def test_boundary_stencil_is_unavailable_without_clipping(self):
        result = probe(ResidualSampler(lambda p: p, [0., 0.], 2.5), [2.5, 0.], [.002])
        self.assertEqual(result['steps'][0]['error_codes'], ['outside_search_square'])

    def test_invalid_callback_output_is_explicit(self):
        for output in ([], [np.nan], [np.inf], [1+2j], [True, 1.], np.ones(2)*u.Jy, 'invalid'):
            with self.subTest(output=str(output)):
                item = ResidualSampler(lambda p: output, [0., 0.], 2.5).at([0., 0.])
                self.assertEqual(item['error_code'], 'invalid_residual')
        sampler = ResidualSampler(lambda p: [1.] if p[0] == 0 else [1., 2.], [0., 0.], 2.5)
        self.assertIn('cost', sampler.at([0., 0.]))
        self.assertEqual(sampler.at([1., 0.])['error_code'], 'residual_dimension_changed')
        self.assertEqual(ResidualSampler(lambda p: [1e308], [0., 0.], 2.5).at([0., 0.])['error_code'], 'nonfinite_cost')

    def test_invalid_controls_refused_before_callback(self):
        for anchor, bound in (([True, 0.], 2.), ([0., 0.], True), ([0., 0.], 0.), ([0.], 2.)):
            with self.subTest(anchor=anchor, bound=bound), self.assertRaises(ValueError):
                ResidualSampler(lambda p: p, anchor, bound)
        sampler = ResidualSampler(lambda p: p, [0., 0.], 2.5)
        for steps in ([0.], [True], [.1, .1], [np.inf]):
            with self.subTest(steps=steps), self.assertRaises(ValueError): probe(sampler, [0., 0.], steps)
        with self.assertRaises(ValueError): grid(sampler, [0., 0.], [0., 1.], [1.])

    def test_cost_topology_rejects_non_json_values_instead_of_coercing_them(self):
        for costs in ([[True, False]], [[np.nan]], [[np.inf]], [[-1.]], [[1., None], [2.]],
                      np.ones((2, 2))*u.one, [[1.*u.one]], [[1+0j]], [[[]]], [], np.array(1.), np.array([1., 2.])):
            with self.subTest(costs=str(costs)), self.assertRaises(ValueError): components(costs, [1.])

    def test_cached_residual_and_anchor_cannot_be_mutated_by_caller(self):
        anchor = np.asarray([0., 0.]); sampler = ResidualSampler(lambda p: p+1, anchor, 2.5)
        anchor[:] = 100.
        first = sampler.at([0., 0.]); first['residual'][:] = 100.
        np.testing.assert_array_equal(sampler.at([0., 0.])['residual'], [1., 1.])


if __name__ == '__main__': unittest.main()
