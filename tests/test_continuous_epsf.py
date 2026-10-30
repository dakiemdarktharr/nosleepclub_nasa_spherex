import unittest
from unittest.mock import patch

import numpy as np
from scipy.ndimage import map_coordinates
from scripts import continuous_epsf_model as candidate
from scripts import ablation_model as baseline
from scripts import run_continuous_epsf_study as study


def sample_fixture(pad, true_position=(.23,-.17)):
    yy,xx=np.indices((33,33),dtype=float)
    raw=np.asarray(np.exp(-((xx-16)**2+(yy-16)**2)/22)+.001,dtype=np.float32)
    table=np.zeros(1,dtype=[('EPSF',np.float32,(33,33))]);table['EPSF'][0]=raw
    frame={'epsf_table':table,'epsf_oversampling':5.,'mjd':60000.,'record':{'obs_id':'synthetic'}}
    gy,gx=np.mgrid[-6:7,-6:7];x=gx.ravel().astype(float);y=gy.ravel().astype(float)
    sample={'frame':frame,'anchor':np.zeros(2),'native_center':np.zeros(2),'jacobian':np.eye(2),
            'x':x,'y':y,'zone':0,'epsf':candidate.padded_coefficients(frame,0,pad),
            'data':np.zeros(len(x)),'error':np.ones(len(x))*.05,
            'background':np.column_stack([np.ones(len(x)),x/6,y/6]),'neighbours':[]}
    sample['data']=3*baseline.motion.stamp_model(sample,np.array(true_position))[:,0]+.1+.01*x
    sample['original_error']=sample['error'].copy()
    return baseline.joint.prepare(sample,[])


class ContinuousEpsfTests(unittest.TestCase):
    def test_padding_zero_reproduces_frozen_position_and_covariance(self):
        sample=sample_fixture(0);reference={'position':np.zeros(2),'covariance':np.eye(2)*.01}
        with patch.object(candidate.old,'samples_for',return_value=[sample]):
            frozen=baseline.fit([],[],{},np.zeros(2),'plane_fixed',reference)
            padded=candidate.fit([],[],{},np.zeros(2),reference,pad=0)
        np.testing.assert_allclose(padded['position'],frozen['position'],atol=1e-12)
        np.testing.assert_allclose(padded['covariance'],frozen['covariance'],atol=1e-12)
        self.assertEqual(padded['quality'],frozen['quality'])

    def test_pad16_flux_center_and_continuity(self):
        s=sample_fixture(16);raw=np.asarray(s['frame']['epsf_table']['EPSF'][0],float);norm=raw*25/raw.sum()
        coeff=s['epsf'];gy,gx=np.indices(raw.shape,dtype=float)
        recovered=map_coordinates(coeff,[gy+16,gx+16],order=3,mode='constant',prefilter=False)
        np.testing.assert_allclose(recovered,norm,atol=1e-12)
        self.assertAlmostEqual(recovered.sum(),25.,places=10)
        self.assertAlmostEqual(recovered[16,16],norm[16,16],places=12)
        # x=3.2 puts this native pixel at the unpadded 33-cell support edge.
        one={**s,'x':np.array([3.2]),'y':np.array([0.]),'background':np.zeros((1,3))}
        a=baseline.motion.stamp_model(one,np.array([-1e-8,0.]))[0,0]
        b=baseline.motion.stamp_model(one,np.array([1e-8,0.]))[0,0]
        self.assertLess(abs(a-b),1e-7)

    def test_noiseless_padded_signal_recovered(self):
        s=sample_fixture(16);reference={'position':np.zeros(2),'covariance':np.eye(2)*.01}
        with patch.object(candidate.old,'samples_for',return_value=[s]):
            fit=candidate.fit([],[],{},np.zeros(2),reference)
        self.assertTrue(candidate.numeric_valid(fit))
        np.testing.assert_allclose(fit['position'],[.23,-.17],atol=1e-5)

    def test_rank_and_boundary_are_invalid(self):
        f={'success':True,'at_boundary':False,'per_frame':[{'amplitude':1.}],
           'information_rank':2,'position':np.zeros(2),'covariance':np.eye(2)}
        self.assertTrue(candidate.numeric_valid(f))
        self.assertFalse(candidate.numeric_valid({**f,'at_boundary':True}))
        self.assertFalse(candidate.numeric_valid({**f,'information_rank':1}))
        self.assertFalse(candidate.numeric_valid({**f,'covariance':np.diag([1.,0.])}))

    def test_paired_summary_keeps_failures_and_support_denominators(self):
        base={'numeric_valid':True,'accepted':True,'error_arcsec':1.,'mahalanobis2_raw':1.}
        good={'numeric_valid':True,'accepted':True,'error_arcsec':2.,'gauss_newton_q':3.}
        bad={'numeric_valid':False,'accepted':False}
        result=study.summarize([{'baseline':base,'candidate':good},{'baseline':base,'candidate':bad}])
        self.assertEqual(result['attempts'],2)
        self.assertEqual(result['baseline_numeric']['count'],2)
        self.assertEqual(result['common_accepted']['count'],1)
        self.assertEqual(result['common_accepted']['candidate_profile']['available'],0)


if __name__=='__main__':unittest.main()
