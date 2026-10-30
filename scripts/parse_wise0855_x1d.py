"""Read the recorded public MAST spectrum; no interpolation or fitting."""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from astropy.io import fits
import numpy as np

FILE_SHA256 = '9474fbbcfe1304fa6763fd3a9ea3190f419785763f53a1827ac997aef84e19a6'
FILENAME = 'jw01230-o007_t001-s000000001_nirspec_f290lp-g395m-s200a1-subs200a1_x1d.fits'
ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'data/raw/external/wise0855' / FILENAME


@dataclass(frozen=True)
class Spectrum:
    wavelength_um: np.ndarray
    flux_jy: np.ndarray
    flux_error_jy: np.ndarray
    dq: np.ndarray
    usable: np.ndarray

    def summary(self):
        w=self.wavelength_um
        band=(w>=4.4)&(w<=5.0)
        return {'rows':len(w), 'usable':int(self.usable.sum()),
                'dq_nonzero':int(np.count_nonzero(self.dq)),
                'invalid_flux':int((~np.isfinite(self.flux_jy)).sum()),
                'wavelength_range_um':[float(w[0]),float(w[-1])],
                'd6_4_4_to_5_0_rows':int(band.sum()),
                'd6_4_4_to_5_0_usable':int((band & self.usable).sum()),
                'usable_negative_flux':int((self.usable & (self.flux_jy<0)).sum())}


def parse_bytes(raw, *, expected_sha256=FILE_SHA256):
    """Check exact bytes, source identity, units and rows; retain invalid rows.

    ``usable`` is a conservative diagnostic rule, not a calibrated selection:
    DQ==0, finite flux/error and strictly positive error. Negative flux is valid.
    """
    if not isinstance(raw,bytes) or sha256(raw).hexdigest()!=expected_sha256:
        raise ValueError('spectrum SHA-256 mismatch')
    with fits.open(BytesIO(raw),memmap=False) as h:
        header=h[0].header
        checks={'PROGRAM':'01230','OBSERVTN':'007','INSTRUME':'NIRSPEC',
                'DETECTOR':'NRS1','EXP_TYPE':'NRS_FIXEDSLIT','FILTER':'F290LP',
                'GRATING':'G395M','TARGNAME':'WISE 0855-0714','DATE-OBS':'2023-04-17',
                'CAL_VER':'3.0.0','CRDS_CTX':'jwst_1584.pmap','EXPCOUNT':3}
        for key,value in checks.items():
            items=[c.value for c in header.cards if c.keyword==key]
            if items != [value]: raise ValueError('unsupported FITS metadata: '+key)
        extract=[x for x in h if x.name=='EXTRACT1D']
        if len(extract)!=1 or extract[0].data is None:
            raise ValueError('missing or ambiguous EXTRACT1D')
        x=extract[0]
        for name,unit in [('WAVELENGTH','um'),('FLUX','Jy'),('FLUX_ERROR','Jy')]:
            if x.columns.names.count(name)!=1 or x.columns[name].unit!=unit:
                raise ValueError('unsupported column or unit: '+name)
        if x.columns.names.count('DQ')!=1:
            raise ValueError('missing or ambiguous DQ column')
        w=np.array(x.data['WAVELENGTH'],dtype=float)
        f=np.array(x.data['FLUX'],dtype=float)
        e=np.array(x.data['FLUX_ERROR'],dtype=float)
        dq=np.array(x.data['DQ'])
    if w.ndim!=1 or not len(w) or any(a.shape!=w.shape for a in (f,e,dq)):
        raise ValueError('invalid spectrum shape')
    if not np.isfinite(w).all() or np.any(w<=0) or np.any(np.diff(w)<=0):
        raise ValueError('invalid wavelength sequence')
    if dq.dtype.kind not in 'iu' or (dq.dtype.kind=='i' and np.any(dq<0)):
        raise ValueError('invalid DQ encoding')
    usable=(dq==0)&np.isfinite(f)&np.isfinite(e)&(e>0)
    return Spectrum(w,f,e,dq,usable)


def read_spectrum(path=PATH):
    return parse_bytes(Path(path).read_bytes())


if __name__=='__main__':
    print(json.dumps(read_spectrum().summary(),indent=2))
