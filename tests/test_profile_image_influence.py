"""Fixed synthetic pixel derivatives against independent full WLS algebra."""
import copy
import unittest

import astropy.units as u
import numpy as np

from scripts import profile_image_influence as influence


I = u.MJy/u.sr


def synthetic():
    yy, xx = np.mgrid[-3:4, -3:4];x = xx.ravel().astype(float);y = yy.ravel().astype(float)
    def gaussian(p): return np.exp(-((x-p[0])**2/2+(y-p[1])**2/3))
    def renderer(p): return gaussian(p)*I/u.Jy
    source = np.column_stack([x*x*gaussian([.1, -.2]), x**3*gaussian([.1, -.2]), y**3*gaussian([.1, -.2])])
    neighbors = np.column_stack([np.exp(-((x-1.3)**2+(y+.7)**2)/2),
                                 np.exp(-((x+1.6)**2+(y-1.)**2)/3)])
    neighbor_shape = np.stack([np.column_stack([neighbors[:, j]*x*x, neighbors[:, j]*x**3,
                                                 neighbors[:, j]*y**3]) for j in range(2)], axis=1)
    background = np.column_stack([np.ones(len(x)), x, y]);error = .4 + .02*(x+3)+.01*(y+3)
    weights = .55 + .4*(x+3)/6
    p = np.array([.1, -.2]);flux = -2.5;nflux = np.array([.6, -.4]);bgcoeff = np.array([.2, -.1, .3])
    h = .002;ex = np.array([h, 0.]);ey = np.array([0., h])
    J = np.column_stack([flux*(gaussian(p+ex)-gaussian(p-ex))/(2*h),
                         flux*(gaussian(p+ey)-gaussian(p-ey))/(2*h), gaussian(p), background, neighbors])
    W = np.diag(weights/error**2);L = np.linalg.solve(J.T@W@J, J.T@W)
    probe = np.sin(x + .7*y);residual = probe-J@(L@probe)
    model = flux*gaussian(p)+background@bgcoeff+neighbors@nflux
    item = {'obs_id': 'synthetic', 'data': model+residual, 'error': error,
            'neighbor_ids': ['n0', 'n1'], 'renderer': renderer,
            'background_design': background, 'neighbor_design': neighbors, 'neighbor_unit': str(I/u.Jy),
            'shape_renderer': lambda position: source,
            'neighbor_shape_design': neighbor_shape}
    fit = {'frames': [{'obs_id': 'synthetic', 'weights': weights, 'error': error.copy(),
                       'neighbor_ids': ['n0', 'n1'], 'target_flux_jy': flux, 'neighbor_flux_jy': nflux,
                       'model': model, 'residual': residual, 'background_coefficients': bgcoeff}], 'position': p,
           'data_unit': 'MJy / sr', 'nonnegative_neighbors': False}
    return item, fit, J, W, L, source, neighbor_shape


