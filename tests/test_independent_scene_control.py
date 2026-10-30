import copy
import unittest

import astropy.units as u
import numpy as np
from scipy.integrate import quad
from scipy.special import erf

from scripts import independent_scene_control as scene


def header(n=3,dt=1.):
    return {'SURLIM':n+2,'SURDLY':3,'TSAMP':dt,'XPOSURE':(n-1)*dt}


def draw(source,bg,error,gain,seed=24,**kw):
    return scene.draw_scene(source,bg,error,gain,header(),np.random.default_rng(seed),
                            gain_provenance={'source':'synthetic gain'},
                            source_provenance={'source':'synthetic Gaussian scene'},**kw)


class IndependentSceneTests(unittest.TestCase):
    def test_gaussian_pixel_integrals_against_independent_quad_and_erf(self):
        x=np.array([-2,0,1,4]);y=np.array([0,-1,2,3]);pos=[.23,-.37];sx=.8;sy=1.35
        actual=scene.gaussian_pixel_fractions(x,y,source_xy=pos,sigma_x=sx,sigma_y=sy)
        def integral(center,mu,sigma):
            return quad(lambda z:np.exp(-.5*((z-mu)/sigma)**2)/(np.sqrt(2*np.pi)*sigma),center-.5,center+.5,epsabs=1e-14)[0]
        expected=[integral(a,pos[0],sx)*integral(b,pos[1],sy) for a,b in zip(x,y)]
        np.testing.assert_allclose(actual,expected,rtol=1e-13,atol=1e-15)
        x0=.5*(erf((.5-pos[0])/(np.sqrt(2)*sx))-erf((-.5-pos[0])/(np.sqrt(2)*sx)))
        y0=.5*(erf((.5-pos[1])/(np.sqrt(2)*sy))-erf((-.5-pos[1])/(np.sqrt(2)*sy)))
        out=scene.gaussian_pixel_fractions([0],[0],source_xy=pos,sigma_x=sx,sigma_y=sy)
        self.assertAlmostEqual(out[0],x0*y0,places=14)
        # Positive-tail evaluation must not lose a representable probability.
        tail=scene.gaussian_pixel_fractions([9],[0],source_xy=[0,0],sigma_x=1,sigma_y=1)
        self.assertGreater(tail[0],0.)

    def test_varying_solid_angles_flux_and_window_not_renormalized(self):
        Y,X=np.mgrid[-20:21,-20:21];x=X.ravel();y=Y.ravel()
        omega=(8e-10+np.arange(len(x))*1e-14)*u.sr
        sources=[{'native_xy':[.25,-.5],'sigma_xy':[.8,1.3],'flux':3*u.mJy},
                 {'native_xy':[-1.3,.9],'sigma_xy':[1.6,.7],'flux':2*u.mJy}]
        result=scene.expected_scene(sources,x,y,omega)
        recovered=(result['expected_source']*omega).to_value(u.Jy).sum()
        self.assertAlmostEqual(recovered,.005,places=14)
        for s in result['per_source']:
            self.assertLessEqual(s['selected_fraction'],1.)
            self.assertAlmostEqual(s['selected_flux_jy']+s['missing_flux_jy'],s['flux_jy'],places=15)
        keep=(abs(x)<=1)&(abs(y)<=1)
        small=scene.expected_scene(sources,x[keep],y[keep],omega[keep])
        np.testing.assert_allclose(small['expected_source'].value,result['expected_source'].value[keep],rtol=0,atol=0)
        self.assertTrue(all(s['missing_fraction']>0 for s in small['per_source']))
        actual=(small['expected_source']*omega[keep]).to_value(u.Jy).sum()
        self.assertAlmostEqual(actual,sum(s['selected_flux_jy'] for s in small['per_source']),places=15)
        self.assertLess(actual,.005)
        zero=scene.expected_scene([],x[keep],y[keep],omega[keep])
        np.testing.assert_array_equal(zero['expected_source'].value,0.)
        self.assertEqual(zero['per_source'],[])

    def test_draw_matches_independent_poisson_increments_and_gaussian(self):
        expected=np.array([.4,1.2,.8])*scene.SURFACE
        bg=np.array([-.3,.2,0.])*scene.SURFACE;error=np.array([.1,.3,.2])*scene.SURFACE
        gain=np.array([.2,.3,.4])*scene.GAIN
        out=draw(expected,bg,error,gain,seed=41)
        rng=np.random.default_rng(41);times=np.arange(3,dtype=float);center=times-times.mean()
        ols=center/(center@center)
        increment_weights=np.array([ols[1:].sum(),ols[2:].sum()])
        lam=expected.value/gain.value
        source_noise=np.zeros(3)
        for weight in increment_weights:source_noise+=gain.value*weight*(rng.poisson(lam)-lam)
        background_noise=rng.normal(0,error.value)
        np.testing.assert_allclose(out['source_noise'].value,source_noise,atol=1e-15)
        np.testing.assert_allclose(out['background_noise'].value,background_noise,atol=1e-15)
        np.testing.assert_allclose(out['data'].value,expected.value+bg.value+source_noise+background_noise,atol=1e-15)
        variance=gain.value**2*lam*np.sum(increment_weights**2)
        np.testing.assert_allclose(out['added_variance'].value,variance,atol=1e-15)
        np.testing.assert_allclose(out['error'].value**2,error.value**2+variance,atol=1e-15)
        same=draw(expected,bg,error,gain,seed=41)
        np.testing.assert_array_equal(same['data'].value,out['data'].value)
        self.assertEqual(out['provenance']['rng_state_after'],same['provenance']['rng_state_after'])
        self.assertEqual(out['provenance']['source_ramp']['valid_pixels'],3)
        self.assertEqual(out['added_variance'].unit,scene.SURFACE**2)

    def test_empirical_moments_and_unclipped_negative_pixels(self):
        n=20000
        source=np.full(n,.4)*scene.SURFACE;bg=np.full(n,-.1)*scene.SURFACE
        error=np.full(n,.15)*scene.SURFACE;gain=np.full(n,.2)*scene.GAIN
        out=draw(source,bg,error,gain,seed=182)
        values=out['data'].value;expected=.3;variance=.0625
        self.assertLess(abs(values.mean()-expected),6*np.sqrt(variance/n))
        self.assertLess(abs(values.var(ddof=1)-variance),.006)
        self.assertTrue(np.any(values<0))
        np.testing.assert_allclose(out['expected_mean'].value,expected)
        np.testing.assert_allclose(out['error'].value**2,variance)

    def test_invalid_units_shapes_pixels_flux_and_provenance(self):
        for x,y in (([0,0],[1,1]),([.1],[0]),([0],[np.nan]),([],[])):
            with self.subTest(x=x),self.assertRaises(ValueError):scene.gaussian_pixel_fractions(x,y,source_xy=[0,0],sigma_x=1,sigma_y=1)
        for sig in (0.,-1.,np.nan,1e14):
            with self.assertRaises(ValueError):scene.gaussian_pixel_fractions([0],[0],source_xy=[0,0],sigma_x=sig,sigma_y=1)
        source={'native_xy':[0,0],'sigma_xy':[1,1],'flux':1*u.Jy}
        with self.assertRaises(ValueError):scene.expected_scene([source],[0],[0],1*u.sr)
        with self.assertRaises(ValueError):scene.expected_scene([source],[0],[0],np.array([0.])*u.sr)
        with self.assertRaises(ValueError):scene.expected_scene([{**source,'flux':-1*u.Jy}],[0],[0],np.ones(1)*u.sr)
        with self.assertRaises(ValueError):scene.expected_scene([{**source,'flux':1}],[0],[0],np.ones(1)*u.sr)
        with self.assertRaises(ValueError):scene.expected_scene([{**source,'flux':1*u.s}],[0],[0],np.ones(1)*u.sr)
        s=np.ones(2)*scene.SURFACE;g=np.ones(2)*scene.GAIN
        for a,b,c,d in ((-s,s,s,g),(s,s,-s,g),(s,s,s,np.zeros(2)*scene.GAIN),
                        (s,s,s,1*scene.GAIN),(s,s,s,np.ones(2)*u.Jy)):
            with self.assertRaises(ValueError):draw(a,b,c,d)
        with self.assertRaises(ValueError):scene.draw_scene(s,s,s,g,header(),np.random.default_rng(1),gain_provenance={},source_provenance={'source':'x'})
        with self.assertRaises(ValueError):scene.draw_scene(s,s,s,g,header(),np.random.default_rng(1),gain_provenance={'source':'x'},source_provenance={})
        rng=np.random.default_rng(9);state=copy.deepcopy(rng.bit_generator.state)
        with self.assertRaises(ValueError):scene.draw_scene(s,s,s,g,{'SURLIM':3},rng,gain_provenance={'source':'x'},source_provenance={'source':'x'})
        self.assertEqual(rng.bit_generator.state,state)


if __name__=='__main__':unittest.main()
