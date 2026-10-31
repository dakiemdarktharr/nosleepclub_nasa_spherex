"""Independent synthetic checks; no observed images or sky products loaded."""
import unittest

import astropy.units as u
import numpy as np

from scripts.reference_frame_diagnostics import analyze_reference_frame


def fixture():
    sources = ['a', 'b', 'c', 'd', 'e', 'held']*2
    exposures = ['e1']*6 + ['e0']*6
    y = np.array([[np.sin(i+.3), np.cos(i*.7)] for i in range(12)])
    # Deterministic dense, nonstationary SPD covariance with cross-signs.
    grid = np.arange(24*13, dtype=float).reshape(24, 13)
    B = (np.sin(grid*.41)+np.cos(grid*.19))*.15
    C = B@B.T + np.diag(np.linspace(.7, 2., 24))
    return dict(offsets=y*u.pix, covariance=C*u.pix**2, source_ids=sources,
                exposure_ids=exposures, allowed_training_ids=['a', 'b', 'c', 'd', 'e'],
                planned_exposures=['e0', 'e1'], provenance='deterministic synthetic full covariance')


def xy(rows):
    return np.array([j for i in rows for j in (2*i, 2*i+1)])


def design(exposures, planned):
    H = np.zeros((2*len(exposures), 2*len(planned)))
    for i, exp in enumerate(exposures):
        j = planned.index(exp)
        H[2*i:2*i+2, 2*j:2*j+2] = np.eye(2)
    return H


