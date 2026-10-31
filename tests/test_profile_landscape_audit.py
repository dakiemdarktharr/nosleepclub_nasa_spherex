"""Independent analytic WLS, grid and derivative audit checks."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import astropy.units as u
import numpy as np

from scripts import audit_profile_landscape as audit
from scripts.experiment_journal import Journal


class ProfileLandscapeAuditTests(unittest.TestCase):
    def test_full_grid_topology_and_missing_nodes(self):
        costs = [[0., 1., None], [1., 2., 5.], [None, 5., 8.]]
        counts = [1, 3, 4, 6]
        levels = []
        for level, count in zip(audit.LEVELS, counts):
            for conn in (4, 8):
                levels.append({'delta_cost': level, 'connectivity': conn, 'component_count': 1,
                    'components': [{'nodes': count, 'touches_grid_boundary': True,
                                    'touches_missing_node': count > 1}]})
        topology = {'minimum_cost': 0., 'valid_nodes': 7, 'missing_nodes': 2, 'levels': levels}
        grid = {'x_common_px': [0., 1., 2.], 'y_common_px': [0., 1., 2.], 'costs': costs,
                'failures': [{'ix': 2, 'iy': 0, 'error_code': 'callback_failed'},
                             {'ix': 0, 'iy': 2, 'error_code': 'callback_failed'}],
                'sampled_connectivity': topology}
        def solve(p):
            if tuple(p) in ((2., 0.), (0., 2.)):return {'error_code': 'callback_failed'}
            return {'cost': p[0]**2+p[1]**2}
        self.assertEqual(audit.inspect_grid(grid, [0., 1., 2.], [0., 1., 2.], (0, 1, 2), solve, np.zeros(2), {}), 9)
        for mutation in ('axis', 'missing', 'cost', 'topology', 'bounds'):
            bad = copy.deepcopy(grid)
            if mutation == 'axis':bad['x_common_px'][1] += .01
            if mutation == 'missing':bad['failures'].pop()
            if mutation == 'cost':bad['costs'][2][2] = -1.
            if mutation == 'topology':bad['sampled_connectivity']['levels'][0]['components'][0]['nodes'] = 2
            if mutation == 'bounds':bad['failures'][0]['error_code'] = 'outside_search_square'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                audit.inspect_grid(bad, [0., 1., 2.], [0., 1., 2.], (0, 1, 2), solve, np.zeros(2), {})

    def test_stencil_full_hessian_and_gn_are_distinct(self):
        def solve(p):
            x, y = p;r = np.array([x*x-1., y]);return {'residual':r, 'cost':float(r@r)}
        p = [.3, .4];h = .001
        output = audit.independent_stencil(solve, p, h)
        np.testing.assert_allclose(output['gradient_cost'], [4*.3*(.3**2-1), .8], atol=2e-6)
        np.testing.assert_allclose(output['hessian_cost'], [[12*.3**2-4, 0.], [0., 2.]], atol=1e-5)
        np.testing.assert_allclose(output['gauss_newton'], [[8*.3**2, 0.], [0., 2.]], atol=1e-12)
        self.assertLess(output['hessian_cost_eigenvalues'][0], 0.)
        self.assertGreaterEqual(output['gauss_newton_eigenvalues'][0], 0.)
        rows = []
        for step in audit.STEPS:
            calc = audit.independent_stencil(solve, p, step)
            rows.append({'step_common_px':step, **{k:(v.tolist() if isinstance(v, np.ndarray) else float(v) if isinstance(v, np.floating) else v) for k, v in calc.items()}})
        entry = {'position': p, 'diagnostic': {'position': p, 'cost': solve(p)['cost'], 'steps': rows}}
        audit.inspect_probe(entry, solve, {}, replay=True)
        changed = copy.deepcopy(entry);changed['diagnostic']['steps'][0]['gauss_newton'][0][0] += 1.
        with self.assertRaisesRegex(ValueError, 'gauss_newton'):
            audit.inspect_probe(changed, solve, {}, replay=True)

    def test_independent_weighted_linear_solution_and_bounds(self):
        axis = np.linspace(-1., 1., 13)
        data = np.sin(axis*3)+.2*axis**2+.3;weights = np.linspace(.4, 1., len(axis))
        item = {'data':data, 'error':np.linspace(.8, 1.3, len(axis)),
                'background_design': np.column_stack((np.ones(len(axis)), axis)),
                'neighbor_design': (axis**2)[:, None],
                'renderer': lambda p: (np.exp(-(axis-p[0])**2)+p[1]*axis**3)*u.MJy/u.sr/u.Jy}
        with patch.object(audit.study.baseline.model, 'least_squares', side_effect=AssertionError('no position optimizer')):
            solve = audit.residual_solver(item, weights, [0., 0.]);value = solve([.15, -.2])
        target = item['renderer']([.15, -.2]).value
        X = np.column_stack((target, item['background_design'], item['neighbor_design']))
        W = np.diag(weights/item['error']**2)
        beta = np.linalg.solve(X.T@W@X, X.T@W@data)
        residual = data-X@beta
        self.assertAlmostEqual(value['cost'], residual@W@residual, places=12)
        self.assertEqual(solve([2.6, 0.])['error_code'], 'outside_search_square')
        different = audit.residual_solver(item, np.ones(len(axis)), [0., 0.])([.15, -.2])
        self.assertNotAlmostEqual(value['cost'], different['cost'])
        with self.assertRaises(ValueError):audit.residual_solver(item, weights[:-1], [0., 0.])

    def test_candidate_origins_preserve_fit_arms(self):
        row = {'fit': {'position': [0., 0.], 'final_mode_audit': {'starts': [
            {'success': True, 'position': [0., 0.]}, {'success': False}],
            'near_best_modes': [{'position': [0., 0.]}]}}}
        rows = {'baseline': row, 'corrected': copy.deepcopy(row)}
        self.assertEqual(len(audit.expected_origins(rows)), 1)
        self.assertEqual(len(audit.expected_origins(rows)[0]['origins']), 4)
        self.assertEqual(len(audit.expected_origins(rows, local=True)[0]['origins']), 2)

    def test_checksum_and_arm_identity_bindings_refuse_corruption(self):
        key = ('s', 'e', 'baseline', 'corrected')
        saved = {'checksum': 'old', 'payload': {'status': 'fit_completed'}}
        new = {'checksum': 'new', 'payload': {'status': 'fit_completed', 'baseline_checksum': 'old'}}
        row = {'source_id':'s', 'obs_id':'e', 'psf_arm':'baseline', 'weight_arm':'corrected',
               'baseline_checksum':'old', 'point_checksum':'new',
               'input_statuses': {'baseline':'fit_completed', 'corrected':'fit_completed'}}
        self.assertEqual(audit.bound_input_rows(key, row, saved, new)[1], row['input_statuses'])
        for field, value in (('source_id', 'bad'), ('weight_arm', 'baseline'),
                             ('point_checksum', 'bad'), ('baseline_checksum', 'bad')):
            bad = copy.deepcopy(row);bad[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):audit.bound_input_rows(key, bad, saved, new)

    def test_unverified_study_failure_is_terminal_and_keeps_reason(self):
        row = audit.unverified_study_failure({'status': 'profile_failed', 'error': 'synthetic rank failure'})
        with tempfile.TemporaryDirectory(dir=audit.study.ROOT) as temp:
            journal = Journal(Path(temp)/'journal', {'synthetic': True}, [('s', 'e', 'baseline', 'baseline')],
                              ('verified', 'unverified_study_failure'))
            written = journal.write(('s', 'e', 'baseline', 'baseline'), row)
            self.assertEqual(written['payload']['status'], 'unverified_study_failure')
            self.assertEqual(written['payload']['study_error'], 'synthetic rank failure')
            self.assertTrue(written['payload']['error'])
            self.assertEqual(len(journal.records(require_complete=True)), 1)

    def test_native_weight_and_neighbor_coefficients_are_bound(self):
        x = np.linspace(-1., 1., 8)
        item = {'metadata': {'x': list(range(8)), 'y': [0]*8}, 'neighbor_ids':['n'],
                'data': np.sin(x), 'error': np.ones(8),
                'background_design': np.column_stack((np.ones(8), x)), 'neighbor_design': (x*x)[:, None],
                'neighbor_unit':'MJy / (Jy sr)',
                'renderer': lambda p: np.cos(x-p[0])*u.MJy/u.sr/u.Jy}
        meta = {'anchor_sky_px':[0., 0.]}
        sample = {'x':list(range(8)), 'y':[0]*8, 'neighbor_ids':['n'],
                  'data_mjysr':item['data'].tolist(), 'error_mjysr':item['error'].tolist(),
                  'background_design':item['background_design'].tolist(),
                  'neighbor_design_per_jy':item['neighbor_design'].tolist(), 'neighbor_unit':item['neighbor_unit']}
        rows = {arm:{'metadata':meta, 'samples':[copy.deepcopy(sample)]} for arm in ('baseline', 'corrected')}
        audit.inspect_native(item, meta, rows, 'corrected', {})
        rows['corrected']['samples'][0]['neighbor_design_per_jy'][0][0] += 1.
        with self.assertRaisesRegex(ValueError, 'native_neighbor_design'):
            audit.inspect_native(item, meta, rows, 'corrected', {})

    def test_own_replay_uses_saved_weight_arm_and_objective(self):
        x = np.linspace(-1., 1., 11)
        item = {'data':np.sin(3*x)+.2*x*x, 'error':np.ones(11),
                'background_design':np.column_stack((np.ones(11), x)),
                'neighbor_design':(x*x)[:, None],
                'renderer':lambda p:(np.exp(-(x-p[0])**2)+p[1]*x**3)*u.MJy/u.sr/u.Jy}
        weights = {'baseline':np.linspace(.3, 1., 11), 'corrected':np.linspace(1., .3, 11)}
        rows = {}
        for arm, p in (('baseline', [.1, .2]), ('corrected', [.2, .1])):
            cost = audit.residual_solver(item, weights[arm], [0., 0.])(p)['cost']
            rows[arm] = {'fit':{'position':p, 'chi2_weighted':cost,
                'frames':[{'weights':weights[arm].tolist()}],
                'final_mode_audit':{'starts':[], 'near_best_modes':[]}}}
        entries = audit.expected_origins(rows)
        for entry in entries:entry['diagnostic'] = {}
        cost = rows['baseline']['fit']['chi2_weighted']
        diag = {'probes':entries, 'global_grid':{}, 'local_grids':[],
                'saved_objective_replay':[{'origin':'point', 'position':[.1, .2],
                    'saved_cost':cost, 'replayed_cost':cost, 'absolute_difference':0.}]}
        with patch.object(audit, 'inspect_grid', return_value=25), patch.object(audit, 'inspect_probe'):
            result = audit.inspect_diagnostics(diag, item, {'anchor_sky_px':[0., 0.]}, rows,
                                               'ordinary', 'baseline', 'baseline', {})
            self.assertEqual((result['sampled_grid_nodes'], result['objective_replays']), (25, 1))
            corrupted = copy.deepcopy(rows)
            corrupted['baseline']['fit']['frames'][0]['weights'] = weights['corrected'].tolist()
            with self.assertRaisesRegex(ValueError, 'own_replayed_cost'):
                audit.inspect_diagnostics(diag, item, {'anchor_sky_px':[0., 0.]}, corrupted,
                                          'ordinary', 'baseline', 'baseline', {})


if __name__ == '__main__':unittest.main()
