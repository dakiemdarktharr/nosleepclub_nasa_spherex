import unittest

from astropy import units as u
import numpy as np
try:
    from photutils.psf import ImagePSF
except ImportError:
    ImagePSF = None
from scipy.ndimage import map_coordinates,spline_filter

from scripts.native_flux_template import native_flux_template


def epsf():
    x=np.arange(33)-16;X,Y=np.meshgrid(x,x)
    gaussian=np.exp(-(X*X+Y*Y)/(2*4.8**2))
    # Preserve a small background-subtracted negative ring.
    return gaussian-1e-4*np.exp(-((np.hypot(X,Y)-12)/1.5)**2)


def calculate(*, data=None,pos=(20.25,20.75),mask=None,omega=(6.15*u.arcsec)**2,ox=5,oy=5,
              omega_prov='synthetic test omega',epsf_prov='synthetic test ePSF'):
    return native_flux_template(epsf() if data is None else data,oversampling_x=ox,oversampling_y=oy,
        source_xy=pos,selection_mask=np.ones((41,41),bool) if mask is None else mask,
        source_omega=omega,source_omega_provenance=omega_prov,epsf_provenance=epsf_prov)


class NativeFluxTemplateTests(unittest.TestCase):
    def test_unit_flux_phase_grid_and_units(self):
        omega=(6.15*u.arcsec)**2
        for dx in (0.,.25,.5,.75):
            for dy in (0.,.25,.5,.75):
                with self.subTest(dx=dx,dy=dy):
                    out=calculate(pos=(20+dx,20+dy),omega=omega)
                    self.assertAlmostEqual(out.normalized_lattice.sum(),1.,places=13)
                    self.assertAlmostEqual(out.normalized_selected.sum(),1.,places=13)
                    recovered=(out.template_per_jy*(1*u.Jy)*omega).to(u.Jy).value
                    np.testing.assert_allclose(recovered,out.normalized_selected,atol=1e-15)
                    self.assertFalse(out.support_truncated_by_image)

    def test_mask_preserves_full_normalization_and_raw_scale_invariance(self):
        full=calculate();mask=np.zeros((41,41),bool);mask[18:22,18:22]=True
        masked=calculate(mask=mask)
        np.testing.assert_allclose(masked.normalized_lattice,full.normalized_lattice,atol=0,rtol=0)
        np.testing.assert_allclose(masked.normalized_selected,full.normalized_selected[mask.ravel()],atol=0,rtol=0)
        self.assertLess(masked.signed_selected_sum,1.)
        for scale in (1e-100,7.,1e100):
            other=calculate(data=epsf()*scale,mask=mask)
            np.testing.assert_allclose(other.normalized_selected,masked.normalized_selected,rtol=1e-13,atol=1e-15)

    @unittest.skipIf(ImagePSF is None, 'optional photutils comparison')
    def test_independent_imagepsf(self):
        data=epsf();out=calculate(data=data);X,Y=np.meshgrid(out.lattice_x,out.lattice_y)
        reference=ImagePSF(np.pad(data/data.sum()*25,16),oversampling=5)
        reference_stamp=reference.evaluate(X,Y,flux=1.,x_0=20.25,y_0=20.75)
        reference_stamp/=reference_stamp.sum()
        np.testing.assert_allclose(out.normalized_lattice,reference_stamp,atol=2e-12,rtol=1e-9)

    def test_free_flux_residual_equivalence(self):
        data=epsf();out=calculate(data=data)
        raw=spline_filter(np.pad(data/data.sum()*25,16),order=3);center=(raw.shape[0]-1)/2
        unnorm=map_coordinates(raw,[(out.y-20.75)*5+center,(out.x-20.25)*5+center],order=3,mode='constant',cval=0,prefilter=False)
        self.assertAlmostEqual(unnorm.sum(),out.native_sum_before_normalization,places=13)
        sky=np.column_stack([np.ones(len(out.x)),out.x-20,out.y-20])
        rng=np.random.default_rng(67)
        y=2.7*unnorm+sky@np.array([.3,.001,-.002])+rng.normal(0,.01,len(out.x))
        X1=np.column_stack([unnorm,sky]);X2=np.column_stack([out.normalized_selected,sky])
        b1=np.linalg.lstsq(X1,y,rcond=None)[0];b2=np.linalg.lstsq(X2,y,rcond=None)[0]
        np.testing.assert_allclose(y-X1@b1,y-X2@b2,atol=1e-13)
        self.assertAlmostEqual(b2[0],b1[0]*out.native_sum_before_normalization,places=12)

    def test_negative_wings_preserved_and_image_boundary_not_renormalized(self):
        out=calculate()
        self.assertLess(np.min(out.normalized_lattice),0.)
        X,Y=np.meshgrid(out.lattice_x,out.lattice_y)
        self.assertAlmostEqual(np.sum(X*out.normalized_lattice),20.25,delta=.001)
        self.assertAlmostEqual(np.sum(Y*out.normalized_lattice),20.75,delta=.001)
        edge=calculate(pos=(.25,.25))
        self.assertTrue(edge.support_truncated_by_image)
        self.assertAlmostEqual(edge.normalized_lattice.sum(),1.,places=13)
        self.assertLess(edge.signed_selected_sum,1.)

    def test_reject_invalid_inputs_and_singular_normalizations(self):
        badmask=np.ones((41,41),int)
        tests=[{'data':np.zeros((33,33))},{'data':-np.ones((33,33))},
            {'data':np.full((33,33),np.nan)},{'data':np.ones((33,32))},
            {'ox':5,'oy':4},{'ox':0},{'ox':True},{'ox':2000},
            {'pos':(-.1,20)},{'pos':(20,np.nan)},{'mask':badmask},
            {'mask':np.zeros((41,41),bool)},{'omega':5.}, {'omega':1*u.arcsec}, {'omega':1*u.one},
            {'omega':0*u.sr},{'omega':np.nan*u.sr},{'omega':np.ones(2)*u.sr},
            {'omega_prov':''},{'epsf_prov':''}]
        for case in tests:
            with self.subTest(case=list(case)),self.assertRaises(ValueError):calculate(**case)
        outside=np.zeros((41,41),bool);outside[0,0]=True
        with self.assertRaisesRegex(ValueError,'no finite nonzero'):calculate(mask=outside)
        off_grid=np.zeros((33,33));off_grid[17,17]=1.
        with self.assertRaisesRegex(ValueError,'native lattice integral'):
            calculate(data=off_grid,pos=(20.,20.))


if __name__=='__main__':unittest.main()