class ReferenceFrameDiagnosticsTests(unittest.TestCase):
    def test_dense_gls_and_cross_covariance_match_independent_equations(self):
        args = fixture();result = analyze_reference_frame(**args)
        cal = [i for i, s in enumerate(args['source_ids']) if s != 'held']
        held = [i for i, s in enumerate(args['source_ids']) if s == 'held']
        ci, hi = xy(cal), xy(held)
        C = args['covariance'].value;y = args['offsets'].value.ravel()
        Hc = design([args['exposure_ids'][i] for i in cal], args['planned_exposures'])
        Hh = design([args['exposure_ids'][i] for i in held], args['planned_exposures'])
        Ccc = C[np.ix_(ci, ci)]
        precision_H = np.linalg.solve(Ccc, Hc)
        L = np.linalg.solve(Hc.T@precision_H, precision_H.T)
        expected_beta = L@y[ci]
        M = np.zeros((len(hi), len(y)))
        M[np.arange(len(hi)), hi] = 1.
        M[:, ci] -= Hh@L
        r = M@y;V = M@C@M.T
        cross = -Hh@L@C[np.ix_(ci, hi)]
        shortcut = C[np.ix_(hi, hi)] + Hh@L@Ccc@L.T@Hh.T
        np.testing.assert_allclose(result.reference_frame.offsets.value.ravel(), expected_beta, atol=2e-13)
        np.testing.assert_allclose(result.reference_frame.influence, L, atol=2e-13)
        np.testing.assert_allclose(result.residual_map, M, atol=2e-13)
        np.testing.assert_allclose(result.residuals.value.ravel(), r, atol=2e-13)
        np.testing.assert_allclose(result.covariance.value, V, atol=2e-13)
        np.testing.assert_allclose(V, shortcut+cross+cross.T, atol=2e-13)
        self.assertGreater(cross.max(), .001);self.assertLess(cross.min(), -.001)
        self.assertGreater(np.linalg.norm(V-shortcut), .01)
        self.assertAlmostEqual(result.chi2, r@np.linalg.solve(V, r), places=12)
        self.assertEqual(result.dof, 2*len(held))
        for i in range(len(held)):
            ri = r[2*i:2*i+2];block = V[2*i:2*i+2, 2*i:2*i+2]
            self.assertAlmostEqual(result.marginal_mahalanobis2[i], ri@np.linalg.solve(block, ri), places=12)
        self.assertEqual(result.calibration_indices, tuple(cal))
        self.assertEqual(result.heldout_indices, tuple(held))
        self.assertIn('conditional', result.qualification)
        self.assertIn('no calibrated coverage', result.qualification)

    def test_unit_covariance_scale_row_permutation_and_training_only(self):
        args = fixture();base = analyze_reference_frame(**args)
        millipix = u.def_unit('reference_diagnostics_test_millipix', .001*u.pix)
        converted = analyze_reference_frame(**{**args, 'offsets': args['offsets'].to(millipix),
                                               'covariance': args['covariance'].to(millipix**2)})
        np.testing.assert_allclose(converted.covariance.value, base.covariance.value, atol=1e-12)
        for factor in (1e-14, 1e14):
            scaled = analyze_reference_frame(**{**args, 'covariance': args['covariance']*factor})
            np.testing.assert_allclose(scaled.covariance.value/factor, base.covariance.value, rtol=1e-11, atol=1e-11)
            np.testing.assert_allclose(scaled.reference_frame.offsets.value, base.reference_frame.offsets.value, atol=1e-11)
            self.assertAlmostEqual(scaled.chi2*factor, base.chi2, places=10)
        order = [11, 4, 2, 9, 6, 1, 0, 8, 7, 5, 10, 3]
        index = xy(order);C = args['covariance'].value
        perm = {**args, 'offsets': args['offsets'][order], 'covariance': C[np.ix_(index, index)]*u.pix**2,
                'source_ids': [args['source_ids'][i] for i in order],
                'exposure_ids': [args['exposure_ids'][i] for i in order]}
        result = analyze_reference_frame(**perm)
        np.testing.assert_allclose(result.reference_frame.offsets.value, base.reference_frame.offsets.value, atol=2e-13)
        # This permutation reverses the two heldout observations.
        np.testing.assert_allclose(result.residuals.value, base.residuals.value[::-1], atol=2e-13)
        p = [2, 3, 0, 1]
        np.testing.assert_allclose(result.covariance.value, base.covariance.value[np.ix_(p, p)], atol=2e-13)
        changed = args['offsets'].copy();changed[[5, 11]] += np.array([[100., -200.], [-400., 300.]])*u.pix
        changed_result = analyze_reference_frame(**{**args, 'offsets': changed})
        np.testing.assert_allclose(changed_result.reference_frame.offsets.value, base.reference_frame.offsets.value, atol=1e-13)
        np.testing.assert_allclose(changed_result.reference_frame.covariance.value, base.reference_frame.covariance.value, atol=1e-13)
        # Even a different heldout cross-covariance cannot enter the fit.
        ci, hi = xy(base.calibration_indices), xy(base.heldout_indices)
        uncrossed = C.copy();uncrossed[np.ix_(ci, hi)] = 0.;uncrossed[np.ix_(hi, ci)] = 0.
        no_cross = analyze_reference_frame(**{**args, 'covariance': uncrossed*u.pix**2})
        np.testing.assert_allclose(no_cross.reference_frame.offsets.value, base.reference_frame.offsets.value, atol=1e-13)
        self.assertGreater(np.linalg.norm(no_cross.covariance.value-base.covariance.value), .01)

    def test_invalid_identity_units_shapes_and_covariance_are_refused(self):
        args = fixture();n = len(args['source_ids']);C = args['covariance'].value
        asymmetric = C.copy();asymmetric[0, 1] += .1
        indefinite = C.copy();indefinite[0, 1] = indefinite[1, 0] = 100.
        bad_cases = [
            {'source_ids': ['a']+args['source_ids'][1:-1]},
            {'source_ids': ['a', 'a']+args['source_ids'][2:]},
            {'source_ids': [True]+args['source_ids'][1:]},
            {'allowed_training_ids': ['a', 'a']},
            {'allowed_training_ids': args['source_ids'][:6]},
            {'allowed_training_ids': ['not-present']},
            {'planned_exposures': ['e0', 'e0']},
            {'planned_exposures': ['e0', 'e1', 'missing']},
            {'exposure_ids': ['unknown']+args['exposure_ids'][1:]},
            {'offsets': args['offsets'].value}, {'offsets': args['offsets'].value*u.m},
            {'covariance': C}, {'covariance': C*u.s**2},
            {'offsets': u.Quantity([[True, 1.]]*n, u.pix, dtype=object)},
            {'covariance': u.Quantity(np.full((2*n, 2*n), True), u.pix**2, dtype=bool)},
            {'offsets': np.full((n, 2), np.nan)*u.pix},
            {'covariance': asymmetric*u.pix**2}, {'covariance': indefinite*u.pix**2},
            {'covariance': np.zeros_like(C)*u.pix**2},
            {'covariance': C[:-1, :-1]*u.pix**2}, {'provenance': ''},
            {'min_references': True}, {'min_references': 3},
        ]
        for case in bad_cases:
            with self.subTest(case=list(case)), self.assertRaises(ValueError):
                analyze_reference_frame(**{**args, **case})

    def test_singular_full_residual_covariance_refused_without_floor(self):
        # The heldout observation exactly equals the mean calibration noise.
        # The full input covariance is PSD but the heldout residual is zero.
        Hc = np.tile(np.eye(2), (4, 1));L = Hc.T/4
        C = np.block([[np.eye(8), L.T], [L, L@L.T]])
        self.assertGreaterEqual(np.linalg.eigvalsh(C).min(), -1e-14)
        with self.assertRaisesRegex(ValueError, 'heldout residual covariance'):
            analyze_reference_frame(np.ones((5, 2))*u.pix, C*u.pix**2,
                                     ['a', 'b', 'c', 'd', 'h'], ['e']*5,
                                     ['a', 'b', 'c', 'd'], ['e'], provenance='synthetic')

    def test_singular_input_psd_is_accepted_when_residual_is_spd(self):
        # Heldout x equals one calibrator's x, not the mean; its residual
        # therefore retains variance even though the input covariance is PSD.
        A = np.zeros((10, 9));A[:8, :8] = np.eye(8)
        A[8, 0] = 1.;A[9, 8] = 1.
        C = A@A.T
        self.assertEqual(np.linalg.matrix_rank(C), 9)
        out = analyze_reference_frame(np.arange(10).reshape(5, 2)*u.pix, C*u.pix**2,
                                       ['a', 'b', 'c', 'd', 'h'], ['e']*5,
                                       ['a', 'b', 'c', 'd'], ['e'], provenance='synthetic')
        np.testing.assert_allclose(out.covariance.value, np.diag([.75, 1.25]), atol=1e-14)
        self.assertEqual(out.dof, 2)


if __name__ == '__main__': unittest.main()
