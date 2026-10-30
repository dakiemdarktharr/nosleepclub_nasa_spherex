"""Ideal source-only Poisson ramp injection, not a detector simulation.

All physical quantities are explicit Astropy Quantities. Input images and
variances are not modified; only incremental signal/noise/variance are returned.
"""
from __future__ import annotations
import copy
from hashlib import sha256
import json
from numbers import Integral, Real
from collections.abc import Mapping
import numpy as np
import astropy.units as u

SOURCE_UNIT=u.MJy/u.sr
GAIN_UNIT=(u.MJy/u.sr)/(u.electron/u.s)
MAX_READS=10000
MAX_BATCH_PIXELS=1000000
PIPELINE_SOURCE='https://github.com/Caltech-IPAC/spherex-pipelines/blob/aa0ba446ee12971024fe13dc1c47387615bbe85e/py_src/spx_tasks/create_variance_map.py'
PIPELINE_BLOB_SHA1='c682a3c8574b16e0f092dd89266a0dbaeaad9b47'


def _jsonable(value):
    if isinstance(value,dict):return {str(k):_jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [_jsonable(v) for v in value]
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    return value


def _header_values(header):
    required=('SURLIM','SURDLY','TSAMP','XPOSURE')
    if not isinstance(header,Mapping) and not hasattr(header,'cards'):raise ValueError('header must be a mapping or FITS Header')
    if hasattr(header,'cards'):
        pairs=[(str(c.keyword).strip().upper(),c.value) for c in header.cards]
    else:pairs=[(str(k).strip().upper(),v) for k,v in header.items()]
    values={}
    for key in required:
        matches=[v for k,v in pairs if k==key]
        if len(matches)!=1:raise ValueError('missing or duplicate '+key)
        values[key]=matches[0]
    for key in ('SURLIM','SURDLY'):
        v=values[key]
        if isinstance(v,(bool,np.bool_)) or not isinstance(v,Integral):raise ValueError(key+' must be an integer')
        values[key]=int(v)
    for key in ('TSAMP','XPOSURE'):
        v=values[key]
        if isinstance(v,(bool,np.bool_)) or not isinstance(v,Real) or not np.isfinite(v) or v<=0:raise ValueError(key+' must be positive and finite seconds')
        values[key]=float(v)
    if values['SURDLY']<1 or values['SURLIM']<values['SURDLY']:raise ValueError('invalid ramp read range')
    n=values['SURLIM']-(values['SURDLY']-1)
    if not 2<=n<=MAX_READS:raise ValueError('nominal read count outside supported range')
    span=(n-1)*values['TSAMP'];integration=n*values['TSAMP']
    if not np.isfinite(span) or not np.isfinite(integration):raise ValueError('nominal timing outside numerical range')
    tolerance=max(1e-4,span*1e-8)
    if abs(values['XPOSURE']-span)>tolerance:raise ValueError('XPOSURE inconsistent with nominal sample span')
    return {**values,'n':n,'sample_span_seconds':span,'nominal_pipeline_integration_seconds':integration,
            'xposure_tolerance_seconds':tolerance}


def poisson_factor(n):
    if isinstance(n,(bool,np.bool_)) or not isinstance(n,Integral) or not 2<=n<=MAX_READS:raise ValueError('invalid read count')
    n=int(n)
    return 6./5.*(n*n+1)/(n*n-1)


def increment_weights(n,dt_seconds):
    """OLS rate coefficient for each of n-1 independent charge increments."""
    poisson_factor(n)
    if isinstance(dt_seconds,(bool,np.bool_)) or not isinstance(dt_seconds,Real) or not np.isfinite(dt_seconds) or dt_seconds<=0:raise ValueError('invalid sample interval')
    j=np.arange(1,int(n),dtype=float)
    with np.errstate(over='ignore',divide='ignore',invalid='ignore'):
        weights=(6*j*(int(n)-j)/(int(n)*(int(n)**2-1)))/float(dt_seconds)
    if not np.isfinite(weights).all():raise ValueError('sample interval outside numerical range')
    return weights


def _quantity_values(value,unit,name):
    if not isinstance(value,u.Quantity):raise ValueError(name+' must be an Astropy Quantity with explicit units')
    try:
        raw=np.asarray(value.to_value(unit))
        if raw.dtype.kind not in 'iuf':raise ValueError(name+' must contain real numeric values')
        return np.asarray(raw,float)
    except (u.UnitConversionError,TypeError,ValueError) as exc:raise ValueError(name+' has incompatible units') from exc


def _digest_array(value,dtype):
    array=np.ascontiguousarray(value,dtype=dtype)
    return sha256(str(array.shape).encode('ascii')+b'|'+array.tobytes()).hexdigest()


def inject_source_ramp(expected_source,gain,header,valid_mask,rng,*,gain_provenance,source_provenance=None,batch_pixels=4096):
    """Generate exact ideal source-only ramp slope and its additive variance.

    ``expected_source``: 2D Quantity convertible to MJy/sr.
    ``gain``: positive scalar or matching-shape Quantity convertible to
    (MJy/sr)/(electron/s). Only valid pixels are processed; invalid output is NaN.
    """
    config=_header_values(header)
    if not isinstance(rng,np.random.Generator):raise ValueError('explicit numpy Generator required')
    if isinstance(batch_pixels,(bool,np.bool_)) or not isinstance(batch_pixels,Integral) or not 1<=batch_pixels<=MAX_BATCH_PIXELS:
        raise ValueError('batch_pixels must be an integer in supported range')
    if not isinstance(gain_provenance,Mapping) or not isinstance(gain_provenance.get('source'),str) or not gain_provenance['source'].strip():
        raise ValueError('gain_provenance must identify its source')
    if source_provenance is not None and not isinstance(source_provenance,Mapping):raise ValueError('source_provenance must be a mapping')
    gain_provenance=_jsonable(dict(gain_provenance));source_provenance=_jsonable(dict(source_provenance or {}))
    try:json.dumps([gain_provenance,source_provenance],allow_nan=False)
    except (ValueError,TypeError) as exc:raise ValueError('provenance must contain JSON-safe values') from exc
    source=_quantity_values(expected_source,SOURCE_UNIT,'expected_source')
    if source.ndim!=2 or not source.size:raise ValueError('expected_source must be a nonempty 2D image')
    mask=np.asarray(valid_mask)
    if mask.dtype!=np.dtype(bool) or mask.shape!=source.shape:raise ValueError('valid_mask must be a same-shape boolean image')
    gain_values=_quantity_values(gain,GAIN_UNIT,'gain')
    if gain_values.shape==():gain_values=np.broadcast_to(gain_values,source.shape)
    elif gain_values.shape!=source.shape:raise ValueError('gain must be scalar or exactly match image shape')
    if np.any(~np.isfinite(source[mask])) or np.any(source[mask]<0):raise ValueError('source must be finite and nonnegative on valid pixels')
    if np.any(~np.isfinite(gain_values[mask])) or np.any(gain_values[mask]<=0):raise ValueError('gain must be finite and positive on valid pixels')
    with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
        rates=source[mask]/gain_values[mask]
        poisson_mean=rates*config['TSAMP']
        variance=poisson_factor(config['n'])*gain_values[mask]*source[mask]/config['nominal_pipeline_integration_seconds']
    limit=float(np.iinfo(np.int64).max)-10*np.sqrt(float(np.iinfo(np.int64).max))
    if not np.isfinite(poisson_mean).all() or np.any(poisson_mean>limit) or not np.isfinite(variance).all():raise ValueError('source rate outside numerical range')
    before=_jsonable(copy.deepcopy(rng.bit_generator.state))
    indices=np.flatnonzero(mask.ravel());noise=np.full(source.size,np.nan);added=np.full(source.size,np.nan);var=np.full(source.size,np.nan)
    flat_source=source.ravel();flat_gain=np.ascontiguousarray(gain_values).ravel()
    weights=increment_weights(config['n'],config['TSAMP'])
    # Scratch storage scales with batch_pixels rather than n_reads*image_size.
    for offset in range(0,len(indices),int(batch_pixels)):
        selected=indices[offset:offset+int(batch_pixels)]
        rate=flat_source[selected]/flat_gain[selected];lam=rate*config['TSAMP']
        slope_noise=np.zeros(len(selected),float)
        for weight in weights:slope_noise+=weight*(rng.poisson(lam).astype(float)-lam)
        delta=flat_gain[selected]*slope_noise
        if not np.isfinite(delta).all() or not np.isfinite(flat_source[selected]+delta).all():raise ValueError('generated signal outside numerical range')
        noise[selected]=delta;added[selected]=flat_source[selected]+delta
        var[selected]=poisson_factor(config['n'])*flat_gain[selected]*flat_source[selected]/config['nominal_pipeline_integration_seconds']
    provenance={'version':'ideal-source-ramp.1','header':config,'source_unit':str(SOURCE_UNIT),'gain_unit':str(GAIN_UNIT),
        'input_source_unit':str(expected_source.unit),'input_gain_unit':str(gain.unit),
        'variance_unit':str(SOURCE_UNIT**2),'source_provenance':source_provenance,'gain_provenance':gain_provenance,
        'source_values_sha256':_digest_array(source,'<f8'),'gain_values_sha256':_digest_array(gain_values,'<f8'),
        'valid_mask_sha256':_digest_array(mask,'u1'),'valid_pixels':int(mask.sum()),'shape':list(source.shape),
        'rng_bit_generator':type(rng.bit_generator).__name__,'rng_state_before':before,
        'rng_state_after':_jsonable(copy.deepcopy(rng.bit_generator.state)),'batch_pixels':int(batch_pixels),
        'pipeline_source_url':PIPELINE_SOURCE,'pipeline_source_blob_sha1':PIPELINE_BLOB_SHA1,
        'assumptions':'ideal independent source-only Poisson increments, uniform non-destructive samples and unweighted linear ramp slope; no detector or sky noise',
        'limitations':'not valid for partial ramps, nonlinear response, crosstalk, PSF uncertainty or unverified calibration alignment'}
    return {'added_image':added.reshape(source.shape)*SOURCE_UNIT,'source_noise':noise.reshape(source.shape)*SOURCE_UNIT,
            'added_variance':var.reshape(source.shape)*SOURCE_UNIT**2,'valid_mask':mask.copy(),'provenance':provenance}
