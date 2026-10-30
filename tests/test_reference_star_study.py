"""Runner contracts using fixed synthetic metadata, no observations or fits."""
from contextlib import ExitStack, redirect_stdout
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import run_reference_star_study as study
from scripts.experiment_journal import Journal


ROOT = Path(__file__).resolve().parents[1]
STATUSES = ('fit_completed', 'fit_failed', 'preparation_failed')


def context():
    references = [{'catalog': {'source_id': f's{i:02d}'},
                   'split': 'training' if i < 14 else 'heldout'} for i in range(21)]
    frames = [{'record': {'obs_id': f'f{i:02d}', 'epoch': 'before' if i < 10 else 'after'}}
              for i in range(20)]
    return SimpleNamespace(references=references, frames=frames)


class ReferenceStarStudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'journal'
        self.ctx = context()
        self.keys = study.expected_keys(self.ctx)
        self.identity = {'section': 'synthetic', 'commit': 'fixed'}

    def test_planned_840_and_three_disjoint_complete_shards(self):
        self.assertEqual(len(self.keys), 840)
        self.assertEqual(len(set(self.keys)), 840)
        shards = [{key for i, r in enumerate(self.ctx.references) if i % 3 == shard
                   for key in self.keys if key[0] == r['catalog']['source_id']} for shard in range(3)]
        self.assertEqual([len(part) for part in shards], [280, 280, 280])
        self.assertFalse(shards[0] & shards[1] or shards[0] & shards[2] or shards[1] & shards[2])
        self.assertEqual(set.union(*shards), set(self.keys))
        counts = {epoch: sum(1 for key in self.keys if int(key[1][1:]) // 10 == epoch)
                  for epoch in range(2)}
        self.assertEqual(counts, {0: 420, 1: 420})
        changed = context(); changed.frames[0] = changed.frames[1]
        with self.assertRaisesRegex(RuntimeError, 'denominator'):
            study.expected_keys(changed)

    def test_three_shards_complete_and_resume_immutable_with_failures(self):
        design = {'metadata': {'expected_keys': [list(k) for k in self.keys]}}
        prepared_calls, fit_calls = [], []
        def prepare(ctx, reference, frame):
            sid = reference['catalog']['source_id']; obs = frame['record']['obs_id']
            prepared_calls.append((sid, obs))
            if (sid, obs) == ('s00', 'f00'):
                raise ValueError('synthetic common preparation failure')
            return {'obs_id': obs, 'sid': sid}, {'anchor_sky_px': [0., 0.], 'source_id': sid}
        def prepare_variant(prepared, anchor, variant):
            return {**prepared, 'variant': variant}
        def fit(samples, anchor, *, data_unit, nonnegative_neighbors, max_irls_iterations):
            item = samples[0]
            self.assertEqual(data_unit, 'MJy/sr')
            self.assertIs(nonnegative_neighbors, False)
            self.assertEqual(max_irls_iterations, 20)
            fit_calls.append((item['sid'], item['obs_id'], item['variant']))
            if (item['sid'], item['obs_id'], item['variant']) == ('s01', 'f02', 'bilinear'):
                raise ValueError('synthetic fit failure')
            return {'frames': [{'obs_id': item['obs_id']}], 'position': [0., 0.]}
        with ExitStack() as stack:
            stack.enter_context(patch.object(study, 'OUTPUT', self.output))
            stack.enter_context(patch.object(study.frozen, 'verify', return_value=design))
            stack.enter_context(patch.object(study.frozen, 'runtime', return_value={'synthetic': True}))
            stack.enter_context(patch.object(study.frozen, 'identity', return_value=self.identity))
            stack.enter_context(patch.object(study.inputs, 'read_context', return_value=self.ctx))
            prepare_mock = stack.enter_context(patch.object(study.inputs, 'prepare_cell', side_effect=prepare))
            stack.enter_context(patch.object(study.inputs, 'prepare_variant', side_effect=prepare_variant))
            stack.enter_context(patch.object(study.previous, 'descriptors', return_value=[]))
            stack.enter_context(patch.object(study.semantic, 'model_samples', side_effect=lambda items: items))
            stack.enter_context(patch.object(study.model, 'fit_epoch', side_effect=fit))
            stack.enter_context(patch.object(study, 'sky_residual_arcsec', return_value=[0., 0.]))
            stack.enter_context(redirect_stdout(io.StringIO()))
            for shard in range(3):
                study.run('synthetic', shard)
                progress = Journal(self.output, self.identity, self.keys, STATUSES)
                actual = {tuple(record['key']) for record in progress.records()}
                expected = {key for key in self.keys if int(key[0][1:]) % 3 <= shard}
                self.assertEqual(actual, expected)
            j = Journal(self.output, self.identity, self.keys, STATUSES)
            records = j.records(require_complete=True)
            self.assertEqual(len(prepared_calls), 420)
            self.assertEqual(len(fit_calls), 838)
            self.assertEqual(j.counts()['statuses'], {'fit_completed': 837, 'fit_failed': 1, 'preparation_failed': 2})
            for v in ('nearest', 'bilinear'):
                failed = j.read(('s00', 'f00', v))['payload']
                self.assertEqual(failed['status'], 'preparation_failed')
                self.assertEqual(failed['failure_stage'], 'common_preparation')
            self.assertEqual(j.read(('s01', 'f02', 'bilinear'))['payload']['status'], 'fit_failed')
            self.assertEqual(j.read(('s01', 'f02', 'nearest'))['payload']['status'], 'fit_completed')
            prepare_mock.side_effect = AssertionError('completed records must not be prepared again')
            for shard in range(3):
                study.run('synthetic', shard)
            self.assertEqual(j.records(require_complete=True), records)

    def test_mismatched_sample_identity_is_recorded_as_failed(self):
        prepared = {'obs_id': 'planned'}
        metadata = {'anchor_sky_px': [0., 0.]}
        with patch.object(study.inputs, 'prepare_variant', return_value={}), \
             patch.object(study.previous, 'descriptors', return_value=[]), \
             patch.object(study.semantic, 'model_samples', return_value=[]), \
             patch.object(study.model, 'fit_epoch', return_value={'frames': [{'obs_id': 'other'}]}):
            row = study.attempt(prepared, metadata, 'nearest')
        self.assertEqual(row['status'], 'fit_failed')
        self.assertIn('fit exposure differs', row['error'])

    def test_design_identity_and_runtime_identity_are_checked(self):
        with patch.object(study, 'OUTPUT', self.output), \
             patch.object(study.frozen, 'verify', return_value={'metadata': {'expected_keys': []}}), \
             patch.object(study.inputs, 'read_context', return_value=self.ctx):
            with self.assertRaisesRegex(RuntimeError, 'identities changed'):
                study.run('synthetic', 0)
        Journal(self.output, self.identity, self.keys, STATUSES)
        valid_design = {'metadata': {'expected_keys': [list(k) for k in self.keys]}}
        with patch.object(study, 'OUTPUT', self.output), \
             patch.object(study.frozen, 'verify', return_value=valid_design), \
             patch.object(study.frozen, 'runtime', return_value={}), \
             patch.object(study.frozen, 'identity', return_value={'section': 'different'}), \
             patch.object(study.inputs, 'read_context', return_value=self.ctx):
            with self.assertRaisesRegex(ValueError, 'header identity'):
                study.run('synthetic', 0)

    def test_invalid_shards_refused_before_loading(self):
        for shard in (-1, 3, True, None, '1', 1.0):
            with self.subTest(shard=shard), self.assertRaises(ValueError):
                study.run('synthetic', shard)


if __name__ == '__main__':
    unittest.main()
