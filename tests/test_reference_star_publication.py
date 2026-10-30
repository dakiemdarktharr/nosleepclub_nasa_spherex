import copy
import unittest

import numpy as np

from scripts import publish_reference_stars as pub
from scripts import run_wise_linked_study as legacy
from tests.test_neighbor_epoch_model import make_frames, XY


def envelope(source, obs, variant, residual, supported=False):
    if residual is None:
        payload = {'status': 'fit_failed', 'error': 'retained failure'}
    else:
        payload = {'status': 'fit_completed', 'residual_east_north_arcsec': residual,
                   'fit': {'numerical_support': supported, 'numerical_reasons': [] if supported else ['boundary'],
                           'frames': [{'negative_target_flux': False}]}}
    return {'key': [source, obs, variant], 'payload': payload}


class ReferencePublicationTests(unittest.TestCase):
    def test_pair_denominators_and_empty_common_supported(self):
        rows = [envelope('a', 'one', 'nearest', [3., 4.]),
                envelope('a', 'one', 'bilinear', [0., 4.]),
                envelope('a', 'two', 'nearest', [0., 0.], True),
                envelope('a', 'two', 'bilinear', None)]
        result = pub.paired_summary(rows)
        self.assertEqual((result['planned_pairs'], result['common_completed'], result['common_numerical']), (2, 1, 0))
        a, b = result['arms']
        self.assertEqual((a['completed'], b['completed'], b['failed']), (2, 1, 1))
        self.assertEqual(a['common_completed']['rms_arcsec'], 5.)
        self.assertEqual(b['common_completed']['rms_arcsec'], 4.)
        self.assertIsNone(a['common_numerical']['rms_arcsec'])
        self.assertEqual(result['maximum_model_shift_arcsec'], 3.)

    def test_exact_spherical_residual_signs(self):
        a = np.array([31.5, 31.5])
        np.testing.assert_allclose(pub.study.sky_residual_arcsec(a, a), [0., 0.], atol=1e-9, rtol=0.)
        east, north = pub.study.sky_residual_arcsec(a + [.1, .1], a)
        self.assertLess(east, 0.)
        self.assertGreater(north, 0.)

    def test_saved_point_and_final_start_costs_replay_and_tamper_refused(self):
        raw = make_frames()[:1]
        fit = pub.study.model.fit_epoch(raw, [0., 0.], data_unit='MJy/sr', nonnegative_neighbors=False)
        item = {**raw[0], 'metadata': {'x': XY[:, 0].astype(int).tolist(), 'y': XY[:, 1].astype(int).tolist()}}
        row = {'fit': legacy.jsonable(fit), 'samples': pub.study.previous.descriptors([item]),
               'residual_east_north_arcsec': pub.study.sky_residual_arcsec(fit['position'], [0., 0.])}
        audit = pub.audit_point(row, item, np.zeros(2))
        self.assertEqual(audit['final_start_replay']['successful_start_count'], 9)
        self.assertLess(audit['frame']['max_scaled_kkt_violation'], 1e-8)
        altered = copy.deepcopy(row);altered['fit']['frames'][0]['model'][0] += .1
        with self.assertRaisesRegex(ValueError, 'frame model'):
            pub.audit_point(altered, item, np.zeros(2))
        altered = copy.deepcopy(row);altered['fit']['final_mode_audit']['starts'][0]['chi2'] += .1
        with self.assertRaises(ValueError):
            pub.audit_point(altered, item, np.zeros(2))


if __name__ == '__main__':
    unittest.main()
