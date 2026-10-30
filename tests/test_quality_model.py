"""Controls for deblending and data-only gates, independent of sky-field results."""
import unittest
import numpy as np
from scripts import quality_model as model
from tests.test_motion import synthetic_frame


class QualityControls(unittest.TestCase):
    def test_vectorized_catalog_propagation_matches_original(self):
        source={'ra':133.7,'dec':-7.2,'ref_epoch':2016.,'parallax':12.,'pmra':23.,'pmdec':-35.}
        catalog=[{'gaia':source}];f=synthetic_frame();f['mjd']=61000.
        actual=model.positions(catalog,[f])[f['record']['obs_id']][0]
        np.testing.assert_allclose(actual,model.gaia.gaia_xy(source,61000.),atol=1e-9)

    def test_ir_neighbour_removes_centroid_bias_with_free_flux(self):
        anchor=np.array([31.5,31.5]);truth=anchor+[.23,-.11];neighbour=anchor+[1.8,.6]
        frames=[];positions={}
        for i,offset in enumerate([(.2,-.3),(-.35,.15)]):
            f=synthetic_frame(offset);f['record']['obs_id']=str(i)
            yy,xx=np.indices((64,64));f['data']=model.motion.render_source(f,truth,4+i)+model.motion.render_source(f,neighbour,7-i)+.01*xx-.02*yy+2
            frames.append(f);positions[str(i)]=np.array([neighbour])
        catalog=[{'id':'neighbour','row':{'w2mpro_pm':12.},'gaia':None}]
        fitted=model.fit(frames,catalog,positions,anchor)
        self.assertTrue(fitted['success']);np.testing.assert_allclose(fitted['position'],truth,atol=4e-4)
        self.assertGreater(np.linalg.norm(model.baseline_fit(frames,anchor)['position']-truth),.3)

    def test_converged_bad_model_is_rejected_without_using_truth(self):
        details=[{'amplitude':10.,'snr':20.,'core_coverage':1.,'core_rms':8.,'core_outlier_fraction':.2,'information_fraction':.8}]
        result=model.gate({'success':True,'at_boundary':False,'reduced_chi2':20.,'per_frame':details})
        self.assertFalse(result['accepted']);self.assertIn('poor_global_fit',result['reasons'])
        self.assertIn('structured_core_residual',result['reasons'])

    def test_unidentifiable_blend_is_not_a_precise_detection(self):
        fit={'success':True,'at_boundary':False,'reduced_chi2':1.,'per_frame':[
            {'amplitude':10.,'snr':20.,'core_coverage':1.,'core_rms':1.,'core_outlier_fraction':0.,'information_fraction':.001}]}
        self.assertIn('unresolved_blend',model.gate(fit)['reasons'])

    def test_low_residual_does_not_override_model_disagreement(self):
        f={'success':True,'at_boundary':False,'reduced_chi2':1.,'model_comparison':{'shift_px':.5,'limit_px':.2},
           'per_frame':[{'amplitude':10.,'snr':20.,'core_coverage':1.,'core_rms':1.,'core_outlier_fraction':0.,'information_fraction':.8}]}
        self.assertIn('model_disagreement',model.gate(f)['reasons'])

    def test_robust_pixel_fit_preserves_large_residual_warning(self):
        f=synthetic_frame();anchor=np.array([31.5,31.5]);truth=anchor+[.18,.05]
        f['data']=model.motion.render_source(f,truth,5)+2
        f['data'][32,33]+=5
        result=model.fit([f],[],{f['record']['obs_id']:np.empty((0,2))},anchor)
        self.assertGreater(result['per_frame'][0]['downweighted_pixels'],0)
        self.assertFalse(result['quality']['accepted'])
        self.assertGreater(result['reduced_chi2'],3)

    def test_truncated_core_is_not_reported_as_full_coverage(self):
        f=synthetic_frame();anchor=np.array([-.2,31.5])
        f['data']=model.motion.render_source(f,anchor,5)+2
        fitted=model.baseline_fit([f],anchor)
        self.assertLess(fitted['per_frame'][0]['core_coverage'],.75)
        self.assertIn('insufficient_core_pixels',fitted['quality']['reasons'])


if __name__=='__main__':unittest.main()
