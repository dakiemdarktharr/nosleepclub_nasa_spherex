"""Independent publisher arithmetic and saved-input integrity checks."""
import copy
import unittest

import numpy as np

from scripts import publish_shape_calibration as publish


def fixture():
    cells = [];old = {};R0 = np.array([[1., -1., 0., 0.], [0., 1., -1., 0.], [0., 0., 1., -1.]])*.1
    error = np.array([1., 2., 3., 4.]);weights = np.array([.8, .9, .7, 1.]);residual = np.array([.3, -.2, .1, -.4])
    white = np.sqrt(weights)/error
    for source, amplitude in (('a', 1.), ('b', 2.), ('c', 4.)):
        R = amplitude*R0;P = R/white[None, :];key = (source, 'same-image')
        cells.append({'source_id': source, 'obs_id': key[1], 'baseline_checksum': source,
            'x': [0, 1, 2, 3], 'y': [0, 0, 0, 0], 'error': error.tolist(),
            'shape_score_pixel_response': R.tolist(), 'shape_information_scaled': (P@P.T).tolist(),
            'shape_score_scaled': (R@residual).tolist()})
        old[key] = {'_checksum': source, 'samples': [{'x': [0, 1, 2, 3], 'y': [0, 0, 0, 0],
            'error_mjysr': error.tolist(), 'data_mjysr': (residual+2.).tolist()}],
            'fit': {'frames': [{'obs_id': key[1], 'weights': weights.tolist(),
                               'error': error.tolist(), 'residual': residual.tolist()}]}}
    return cells, old, R0, error, weights, residual


class CalibrationPublicationTests(unittest.TestCase):
    def test_independent_weight_and_duplicate_physical_pixel_propagation(self):
        cells, old, R, error, weights, residual = fixture()
        result = publish.audit_arrays(cells, old)
        F0 = (R/(np.sqrt(weights)/error)[None, :])@(R/(np.sqrt(weights)/error)[None, :]).T
        self.assertEqual(result['source_weights'], {'a': 4., 'b': 1., 'c': .25})
        np.testing.assert_allclose(result['information'], F0*12, atol=1e-14)
        expected = np.linalg.solve(F0*12, R@residual*7)
        G = np.linalg.solve(F0*12, R*7)
        np.testing.assert_allclose(result['scaled_values'], expected, atol=1e-13)
        np.testing.assert_allclose(result['scaled_covariance'], G@np.diag(error**2)@G.T, atol=1e-13)
        self.assertEqual(result['unique_pixels'], 4)
        self.assertLess(result['maximum_projected_data_score_gap'], 1e-15)

    def test_changed_saved_pixel_identity_error_or_algebra_refused(self):
        for mutation in ('checksum', 'x', 'error', 'information', 'score', 'model_projection', 'duplicate'):
            cells, old, *_ = fixture();cells = copy.deepcopy(cells)
            if mutation == 'checksum':cells[0]['baseline_checksum'] = 'wrong'
            if mutation == 'x':cells[0]['x'][0] = 99
            if mutation == 'error':cells[0]['error'][0] += .1
            if mutation == 'information':cells[0]['shape_information_scaled'][0][0] += .1
            if mutation == 'score':cells[0]['shape_score_scaled'][0] += .1
            if mutation == 'model_projection':old[('a', 'same-image')]['samples'][0]['data_mjysr'][0] += .1
            if mutation == 'duplicate':cells.append(cells[0])
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):publish.audit_arrays(cells, old)


if __name__ == '__main__':
    unittest.main()
