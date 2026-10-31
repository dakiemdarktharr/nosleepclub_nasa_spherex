"""Factorial isolation, no optimizer/assessment access, and all-cell accounting."""
from collections import Counter
from contextlib import ExitStack, redirect_stdout
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import astropy.units as u
import numpy as np

from scripts import run_profile_landscape_study as study
from scripts.experiment_journal import Journal


def context():
    ids = ['training-'+str(i) for i in range(14)]
    return SimpleNamespace(training_ids=ids,
        references=[{'catalog': {'source_id': sid}} for sid in ids],
        frames=[{'record': {'obs_id': obs}} for obs in study.FRAMES])


class LandscapeStudyTests(unittest.TestCase):
    def test_factorial_keys_include_all_sources_and_both_old_frames(self):
        ctx = context()
        with patch.object(study.calibration, 'planned_cells', return_value=([], study.FRAMES, [])):
            keys = study.expected_keys(ctx)
            self.assertEqual(len(keys), 112)
            self.assertEqual(set(k[0] for k in keys), set(ctx.training_ids))
            self.assertEqual(Counter(k[2:] for k in keys), {a: 28 for a in [('baseline', 'baseline'),
                ('baseline', 'corrected'), ('corrected', 'baseline'), ('corrected', 'corrected')]})
            ctx.training_ids.pop()
            with self.assertRaises(ValueError): study.expected_keys(ctx)

    def test_all_failed_inputs_retained_across_shards_without_new_preparation(self):
        ctx = context(); identity = {'synthetic-profile': 1}; metadata = {'bound_inputs': 'old'}
        old = SimpleNamespace(read=lambda _: {'checksum': 'old', 'payload': {'status': 'preparation_failed', 'error': 'edge'}})
        new = SimpleNamespace(read=lambda _: {'checksum': 'new', 'payload': {'status': 'preparation_failed',
            'error': 'edge', 'baseline_checksum': 'old'}})
        with tempfile.TemporaryDirectory(dir=study.ROOT) as temp, ExitStack() as stack:
            output = Path(temp)/'diagnostic'; point_output = Path(temp)/'points'
            stack.enter_context(patch.object(study, 'OUTPUT', output))
            stack.enter_context(patch.object(study.points, 'OUTPUT', point_output))
            stack.enter_context(patch.object(study.calibration, 'planned_cells', return_value=([], study.FRAMES, [])))
            stack.enter_context(patch.object(study.frozen, 'verify', return_value={'metadata': metadata}))
            stack.enter_context(patch.object(study, 'open_inputs', return_value=(ctx, old, new, np.zeros(3), metadata)))
            stack.enter_context(patch.object(study.frozen, 'runtime', return_value={}))
            stack.enter_context(patch.object(study.frozen, 'identity', return_value=identity))
            prepare = stack.enter_context(patch.object(study.baseline.inputs, 'prepare_cell'))
            optimizer = stack.enter_context(patch.object(study.baseline.model, 'least_squares', side_effect=AssertionError('no optimizer')))
            stack.enter_context(redirect_stdout(io.StringIO()))
            study.run('synthetic', 0); study.run('synthetic', 1); study.run('synthetic', 0)
            records = Journal(output/'cells', identity, study.expected_keys(ctx), study.STATUSES).records(require_complete=True)
            self.assertEqual(len(records), 112)
            self.assertEqual(Counter(r['payload']['status'] for r in records), {'preparation_failed': 112})
            self.assertEqual({r['key'][0] for r in records}, set(ctx.training_ids))
            prepare.assert_not_called(); optimizer.assert_not_called()
            self.assertFalse((point_output/'assessment').exists())

    def test_existing_assessment_directory_refused(self):
        with tempfile.TemporaryDirectory(dir=study.ROOT) as temp, patch.object(study.points, 'OUTPUT', Path(temp)):
            (Path(temp)/'assessment').mkdir()
            with self.assertRaisesRegex(ValueError, 'unopened'): study.assert_assessment_unopened()

    def test_invalid_shard_rejected_before_opening_inputs(self):
        with patch.object(study, 'open_inputs') as opened:
            for shard in (True, -1, 2, .5):
                with self.subTest(shard=shard), self.assertRaises(ValueError): study.run('synthetic', shard)
            opened.assert_not_called()

    def test_candidate_deduplication_keeps_both_fit_origins(self):
        fit = {'position': [0., 0.], 'final_mode_audit': {'starts': [
            {'success': True, 'position': [0., 0.]}, {'success': False}],
            'near_best_modes': [{'position': [0., 0.]}]}}
        rows = {a: {'fit': fit} for a in study.ARMS}
        candidates = study.candidate_positions(rows)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(len(candidates[0]['origins']), 4)
        self.assertEqual(len(study.local_centers(rows)[0]['origins']), 2)

    def test_saved_psf_and_weight_arms_cross_without_reestimating(self):
        yy, xx = np.mgrid[-4:5, -4:5]; x = xx.ravel(); y = yy.ravel()
        data = np.exp(-((x-.1)**2+(y-.2)**2)/2)+.1+.02*x+.01*y
        data[40] += .4
        weights = {'baseline': np.where(np.arange(len(x)) == 40, .2, 1.),
                   'corrected': np.where(np.arange(len(x)) == 41, .3, 1.)}
        def problem(sigma):
            return study.baseline.model.NeighborEpochProblem([{'obs_id': 'synthetic', 'data': data,
                'error': np.full(len(x), .2), 'background_design': np.column_stack((np.ones(len(x)), x, y)),
                'neighbor_design': np.empty((len(x), 0)), 'neighbor_ids': [], 'neighbor_unit': u.MJy/u.sr/u.Jy,
                'renderer': lambda p: np.exp(-((x-p[0])**2+(y-p[1])**2)/(2*sigma**2))*u.MJy/u.sr/u.Jy}],
                data_unit='MJy/sr', nonnegative_neighbors=False)
        problems = {'baseline': problem(1.), 'corrected': problem(1.03)}; rows = {}
        for arm in study.ARMS:
            p = [.1, .2] if arm == 'baseline' else [.12, .18]
            own = problems[arm]; own.set_weights([weights[arm]])
            cost = own.profile(p)['chi2_weighted']
            rows[arm] = {'fit': {'position': p, 'chi2_weighted': cost,
                'frames': [{'obs_id': 'synthetic', 'weights': weights[arm].tolist()}],
                'final_mode_audit': {'starts': [{'success': True, 'position': p, 'chi2': cost}],
                                     'near_best_modes': [{'position': p}]}}}
        results = {}
        def tiny_grid(sampler, *_): return {'one_test_cost': sampler.at([.3, .1])['cost']}
        with patch.object(study, 'grid', side_effect=tiny_grid), \
             patch.object(study.baseline.model, 'least_squares', side_effect=AssertionError('no optimizer')):
            for psf in study.ARMS:
                for weight in study.ARMS:
                    result = study.diagnose(problems[psf], np.zeros(2), rows, 'control', psf, weight)
                    results[(psf, weight)] = result['global_grid']['one_test_cost']
                    np.testing.assert_array_equal(problems[psf].weights[0], weights[weight])
                    self.assertEqual(len(result['saved_objective_replay']), 2 if psf == weight else 0)
            self.assertNotEqual(results[('baseline', 'baseline')], results[('baseline', 'corrected')])
            self.assertNotEqual(results[('baseline', 'corrected')], results[('corrected', 'corrected')])
            rows['baseline']['fit']['chi2_weighted'] += 1.
            with self.assertRaisesRegex(ValueError, 'replay failed'):
                study.diagnose(problems['baseline'], np.zeros(2), rows, 'control', 'baseline', 'baseline')


if __name__ == '__main__': unittest.main()
