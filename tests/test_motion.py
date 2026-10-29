"""Independent numerical controls for coadd noise and native-pixel astrometry."""
import json
from hashlib import sha256
from pathlib import Path
import unittest

from astropy.wcs import WCS
import numpy as np

from scripts import motion_analysis as motion

ROOT=Path(__file__).resolve().parents[1]


def synthetic_frame(offset=(0.,0.),variance=.0025):
    yy,xx=np.indices((33,33))
    epsf=np.exp(-((xx-16)**2+(yy-16)**2)/(2*4.2**2))
    table=np.zeros(1,dtype=[('XCENTER','f8'),('YCENTER','f8'),('EPSF','f8',(33,33))])
    table['XCENTER']=32.;table['YCENTER']=32.;table['EPSF'][0]=epsf
    parent=WCS(naxis=2);parent.wcs.crpix=[1,1];parent.wcs.crval=[0,0];parent.wcs.cdelt=[1,1]
    return {'data':np.zeros((64,64)),'variance':np.full((64,64),variance),'valid':np.ones((64,64),bool),
            'wcs':motion.base.grid_wcs(),'parent_wcs':parent,'epsf_table':table,'epsf_oversampling':5.,
            'offset':np.array(offset),'offset_cov':np.zeros((2,2)),
            'cwave_map':np.full((64,64),4.7),'cband_map':np.full((64,64),.05),
            'record':{'obs_id':'synthetic'},'mjd':61000.}


class NativeControls(unittest.TestCase):
    def test_centroids_recover_known_motion_with_different_wcs_offsets(self):
        anchor=np.array([31.5,31.5]);delta=np.array([.6,-.12]);fits=[]
        for position,offset in [(anchor,(.23,-.17)),(anchor+delta,(-.31,.12))]:
            frame=synthetic_frame(offset)
            yy,xx=np.indices(frame['data'].shape)
            frame['data']=motion.render_source(frame,position,8.)+.01*xx-.02*yy+2.
            result=motion.fit_position([frame],anchor,multistart=True)
            self.assertTrue(result['success']);self.assertFalse(result['at_boundary'])
            np.testing.assert_allclose(result['position'],position,atol=2e-4)
            self.assertTrue(np.all(np.linalg.eigvalsh(result['covariance'])>0))
            fits.append(result['position'])
        np.testing.assert_allclose(fits[1]-fits[0],delta,atol=3e-4)

    def test_stationary_centroid_is_stable_under_subpixel_sampling(self):
        anchor=np.array([31.72,31.39]);positions=[]
        for offset in [(0.,0.),(.4,-.35)]:
            frame=synthetic_frame(offset)
            frame['data']=motion.render_source(frame,anchor,4.)
            positions.append(motion.fit_position([frame],np.array([31.5,31.5]))['position'])
        np.testing.assert_allclose(positions[1]-positions[0],[0,0],atol=2e-4)

    def test_adjoint_aperture_noise_matches_monte_carlo(self):
        frames=[synthetic_frame((.3,-.2),1.),synthetic_frame((-.25,.4),2.)]
        stack=motion.coadd(frames,np.array([.4,.6]));rng=np.random.default_rng(1107)
        snrs=[]
        for _ in range(240):
            image=sum(g*(p@(rng.normal(size=f['data'].size)*np.sqrt(f['variance'].ravel())))
                      for f,p,g in zip(frames,stack['operators'],stack['coefficients']))
            trial={**stack,'image':image.reshape((64,64))}
            snrs.append(motion.aperture_snr(trial,np.array([31.5,31.5]))['snr'])
        self.assertLess(abs(np.mean(snrs)),.2)
        self.assertAlmostEqual(np.std(snrs,ddof=1),1.,delta=.15)

    def test_aperture_cancels_linear_background_with_asymmetric_missing_pixels(self):
        frame=synthetic_frame();yy,xx=np.indices((64,64))
        frame['data']=2.+.1*xx+.2*yy;frame['valid'][31,32]=False
        stack=motion.coadd([frame],np.array([1.]))
        result=motion.aperture_snr(stack,np.array([31.5,31.5]))
        self.assertLess(result['coverage'],1.);self.assertAlmostEqual(result['signal'],0.,places=7)

    def test_external_prediction_has_zero_shift_at_equal_times(self):
        p=motion.expected_motion(61000.,61000.)
        np.testing.assert_allclose([p['east_arcsec'],p['north_arcsec']],[0,0],atol=1e-12)


