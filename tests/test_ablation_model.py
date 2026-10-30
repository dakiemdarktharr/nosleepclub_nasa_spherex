"""Independent numerical, failure-isolation and calibration-routing controls."""
import copy
import unittest
from unittest.mock import patch
import numpy as np
from scripts import ablation_model as model
from scripts import ablation_study as study
from scripts import conditional_covariance as cc
from tests.test_motion import synthetic_frame


class AblationControls(unittest.TestCase):
    def setUp(self):model.motion.WCS=model.motion.base.grid_wcs()

    def frames(self,curved=False):
        anchor=np.array([31.5,31.5]);truth=anchor+[.23,-.11];frames=[];xy={}
        for i,offset in enumerate([(.2,-.3),(-.35,.15)]):
            f=synthetic_frame(offset);f['record']['obs_id']=str(i);yy,xx=np.indices((64,64))
            f['data']=model.motion.render_source(f,truth,7.)+2.+.01*xx-.02*yy
            if curved:f['data']+=.01*(xx-32)**2+.008*(xx-32)*(yy-32)
            frames.append(f);xy[str(i)]=np.empty((0,2))
        return anchor,truth,frames,xy

    def test_quadratic_recovers_centroid_in_curved_background(self):
        anchor,truth,frames,xy=self.frames(True);ref=model.motion.fit_position(frames,anchor,multistart=True)
        fit=model.fit(frames,[],xy,anchor,'quadratic_fixed',ref)
        np.testing.assert_allclose(fit['position'],truth,atol=3e-4)
        self.assertEqual(fit['parameter_count'],2)

    def test_plane_fixed_matches_frozen_07_estimator(self):
        anchor,_,frames,xy=self.frames();ref=model.motion.fit_position(frames,anchor,multistart=True)
        actual=model.fit(frames,[],xy,anchor,'plane_fixed',ref);expected=model.old.fit(frames,[],xy,anchor)
        np.testing.assert_allclose(actual['position'],expected['position'],atol=1e-10)
        np.testing.assert_allclose(actual['covariance'],expected['covariance'],atol=1e-10)
        self.assertEqual(actual['quality']['accepted'],expected['quality']['accepted'])

    def test_flexible_models_recover_center_and_marginalize_width(self):
        anchor,truth,frames,xy=self.frames()
        for f in frames:f['data']=study.prior.source_image(f,truth,7.,'isotropic_015px')+2.
        ref=model.motion.fit_position(frames,anchor,multistart=True)
        for kind in ['plane_flexible','quadratic_flexible']:
            result=model.fit(frames,[],xy,anchor,kind,ref)
            np.testing.assert_allclose(result['position'],truth,atol=.002)
            self.assertEqual(result['parameter_count'],3);self.assertGreater(np.linalg.eigvalsh(result['covariance']).min(),0.)

    def test_one_model_failure_does_not_erase_other_models(self):
        anchor,_,frames,xy=self.frames();original=model.fit
        def isolated(*args,**kwargs):
            if args[4]=='quadratic_fixed':raise ValueError('deliberate isolated exception')
            return original(*args,**kwargs)
        with patch.object(study.model,'fit',side_effect=isolated):
            r=study.measure([frames[0]],[frames[1]],[],xy,[anchor,anchor],study.KINDS,truth=[0.,0.])
        self.assertFalse(r['quadratic_fixed']['numeric_valid']);self.assertTrue(r['plane_fixed']['numeric_valid'])
        self.assertTrue(r['plane_flexible']['numeric_valid'])

    def test_background_uses_original_annulus_and_resists_target_flux(self):
        rng=np.random.default_rng(93);anchor=np.array([31.5,31.5]);f=synthetic_frame();yy,xx=np.indices((64,64))
        f['data']=2.+.01*xx-.02*yy+rng.normal(0,.05,(64,64));xy={'synthetic':np.empty((0,2))}
        before=model.background([f],xy,anchor)['score']
        f['data']+=model.motion.render_source(f,anchor,50.)
        after=model.background([f],xy,anchor)['score']
        self.assertAlmostEqual(before,after,places=8);self.assertTrue(.6<before<1.4)


