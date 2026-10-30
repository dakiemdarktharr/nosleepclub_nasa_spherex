"""Synthetic-only adapter checks; no FITS, sky frames or SED calculations."""
import unittest
import json
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.wcs import WCS

from scripts import wise_linked_inputs as adapter
from scripts.native_flux_template import native_flux_template
from scripts.wcs_pixel_area import wcs_pixel_area


def celestial(cd, crpix):
    w=WCS(naxis=2)
    w.wcs.ctype=['RA---TAN','DEC--TAN']
    w.wcs.crval=[359.999,42.]
    w.wcs.crpix=crpix
    w.wcs.cd=np.asarray(cd,float)
    return w


def fixture(frame_id, angle, offset):
    theta=angle;s=1/3600
    cd=s*np.array([[-np.cos(theta),np.sin(theta)],[np.sin(theta),np.cos(theta)]])
    w=celestial(cd,[21.,21.])
    z=np.arange(33)-16;X,Y=np.meshgrid(z,z)
    raw=np.exp(-(X*X+Y*Y)/38.)
    frame={'record':{'obs_id':frame_id,'path':'synthetic/'+frame_id,'sha256':'synthetic-sha'},'data_unit':'MJy/sr',
           'data':np.zeros((41,41)),'wcs':w,'offset':np.array(offset),
           'epsf_table':{'EPSF':np.array([raw])},'epsf_oversampling':5.,
           'epsf_provenance':'synthetic ePSF provenance'}
    mask=np.zeros((41,41),bool);mask[15:26,15:26]=True
    mask[17,19]=False;mask[23,22]=False
    y,x=np.nonzero(mask);error=.3+.01*(x-15)+.02*(y-15)
    design=np.column_stack([np.ones(len(x)),(x-20)/6,(y-20)/6,
                            np.exp(-((x-18)**2+(y-22)**2)/3)])
    q=np.linalg.svd(design/error[:,None],full_matrices=False)[0]
    sample={'frame':frame,'x':x.astype(float),'y':y.astype(float),
            'error':error,'q':q,'zone':0,'data':.1*x-.2*y}
    return frame,sample,mask,design,cd


