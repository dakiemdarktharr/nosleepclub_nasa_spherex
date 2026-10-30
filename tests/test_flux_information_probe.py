import unittest
from unittest.mock import patch
import numpy as np
from scripts import flux_information_probe as probe


def toy():
    # Non-orthogonal 2D derivatives and one plane-like nuisance direction.
    q=np.ones((6,1))/np.sqrt(6)
    p=np.array([1.,2.,-.5,.7,-1.,.2])
    d=np.column_stack([np.array([.4,.2,-.7,.3,-.1,.8]),np.array([-.2,.6,.1,.5,-.8,-.3])])
    s={'q':q,'rank':1,'error':np.ones(6),'p0':p,'D':d}
    return s


def fake_stamp(s,x):return np.column_stack([s['p0']+s['D']@x,np.ones(6)])


class FluxInformationProbeTests(unittest.TestCase):
    def test_analytic_variable_projection_jacobian(self):
        s=toy();point=np.array([.13,-.22]);data=np.array([.1,1.,-1.,2.,0.,3.])
        with patch.object(probe.candidate.baseline.motion,'stamp_model',side_effect=fake_stamp):
            g=probe.geometry([s],point,[1.7]);r=probe.trial(g,[data]);e=g['entries'][0]
            y=data-s['q']@(s['q'].T@data);a=e['p']@y/e['I'];res=a*e['p']-y
            jac=a*e['transverse']-np.outer(e['p'],e['D'].T@res/e['I'])
            h=1e-6;fd=np.column_stack([(probe.residual(s,point+v*h,data)-probe.residual(s,point-v*h,data))/(2*h) for v in np.eye(2)])
            np.testing.assert_allclose(jac,fd,rtol=1e-8,atol=1e-8)
            np.testing.assert_allclose(r['jtj'],fd.T@fd,rtol=1e-8,atol=1e-8)
            self.assertGreater(abs(g['fisher_effective'][0,1]),1e-3)
            self.assertGreaterEqual(np.linalg.eigvalsh(g['fisher_known']-g['fisher_effective']).min(),-1e-12)

    def test_deterministic_gaussian_quadrature_expected_information(self):
        s=toy();point=np.array([.13,-.22]);amp=1.7
        with patch.object(probe.candidate.baseline.motion,'stamp_model',side_effect=fake_stamp):
            g=probe.geometry([s],point,[amp]);mean=amp*fake_stamp(s,point)[:,0]
            draws=[probe.trial(g,[mean+sign*np.sqrt(6)*v]) for v in np.eye(6) for sign in [-1,1]]
            np.testing.assert_allclose(np.mean([x['jtj'] for x in draws],axis=0),g['expected_jtj'],rtol=1e-8,atol=1e-8)
            for k in [0,1]:np.testing.assert_allclose(np.mean([x['hessians'][k] for x in draws],axis=0),g['fisher_effective'],rtol=3e-5,atol=3e-5)
            self.assertAlmostEqual(np.mean([x['profile_chi2'] for x in draws]),g['dof'],places=10)
            np.testing.assert_allclose(np.mean([x['profile_score'] for x in draws],axis=0),np.zeros(2),atol=1e-10)

    def test_reject_rank_deficiency_and_allow_negative_estimated_amplitude(self):
        s=toy();point=np.zeros(2)
        with patch.object(probe.candidate.baseline.motion,'stamp_model',side_effect=fake_stamp):
            g=probe.geometry([s],point,[1.]);r=probe.trial(g,[-2*s['p0']])
            self.assertLess(r['profile_amplitudes'][0],0)
            bad={**s,'D':np.column_stack([s['D'][:,0],s['D'][:,0]])}
            with self.assertRaisesRegex(ValueError,'rank deficient'):probe.geometry([bad],point,[1.])


if __name__=='__main__':unittest.main()
