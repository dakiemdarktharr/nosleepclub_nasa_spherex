import unittest

import astropy.units as u
import numpy as np
from scipy.integrate import quad

from scripts.spectral_bandpass import photon_weighted_bandpass


class SpectralBandpassTests(unittest.TestCase):
    def calculate(self, wave, flux, usable=None, rwave=None, response=None, gap=2*u.um, kind='nonnegative_throughput'):
        return photon_weighted_bandpass(
            np.asarray(wave)*u.um, np.asarray(flux)*u.Jy,
            np.ones(len(wave), dtype=bool) if usable is None else usable,
            np.asarray([1., 2.])*u.um if rwave is None else np.asarray(rwave)*u.um,
            np.asarray([1., 1.])*u.one if response is None else np.asarray(response)*u.one,
            maximum_gap=gap, response_kind=kind)

    def test_photon_convention_analytic_linear_and_negative_flux(self):
        # Fnu=lambda-1.5; a flat response has exact analytic integral.
        result = self.calculate([1., 1.25, 1.5, 1.75, 2.], [-.5, -.25, 0., .25, .5])
        self.assertTrue(result.support_complete)
        self.assertAlmostEqual(result.full_band_mean_jy, 1/np.log(2)-1.5, places=10)
        self.assertAlmostEqual(result.supported_part_weights.sum(), 1., places=13)
        scaled = photon_weighted_bandpass(
            np.array([1000,1250,1500,1750,2000])*u.nm,
            np.array([-500,-250,0,250,500])*u.mJy, np.ones(5,dtype=bool),
            np.array([1000,2000])*u.nm, np.array([1,1])*u.one,
            maximum_gap=2000*u.nm, response_kind='nonnegative_throughput')
        self.assertAlmostEqual(result.full_band_mean_jy, scaled.full_band_mean_jy, places=13)

    def test_constant_flux_and_response_scale_invariance(self):
        for scale in (1e-15, 1., 1e15):
            result = self.calculate([1., 1.5, 2.], [3., 3., 3.], rwave=[1.,1.5,2.], response=np.array([0.,2.,0.])*scale)
            self.assertAlmostEqual(result.full_band_mean_jy, 3., places=12)
            self.assertEqual(result.unsupported_absolute_fraction, 0.)

    def test_missing_points_gaps_and_endpoints_never_complete(self):
        result = self.calculate([1.,1.25,1.5,1.75,2.], [3.,3.,np.nan,3.,3.], usable=np.array([1,1,0,1,1],bool))
        self.assertFalse(result.support_complete)
        self.assertIsNone(result.full_band_mean_jy)
        self.assertGreater(result.unsupported_absolute_fraction, .4)
        self.assertAlmostEqual(result.supported_part_mean_jy, 3.)
        self.assertEqual(result.supported_part_weights[2], 0.)
        gap = self.calculate([1.,1.2,1.8,2.], [3.,3.,3.,3.], gap=.25*u.um)
        self.assertFalse(gap.support_complete)
        edge = self.calculate([1.1,1.5,2.], [3.,3.,3.])
        self.assertFalse(edge.support_complete)
        absent = self.calculate([3.,4.], [1.,1.])
        self.assertIsNone(absent.supported_part_mean_jy)
        self.assertTrue(np.array_equal(absent.supported_part_weights, np.zeros(2)))

    def test_signed_response_does_not_clip_or_cancel_missing_support(self):
        result = self.calculate([1.,1.5,2.], [1.,1.,1.], rwave=[.8,1.,1.5,2.,2.2], response=[-.1,0.,1.,0.,.1], kind='signed_laboratory_measurement')
        self.assertGreater(result.negative_response_absolute_fraction, 0.)
        self.assertGreater(result.unsupported_absolute_fraction, 0.)
        self.assertIsNone(result.full_band_mean_jy)
        with self.assertRaisesRegex(ValueError, 'negative'):
            self.calculate([1.,2.], [1.,1.], response=[-.1,1.])
        with self.assertRaisesRegex(ValueError, 'normalization'):
            self.calculate([1.,2.], [1.,1.], response=[-1.,-1.], kind='signed_laboratory_measurement')

    def test_units_axis_mask_and_numerical_validation(self):
        with self.assertRaisesRegex(ValueError, 'units'):
            photon_weighted_bandpass([1.,2.], np.ones(2)*u.Jy, np.ones(2,bool), np.array([1,2])*u.um, np.ones(2)*u.one, maximum_gap=1*u.um, response_kind='nonnegative_throughput')
        for wave in ([1.,1.], [2.,1.], [1.,np.nan]):
            with self.assertRaises(ValueError): self.calculate(wave,[1.,1.])
        with self.assertRaises(ValueError): self.calculate([1.,2.], [np.nan,1.])
        with self.assertRaises(ValueError): self.calculate([1.,2.], [1.,1.], usable=[1,1])
        with self.assertRaises(ValueError): self.calculate([1.,2.], [1.,1.], gap=0*u.um)
        with self.assertRaises(ValueError): self.calculate([1.,2.], [1.,1.], kind='guessed')

    def test_piecewise_integral_against_independent_adaptive_quadrature(self):
        wave=np.array([1.,1.13,1.4,1.7,2.])
        flux=np.array([-2.,.7,1.9,-.4,3.])
        rwave=np.array([1.,1.08,1.43,1.58,1.91,2.])
        response=np.array([.5,-.3,1.,1.2,-.02,.7])
        result=self.calculate(wave,flux,rwave=rwave,response=response,kind='signed_laboratory_measurement')
        def trans(x):return np.interp(x,rwave,response)
        knots=np.sort(np.unique(np.r_[wave,rwave]))
        den=sum(quad(lambda x:trans(x)/x,a,b,epsabs=1e-14)[0] for a,b in zip(knots[:-1],knots[1:]))
        num=sum(quad(lambda x:trans(x)*np.interp(x,wave,flux)/x,a,b,epsabs=1e-14)[0] for a,b in zip(knots[:-1],knots[1:]))
        self.assertAlmostEqual(result.full_band_mean_jy,num/den,places=12)
        self.assertAlmostEqual(result.full_signed_weight,den,places=12)
        self.assertAlmostEqual(result.supported_part_weights@flux,num/den,places=12)

    def test_small_interval_and_refining_linear_knots(self):
        # Independently integrate a narrow, nonconstant response using a
        # well-scaled dimensionless coordinate, avoiding subtraction of close λ.
        a=4.7;h=1e-10;b=a+h;h=b-a
        result=self.calculate([a,b],[-1.,2.],rwave=[a,b],response=[.2,2.],gap=1*u.um)
        num=quad(lambda t:(-1+3*t)*(.2+1.8*t)/(a+h*t),0,1,epsabs=1e-14)[0]
        den=quad(lambda t:(.2+1.8*t)/(a+h*t),0,1,epsabs=1e-14)[0]
        self.assertAlmostEqual(result.full_band_mean_jy,num/den,places=12)
        coarse=self.calculate([1.,2.],[2.,5.],rwave=[1.,2.],response=[.1,.8])
        refined=self.calculate([1.,1.25,1.7,2.],[2.,2.75,4.1,5.],rwave=[1.,1.3,2.],response=[.1,.31,.8])
        self.assertAlmostEqual(coarse.full_band_mean_jy,refined.full_band_mean_jy,places=13)
        self.assertAlmostEqual(coarse.full_signed_weight,refined.full_signed_weight,places=13)

    def test_tiny_missing_weight_and_masked_zero_response(self):
        result=self.calculate([1.,1.6],[2.,2.],rwave=[1.,1.5,1.6,1.7],response=[1.,1.,1e-14,0.])
        self.assertGreater(result.unsupported_absolute_weight,0.)
        self.assertLess(result.unsupported_absolute_fraction,1e-12)
        self.assertFalse(result.support_complete)
        self.assertIsNone(result.full_band_mean_jy)
        result=self.calculate([1.,1.5,2.],[2.,2.,np.nan],usable=np.array([True,True,False]),
                              rwave=[1.,1.5,2.],response=[1.,0.,0.])
        self.assertTrue(result.support_complete)
        self.assertAlmostEqual(result.full_band_mean_jy,2.)
        self.assertEqual(result.supported_part_weights[2],0.)

    def test_extreme_response_and_strict_input_order(self):
        result=self.calculate([1.,1.5,2.],[1.,1.,1.],rwave=[1.,1.25,2.],
                              response=[-1e308,1e308,1e308],kind='signed_laboratory_measurement')
        self.assertTrue(result.support_complete)
        self.assertAlmostEqual(result.full_band_mean_jy,1.,places=12)
        self.assertGreater(result.negative_response_absolute_fraction,0.)
        with self.assertRaises(ValueError):
            self.calculate([1.,1.5,2.],[1.,1.,1.],rwave=[1.,1.5,2.],response=[1e-300,1e308,1e308])
        with self.assertRaises(ValueError):self.calculate([1.,2.,1.5],[1.,1.,1.])


if __name__ == '__main__':
    unittest.main()
