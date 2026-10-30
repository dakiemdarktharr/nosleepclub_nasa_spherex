"""Fixed-position neighbor-flux profiling and bounded epoch position fitting.

This is a numerical primitive only. Data/error are numeric in one caller-
declared physical unit; background columns are dimensionless, target and
neighbor templates are data_unit/Jy. Only semantic neighbor fluxes may be
constrained; target fluxes and background coefficients remain signed. All
pixel errors are diagonal and frame/registration correlations are omitted.
No covariance, confidence interval, SNR, or scientific gate is produced.
"""
from numbers import Integral

import numpy as np
from astropy import units as u
from scipy.optimize import least_squares

from .constrained_linear_profile import profile_linear


BOUND = 2.5
STEP = .002
HUBER = 2.5
WEIGHT_TOLERANCE = .001
POSITION_TOLERANCE = .0001
RCOND = 1e-10
START_OFFSETS = tuple((x,y) for y in (-1.5,0.,1.5) for x in (-1.5,0.,1.5))


def _array(value, name, ndim):
    if isinstance(value,u.Quantity):raise ValueError(name+' must be numeric in the declared units')
    a=np.asarray(value)
    if a.ndim!=ndim or a.dtype.kind not in 'iuf':raise ValueError(name+' must be a real numeric array')
    a=np.asarray(a,float)
    if not np.isfinite(a).all():raise ValueError(name+' must be finite')
    return a


def _unit(value, name):
    if value is None:raise ValueError(name+' requires an explicit unit')
    try:return u.Unit(value)
    except (TypeError,ValueError) as exc:raise ValueError('invalid '+name) from exc


