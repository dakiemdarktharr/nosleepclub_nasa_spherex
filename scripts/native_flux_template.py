"""Conditional native point-source template, using Tractor's center-Ω rule.

The caller supplies an ePSF, a source-position solid angle and provenance.
The padded spline is normalized on its entire integer lattice before selecting
the caller's mask. This defines a numerical template, not physical PSF truth,
a calibrated color convention, or a validation of the ePSF's missing wings.
"""
from dataclasses import dataclass
from numbers import Integral

from astropy import units as u
import numpy as np
from scipy.ndimage import map_coordinates, spline_filter

PAD_OVERSAMPLED=16
EPSF_SHAPE=(33,33)


@dataclass(frozen=True)
class NativeFluxTemplate:
    x: np.ndarray
    y: np.ndarray
    normalized_selected: np.ndarray
    template_per_jy: u.Quantity
    lattice_x: np.ndarray
    lattice_y: np.ndarray
    normalized_lattice: np.ndarray
    native_sum_before_normalization: float
    signed_selected_sum: float
    source_omega_sr: float
    source_omega_provenance: str
    epsf_provenance: str
    support_truncated_by_image: bool


def _positive_integer(value,name):
    if isinstance(value,(bool,np.bool_)) or not isinstance(value,Integral) or not 1<=value<=1024:
        raise ValueError(name+' must be an integer between 1 and 1024')
    return int(value)


def native_flux_template(epsf, *, oversampling_x, oversampling_y, source_xy,
                         selection_mask, source_omega, source_omega_provenance,
                         epsf_provenance):
    """Return native PSF fractions and template in (MJy/sr)/Jy.

    The sole geometric approximation here is Ω_source applied uniformly over
    the PSF patch, matching the published Tractor conversion convention. The
    native integer lattice is evaluated over the full finite zero-padded spline
    support, including points outside the image; a mask never defines its
    normalization. x/y are zero-based image coordinates; WCS and masks must be
    resolved and validated by the caller. No color correction is supplied.
    """
    for key,value in [('source_omega_provenance',source_omega_provenance),('epsf_provenance',epsf_provenance)]:
        if not isinstance(value,str) or not value.strip():raise ValueError(key+' must be supplied')
    ox=_positive_integer(oversampling_x,'oversampling_x')
    oy=_positive_integer(oversampling_y,'oversampling_y')
    if ox!=oy:raise ValueError('square and equally oversampled ePSF required')
    a=np.asarray(epsf)
    if a.shape!=EPSF_SHAPE or a.dtype.kind not in 'iuf':raise ValueError('ePSF must be a real 33x33 array')
    a=np.asarray(a,dtype=float)
    if not np.isfinite(a).all():raise ValueError('ePSF must be finite')
    raw_sum=float(a.sum());raw_abs=float(np.abs(a).sum())
    if not np.isfinite([raw_sum,raw_abs]).all() or raw_sum<=64*np.finfo(float).eps*raw_abs:
        raise ValueError('ePSF sum must be positive and numerically stable')
    mask=np.asarray(selection_mask)
    if mask.ndim!=2 or mask.size==0 or mask.dtype!=np.dtype(bool) or not mask.any():
        raise ValueError('selection mask must be a nonempty 2D boolean mask')
    pos=np.asarray(source_xy)
    if pos.shape!=(2,) or pos.dtype.kind not in 'iuf' or not np.isfinite(pos).all():
        raise ValueError('source_xy must be finite real x,y')
    x0,y0=map(float,pos)
    if not (0<=x0<=mask.shape[1]-1 and 0<=y0<=mask.shape[0]-1):
        raise ValueError('source position outside image')
    if not isinstance(source_omega,u.Quantity):raise ValueError('solid angle must be an explicit Quantity')
    try:omega=source_omega.to_value(u.sr)
    except (u.UnitConversionError,TypeError,ValueError) as exc:raise ValueError('solid angle must have angle-squared units') from exc
    if np.shape(omega)!=() or not np.isfinite(omega) or omega<=0:raise ValueError('solid angle must be a positive finite scalar')
    omega=float(omega)
    with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
        normalized_raw=(a/raw_sum)*float(ox)**2
    if not np.isfinite(normalized_raw).all():raise ValueError('ePSF scale outside numerical range')
    coefficients=spline_filter(np.pad(normalized_raw,PAD_OVERSAMPLED),order=3)
    if not np.isfinite(coefficients).all():raise ValueError('spline coefficients invalid')
    center=(coefficients.shape[0]-1)/2
    radius=center/ox
    # Include an exterior integer on each side when necessary.  Sampling there
    # returns zero, and avoids dropping an endpoint due to rounding of radius.
    lattice_x=np.arange(int(np.floor(x0-radius)),int(np.ceil(x0+radius))+1,dtype=np.int64)
    lattice_y=np.arange(int(np.floor(y0-radius)),int(np.ceil(y0+radius))+1,dtype=np.int64)
    if not len(lattice_x) or not len(lattice_y):raise ValueError('no native lattice support')
    X,Y=np.meshgrid(lattice_x,lattice_y)
    lattice=map_coordinates(coefficients,[(Y-y0)*oy+center,(X-x0)*ox+center],
                            order=3,mode='constant',cval=0.,prefilter=False)
    integral=float(lattice.sum());absolute=float(np.abs(lattice).sum())
    # The second scale detects a lattice consisting solely of interpolation
    # roundoff, even if its signed sum happens to have little cancellation.
    scale=max(absolute,raw_abs/raw_sum)
    if not np.isfinite([integral,absolute,scale]).all() or integral<=64*np.finfo(float).eps*scale:
        raise ValueError('native lattice integral must be positive and numerically stable')
    lattice=lattice/integral
    if not np.isfinite(lattice).all() or not np.isclose(lattice.sum(),1.,rtol=1e-12,atol=0):
        raise ValueError('native lattice normalization failed')
    y,x=np.nonzero(mask)
    selected=map_coordinates(coefficients,[(y-y0)*oy+center,(x-x0)*ox+center],
                             order=3,mode='constant',cval=0.,prefilter=False)/integral
    if not np.isfinite(selected).all() or not np.any(selected!=0):
        raise ValueError('mask has no finite nonzero template support')
    with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
        surface_per_jy=selected/(1e6*omega)
    if not np.isfinite(surface_per_jy).all() or np.any((selected!=0)&(surface_per_jy==0)):
        raise ValueError('template unit conversion outside numerical range')
    outside=(X<0)|(Y<0)|(X>=mask.shape[1])|(Y>=mask.shape[0])
    truncated=bool(np.any(outside & (lattice!=0)))
    return NativeFluxTemplate(x,y,selected,surface_per_jy*(u.MJy/u.sr/u.Jy),lattice_x,lattice_y,lattice,
        integral,float(selected.sum()),omega,source_omega_provenance,epsf_provenance,truncated)