class WiseAdapterTests(unittest.TestCase):
    def test_exact_rotated_wcs_and_frame_offsets(self):
        common_cd=np.array([[-1/3600,0],[0,1/3600]])
        common=celestial(common_cd,[1.,1.])
        frame,_,_,_,native_cd=fixture('frame-a',.47,[.35,-.4])
        with patch.object(adapter.gaia.motion,'WCS',common):
            for pos in ([0.,0.],[.7,-.3],[-1.,.5]):
                expected=np.array([20.,20.])+np.linalg.solve(native_cd,common_cd@(np.array(pos)+frame['offset']))
                np.testing.assert_allclose(adapter.native_position(frame,pos),expected,atol=3e-10,rtol=0)

    def test_renderer_order_units_closures_and_provenance(self):
        common=celestial([[-1/3600,0],[0,1/3600]],[1.,1.])
        a,sa,ma,_,_=fixture('frame-a',.47,[.2,-.1])
        b,sb,mb,_,_=fixture('frame-b',-.32,[-.3,.15])
        with patch.object(adapter.gaia.motion,'WCS',common), patch.object(adapter.quality,'samples_for',return_value=[sa,sb]):
            actual=adapter.prepared_samples([a,b],[],{},np.zeros(2))
            self.assertEqual([v['obs_id'] for v in actual],['frame-a','frame-b'])
            for frame,sample,mask,prepared in zip([a,b],[sa,sb],[ma,mb],actual):
                self.assertEqual(prepared['data_unit'],'MJy/sr')
                self.assertIn('synthetic/'+frame['record']['obs_id'],prepared['renderer_provenance'])
                np.testing.assert_array_equal(prepared['data'],sample['data'])
                np.testing.assert_array_equal(prepared['selection_mask'],mask)
                position=np.array([.15,-.25]);native=adapter.native_position(frame,position)
                omega=wcs_pixel_area(frame['wcs'],native,provenance='synthetic').solid_angle
                reference=native_flux_template(frame['epsf_table']['EPSF'][0],oversampling_x=5,oversampling_y=5,
                    source_xy=native,selection_mask=mask,source_omega=omega,
                    source_omega_provenance='synthetic',epsf_provenance='synthetic')
                output=prepared['renderer'](position)
                self.assertEqual(output.unit,u.MJy/u.sr/u.Jy)
                np.testing.assert_allclose(output.value,reference.template_per_jy.value,rtol=1e-13,atol=0)
                np.testing.assert_array_equal(np.nonzero(mask)[0],sample['y'])
                np.testing.assert_array_equal(np.nonzero(mask)[1],sample['x'])
            self.assertFalse(np.allclose(actual[0]['renderer']([.15,-.25]).value,actual[1]['renderer']([.15,-.25]).value))

    def test_recovered_nuisance_span_and_reweight_projection(self):
        frame,sample,_,design,_=fixture('frame',.4,[0.,0.])
        with patch.object(adapter.quality,'samples_for',return_value=[sample]):
            prepared=adapter.prepared_samples([frame],[],{},np.zeros(2))[0]
        self.assertEqual(prepared['nuisance_provenance'],
                         'fixed frozen neighbor/background span; rescaled from initial whitened SVD basis')
        weight=np.linspace(.2,1.,len(sample['error']))
        whiten=np.sqrt(weight)/sample['error']
        direct=np.linalg.svd(design*whiten[:,None],full_matrices=False)[0]
        recovered=np.linalg.svd(prepared['nuisance']*whiten[:,None],full_matrices=False)[0]
        np.testing.assert_allclose(direct@direct.T,recovered@recovered.T,atol=2e-14,rtol=0)

    def test_synthetic_active_and_per_hdu_orientation(self):
        primary=fits.Header();primary['VERSION']='6.4+psffix1'
        header=fits.Header()
        cards={'DETECTOR':6,'DETCOORD':'sky','WCSNAMEA':'0-based active pixel coordinates',
               'WCSAXESA':2,'CTYPE1A':'LINEAR','CTYPE2A':'LINEAR','CUNIT1A':'pixel','CUNIT2A':'pixel',
               'CRPIX1A':-99.,'CRPIX2A':-199.,'CRVAL1A':0.,'CRVAL2A':0.,
               'CDELT1A':1.,'CDELT2A':1.,'NAXIS1':41,'NAXIS2':41}
        for key,value in cards.items():header[key]=value
        header.add_history('[CALIB] abs_gain_matrix '+adapter.active_geometry.UUID)
        x,y=adapter.active_geometry.detector_indices(header,primary,'spherex_qr2',
                                                    np.array([20]),np.array([15]),(41,41))
        np.testing.assert_array_equal(x,[120]);np.testing.assert_array_equal(y,[215])
        sx,sy=adapter.binding.active_to_map_indices(x,y,(2040,2040),'sky')
        dx,dy=adapter.binding.active_to_map_indices(x,y,(2040,2040),'DEVICE')
        np.testing.assert_array_equal(sx,[120]);np.testing.assert_array_equal(dx,[1919])
        np.testing.assert_array_equal(sy,dy)
        bad=header.copy();bad['CDELT1A']=-1.
        with self.assertRaises(ValueError):
            adapter.active_geometry.detector_indices(bad,primary,'spherex_qr2',np.array([20]),np.array([15]),(41,41))

    def test_unit_and_calibration_metadata(self):
        h=fits.Header();h['BUNIT']='MJy/sr'
        adapter.checked_unit(h,u.MJy/u.sr)
        for text in ('Jy/sr','MJy','invalid unit'):
            bad=h.copy();bad['BUNIT']=text
            with self.subTest(text=text),self.assertRaises(ValueError):adapter.checked_unit(bad,u.MJy/u.sr)
        duplicate=h.copy();duplicate.append(('BUNIT','MJy/sr'))
        with self.assertRaises(ValueError):adapter.checked_unit(duplicate,u.MJy/u.sr)
        def hdu(name,orientation='sky',unit='um',detector=6):
            header=fits.Header();header['BUNIT']=unit;header['DETCOORD']=orientation;header['DETECTOR']=detector
            return SimpleNamespace(name=name,data=np.broadcast_to(np.zeros(1),(2040,2040)),header=header)
        adapter.validate_spectral_calibration([hdu('CWAVE'),hdu('CBAND')])
        for bad in ([hdu('CWAVE','DEVICE'),hdu('CBAND')], [hdu('CWAVE',unit='nm'),hdu('CBAND')],
                    [hdu('CWAVE',detector=5),hdu('CBAND')],[hdu('CWAVE'),hdu('CWAVE'),hdu('CBAND')]):
            with self.assertRaises(ValueError):adapter.validate_spectral_calibration(bad)

    def test_shuffled_duplicate_noninteger_and_wrong_unit_rejected(self):
        frame,sample,_,_,_=fixture('frame',.4,[0.,0.])
        def prepare(value):
            with patch.object(adapter.quality,'samples_for',return_value=[value]):
                return adapter.prepared_samples([frame],[],{},np.zeros(2))
        bad_x=sample['x'].copy();bad_y=sample['y'].copy();bad_x[:2]=bad_x[1::-1];bad_y[:2]=bad_y[1::-1]
        duplicate=sample['x'].copy();duplicate[1]=duplicate[0]
        fraction=sample['x'].copy();fraction[0]+=.1
        for value in ({**sample,'x':bad_x,'y':bad_y},{**sample,'x':duplicate},
                      {**sample,'x':fraction},{**sample,'frame':{**frame,'data_unit':'Jy/sr'}}):
            with self.assertRaises(ValueError):prepare(value)

    def test_duplicate_exposures_rejected_from_fake_config(self):
        f1,*_=fixture('a',0,[0,0]); f2,*_=fixture('b',0,[0,0])
        registration=[{'obs_id':i,'offset_px':[0,0],'covariance_px2':[[1,0],[0,1]]} for i in ('a','b')]
        def report(before,after):
            payload={'configurations':[{'spectral_configuration':'broad','frame_registration':registration,
                                         'spectral_pairs':[{'before':{'obs_id':before},'after':{'obs_id':after}}]}]}
            return SimpleNamespace(read_text=lambda **kwargs:json.dumps(payload))
        with patch.object(adapter,'GAIA_RESULTS',report('a','b')):
            with self.assertRaisesRegex(ValueError,'duplicate native exposure'):adapter.configuration([f1,f1],'broad')
        with patch.object(adapter,'GAIA_RESULTS',report('a','a')):
            with self.assertRaisesRegex(ValueError,'both epochs'):adapter.configuration([f1,f2],'broad')


if __name__=='__main__':unittest.main()
