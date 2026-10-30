"""Per-exposure SPHEREx absolute timing and tangent-plane GLS design.

This module is a computational building block, not an astrometric measurement.
Coordinates are tangent-plane arcsec and rates are arcsec per Julian year TDB.
"""
from __future__ import annotations
from dataclasses import dataclass
from numbers import Real
import numpy as np
import astropy.units as u
from astropy.coordinates import get_body_barycentric
from astropy.time import Time
from scipy.linalg import solve_triangular

TIME_SCALES={'utc','tai','tt','tdb','tcg','tcb'}
MJD_ABSOLUTE_RANGE=(40000.,100000.)
MIDPOINT_TOLERANCE_SECONDS=1.0
DATE_TOLERANCE_SECONDS=.005
DEFAULT_MAX_CONDITION=1000.


class TimeMetadataError(ValueError):
    """Missing, inconsistent, or ambiguous absolute exposure time."""


class UnidentifiableDesign(ValueError):
    """Model has insufficient degrees of freedom, rank, or conditioning."""
    def __init__(self,reason,diagnostics):
        super().__init__(reason);self.reason=reason;self.diagnostics=diagnostics


@dataclass(frozen=True)
class ExposureTime:
    start: Time
    midpoint: Time
    end: Time
    input_scale: str

    def metadata(self):
        return {'input_scale':self.input_scale,'start_mjd_absolute':float(self.start.mjd),
                'midpoint_mjd_absolute':float(self.midpoint.mjd),'end_mjd_absolute':float(self.end.mjd),
                'midpoint_mjd_tdb':float(self.midpoint.tdb.mjd),
                'duration_seconds':float((self.end.tai-self.start.tai).to_value(u.s)),
                'ephemeris':'astropy builtin Earth barycentric ICRS; spacecraft position not added'}


def _number(header,key):
    value=header.get(key)
    if isinstance(value,(bool,np.bool_)) or not isinstance(value,Real) or not np.isfinite(value):
        raise TimeMetadataError('Missing or invalid numeric '+key)
    return float(value)


def parse_image_header(header):
    """Parse absolute MJD date keywords, never adding MJDREF or TIMEZERO.

    Scope is SPHEREx-era absolute MJD, not generic relative FITS time axes.
    DATE-* values, when supplied, must agree with the stated scale and MJD.
    """
    if str(header.get('EXTNAME','')).strip().upper()!='IMAGE':raise TimeMetadataError('Expected IMAGE header')
    scale=header.get('TIMESYS')
    if not isinstance(scale,str) or scale.strip().lower() not in TIME_SCALES:raise TimeMetadataError('Missing or unsupported TIMESYS')
    scale=scale.strip().lower()
    for key in ['MJD-BEG','MJD-AVG','MJD-END','TIMESYS','MJDREF','MJDREFI','MJDREFF','TIMEZERO','TIMEOFFS']:
        if hasattr(header,'cards') and sum(c.keyword.upper()==key for c in header.cards)>1:raise TimeMetadataError('Duplicate '+key)
    references={k:_number(header,k) for k in ['MJDREF','MJDREFI','MJDREFF'] if k in header}
    if 'MJDREF' in references and any(k in references for k in ['MJDREFI','MJDREFF']):
        split=references.get('MJDREFI',0.)+references.get('MJDREFF',0.)
        if not np.isclose(references['MJDREF'],split,rtol=0.,atol=1e-12):raise TimeMetadataError('Conflicting MJDREF forms')
    for key in ['TIMEZERO','TIMEOFFS']:
        if key in header and _number(header,key)!=0:raise TimeMetadataError('Nonzero '+key+' is ambiguous for absolute MJD')
    tref=header.get('TREFPOS')
    if tref is not None and str(tref).strip().upper() not in {'TOPOCENTER','GEOCENTER'}:
        raise TimeMetadataError('Unsupported TREFPOS for observation timestamp')
    vals=[_number(header,k) for k in ['MJD-BEG','MJD-AVG','MJD-END']]
    if not all(MJD_ABSOLUTE_RANGE[0]<=x<=MJD_ABSOLUTE_RANGE[1] for x in vals):
        raise TimeMetadataError('Absolute MJD outside declared SPHEREx-era range')
    start,mid,end=[Time(x,format='mjd',scale=scale) for x in vals]
    if not start.tai<mid.tai<end.tai:raise TimeMetadataError('Expected MJD-BEG < MJD-AVG < MJD-END')
    interval=(end.tai-start.tai).to_value(u.s);offset=(mid.tai-start.tai).to_value(u.s)
    if abs(offset-interval/2)>MIDPOINT_TOLERANCE_SECONDS:raise TimeMetadataError('MJD-AVG inconsistent with exposure midpoint')
    for key,t in [('DATE-BEG',start),('DATE-AVG',mid),('DATE-END',end)]:
        if key in header:
            value=header[key]
            if not isinstance(value,str):raise TimeMetadataError('Invalid '+key)
            try:parsed=Time(value.strip(),format='isot',scale=scale)
            except (ValueError,TypeError) as exc:raise TimeMetadataError('Invalid '+key) from exc
            if abs((parsed.tai-t.tai).to_value(u.s))>DATE_TOLERANCE_SECONDS:raise TimeMetadataError(key+' conflicts with MJD')
    return ExposureTime(start,mid,end,scale)


