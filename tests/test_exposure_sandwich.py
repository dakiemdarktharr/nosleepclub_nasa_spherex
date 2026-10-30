import unittest
from unittest.mock import patch
import numpy as np
from scripts import exposure_sandwich as sandwich
from scripts import run_sandwich_study as study
from tests.test_continuous_epsf import sample_fixture


def sample(A,y,i):return {'A':np.asarray(A,float),'y':np.asarray(y,float),'frame':{'record':{'obs_id':str(i)}}}
def linear_residual(s,p):return s['A']@p-s['y']
def fit_template(samples,position):
    return {'samples':samples,'position':np.asarray(position,float),'success':True,'at_boundary':False,'information_rank':2}


class SandwichTests(unittest.TestCase):
    def test_nondiagonal_linear_gaussian_block_sandwich(self):
        rng=np.random.default_rng(9);samples=[]
        for i in range(8):
            A=np.array([[1.+.03*i,.35],[-.2,.8+.02*i],[.4,-.3]])
            samples.append(sample(A,A@np.array([.4,-.2])+rng.normal(size=3)*.3,i))
        H=sum(s['A'].T@s['A'] for s in samples);position=np.linalg.solve(H,sum(s['A'].T@s['y'] for s in samples))
        scores=np.array([s['A'].T@linear_residual(s,position) for s in samples]);B=scores.T@scores
        with patch.object(sandwich.joint,'residual_sample',side_effect=linear_residual):
            out=sandwich.compute(fit_template(samples,position))
        self.assertTrue(out['supported']);self.assertAlmostEqual(out['correction_factor'],8/6)
        np.testing.assert_allclose(out['hessians'][0],H,atol=1e-9)
        np.testing.assert_allclose(out['meat'],B,atol=1e-9)
        np.testing.assert_allclose(out['covariance_px2'],(8/6)*np.linalg.inv(H)@B@np.linalg.inv(H),atol=1e-9)
        self.assertGreater(abs(H[0,1]),.1);self.assertLess(np.linalg.norm(out['score_sum']),1e-9)
        self.assertLess(out['scalar_vs_residual_jacobian_difference'],1e-9)

    def test_profiled_flux_score_matches_residual_jacobian(self):
        rng=np.random.default_rng(23);base=sample_fixture(16);samples=[]
        for i in range(8):
            frame={**base['frame'],'record':{'obs_id':str(i)}}
            samples.append({**base,'frame':frame,'data':base['data']+rng.normal(size=len(base['data']))*base['error']})
        fit=fit_template(samples,[.21,-.16]);out=sandwich.compute(fit)
        self.assertIn('exposures',out)
        for s,item in zip(samples,out['exposures']):
            p=fit['position'];h=1e-5;v=np.eye(2)*h
            residual=lambda x:sandwich.joint.residual_sample(s,x)
            jac=np.column_stack([(residual(p+d)-residual(p-d))/(2*h) for d in v])
            np.testing.assert_allclose(item['score'],jac.T@residual(p),rtol=1e-3,atol=1e-3)

    def test_reject_boundary_few_duplicate_singular_hessian_and_meat(self):
        samples=[sample(np.eye(2),[1.,2.],i) for i in range(8)];fit=fit_template(samples,[0.,0.])
        self.assertEqual(sandwich.compute({**fit,'samples':samples[:7]})['reason'],'too_few_exposures')
        self.assertEqual(sandwich.compute({**fit,'at_boundary':True})['reason'],'centroid_at_boundary')
        self.assertEqual(sandwich.compute({**fit,'information_rank':1})['reason'],'singular_point_information')
        self.assertEqual(sandwich.compute({**fit,'samples':[samples[0]]*8})['reason'],'duplicate_exposure')
        with patch.object(sandwich.joint,'residual_sample',side_effect=linear_residual):
            self.assertEqual(sandwich.compute(fit)['reason'],'nonpositive_or_singular_meat')
            bad=[sample([[1.,0.],[0.,0.]],[i,1.],i) for i in range(8)]
            self.assertEqual(sandwich.compute(fit_template(bad,[0.,0.]))['reason'],'nonpositive_or_singular_hessian')

    def test_denominators_selections_and_separate_total_covariance(self):
        def method(q):return {'supported':True,'centroid_only':{'q':q,'covariance_arcsec2':np.eye(2)},
                              'plus_registration':{'q':q/2,'covariance_arcsec2':np.eye(2)*2}}
        m={k:method(2.) for k in study.METHODS}
        rows=[{'numeric_valid':True,'accepted':True,'error_east_north_arcsec':[1.,0.],'methods':m,'epochs':[]},
              {'numeric_valid':True,'accepted':False,'error_east_north_arcsec':[0.,2.],
               'methods':{**m,'exposure_sandwich':{'supported':False,'reasons':['singular']}},'epochs':[]},
              {'numeric_valid':False,'accepted':False,'failure':'ValueError','methods':{},'epochs':[]}]
        out=study.summarize(rows);self.assertEqual((out['attempts'],out['numeric'],out['accepted']),(3,2,1))
        self.assertEqual(out['selections']['common_supported']['attempts'],1)
        self.assertEqual(out['selections']['numeric']['methods']['exposure_sandwich']['unsupported'],1)
        g=out['selections']['numeric']['methods']['gauss_newton']
        self.assertEqual(g['centroid_only']['coverage']['50']['inside'],0)
        self.assertEqual(g['plus_registration']['coverage']['50']['inside'],2)
        self.assertEqual(g['centroid_only']['coverage']['50']['denominator'],2)
        self.assertIsNone(study.wilson(0,0))
        seeds=[v for f in study.seeds().values() for v in f.values()]
        self.assertEqual(len(set(seeds)),6);self.assertNotIn('20261030',seeds)

    def test_method_covariances_share_point_and_keep_registration_separate(self):
        fits=[]
        for scale in [1.,2.]:
            fits.append({'covariance':np.array([[.1,.02],[.02,.2]])*scale,
                'profile':{'supported':True,'covariance_px2':np.array([[.15,.01],[.01,.25]])*scale},
                'sandwich':{'supported':True,'covariance_px2':np.array([[.3,-.03],[-.03,.4]])*scale}})
        registration=np.array([[.01,.002],[.002,.03]]);error=np.array([.7,-.3])
        result=study.method_covariances(fits,registration,error);T=study.d.study.gaia.TRANSFORM
        for name,key in [('gauss_newton','covariance'),('profile_hessian','profile'),('exposure_sandwich','sandwich')]:
            parts=[f[key] if key=='covariance' else f[key]['covariance_px2'] for f in fits]
            centroid=T@sum(parts)@T.T;total=T@(sum(parts)+registration)@T.T
            self.assertTrue(result[name]['supported'])
            np.testing.assert_allclose(result[name]['centroid_only']['covariance_arcsec2'],centroid,atol=1e-12)
            np.testing.assert_allclose(result[name]['plus_registration']['covariance_arcsec2'],total,atol=1e-12)
            self.assertAlmostEqual(result[name]['centroid_only']['q'],float(error@np.linalg.solve(centroid,error)))
            self.assertAlmostEqual(result[name]['plus_registration']['q'],float(error@np.linalg.solve(total,error)))
        fits[0]['sandwich']={'supported':False,'reason':'too_few_exposures'}
        rejected=study.method_covariances(fits,registration,error)['exposure_sandwich']
        self.assertFalse(rejected['supported']);self.assertEqual(rejected['reasons'],['too_few_exposures'])


if __name__=='__main__':unittest.main()
