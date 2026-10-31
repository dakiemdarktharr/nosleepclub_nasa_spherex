"""Synthetic native-frame adapter contracts; no observed data or position fit."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import astropy.units as u
import numpy as np

from scripts import neighbor_intervention_inputs as semantic
from scripts import shape_native_inputs as shape
from tests.test_neighbor_intervention_inputs import prepared_fixture


ZERO = (0*u.pix**2, 0*u.pix**3, 0*u.pix**3)
ANCHOR = np.array([31.5, 31.5])


def with_two_neighbors():
    prepared = prepared_fixture()[0]
    prepared['sample']['neighbour_ids'] = ['known-1', 'known-2']
    prepared['sample']['neighbours'] = [('known-1', np.array([34.7, 31.2])),
                                        ('known-2', np.array([28.0, 33.1]))]
    return prepared


class ShapeNativeInputsTests(unittest.TestCase):
    def test_theta_zero_preserves_frozen_native_semantics_and_both_neighbors(self):
        prepared = with_two_neighbors()
        old = semantic.prepare_semantic([prepared], ANCHOR, epsf_kind='nearest')[0]
        new = shape.prepare_shape_sample(prepared, ANCHOR, ZERO, kind='nearest')
        for key in ('data', 'error', 'background_design', 'neighbor_design'):
            np.testing.assert_allclose(new[key], old[key], atol=1e-12, rtol=1e-11)
        self.assertEqual(new['neighbor_ids'], ['known-1', 'known-2'])
        self.assertEqual(new['neighbor_unit'], old['neighbor_unit'])
        self.assertEqual(new['metadata']['x'], old['metadata']['x'])
        self.assertEqual(new['metadata']['y'], old['metadata']['y'])
        self.assertEqual(new['neighbor_shape_design'].shape, (len(new['data']), 2, 3))
        for pos in (ANCHOR, ANCHOR+[.17, -.21]):
            np.testing.assert_allclose(new['renderer'](pos).to_value(shape.I/u.Jy),
                                       old['renderer'](pos).to_value(shape.I/u.Jy), rtol=1e-11, atol=1e-11)

    def test_target_and_every_neighbor_have_correct_omega_scaled_shape_derivatives(self):
        prepared = with_two_neighbors()
        base = shape.prepare_shape_sample(prepared, ANCHOR, ZERO)
        target_derivative = base['shape_renderer'](ANCHOR)
        direction = base['neighbor_shape_design']
        for axis, unit in enumerate((u.pix**2, u.pix**3, u.pix**3)):
            # The model is exactly linear in theta, so a larger symmetric step
            # avoids cancellation in tiny wing pixels without truncation error.
            amount = 1e-4
            parameters = [0*u.pix**2, 0*u.pix**3, 0*u.pix**3]
            parameters[axis] = amount*unit
            plus = shape.prepare_shape_sample(prepared, ANCHOR, tuple(parameters))
            parameters[axis] = -amount*unit
            minus = shape.prepare_shape_sample(prepared, ANCHOR, tuple(parameters))
            derivative = (plus['renderer'](ANCHOR)-minus['renderer'](ANCHOR)).to_value(shape.I/u.Jy)/(2*amount)
            np.testing.assert_allclose(target_derivative[:, axis], derivative, rtol=2e-8, atol=3e-9)
            reconstructed = (plus['neighbor_design']-minus['neighbor_design'])/(2*amount)
            np.testing.assert_allclose(direction[:, :, axis], reconstructed, rtol=2e-8, atol=3e-9)
            self.assertTrue(all(np.linalg.norm(direction[:, j, axis]) > 0 for j in range(2)))
        details = base['render_details'](ANCHOR, ZERO)
        np.testing.assert_allclose(target_derivative,
            details.selected_shape_directions/(1e6*details.metadata['source_omega_sr']), rtol=1e-13)
        self.assertEqual(base['renderer'](ANCHOR).unit, shape.I/u.Jy)

    def test_holey_mask_does_not_renormalize_target_or_neighbors(self):
        full = with_two_neighbors();masked = with_two_neighbors()
        selection = masked['selection_mask'];selection[29:32, 30:33] = False
        full_y, full_x = np.nonzero(full['selection_mask'])
        keep = selection[full_y, full_x]
        masked['sample']['x'] = masked['sample']['x'][keep]
        masked['sample']['y'] = masked['sample']['y'][keep]
        masked['sample']['background'] = masked['sample']['background'][keep]
        masked['data'] = masked['data'][keep];masked['error'] = masked['error'][keep]
        params = (.005*u.pix**2, .0001*u.pix**3, -.0001*u.pix**3)
        a = shape.prepare_shape_sample(full, ANCHOR, params)
        b = shape.prepare_shape_sample(masked, ANCHOR, params)
        np.testing.assert_allclose(b['renderer'](ANCHOR).value, a['renderer'](ANCHOR).value[keep], rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(b['neighbor_design'], a['neighbor_design'][keep], rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(b['neighbor_shape_design'], a['neighbor_shape_design'][keep], rtol=1e-12, atol=1e-12)
        self.assertLess(b['render_details'](ANCHOR, params).metadata['signed_selected_fraction'],
                        a['render_details'](ANCHOR, params).metadata['signed_selected_fraction'])

    def test_unsupported_neighbor_area_or_shape_refuses_preparation(self):
        with patch.object(shape, 'wcs_pixel_area', return_value=SimpleNamespace(supported=False)):
            with self.assertRaisesRegex(ValueError, 'neighbor solid-angle'):
                shape.prepare_shape_sample(with_two_neighbors(), ANCHOR, ZERO)
        with patch.object(shape.MomentPreservingEPSF, 'render', side_effect=ValueError('synthetic shape guard')):
            with self.assertRaisesRegex(ValueError, 'synthetic shape guard'):
                shape.prepare_shape_sample(with_two_neighbors(), ANCHOR, ZERO)

    def test_empty_neighbors_and_unsupported_target_area_are_explicit(self):
        prepared = prepared_fixture()[0];prepared['sample']['neighbour_ids'] = [];prepared['sample']['neighbours'] = []
        item = shape.prepare_shape_sample(prepared, ANCHOR, ZERO)
        self.assertEqual(item['neighbor_design'].shape, (len(item['data']), 0))
        self.assertEqual(item['neighbor_shape_design'].shape, (len(item['data']), 0, 3))
        # theta=0 parity is checked during preparation, while a nonzero theta
        # postpones the target area check until the renderer is evaluated.
        params = (.005*u.pix**2, 0*u.pix**3, 0*u.pix**3)
        with patch.object(shape, 'wcs_pixel_area', return_value=SimpleNamespace(supported=False)):
            with self.assertRaisesRegex(ValueError, 'target solid-angle'):
                shape.prepare_shape_sample(prepared, ANCHOR, params)['renderer'](ANCHOR)


if __name__ == '__main__': unittest.main()
