"""Narrow QR2 D6 gain binding using public pipeline's active-pixel WCS.

Research audit only. Do not use this as an injection or science calibration.
"""
import re
from xml.etree import ElementTree as ET

import numpy as np
from astropy import units as u
from astropy.wcs import WCS

UUID = '0b762d1b-bec8-473f-9e6e-436fff6c631f'
URI = 'ibe/data/spherex/qr2/abs_gain_matrix/cal-agm-v7-2025-218/6/abs_gain_matrix_D6_spx_cal-agm-v7-2025-218.fits'
GAIN_SHA256 = 'b297b1f286cd66b0ce109c5cb884ab08ca980376edf9f161cbf9cd754674bdb8'
GAIN_VERSION = '6.1.3.post97+g4430725'
IMAGE_VERSIONS = frozenset(('6.4+psffix1', '6.5.6'))
GAIN_UNIT = u.MJy * u.s / (u.electron * u.sr)
GAIN_BYTES = 16652160


def validate_lookup(xml_bytes):
    root = ET.fromstring(xml_bytes)
    ns = {'v': 'http://www.ivoa.net/xml/VOTable/v1.3'}
    status = root.findall('.//v:INFO[@name="QUERY_STATUS"]', ns)
    if len(status) != 1 or status[0].get('value') != 'OK':
        raise ValueError('TAP result not uniquely OK')
    tables = root.findall('.//v:TABLE', ns)
    if len(tables) != 1:
        raise ValueError('TAP table ambiguous')
    table = tables[0]
    names = [f.get('name') for f in table.findall('v:FIELD', ns)]
    wanted = ['planeid', 'uri', 'producttype', 'productid', 'provenance_version']
    if len(names) != len(set(names)) or any(names.count(x) != 1 for x in wanted):
        raise ValueError('TAP schema ambiguous')
    matches = []
    for tr in table.findall('.//v:TR', ns):
        cells = [(td.text or '').strip() for td in tr.findall('v:TD', ns)]
        if len(cells) != len(names):
            raise ValueError('TAP row length mismatch')
        row = dict(zip(names, cells))
        if row['planeid'] == UUID:
            matches.append(row)
    if len(matches) != 1 or any(matches[0][k] != v for k,v in
       {'uri':URI, 'producttype':'calibration', 'productid':'D6', 'provenance_version':'6.1'}.items()):
        raise ValueError('TAP calibration mapping mismatch or ambiguous')
    return matches[0]


def unique(header, key):
    cards = [c.value for c in header.cards if c.keyword == key]
    if len(cards) != 1:
        raise ValueError('missing or duplicated header ' + key)
    return cards[0]


def validate_calibration(hdus, sha256, size, lookup):
    validate_lookup(lookup)
    if sha256 != GAIN_SHA256 or size != GAIN_BYTES:
        raise ValueError('gain file hash or size mismatch')
    if unique(hdus[0].header, 'VERSION') != GAIN_VERSION:
        raise ValueError('gain software version mismatch')
    if len([h for h in hdus if h.name == 'IMAGE']) != 1:
        raise ValueError('gain IMAGE missing or ambiguous')
    h = hdus['IMAGE']
    if h.data is None or h.data.shape != (2040,2040) or h.data.dtype.kind != 'f':
        raise ValueError('gain layout mismatch')
    try:
        unit = u.Unit(unique(h.header, 'BUNIT'))
    except Exception as e:
        raise ValueError('invalid gain BUNIT') from e
    if unit != GAIN_UNIT:
        raise ValueError('gain unit mismatch')
    if 'DETCOORD' in h.header and unique(h.header, 'DETCOORD') != 'sky':
        raise ValueError('gain orientation contradicts supported layout')
    return h.data