class ConditionalControls(unittest.TestCase):
    @staticmethod
    def records():
        rng=np.random.default_rng(104);rows=[]
        for field in range(3):
            for patch_index in range(8):
                for snr in [7.,14.]:
                    for bg in [1.,2.]:
                        err=rng.normal(size=2)*(1. if snr<10 else .5)*bg
                        rows.append({'phase':'calibration','field_id':str(field),'patch_index':patch_index,
                            'background':{'score':bg},'models':{'plane_fixed':{'accepted':True,'observed_snr':snr,
                            'error_east_north_arcsec':err.tolist(),'covariance_arcsec2':[[.1,0.],[0.,.1]]}}})
        return rows

    def test_floor_and_quantile_patches_are_separate(self):
        rows=self.records();expected=cc.fit(rows,'plane_fixed');changed=copy.deepcopy(rows)
        for r in changed:
            if r['patch_index']%2==1:r['models']['plane_fixed']['error_east_north_arcsec']=[30.,20.]
        actual=cc.fit(changed,'plane_fixed')
        for key in actual['nodes']:
            self.assertEqual(actual['nodes'][key]['parameters']['floor_arcsec2'],expected['nodes'][key]['parameters']['floor_arcsec2'])

    def test_conditional_covariance_psd_and_nonshrinking(self):
        cal=cc.fit(self.records(),'plane_fixed');raw=np.array([[.2,.03],[.03,.1]])
        for snr in [7.,14.]:
            for bg in [1.,2.]:
                value=cc.apply(raw,{'observed_snr':snr,'background_score':bg},cal)
                self.assertTrue(value['supported']);self.assertGreaterEqual(np.linalg.eigvalsh(np.asarray(value['covariance_arcsec2'])-raw).min(),-1e-12)

    def test_routing_uses_observed_features_and_abstains_outside_support(self):
        cal=cc.fit(self.records(),'plane_fixed');raw=np.eye(2)
        f={'observed_snr':7.,'background_score':1.,'injected_snr':1000.,'truth_error':[1e6,1e6]}
        self.assertEqual(cc.classify(f),'snr_low_bg_smooth')
        f['injected_snr']=.01;f['truth_error']=[0.,0.];self.assertEqual(cc.classify(f),'snr_low_bg_smooth')
        self.assertFalse(cc.apply(raw,{'observed_snr':10000.,'background_score':1.},cal)['supported'])

    def test_validation_errors_cannot_enter_fit(self):
        rows=self.records();rows[0]['phase']='validation'
        with self.assertRaisesRegex(ValueError,'Only calibration'):cc.fit(rows,'plane_fixed')

    def test_sparse_cells_pool_instead_of_fitting_unstable_floor(self):
        rows=self.records();rows=[r for r in rows if not (r['models']['plane_fixed']['observed_snr']>10 and r['background']['score']>1.5)]
        cal=cc.fit(rows,'plane_fixed');node=cal['nodes']['snr_high_bg_structured']
        self.assertFalse(node['local_fitted']);self.assertNotEqual(node['parameter_source'],'snr_high_bg_structured')

    def test_rejected_case_truth_does_not_change_calibration(self):
        rows=self.records();expected=cc.fit(rows,'plane_fixed');bad=copy.deepcopy(rows[0]);bad['models']['plane_fixed'].update(accepted=False,error_east_north_arcsec=[1e6,1e6]);rows.append(bad)
        actual=cc.fit(rows,'plane_fixed');self.assertEqual(actual['nodes'],expected['nodes'])


class SelectionControls(unittest.TestCase):
    @staticmethod
    def fields():
        def value(error):
            return {'numeric_valid':True,'accepted':True,'quality_reasons':[],'error_arcsec':error,
                'error_east_north_arcsec':[error,0.],'mahalanobis2_raw':1.,
                'before':{'width_at_boundary':False},'after':{'width_at_boundary':False}}
        fields=[]
        for f in range(3):
            rows=[]
            for p in range(4):
                for truth in study.RULES['development_truth_psfs']:
                    for snr in [2.,4.]:
                        for delta in [[0.,0.],[.6,.05]]:
                            rows.append({'patch_index':p,'truth_psf':truth,'snr_per_frame':snr,'truth_delta_px':delta,
                                'background':{'score':1.+.1*f},'models':{k:value(1. if k=='plane_fixed' else .8) for k in study.KINDS}})
            fields.append({'field':{'id':str(f)},'injections':rows,'real_controls':[{'models':{k:value(1. if k=='plane_fixed' else .8) for k in study.KINDS}} for _ in range(4)]})
        return fields

    def test_one_bad_group_prevents_pooled_rms_from_selecting_complex_model(self):
        fields=self.fields()
        for kind in study.KINDS[1:]:
            v=fields[0]['injections'][0]['models'][kind];v.update(error_arcsec=4.,error_east_north_arcsec=[4.,0.])
        selected=study.choose(fields)
        self.assertEqual(selected['selected_model'],'plane_fixed')
        self.assertTrue(all(not c['eligible_to_replace'] for c in selected['candidates'].values()))

    def test_feature_cut_does_not_depend_on_truth_or_fit_error(self):
        fields=self.fields();expected=study.feature_thresholds(fields)
        for f in fields:
            for r in f['injections']:
                r['truth_delta_px']=[999.,999.]
                for v in r['models'].values():v.update(error_arcsec=1e8,accepted=False)
        self.assertEqual(study.feature_thresholds(fields),expected)


if __name__=='__main__':unittest.main()
