import unittest
from unittest.mock import patch

import numpy as np
from astropy import units as u

from scripts import neighbor_epoch_model as model


UNIT=u.MJy/u.sr
XY=np.array([(x,y) for y in range(-3,4) for x in range(-3,4)],float)


def gaussian(position):
    d=XY-position
    values=np.exp(-np.sum(d*d,axis=1)/1.3)
    return values/values.sum()


def renderer(position):return gaussian(position)*(UNIT/u.Jy)


def make_frames(position=(.21,-.27),target=(4.,6.),neighbor=(2.,3.),outlier=False):
    background=np.column_stack((np.ones(len(XY)),XY[:,0],XY[:,1]))
    neighbor_template=gaussian(np.array([1.1,.6]))[:,None]
    result=[]
    for i,(amplitude,nflux) in enumerate(zip(target,neighbor)):
        error=.015*(1+.08*np.abs(XY[:,0])+.1*i)
        data=amplitude*gaussian(np.array(position))+nflux*neighbor_template[:,0]+background@np.array([.1,.002,-.003])
        if outlier and i==0:data=data.copy();data[0]+=1.4
        result.append({'obs_id':'synthetic-'+str(i),'data':data,'error':error,
                       'background_design':background,'neighbor_design':neighbor_template,
                       'neighbor_ids':['synthetic-neighbor'],'neighbor_unit':str(UNIT/u.Jy),'renderer':renderer})
    return result


