"""Synthetic checks of independent covariance and native QR audits."""
import copy
import unittest

import astropy.units as u
import numpy as np

from scripts.audit_reference_covariance import assemble_independently, audit_native, compare


class CovarianceAuditTests(unittest.TestCase):
    def test_closed_form_overlap_gaia_and_heldout_cross_terms(self):
        cells = []
        J = np.zeros((2, 5));J[0, 0] = J[1, 1] = 1.
        for i in range(5):
            cells.append({'key': [f's{i}', 'e'], 'source_id': f's{i}', 'obs_id': 'e',
                'x': [0, 2*i+1, 2*i+2], 'y': [0, 0, 0], 'error': [1., 1., 1.],
                'position_pixel_influence': [[.1*(-1)**i, 1., 0.], [.2, 0., 1.]],
                'raw_offset_px': [.1*i, -.2*i],
                'metadata': {'gaia_jacobian_px_per_catalog_unit': J,
                             'gaia_covariance_catalog_units': np.eye(5)*.1}})
        result = assemble_independently(cells, {'s0', 's1', 's2', 's3'}, ['e'])
        shared = np.array([v for i in range(5) for v in (.1*(-1)**i, .2)])
        pixel = np.eye(10)+np.outer(shared, shared)
        expected_C = pixel+np.eye(10)*.1
        np.testing.assert_allclose(result['pixel'], pixel, atol=1e-14)
        np.testing.assert_allclose(result['catalogue'], np.eye(10)*.1, atol=1e-14)
        np.testing.assert_allclose(result['total'], expected_C, atol=1e-14)
        self.assertLess(result['pixel'][0, 2], 0.)
        self.assertEqual(result['unique_pixels'], 11)
        H = np.tile(np.eye(2), (4, 1));Ccc = expected_C[:8, :8]
        L = np.linalg.solve(H.T@np.linalg.solve(Ccc, H), H.T@np.linalg.inv(Ccc))
        y = np.array([v for i in range(5) for v in (.1*i, -.2*i)])
        M = np.column_stack((-L, np.eye(2)))
        V = M@expected_C@M.T;r = M@y
        np.testing.assert_allclose(result['beta'], L@y[:8], atol=1e-13)
        np.testing.assert_allclose(result['heldout_covariance'], V, atol=1e-13)
        np.testing.assert_allclose(result['residual'], r, atol=1e-13)
        self.assertAlmostEqual(result['heldout_chi2'], r@np.linalg.solve(V, r), places=12)
        shortcut = expected_C[8:, 8:]+L@Ccc@L.T
        self.assertGreater(np.linalg.norm(V-shortcut), .001)
        bad = copy.deepcopy(cells);bad[0]['error'][0] = 2.
        with self.assertRaisesRegex(ValueError, 'inconsistent variance'):
            assemble_independently(bad, {'s0', 's1', 's2', 's3'}, ['e'])

    def test_native_qr_against_explicit_weighted_normal_equations(self):
        x = np.linspace(-1., 1., 14)
        base = np.cos(2.2*x);dx = np.sin(2.3*x);dy = x*x
        background = np.column_stack((np.ones(len(x)), x, x*x*x))
        target_flux = 2.3;pos = np.array([.1, -.2]);weights = np.linspace(.5, 1., len(x))
        error = np.linspace(.8, 1.4, len(x));beta = np.array([.1, -.2, .3])
        def renderer(p):return (base+p[0]*dx+p[1]*dy)*(u.MJy/u.sr/u.Jy)
        target = renderer(pos).value;residual = np.sin(3*x)*.01
        data = target_flux*target+background@beta+residual
        J = np.column_stack((target_flux*dx, target_flux*dy, target, background))
        W = np.diag(weights/error**2)
        influence = np.linalg.solve(J.T@W@J, J.T@W)[:2]
        meta = {'anchor_sky_px': [0., 0.]}
        item = {'data': data, 'error': error, 'background_design': background,
                'neighbor_design': np.empty((len(x), 0)), 'neighbor_ids': [],
                'neighbor_unit': 'MJy / (Jy sr)', 'renderer': renderer,
                'metadata': {'x': list(range(len(x))), 'y': [0]*len(x)}}
        frame = {'obs_id': 'e', 'error': error.tolist(), 'weights': weights.tolist(),
                 'target_flux_jy': target_flux, 'neighbor_ids': [], 'neighbor_flux_jy': [],
                 'background_coefficients': beta.tolist(), 'residual': residual.tolist()}
        saved = {'payload': {'metadata': meta, 'fit': {'position': pos.tolist(), 'frames': [frame],
                           'data_unit': 'MJy / sr'}, 'samples': [{'x': item['metadata']['x'],
                           'y': item['metadata']['y'], 'data_mjysr': data.tolist(), 'error_mjysr': error.tolist(),
                           'background_design': background.tolist(), 'neighbor_design_per_jy': item['neighbor_design'].tolist(),
                           'neighbor_ids': [], 'neighbor_unit': item['neighbor_unit']}]}}
        cell = {'obs_id': 'e', 'x': item['metadata']['x'], 'y': item['metadata']['y'],
                'error': error.tolist(), 'position_pixel_influence': influence}
        maxima = {};audit_native(item, meta, saved, cell, maxima)
        self.assertLess(maxima['position_influence'], 1e-10)
        bad = copy.deepcopy(cell);bad['position_pixel_influence'][0, 0] += .1
        with self.assertRaisesRegex(ValueError, 'position_influence'):
            audit_native(item, meta, saved, bad, {})

    def test_comparison_refuses_mismatch_and_nonfinite(self):
        for value in ([1., 2.], [np.nan, 1.]):
            with self.assertRaises(ValueError):compare(value, [1., 1.], 'synthetic', {})


if __name__ == '__main__':unittest.main()
