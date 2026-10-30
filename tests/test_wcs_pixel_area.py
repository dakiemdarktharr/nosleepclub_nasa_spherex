import unittest

import numpy as np
from astropy import units as u
from astropy.wcs import Sip, WCS

from scripts.wcs_pixel_area import wcs_pixel_area


def make_wcs(scale=0.05, dec=0., ra=0., matrix=None):
    w = WCS(naxis=2)
    w.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    w.wcs.cunit = ['deg', 'deg']
    w.wcs.crval = [ra, dec]
    w.wcs.crpix = [1., 1.]
    w.wcs.cd = np.array(matrix if matrix is not None else [[-scale, 0.], [0., scale]])
    return w


def area(w, xy=(0., 0.), **kw):
    return wcs_pixel_area(w, xy, provenance='synthetic WCS fixture', **kw)


class PixelAreaTests(unittest.TestCase):
    def test_tan_analytic_center_and_scales(self):
        for scale in (6.15/3600, .05, 2.):
            with self.subTest(scale=scale):
                out = area(make_wcs(scale), relative_tolerance=1e-5)
                a = np.deg2rad(scale)/2
                expected = 4*np.arctan2(a*a, np.sqrt(1+2*a*a))
                self.assertAlmostEqual(out.solid_angle.to_value(u.sr)/expected, 1., delta=2e-9)
                self.assertTrue(out.supported)
                self.assertEqual(out.orientation, -1)
                self.assertEqual(out.provenance, 'synthetic WCS fixture')

    def test_rotation_reflection_wrap_and_pole(self):
        angle=.69; s=.03
        rotation=s*np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        baseline=area(make_wcs(s)).solid_angle.value
        for dec in (0., 89.999, -89.999):
            for ra in (0., 359.999):
                with self.subTest(ra=ra, dec=dec):
                    positive=area(make_wcs(ra=ra,dec=dec,matrix=rotation))
                    negative=area(make_wcs(ra=ra,dec=dec,matrix=rotation@np.diag([-1,1])))
                    self.assertAlmostEqual(positive.solid_angle.value/baseline,1.,delta=1e-8)
                    self.assertAlmostEqual(negative.solid_angle.value/baseline,1.,delta=1e-8)
                    self.assertEqual(positive.orientation,1)
                    self.assertEqual(negative.orientation,-1)

    def test_sip_curved_boundary_refinement_and_unsupported(self):
        w=make_wcs(scale=2.,dec=30.)
        w.wcs.ctype=['RA---TAN-SIP','DEC--TAN-SIP']
        a=np.zeros((4,4)); b=np.zeros((4,4))
        a[0,2]=.25; b[2,0]=.2; a[3,0]=.03
        w.sip=Sip(a,b,None,None,np.array([1.,1.]))
        coarse=area(w,relative_tolerance=0.)
        finer=area(w,coarse_subdivisions=4,fine_subdivisions=8)
        finest=area(w,coarse_subdivisions=8,fine_subdivisions=16)
        self.assertGreater(coarse.relative_difference,0.)
        self.assertFalse(coarse.supported)
        self.assertLess(abs(finer.solid_angle.value-finest.solid_angle.value),abs(coarse.solid_angle.value-finest.solid_angle.value))

    def test_swapped_and_galactic_world_axes(self):
        baseline=area(make_wcs()).solid_angle.value
        swapped=make_wcs()
        swapped.wcs.ctype=['DEC--TAN','RA---TAN']
        swapped.wcs.crval=[0.,0.]
        galactic=make_wcs()
        galactic.wcs.ctype=['GLON-TAN','GLAT-TAN']
        self.assertAlmostEqual(area(swapped).solid_angle.value/baseline,1.,delta=1e-9)
        self.assertAlmostEqual(area(galactic).solid_angle.value/baseline,1.,delta=1e-9)

    def test_folded_wcs_and_invalid_inputs(self):
        w=make_wcs()
        w.wcs.ctype=['RA---TAN-SIP','DEC--TAN-SIP']
        a=np.zeros((3,3));a[2,0]=2.;b=np.zeros((3,3))
        w.sip=Sip(a,b,None,None,np.array([1.,1.]))
        with self.assertRaises(ValueError):area(w)
        bad=make_wcs();bad.wcs.cd=np.zeros((2,2))
        with self.assertRaises(ValueError):area(bad)
        not_sky=WCS(naxis=2)
        for w,xy,kw in [(not_sky,(0,0),{}),(make_wcs(),(np.nan,0),{}),
                        (make_wcs(),(0,0),{'relative_tolerance':-1}),
                        (make_wcs(),(0,0),{'fine_subdivisions':3}),
                        (make_wcs(),(0,0),{'coarse_subdivisions':True})]:
            with self.subTest(kw=kw),self.assertRaises(ValueError):area(w,xy,**kw)
        with self.assertRaises(ValueError):wcs_pixel_area(make_wcs(),(0,0),provenance='')


if __name__ == '__main__':
    unittest.main()