class NeighborEpochTests(unittest.TestCase):
    def test_fixed_position_profile_matches_full_wls_both_interventions(self):
        samples=make_frames();position=np.array([.21,-.27])
        for bounded in (False,True):
            problem=model.NeighborEpochProblem(samples,data_unit=UNIT,nonnegative_neighbors=bounded)
            out=problem.profile(position)
            self.assertEqual([f['obs_id'] for f in out['frames']],['synthetic-0','synthetic-1'])
            for frame,raw in zip(out['frames'],samples):
                X=np.column_stack([gaussian(position),raw['background_design'],raw['neighbor_design']])
                beta=np.linalg.lstsq(X/raw['error'][:,None],raw['data']/raw['error'],rcond=None)[0]
                self.assertAlmostEqual(frame['target_flux_jy'],beta[0],places=11)
                np.testing.assert_allclose(frame['background_coefficients'],beta[1:4],atol=1e-12)
                np.testing.assert_allclose(frame['neighbor_flux_jy'],beta[4:],atol=1e-11)
                np.testing.assert_allclose(frame['model'],X@beta,atol=1e-12)
                if bounded:self.assertFalse(frame['neighbor_active_mask'][0])
                else:self.assertIsNone(frame['neighbor_active_mask'])

    def test_noiseless_position_and_positive_neighbors(self):
        for bounded in (False,True):
            with self.subTest(bounded=bounded):
                out=model.fit_epoch(make_frames(),[0.,0.],data_unit=UNIT,nonnegative_neighbors=bounded)
                np.testing.assert_allclose(out['position'],[.21,-.27],atol=1e-7)
                self.assertEqual(len([x for x in out['start_reports'] if x['stage']=='initial']),9)
                self.assertEqual(len(out['final_mode_audit']['starts']),9)
                self.assertTrue(out['irls']['converged'])
                self.assertTrue(out['numerical_support'])
                self.assertLess(out['chi2_raw'],1e-16)
                self.assertNotIn('covariance',out);self.assertNotIn('snr',out)
                np.testing.assert_allclose([f['target_flux_jy'] for f in out['frames']],[4.,6.],atol=1e-7)
                np.testing.assert_allclose([f['neighbor_flux_jy'][0] for f in out['frames']],[2.,3.],atol=1e-7)

    def test_negative_target_retained_and_negative_neighbor_is_bounded(self):
        samples=make_frames(target=(-4.,-6.),neighbor=(-2.,-3.))
        unconstrained=model.NeighborEpochProblem(samples,data_unit=UNIT,nonnegative_neighbors=False).profile([.21,-.27])
        constrained=model.NeighborEpochProblem(samples,data_unit=UNIT,nonnegative_neighbors=True).profile([.21,-.27])
        self.assertTrue(all(f['negative_target_flux'] for f in unconstrained['frames']))
        self.assertTrue(all(f['negative_target_flux'] for f in constrained['frames']))
        self.assertTrue(all(f['neighbor_flux_jy'][0]<0 for f in unconstrained['frames']))
        self.assertTrue(all(f['neighbor_flux_jy'][0]==0 and f['neighbor_active_mask'][0] for f in constrained['frames']))
        self.assertGreater(constrained['chi2_weighted'],unconstrained['chi2_weighted'])

    def test_no_neighbor_columns_and_unit_failure(self):
        frames=make_frames(neighbor=(0.,0.))
        for f in frames:
            f['neighbor_design']=np.empty((49,0));f['neighbor_ids']=[]
        for bounded in (False,True):
            out=model.NeighborEpochProblem(frames,data_unit=UNIT,nonnegative_neighbors=bounded).profile([.21,-.27])
            np.testing.assert_allclose([x['target_flux_jy'] for x in out['frames']],[4.,6.],atol=1e-12)
            self.assertTrue(all(len(x['neighbor_flux_jy'])==0 for x in out['frames']))
        bad=[{**f,'renderer':lambda p:np.ones(49)*u.Jy} for f in frames]
        with self.assertRaisesRegex(ValueError,'renderer output units'):
            model.NeighborEpochProblem(bad,data_unit=UNIT,nonnegative_neighbors=True).profile([0,0])

    def test_irls_rebuild_and_nonconvergence_preserve_point(self):
        frames=make_frames(outlier=True)
        out=model.fit_epoch(frames,[0,0],data_unit=UNIT,nonnegative_neighbors=True,max_irls_iterations=2)
        self.assertFalse(out['irls']['converged'])
        self.assertFalse(out['numerical_support'])
        self.assertIn('irls_not_converged',out['numerical_reasons'])
        self.assertTrue(np.isfinite(out['position']).all())
        diff=[]
        for frame in out['frames']:
            desired=np.minimum(1.,2.5/np.maximum(np.abs(frame['raw_standardized_residual']),1e-300))
            diff.append(np.max(np.abs(desired-frame['weights'])))
        self.assertAlmostEqual(max(diff),out['irls']['next_weight_max_difference'],places=15)
        self.assertLess(out['frames'][0]['weights'][0],.1)

    def test_all_start_failures_and_boundary_are_explicit(self):
        bad=make_frames()
        for f in bad:f['renderer']=lambda p:np.zeros(len(XY))*(UNIT/u.Jy)
        with self.assertRaises(model.NeighborFitError) as exc:
            model.fit_epoch(bad,[0,0],data_unit=UNIT,nonnegative_neighbors=True)
        self.assertEqual(len(exc.exception.start_reports),9)
        self.assertTrue(all(not x['success'] for x in exc.exception.start_reports))
        boundary=model.fit_epoch(make_frames(position=(3.1,0.)),[0,0],data_unit=UNIT,nonnegative_neighbors=True)
        self.assertTrue(boundary['at_boundary']);self.assertFalse(boundary['numerical_support'])
        self.assertIn('boundary',boundary['numerical_reasons'])

    def test_final_mode_audit_detects_better_and_failed_starts(self):
        frames=make_frames();problem=model.NeighborEpochProblem(frames,data_unit=UNIT,nonnegative_neighbors=True)
        point=np.array([-.6,.4]);audit=model.audit_final_modes(problem,np.zeros(2),point)
        self.assertTrue(audit['better_than_point'])
        self.assertGreater(audit['best_improvement_chi2'],1e-4)
        np.testing.assert_array_equal(point,[-.6,.4])
        original=model._attempt
        def fail_final(res,jac,low,high,start,stage):
            if stage=='final_fixed_weights':return None,{'stage':stage,'start':start.copy(),'success':False,'message':'synthetic failure'}
            return original(res,jac,low,high,start,stage)
        with patch.object(model,'_attempt',side_effect=fail_final):
            out=model.fit_epoch(frames,[0,0],data_unit=UNIT,nonnegative_neighbors=True)
        self.assertTrue(out['final_mode_audit']['all_starts_failed'])
        self.assertEqual(len(out['final_mode_audit']['starts']),9)
        self.assertIn('final_mode_audit_failed',out['numerical_reasons'])
        self.assertFalse(out['numerical_support'])
        actual_audit=model.audit_final_modes
        def mark_better(problem,anchor,position):
            result=actual_audit(problem,anchor,position)
            return {**result,'better_than_point':True,'best_improvement_chi2':.2}
        with patch.object(model,'audit_final_modes',side_effect=mark_better):
            out=model.fit_epoch(frames,[0,0],data_unit=UNIT,nonnegative_neighbors=True)
        np.testing.assert_allclose(out['position'],[.21,-.27],atol=1e-7)
        self.assertIn('better_final_weight_mode',out['numerical_reasons'])
        self.assertFalse(out['numerical_support'])

    def test_multiple_modes_refused_without_point_replacement(self):
        def periodic(p):return gaussian(np.array([.4*np.sin(2*np.pi*p[0]/1.5),p[1]]))*(UNIT/u.Jy)
        frames=make_frames(position=(0.,.1))
        for f in frames:
            f['renderer']=periodic
            f['data']=4.*periodic(np.array([0.,.1])).value+2*f['neighbor_design'][:,0]+f['background_design']@np.array([.1,.002,-.003])
        out=model.fit_epoch(frames,[0,0],data_unit=UNIT,nonnegative_neighbors=True)
        self.assertGreater(out['final_mode_audit']['near_best_count'],1)
        self.assertIn('multiple_near_best_modes',out['numerical_reasons'])
        self.assertFalse(out['numerical_support'])
        self.assertAlmostEqual(out['chi2_weighted'],out['final_mode_audit']['point_chi2'],places=12)

    def test_invalid_inputs_and_scaled_neighbor_unit(self):
        frames=make_frames()
        for change in ({'neighbor_unit':'1 / sr'}, {'data':np.full(49,np.nan)},
                       {'error':np.zeros(49)}, {'neighbor_design':np.zeros((49,1))},
                       {'neighbor_ids':[]}, {'neighbor_ids':['','']},
                       {'background_design':np.ones((49,60))}):
            candidate=[{**frames[0],**change},frames[1]]
            with self.subTest(change=list(change)),self.assertRaises(ValueError):
                model.NeighborEpochProblem(candidate,data_unit=UNIT,nonnegative_neighbors=True).profile([0,0])
        with self.assertRaises(ValueError):model.NeighborEpochProblem([frames[0],frames[0]],data_unit=UNIT,nonnegative_neighbors=True)
        with self.assertRaises(ValueError):model.fit_epoch(frames,[0,0],data_unit=UNIT,nonnegative_neighbors=True,max_irls_iterations=1)


if __name__=='__main__':unittest.main()