class MotionProducts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results=json.loads((ROOT/'web/data/motion/results.json').read_text(encoding='utf-8'))
        cls.manifest=json.loads((ROOT/'web/data/manifest.json').read_text(encoding='utf-8'))

    def test_provenance_matches_analysis_code_and_calibrations(self):
        source=Path(motion.__file__).read_bytes()
        self.assertEqual(self.results['analysis_sha256'],sha256(source).hexdigest())
        self.assertEqual(self.manifest.get('coadd_analysis_sha256',self.manifest['analysis_sha256']),sha256(source+Path(motion.base.__file__).read_bytes()).hexdigest())
        for record in self.results['calibrations'].values():
            path=ROOT/record['path']
            if path.exists():self.assertEqual(sha256(path.read_bytes()).hexdigest(),record['sha256'])

    def test_pairs_are_unique_spectrally_gated_and_have_common_weights(self):
        self.assertEqual({c['id'] for c in self.results['configurations']},{'strict','broad'})
        for c in self.results['configurations']:
            pairs=c['spectral_pairs'];n=c['frame_count_per_epoch']
            for epoch in ['before','after']:
                self.assertEqual(len({p[epoch]['obs_id'] for p in pairs}),n)
            self.assertTrue(all(p['mismatch_bandwidth']<=c['tolerance_bandwidth'] for p in pairs))
            self.assertAlmostEqual(sum(c['common_spectral_weights']),1.)
            np.testing.assert_allclose(c['common_spectral_weights'],[p['weight'] for p in pairs])

    def test_uncertainty_is_positive_and_holdout_is_disjoint(self):
        for c in self.results['configurations']:
            training={tuple(v) for v in c['training_reference_positions']}
            heldout={tuple(v['anchor']) for v in c['heldout_controls']}
            self.assertFalse(training&heldout);self.assertGreaterEqual(len(heldout),2)
            covariance=np.array(c['covariance_arcsec2'])
            self.assertTrue(np.all(np.linalg.eigvalsh(covariance)>0))
            delta=np.array([c['east_arcsec'],c['north_arcsec']])
            self.assertAlmostEqual(c['mahalanobis_distance'],np.sqrt(delta@np.linalg.inv(covariance)@delta))
            self.assertFalse(c['position_tied_to_expected_motion']);self.assertFalse(c['parallax_fitted'])
            for epoch in ['before','after']:
                self.assertTrue(c['target_'+epoch]['success']);self.assertFalse(c['target_'+epoch]['at_boundary'])
                self.assertGreaterEqual(c['bootstrap_'+epoch]['draws'],128)
                self.assertEqual(c['bootstrap_'+epoch]['boundary_fraction'],0.)

    def test_known_robustness_gaps_are_preserved(self):
        for c in self.results['configurations']:
            self.assertEqual(c['status'],'candidate_motion')
            self.assertIsNotNone(c['reference_swap_unavailable_reason'])
            self.assertEqual({v['kind'] for v in c['real_background_injection_controls']},{'stationary','moving'})
            # A single control must remain a diagnostic, not a tuned error floor.
            self.assertIn('not a completeness benchmark',c['real_background_injection_controls'][0]['note'])
        broad=next(c for c in self.results['configurations'] if c['id']=='broad')
        self.assertGreater(broad['coadd_snr_before']['snr'],broad['best_single_snr_before'])
        self.assertGreater(broad['coadd_snr_after']['snr'],broad['best_single_snr_after'])


if __name__=='__main__':unittest.main()
