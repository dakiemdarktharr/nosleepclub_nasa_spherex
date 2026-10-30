import copy
from contextlib import ExitStack
from hashlib import sha256
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from astropy import units as u

from scripts import publish_neighbor_intervention as pub
from scripts import run_neighbor_intervention as study
from scripts import run_wise_linked_study as legacy
from scripts.constrained_linear_profile import profile_linear


def seal(row):
    row.pop('record_sha256',None)
    row['record_sha256']=sha256(legacy.encoded(row)).hexdigest()
    return row


def failure_rows():
    rows=[]
    for key in sorted(study.expected_keys()):
        if key[0]=='real':
            _,config,variant,epoch=key
            row={'section':'real','configuration':config,'variant':variant,'epoch':epoch}
        else:
            _,case,draw,variant,epoch=key
            row={'section':'control','configuration':'strict','case':case,'draw':int(draw),'variant':variant,'epoch':epoch}
        rows.append(seal({**row,'obs_ids':[],'status':'preparation_failed','error':'synthetic failure'}))
    return rows


def sample_and_frame():
    target=np.array([1.,0.,0.,0.]);bg=np.array([[0.],[1.],[0.],[0.]])
    neighbor=np.array([[0.],[0.],[1.],[0.]])
    data=np.array([-2.,.5,-1.,.3]);mean=np.array([-2.,.5,0.,0.]);resid=data-mean
    sample={'data_mjysr':data.tolist(),'error_mjysr':[1.]*4,'background_design':bg.tolist(),
            'neighbor_design_per_jy':neighbor.tolist(),'neighbor_ids':['N1'],'neighbor_unit':'MJy / (Jy sr)',
            'x':[0,1,2,3],'y':[0,0,0,0]}
    frame={'obs_id':'E1','neighbor_ids':['N1'],'weights':[1.]*4,'error':[1.]*4,
           'target_flux_jy':-2.,'background_coefficients':[.5],'neighbor_flux_jy':[0.],
           'neighbor_active_mask':[True],'negative_target_flux':True,'model':mean.tolist(),
           'residual':resid.tolist(),'raw_standardized_residual':resid.tolist(),
           'weighted_residual':resid.tolist(),'chi2_weighted':1.09,'linear_rank':3,'scaled_condition':1.,
           'scaled_gradient_free':[0.,0.],'scaled_gradient_nonnegative':[-.5],
           'scaled_free_stationarity_violation':0.,'scaled_bound_dual_violation':0.,
           'scaled_interior_stationarity_violation':0.,'scaled_complementarity_violation':0.}
    return sample,frame,target


def attach_synthetic_fit(row,error,supported=True):
    truth=np.asarray(study.RULES['controls']['displacement_sky_px']);anchor=np.asarray(study.RULES['anchor'])
    pos=anchor if row['epoch']=='before' else anchor+truth+np.linalg.solve(pub.T,np.asarray(error))
    frame={'obs_id':'synthetic','target_flux_jy':1.,'negative_target_flux':False,
           'neighbor_ids':[],'neighbor_flux_jy':[],'neighbor_active_mask':[]}
    row.update(status='fit_completed',obs_ids=['synthetic'],fit={'position':pos.tolist(),
        'numerical_support':supported,'numerical_reasons':[] if supported else ['multiple_near_best_modes'],
        'irls':{'converged':True},'at_boundary':False,'position_rank':2,
        'final_mode_audit':{'near_best_count':1 if supported else 2},'frames':[frame]})
    row.pop('error',None)
    return seal(row)


