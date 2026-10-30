"""Pinned MAST PRISM x1d provenance and row-preserving parser; no SED merge."""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import argparse
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from astropy.io import fits
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/external/wise0855'
FILENAME='jw01230-o007_t001-s000000001_nirspec_clear-prism-s200a1-subs200a1_x1d.fits'
PATH=RAW/FILENAME
FILE_SHA256='17164197d803117d02c0e1e89ce64d5521ba86b523d3ba0cc03679974df53e3f'
ASN_NAME='jw01230-o007_20261012t042609_spec3_00001_asn.json'
ASN_SHA256='1f550a1e6dd3f7ca8df364aed0042043de32086a5e77ce8916983e452fc55b29'
META_NAME='mast-products-349842176.json'
META_SHA256='663449493384f7b806863b551cfe8e2fb3e15f82ce4860d75b8825640951f2ca'
DOWNLOAD='https://mast.stsci.edu/jwst/api/v0.1/Download/file?'
MAX_BYTES=2000000
SELECTED_INTERVAL=(4.266020,5.110683)
TAIL_INTERVAL=(5.093073844909667,5.110683)


@dataclass(frozen=True)
class PrismSpectrum:
    wavelength_um: np.ndarray
    flux_jy: np.ndarray
    flux_error_jy: np.ndarray
    dq: np.ndarray
    usable: np.ndarray

    def interval(self, lo, hi, *, maximum_gap_um=.01):
        """Check measured-row brackets and gaps; perform no interpolation."""
        w=self.wavelength_um
        if not np.isfinite([lo,hi,maximum_gap_um]).all() or lo>=hi or maximum_gap_um<=0:
            raise ValueError('invalid interval or maximum gap')
        inside=(w>=lo)&(w<=hi)
        left=int(np.searchsorted(w,lo,side='right')-1)
        right=int(np.searchsorted(w,hi,side='left'))
        result={'interval_um':[float(lo),float(hi)],'maximum_gap_um':float(maximum_gap_um),
            'in_interval_rows':int(inside.sum()),'in_interval_usable_rows':int((inside&self.usable).sum()),
            'bracket_range_um':None,'bracket_rows':0,'bracket_usable_rows':0,
            'max_bracket_gap_um':None,'fully_bracketed_and_usable':False}
        if left<0 or right>=len(w):return result
        sl=slice(left,right+1);gap=float(np.max(np.diff(w[sl])))
        result.update(bracket_range_um=[float(w[left]),float(w[right])],bracket_rows=right-left+1,
            bracket_usable_rows=int(self.usable[sl].sum()),max_bracket_gap_um=gap,
            fully_bracketed_and_usable=bool(self.usable[sl].all() and gap<=maximum_gap_um))
        return result

    def summary(self):
        w=self.wavelength_um
        valid_w=w[self.usable]
        return {'rows':len(w),'usable':int(self.usable.sum()),'dq_nonzero':int(np.count_nonzero(self.dq)),
            'nonfinite_flux':int((~np.isfinite(self.flux_jy)).sum()),
            'nonfinite_error':int((~np.isfinite(self.flux_error_jy)).sum()),
            'nonpositive_error':int((self.flux_error_jy<=0).sum()),
            'usable_negative_flux':int((self.usable&(self.flux_jy<0)).sum()),
            'wavelength_range_um':[float(w[0]),float(w[-1])],
            'usable_wavelength_range_um':[float(valid_w[0]),float(valid_w[-1])] if len(valid_w) else None,
            'diagnostic_interval':self.interval(*SELECTED_INTERVAL),
            'previous_g395m_missing_tail':self.interval(*TAIL_INTERVAL)}


