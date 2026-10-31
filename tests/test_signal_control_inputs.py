"""Synthetic-only tests of WCS, matched truth, shared pixels and provenance."""
import unittest
from unittest.mock import patch

import astropy.units as u
from astropy.wcs import WCS
import numpy as np

from scripts import signal_control_inputs as inputs


def geometry():
    y, x = np.mgrid[0:9, 0:9];x = x.ravel();y = y.ravel();n = len(x)
    error = np.linspace(.1, .2, n)
    render = lambda p: (np.exp(-((x-p[0])**2+(y-p[1])**2)/2)*1e5)*u.MJy/u.sr/u.Jy
    neighbor = render([5.75, 4.25]).value[:, None]
    base = {'data': np.zeros(n), 'error': error, 'neighbor_design': neighbor,
        'neighbor_ids': [inputs.COMPANION_ID], 'renderer': render,
        'metadata': {'neighbors': [{'id': inputs.COMPANION_ID}]}}
    corrected = {**base, 'renderer': lambda p: 2*render(p), 'neighbor_design': 2*neighbor,
        'neighbor_shape_design': np.ones((n, 1, 3)),
        'metadata': {**base['metadata'], 'corrected_neighbors': [{'id': inputs.COMPANION_ID}]}}
    models = {}
    for arm, item in (('baseline', base), ('corrected', corrected)):
        models[(arm, True)] = (item, None)
        empty = {**item, 'neighbor_design': np.empty((n, 0)), 'neighbor_ids': [],
                 'metadata': {**item['metadata'], 'neighbors': []}}
        if arm == 'corrected':
            empty['metadata']['corrected_neighbors'] = []
            empty['neighbor_shape_design'] = np.empty((n, 0, 3))
        models[(arm, False)] = (empty, None)
    center = {'center_omega_sr': 1e-9, 'pixel_to_center_omega_ratio_range': [.8, 1.2]}
    return {'x': x, 'y': y, 'omega': np.linspace(8e-10, 1.2e-9, n)*u.sr,
        'target_native': np.array([4.25, 4.25]), 'companion_native': np.array([5.75, 4.25]),
        'target_common': np.array([4.25, 4.25]), '_models': models,
        '_center_areas': {'target': center, 'companion': center}, 'background': np.full(n, .04),
        'error': error, 'frame': {'data': np.zeros((9, 9))}, 'phase': 0,
        }