def spacecraft_parallax_bound(header,assumed_parallax_arcsec):
    """Bound using coordinate magnitude only; unknown orientation is never used."""
    if isinstance(assumed_parallax_arcsec,(bool,np.bool_)) or not isinstance(assumed_parallax_arcsec,Real) or not np.isfinite(assumed_parallax_arcsec) or assumed_parallax_arcsec<0:
        raise ValueError('assumed parallax must be finite, nonnegative arcsec')
    if str(header.get('XYZ_SC_SYSTEM','')).strip().upper()!='GEOCENTER':
        return {'available':False,'reason':'missing_or_non_geocentric_spacecraft_origin'}
    try:xyz=np.array([_number(header,k) for k in ['X_SC','Y_SC','Z_SC']])
    except TimeMetadataError:return {'available':False,'reason':'missing_or_invalid_spacecraft_coordinates'}
    radius=float(np.linalg.norm(xyz));bound=radius/u.au.to(u.km)*float(assumed_parallax_arcsec)
    return {'available':True,'radius_km':radius,'assumed_parallax_arcsec':float(assumed_parallax_arcsec),
            'bound_arcsec':bound,'assumptions':'header values are km in an orthonormal Cartesian geocentric frame; orientation not used',
            'interpretation':'maximum first-order angular error from omitted spacecraft position, not an uncertainty or fitted correction'}


def tangent_basis(ra_deg,dec_deg):
    if not np.isfinite([ra_deg,dec_deg]).all() or not -90<=dec_deg<=90:raise ValueError('invalid ICRS direction')
    a=np.deg2rad(ra_deg%360.);d=np.deg2rad(dec_deg)
    east=np.array([-np.sin(a),np.cos(a),0.])
    north=np.array([-np.sin(d)*np.cos(a),-np.sin(d)*np.sin(a),np.cos(d)])
    return east,north


def parallax_factors(ra_deg,dec_deg,earth_barycentric_au):
    """Observer parallax on east,north axes, dimensionless per arcsec parallax."""
    position=np.asarray(earth_barycentric_au,float)
    if position.ndim!=2 or position.shape[1]!=3 or not np.isfinite(position).all():raise ValueError('Earth positions must be finite N x 3 AU')
    east,north=tangent_basis(ra_deg,dec_deg)
    return -np.column_stack([position@east,position@north])


def earth_barycentric_au(times):
    if not times or not all(isinstance(t,Time) and t.isscalar for t in times):raise ValueError('scalar Astropy Time list required')
    return np.array([get_body_barycentric('earth',t.tdb,ephemeris='builtin').xyz.to_value(u.au) for t in times])


def design_matrix(times,reference,ra_deg,dec_deg,model):
    """Rows ordered east,north per exposure; use full Earth factors without SC."""
    if model not in {'pm_only','pm_parallax'}:raise ValueError('select pm_only or pm_parallax explicitly')
    if not isinstance(reference,Time) or not reference.isscalar:raise ValueError('reference must be scalar Astropy Time')
    positions=earth_barycentric_au(times)
    dt=np.array([(t.tdb-reference.tdb).to_value(u.day)/365.25 for t in times])
    p=parallax_factors(ra_deg,dec_deg,positions);n=len(times);cols=5 if model=='pm_parallax' else 4
    a=np.zeros((2*n,cols));a[0::2,0]=1;a[1::2,1]=1;a[0::2,2]=dt;a[1::2,3]=dt
    if cols==5:a[0::2,4]=p[:,0];a[1::2,4]=p[:,1]
    return a,{'model':model,'reference_mjd_tdb':float(reference.tdb.mjd),'input_time_scales':[t.scale for t in times],
        'fit_time_scale':'tdb','years':'365.25 TDB days','ephemeris':'builtin','position_frame':'ICRS barycentric',
        'axes':'east = ΔRA cos(dec), north = Δdec; origin at supplied ICRS direction',
        'parameters':['east0_arcsec','north0_arcsec','mu_east_arcsec_per_year','mu_north_arcsec_per_year']+(['parallax_arcsec'] if cols==5 else []),
        'earth_barycentric_au':positions.tolist(),'parallax_factors_east_north':p.tolist()}


