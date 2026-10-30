"""Independent synthetic scene: pixel-integrated Gaussian and ideal ramp.

This axis-aligned Gaussian is a deliberately different PSF family from the
ePSF fitter; it is not a validated SPHEREx instrument PSF. No stamp or mask
normalization is applied. The diagonal Gaussian background is only a declared
control model, and oracle source variance is not an observed-data estimator.
"""
from collections.abc import Mapping
import copy
from hashlib import sha256
import json
import math

from astropy import units as u
import numpy as np
from scipy.special import ndtr

from . import source_ramp_noise as ramp


SURFACE=u.MJy/u.sr
GAIN=(u.MJy/u.sr)/(u.electron/u.s)
_MAX_COORDINATE=2**50
_MAX_SIGMA=1e12


def _numeric(value,name,ndim):
    if isinstance(value,u.Quantity):raise ValueError(name+' must be numeric in declared native units')
    a=np.asarray(value)
    if a.ndim!=ndim or a.dtype.kind not in 'iuf':raise ValueError(name+' must be real numeric')
    a=np.asarray(a,float)
    if not np.isfinite(a).all():raise ValueError(name+' must be finite')
    return a


def _quantity(value,unit,name,ndim):
    if not isinstance(value,u.Quantity):raise ValueError(name+' must be an explicit Quantity')
    try:a=value.to_value(unit)
    except (TypeError,ValueError,u.UnitConversionError) as exc:raise ValueError(name+' has incompatible units') from exc
    return _numeric(a,name,ndim)


def _pixels(x,y):
    x=_numeric(x,'x',1);y=_numeric(y,'y',1)
    if (not len(x) or x.shape!=y.shape or np.any(x!=np.rint(x)) or np.any(y!=np.rint(y))
            or np.any(np.abs(x)>_MAX_COORDINATE) or np.any(np.abs(y)>_MAX_COORDINATE)):
        raise ValueError('pixel coordinates must be nonempty matching exact native integers')
    if len(np.unique(np.column_stack((x,y)),axis=0))!=len(x):raise ValueError('duplicate pixel coordinates')
    return x,y


def _axis_fraction(center,position,sigma):
    # Reflect positive tails to prevent subtracting two CDFs rounded to 1.
    with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
        lower=(center-.5-position)/sigma;upper=(center+.5-position)/sigma
        value=np.where(lower>0,ndtr(-lower)-ndtr(-upper),ndtr(upper)-ndtr(lower))
    if not np.isfinite(value).all() or np.any(value<0) or np.any(value>1):
        raise ValueError('Gaussian integral outside numerical range')
    return value


def gaussian_pixel_fractions(x,y,*,source_xy,sigma_x,sigma_y):
    """Integrate an axis-aligned unit 2D Gaussian over exact native pixels.

    x/y are unique integer pixel centers; source_xy and sigma_x/y use native
    pixel units. Finite subsets are never renormalized. Very far tails can
    underflow to zero, and widths >1e12 pixels are rejected to avoid lost
    central CDF differences. Coordinates are bounded for exact pixel edges.
    """
    x,y=_pixels(x,y)
    pos=_numeric(source_xy,'source_xy',1)
    if pos.shape!=(2,) or np.any(np.abs(pos)>_MAX_COORDINATE):raise ValueError('invalid source_xy')
    widths=[]
    for value in (sigma_x,sigma_y):
        a=_numeric(value,'sigma',0)
        if a<=0 or a>_MAX_SIGMA:raise ValueError('sigma must be positive and numerically resolvable')
        widths.append(float(a))
    fraction=_axis_fraction(x,pos[0],widths[0])*_axis_fraction(y,pos[1],widths[1])
    if not np.isfinite(fraction).all() or np.any(fraction<0):raise ValueError('invalid Gaussian fraction')
    return fraction


