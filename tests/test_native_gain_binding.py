import json
from pathlib import Path
import unittest

import numpy as np
from astropy.io import fits
from scripts import native_gain_binding as b, audit_native_gain as audit


def lookup():
    return (f'''<VOTABLE xmlns="http://www.ivoa.net/xml/VOTable/v1.3"><RESOURCE>
      <INFO name="QUERY_STATUS" value="OK"/><TABLE>
      <FIELD name="planeid"/><FIELD name="uri"/><FIELD name="producttype"/>
      <FIELD name="productid"/><FIELD name="provenance_version"/><DATA><TABLEDATA><TR>
      <TD>{b.UUID}</TD><TD>{b.URI}</TD><TD>calibration</TD><TD>D6</TD><TD>6.1</TD>
      </TR></TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>''').encode()


def image_headers():
    pri=fits.Header(); pri['VERSION']='6.4+psffix1'
    h=fits.Header()
    for k,v in {'DETECTOR':6,'DETCOORD':'sky','WCSNAMEA':'0-based active pixel coordinates',
       'WCSAXESA':2,'CTYPE1A':'LINEAR','CTYPE2A':'LINEAR','CUNIT1A':'pixel','CUNIT2A':'pixel',
       'CRPIX1A':-895.0,'CRPIX2A':-1947.0,'CRVAL1A':0.0,'CRVAL2A':0.0,
       'CDELT1A':1.0,'CDELT2A':1.0,'NAXIS1':70,'NAXIS2':70}.items():
        h['HIERARCH '+k if len(k)>8 else k]=v
    h.add_history('[CALIB] abs_gain_matrix '+b.UUID)
    return pri,h


class GainTests(unittest.TestCase):
    def test_exact_lookup_and_history(self):
        self.assertEqual(b.validate_lookup(lookup())['planeid'],b.UUID)
        for bad in [lookup().replace(b'calibration',b'science'),lookup().replace(b.UUID.encode(),b'wrong'),
                    lookup().replace(b'QUERY_STATUS" value="OK',b'QUERY_STATUS" value="ERROR')]:
            with self.assertRaises(ValueError): b.validate_lookup(bad)
        pri,h=image_headers()
        for mutate in ('wrong_uuid','duplicate','version','detector','detcoord','collection'):
            ph,ih=pri.copy(),h.copy();collection='spherex_qr2'
            if mutate=='wrong_uuid': ih.remove('HISTORY',remove_all=True);ih.add_history('[CALIB] abs_gain_matrix other')
            if mutate=='duplicate': ih.add_history('[CALIB] abs_gain_matrix '+b.UUID)
            if mutate=='version': ph['VERSION']='unknown'
            if mutate=='detector': ih['DETECTOR']=5
            if mutate=='detcoord': ih['DETCOORD']='device'
            if mutate=='collection': collection='spherex_qr3'
            with self.subTest(mutate=mutate),self.assertRaises(ValueError): b.validate_image(ih,ph,collection)

    def test_axis_mapping_rejects_manual_flip_and_bad_coordinates(self):
        pri,h=image_headers()
        dx,dy=b.detector_indices(h,pri,'spherex_qr2',np.array([0,1]),np.array([0,1]),(70,70))
        np.testing.assert_array_equal(dx,[896,897]);np.testing.assert_array_equal(dy,[1948,1949])
        # Deliberately non-symmetric pattern proves y,x indexing, no extra D6 flip.
        gain=np.ones((2040,2040),dtype=np.float32)
        gain[1948,896]=3;gain[1949,897]=7;gain[1948,2040-1-896]=99
        np.testing.assert_array_equal(b.bind_values(gain,dx,dy).value,[3,7])
        gain[1948,896]=-1
        with self.assertRaises(ValueError): b.bind_values(gain,dx,dy)
        gain[1948,896]=np.nan
        with self.assertRaises(ValueError): b.bind_values(gain,dx,dy)
        for x,y in [([0.1],[1]),([70],[0]),([-1],[0]),([float('nan')],[0])]:
            with self.assertRaises(ValueError): b.detector_indices(h,pri,'spherex_qr2',x,y,(70,70))
        flip=h.copy();flip['CDELT1A']=-1
        with self.assertRaises(ValueError): b.detector_indices(flip,pri,'spherex_qr2',[1],[1],(70,70))
        far=h.copy();far['CRPIX1A']=-2040
        with self.assertRaises(ValueError): b.detector_indices(far,pri,'spherex_qr2',[1],[1],(70,70))
        missing=h.copy();del missing['CRPIX1A']
        with self.assertRaises(ValueError): b.detector_indices(missing,pri,'spherex_qr2',[1],[1],(70,70))
        with self.assertRaises(ValueError): b.detector_indices(h,pri,'spherex_qr2',[1],[1],(71,70))

    def test_gain_metadata_and_units(self):
        pri=fits.PrimaryHDU();pri.header['VERSION']=b.GAIN_VERSION
        im=fits.ImageHDU(np.ones((2040,2040),dtype=np.float32),name='IMAGE')
        im.header['BUNIT']='MJy s / (electron sr)'
        hdus=fits.HDUList([pri,im])
        self.assertEqual(b.validate_calibration(hdus,b.GAIN_SHA256,b.GAIN_BYTES,lookup()).shape,(2040,2040))
        with self.assertRaises(ValueError): b.validate_calibration(hdus,'bad',b.GAIN_BYTES,lookup())
        with self.assertRaises(ValueError): b.validate_calibration(hdus,b.GAIN_SHA256,1,lookup())
        im.header['BUNIT']='MJy / sr'
        with self.assertRaises(ValueError): b.validate_calibration(hdus,b.GAIN_SHA256,b.GAIN_BYTES,lookup())
        im.header['BUNIT']='MJy s / (electron sr)';im.header['DETCOORD']='device'
        with self.assertRaises(ValueError): b.validate_calibration(hdus,b.GAIN_SHA256,b.GAIN_BYTES,lookup())

    def test_public_report_and_optional_replay(self):
        product=json.loads(audit.OUT.read_text(encoding='utf-8'))
        self.assertEqual(product['record_count'],31)
        self.assertEqual(sum(r['invalid_gain_count'] for r in product['records']),1)
        for path,h in product['source_sha256'].items(): self.assertEqual(audit.digest(Path(path)),h)
        self.assertEqual(product['calibration']['sha256'],b.GAIN_SHA256)
        if audit.MANIFEST.exists() and audit.LOOKUP.exists() and audit.GAIN.exists():
            self.assertEqual(audit.build(),product)
