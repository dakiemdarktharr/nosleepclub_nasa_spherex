import unittest

import numpy as np
import astropy.units as u
from scipy.integrate import quad

from scripts.sed_flux_coefficient import sed_flux_coefficient


def run(*, wave=None, flux=None, usable=None, rwave=None, response=None,
        local=5*u.um, fiducial=5*u.um, alpha=0., gap=1*u.um, **kwargs):
    if wave is None:wave=np.array([4.,4.5,5.,5.5,6.])*u.um
    if flux is None:flux=np.array([2.,2.,2.,2.,2.])*u.Jy
    if usable is None:usable=np.ones(len(wave),bool)
    if rwave is None:rwave=np.array([4.1,4.6,5.4,5.9])*u.um
    if response is None:response=np.array([-.01,1.,.8,-.02])*u.one
    options={'spectrum_provenance':'test spectrum', 'response_provenance':'lab fixture',
             'reference_provenance':'assumed power law'}
    options.update(kwargs)
    return sed_flux_coefficient(wave,flux,usable,rwave,response,local_center=local,
                                fiducial_center=fiducial,reference_alpha=alpha,
                                maximum_gap=gap,**options)


class SedFluxCoefficientTests(unittest.TestCase):
    def test_same_reference_recovers_local_flux(self):
        # Alpha 0 and 1 are represented exactly by source linear interpolation.
        w=np.linspace(4,6,41)
        for alpha in (0,1):
            out=run(wave=w*u.um, flux=7*(w/5)**alpha*u.Jy, alpha=alpha)
            self.assertAlmostEqual(out.coefficient.to_value(u.Jy),7.,places=12)
            self.assertAlmostEqual(out.contribution_weights@(7*(w/5)**alpha),7.,places=12)
        # Curved reference is not piecewise linear; interpolation converges.
        w=np.linspace(4,6,4001)
        for alpha in (-4,4):
            out=run(wave=w*u.um,flux=7*(w/5)**alpha*u.Jy,alpha=alpha)
            self.assertAlmostEqual(out.coefficient.to_value(u.Jy),7.,delta=1e-6)

    def test_reference_and_source_against_independent_quadrature(self):
        w=np.array([4.,4.4,4.9,5.3,5.8,6.]);f=np.array([-.3,.8,2.,1.4,1.8,.9])
        rw=np.array([4.1,4.6,5.4,5.9]);r=np.array([-.01,1.,.8,-.02])
        knots=np.unique(np.r_[w[(w>=rw[0]) & (w<=rw[-1])],rw])
        den=sum(quad(lambda x:np.interp(x,rw,r)/x,a,b,epsabs=1e-13)[0] for a,b in zip(knots[:-1],knots[1:]))
        num=sum(quad(lambda x:np.interp(x,rw,r)*np.interp(x,w,f)/x,a,b,epsabs=1e-13)[0] for a,b in zip(knots[:-1],knots[1:]))
        for alpha in (-4,0,4):
            ref=sum(quad(lambda x:np.interp(x,rw,r)*(x/5)**alpha/x,a,b,epsabs=1e-13)[0] for a,b in zip(knots[:-1],knots[1:]))
            out=run(wave=w*u.um,flux=f*u.Jy,alpha=alpha)
            self.assertAlmostEqual(out.source_mean.value,num/den,places=13)
            self.assertAlmostEqual(out.reference_mean,ref/den,places=13)
            self.assertAlmostEqual(out.coefficient.value,num/ref,places=13)
            self.assertAlmostEqual(out.contribution_weights@f,num/ref,places=13)
            self.assertGreater(out.response_negative_absolute_fraction,0)
            self.assertLessEqual(out.reference_quadrature_relative_difference,1e-12)

    def test_scaling_shift_units_and_provenance(self):
        base=run(local=5.1*u.um,alpha=4.)
        alt=run(local=5100*u.nm, fiducial=5000*u.nm, alpha=4.,
                wave=np.array([4000,4500,5000,5500,6100])*u.nm,
                flux=np.full(5,2000)*u.mJy,
                rwave=np.array([4100,4600,5400,5900])*u.nm,
                response=np.array([-.01,1.,.8,-.02])*1e200*u.one)
        self.assertAlmostEqual(base.coefficient.to_value(u.Jy),alt.coefficient.to_value(u.Jy),places=13)
        np.testing.assert_allclose(base.shifted_response_wavelength.to_value(u.um),[4.2,4.7,5.5,6.0])
        self.assertAlmostEqual(base.shift.to_value(u.nm),100.)
        self.assertEqual(base.reference_provenance,'assumed power law')
        self.assertAlmostEqual(base.reference_alpha,4.)

    def test_missing_tiny_absolute_support_and_nonpositive_source(self):
        with self.assertRaisesRegex(ValueError,'missing absolute'):
            run(wave=np.array([4.,5.5])*u.um,flux=np.ones(2)*u.Jy,
                rwave=np.array([4.,5.4,5.5,5.6])*u.um,
                response=np.array([1.,1.,1e-14,0.])*u.one,gap=2*u.um)
        with self.assertRaisesRegex(ValueError,'missing absolute'):
            run(usable=np.array([True,True,False,True,True]))
        with self.assertRaisesRegex(ValueError,'positive'):
            run(flux=-np.ones(5)*u.Jy)
        self.assertGreater(run(flux=np.array([-1.,2.,2.,2.,-1.])*u.Jy).coefficient.value,0)

    def test_unusable_nan_allowed_only_under_zero_response(self):
        usable=np.array([True,True,True,False,False])
        flux=np.array([2.,2.,2.,np.nan,np.nan])*u.Jy
        out=run(flux=flux,usable=usable,rwave=np.array([4.1,4.5,5.,5.9])*u.um,
                response=np.array([1.,1.,0.,0.])*u.one)
        self.assertAlmostEqual(out.coefficient.value,2.)
        self.assertTrue(np.all(out.contribution_weights[~usable]==0))
        self.assertAlmostEqual(out.contribution_weights[usable]@flux.value[usable],2.)

    def test_reference_rejects_negative_and_unconverged_integrals(self):
        w=np.linspace(4,6,101)
        args={'wave':w*u.um, 'flux':np.ones(len(w))*u.Jy, 'rwave':w*u.um,
              'response':(1-1.05*(w-4))*u.one}
        self.assertAlmostEqual(run(alpha=0,**args).coefficient.value,1.,places=12)
        with self.assertRaisesRegex(ValueError,'reference mean'):
            run(alpha=4,**args)
        # An extremely broad interval can defeat a fixed 8-node rule; do not
        # silently publish its value when the 16-node check disagrees.
        with self.assertRaisesRegex(ValueError,'quadrature did not converge'):
            run(wave=np.array([1.,2.,4.])*u.um,flux=np.ones(3)*u.Jy,
                rwave=np.array([1.,2.,4.])*u.um,response=np.array([1.,1.,-.4])*u.one,
                local=1*u.um,fiducial=1*u.um,gap=3*u.um)

    def test_invalid_inputs_and_numerical_guard(self):
        for kwargs in ({'local':5.}, {'local':-1*u.um}, {'fiducial':5*u.Jy},
                       {'alpha':np.nan},{'alpha':True}, {'gap':0*u.um},
                       {'reference_provenance':''}, {'spectrum_provenance':''},
                       {'response_provenance':''}, {'response':np.ones(4)*u.Jy},
                       {'rwave':np.array([4.1,4.6,4.6,5.9])*u.um},
                       {'local':.1*u.um,'fiducial':10*u.um}, {'alpha':1e308}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):run(**kwargs)


if __name__=='__main__':unittest.main()
