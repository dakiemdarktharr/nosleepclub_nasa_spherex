from hashlib import sha256
from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import run_wise_linked_study as study


class LinkedStudyTests(unittest.TestCase):
    def test_packing_preserves_order_and_refuses_missing_or_duplicate_predictions(self):
        renderer=lambda p: p
        prepared=[{'obs_id':'a','data':np.array([1.]),'error':np.array([2.]),
                   'nuisance':np.ones((1,1)),'renderer':renderer,'unused_metadata':123}]
        prediction={'obs_id':'a','relative_coefficient':1.2,'chosen_center_um':4.7}
        result=study.packed_samples(prepared,[prediction],{'mode':'shared'})[0]
        self.assertEqual(set(result),{'data','error','nuisance','renderer','coefficient','coefficient_provenance'})
        self.assertEqual(result['coefficient'],1.2)
        self.assertIs(result['renderer'],renderer)
        with self.assertRaises(ValueError):study.packed_samples(prepared,[],{'mode':'shared'})
        with self.assertRaises(ValueError):study.packed_samples(prepared,[prediction,prediction],{'mode':'shared'})
        self.assertEqual(study.packed_samples(prepared,[],{'mode':'independent'})[0]['coefficient'],1.)

    def test_pairs_distinguish_sensitivity_and_conditional_covariance(self):
        rows=[]
        for variant,delta in (('independent',[.5,.1]),('shared_r7_68_a0',[.7,.2])):
            for epoch,p in (('before',[31.,32.]),('after',np.array([31.,32.])+delta)):
                fit={'position':list(p),'inference_supported':True,
                     'position_covariance_px2':np.eye(2).tolist(),'profile_hessian':{'supported':False}}
                rows.append({'configuration':'broad','variant':variant,'epoch':epoch,'status':'fit_completed','fit':fit})
        result=study.pair_summaries(rows)
        candidate=next(x for x in result if x['variant']=='shared_r7_68_a0')
        scale=abs(study.inputs.gaia.TRANSFORM[0,0])
        np.testing.assert_allclose(candidate['east_north_arcsec'],[-.7*scale,.2*scale],atol=1e-12)
        self.assertAlmostEqual(candidate['change_from_independent_arcsec'],np.hypot(.2,.1)*scale)
        np.testing.assert_allclose(candidate['gn_conditional_centroid_covariance_arcsec2'],2*scale**2*np.eye(2))
        self.assertNotIn('profile_conditional_centroid_covariance_arcsec2',candidate)
        self.assertNotIn('accuracy',candidate)

    def test_checkpoint_checksum_and_atomic_roundtrip(self):
        row={'configuration':'strict','variant':'independent','epoch':'before','status':'fit_failed','error':'synthetic'}
        row['record_sha256']=sha256(study.encoded(row)).hexdigest()
        report={'records':[row]}
        parent=study.ROOT/'data/raw/benchmark'
        parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as directory,patch.object(study,'OUTPUT',Path(directory)/'checkpoint.json'):
            self.assertTrue(Path(directory).resolve().is_relative_to(parent.resolve()))
            study.save_report(report)
            saved=json.loads(study.OUTPUT.read_text(encoding='utf-8'))
            self.assertFalse(saved['completed'])
            self.assertEqual(saved['counts']['failures'],1)
            self.assertEqual(saved['counts']['planned_epoch_attempts'],28)
            before=study.OUTPUT.read_bytes()
            study.save_report(saved)
            self.assertEqual(study.OUTPUT.read_bytes(),before)
            saved['records'][0]['error']='changed'
            with self.assertRaisesRegex(RuntimeError,'checksum'):study.save_report(saved)

    def run_mocked(self, *, configurations, variants, fail_before_prepare=False,
                   fail_before_spectrum=False, fail_broad_config=False, repeat=False,
                   expected_complete=False,fail_before_metadata=False,fail_before_describe=False):
        """Exercise runner/checkpoint boundaries without real inputs or fitting."""
        parent=study.ROOT/'data/raw/benchmark'
        parent.mkdir(parents=True,exist_ok=True)
        fake_protocol={'sources':{},'raw':{},'opened_products':{}}
        counts={'prepare':[], 'spectral':[], 'fit':[]}
        def configuration(_frames,label):
            if label=='broad' and fail_broad_config:raise KeyError('synthetic configuration')
            groups=[[{'record':{'obs_id':label+'-before'}}],
                    [{'record':{'obs_id':label+'-after'}}]]
            return groups,[],{}, {'predicted_motion':{'description':'synthetic context'}}
        def prepare(group,_catalog,_xy,_anchor):
            obs=group[0]['record']['obs_id'];counts['prepare'].append(obs)
            if obs.endswith('-before') and fail_before_prepare:raise KeyError('synthetic preparation')
            sample={'x':np.array([2.,3.]),'y':np.array([1.,1.]),'zone':3,
                    'frame':{'record':{'cutout_url':'https://synthetic.invalid/cutout','sha256':'synthetic-sha'}}}
            if obs.endswith('-before') and fail_before_metadata:sample.pop('x')
            def describe(p):
                if obs.endswith('-before') and fail_before_describe:raise KeyError('synthetic renderer metadata')
                return {'source_xy':list(p),'provenance':'synthetic'}
            return [{'obs_id':obs,'data':np.array([1.,2.]),'error':np.array([.2,.3]),
                     'nuisance':np.ones((2,1)),'renderer':lambda p:None,'sample':sample,
                     'nuisance_provenance':'synthetic nuisance','renderer_provenance':'synthetic renderer',
                     'describe_renderer':describe}]
        def spectral(group,**kwargs):
            obs=group[0]['record']['obs_id'];counts['spectral'].append((obs,kwargs))
            if obs.endswith('-before') and fail_before_spectrum:raise KeyError('synthetic spectrum '+obs)
            return ([{'obs_id':obs,'relative_coefficient':1.2,'chosen_center_um':4.7}],{'synthetic':{'sha256':'test'}})
        def fit(packed,anchor,**kwargs):
            counts['fit'].append({'packed':packed,'anchor':anchor,'kwargs':kwargs})
            return {'position':[31.5,31.5],'inference_supported':True,
                    'position_covariance_px2':np.eye(2),'profile_hessian':{'supported':False}}
        with tempfile.TemporaryDirectory(dir=parent) as directory, ExitStack() as stack:
            stack.enter_context(redirect_stdout(io.StringIO()))
            stack.enter_context(patch.object(study,'OUTPUT',Path(directory)/'synthetic-checkpoint.json'))
            stack.enter_context(patch.object(study,'verify_design',return_value=fake_protocol))
            stack.enter_context(patch.object(study.lab,'digest',return_value='synthetic-protocol-hash'))
            stack.enter_context(patch.object(study,'execution_runtime',return_value={'runtime':'synthetic'}))
            stack.enter_context(patch.object(study.subprocess,'check_output',return_value='synthetic-commit\n'))
            stack.enter_context(patch.object(study.inputs,'read_verified_frames',return_value=([],{})))
            stack.enter_context(patch.object(study.inputs,'configuration',side_effect=configuration))
            stack.enter_context(patch.object(study.inputs,'prepared_samples',side_effect=prepare))
            stack.enter_context(patch.object(study.inputs,'spectral_predictions',side_effect=spectral))
            stack.enter_context(patch.object(study.model,'fit_epoch',side_effect=fit))
            study.run(configurations,variants)
            data=json.loads(study.OUTPUT.read_text(encoding='utf-8'))
            if repeat:
                before=study.OUTPUT.read_bytes();nfit=len(counts['fit']);nspec=len(counts['spectral'])
                study.run(configurations,variants)
                self.assertEqual(len(counts['fit']),nfit)
                self.assertEqual(len(counts['spectral']),nspec)
                self.assertEqual(study.OUTPUT.read_bytes(),before)
            self.assertEqual(data['counts']['planned_epoch_attempts'],28)
            self.assertEqual(data['completed'],expected_complete)
            for row in data['records']:
                self.assertEqual(row['record_sha256'],sha256(study.encoded({k:v for k,v in row.items() if k!='record_sha256'})).hexdigest())
            return data,counts

    def test_epoch_preparation_failure_keeps_after_and_resumes(self):
        variants=[study.VARIANTS[0],study.VARIANTS[1]]
        report,calls=self.run_mocked(configurations=['broad'],variants=variants,fail_before_prepare=True,repeat=True)
        self.assertEqual(report['counts']['recorded_epoch_attempts'],4)
        self.assertEqual(report['counts']['fit_completed'],2)
        for row in report['records']:
            if row['epoch']=='before':
                self.assertEqual(row['status'],'preparation_failed');self.assertIn('KeyError',row['error'])
            else:
                self.assertEqual(row['status'],'fit_completed')
                self.assertEqual(row['samples'][0]['x'],[2.,3.])
                self.assertEqual(row['samples'][0]['at_fitted_position']['provenance'],'synthetic')
        self.assertEqual([c[0] for c in calls['spectral']],['broad-after'])
        self.assertEqual(calls['spectral'][0][1]['normalization_jy'],.0005)
        self.assertEqual(len(calls['fit']),2)

    def test_spectral_failure_in_one_epoch_does_not_block_other(self):
        report,calls=self.run_mocked(configurations=['broad'],variants=[study.VARIANTS[1]],fail_before_spectrum=True)
        self.assertEqual(report['counts']['recorded_epoch_attempts'],2)
        before,after=report['records']
        self.assertEqual(before['status'],'preparation_failed');self.assertIn('broad-before',before['error'])
        self.assertEqual(after['status'],'fit_completed')
        self.assertEqual([x[0] for x in calls['spectral']],['broad-before','broad-after'])
        self.assertEqual(len(calls['fit']),1)
        self.assertEqual(after['predictions'][0]['relative_coefficient'],1.2)

    def test_configuration_failure_does_not_block_other_configuration(self):
        report,calls=self.run_mocked(configurations=['broad','strict'],variants=[study.VARIANTS[0],study.VARIANTS[1]],
                                     fail_broad_config=True)
        self.assertEqual(report['counts']['recorded_epoch_attempts'],8)
        self.assertEqual(report['counts']['failures'],4)
        for row in report['records']:
            self.assertEqual(row['status'],'preparation_failed' if row['configuration']=='broad' else 'fit_completed')
        self.assertEqual(len(calls['fit']),4)
        self.assertEqual([x[0] for x in calls['spectral']],['strict-before','strict-after'])

    def test_all_28_mocked_attempts_recorded(self):
        report,calls=self.run_mocked(configurations=['broad','strict'],variants=study.VARIANTS,expected_complete=True)
        self.assertEqual(report['counts']['recorded_epoch_attempts'],28)
        self.assertEqual(report['counts']['fit_completed'],28)
        self.assertEqual(len(calls['fit']),28)
        self.assertEqual(len(calls['spectral']),24)
        self.assertTrue(all(x[1]['normalization_jy']==.0005 for x in calls['spectral']))

    def test_sample_metadata_failure_retained_before_fit(self):
        report,calls=self.run_mocked(configurations=['broad'],variants=[study.VARIANTS[0]],fail_before_metadata=True)
        before,after=report['records']
        self.assertEqual(before['status'],'preparation_failed')
        self.assertEqual(before['failure_stage'],'sample_metadata')
        self.assertEqual(after['status'],'fit_completed')
        self.assertEqual(len(calls['fit']),1)

    def test_postfit_metadata_failure_retains_point_and_refuses_screening(self):
        report,calls=self.run_mocked(configurations=['broad'],variants=[study.VARIANTS[0]],fail_before_describe=True)
        before,after=report['records']
        self.assertEqual(before['status'],'fit_completed')
        self.assertTrue(before['renderer_metadata_failed'])
        self.assertFalse(before['fit']['inference_supported'])
        self.assertEqual(before['fit']['position'],[31.5,31.5])
        self.assertTrue(after['fit']['inference_supported'])
        self.assertEqual(len(calls['fit']),2)


if __name__=='__main__':unittest.main()