class ProfileInfluenceTests(unittest.TestCase):
    def test_full_wls_response_original_variance_and_shape_score(self):
        item, fit, J, W, L, ds, dn = synthetic()
        result = influence.centroid_and_shape_influence(item, fit, [0., 0.])
        frame = fit['frames'][0];D = frame['target_flux_jy']*ds + np.einsum('nqj,q->nj', dn, frame['neighbor_flux_jy'])
        np.testing.assert_allclose(result['position_pixel_influence'], L[:2], rtol=2e-11, atol=2e-12)
        expected_cov = L[:2] @ np.diag(item['error']**2) @ L[:2].T
        np.testing.assert_allclose(result['position_covariance_px2_nominal'], expected_cov, rtol=1e-11, atol=1e-12)
        # Under nonuniform robust weights, the original-variance sandwich differs
        # from a naively reported inverse weighted normal matrix.
        self.assertGreater(np.max(np.abs(expected_cov-np.linalg.inv(J.T@W@J)[:2, :2])), 1e-4)
        np.testing.assert_allclose(result['shape_model_derivative'], D, rtol=1e-13, atol=1e-13)
        np.testing.assert_allclose(result['position_shape_response'], -L[:2]@D, rtol=1e-11, atol=1e-12)
        self.assertGreater(np.linalg.norm(L[:2]@np.einsum('nqj,q->nj', dn, frame['neighbor_flux_jy'])), 1e-3)
        white = np.sqrt(frame['weights'])/item['error'];A = J*white[:, None]
        Q, _ = np.linalg.qr(A);Ds = D*white[:, None]*np.asarray(influence.DEFAULT_BOUNDS)
        P = Ds-Q@(Q.T@Ds)
        np.testing.assert_allclose(result['shape_information_scaled'], P.T@P, rtol=1e-10, atol=1e-12)
        np.testing.assert_allclose(result['shape_score_scaled'], P.T@(frame['residual']*white), rtol=1e-10, atol=1e-12)
        np.testing.assert_allclose(result['shape_score_pixel_response'], P.T*white[None, :], rtol=1e-10, atol=1e-12)
        np.testing.assert_allclose(result['shape_score_pixel_response'] @ item['data'], result['shape_score_scaled'], atol=1e-12)

    def test_scaled_degenerate_shape_information_does_not_become_support(self):
        item, fit, J, _, _, _, _ = synthetic()
        item['shape_renderer'] = lambda p: np.column_stack((J[:, 2], J[:, 3], J[:, 4]))
        item['neighbor_shape_design'] = np.zeros_like(item['neighbor_shape_design'])
        result = influence.centroid_and_shape_influence(item, fit, [0., 0.])
        self.assertLess(np.linalg.norm(result['shape_information_scaled']), 1e-25)

    def test_rank_failure_and_invalid_frame_contract(self):
        item, fit, _, _, _, _, _ = synthetic()
        bad = copy.deepcopy(item);bad['neighbor_design'][:, 1] = bad['neighbor_design'][:, 0]
        with self.assertRaisesRegex(ValueError, 'rank deficient'):
            influence.centroid_and_shape_influence(bad, fit, [0., 0.])
        for mutation in ('obs', 'neighbors', 'fit_unit', 'neighbor_unit', 'shape_unit', 'constrained', 'bad_weights', 'position', 'renderer_unit'):
            i, f, *_ = synthetic()
            if mutation == 'obs': f['frames'][0]['obs_id'] = 'other'
            if mutation == 'neighbors': f['frames'][0]['neighbor_ids'] = ['n1', 'n0']
            if mutation == 'fit_unit': f['data_unit'] = 'Jy'
            if mutation == 'neighbor_unit': i['neighbor_unit'] = str(u.Jy/u.sr/u.Jy)
            if mutation == 'shape_unit': i['shape_renderer'] = lambda p: np.ones((49, 3))*u.m
            if mutation == 'constrained': f['nonnegative_neighbors'] = True
            if mutation == 'bad_weights': f['frames'][0]['weights'][0] = 0.
            if mutation == 'position': f['position'][0] = 3.
            if mutation == 'renderer_unit': i['renderer'] = lambda p: np.ones(49)*u.m
            with self.subTest(mutation=mutation), self.assertRaises((ValueError, TypeError)):
                influence.centroid_and_shape_influence(i, f, [0., 0.])

    def test_saved_data_and_variance_mismatch_are_refused(self):
        for name in ('data', 'error'):
            item, fit, *_ = synthetic()
            item[name] = item[name].copy();item[name][0] += .1
            with self.subTest(name=name), self.assertRaises(ValueError):
                influence.centroid_and_shape_influence(item, fit, [0., 0.])

    def test_invalid_numerical_tuning_refused(self):
        item, fit, *_ = synthetic()
        for kwargs in ({'step': -1.}, {'step': np.nan}, {'step': True}, {'bound': -1.},
                       {'rcond': -1.}, {'rcond': np.nan}, {'max_condition': 1.}, {'max_condition': np.nan}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                influence.centroid_and_shape_influence(item, fit, [0., 0.], **kwargs)


if __name__ == '__main__': unittest.main()