class NeighborEpochProblem:
    """Frame-wise linear profile at a common position; no data are loaded.

    Each sample has exactly obs_id, data, error, background_design,
    neighbor_design, neighbor_ids, neighbor_unit and renderer. Designs are numeric arrays;
    neighbor_unit must equal the declared data_unit/Jy with no implicit scale
    conversion. renderer(position) must return an n-vector Quantity convertible
    to data_unit/Jy. Coefficients of background columns use data_unit, while
    target and neighbor amplitudes use Jy. The same semantic native columns
    must be used for both constrained and unconstrained interventions.
    """
    def __init__(self,samples,*,data_unit,nonnegative_neighbors):
        self.data_unit=_unit(data_unit,'data_unit')
        if self.data_unit==u.one:raise ValueError('data_unit must be physical')
        if not isinstance(nonnegative_neighbors,bool):raise ValueError('nonnegative_neighbors must be boolean')
        if not isinstance(samples,(list,tuple)) or not samples:raise ValueError('nonempty frame list required')
        self.nonnegative_neighbors=nonnegative_neighbors
        self.frames=[];ids=set()
        required={'obs_id','data','error','background_design','neighbor_design','neighbor_ids','neighbor_unit','renderer'}
        for sample in samples:
            if not isinstance(sample,dict) or set(sample)!=required:raise ValueError('missing or unexpected frame fields')
            ident=sample['obs_id']
            if not isinstance(ident,str) or not ident.strip() or ident in ids:raise ValueError('unique nonempty obs_id required')
            ids.add(ident)
            data=_array(sample['data'],'data',1);error=_array(sample['error'],'error',1)
            background=_array(sample['background_design'],'background_design',2)
            neighbors=_array(sample['neighbor_design'],'neighbor_design',2)
            if (not len(data) or error.shape!=data.shape or np.any(error<=0)
                    or background.shape[0]!=len(data) or neighbors.shape[0]!=len(data)
                    or 1+background.shape[1]+neighbors.shape[1]>len(data)):
                raise ValueError('invalid frame dimensions or errors')
            if _unit(sample['neighbor_unit'],'neighbor_unit')!=self.data_unit/u.Jy:
                raise ValueError('neighbor_unit must exactly equal data_unit/Jy')
            neighbor_ids=sample['neighbor_ids']
            if (not isinstance(neighbor_ids,(list,tuple)) or len(neighbor_ids)!=neighbors.shape[1]
                    or any(not isinstance(x,str) or not x.strip() for x in neighbor_ids)
                    or len(set(neighbor_ids))!=len(neighbor_ids)):
                raise ValueError('neighbor_ids must uniquely identify every neighbor column')
            if not callable(sample['renderer']):raise ValueError('renderer must be callable')
            self.frames.append({'obs_id':ident,'data':data.copy(),'error':error.copy(),
                                'background':background.copy(),'neighbors':neighbors.copy(),
                                'neighbor_ids':tuple(neighbor_ids),'renderer':sample['renderer']})
        self.set_weights([np.ones_like(f['data']) for f in self.frames])

    def set_weights(self,weights):
        if not isinstance(weights,(list,tuple)) or len(weights)!=len(self.frames):raise ValueError('weights must match frames')
        checked=[]
        for f,w in zip(self.frames,weights):
            a=_array(w,'weights',1)
            if a.shape!=f['data'].shape or np.any(a<=0) or np.any(a>1):raise ValueError('weights must lie in (0,1]')
            checked.append(a.copy())
        self.weights=checked

    def profile(self,position):
        position=_array(position,'position',1)
        if position.shape!=(2,):raise ValueError('position must have two coordinates')
        frames=[];weighted=[]
        for f,weight in zip(self.frames,self.weights):
            rendered=f['renderer'](position.copy())
            if not isinstance(rendered,u.Quantity):raise ValueError('renderer must return a Quantity')
            try:target=_array(rendered.to_value(self.data_unit/u.Jy),'renderer output',1)
            except (TypeError,ValueError,u.UnitConversionError) as exc:raise ValueError('renderer output units or values invalid') from exc
            if target.shape!=f['data'].shape:raise ValueError('renderer output shape mismatch')
            n_background=f['background'].shape[1];n_neighbors=f['neighbors'].shape[1]
            common=np.column_stack((target,f['background']))
            if self.nonnegative_neighbors:
                free=common;bounded=f['neighbors']
            else:
                free=np.column_stack((common,f['neighbors']));bounded=np.empty((len(target),0))
            solved=profile_linear(f['data'],f['error'],free,bounded,weights=weight)
            b=solved['free_coefficients'];target_flux=float(b[0]);background=b[1:1+n_background].copy()
            neighbor_flux=(solved['nonnegative_coefficients'] if self.nonnegative_neighbors else b[1+n_background:]).copy()
            if len(neighbor_flux)!=n_neighbors:raise ValueError('neighbor coefficient shape mismatch')
            with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
                raw_standardized=solved['residual']/f['error']
            if not np.isfinite(raw_standardized).all():raise ValueError('raw standardized residual invalid')
            frames.append({'obs_id':f['obs_id'],'target_flux_jy':target_flux,
                'negative_target_flux':target_flux<0,'background_coefficients':background,
                'neighbor_ids':f['neighbor_ids'],'neighbor_flux_jy':neighbor_flux,
                'neighbor_active_mask':solved['active_mask'].copy() if self.nonnegative_neighbors else None,
                'model':solved['model'],'residual':solved['residual'],
                'raw_standardized_residual':raw_standardized,
                'weighted_residual':solved['weighted_residual'],'error':f['error'].copy(),'weights':weight.copy(),
                'chi2_weighted':solved['chi2'],'linear_rank':solved['rank'],'scaled_condition':solved['scaled_condition'],
                'scaled_gradient_free':solved['scaled_gradient_free'],
                'scaled_gradient_nonnegative':solved['scaled_gradient_nonnegative'],
                'scaled_free_stationarity_violation':solved['scaled_free_stationarity_violation'],
                'scaled_bound_dual_violation':solved['scaled_bound_dual_violation'],
                'scaled_interior_stationarity_violation':solved['scaled_interior_stationarity_violation'],
                'scaled_complementarity_violation':solved['scaled_complementarity_violation']})
            weighted.append(solved['weighted_residual'])
        residual=np.concatenate(weighted)
        chi2=float(residual@residual)
        if not np.isfinite(chi2):raise ValueError('invalid total chi-square')
        with np.errstate(over='ignore',invalid='ignore'):
            chi2_raw=float(sum(f['raw_standardized_residual']@f['raw_standardized_residual'] for f in frames))
        if not np.isfinite(chi2_raw):raise ValueError('invalid raw chi-square')
        return {'position':position.copy(),'frames':frames,'weighted_residual':residual,'chi2_weighted':chi2,
                'chi2_raw':chi2_raw,
                'nonnegative_neighbors':self.nonnegative_neighbors,'data_unit':str(self.data_unit)}