def _spd(covariance,size):
    c=np.asarray(covariance,float)
    if size<=0 or c.shape!=(size,size) or not np.isfinite(c).all():raise ValueError('covariance must be finite, symmetric and correctly sized')
    diagonal=np.diag(c)
    if np.any(diagonal<=0):raise ValueError('covariance must be positive definite')
    std=np.sqrt(diagonal)
    with np.errstate(over='ignore',divide='ignore',invalid='ignore'):
        normalized=(c/std[:,None])/std[None,:]
    if not np.isfinite(normalized).all():raise ValueError('covariance must be finite, symmetric and correctly sized')
    symmetry_tolerance=64*np.finfo(float).eps*size*float(np.max(np.abs(normalized)))
    if np.max(np.abs(normalized-normalized.T))>symmetry_tolerance:raise ValueError('covariance must be finite, symmetric and correctly sized')
    # Only roundoff-scale asymmetry is symmetrized, before Cholesky.
    c=c*.5+c.T*.5
    try:chol=np.linalg.cholesky(c)
    except np.linalg.LinAlgError as exc:raise ValueError('covariance must be positive definite') from exc
    return c,chol


def inspect_design(matrix,covariance,max_condition=DEFAULT_MAX_CONDITION):
    a=np.asarray(matrix,float)
    if a.ndim!=2 or not np.isfinite(a).all() or a.shape[1] not in (4,5) or a.shape[0]%2:raise ValueError('invalid astrometric design matrix')
    if not np.isfinite(max_condition) or max_condition<=1:raise ValueError('max_condition must exceed 1')
    cov,L=_spd(covariance,a.shape[0]);aw=solve_triangular(L,a,lower=True)
    scales=np.linalg.norm(aw,axis=0);dof=a.shape[0]-a.shape[1]
    if np.any(scales<=0):
        keep=scales>0
        rank=int(np.linalg.matrix_rank(aw[:,keep]/scales[keep])) if np.any(keep) else 0
        return {'rank':rank,'condition':None,'dof':dof,'reason':'zero_design_column'}
    singular=np.linalg.svd(aw/scales,compute_uv=False)
    tolerance=np.finfo(float).eps*max(a.shape)*singular[0]
    rank=int(np.sum(singular>tolerance));cond=float(singular[0]/singular[-1]) if rank==a.shape[1] and len(singular)==a.shape[1] else None
    reason='zero_or_negative_degrees_of_freedom' if dof<=0 else ('rank_deficient' if rank<a.shape[1] else ('ill_conditioned' if cond>max_condition else None))
    return {'rank':rank,'condition':cond,'dof':dof,'singular_values_scaled':singular.tolist(),
            'column_norms_whitened':scales.tolist(),'max_condition':float(max_condition),'reason':reason}


def fit_gls(matrix,observations,covariance,max_condition=DEFAULT_MAX_CONDITION):
    a=np.asarray(matrix,float);diagnostics=inspect_design(a,covariance,max_condition)
    if diagnostics['reason']:raise UnidentifiableDesign(diagnostics['reason'],diagnostics)
    y=np.asarray(observations,float)
    if y.shape!=(a.shape[0],) or not np.isfinite(y).all():raise ValueError('observations must be a finite 2N vector')
    c,L=_spd(covariance,a.shape[0]);aw=solve_triangular(L,a,lower=True);yw=solve_triangular(L,y,lower=True)
    scales=np.asarray(diagnostics['column_norms_whitened']);U,s,Vt=np.linalg.svd(aw/scales,full_matrices=False)
    gain_scaled=(Vt.T/s)@U.T@solve_triangular(L,np.eye(len(y)),lower=True)
    gain=gain_scaled/scales[:,None];beta=gain@y
    parameter_covariance=(Vt.T/s**2)@Vt/np.outer(scales,scales)
    residual=y-a@beta;whitened=solve_triangular(L,residual,lower=True)
    return {'parameters':beta,'parameter_covariance':parameter_covariance,'chi2':float(whitened@whitened),
            'dof':diagnostics['dof'],'design_diagnostics':diagnostics,'gain':gain,'training_covariance':c,
            'qualification':'GLS conditional on supplied full covariance; no chi-square inflation or physical-systematics guarantee'}


