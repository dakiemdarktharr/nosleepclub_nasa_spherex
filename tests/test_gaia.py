"""Gaia propagation, frame calibration, and published validation evidence."""
from hashlib import sha256
import json
from pathlib import Path
import unittest

from astropy.io import fits
from astropy.time import Time
import numpy as np

from scripts import gaia_motion as gaia

ROOT=Path(__file__).resolve().parents[1]


def source():
    s={'ra':gaia.base.CENTER[0],'dec':gaia.base.CENTER[1],'ref_epoch':2016.,
       'parallax':0.,'pmra':100.,'pmdec':-40.,'ruwe':1.,'visibility_periods_used':12,
       'astrometric_params_solved':31,'duplicated_source':False,'non_single_star':0,'ipd_frac_multi_peak':0}
    for key in gaia.PARAMETERS:s[key+'_error']=1.
    for i,j in gaia.PAIRS:s[f'{gaia.PARAMETERS[i]}_{gaia.PARAMETERS[j]}_corr']=0.
    return s


def registration_fixture(model='translation'):
    frame={'record':{'obs_id':'test'}};refs=[]
    parameters=np.array([.12,-.08] if model=='translation' else [.12,-.08,.02,-.01,.03,.04])
    for i,p in enumerate([[0,0],[20,90],[60,10],[110,100],[-40,60],[70,-30],[40,45]]):
        h=gaia.design_at(p,model)
        refs.append({'catalog':{'source_id':str(i)},'entries':[{'obs_id':'test','rejection':None,
                     'expected_px':p,'delta_px':(h@parameters).tolist(),
                     'covariance_px2':[[.01,.002],[.002,.02]],'gaia_covariance_px2':[[1e-8,0],[0,1e-8]]}]})
    return frame,refs,parameters


class GaiaNumerics(unittest.TestCase):
    def test_proper_motion_is_propagated_with_cos_declination(self):
        s=source();mjd=float(Time(2026.,format='jyear',scale='tcb').utc.mjd)
        x,y=gaia.gaia_xy(s,mjd)
        # 1 arcsec east and 0.4 arcsec south in ten Julian years.
        np.testing.assert_allclose([x-31.5,y-31.5],[-1/6.15,-.4/6.15],atol=2e-7)

    def test_shared_catalog_position_error_cancels_between_epochs(self):
        s=source();s['pmra']=s['pmdec']=0.
        ja=gaia.gaia_jacobian(s,60990.);jb=gaia.gaia_jacobian(s,61154.)
        covariance=np.diag([100.,100.,0.,0.,0.])
        paired=(jb-ja)@covariance@(jb-ja).T
        independent=ja@covariance@ja.T+jb@covariance@jb.T
        self.assertLess(np.trace(paired),1e-12)
        self.assertGreater(np.trace(independent),1e-6)

    def test_gaia_covariance_retains_correlations(self):
        s=source();s['ra_pmra_corr']=.4
        cov=gaia.gaia_covariance(s)
        self.assertEqual(cov[0,3],.4);np.testing.assert_allclose(cov,cov.T)
        self.assertTrue(np.all(np.linalg.eigvalsh(cov)>0))

    def test_translation_solver_and_leave_one_out_recover_known_offset(self):
        frame,refs,truth=registration_fixture()
        for subset in [refs,*[refs[:i]+refs[i+1:] for i in range(len(refs))]]:
            fit=gaia.fit_registration(frame,subset)
            np.testing.assert_allclose(fit['offset'],truth,atol=1e-12)

    def test_affine_solver_recovers_known_field_gradient(self):
        frame,refs,truth=registration_fixture('affine')
        fit=gaia.fit_registration(frame,refs,'affine')
        np.testing.assert_allclose(fit['parameters'],truth,atol=1e-12)
        np.testing.assert_allclose(fit['offset'],truth[:2],atol=1e-12)

    def test_insufficient_references_are_reported(self):
        frame,refs,_=registration_fixture()
        with self.assertRaises(RuntimeError):gaia.fit_registration(frame,refs[:3])

    def test_covariance_envelope_never_reduces_formal_errors(self):
        formal=np.array([[2.,.2],[.2,1.]])
        empirical=np.array([[1.,.1],[.1,3.]])
        used=gaia.positive_envelope(formal,empirical)
        self.assertTrue(np.all(np.linalg.eigvalsh(used-formal)>-1e-10))
        self.assertTrue(np.all(np.linalg.eigvalsh(used-empirical)>-1e-10))

    def test_bad_astrometric_quality_is_not_accepted(self):
        s=source();self.assertIsNone(gaia.catalog_quality(s))
        s['ruwe']=2.;self.assertEqual(gaia.catalog_quality(s),'ruwe')
        s['ruwe']=1.;s['duplicated_source']=True
        self.assertEqual(gaia.catalog_quality(s),'catalog_flag')