class NeighborFitError(ValueError):
    def __init__(self,message,start_reports):
        super().__init__(message);self.start_reports=start_reports


def _functions(problem,anchor):
    low=anchor-BOUND;high=anchor+BOUND
    def residual(position):return problem.profile(position)['weighted_residual']
    def jac(position):
        columns=[]
        for i in range(2):
            a=position.copy();b=position.copy()
            a[i]=max(low[i],position[i]-STEP);b[i]=min(high[i],position[i]+STEP)
            columns.append((residual(b)-residual(a))/(b[i]-a[i]))
        return np.column_stack(columns)
    return residual,jac,low,high


def _attempt(residual,jac,low,high,start,stage):
    report={'stage':stage,'start':start.copy(),'success':False}
    try:
        fit=least_squares(residual,start,jac=jac,bounds=(low,high),ftol=1e-8,xtol=1e-8,gtol=1e-7,max_nfev=100)
        cost=float(fit.fun@fit.fun)
        report.update(success=bool(fit.success and np.isfinite(cost)),chi2=cost,position=fit.x.copy(),
                      status=int(fit.status),message=str(fit.message),nfev=int(fit.nfev))
        if not report['success']:fit=None
    except Exception as exc:
        fit=None;report['message']=type(exc).__name__+': '+str(exc)
    return fit,report


def audit_final_modes(problem,anchor,position):
    """Nine starts on existing fixed weights; retain rather than replace point."""
    if not isinstance(problem,NeighborEpochProblem):raise ValueError('NeighborEpochProblem required')
    anchor=_array(anchor,'anchor',1);position=_array(position,'position',1)
    if anchor.shape!=(2,) or position.shape!=(2,) or np.any(np.abs(position-anchor)>BOUND):raise ValueError('invalid anchor or position')
    residual,jac,low,high=_functions(problem,anchor)
    vector=residual(position);point_cost=float(vector@vector)
    if not np.isfinite(point_cost):raise ValueError('point chi-square invalid')
    reports=[]
    for offset in START_OFFSETS:
        _,report=_attempt(residual,jac,low,high,anchor+np.asarray(offset),'final_fixed_weights')
        reports.append(report)
    successful=[r for r in reports if r['success']]
    candidates=[{'position':position.copy(),'chi2':point_cost,'origin':'point'}]
    candidates.extend({'position':r['position'].copy(),'chi2':r['chi2'],'origin':'start'} for r in successful)
    candidates.sort(key=lambda item:item['chi2'])
    modes=[]
    for candidate in candidates:
        group=next((m for m in modes if np.linalg.norm(candidate['position']-m['position'])<=.15),None)
        if group is None:modes.append({**candidate,'member_count':1})
        else:group['member_count']+=1
    best_cost=modes[0]['chi2']
    for m in modes:m['delta_chi2']=m['chi2']-best_cost
    near=[m for m in modes if m['delta_chi2']<=5.991]
    improvement=point_cost-min((r['chi2'] for r in successful),default=point_cost)
    return {'starts':reports,'point_chi2':point_cost,'modes':modes,'near_best_modes':near,
            'near_best_count':len(near),'all_starts_failed':not successful,
            'best_improvement_chi2':improvement,'better_than_point':improvement>1e-4,
            'qualification':'fixed-weight finite-start heuristic; delta chi2 5.991 is not calibrated coverage'}


def _next_weights(profile):
    return [np.minimum(1.,HUBER/np.maximum(np.abs(f['raw_standardized_residual']),1e-300)) for f in profile['frames']]