def expected_scene(sources,x,y,pixel_omega):
    """Return expected brightness and finite-window flux accounting.

    Each source dict has exactly native_xy, sigma_xy, and nonnegative scalar
    flux Quantity convertible to Jy. pixel_omega is a positive, matching vector
    Quantity in sr; it may vary across the window. Reported missing fraction is
    zero if a summed fraction exceeds one only by floating-point roundoff;
    per-pixel fractions are never changed or renormalized.
    """
    x,y=_pixels(x,y)
    omega=_quantity(pixel_omega,u.sr,'pixel_omega',1)
    if omega.shape!=x.shape or np.any(omega<=0):raise ValueError('pixel_omega must be positive and match pixels')
    if not isinstance(sources,(list,tuple)):raise ValueError('sources must be a sequence')
    image=np.zeros(len(x));results=[]
    for source in sources:
        if not isinstance(source,dict) or set(source)!={'native_xy','sigma_xy','flux'}:raise ValueError('source fields invalid')
        flux=_quantity(source['flux'],u.Jy,'flux',0)
        if flux<0:raise ValueError('source flux must be nonnegative')
        sigma=_numeric(source['sigma_xy'],'sigma_xy',1)
        if sigma.shape!=(2,):raise ValueError('sigma_xy must have two components')
        fractions=gaussian_pixel_fractions(x,y,source_xy=source['native_xy'],sigma_x=sigma[0],sigma_y=sigma[1])
        fraction_sum=float(math.fsum(map(float,fractions)))
        if not np.isfinite(fraction_sum) or fraction_sum>1+1e-12:raise ValueError('finite-window fraction exceeds one')
        selected=min(1.,fraction_sum);missing=max(0.,1.-fraction_sum)
        with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
            increment=float(flux)*fractions/(1e6*omega)
            image+=increment
        if not np.isfinite(image).all() or np.any((fractions>0)&(flux>0)&(increment==0)):
            raise ValueError('source brightness outside numerical range')
        results.append({'native_xy':_numeric(source['native_xy'],'native_xy',1).tolist(),
            'sigma_xy_native_pixels':sigma.tolist(),'flux_jy':float(flux),
            'selected_fraction':selected,'selected_fraction_float_sum':fraction_sum,
            'missing_fraction':missing,'selected_flux_jy':float(flux)*selected,
            'missing_flux_jy':float(flux)*missing})
    return {'expected_source':image*SURFACE,'per_source':results,
            'unit_metadata':{'pixel_coordinates':'zero-based native pixel centers','sigma':'native pixels',
                             'flux':'Jy','pixel_omega':'sr','brightness':'MJy/sr'},
            'qualification':'axis-aligned pixel-integrated Gaussian synthetic PSF, not instrument PSF truth; no window normalization'}


def _provenance(value,name):
    if not isinstance(value,Mapping) or not isinstance(value.get('source'),str) or not value['source'].strip():
        raise ValueError(name+' must be a mapping identifying source')
    try:
        result=json.loads(json.dumps(dict(value),allow_nan=False))
    except (ValueError,TypeError) as exc:raise ValueError(name+' must be JSON-safe') from exc
    return result


def _digest(values):
    array=np.ascontiguousarray(values,dtype='<f8')
    return sha256(str(array.shape).encode('ascii')+b'|'+array.tobytes()).hexdigest()


def draw_scene(expected_source,background,background_error,gain,header,rng,*,gain_provenance,source_provenance):
    """Draw source-only Poisson ramp plus independent Gaussian background.

    All four input vectors are matching Astropy Quantities and every pixel is
    selected. ``background`` is a deterministic mean, not an already-noisy
    image; the routine draws one independent Gaussian realization. The output
    error uses oracle expected-source variance, not an observed-data estimator.
    """
    source=_quantity(expected_source,SURFACE,'expected_source',1)
    bg=_quantity(background,SURFACE,'background',1)
    bg_error=_quantity(background_error,SURFACE,'background_error',1)
    g=_quantity(gain,GAIN,'gain',1)
    if not len(source) or bg.shape!=source.shape or bg_error.shape!=source.shape or g.shape!=source.shape:
        raise ValueError('all scene vectors must match')
    if np.any(source<0) or np.any(bg_error<=0) or np.any(g<=0):raise ValueError('invalid source, error or gain')
    if not isinstance(rng,np.random.Generator):raise ValueError('explicit numpy Generator required')
    gain_provenance=_provenance(gain_provenance,'gain_provenance')
    source_provenance=_provenance(source_provenance,'source_provenance')
    before=copy.deepcopy(rng.bit_generator.state)
    shot=ramp.inject_source_ramp(source[None,:]*SURFACE,g[None,:]*GAIN,header,np.ones((1,len(source)),bool),rng,
        gain_provenance=gain_provenance,source_provenance=source_provenance)
    source_noise=shot['source_noise'].to_value(SURFACE).reshape(-1)
    variance=shot['added_variance'].to_value(SURFACE**2).reshape(-1)
    background_noise=rng.normal(0.,bg_error)
    with np.errstate(over='ignore',invalid='ignore'):
        expected=source+bg;data=expected+source_noise+background_noise
        total_error=np.hypot(bg_error,np.sqrt(variance))
    if not np.isfinite(expected).all() or not np.isfinite(data).all() or not np.isfinite(total_error).all() or np.any(total_error<=0):
        raise ValueError('scene realization outside numerical range')
    provenance={'version':'independent-gaussian-scene.1','rng_bit_generator':type(rng.bit_generator).__name__,
        'rng_state_before':ramp._jsonable(before),'rng_state_after':ramp._jsonable(copy.deepcopy(rng.bit_generator.state)),
        'source_ramp':shot['provenance'],'gain_provenance':gain_provenance,'source_provenance':source_provenance,
        'pixels':len(source),'background_values_sha256':_digest(bg),'background_error_values_sha256':_digest(bg_error),
        'source_unit':str(SURFACE),'background_unit':str(SURFACE),'background_error_unit':str(SURFACE),'gain_unit':str(GAIN),
        'qualification':'oracle source-noise variance and independent Gaussian background control; not an observed-data error estimate, real detector model, or instrument PSF validation'}
    return {'data':data*SURFACE,'expected_mean':expected*SURFACE,'error':total_error*SURFACE,
            'background_noise':background_noise*SURFACE,'source_noise':source_noise*SURFACE,
            'added_variance':variance*SURFACE**2,'provenance':provenance}