class GaiaProducts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results=json.loads((ROOT/'web/data/gaia/results.json').read_text(encoding='utf-8'))
        cls.manifest=json.loads((ROOT/'web/data/manifest.json').read_text(encoding='utf-8'))

    def test_reproducible_source_and_input_hashes(self):
        r=self.results
        for name,digest in r['source_sha256'].items():
            self.assertEqual(sha256((ROOT/'scripts'/name).read_bytes()).hexdigest(),digest)
        digest=sha256(json.dumps(r['source_sha256'],sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest,r['analysis_sha256']);self.assertEqual(digest,self.manifest['analysis_sha256'])
        catalog=ROOT/r['gaia_catalog']['path']
        if catalog.exists():self.assertEqual(sha256(catalog.read_bytes()).hexdigest(),r['gaia_catalog']['sha256'])

    def test_reference_split_and_catalog_ids_are_preserved(self):
        refs=self.results['references']
        train={r['catalog']['source_id'] for r in refs if r['split']=='training'}
        held={r['catalog']['source_id'] for r in refs if r['split']=='heldout'}
        self.assertFalse(train&held);self.assertEqual(len(train)+len(held),self.results['selected_count'])
        self.assertGreaterEqual(len(held),5)
        self.assertTrue(all(isinstance(s,str) and s.isdigit() for s in train|held))
        for c in self.results['configurations']:
            self.assertEqual(set(c['training_source_ids']),train)
            self.assertEqual(set(c['heldout_source_ids']),held)
            self.assertTrue({r['id'] for r in c['heldout_controls']}<=held)

    def test_gaia_fits_headers_identify_the_analysis_and_reference_catalog(self):
        for scene in self.manifest['scenes']:
            if not scene.get('motion',{}).get('gaia_reference'):continue
            with fits.open(ROOT/'web'/scene['fits']) as h:
                self.assertEqual(h[0].header['ANAVERS'],'0.3.0')
                self.assertEqual(h[0].header['ASTREF'],'Gaia DR3')
                self.assertEqual(h[0].header['ANAHASH'],self.results['analysis_sha256'])
                self.assertEqual(h[0].header['GACATHSH'],self.results['gaia_catalog']['sha256'])

    def test_error_budget_closes_and_numerical_response_has_correct_sign(self):
        for c in self.results['configurations']:
            cov=sum(np.array(c[k]) for k in ['statistical_covariance_px2','registration_covariance_px2','holdout_covariance_px2'])
            arc=gaia.TRANSFORM@cov@gaia.TRANSFORM
            np.testing.assert_allclose(arc,c['covariance_arcsec2'])
            self.assertTrue(np.all(np.linalg.eigvalsh(arc)>0))
            for key in ['response_sum_before','response_sum_after']:
                np.testing.assert_allclose(c['calibration_bootstrap'][key],-np.eye(2),atol=.04)

    def test_cross_validation_and_injections_report_every_attempt(self):
        for c in self.results['configurations']:
            self.assertTrue(c['reference_swap']['success']);self.assertTrue(c['affine_sensitivity']['success'])
            self.assertEqual(len(c['leave_one_out']),len(c['training_source_ids']))
            self.assertTrue(all(v['success'] for v in c['leave_one_out']))
            injection=c['injection_diagnostics'];self.assertEqual(len(injection['records']),32)
            self.assertEqual(sum(g['attempted'] for g in injection['groups']),32)
            self.assertIn('not completeness',injection['note'])
            self.assertEqual(c['status'],'candidate_motion_unconfirmed')


if __name__=='__main__':unittest.main()
