from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from astropy.io import fits
import numpy as np
from scripts import parse_wise0855_prism as p


def fixture(*, wave=(1.,2.,3.,4.,5.), flux=(1.,-2.,np.nan,3.,4.),
            error=(.1,.2,0.,.3,.4),dq=(0,0,1,0,0),unit='Jy',header_changes=None):
    h=fits.PrimaryHDU()
    for k,v in {'PROGRAM':'01230','OBSERVTN':'007','INSTRUME':'NIRSPEC',
        'DETECTOR':'NRS1','EXP_TYPE':'NRS_FIXEDSLIT','FILTER':'CLEAR','GRATING':'PRISM',
        'TARGNAME':'WISE 0855-0714','DATE-OBS':'2023-04-17','CAL_VER':'3.0.0',
        'CRDS_CTX':'jwst_1584.pmap','ASNTABLE':p.ASN_NAME,'EXPCOUNT':7}.items():h.header[k]=v
    for k,v in (header_changes or {}).items():h.header[k]=v
    columns=[fits.Column(name='WAVELENGTH',format='D',unit='um',array=wave),
             fits.Column(name='FLUX',format='D',unit=unit,array=flux),
             fits.Column(name='FLUX_ERROR',format='D',unit='Jy',array=error),
             fits.Column(name='DQ',format='J',array=np.asarray(dq,dtype=np.int32))]
    b=BytesIO();fits.HDUList([h,fits.BinTableHDU.from_columns(columns,name='EXTRACT1D')]).writeto(b)
    return b.getvalue()


def parse(raw):return p.parse_bytes(raw,expected_sha256=sha256(raw).hexdigest())


class PrismTests(unittest.TestCase):
    def test_rows_retained_negative_flux_and_invalid_error(self):
        s=parse(fixture())
        self.assertEqual(s.usable.tolist(),[True,True,False,True,True])
        self.assertEqual(s.flux_jy[1],-2.)
        self.assertTrue(np.isnan(s.flux_jy[2]));self.assertEqual(s.dq[2],1)
        self.assertEqual(s.summary()['usable_negative_flux'],1)
        s=parse(fixture(error=(.1,-.2,0,.3,.4)))
        self.assertFalse(s.usable[1]);self.assertEqual(s.flux_error_jy[1],-.2)

    def test_interval_bracketing_gap_bad_rows_and_no_extrapolation(self):
        s=parse(fixture())
        valid=s.interval(1.1,1.9,maximum_gap_um=1.)
        self.assertTrue(valid['fully_bracketed_and_usable'])
        self.assertEqual(valid['bracket_range_um'],[1.,2.])
        self.assertEqual(valid['in_interval_rows'],0)
        self.assertFalse(s.interval(1.1,3.1,maximum_gap_um=1.)['fully_bracketed_and_usable'])
        self.assertFalse(s.interval(1.1,1.9,maximum_gap_um=.9)['fully_bracketed_and_usable'])
        self.assertFalse(s.interval(.9,1.9,maximum_gap_um=1.)['fully_bracketed_and_usable'])
        self.assertFalse(s.interval(4.1,5.1,maximum_gap_um=1.)['fully_bracketed_and_usable'])
        with self.assertRaises(ValueError):s.interval(1,1)

    def test_hash_unit_wavelength_target_and_calibration_guards(self):
        raw=fixture()
        with self.assertRaises(ValueError):p.parse_bytes(raw,expected_sha256='0'*64)
        for candidate in (fixture(unit='mJy'),fixture(wave=(1,2,2,4,5)),
            fixture(dq=(0,0,-1,0,0)),fixture(header_changes={'GRATING':'G395M'}),
            fixture(header_changes={'TARGNAME':'OTHER'}),fixture(header_changes={'CAL_VER':'old'}),
            fixture(header_changes={'ASNTABLE':'other.json'})):
            with self.assertRaises(ValueError):parse(candidate)

    def test_public_metadata_and_cached_replay(self):
        product=json.loads((p.ROOT/'web/data/external/wise0855-prism-reference.json').read_text(encoding='utf-8'))
        self.assertEqual(product['product']['sha256'],p.FILE_SHA256)
        self.assertEqual(sha256((p.ROOT/product['provenance']['parser']).read_bytes()).hexdigest(),product['provenance']['parser_sha256'])
        if not p.PATH.exists():self.skipTest('ignored public FITS not cached')
        self.assertEqual(p.read_spectrum().summary(),product['product']['parser_summary'])
        self.assertEqual(p.PATH.stat().st_size,product['product']['bytes'])
        for key in ('metadata_snapshot','association'):
            info=product['provenance'][key];path=p.ROOT/info['path']
            self.assertEqual(sha256(path.read_bytes()).hexdigest(),info['sha256'])
        meta=json.loads((p.RAW/p.META_NAME).read_bytes())
        self.assertIn(product['product']['metadata'],meta['data'])
        asn=json.loads((p.RAW/p.ASN_NAME).read_bytes())
        self.assertEqual(asn['products'][0]['members'],product['provenance']['association']['members'])
        self.assertEqual(sum(x['exptype']=='science' for x in asn['products'][0]['members']),3)

    def test_fetch_pinned_checks_and_refuses_replacement_if_cached(self):
        files=[p.PATH,p.RAW/p.ASN_NAME,p.RAW/p.META_NAME]
        if not all(x.exists() for x in files):self.skipTest('ignored MAST inputs not cached')
        raw,asn,meta=[x.read_bytes() for x in files]
        def mocked_open(request,timeout):
            url=request.full_url
            if 'Mast.Caom.Products' in url or '/api/v0/invoke?' in url:return BytesIO(meta)
            if p.FILENAME in url:return BytesIO(raw)
            if p.ASN_NAME in url:return BytesIO(asn)
            raise AssertionError('unexpected URL')
        with TemporaryDirectory() as tmp,patch.object(p,'RAW',Path(tmp)),patch.object(p,'urlopen',side_effect=mocked_open):
            p.fetch_pinned()
            self.assertEqual((Path(tmp)/p.FILENAME).read_bytes(),raw)
            p.fetch_pinned()  # identical cache is left intact
            (Path(tmp)/p.ASN_NAME).write_bytes(b'different')
            with self.assertRaisesRegex(ValueError,'refusing to overwrite'):p.fetch_pinned()
            self.assertEqual((Path(tmp)/p.ASN_NAME).read_bytes(),b'different')