class NeighborPublicationTests(unittest.TestCase):
    def test_complete_build_with_all_failures_preserves_records(self):
        rows=failure_rows()
        report={'completed':True,'records':rows,'counts':{'planned':288,'recorded':288,'fit_completed':0,'failed':288},
                'source_hashes':{},'input_hashes':{},'opened_products':{},'runtime':{},'rules':legacy.jsonable(study.RULES)}
        class FakeRaw:
            def read_text(self,**kwargs):return json.dumps(report)
            def stat(self):return SimpleNamespace(st_size=100)
        expected='a'*64
        with ExitStack() as stack:
            stack.enter_context(patch.object(pub,'RAW',FakeRaw()))
            stack.enter_context(patch.object(pub,'verify_lock'))
            stack.enter_context(patch.object(pub.legacy.lab,'digest',return_value=expected))
            stack.enter_context(patch.object(pub.legacy,'relative',return_value='synthetic/raw.json'))
            stack.enter_context(patch.object(pub,'SavedRendererCache'))
            real,controls=pub.build(expected)
        self.assertEqual(len(real['records']),32)
        self.assertEqual(len(controls['paired_draws']),64)
        self.assertEqual(len(real['contrast_audits']),16)
        self.assertEqual(len(controls['contrast_audits']),128)
        self.assertTrue(all(not x['available'] for x in real['contrast_audits']+controls['contrast_audits']))
        self.assertEqual(len(controls['control_replay_checks']),256)
        self.assertEqual(real['counts']['failed'],288)

    def test_complete_build_invokes_both_saved_renderer_and_control_checks(self):
        rows=failure_rows();keyed={study.record_key(r):r for r in rows}
        real_row=keyed[('real','broad',study.VARIANTS[0]['id'],'before')]
        real_row.update(status='fit_completed',obs_ids=['synthetic'],fit={'position':[31.5,31.5],
                        'numerical_support':True,'numerical_reasons':[]})
        real_row.pop('error');seal(real_row)
        case=study.CASES[0]['id'];control_row=keyed[('control',case,'0',pub.ARMS[0],'before')]
        attach_synthetic_fit(control_row,[0.,0.]);control_row['samples']=[{'fake':True}];seal(control_row)
        report={'completed':True,'records':rows,'counts':{'planned':288,'recorded':288,'fit_completed':2,'failed':286},
                'source_hashes':{},'input_hashes':{},'opened_products':{},'runtime':{},'rules':legacy.jsonable(study.RULES)}
        class FakeRaw:
            def read_text(self,**kwargs):return json.dumps(report)
            def stat(self):return SimpleNamespace(st_size=100)
        class Cache:
            def get(self,*args):return ['synthetic-renderer']
            def control_geometry(self,*args):return ['synthetic-geometry']
        expected='a'*64
        with ExitStack() as stack:
            stack.enter_context(patch.object(pub,'RAW',FakeRaw()))
            stack.enter_context(patch.object(pub,'verify_lock'))
            stack.enter_context(patch.object(pub.legacy.lab,'digest',return_value=expected))
            stack.enter_context(patch.object(pub.legacy,'relative',return_value='synthetic/raw.json'))
            stack.enter_context(patch.object(pub,'SavedRendererCache',return_value=Cache()))
            audited=stack.enter_context(patch.object(pub,'audit_fit',return_value={'qualification':'synthetic'}))
            controls_checked=stack.enter_context(patch.object(pub,'check_control',return_value={'available':True,'realization_sha256':'synthetic'}))
            real,controls=pub.build(expected)
        self.assertEqual(audited.call_count,2)
        controls_checked.assert_called_once()
        self.assertEqual(len(real['attempt_audits']),1)
        self.assertEqual(sum(x['audit']['available'] for x in controls['control_replay_checks']),1)

    def test_complete_ledger_keeps_all_failures_and_refuses_tampering(self):
        rows=failure_rows();report={'completed':True,'records':rows,'counts':{'planned':288,'recorded':288,'fit_completed':0,'failed':288}}
        keyed=pub.audit_keys(report)
        self.assertEqual(len(keyed),288)
        with self.assertRaises(ValueError):pub.audit_keys({**report,'completed':False})
        with self.assertRaises(ValueError):pub.audit_keys({**report,'records':rows[:-1]})
        altered=copy.deepcopy(rows);altered[-1]=copy.deepcopy(altered[0])
        with self.assertRaises(ValueError):pub.audit_keys({**report,'records':altered})
        altered=copy.deepcopy(rows);altered[0]['error']='mutated'
        with self.assertRaisesRegex(ValueError,'checksum'):pub.audit_keys({**report,'records':altered})

    def test_lock_verifies_hash_provenance_runtime_and_frozen_commit(self):
        class FakePath:
            def __init__(self,text):self.text=text
            def read_text(self,**kwargs):return self.text
        hashes={'sources':{'x':'s'},'raw':{'y':{'sha256':'d','bytes':1}},'opened_products':{'z':'p'}}
        design={'rules':legacy.jsonable(study.RULES),**hashes}
        design_path=FakePath(json.dumps(design));raw_path=FakePath('unused');raw_sha='a'*64
        runtime={'python':'3.11','platform':'synthetic','packages':{'numpy':'locked'}}
        raw={'protocol_commit':pub.COMMIT,'protocol_sha256':pub.DESIGN_SHA,'rules':design['rules'],
             'source_hashes':hashes['sources'],'input_hashes':hashes['raw'],'opened_products':hashes['opened_products'],
             'runtime':{**runtime,'thread_environment':study.RULES['thread_environment_request'],
                 'thread_qualification':'environment requests recorded before CLI imports; not independent verification of every backend thread'}}
        with ExitStack() as stack:
            stack.enter_context(patch.object(pub,'DESIGN',design_path));stack.enter_context(patch.object(pub,'RAW',raw_path))
            stack.enter_context(patch.object(pub.legacy.lab,'digest',side_effect=lambda p:pub.DESIGN_SHA if p is design_path else raw_sha))
            stack.enter_context(patch.object(pub.study,'inventory',return_value=hashes))
            verified=stack.enter_context(patch.object(pub.study,'verify_frozen_commit'))
            stack.enter_context(patch.object(pub.legacy,'execution_runtime',return_value=runtime))
            stack.enter_context(patch.dict(pub.os.environ,study.RULES['thread_environment_request']))
            self.assertEqual(pub.verify_lock(raw,raw_sha),design)
            verified.assert_called_once_with(pub.COMMIT,design,pub.DESIGN_SHA)
            for key,value in [('protocol_commit','b'*40),('protocol_sha256','c'*64),('source_hashes',{'x':'changed'})]:
                with self.subTest(key=key),self.assertRaises(ValueError):pub.verify_lock({**raw,key:value},raw_sha)
            wrong=copy.deepcopy(raw);wrong['runtime']['packages']['numpy']='other'
            with self.assertRaisesRegex(ValueError,'runtime'):pub.verify_lock(wrong,raw_sha)
            with self.assertRaisesRegex(ValueError,'raw report SHA'):pub.verify_lock(raw,'d'*64)

    def test_frame_model_residual_chi_kkt_and_negative_target(self):
        sample,frame,target=sample_and_frame()
        out=pub.audit_frame(sample,frame,target,True,'E1')
        self.assertAlmostEqual(out['weighted_chi2'],1.09)
        self.assertTrue(out['negative_target_flux']);self.assertEqual(out['active_neighbor_count'],1)
        for change in ('model','flux','gradient','active','weights','units'):
            s=copy.deepcopy(sample);f=copy.deepcopy(frame)
            if change=='model':f['model'][0]+=1
            if change=='flux':f['neighbor_flux_jy'][0]=-.1
            if change=='gradient':f['scaled_gradient_nonnegative'][0]=.5
            if change=='active':f['neighbor_active_mask'][0]=False
            if change=='weights':f['weights'][0]=-1
            if change=='units':s['neighbor_unit']='1 / sr'
            with self.subTest(change=change),self.assertRaises(ValueError):pub.audit_frame(s,f,target,True,'E1')
        free=copy.deepcopy(frame);free.update(neighbor_flux_jy=[-1.],neighbor_active_mask=None,
            model=[-2.,.5,-1.,0.],residual=[0.,0.,0.,.3],raw_standardized_residual=[0.,0.,0.,.3],
            weighted_residual=[0.,0.,0.,.3],chi2_weighted=.09,scaled_gradient_free=[0.,0.,0.],scaled_gradient_nonnegative=[])
        self.assertAlmostEqual(pub.audit_frame(sample,free,target,False,'E1')['weighted_chi2'],.09)
        # Explicit heteroscedastic errors and IRLS weights distinguish raw
        # residuals, standardized residuals, and the weighted objective.
        weighted_sample=copy.deepcopy(sample);weighted_sample['error_mjysr']=[2.,1.,.5,2.]
        weighted_frame=copy.deepcopy(frame);weighted_frame.update(
            error=[2.,1.,.5,2.],weights=[.25,1.,.25,.25],
            raw_standardized_residual=[0.,0.,-2.,.15],weighted_residual=[0.,0.,-1.,.075],
            chi2_weighted=1.005625,scaled_gradient_nonnegative=[-1.])
        got=pub.audit_frame(weighted_sample,weighted_frame,target,True,'E1')
        self.assertAlmostEqual(got['weighted_chi2'],1.005625)
        self.assertAlmostEqual(got['raw_chi2'],4.0225)

    def test_saved_position_reconstructed_target_and_screening(self):
        sample,frame,target=sample_and_frame();point=[31.5,31.5];cost=frame['chi2_weighted']
        starts=[{'stage':'initial','start':(np.asarray(point)+offset).tolist(),'success':True,'position':point,'chi2':cost} for offset in study.model.START_OFFSETS]
        starts.extend({'stage':'irls_'+str(i),'start':point,'success':True,'position':point,'chi2':cost} for i in (1,2))
        modes={'starts':[{'stage':'final_fixed_weights','start':(np.asarray(point)+offset).tolist(),
                          'success':True,'position':point,'chi2':cost} for offset in study.model.START_OFFSETS],
               'point_chi2':cost,'modes':[{'position':point,'chi2':cost,'origin':'point','member_count':10,'delta_chi2':0.}],
               'near_best_modes':[{'position':point,'chi2':cost,'origin':'point','member_count':10,'delta_chi2':0.}],
               'near_best_count':1,'all_starts_failed':False,'best_improvement_chi2':0.,'better_than_point':False}
        fit={'position':point,'data_unit':'MJy / sr','nonnegative_neighbors':True,'frames':[frame],
             'weighted_residual':frame['weighted_residual'],'chi2_weighted':cost,'chi2_raw':cost,
             'irls':{'next_weight_max_difference':0.,'position_max_change':0.,'converged':True,'iterations':2,'max_iterations':20,
                     'weight_tolerance':.001,'position_tolerance_px':.0001},
             'start_reports':starts,'at_boundary':False,'position_rank':2,'final_mode_audit':modes,'numerical_support':True,'numerical_reasons':[]}
        row={'section':'real','variant':'plane_nearest_nonnegative','obs_ids':['E1'],'samples':[sample],'fit':fit}
        item={'obs_id':'E1','neighbor_ids':['N1'],'background_design':np.array(sample['background_design']),
              'neighbor_design':np.array(sample['neighbor_design_per_jy']),
              'data':np.array(sample['data_mjysr']),'error':np.array(sample['error_mjysr']),
              'metadata':{'x':sample['x'],'y':sample['y']},'renderer':lambda p:target*(u.MJy/u.sr/u.Jy)}
        audit=pub.audit_fit(row,[item])
        self.assertTrue(audit['numerical_support']);self.assertEqual(audit['frames'][0]['active_neighbor_count'],1)
        self.assertEqual(audit['mode_objective_replay']['successful_start_count'],9)
        self.assertLess(audit['mode_objective_replay']['max_absolute_difference'],1e-12)
        changed={**item,'renderer':lambda p:(target+np.array([0,0,0,.1]))*(u.MJy/u.sr/u.Jy)}
        with self.assertRaisesRegex(ValueError,'frame model'):pub.audit_fit(row,[changed])
        altered=copy.deepcopy(row);altered['fit']['numerical_support']=False
        with self.assertRaisesRegex(ValueError,'numerical support'):pub.audit_fit(altered,[item])

    def test_independent_final_start_replay_free_and_active_with_weights(self):
        sample,_,target=sample_and_frame();sample['error_mjysr']=[2.,1.,.5,2.]
        weights=[[.25,1.,.25,.25]]
        item={'renderer':lambda p:target*(u.MJy/u.sr/u.Jy)}
        point=[31.5,31.5]
        free,free_frames=pub.independent_cost_at_position([sample],[item],weights,point,False)
        constrained,bound_frames=pub.independent_cost_at_position([sample],[item],weights,point,True)
        self.assertAlmostEqual(free,.005625,places=12)
        self.assertAlmostEqual(constrained,1.005625,places=12)
        self.assertEqual(len(free_frames),1);self.assertEqual(len(bound_frames),1)
        starts=[{'success':True,'position':point,'chi2':constrained} for _ in range(8)]
        starts.append({'success':False,'message':'synthetic failed start'})
        row={'samples':[sample],'fit':{'frames':[{'weights':weights[0]}],
             'nonnegative_neighbors':True,'final_mode_audit':{'starts':starts}}}
        result=pub.replay_final_starts(row,[item])
        self.assertEqual(result['successful_start_count'],8);self.assertEqual(result['failed_start_count'],1)
        self.assertFalse(result['starts'][-1]['replayed'])
        self.assertLess(result['max_absolute_difference'],1e-12)
        wrong=copy.deepcopy(row);wrong['fit']['final_mode_audit']['starts'][2]['chi2']+=.001
        with self.assertRaisesRegex(ValueError,'mode cost mismatch'):pub.replay_final_starts(wrong,[item])

    def test_bvls_cost_matches_frozen_profile_on_varied_synthetic_designs(self):
        rng=np.random.default_rng(834)
        for index in range(24):
            n=18;target=rng.normal(size=n);bg=rng.normal(size=(n,2));neighbor=rng.normal(size=(n,3))
            error=rng.uniform(.2,2.,size=n);weight=rng.uniform(.1,1.,size=n);data=rng.normal(size=n)
            item={'renderer':lambda p,t=target:t*(u.MJy/u.sr/u.Jy)}
            sample={'data_mjysr':data.tolist(),'error_mjysr':error.tolist(),
                    'background_design':bg.tolist(),'neighbor_design_per_jy':neighbor.tolist()}
            for positive in (False,True):
                free=np.column_stack((target,bg))
                if not positive:free=np.column_stack((free,neighbor))
                bounded=neighbor if positive else np.empty((n,0))
                expected=profile_linear(data,error,free,bounded,weight)['chi2']
                actual,_=pub.independent_cost_at_position([sample],[item],[weight],[0,0],positive)
                with self.subTest(case=index,positive=positive):self.assertAlmostEqual(actual,expected,places=10)

    def test_pairing_requires_same_pixels_data_and_realization(self):
        sample,_,_=sample_and_frame()
        sample.update({'spatial_epsf':'nearest','background_degree':1,'raw_sha256':'s','cutout_url':'https://x.invalid'})
        a={'section':'control','obs_ids':['E1'],'samples':[sample],'control':{'realization_sha256':'abc'}}
        b=copy.deepcopy(a)
        self.assertTrue(pub.check_contrast(a,b))
        b['samples'][0]['data_mjysr'][0]+=.1
        with self.assertRaises(ValueError):pub.check_contrast(a,b)
        b=copy.deepcopy(a);b['control']['realization_sha256']='changed'
        with self.assertRaises(ValueError):pub.check_contrast(a,b)
        self.assertFalse(pub.check_contrast(a,{'samples':[]}))

    def test_control_oracle_mean_and_variance_without_noise_redraw(self):
        case=study.CASES[0];draw=0;seed=[study.RULES['controls']['seed_prefix'],0,draw,0,0]
        x=np.array([0,1,0,1]);y=np.array([0,0,1,1]);omega=np.full(4,1e-9)*u.sr
        gain=np.full(4,.2)*study.control.GAIN;error=np.full(4,.1)
        h={'SURLIM':5,'SURDLY':3,'TSAMP':1.,'XPOSURE':2.}
        background=np.column_stack([np.ones(4),np.zeros((4,2))])
        geo={'obs_id':'E1','frame':{'image_header':h},'x':x,'y':y,'omega':omega,'gain':gain,
             'background':background,'error':error,'neighbors':[]}
        spec=[{'native_xy':[0.,0.],'flux':case['target_flux_jy']*u.Jy,
               'sigma_xy':study.RULES['controls']['target_sigma_xy_native']}]
        scene=study.control.expected_scene(spec,x,y,omega)
        src=scene['expected_source'].value
        config=study.control.ramp._header_values(h)
        var=study.control.ramp.poisson_factor(config['n'])*gain.value*src/config['nominal_pipeline_integration_seconds']
        err=np.hypot(error,np.sqrt(var));data=src+.04
        first=legacy.jsonable(np.random.PCG64(np.random.SeedSequence(seed)).state)
        rampmeta={'header':config,'rng_state_before':first,
                  'source_values_sha256':study.control.ramp._digest_array(src[None,:],'<f8'),
                  'gain_values_sha256':study.control.ramp._digest_array(gain.value[None,:],'<f8'),
                  'valid_mask_sha256':study.control.ramp._digest_array(np.ones((1,4),bool),'u1')}
        f={'obs_id':'E1','seed':seed,'per_source':scene['per_source'],
           'provenance':{'rng_bit_generator':'PCG64','rng_state_before':first,'source_ramp':rampmeta},
           'pixel_omega_sr':omega.value.tolist(),'gain_mjysr_per_electron_rate':gain.value.tolist(),
           'expected_source_mjysr':src.tolist(),'background_mjysr':[.04]*4,'source_noise_mjysr':[0.]*4,
           'added_variance_mjysr2':var.tolist()}
        sample={'data_mjysr':data.tolist(),'error_mjysr':err.tolist()}
        realized=[{'obs_id':'E1','data':sample['data_mjysr'],'error':sample['error_mjysr']}]
        metadata={'truth_position_sky_px':study.RULES['controls']['before_position'],'frames':[f],
                  'realization_sha256':sha256(legacy.encoded(realized)).hexdigest()}
        row={'section':'control','case':case['id'],'draw':draw,'epoch':'before','obs_ids':['E1'],
             'samples':[sample],'control':metadata}
        with patch.object(pub.inputs,'native_position',return_value=np.array([0.,0.])):
            self.assertTrue(pub.check_control(row,[geo])['available'])
            bad=copy.deepcopy(row);bad['control']['frames'][0]['added_variance_mjysr2'][0]+=.1
            with self.assertRaisesRegex(ValueError,'oracle source variance'):pub.check_control(bad,[geo])

    def test_draw_denominators_and_errors_from_independent_reference(self):
        rows=failure_rows();bykey={study.record_key(r):r for r in rows};case=study.CASES[0]['id']
        for draw,free_error,nonneg_error,support in [(0,[1.,0.],[0.,2.],True),(1,[0.,1.],[2.,0.],False)]:
            for arm,error in zip(pub.ARMS,(free_error,nonneg_error)):
                for epoch in ('before','after'):
                    r=bykey[('control',case,str(draw),arm,epoch)]
                    attach_synthetic_fit(r,error,supported=(support or arm==pub.ARMS[0]))
        for epoch in ('before','after'):
            attach_synthetic_fit(bykey[('control',case,'2',pub.ARMS[0],epoch)],[3.,4.])
        summary,paired=pub.control_summary(bykey,{})
        self.assertEqual(len(paired),64)
        case_result=summary['cases'][0];self.assertEqual(case_result['planned_draws'],16)
        free,positive=case_result['arms']
        self.assertEqual(free['selections']['all_completed']['n'],3)
        self.assertEqual(positive['selections']['all_completed']['n'],2)
        self.assertAlmostEqual(free['selections']['all_completed']['rms_arcsec'],3.)
        self.assertAlmostEqual(free['selections']['all_completed']['p90_arcsec'],4.2)
        self.assertEqual(case_result['paired']['common_completed']['n'],2)
        self.assertEqual(case_result['paired']['common_numerically_supported']['n'],1)
        self.assertAlmostEqual(case_result['paired']['common_completed']['rms_difference_nonnegative_minus_free_arcsec'],1.)
        self.assertAlmostEqual(case_result['paired']['common_numerically_supported']['mean_paired_radial_error_difference_arcsec'],1.)
        self.assertFalse(paired[2]['arms'][pub.ARMS[1]]['completed'])
        self.assertIsNone(paired[2]['arms'][pub.ARMS[1]]['error_arcsec'])

    def test_real_pair_spread_includes_unsupported_and_failure(self):
        rows=failure_rows();bykey={study.record_key(r):r for r in rows}
        for variant,error,supported in [(study.VARIANTS[0]['id'],[0,0],True),(study.VARIANTS[1]['id'],[1,2],False)]:
            for epoch in ('before','after'):
                row=bykey[('real','broad',variant,epoch)]
                anchor=np.asarray(study.RULES['anchor']);pos=anchor if epoch=='before' else anchor+np.linalg.solve(pub.T,np.asarray(error))
                row.update(status='fit_completed',obs_ids=['synthetic'],fit={'position':pos.tolist(),
                    'numerical_support':supported,'numerical_reasons':[] if supported else ['multiple_near_best_modes']})
        configs=pub.real_summary(bykey);broad=configs[0]
        self.assertEqual(broad['complete_pairs'],2);self.assertEqual(broad['numerical_supported_pairs'],1)
        self.assertAlmostEqual(broad['max_pairwise_spread_arcsec'],np.sqrt(5),places=12)
        self.assertEqual(broad['refusal_counts']['multiple_near_best_modes'],2)
        self.assertEqual(len(broad['pairs']),8)
        self.assertIsNone(broad['pairs'][2]['east_north_arcsec'])

    def test_optional_public_products_recompute_metrics_and_hashes(self):
        if not all(p.exists() for p in (pub.REAL_OUT,pub.CONTROLS_OUT,pub.OVERVIEW_OUT)):
            self.skipTest('completed public products not built')
        real_bytes=pub.REAL_OUT.read_bytes();control_bytes=pub.CONTROLS_OUT.read_bytes()
        real=json.loads(real_bytes);controls=json.loads(control_bytes)
        overview=json.loads(pub.OVERVIEW_OUT.read_text(encoding='utf-8'))
        self.assertEqual(overview['provenance']['real_report']['sha256'],sha256(real_bytes).hexdigest())
        self.assertEqual(overview['provenance']['controls_report']['sha256'],sha256(control_bytes).hexdigest())
        self.assertEqual(overview['provenance']['real_report']['bytes'],len(real_bytes))
        self.assertEqual(overview['provenance']['controls_report']['bytes'],len(control_bytes))
        self.assertEqual(len(real['records']),32);self.assertEqual(len(controls['paired_draws']),64)
        self.assertLess(pub.OVERVIEW_OUT.stat().st_size,150_000)
        for case in overview['controls']['cases']:
            draws=[d for d in controls['paired_draws'] if d['case']==case['case']]
            self.assertEqual(len(draws),16)
            for arm in case['arms']:
                rows=[d['arms'][arm['variant']]['error_east_north_arcsec'] for d in draws if d['arms'][arm['variant']]['completed']]
                self.assertEqual(arm['selections']['all_completed']['n'],len(rows))
                if rows:
                    a=np.asarray(rows);radial=np.linalg.norm(a,axis=1)
                    self.assertAlmostEqual(arm['selections']['all_completed']['rms_arcsec'],np.sqrt(np.mean(radial**2)),places=12)
                    self.assertAlmostEqual(arm['selections']['all_completed']['p90_arcsec'],np.percentile(radial,90),places=12)
                    np.testing.assert_allclose(arm['selections']['all_completed']['mean_error_east_north_arcsec'],a.mean(axis=0),atol=1e-12)
        if pub.RAW.exists():
            raw_bytes=pub.RAW.read_bytes()
            self.assertEqual(sha256(raw_bytes).hexdigest(),overview['provenance']['raw_report_sha256'])
            raw=json.loads(raw_bytes);expected={study.record_key(r):r['record_sha256'] for r in raw['records']}
            for d in controls['paired_draws']:
                for arm in pub.ARMS:
                    for epoch,rec in d['arms'][arm]['epochs'].items():
                        self.assertEqual(rec['record_sha256'],expected[('control',d['case'],str(d['draw']),arm,epoch)])


if __name__=='__main__':unittest.main()