class SignalInputTests(unittest.TestCase):
    def test_wcs_inverse_keeps_registration_offset_and_roundtrips_native(self):
        common = WCS(naxis=2); common.wcs.crpix = [40., 35.];common.wcs.crval = [133.7, -7.2]
        common.wcs.cd = np.array([[-.0017, .0001], [.0002, .0017]]); common.wcs.ctype = ['RA---TAN', 'DEC--TAN']
        native = common.deepcopy();native.wcs.crpix = [50., 60.]
        frame = {'wcs': native, 'offset': np.array([.2, -.3])}
        with patch.object(inputs.original.gaia.motion, 'WCS', common):
            p = inputs.common_from_native(frame, [47.25, 62.75])
            np.testing.assert_allclose(inputs.original.native_position(frame, p), [47.25, 62.75], atol=1e-7)
            np.testing.assert_allclose(p, [37.05, 38.05], atol=1e-7)

    def test_controlled_and_omitted_companion_share_truth_and_noise(self):
        g = geometry();bank = np.arange(81).reshape(9, 9)/100
        with patch.object(inputs, 'standardized_noise', return_value=bank):
            for family in ('matched', 'gaussian'):
                modeled = inputs.realize(g, 'noisy', family, 'modeled', 1200, 1)
                omitted = inputs.realize(g, 'noisy', family, 'omitted', 1200, 1)
                np.testing.assert_array_equal(modeled['data'], omitted['data'])
                self.assertEqual(modeled['metadata']['realization_sha256'], omitted['metadata']['realization_sha256'])
                np.testing.assert_allclose(modeled['data']-modeled['mean'], bank.ravel()*g['error'], atol=1e-14)
                self.assertFalse(modeled['metadata']['original_image_added'])

    def test_matched_truth_uses_original_renderer_and_keeps_signed_unit_scale(self):
        g = geometry(); result = inputs.realize(g, 'noiseless', 'matched', 'modeled', 600, 0)
        expected = .0006*(inputs.model_for(g, 'baseline', False)['renderer'](g['target_common']).value+
                          inputs.model_for(g, 'baseline', True)['neighbor_design'][:, 0])
        np.testing.assert_allclose(result['mean']-g['background'], expected)
        for arm in ('baseline', 'corrected'):
            item = inputs.fit_item(g, result, 'modeled', arm)
            np.testing.assert_array_equal(item['data'], result['data'])
            np.testing.assert_array_equal(item['error'], g['error'])

    def test_fitter_neighbor_columns_and_metadata_are_removed_together(self):
        g = geometry(); result = inputs.realize(g, 'noiseless', 'gaussian', 'modeled', 600, 0)
        for arm in ('baseline', 'corrected'):
            for scene in ('isolated', 'modeled', 'omitted'):
                item = inputs.fit_item(g, result, scene, arm);present = scene == 'modeled'
                self.assertEqual(item['neighbor_design'].shape[1], int(present))
                self.assertEqual(len(item['neighbor_ids']), int(present))
                self.assertEqual(len(item['metadata']['neighbors']), int(present))
                if arm == 'corrected':
                    self.assertEqual(len(item['metadata']['corrected_neighbors']), int(present))
                    self.assertEqual(item['neighbor_shape_design'].shape[1], int(present))
        self.assertEqual(len(inputs.model_for(g, 'corrected', True)['metadata']['corrected_neighbors']), 1)

    def test_model_preparation_failure_is_scoped_to_arm_and_neighbor(self):
        g = geometry(); g['_models'][('corrected', True)] = (None, 'synthetic companion refusal')
        result = inputs.realize(g, 'noiseless', 'gaussian', 'modeled', 600, 0)
        self.assertEqual(inputs.fit_item(g, result, 'modeled', 'baseline')['neighbor_design'].shape[1], 1)
        for scene in ('isolated', 'omitted'):
            self.assertEqual(inputs.fit_item(g, result, scene, 'corrected')['neighbor_design'].shape[1], 0)
        with self.assertRaisesRegex(ValueError, 'synthetic companion refusal'):
            inputs.fit_item(g, result, 'modeled', 'corrected')

    def test_noise_bank_uses_physical_pixel_identity_and_is_read_only(self):
        bank = inputs.standardized_noise((9, 9), 2, prefix=17)
        np.testing.assert_array_equal(bank, inputs.standardized_noise((9, 9), 2, prefix=17))
        self.assertFalse(np.array_equal(bank, inputs.standardized_noise((9, 9), 3, prefix=17)))
        self.assertEqual(bank[[1, 2], [3, 4]][1], bank[[2, 8], [4, 0]][0])
        with self.assertRaises(ValueError): bank[0, 0] = 0
        for shape, draw in (((True, 9), 0), ((9, 9), True), ((9, 9), 16)):
            with self.assertRaises(ValueError): inputs.standardized_noise(shape, draw, prefix=17)

    def test_null_has_no_target_position_truth_and_no_companion(self):
        g = geometry()
        with patch.object(inputs, 'standardized_noise', return_value=np.zeros((9, 9))):
            result = inputs.realize(g, 'null', 'none', 'isolated', 0, 0)
        np.testing.assert_array_equal(result['data'], g['background'])
        self.assertIsNone(result['metadata']['target_native_xy'])
        self.assertIsNone(result['metadata']['companion_native_xy'])
        self.assertEqual(result['metadata']['target_flux_jy'], 0)

    def test_isolated_gaussian_does_not_render_absent_companion_or_accept_bool_draw(self):
        g = geometry()
        original = inputs.integrated_source
        with patch.object(inputs, 'integrated_source', wraps=original) as rendered:
            inputs.realize(g, 'noiseless', 'gaussian', 'isolated', 600, 0)
        self.assertEqual(rendered.call_count, 1)
        with self.assertRaises(ValueError): inputs.realize(g, 'noiseless', 'gaussian', 'isolated', 600, False)


if __name__ == '__main__': unittest.main()