def validate_image(header, primary, collection):
    if collection != 'spherex_qr2' or unique(header, 'DETECTOR') != 6 or unique(header, 'DETCOORD') != 'sky':
        raise ValueError('unsupported collection/detector/orientation')
    if unique(primary, 'VERSION') not in IMAGE_VERSIONS:
        raise ValueError('unsupported image pipeline version')
    lines = [str(c.value) for c in header.cards if c.keyword == 'HISTORY']
    entries = [line for line in lines if re.match(r'^\[CALIB\]\s+abs_gain_matrix(?:\s|$)', line)]
    if entries != ['[CALIB] abs_gain_matrix ' + UUID]:
        raise ValueError('gain HISTORY missing, mismatched, or ambiguous')
    for key, value in [('WCSNAMEA','0-based active pixel coordinates'), ('WCSAXESA',2),
                       ('CTYPE1A','LINEAR'), ('CTYPE2A','LINEAR'), ('CUNIT1A','pixel'), ('CUNIT2A','pixel')]:
        if unique(header,key) != value:
            raise ValueError('unsupported active-pixel WCS ' + key)
    for key in ('CRPIX1A','CRPIX2A','CRVAL1A','CRVAL2A','CDELT1A','CDELT2A'):
        value=unique(header,key)
        if isinstance(value,(bool,np.bool_)) or not isinstance(value,(int,float,np.integer,np.floating)) or not np.isfinite(value):
            raise ValueError('invalid active-pixel WCS ' + key)
    # Celestial SIP cards apply to the primary WCS, not alternate linear WCS A.
    clean = header.copy()
    for key in list(clean):
        if key in ('A_ORDER','B_ORDER','AP_ORDER','BP_ORDER') or key.startswith(('A_','B_','AP_','BP_')):
            del clean[key]
    w = WCS(clean, key='A')
    if w.pixel_n_dim != 2 or w.world_n_dim != 2 or not np.array_equal(w.pixel_scale_matrix, np.eye(2)):
        raise ValueError('unsupported active-pixel axes or matrix')
    x, y = w.pixel_to_world_values(np.array([0.,1.,0.]), np.array([0.,0.,1.]))
    origin = np.array([x[0], y[0]])
    if not np.isfinite(origin).all() or not np.allclose(origin, np.rint(origin), atol=1e-8, rtol=0):
        raise ValueError('noninteger active-pixel origin')
    if not np.allclose([x[1]-x[0],x[2]-x[0],y[1]-y[0],y[2]-y[0]], [1,0,0,1], atol=1e-10, rtol=0):
        raise ValueError('nonidentity active-pixel axes')
    return w


def detector_indices(header, primary, collection, x, y, image_shape):
    w = validate_image(header, primary, collection)
    x, y = np.asarray(x), np.asarray(y)
    if x.shape != y.shape or x.dtype.kind not in 'iuf' or y.dtype.kind not in 'iuf':
        raise ValueError('native coordinates invalid')
    if len(image_shape) != 2 or tuple(image_shape) != (unique(header,'NAXIS2'),unique(header,'NAXIS1')) or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('native coordinates invalid')
    if np.any(x != np.rint(x)) or np.any(y != np.rint(y)) or np.any(x < 0) or np.any(y < 0) or np.any(x >= image_shape[1]) or np.any(y >= image_shape[0]):
        raise ValueError('native coordinates noninteger or outside image')
    dx,dy = w.pixel_to_world_values(x,y)
    if not np.isfinite(dx).all() or not np.isfinite(dy).all() or not np.allclose(dx,np.rint(dx),rtol=0,atol=1e-8) or not np.allclose(dy,np.rint(dy),rtol=0,atol=1e-8):
        raise ValueError('detector coordinates not exact integers')
    dx,dy=np.rint(dx).astype(np.int64),np.rint(dy).astype(np.int64)
    if np.any(dx<0) or np.any(dy<0) or np.any(dx>=2040) or np.any(dy>=2040):
        raise ValueError('detector coordinates out of bounds')
    return dx,dy


def bind_values(gain, dx, dy):
    dx,dy=np.asarray(dx),np.asarray(dy)
    if gain.shape != (2040,2040) or dx.shape != dy.shape or dx.dtype.kind not in 'iu' or dy.dtype.kind not in 'iu' or np.any(dx<0) or np.any(dy<0) or np.any(dx>=2040) or np.any(dy>=2040):
        raise ValueError('invalid gain or detector indices')
    values = np.asarray(gain[dy,dx], dtype=float)
    if not np.isfinite(values).all() or np.any(values<=0):
        raise ValueError('nonfinite or nonpositive gain at requested pixel')
    return values * GAIN_UNIT
