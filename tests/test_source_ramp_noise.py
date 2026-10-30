import unittest
import numpy as np
import astropy.units as u
from astropy.io.fits import Header
from scripts import source_ramp_noise as ramp


def header(n,dt=1.5349):
    return {'SURLIM':n+2,'SURDLY':3,'TSAMP':dt,'XPOSURE':(n-1)*dt}


def injection(source,gain,h,mask,rng,**kwargs):
    return ramp.inject_source_ramp(source,gain,h,mask,rng,gain_provenance={'source':'synthetic calibration'},**kwargs)


class SourceRampNoiseTests(unittest.TestCase):
    def test_exact_ols_variance_from_sample_covariance(self):
        for n in [2,3,75]:
            dt=1.5349;s=2.7
            times=np.arange(n)*dt;centered=times-times.mean()
            ols=centered/(centered@centered)
            sample_cov=s*dt*np.minimum.outer(np.arange(n),np.arange(n))
            exact=float(ols@sample_cov@ols)
            formula=ramp.poisson_factor(n)*s/(n*dt)
            self.assertAlmostEqual(exact,formula,places=13)
            weights=ramp.increment_weights(n,dt)
            self.assertAlmostEqual(weights.sum()*dt,1.,places=13)
            self.assertAlmostEqual(s*dt*float(weights@weights),formula,places=13)
            self.assertTrue(np.all(weights>0))
        self.assertAlmostEqual(ramp.poisson_factor(2),2.)
        self.assertAlmostEqual(ramp.poisson_factor(3),1.5)

    def test_n2_is_poisson_not_gaussian_and_zero_source(self):
        source=np.full((1,500),2.)*ramp.SOURCE_UNIT;gain=1.*ramp.GAIN_UNIT
        result=injection(source,gain,header(2,1.),np.ones(source.shape,bool),np.random.default_rng(4))
        np.testing.assert_allclose(result['added_image'].value,np.rint(result['added_image'].value),atol=1e-12)
        self.assertTrue(np.all(result['added_image'].value>=0))
        np.testing.assert_allclose(result['added_variance'].value,2.)
        zero=injection(np.zeros((2,3))*ramp.SOURCE_UNIT,gain,header(75),np.ones((2,3),bool),np.random.default_rng(4))
        np.testing.assert_array_equal(zero['added_image'].value,np.zeros((2,3)))
        np.testing.assert_array_equal(zero['added_variance'].value,np.zeros((2,3)))

    def test_empirical_mean_and_variance_multiple_rates(self):
        samples=25000;dt=1.25;gain=.9
        for index,(n,rate) in enumerate([(2,.02),(3,3.),(75,30.)]):
            with self.subTest(n=n,rate=rate):
                source=np.full((1,samples),rate*gain)*ramp.SOURCE_UNIT
                out=injection(source,gain*ramp.GAIN_UNIT,header(n,dt),np.ones(source.shape,bool),np.random.default_rng(20261030+index),batch_pixels=2048)
                noise=out['source_noise'].to_value(ramp.SOURCE_UNIT).ravel();weights=ramp.increment_weights(n,dt)
                lam=rate*dt;variance=gain**2*lam*np.sum(weights**2);k4=gain**4*lam*np.sum(weights**4)
                self.assertLess(abs(noise.mean()),6*np.sqrt(variance/samples))
                self.assertLess(abs(noise.var(ddof=1)-variance),6*np.sqrt((k4+2*variance**2)/(samples-1)))
                np.testing.assert_allclose(out['added_variance'].value,variance,rtol=1e-12)

    def test_independent_pixels_have_zero_cross_covariance(self):
        samples=20000
        image=np.tile([1.,4.],(samples,1))*ramp.SOURCE_UNIT
        result=injection(image,1.*ramp.GAIN_UNIT,header(3,1.),np.ones(image.shape,bool),np.random.default_rng(97))
        noise=result['source_noise'].value
        covariance=np.cov(noise,rowvar=False)
        sigma=np.sqrt(covariance[0,0]*covariance[1,1]/samples)
        self.assertLess(abs(covariance[0,1]),6*sigma)

    def test_units_scaling_masks_determinism_and_no_mutation(self):
        source=np.array([[2.,3.],[np.nan,-2.]])*ramp.SOURCE_UNIT
        gain=np.array([[.5,1.5],[np.nan,-1.]])*ramp.GAIN_UNIT
        mask=np.array([[True,True],[False,False]])
        a=injection(source,gain,header(3),mask,np.random.default_rng(42),batch_pixels=1,source_provenance={'model':'synthetic'})
        b=injection(source,gain,header(3),mask,np.random.default_rng(42),batch_pixels=1,source_provenance={'model':'synthetic'})
        np.testing.assert_array_equal(a['source_noise'].value,b['source_noise'].value)
        np.testing.assert_array_equal(a['valid_mask'],mask);self.assertTrue(np.isnan(a['added_variance'].value[~mask]).all())
        np.testing.assert_allclose(a['added_image'].value[mask],source.value[mask]+a['source_noise'].value[mask])
        np.testing.assert_allclose(a['added_variance'].value[mask],ramp.poisson_factor(3)*gain.value[mask]*source.value[mask]/(3*1.5349))
        self.assertEqual(a['added_variance'].unit,ramp.SOURCE_UNIT**2)
        self.assertEqual(a['provenance']['valid_pixels'],2);self.assertEqual(a['provenance']['source_provenance']['model'],'synthetic')
        self.assertEqual(a['provenance']['header']['n'],3)
        original=np.array([[10.,20.],[30.,40.]])*ramp.SOURCE_UNIT
        old_variance=np.full((2,2),7.)*ramp.SOURCE_UNIT**2
        combined=np.where(mask,original.value+a['added_image'].value,original.value)
        combined_variance=np.where(mask,old_variance.value+a['added_variance'].value,old_variance.value)
        np.testing.assert_array_equal(original.value,[[10.,20.],[30.,40.]])
        np.testing.assert_array_equal(old_variance.value,np.full((2,2),7.))
        np.testing.assert_array_equal(combined[~mask],original.value[~mask]);np.testing.assert_array_equal(combined_variance[~mask],old_variance.value[~mask])
        # Scaling flux and gain together keeps rates fixed, so identical counts
        # scale the intensity noise by k and source variance by k².
        c=injection(source*3,gain*3,header(3),mask,np.random.default_rng(42),batch_pixels=1)
        np.testing.assert_allclose(c['source_noise'].value[mask],3*a['source_noise'].value[mask])
        np.testing.assert_allclose(c['added_variance'].value[mask],9*a['added_variance'].value[mask])

    def test_strict_header_and_invalid_inputs(self):
        s=np.ones((1,2))*ramp.SOURCE_UNIT;g=np.ones((1,2))*ramp.GAIN_UNIT;mask=np.ones((1,2),bool);h=header(3)
        def run(source=s,gain=g,header_value=h,valid=mask,rng=None,**kwargs):
            return injection(source,gain,header_value,valid,np.random.default_rng(2) if rng is None else rng,**kwargs)
        for values in [{'SURLIM':3.},{'SURLIM':True},{'SURDLY':0},{'SURLIM':2}, {'TSAMP':0.},
                       {'TSAMP':float('inf')},{'TSAMP':'1.5'},{'XPOSURE':99.},{'XPOSURE':float('nan')}]:
            with self.subTest(values=values),self.assertRaises(ValueError):run(header_value={**h,**values})
        with self.assertRaisesRegex(ValueError,'missing or duplicate'):run(header_value={k:v for k,v in h.items() if k!='XPOSURE'})
        with self.assertRaisesRegex(ValueError,'duplicate'):run(header_value={**h,'surlim':h['SURLIM']})
        hh=Header()
        for k,v in h.items():hh[k]=v
        hh.append(('TSAMP',h['TSAMP']))
        with self.assertRaisesRegex(ValueError,'duplicate'):run(header_value=hh)
        for bad in [np.array([[1.,-1.]])*ramp.SOURCE_UNIT,np.array([[1.,np.nan]])*ramp.SOURCE_UNIT]:
            with self.assertRaises(ValueError):run(source=bad)
        with self.assertRaises(ValueError):run(source=np.array([[1+2j,1+0j]])*ramp.SOURCE_UNIT)
        for bad in [np.array([[1.,0.]])*ramp.GAIN_UNIT,np.array([[1.,np.nan]])*ramp.GAIN_UNIT,
                    np.array([1.,2.])*ramp.GAIN_UNIT,1.*u.s]:
            with self.assertRaises(ValueError):run(gain=bad)
        with self.assertRaises(ValueError):run(source=np.ones((1,2)))
        with self.assertRaises(ValueError):run(valid=np.ones((1,2),int))
        with self.assertRaises(ValueError):run(rng=np.random.RandomState(1))
        with self.assertRaises(ValueError):run(batch_pixels=0)
        with self.assertRaises(ValueError):ramp.inject_source_ramp(s,g,h,mask,np.random.default_rng(1),gain_provenance={})


if __name__=='__main__':unittest.main()