def predict(fit,new_matrix,new_observation_covariance=None,train_new_covariance=None):
    b=np.asarray(new_matrix,float);beta=np.asarray(fit['parameters']);C=np.asarray(fit['parameter_covariance'])
    if b.ndim!=2 or b.shape[0]==0 or b.shape[1]!=len(beta) or b.shape[0]%2 or not np.isfinite(b).all():raise ValueError('invalid prediction design')
    result={'mean':b@beta,'fitted_mean_covariance':b@C@b.T}
    if train_new_covariance is not None and new_observation_covariance is None:raise ValueError('new observation covariance required for cross-covariance')
    if new_observation_covariance is not None:
        new,_=_spd(new_observation_covariance,b.shape[0]);train=np.asarray(fit['training_covariance'])
        if train.ndim!=2 or train.shape[0]!=train.shape[1]:raise ValueError('invalid training covariance')
        train,_=_spd(train,train.shape[0])
        cross=np.zeros((train.shape[0],b.shape[0])) if train_new_covariance is None else np.asarray(train_new_covariance,float)
        if cross.shape!=(train.shape[0],b.shape[0]) or not np.isfinite(cross).all():raise ValueError('invalid train/new cross-covariance')
        joint=np.block([[train,cross],[cross.T,new]])
        # Normalize by marginal standard deviations before the PSD test. This
        # makes the roundoff allowance dimensionless and independent of units.
        std=np.sqrt(np.diag(joint))
        with np.errstate(over='ignore',divide='ignore',invalid='ignore'):
            correlation=(joint/std[:,None])/std[None,:]
        if not np.isfinite(correlation).all():raise ValueError('joint train/new covariance must be positive semidefinite')
        ev=np.linalg.eigvalsh(correlation*.5+correlation.T*.5)
        eigen_scale=float(np.max(np.abs(ev)))
        if not np.isfinite(eigen_scale) or eigen_scale==0:raise ValueError('joint train/new covariance must be positive semidefinite')
        relative_tolerance=64*np.finfo(float).eps*len(joint)*eigen_scale
        if ev.min() < -relative_tolerance:raise ValueError('joint train/new covariance must be positive semidefinite')
        joint_term=b@fit['gain']@cross
        covariance=new+result['fitted_mean_covariance']-joint_term-joint_term.T
        covariance=covariance*.5+covariance.T*.5
        if not np.isfinite(covariance).all():raise ValueError('prediction residual covariance must be finite')
        scale=max(float(np.max(np.abs(new))),float(np.max(np.abs(result['fitted_mean_covariance']))),float(np.max(np.abs(joint_term))))
        if not np.isfinite(scale) or scale<=0:raise ValueError('invalid prediction covariance scale')
        min_relative=float(np.linalg.eigvalsh(covariance/scale).min())
        residual_tolerance=64*np.finfo(float).eps*len(joint)
        if min_relative < -residual_tolerance:raise ValueError('prediction residual covariance must be positive semidefinite')
        adjustment=0.
        if min_relative<0:
            # A recorded diagonal adjustment covers cancellation-scale roundoff;
            # it is never used to repair a materially invalid cross-covariance.
            adjustment=float((-min_relative+8*np.finfo(float).eps*len(joint))*scale)
            covariance=covariance+np.eye(len(covariance))*adjustment
        if np.linalg.eigvalsh(covariance/scale).min()<0:raise ValueError('unable to obtain a PSD prediction residual covariance at roundoff precision')
        result['prediction_residual_covariance']=covariance
        result['prediction_residual_psd_roundoff_adjustment_arcsec2']=adjustment
        result['prediction_residual_psd_tolerance_arcsec2']=float(residual_tolerance*scale)
        result['qualification']='Unconditional y_new minus fitted mean; cross-covariance included, no conditional kriging correction.'
    return result
