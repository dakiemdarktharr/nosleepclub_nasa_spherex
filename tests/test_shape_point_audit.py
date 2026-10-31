"""Synthetic fixed-position audit tests; no optimization or sky data."""
import copy
import unittest
from unittest.mock import patch

import astropy.units as u
import numpy as np

from scripts import audit_shape_points as audit


class ShapePointAuditTests(unittest.TestCase):
    def test_gate_reconstructs_change_from_saved_positions_and_retains_failure(self):
        keys = [('s1', 'e1'), ('s2', 'e1')]
        score = [{'key': list(k), 'payload': {'status': 'information_available',
                  'position_shape_response': [[1., 0., 0.], [0., 1., 0.]]}} for k in keys]
        old = {k: {'status': 'fit_completed', 'fit': {'position': [1., 2.],
               'numerical_support': True}} for k in keys}
        point = {keys[0]: {'status': 'fit_completed', 'fit': {'position': [1.01, 1.995],
                            'numerical_support': True}, 'position_change_common_px': [.01, -.005]},
                 keys[1]: {'status': 'fit_completed', 'fit': {'position': [1., 2.],
                            'numerical_support': False, 'numerical_reasons': ['multiple_near_best_modes']}}}
        calculated = audit.reconstruct_gate(score, point, old, [.01, -.005, 0.])
        self.assertEqual(len(calculated['comparisons']), 1)
        self.assertEqual(calculated['failures'], [{'key': list(keys[1]), 'reason': ['multiple_near_best_modes']}])
        self.assertAlmostEqual(calculated['max'], 0., places=14)
        gate = {'assessment_allowed': False, 'promotion': False,
                'reasons': ['old_numerical_cell_no_longer_supported'],
                'failures': calculated['failures'], 'comparisons': calculated['comparisons'],
                'linearization_error_p90_common_px': calculated['p90'],
                'linearization_error_max_common_px': calculated['max']}
        audit.verify_gate(gate, calculated)
        for mutation in ('allowed', 'omitted_failure', 'incorrect_delta', 'drifted_position'):
            bad_gate = copy.deepcopy(gate);bad_point = copy.deepcopy(point)
            if mutation == 'allowed':bad_gate['assessment_allowed'] = True
            if mutation == 'omitted_failure':bad_gate['failures'] = []
            if mutation == 'incorrect_delta':bad_gate['comparisons'][0]['predicted_change_common_px'][0] = .3
            if mutation == 'drifted_position':bad_point[keys[0]]['position_change_common_px'] = [9., 9.]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                rec = audit.reconstruct_gate(score, bad_point, old, [.01, -.005, 0.])
                audit.verify_gate(bad_gate, rec)

    def test_native_preserves_baseline_and_calls_auditor_at_saved_point(self):
        meta = {'anchor_sky_px': [0., 0.]};unit = u.MJy/u.sr/u.Jy
        item = {'metadata': {'x': [0, 1], 'y': [0, 0]}, 'neighbor_ids': [],
                'data': np.array([3., 4.]), 'error': np.array([1., 2.]),
                'background_design': np.ones((2, 1)), 'neighbor_design': np.empty((2, 0)),
                'renderer': lambda p: np.array([1., 2.])*unit}
        old = {'metadata': meta, 'samples': [{'x': [0, 1], 'y': [0, 0], 'neighbor_ids': [],
               'data_mjysr': [3., 4.], 'error_mjysr': [1., 2.], 'background_design': [[1.], [1.]]}],
               'fit': {'position': [.1, .2], 'numerical_support': True},
               'residual_east_north_arcsec': [.3, .4]}
        row = {'metadata': meta, 'baseline_numerical_support': True, 'baseline_position': [.1, .2],
               'baseline_residual_east_north_arcsec': [.3, .4], 'position_change_common_px': [.01, .01],
               'fit': {'position': [.11, .21], 'frames': [{'target_flux_jy': 1.,
               'background_coefficients': [2.], 'neighbor_flux_jy': [], 'model': [3., 4.]}]}}
        reported = {'frame': {'max_scaled_kkt_violation': 1e-12},
                    'final_start_replay': {'successful_start_count': 9, 'failed_start_count': 0,
                                           'max_absolute_difference': 1e-11}}
        with patch.object(audit.point_auditor, 'audit_point', return_value=reported) as verify:
            output = audit.audit_native(row, old, item, meta)
            self.assertEqual(output['successful_final_starts'], 9)
            self.assertEqual(output['maximum_model_delta_mjysr'], 0.)
            verify.assert_called_once()
        bad = copy.deepcopy(old);bad['samples'][0]['error_mjysr'][0] = 10.
        with self.assertRaisesRegex(ValueError, 'unchanged error'):
            audit.audit_native(row, bad, item, meta)


if __name__ == '__main__':unittest.main()
