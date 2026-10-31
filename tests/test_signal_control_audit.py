"""Only synthetic fixtures: independent controls audit and adversarial cases."""
import copy
import json
from contextlib import ExitStack, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import astropy.units as u
import numpy as np

from scripts import audit_signal_controls as audit
from scripts.signal_control_metrics import summarize_signal_control
from tests.test_signal_control_metrics import fixture, index
from tests.test_signal_control_inputs import geometry


class SignalAuditTests(unittest.TestCase):
    def test_gaussian64_symmetry_and_known_unrotated_limit(self):
        # Equal widths are not the frozen case; check frozen rotated density's
        # reflection symmetry and translation invariance on all selected pixels.
        x = np.array([0,1,2,-1]); y = np.array([0,1,-1,2])
        a = audit.gaussian64(x,y,[.25,.75])
        np.testing.assert_allclose(a, audit.gaussian64(-x,-y,[-.25,-.75]), atol=1e-15)
        np.testing.assert_allclose(a, audit.gaussian64(x+10,y-8,[10.25,-7.25]), atol=1e-15)
        self.assertTrue(np.all(a > 0)); self.assertLess(float(sum(a)),1.)
        with self.assertRaises(ValueError):audit.gaussian64(x,y,[True,np.nan])

    def test_normalized_wls_retains_negative_flux_and_neighbor(self):
        rng = np.random.default_rng(17); n = 30
        target = rng.normal(size=n)*1e5; neighbor = rng.normal(size=(n,1))*2e5
        background = np.column_stack((np.ones(n),np.linspace(-1,1,n)))
        coeff = np.array([-.0012,.04,-.02,.0006])
        design = np.column_stack((target,background,neighbor)); data = design@coeff
        item = {'renderer':lambda p:target*u.MJy/u.sr/u.Jy, 'error':np.ones(n)*.2,
                'background_design':background, 'neighbor_design':neighbor}
        with patch.object(audit.study.parent.baseline.model, 'fit_epoch', side_effect=AssertionError('optimizer called')):
            result = audit.solve_wls(item,data,np.linspace(.4,1,n),[1,2])
        np.testing.assert_allclose(result['coefficients'],coeff,rtol=1e-10,atol=1e-12)
        self.assertLess(result['coefficients'][0],0); self.assertLess(result['cost'],1e-20)
        with self.assertRaises((u.UnitConversionError,ValueError)):
            audit.solve_wls({**item,'renderer':lambda p:target*u.Jy},data,np.ones(n),[1,2])

    def test_normalized_wls_refuses_frozen_rank_boundary(self):
        x = np.linspace(-1,1,20); data = np.ones(20); weights = np.ones(20)
        def item(epsilon):
            return {'renderer':lambda p:(1+epsilon*x)*u.MJy/u.sr/u.Jy,
                    'background_design':np.ones((20,1)), 'neighbor_design':np.empty((20,0)), 'error':np.ones(20)}
        with self.assertRaisesRegex(ValueError,'rank deficient'):
            audit.solve_wls(item(1e-11),data,weights,[0,0])
        self.assertTrue(np.isfinite(audit.solve_wls(item(1e-8),data,weights,[0,0])['cost']))

    def test_preparation_replay_requires_same_stage_and_exact_error(self):
        def fail(): raise ValueError('synthetic input failure')
        row = {'status':'preparation_failed', 'failure_stage':'preparation', 'error':'ValueError: synthetic input failure'}
        with self.assertRaises(audit.ReplayedPreparation):audit.replay_preparation(row,'preparation',fail)
        with self.assertRaises(ValueError):audit.replay_preparation(row,'geometry_or_realization',fail)
        with self.assertRaises(ValueError):audit.replay_preparation({**row,'error':'ValueError: other'},'preparation',fail)
        with self.assertRaises(ValueError):audit.replay_preparation({**row,'status':'fit_failed'},'preparation',fail)

    def test_independent_metrics_detect_gate_corruption_and_missing_pairs(self):
        keys, records = fixture(); rows = index(records)
        rows[('noiseless','g0','matched','0','isolated','600','0','corrected')].update(
            status='fit_failed',error='synthetic failure')
        rows[('noisy','g0','gaussian','3','modeled','1200','0','baseline')]['target_flux_jy'] = -.001
        summary = summarize_signal_control(records, keys)
        counts = audit.verify_metrics(records,keys,summary)
        self.assertEqual(counts['pairs'],320); self.assertEqual(counts['noisy_gates'],16)
        corrupted = copy.deepcopy(summary);corrupted['noiseless_clean_gate']['passed'] = True
        with self.assertRaisesRegex(ValueError, 'passed'): audit.verify_metrics(records,keys,corrupted)
        corrupted = copy.deepcopy(summary);corrupted['paired']['missing'] = 0
        with self.assertRaisesRegex(ValueError, 'missing'): audit.verify_metrics(records,keys,corrupted)
        corrupted = copy.deepcopy(summary);corrupted['noisy_clean_gates'][0]['exact_interval_95'][0] += .001
        with self.assertRaisesRegex(ValueError, 'interval'): audit.verify_metrics(records,keys,corrupted)
        with self.assertRaisesRegex(ValueError, 'missing or duplicate'): audit.verify_metrics(records[:-1],keys,summary)

    def test_physical_scene_metadata_phase_seed_and_null(self):
        g = geometry(); data = np.arange(81,dtype=float).reshape(9,9)/10
        key = ('null','g0','none','0','isolated','0','1','baseline')
        bank = type('Bank',(),{'standard_normal':lambda self,shape:data})()
        with patch.object(audit.np.random,'Generator',return_value=bank), \
             patch.object(audit.study.inputs,'standardized_noise',return_value=data):
            result = audit.study.inputs.realize(g,'null','none','isolated',0,1)
            audit.check_scene(g,key,result,{})
            result['metadata']['seed'] = [17,1]
            with self.assertRaisesRegex(ValueError,'seed'): audit.check_scene(g,key,result,{})
        self.assertIsNone(result['metadata']['target_native_xy'])

    def test_phase_and_companion_native_identity_are_required(self):
        g = geometry(); g['anchor_common'] = np.array([1.,2.])
        columns = np.column_stack((np.ones(len(g['x'])),np.zeros((len(g['x']),2))))
        g['synthetic_prepared'] = {'sample':{'background':columns}}
        def native(frame, common):
            return np.array([4.1,4.1]) if np.array_equal(common,g['anchor_common']) else np.array([4.25,4.25])
        # Gaussian itself is exercised separately; these deterministic stubs
        # isolate the native WCS and injected-phase guard.
        fraction = np.full(len(g['x']), 1e-5)
        def synthetic(geometry,section,truth,scene,flux,draw):
            surface = fraction*.0006/(1e6*geometry['omega'].to_value(u.sr))
            return {'target':surface,'companion':surface}
        with patch.object(audit.study.inputs.original,'native_position',side_effect=native), \
             patch.object(audit,'gaussian64',return_value=fraction), \
             patch.object(audit.study.inputs,'realize',side_effect=synthetic):
            audit.check_geometry(g,'0')
            with self.assertRaisesRegex(ValueError,'phase native'):audit.check_geometry(g,'3')
            g['companion_native'][0] += .1
            with self.assertRaisesRegex(ValueError,'companion native'):audit.check_geometry(g,'0')

    def test_saved_start_objectives_and_full_model_use_only_linear_solve(self):
        g = geometry(); n = len(g['x']); item = audit.study.inputs.model_for(g,'baseline',True)
        g['anchor_common'] = g['target_common'].copy()
        item = {**item, 'background_design':np.column_stack((np.ones(n),np.linspace(-1,1,n)))}
        target = item['renderer'](g['target_common']).value
        model = np.column_stack((target,item['background_design'],item['neighbor_design']))
        data = model@np.array([-.0003,.04,.01,.0006]); weights = np.ones(n)
        solved = audit.solve_wls(item,data,weights,g['target_common'])
        sample = {'data_mjysr':data.tolist(),'error_mjysr':g['error'].tolist(),
            'background_design':item['background_design'].tolist(), 'neighbor_design_per_jy':item['neighbor_design'].tolist(),
            'neighbor_ids':[audit.study.inputs.COMPANION_ID], 'neighbor_unit':'MJy / (Jy sr)',
            'x':g['x'].tolist(), 'y':g['y'].tolist()}
        item['neighbor_unit'] = sample['neighbor_unit']
        frame = {'obs_id':audit.study.OBS_ID,'weights':weights.tolist(),'target_flux_jy':-.0003,
            'background_coefficients':[.04,.01], 'neighbor_flux_jy':[.0006],
            'model':solved['model'].tolist(),'residual':solved['residual'].tolist(),
            'weighted_residual':solved['weighted_residual'].tolist(),'chi2_weighted':solved['cost']}
        starts = [{'stage':'final_fixed_weights','success':True,'position':g['target_common'].tolist(),
                   'start':(g['anchor_common']+np.asarray(offset)).tolist(), 'chi2':solved['cost']}
                  for offset in audit.study.parent.baseline.model.START_OFFSETS]
        fit = {'position':g['target_common'].tolist(),'frames':[frame],'numerical_support':True,
               'nonnegative_neighbors':False, 'data_unit':str(u.MJy/u.sr),
               'chi2_weighted':solved['cost'],'final_mode_audit':{'starts':starts}}
        row = {'samples':[sample], 'status':'fit_completed', 'fit':fit, 'target_flux_jy':-.0003,
               'numerical_support':True,
               'position_native':g['target_native'].tolist(), 'position_native_error':[0.,0.],
               'distance_to_companion_native':1.5}
        key = ('noiseless','g0','matched','0','modeled','600','0','baseline')
        with patch.object(audit.study.inputs,'fit_item',return_value=item), \
             patch.object(audit.study.inputs.original,'native_position',return_value=g['target_native']), \
             patch.object(audit.study.parent.baseline.model,'fit_epoch',side_effect=AssertionError('optimizer called')):
            checked = audit.check_fit(g,key,{'data':data},row)
            self.assertEqual(checked['successful_final_starts'],9)
            starts[3]['chi2'] = 1.
            with self.assertRaisesRegex(ValueError,'final start cost'):audit.check_fit(g,key,{'data':data},row)

    def test_paired_and_omitted_mismatch_detected(self):
        base = ('noiseless','g0','gaussian','0','modeled','600','0')
        records = [{'key':list((*base,arm)), 'payload':{'realization':{'realization_sha256':'same'}}}
                   for arm in ('baseline','corrected')]
        omitted = (*base[:4],'omitted',*base[5:])
        records += [{'key':list((*omitted,arm)), 'payload':{'realization':{'realization_sha256':'same'}}}
                    for arm in ('baseline','corrected')]
        audit.check_pair_hashes(records)
        records[-1]['payload']['realization']['realization_sha256'] = 'wrong'
        with self.assertRaisesRegex(ValueError,'realization differs'):audit.check_pair_hashes(records)

    def test_checkpoint_resume_keeps_failures_and_failed_receipt(self):
        keys = [('noiseless','g0','matched','0','isolated','600','0',arm)
                for arm in ('baseline','corrected')]
        keys += [('noiseless','g0','matched','0','modeled','600','0','baseline')]
        keys += [('noiseless','g1','matched','0','isolated','600','0',arm) for arm in ('baseline','corrected')]
        keys += [('noiseless','g0','matched','0','omitted','600','0',arm) for arm in ('baseline','corrected')]
        records = [{'key':list(keys[0]), 'checksum':'a', 'payload':{'status':'fit_completed','samples':[{}]}},
                   {'key':list(keys[1]), 'checksum':'b', 'payload':{'status':'fit_failed','error':'original optimizer failure'}},
                   {'key':list(keys[2]), 'checksum':'c', 'payload':{'status':'fit_completed','samples':[{}]}},
                   {'key':list(keys[3]), 'checksum':'d', 'payload':{'status':'preparation_failed', 'failure_stage':'geometry_or_realization','error':'ValueError: unavailable geometry'}},
                   {'key':list(keys[4]), 'checksum':'e', 'payload':{'status':'preparation_failed', 'failure_stage':'geometry_or_realization','error':'ValueError: different failure'}},
                   {'key':list(keys[5]), 'checksum':'f', 'payload':{'status':'preparation_failed', 'failure_stage':'preparation','error':'ValueError: unavailable model'}},
                   {'key':list(keys[6]), 'checksum':'g', 'payload':{'status':'preparation_failed', 'failure_stage':'geometry_or_realization','error':'ValueError: unavailable model'}}]
        with tempfile.TemporaryDirectory(dir=audit.study.ROOT) as temp, ExitStack() as stack:
            root = Path(temp); design = root/'design.json'; design.write_text('{}',encoding='utf-8')
            output = root/'study'; output.mkdir(); audit_dir = root/'audit'
            (root/'source.txt').write_text('synthetic audit source',encoding='utf-8')
            summary = {'protocol_commit':audit.COMMIT,'cell_digest':'digest',
                       'design_sha256':audit.study.parent.calibration.legacy.lab.digest(design),
                       'assessment_opened':False,'promotion':False,'metrics':{}}
            (output/'summary.json').write_text(json.dumps(summary),encoding='utf-8')
            stack.enter_context(patch.object(audit,'FILES',('source.txt',)))
            stack.enter_context(patch.object(audit,'AUDIT_DIR',audit_dir))
            stack.enter_context(patch.object(audit,'RECEIPT',audit_dir/'audit-receipt.json'))
            stack.enter_context(patch.object(audit.study,'ROOT',root))
            stack.enter_context(patch.object(audit.study,'DESIGN',design))
            stack.enter_context(patch.object(audit.study,'OUTPUT',output))
            stack.enter_context(patch.object(audit.study.parent,'assert_assessment_unopened'))
            metadata = {'fixture':('alpha','beta'), 'expected_keys':[keys[0]]}
            stack.enter_context(patch.object(audit.study.parent.frozen,'verify',return_value={
                'metadata':audit.study.parent.calibration.legacy.jsonable(metadata)}))
            stack.enter_context(patch.object(audit.study.parent.frozen,'runtime',return_value={}))
            stack.enter_context(patch.object(audit.study,'open_inputs',return_value=(None,np.zeros(3),metadata)))
            stack.enter_context(patch.object(audit.study,'expected_keys',return_value=keys))
            stack.enter_context(patch.object(audit.study,'open_journal',return_value=type('J',(),{'records':lambda self,require_complete:records})()))
            stack.enter_context(patch.object(audit.study.parent.calibration,'record_digest',return_value='digest'))
            stack.enter_context(patch.object(audit,'verify_metrics',return_value={'fixture':1}))
            stack.enter_context(patch.object(audit,'check_pair_hashes'))
            stack.enter_context(patch.object(audit,'check_geometry'))
            stack.enter_context(patch.object(audit,'check_scene'))
            def prepare(context,sid,obs,phase,coefficients):
                if sid == 'g1': raise ValueError('unavailable geometry')
                return {}
            def fit_item(geometry,realized,scene,arm):
                if scene == 'omitted': raise ValueError('unavailable model')
                return {}
            stack.enter_context(patch.object(audit.study.inputs,'prepare_geometry',side_effect=prepare))
            stack.enter_context(patch.object(audit.study.inputs,'realize',return_value={}))
            stack.enter_context(patch.object(audit.study.inputs,'fit_item',side_effect=fit_item))
            stack.enter_context(patch.object(audit.study.parent.baseline.previous,'descriptors',return_value=[]))
            checks = stack.enter_context(patch.object(audit,'check_fit',side_effect=[
                {'objective_available':True,'successful_final_starts':9}, ValueError('synthetic model mismatch')]))
            stack.enter_context(redirect_stdout(io.StringIO()))
            receipt = audit.run(); calls = checks.call_count; resumed = audit.run()
            saved = {tuple(row['key']):row['payload'] for row in
                     (json.loads(p.read_text(encoding='utf-8')) for p in (audit_dir/'cells'/'records').glob('*.json'))}
        self.assertEqual(receipt,resumed); self.assertEqual(calls,checks.call_count)
        self.assertEqual(receipt['identity']['upstream']['fixture'],['alpha','beta'])
        self.assertEqual(receipt['identity']['upstream']['expected_keys'],[list(keys[0])])
        self.assertEqual(receipt['status'],'failed'); self.assertEqual(len(receipt['failures']),3)
        self.assertEqual(receipt['counts'],{'verified':1,'input_checked_unavailable':3,'audit_mismatch':1,'unverified_failure':2})
        self.assertIn('synthetic model mismatch',receipt['failures'][0]['error'])
        self.assertEqual(saved[keys[3]]['replayed_preparation_error'],'ValueError: unavailable geometry')
        self.assertEqual(saved[keys[3]]['replayed_failure_stage'],'geometry_or_realization')
        self.assertEqual(saved[keys[5]]['replayed_preparation_error'],'ValueError: unavailable model')
        self.assertEqual(saved[keys[5]]['replayed_failure_stage'],'preparation')
        self.assertFalse(saved[keys[3]]['objective_available'])
        self.assertEqual(saved[keys[4]]['status'],'unverified_failure')
        self.assertEqual(saved[keys[6]]['status'],'unverified_failure')


if __name__ == '__main__': unittest.main()