def parse_bytes(raw, *, expected_sha256=FILE_SHA256):
    """Validate recorded bytes and metadata; retain every original row."""
    if not isinstance(raw,bytes) or sha256(raw).hexdigest()!=expected_sha256:
        raise ValueError('spectrum SHA-256 mismatch')
    with fits.open(BytesIO(raw),memmap=False) as h:
        checks={'PROGRAM':'01230','OBSERVTN':'007','INSTRUME':'NIRSPEC','DETECTOR':'NRS1',
            'EXP_TYPE':'NRS_FIXEDSLIT','FILTER':'CLEAR','GRATING':'PRISM','TARGNAME':'WISE 0855-0714',
            'DATE-OBS':'2023-04-17','CAL_VER':'3.0.0','CRDS_CTX':'jwst_1584.pmap',
            'ASNTABLE':ASN_NAME,'EXPCOUNT':7}
        for key,value in checks.items():
            if [c.value for c in h[0].header.cards if c.keyword==key]!=[value]:
                raise ValueError('unsupported FITS metadata: '+key)
        hdus=[x for x in h if x.name=='EXTRACT1D']
        if len(hdus)!=1 or hdus[0].data is None:raise ValueError('missing or ambiguous EXTRACT1D')
        x=hdus[0]
        for name,unit in [('WAVELENGTH','um'),('FLUX','Jy'),('FLUX_ERROR','Jy')]:
            if x.columns.names.count(name)!=1 or x.columns[name].unit!=unit:raise ValueError('unsupported column or unit: '+name)
        if x.columns.names.count('DQ')!=1:raise ValueError('missing or ambiguous DQ')
        w=np.array(x.data['WAVELENGTH'],dtype=float);f=np.array(x.data['FLUX'],dtype=float)
        e=np.array(x.data['FLUX_ERROR'],dtype=float);dq=np.array(x.data['DQ'])
    if w.ndim!=1 or len(w)<2 or any(z.shape!=w.shape for z in (f,e,dq)):
        raise ValueError('invalid spectrum shape')
    if not np.isfinite(w).all() or np.any(w<=0) or np.any(np.diff(w)<=0):raise ValueError('invalid wavelength sequence')
    if dq.dtype.kind not in 'iu' or (dq.dtype.kind=='i' and np.any(dq<0)):raise ValueError('invalid DQ encoding')
    usable=(dq==0)&np.isfinite(f)&np.isfinite(e)&(e>0)
    return PrismSpectrum(w,f,e,dq,usable)


def read_spectrum(path=PATH):return parse_bytes(Path(path).read_bytes())


def _download_checked(url, size, digest):
    with urlopen(Request(url,headers={'User-Agent':'NASA-hacks-reference-audit'}),timeout=45) as response:
        data=response.read(MAX_BYTES+1)
    if len(data)!=size or sha256(data).hexdigest()!=digest:
        raise ValueError('retrieved bytes differ from recorded MAST snapshot')
    return data


def fetch_pinned():
    """Fetch only the two recorded public files and product metadata, no overwrite."""
    request={'service':'Mast.Caom.Products','params':{'obsid':'349842176'},'format':'json','pagesize':1000,'page':1}
    meta_url='https://mast.stsci.edu/api/v0/invoke?'+urlencode({'request':json.dumps(request)})
    with urlopen(Request(meta_url,headers={'User-Agent':'NASA-hacks-reference-audit'}),timeout=45) as response:
        meta=response.read(MAX_BYTES+1)
    if len(meta)>MAX_BYTES or sha256(meta).hexdigest()!=META_SHA256:raise ValueError('MAST metadata changed from recorded snapshot')
    records=json.loads(meta)['data']
    def selected(filename, subgroup):
        rows=[x for x in records if x.get('obsID')==349842176 and x.get('productFilename')==filename
            and x.get('productSubGroupDescription')==subgroup and x.get('calib_level')==3 and x.get('dataRights')=='PUBLIC']
        if len(rows)!=1 or not 0<rows[0]['size']<=MAX_BYTES:raise ValueError('product metadata mismatch')
        return rows[0]
    spectrum=selected(FILENAME,'X1D');association=selected(ASN_NAME,'ASN')
    def url(row):return DOWNLOAD+urlencode({'uri':row['dataURI']})
    raw=_download_checked(url(spectrum),spectrum['size'],FILE_SHA256)
    asn=_download_checked(url(association),association['size'],ASN_SHA256)
    parse_bytes(raw);json.loads(asn)
    RAW.mkdir(parents=True,exist_ok=True)
    files=[(FILENAME,raw),(ASN_NAME,asn),(META_NAME,meta)]
    for name,data in files:
        path=RAW/name
        if path.exists() and path.read_bytes()!=data:
            raise ValueError('refusing to overwrite different cached bytes: '+name)
    for name,data in files:
        path=RAW/name
        if not path.exists():
            with path.open('xb') as stream:stream.write(data)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fetch',action='store_true');args=parser.parse_args()
    if args.fetch:fetch_pinned()
    print(json.dumps(read_spectrum().summary(),indent=2,allow_nan=False))
