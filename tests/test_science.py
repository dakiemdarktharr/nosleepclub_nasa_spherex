"""Numerical controls and real-data provenance checks. No network needed."""
import json
from hashlib import sha256
from pathlib import Path
import unittest

import numpy as np
from astropy.io import fits
from scipy.ndimage import shift as image_shift
from scipy.signal import convolve2d

from scripts import build_demo as pipeline

ROOT = Path(__file__).resolve().parents[1]


def gaussian(sigma):
    yy, xx = np.indices((11, 11))
    psf = np.exp(-((xx-5)**2+(yy-5)**2)/(2*sigma**2))
    return psf/psf.sum()


class NumericalControls(unittest.TestCase):
    def test_bilinear_variance_uses_squared_weights(self):
        data = np.array([[1.,2.],[3.,4.]])
        image, variance, support = pipeline.bilinear(data, np.full((2,2),4.), np.ones((2,2),bool),
                                                    np.array([[.5]]), np.array([[.5]]))
        self.assertAlmostEqual(image.item(),2.5)
        self.assertAlmostEqual(variance.item(),1.)
        self.assertEqual(support.item(),1.)

    def test_missing_data_is_nan_not_zero(self):
        image, variance, _ = pipeline.bilinear(np.ones((2,2)),np.ones((2,2)),np.zeros((2,2),bool),
                                               np.array([[.5]]),np.array([[.5]]))
        self.assertTrue(np.isnan(image.item()))
        self.assertTrue(np.isnan(variance.item()))

    def test_known_source_bit_remains_usable(self):
        self.assertEqual((1<<21)&pipeline.BAD_MASK,0)
        self.assertNotEqual((1<<6)&pipeline.BAD_MASK,0)

    def test_registration_shift_and_sampling_sign(self):
        yy,xx=np.indices(pipeline.SHAPE)
        a=np.zeros(pipeline.SHAPE)
        for x,y in [(12,13),(19,43),(40,14),(49,48),(11,53)]:
            a+=np.exp(-((xx-x)**2+(yy-y)**2)/2)
        b=image_shift(a,(-.25,.35),order=3)
        correction,info=pipeline.registration(a,b,[np.array([32,32])])
        np.testing.assert_allclose(correction,[.35,-.25],atol=.08)
        self.assertGreaterEqual(info['matched_stars'],3)
        frame={'data':b,'variance':np.ones_like(b),'valid':np.ones_like(b,dtype=bool),
               'wcs':pipeline.grid_wcs()}
        # Test the spatial sampling independently of the spectral lookup.
        ra,dec=pipeline.grid_wcs().pixel_to_world_values(xx+correction[0],yy+correction[1])
        sx,sy=frame['wcs'].world_to_pixel_values(ra,dec)
        corrected,_,_=pipeline.bilinear(b,frame['variance'],frame['valid'],sx,sy)
        self.assertLess(np.nanmean((corrected-a)**2),np.mean((b-a)**2))

    def test_static_source_psf_control_and_injected_mover(self):
        scene=np.zeros(pipeline.SHAPE);scene[32,30]=5.
        pa,pb=gaussian(.8),gaussian(1.2)
        a=convolve2d(scene,pa,mode='same');b=convolve2d(scene,pb,mode='same')
        aa,_,_=pipeline.smooth_with_psf(a,np.ones_like(a),pb)
        bb,_,_=pipeline.smooth_with_psf(b,np.ones_like(b),pa)
        self.assertLess(np.nanmax(np.abs(aa-bb)),1e-10)
        moved=np.zeros_like(scene);moved[32,32]=5.
        b=convolve2d(moved,pb,mode='same')
        bb,_,_=pipeline.smooth_with_psf(b,np.ones_like(b),pa)
        delta=bb-aa
        self.assertLess(np.nanmin(delta),-.05)
        self.assertGreater(np.nanmax(delta),.05)

    def test_prior_is_guide_and_moves_west(self):
        a=pipeline.expected_position(60800.)
        b=pipeline.expected_position(61170.)
        self.assertLess(b[0],a[0])
        self.assertGreater(b[1],a[1])


class RealDataProducts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((ROOT/'web/data/manifest.json').read_text(encoding='utf-8'))

    def test_three_real_pairs_are_unconfirmed(self):
        self.assertTrue(self.manifest['data_real'])
        self.assertEqual(self.manifest['legacy_analysis_sha256'],sha256(Path(pipeline.__file__).read_bytes()).hexdigest())
        legacy=[s for s in self.manifest['scenes'] if s.get('kind')!='coadd']
        self.assertEqual(len(legacy),3)
        for s in legacy:
            self.assertEqual(s['target_detection'],'unconfirmed')
            self.assertGreater(s['baseline_days'],150)
            self.assertLess(s['wavelength_mismatch_channels'],.5)

    def test_input_hashes_when_raw_cache_available(self):
        for s in self.manifest['scenes']:
            for frame in [s['before'],s['after']]:
                for record in frame.get('inputs',[frame]):
                    path=ROOT/record['path']
                    if path.exists():
                        self.assertEqual(sha256(path.read_bytes()).hexdigest(),record['sha256'])

    def test_products_have_wcs_and_no_highlights_in_invalid_regions(self):
        for s in self.manifest['scenes']:
            with fits.open(ROOT/'web'/s['fits']) as h:
                for name in ['BEFORE','AFTER','DIFFERENCE','EMP_SCORE','VALID']:
                    self.assertEqual(h[name].data.shape,(64,64))
                    w=pipeline.WCS(h[name].header)
                    ra,dec=w.pixel_to_world_values(31.5,31.5)
                    x,y=w.world_to_pixel_values(ra,dec)
                    np.testing.assert_allclose([x,y],[31.5,31.5],atol=1e-6)
                for candidate in s['candidates']:
                    self.assertEqual(h['VALID'].data[candidate['y'],candidate['x']],1)


if __name__=='__main__':
    unittest.main()
