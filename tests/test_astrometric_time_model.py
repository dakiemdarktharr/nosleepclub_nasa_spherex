import unittest
import json
import hashlib
from pathlib import Path
import numpy as np
from astropy.time import Time
from astropy.io.fits import Header
from scripts import astrometric_time_model as astro


def header():
    return {'EXTNAME':'IMAGE','TIMESYS':'UTC','MJD-BEG':60989.296807454,
            'MJD-AVG':60989.297473643,'MJD-END':60989.298139832,'MJDREF':0.,
            'X_SC':-5176.678341946553,'Y_SC':4749.4097044227965,'Z_SC':426.981030022882,'XYZ_SC_SYSTEM':'GEOCENTER'}


def t(mjd):return Time(mjd,format='mjd',scale='utc')


class AstrometricTimeModelTests(unittest.TestCase):
    def test_header_scales_absolute_semantics_and_consistency(self):
        h=header();result=astro.parse_image_header(h)
        self.assertEqual(result.input_scale,'utc');self.assertAlmostEqual(result.midpoint.mjd,h['MJD-AVG'])
        self.assertGreater(result.midpoint.tdb.mjd-result.midpoint.mjd,0.)
        # MJDREF never gets added to absolute MJD-BEG/AVG/END.
        self.assertEqual(astro.parse_image_header({**h,'MJDREF':60000.}).midpoint.mjd,result.midpoint.mjd)
        for mutation in [{'TIMESYS':None},{'TIMESYS':'GPS'},{'TIMESYS':'LOCAL'}, {'MJD-AVG':None},
                         {'MJD-AVG':'60989.297'}, {'MJD-AVG':1.},{'MJD-AVG':60989.299},
                         {'MJD-AVG':60989.2979}, {'TIMEZERO':3.}, {'MJDREF':float('nan')},
                         {'MJDREFI':60000.}, {'TREFPOS':'BARYCENTER'}, {'EXTNAME':'PRIMARY'}]:
            with self.subTest(mutation=mutation),self.assertRaises(astro.TimeMetadataError):astro.parse_image_header({**h,**mutation})
        hh=Header()
        for k,v in h.items():
            if k!='XYZ_SC_SYSTEM':hh[k]=v
        hh.append(('MJD-AVG',h['MJD-AVG']))
        with self.assertRaises(astro.TimeMetadataError):astro.parse_image_header(hh)
        for scale in ['UTC','TAI','TT','TDB','TCB','TCG']:
            self.assertEqual(astro.parse_image_header({**h,'TIMESYS':scale}).input_scale,scale.lower())
        with self.assertRaises(astro.TimeMetadataError):astro.parse_image_header({**h,'DATE-AVG':'2025-01-01T00:00:00'})

    def test_parallax_sign_ra_wrap_high_declination(self):
        earth=np.array([[0.,1.,0.],[1.,0.,0.],[0.,0.,1.]])
        np.testing.assert_allclose(astro.parallax_factors(0.,0.,earth),[[-1.,0.],[0.,0.],[0.,-1.]],atol=1e-14)
        a=astro.parallax_factors(359.999,89.9,earth);b=astro.parallax_factors(-.001,89.9,earth)
        np.testing.assert_allclose(a,b,atol=1e-14)
        east,north=astro.tangent_basis(180.,89.99999)
        np.testing.assert_allclose([east@east,north@north,east@north],[1,1,0],atol=1e-12)
        self.assertTrue(np.isfinite(a).all())

    def test_exact_recovery_and_withheld_epoch_cross_covariance(self):
        times=[t(v) for v in [59000,59100,59250,59420,59560,59700,59840,59980]]
        ref=t(59400);a,meta=astro.design_matrix(times,ref,359.9,70.,'pm_parallax')
        expected=np.array([.2,-.3,.7,-.1,.42]);y=a@expected
        C=np.eye(len(y))*.04;C+=np.kron(np.ones((len(times),len(times))),np.array([[.01,.004],[.004,.02]]))
        fit=astro.fit_gls(a,y,C);np.testing.assert_allclose(fit['parameters'],expected,atol=1e-10)
        self.assertEqual(meta['ephemeris'],'builtin');self.assertEqual(meta['fit_time_scale'],'tdb')
        test,_=astro.design_matrix([t(60100)],ref,359.9,70.,'pm_parallax')
        future=np.array([[.07,.004],[.004,.08]])
        cross=np.tile(np.array([[.01,.004],[.004,.02]]),(len(times),1))
        result=astro.predict(fit,test,future,cross)
        np.testing.assert_allclose(result['mean'],test@expected,atol=1e-10)
        term=test@fit['gain']@cross
        np.testing.assert_allclose(result['prediction_residual_covariance'],future+test@fit['parameter_covariance']@test.T-term-term.T,atol=1e-12)
        diagfit=astro.fit_gls(a,y,np.diag(np.diag(C)))
        self.assertGreater(np.linalg.norm(fit['parameter_covariance']-diagfit['parameter_covariance']),1e-4)
        with self.assertRaises(ValueError):astro.predict(fit,test,train_new_covariance=cross)
        with self.assertRaises(ValueError):astro.predict(fit,test,future,np.ones_like(cross)*100)

    def test_rank_dof_and_poor_condition_refusal(self):
        times=[t(59000)]*5;ref=t(58900)
        for mode in ['pm_only','pm_parallax']:
            a,_=astro.design_matrix(times,ref,120.,-20.,mode)
            with self.assertRaises(astro.UnidentifiableDesign):astro.fit_gls(a,np.zeros(len(a)),np.eye(len(a)))
        a,_=astro.design_matrix([t(59000),t(59100)],ref,120.,-20.,'pm_only')
        with self.assertRaises(astro.UnidentifiableDesign) as caught:astro.fit_gls(a,np.zeros(4),np.eye(4))
        self.assertEqual(caught.exception.reason,'zero_or_negative_degrees_of_freedom')
        a,_=astro.design_matrix([t(59000+i*.05) for i in range(10)],ref,120.,-20.,'pm_parallax')
        with self.assertRaises(astro.UnidentifiableDesign) as caught:astro.fit_gls(a,np.zeros(20),np.eye(20))
        self.assertIn(caught.exception.reason,['ill_conditioned','rank_deficient'])
        with self.assertRaises(ValueError):astro.fit_gls(a,np.zeros(20),np.diag([1.]*19+[-1.]))

    def test_explicit_proper_motion_only_recovery(self):
        times=[t(59000),t(59100),t(59200),t(59350),t(59500)]
        a,meta=astro.design_matrix(times,t(59200),15.,-45.,'pm_only')
        truth=np.array([.4,-.2,.7,.1]);fit=astro.fit_gls(a,a@truth,np.eye(10)*.09)
        self.assertEqual(len(fit['parameters']),4);self.assertNotIn('parallax_arcsec',meta['parameters'])
        np.testing.assert_allclose(fit['parameters'],truth,atol=1e-12)
        self.assertEqual(fit['dof'],6)

    def test_covariance_validation_is_relative_at_small_and_large_scales(self):
        times=[t(v) for v in [59000,59100,59200,59300,59400]]
        a,_=astro.design_matrix(times,t(59200),15.,-45.,'pm_only')
        for scale in [1e-14,1e14]:
            with self.subTest(scale=scale):
                covariance=np.eye(10)*scale
                invalid=covariance.copy();invalid[0,1]=.2*scale;invalid[1,0]=.1*scale
                with self.assertRaisesRegex(ValueError,'symmetric'):astro.fit_gls(a,np.zeros(10),invalid)
                np.testing.assert_allclose(astro.fit_gls(a,np.zeros(10),covariance)['parameters'],np.zeros(4),atol=1e-20)
                with self.assertRaises(ValueError):astro.fit_gls(a,np.zeros(10),np.zeros((10,10)))
                bad=covariance.copy();bad[0,0]=np.nan
                with self.assertRaises(ValueError):astro.fit_gls(a,np.zeros(10),bad)

    def test_cross_covariance_psd_relative_and_perfect_correlation(self):
        for scale in [1e-14,1e14]:
            with self.subTest(scale=scale):
                c=np.array([[2.,.3],[.3,1.]])*scale
                fit={'parameters':np.zeros(2),'parameter_covariance':c,
                     'training_covariance':c,'gain':np.eye(2)}
                # Same measurements in train and future: joint covariance is
                # singular PSD and the residual is identically zero.
                good=astro.predict(fit,np.eye(2),c,c)
                residual=good['prediction_residual_covariance']
                self.assertGreaterEqual(np.linalg.eigvalsh(residual/scale).min(),0.)
                np.testing.assert_allclose(residual,np.zeros((2,2)),rtol=0,atol=1e-12*scale)
                self.assertGreaterEqual(good['prediction_residual_psd_roundoff_adjustment_arcsec2'],0.)
                with self.assertRaisesRegex(ValueError,'joint train/new covariance'):
                    astro.predict(fit,np.eye(2),c,c*1.001)
                asymmetric=c.copy();asymmetric[0,1]+=.05*scale
                with self.assertRaisesRegex(ValueError,'symmetric'):
                    astro.predict(fit,np.eye(2),asymmetric,c)
                with self.assertRaises(ValueError):astro.predict(fit,np.eye(2),np.zeros((2,2)),c)
                nonfinite=c.copy();nonfinite[0,0]=np.nan
                with self.assertRaises(ValueError):astro.predict(fit,np.eye(2),c,nonfinite)
                # Only a residual eigenvalue within cancellation roundoff may
                # receive a recorded correction; the joint covariance is PSD.
                roundoff={**fit,'parameter_covariance':c*(1-1e-15)}
                stabilized=astro.predict(roundoff,np.eye(2),c,c)
                self.assertGreater(stabilized['prediction_residual_psd_roundoff_adjustment_arcsec2'],0.)
                self.assertLessEqual(stabilized['prediction_residual_psd_roundoff_adjustment_arcsec2'],
                                     2*stabilized['prediction_residual_psd_tolerance_arcsec2'])
                self.assertGreaterEqual(np.linalg.eigvalsh(stabilized['prediction_residual_covariance']/scale).min(),0.)
                # Even with valid joint covariance, inconsistent parameter
                # covariance must not result in a negative residual matrix.
                inconsistent={**fit,'parameter_covariance':c*.5}
                with self.assertRaisesRegex(ValueError,'prediction residual covariance'):
                    astro.predict(inconsistent,np.eye(2),c,c)

    def test_spacecraft_bound_uses_only_norm_not_axes(self):
        h=header();v=astro.spacecraft_parallax_bound(h,.454)
        self.assertTrue(v['available']);self.assertGreater(v['bound_arcsec'],0)
        changed={**h,'X_SC':h['Z_SC'],'Y_SC':-h['X_SC'],'Z_SC':h['Y_SC']}
        self.assertAlmostEqual(v['bound_arcsec'],astro.spacecraft_parallax_bound(changed,.454)['bound_arcsec'],places=15)
        self.assertFalse(astro.spacecraft_parallax_bound({**h,'XYZ_SC_SYSTEM':'UNKNOWN'},.454)['available'])
        self.assertFalse(astro.spacecraft_parallax_bound({**h,'X_SC':None},.454)['available'])
        with self.assertRaises(ValueError):astro.spacecraft_parallax_bound(h,-.1)
        # Neither the sign nor orientation of header XYZ enters Earth-only design.
        x,_=astro.design_matrix([astro.parse_image_header(h).midpoint],t(60989.),20.,-30.,'pm_parallax')
        y,_=astro.design_matrix([astro.parse_image_header(changed).midpoint],t(60989.),20.,-30.,'pm_parallax')
        np.testing.assert_array_equal(x,y)

    def test_cached_development_audit_provenance_and_rank(self):
        root=Path(__file__).resolve().parents[1]
        path=root/'web/data/time-model/development-audit.json'
        if not path.exists():self.skipTest('Optional audit not available')
        audit=json.loads(path.read_text(encoding='utf-8'))
        for name,value in audit['source_hashes'].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),value)
        self.assertEqual(audit['attempted_exposures'],len(audit['exposures']))
        self.assertEqual(audit['valid_exposures'],sum('time' in r for r in audit['exposures']))
        self.assertEqual(audit['collapsed_two_season_design_identity_weights']['pm_parallax']['reason'],'rank_deficient')
        self.assertNotIn('parameters',audit)
        for r in audit['exposures']:
            if 'time' in r:
                tm=r['time'];self.assertLess(tm['start_mjd_absolute'],tm['midpoint_mjd_absolute'])
                self.assertLess(tm['midpoint_mjd_absolute'],tm['end_mjd_absolute'])
                self.assertEqual(tm['input_scale'],'utc')
                self.assertEqual(r['spacecraft_parallax_bound']['assumed_parallax_arcsec'],.454)


if __name__=='__main__':unittest.main()