def fit_epoch(samples,anchor,*,data_unit,nonnegative_neighbors,max_irls_iterations=20):
    """Fit 2D epoch position; nine starts and converged fixed-weight audit.

    Huber updates use residuals divided by the original error. At least two
    updates are performed; the returned point is retained even if convergence
    or multimode screening fails. Numerical support is not a science gate.
    """
    anchor=_array(anchor,'anchor',1)
    if anchor.shape!=(2,):raise ValueError('anchor must have two coordinates')
    if isinstance(max_irls_iterations,(bool,np.bool_)) or not isinstance(max_irls_iterations,Integral) or not 2<=max_irls_iterations<=200:
        raise ValueError('max_irls_iterations must be an integer in [2,200]')
    problem=NeighborEpochProblem(samples,data_unit=data_unit,nonnegative_neighbors=nonnegative_neighbors)
    residual,jac,low,high=_functions(problem,anchor)
    reports=[]
    def attempt(start,stage):
        fit,report=_attempt(residual,jac,low,high,start,stage);reports.append(report);return fit
    fits=[attempt(anchor+np.asarray(offset),'initial') for offset in START_OFFSETS]
    successful=[f for f in fits if f is not None]
    if not successful:raise NeighborFitError('no successful initial fit',reports)
    best=min(successful,key=lambda x:float(x.fun@x.fun));converged=False
    for iteration in range(max_irls_iterations):
        weights=_next_weights(problem.profile(best.x));old=best.x.copy()
        try:problem.set_weights(weights)
        except ValueError as exc:
            reports.append({'stage':'irls_'+str(iteration+1),'start':old,'success':False,'message':str(exc)})
            raise NeighborFitError('IRLS reweighting failed',reports) from exc
        best=attempt(old,'irls_'+str(iteration+1))
        if best is None:raise NeighborFitError('IRLS refit failed',reports)
        after=problem.profile(best.x);next_weights=_next_weights(after)
        next_diff=max(float(np.max(np.abs(a-b))) for a,b in zip(next_weights,weights))
        position_diff=float(np.max(np.abs(best.x-old)))
        converged=bool(next_diff<=WEIGHT_TOLERANCE and position_diff<=POSITION_TOLERANCE)
        if converged and iteration+1>=2:break
    point=problem.profile(best.x)
    if not np.isfinite(point['chi2_raw']):raise NeighborFitError('nonfinite raw chi-square',reports)
    boundary=bool(np.any(np.abs(best.x-anchor)>=.95*BOUND))
    rank=0;rank_reason=None
    try:
        J=jac(best.x);norms=np.linalg.norm(J,axis=0)
        if not np.isfinite(norms).all() or np.any(norms<=0):raise ValueError('zero or invalid derivative column')
        s=np.linalg.svd(J/norms,compute_uv=False)
        if len(s)!=2 or not np.isfinite(s).all() or s[-1]<=RCOND*s[0]:raise ValueError('position rank deficient')
        rank=2
    except (ValueError,np.linalg.LinAlgError) as exc:rank_reason=str(exc)
    modes=audit_final_modes(problem,anchor,best.x)
    reasons=[]
    if boundary:reasons.append('boundary')
    if rank<2:reasons.append('position_rank')
    if not converged:reasons.append('irls_not_converged')
    if modes['all_starts_failed']:reasons.append('final_mode_audit_failed')
    if modes['better_than_point']:reasons.append('better_final_weight_mode')
    if modes['near_best_count']>1:reasons.append('multiple_near_best_modes')
    return {**point,'at_boundary':boundary,'position_rank':rank,'position_rank_reason':rank_reason,
            'start_reports':reports,'final_mode_audit':modes,
            'irls':{'iterations':iteration+1,'max_iterations':int(max_irls_iterations),'converged':converged,
                    'next_weight_max_difference':next_diff,'position_max_change':position_diff,
                    'weight_tolerance':WEIGHT_TOLERANCE,'position_tolerance_px':POSITION_TOLERANCE},
            'numerical_support':not reasons,'numerical_reasons':reasons,
            'qualification':'numerical screening only; piecewise active constraints and fixed final IRLS weights, not scientific support'}
