from hashlib import sha256
from io import BytesIO
import json
import unittest

from astropy.io import fits
import numpy as np
from scripts import parse_wise0855_x1d as p


def sample(wave=(4.4,4.5,4.6,4.7),flux=(1.,-2.,np.nan,3.),
           error=(.1,.2,.0,.3),dq=(0,0,1,4),unit='Jy',header_changes=None):
    h=fits.PrimaryHDU()
    for k,v in {'PROGRAM':'01230','OBSERVTN':'007','INSTRUME':'NIRSPEC',
        'DETECTOR':'NRS1','EXP_TYPE':'NRS_FIXEDSLIT','FILTER':'F290LP',
        'GRATING':'G395M','TARGNAME':'WISE 0855-0714','DATE-OBS':'2023-04-17',
        'CAL_VER':'3.0.0','CRDS_CTX':'jwst_1584.pmap','EXPCOUNT':3}.items():h.header[k]=v
    for k,v in (header_changes or {}).items():h.header[k]=v
    col=[fits.Column(name='WAVELENGTH',format='D',unit='um',array=wave),
         fits.Column(name='FLUX',format='D',unit=unit,array=flux),
         fits.Column(name='FLUX_ERROR',format='D',unit='Jy',array=error),
         fits.Column(name='DQ',format='J',array=np.asarray(dq,dtype=np.int32))]
    hdus=fits.HDUList([h,fits.BinTableHDU.from_columns(col,name='EXTRACT1D')])
    b=BytesIO();hdus.writeto(b);return b.getvalue()


def parse(raw):return p.parse_bytes(raw,expected_sha256=sha256(raw).hexdigest())


class WiseSpectrumTests(unittest.TestCase):
    def test_conservative_mask_preserves_negative_flux_and_bad_rows(self):
        data=parse(sample())
        self.assertEqual(data.usable.tolist(),[True,True,False,False])
        self.assertEqual(data.summary()['usable_negative_flux'],1)
        self.assertTrue(np.isnan(data.flux_jy[2]))
        self.assertEqual(data.summary()['d6_4_4_to_5_0_rows'],4)

    def test_hash_units_and_monotonicity(self):
        raw=sample()
        with self.assertRaises(ValueError):p.parse_bytes(raw,expected_sha256='0'*64)
        with self.assertRaises(ValueError):parse(sample(unit='mJy'))
        with self.assertRaises(ValueError):parse(sample(wave=(4.4,4.5,4.5,4.7)))
        with self.assertRaises(ValueError):parse(sample(wave=(4.4,4.5,np.nan,4.7)))
        with self.assertRaises(ValueError):parse(sample(dq=(0,0,-1,4)))
        with self.assertRaises(ValueError):parse(sample(header_changes={'TARGNAME':'OTHER'}))
        with self.assertRaises(ValueError):parse(sample(header_changes={'CAL_VER':'2.0.0'}))

    def test_actual_product_and_public_provenance_if_cached(self):
        metadata=json.loads((p.ROOT/'web/data/external/wise0855-sed-reference.json').read_text(encoding='utf-8'))
        product=metadata['mast_x1d']
        self.assertEqual(product['sha256'],p.FILE_SHA256)
        self.assertEqual(sha256((p.ROOT/product['parser']).read_bytes()).hexdigest(),product['parser_sha256'])
        if p.PATH.exists():
            result=p.read_spectrum()
            self.assertEqual(result.summary(),product['parser_summary'])
            self.assertEqual(len(p.PATH.read_bytes()),product['bytes'])
            for part in ('association','metadata_snapshot'):
                path=p.ROOT/product[part]['path']
                self.assertEqual(sha256(path.read_bytes()).hexdigest(),product[part]['sha256'])
            rows=json.loads((p.ROOT/product['metadata_snapshot']['path']).read_text())['data']
            self.assertIn(product['product_metadata'],rows)
            a=json.loads((p.ROOT/product['association']['path']).read_text())
            self.assertEqual([m for m in a['products'][0]['members'] if m['exptype']=='science'],product['association']['science_members'])
        else:
            self.skipTest('ignored MAST FITS not cached')
