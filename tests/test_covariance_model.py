"""Independent controls for 0.8 nuisance fits and calibration isolation."""
import copy
import unittest
import numpy as np
from scripts import covariance_model as model
from scripts import covariance_study as study
from tests.test_motion import synthetic_frame


class CovarianceControls(unittest.TestCase):
    def test_curved_background_and_broadened_source_recover_centroid(self):
        anchor=np.array([31.5,31.5]);truth=anchor+[.23,-.11];frames=[];xy={}
        for i,offset in enumerate([(.2,-.3),(-.35,.15)]):
            f=synthetic_frame(offset);f['record']['obs_id']=str(i);yy,xx=np.indices((64,64))
            s=model.samples_for([f],[],{str(i):np.empty((0,2))},anchor)[0]
            # Independent full-image rendering at a known width mixture.
            narrow=model.motion.render_source(f,truth,1.)
            broad=study.source_image(f,truth,1.,'isotropic_015px')
            f['data']=7.*(.4*narrow+.6*broad)+2.+.01*xx-.02*yy+.0009*(xx-32)**2+.0005*(xx-32)*(yy-32)
            frames.append(f);xy[str(i)]=np.empty((0,2))
        fitted=model.fit(frames,[],xy,anchor)
        self.assertTrue(fitted['success']);np.testing.assert_allclose(fitted['position'],truth,atol=.002)
        self.assertEqual(len(fitted['covariance']),2)
        self.assertGreater(np.linalg.eigvalsh(fitted['covariance']).min(),0.)

    def test_width_mixture_keeps_flux_and_centroid(self):
        f=synthetic_frame();a=np.array([31.5,31.5]);s=model.samples_for([f],[],{'synthetic':np.empty((0,2))},a)[0]
        for eta in [0.,.4,1.]:
            c=model.at_width(s,eta)['epsf'];np.testing.assert_allclose(c,c[::-1,::-1],atol=1e-10)
            self.assertTrue(np.isfinite(c).all())

    @staticmethod
    def records():
        return [{'phase':'calibration','field_id':str(f),'patch_index':p,
            'models':{'candidate':{'accepted':True,'error_east_north_arcsec':[(-1)**p*2.,float(f-1)],
            'covariance_arcsec2':[[.1,0.],[0.,.1]]}}} for f in range(3) for p in range(3)]

    def test_calibrator_is_psd_and_does_not_shrink(self):
        cal=model.calibrate(self.records());raw=np.array([[.3,.1],[.1,.7]])
        calibrated=model.apply_covariance(raw,cal)
        self.assertGreaterEqual(cal['scale_squared'],1.)
        self.assertGreater(np.linalg.eigvalsh(np.asarray(cal['floor_arcsec2'])).min(),0.)
        self.assertGreaterEqual(np.linalg.eigvalsh(calibrated-raw).min(),-1e-10)

    def test_validation_truth_cannot_enter_calibration(self):
        records=self.records();records[0]['phase']='validation'
        with self.assertRaisesRegex(ValueError,'must not include'):model.calibrate(records)

    def test_rejected_records_do_not_fit_covariance(self):
        rows=self.records();expected=model.calibrate(rows)
        bad=copy.deepcopy(rows[0]);bad['models']['candidate'].update(accepted=False,error_east_north_arcsec=[1e6,1e6]);rows.append(bad)
        actual=model.calibrate(rows)
        self.assertEqual(actual['floor_arcsec2'],expected['floor_arcsec2'])
        self.assertEqual(actual['scale_squared'],expected['scale_squared'])
        self.assertEqual(actual['attempted'],expected['attempted']+1)

    def test_area_and_coverage_recomputed_without_changing_point_error(self):
        r={'models':{'candidate':{'numeric_valid':True,'accepted':True,'quality_reasons':[],
            'covariance_arcsec2':[[1.,0.],[0.,4.]],'error_east_north_arcsec':[2.,0.],
            'error_arcsec':2.,'mahalanobis2_raw':4.}}}
        study.apply_record(r,{'floor_arcsec2':[[1.,0.],[0.,0.]],'scale_squared':2.})
        v=r['models']['candidate'];self.assertEqual(v['error_arcsec'],2.)
        self.assertAlmostEqual(v['ellipse_area_inflation'],np.sqrt(8.))
        self.assertAlmostEqual(v['mahalanobis2_calibrated'],1.)

    def test_group_counts_keep_unavailable_attempts(self):
        records=[{'models':study.failure('registration_unavailable')} for _ in range(32)]
        s=study.summarize(records)
        self.assertEqual(s['models']['candidate']['accepted']['attempted'],32)
        self.assertEqual(s['models']['candidate']['accepted']['valid'],0)
        self.assertEqual(s['paired_numeric']['common'],0)


if __name__=='__main__':unittest.main()
