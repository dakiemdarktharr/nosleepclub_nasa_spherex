"""Conditional linked-flux epoch fit with diagonal pixel errors only.

Renderers accept a 2-D position and return native vectors with units
data_unit/Jy. No WCS, PSF, color convention or calibration is inferred here.
The covariance outputs condition on the final fixed IRLS weights; they are not
validated coverage, include no reference correlations, and are not detections.
"""
from numbers import Integral, Real

import numpy as np
from astropy import units as u
from scipy.optimize import least_squares

from scripts.profile_uncertainty import hessian

BOUND = 2.5
HUBER = 2.5
START_OFFSETS = ((0., 0.), (-.7, 0.), (.7, 0.), (0., -.7), (0., .7))
STEP = .002
RCOND = 1e-10


def _vector(value, name, ndim):
    a = np.asarray(value)
    if a.ndim != ndim or a.dtype.kind not in 'iuf' or not np.isfinite(a).all():
        raise ValueError(name+' must be a finite real array')
    return a.astype(float)


def _positive_length(q, name):
    if not isinstance(q, u.Quantity):
        raise ValueError(name+' requires wavelength units')
    try:
        value = np.asarray(q.to_value(u.um))
    except (ValueError, TypeError, u.UnitConversionError) as exc:
        raise ValueError(name+' requires wavelength units') from exc
    if value.shape != () or value.dtype.kind not in 'iuf' or not np.isfinite(value) or value <= 0:
        raise ValueError(name+' must be positive and finite')
    return float(value)


def _svd(matrix, label):
    n, k = matrix.shape
    if k == 0:
        return np.empty((n, 0)), np.empty(0), np.empty((0, 0)), np.empty(0)
    norms = np.linalg.norm(matrix, axis=0)
    if not np.isfinite(norms).all() or np.any(norms <= 0):
        raise ValueError(label+' has a zero or invalid column')
    try:
        left, singular, right = np.linalg.svd(matrix/norms, full_matrices=False)
    except np.linalg.LinAlgError as exc:
        raise ValueError(label+' SVD failed') from exc
    if len(singular) != k or not np.isfinite(singular).all() or singular[-1] <= RCOND*singular[0]:
        raise ValueError(label+' rank deficient or poorly conditioned')
    return left, singular, right, norms


def _solution(left, singular, right, norms, y):
    return (right.T @ ((left.T @ y)/singular))/norms


def _covariance(singular, right, norms):
    factor=(right.T/singular)/norms[:, None]
    covariance=factor@factor.T
    if not np.isfinite(covariance).all() or np.linalg.eigvalsh(covariance).min() <= 0:
        raise ValueError('invalid conditional flux covariance')
    return covariance


class EpochProblem:
    """Validated inputs and exact linear profile at a caller-supplied position.

    Every frame is a dict containing data, error, nuisance (n-by-k), renderer,
    coefficient (finite dimensionless number) and coefficient_provenance.
    Numeric data/error use the common explicit data_unit. Nuisance columns are
    numeric per-frame bases; their coefficients carry data units. In independent
    mode the free per-frame Jy fluxes use unit coefficients; in shared modes
    each supplied coefficient multiplies the Jy amplitude. For shared_tilt,
    each frame additionally provides wavelength as a Quantity, and caller
    specifies fixed positive tilt_center and tilt_scale wavelengths.
    """
    def __init__(self, samples, *, data_unit, mode, tilt_center=None, tilt_scale=None):
        if mode not in ('independent', 'shared', 'shared_tilt'):
            raise ValueError('unknown flux mode')
        try:
            self.unit = u.Unit(data_unit)
        except (TypeError, ValueError) as exc:
            raise ValueError('explicit physical data unit required') from exc
        if data_unit is None or self.unit == u.one:
            raise ValueError('explicit physical data unit required')
        if not isinstance(samples, (tuple, list)) or not samples:
            raise ValueError('nonempty sample list required')
        if mode == 'shared_tilt':
            center = _positive_length(tilt_center, 'tilt_center')
            scale = _positive_length(tilt_scale, 'tilt_scale')
        elif tilt_center is not None or tilt_scale is not None:
            raise ValueError('tilt parameters only apply to shared_tilt')
        self.mode=mode
        self.tilt_center_um=center if mode=='shared_tilt' else None
        self.tilt_scale_um=scale if mode=='shared_tilt' else None
        self.frames=[]
        n=len(samples); self.k=n if mode == 'independent' else (2 if mode == 'shared_tilt' else 1)
        for i, frame in enumerate(samples):
            if not isinstance(frame, dict):
                raise ValueError('each sample must be a dict')
            required={'data','error','nuisance','renderer','coefficient','coefficient_provenance'}
            allowed=required|({'wavelength'} if mode=='shared_tilt' else set())
            if set(frame) != allowed:
                raise ValueError('sample fields missing or unexpected')
            y=_vector(frame['data'],'data',1); error=_vector(frame['error'],'error',1)
            nuisance=_vector(frame['nuisance'],'nuisance',2)
            if len(y)==0 or error.shape != y.shape or np.any(error<=0) or nuisance.shape[0]!=len(y):
                raise ValueError('sample shapes or positive errors invalid')
            if not callable(frame['renderer']):raise ValueError('renderer must be callable')
            c=frame['coefficient']
            if isinstance(c,(bool,np.bool_)) or not isinstance(c,Real) or not np.isfinite(c):
                raise ValueError('coefficient must be finite and dimensionless')
            if not isinstance(frame['coefficient_provenance'],str) or not frame['coefficient_provenance'].strip():
                raise ValueError('coefficient provenance required')
            row=np.zeros(self.k)
            if mode=='independent':row[i]=1.
            elif mode=='shared':row[0]=c
            else:
                wave=_positive_length(frame['wavelength'],'wavelength')
                row[:]=[c,c*(wave-center)/scale]
            if not np.isfinite(row).all():raise ValueError('invalid flux basis')
            self.frames.append({'data':y.copy(),'error':error.copy(),'nuisance':nuisance.copy(),
                                'renderer':frame['renderer'],'basis':row,
                                'coefficient_provenance':frame['coefficient_provenance']})
        self.dof=sum(len(f['data'])-f['nuisance'].shape[1] for f in self.frames)-self.k-2
        if self.dof <= 0:raise ValueError('model requires positive residual degrees of freedom')
        self.set_weights([np.ones(len(f['data'])) for f in self.frames])

    def set_weights(self, weights):
        if len(weights)!=len(self.frames):raise ValueError('weights must match frames')
        blocks=[]
        for f, value in zip(self.frames,weights):
            weight=_vector(value,'weights',1)
            if weight.shape!=f['data'].shape or np.any(weight<=0) or np.any(weight>1):
                raise ValueError('weights must be in (0,1]')
            whitening=np.sqrt(weight)/f['error']
            if not np.isfinite(whitening).all() or np.any(whitening<=0):raise ValueError('invalid whitening')
            wn=f['nuisance']*whitening[:,None]
            left,singular,right,norms=_svd(wn,'nuisance')
            blocks.append((weight.copy(),whitening,left,singular,right,norms))
        self.blocks=blocks

    def profile(self, position):
        position=_vector(position,'position',1)
        if position.shape!=(2,):raise ValueError('position must have two coordinates')
        projected_y=[]; projected_design=[]; unprojected_design=[]; models=[]
        for f,(_,whitening,left,_,_,_) in zip(self.frames,self.blocks):
            rendered=f['renderer'](position.copy())
            if not isinstance(rendered,u.Quantity):raise ValueError('renderer must return a Quantity')
            try:t=_vector(rendered.to_value(self.unit/u.Jy),'rendered template',1)
            except (u.UnitConversionError,TypeError) as exc:raise ValueError('renderer unit mismatch') from exc
            if t.shape!=f['data'].shape:raise ValueError('renderer vector shape mismatch')
            wy=f['data']*whitening; wt=t*whitening
            projected_y.append(wy-left@(left.T@wy))
            projected_template=wt-left@(left.T@wt)
            projected_design.append(projected_template[:,None]*f['basis'][None,:])
            unprojected_design.append(wt[:,None]*f['basis'][None,:])
            models.append(t)
        Y=np.concatenate(projected_y); X=np.vstack(projected_design)
        before=np.linalg.norm(np.vstack(unprojected_design),axis=0)
        after=np.linalg.norm(X,axis=0)
        if (not np.isfinite(before).all() or not np.isfinite(after).all()
                or np.any(before<=0) or np.any(after<=RCOND*before)):
            raise ValueError('source design unidentifiable after nuisance projection')
        left,singular,right,norms=_svd(X,'source design')
        flux=_solution(left,singular,right,norms,Y)
        covariance=_covariance(singular,right,norms)
        residuals=[]; weighted=[]; nuisance=[]; per_flux=[]; per_error=[]
        for f,(_,whitening,q,s,vh,norm), t in zip(self.frames,self.blocks,models):
            amplitude=float(f['basis']@flux)
            nuisance_coeff=_solution(q,s,vh,norm,(f['data']-amplitude*t)*whitening) if len(s) else np.empty(0)
            resid=f['data']-amplitude*t-f['nuisance']@nuisance_coeff
            variance=float(f['basis']@covariance@f['basis'])
            if not np.isfinite(resid).all() or not np.isfinite(variance) or variance<0:
                raise ValueError('invalid profiled result')
            residuals.append(resid);weighted.append(resid*whitening);nuisance.append(nuisance_coeff)
            per_flux.append(amplitude);per_error.append(float(np.sqrt(variance)))
        wr=np.concatenate(weighted)
        if not np.isfinite(flux).all() or not np.isfinite(wr).all():raise ValueError('invalid profiled result')
        bases=np.stack([f['basis'] for f in self.frames])
        frame_covariance=bases@covariance@bases.T
        return {'flux_parameters_jy':flux,'flux_covariance_jy2':covariance,'flux_basis':bases,
                'per_frame_flux_covariance_jy2':frame_covariance,'per_frame_flux_jy':np.asarray(per_flux),
                'per_frame_error_jy':np.asarray(per_error),'residuals':residuals,'weighted_residual':wr,
                'nuisance_coefficients':nuisance,'source_rank':len(singular),
                'source_condition':float(singular[0]/singular[-1]),'nuisance_ranks':[len(b[3]) for b in self.blocks]}


class EpochFitError(ValueError):
    def __init__(self, message, start_reports):
        super().__init__(message)
        self.start_reports=start_reports


def _functions(problem, anchor):
    low=anchor-BOUND; high=anchor+BOUND
    def residual(p):return problem.profile(p)['weighted_residual']
    def jac(p):
        columns=[]
        for i in range(2):
            a=p.copy();b=p.copy()
            a[i]=max(low[i],p[i]-STEP);b[i]=min(high[i],p[i]+STEP)
            columns.append((residual(b)-residual(a))/(b[i]-a[i]))
        return np.column_stack(columns)
    return residual,jac,low,high


def _attempt(residual, jac, low, high, start, stage):
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


def audit_final_modes(problem, anchor, point):
    """Five starts under current fixed weights; never replace the supplied point.

    Greedy clustering joins solutions at distance <=0.15 pixel from the
    lowest-cost representative. Delta 5.991 is a heuristic, not a confidence
    threshold. Results and failures refer only to the finite starts tried.
    """
    if not isinstance(problem,EpochProblem):raise ValueError('EpochProblem required')
    anchor=_vector(anchor,'anchor',1);point=_vector(point,'point',1)
    if anchor.shape!=(2,) or point.shape!=(2,) or np.any(np.abs(point-anchor)>BOUND):
        raise ValueError('invalid anchor or point')
    residual,jac,low,high=_functions(problem,anchor)
    point_residual=residual(point);point_cost=float(point_residual@point_residual)
    if not np.isfinite(point_cost):raise ValueError('point cost must be finite')
    reports=[]
    for offset in START_OFFSETS:
        _,report=_attempt(residual,jac,low,high,anchor+np.asarray(offset),'final_fixed_weights')
        reports.append(report)
    successful=[r for r in reports if r['success']]
    candidates=[{'position':point.copy(),'chi2':point_cost,'origin':'point'}]
    candidates.extend({'position':r['position'].copy(),'chi2':r['chi2'],'origin':'start'} for r in successful)
    candidates.sort(key=lambda item:item['chi2'])
    modes=[]
    for candidate in candidates:
        group=next((m for m in modes if np.linalg.norm(candidate['position']-m['position'])<=.15),None)
        if group is None:
            modes.append({**candidate,'member_count':1})
        else:group['member_count']+=1
    best_cost=modes[0]['chi2']
    for m in modes:m['delta_chi2']=m['chi2']-best_cost
    near=[m for m in modes if m['delta_chi2']<=5.991]
    improvement=point_cost-min((r['chi2'] for r in successful),default=point_cost)
    return {'requested':True,'starts':reports,'point_chi2':point_cost,'modes':modes,
            'near_best_modes':near,'near_best_count':len(near),'better_than_point':improvement>1e-4,
            'best_improvement_chi2':improvement,'all_starts_failed':not successful,
            'qualification':'fixed-weight finite-start heuristic; 5.991 is not a calibrated confidence threshold'}


def _next_weights(problem, prof):
    weights=[]
    for f,resid in zip(problem.frames,prof['residuals']):
        standardized=np.abs(resid/f['error'])
        weights.append(np.minimum(1.,HUBER/np.maximum(standardized,1e-300)))
    return weights


def fit_epoch(samples, anchor, *, data_unit, mode, tilt_center=None, tilt_scale=None,
              observed_hessian=False, max_irls_iterations=2, weight_tolerance=1e-3,
              position_tolerance=1e-4, final_mode_audit=False):
    """Five starts then up to max_irls_iterations fixed-weight Huber refits.

    Default makes two updates. At least two updates are performed when possible;
    thereafter stop only if the *next* raw-error Huber weight change and latest
    position change meet their tolerances. Failed convergence retains the point
    with an explicit inference failure. Optional mode audit cannot change it.
    """
    anchor=_vector(anchor,'anchor',1)
    if anchor.shape!=(2,):raise ValueError('anchor must have two coordinates')
    if not isinstance(observed_hessian,bool) or not isinstance(final_mode_audit,bool):raise ValueError('flags must be boolean')
    if isinstance(max_irls_iterations,(bool,np.bool_)) or not isinstance(max_irls_iterations,Integral) or not 1<=max_irls_iterations<=200:
        raise ValueError('max_irls_iterations must be an integer in [1,200]')
    for name,val in [('weight_tolerance',weight_tolerance),('position_tolerance',position_tolerance)]:
        if isinstance(val,(bool,np.bool_)) or not isinstance(val,Real) or not np.isfinite(val) or val<=0:
            raise ValueError(name+' must be positive and finite')
    problem=EpochProblem(samples,data_unit=data_unit,mode=mode,tilt_center=tilt_center,tilt_scale=tilt_scale)
    residual,jac,low,high=_functions(problem,anchor)
    reports=[]
    def attempt(start, stage):
        fit,report=_attempt(residual,jac,low,high,start,stage)
        reports.append(report)
        return fit
    fits=[attempt(anchor+np.asarray(offset),'initial') for offset in START_OFFSETS]
    successful=[f for f in fits if f is not None]
    if not successful:raise EpochFitError('no successful initial fit',reports)
    best=min(successful,key=lambda f:float(f.fun@f.fun))
    converged=False
    for iteration in range(max_irls_iterations):
        prof=problem.profile(best.x)
        weights=_next_weights(problem,prof)
        previous_position=best.x.copy()
        try:
            problem.set_weights(weights)
        except (ValueError,np.linalg.LinAlgError) as exc:
            reports.append({'stage':'irls_'+str(iteration+1),'start':best.x.copy(),
                            'success':False,'message':type(exc).__name__+': '+str(exc)})
            raise EpochFitError('IRLS reweighting failed',reports) from exc
        best=attempt(best.x,'irls_'+str(iteration+1))
        if best is None:raise EpochFitError('IRLS refit failed',reports)
        next_weights=_next_weights(problem,problem.profile(best.x))
        next_difference=max(float(np.max(np.abs(new-old))) for new,old in zip(next_weights,weights))
        position_change=float(np.max(np.abs(best.x-previous_position)))
        converged=bool(next_difference<=weight_tolerance and position_change<=position_tolerance)
        if converged and iteration+1>=min(2,max_irls_iterations):break
    out=problem.profile(best.x)
    raw_chi2=sum(float(np.sum((r/f['error'])**2)) for r,f in zip(out['residuals'],problem.frames))
    weighted_chi2=float(out['weighted_residual']@out['weighted_residual'])
    if not np.isfinite([raw_chi2,weighted_chi2]).all():
        raise EpochFitError('nonfinite final chi-square',reports)
    boundary=bool(np.any(np.abs(best.x-anchor)>=.95*BOUND))
    position_cov=None;position_reason=None;position_rank=0
    try:
        J=jac(best.x)
        _,s,vh,norms=_svd(J,'position Jacobian')
        position_rank=len(s)
        if boundary:position_reason='boundary'
        else:position_cov=_covariance(s,vh,norms)
    except (ValueError,np.linalg.LinAlgError) as exc:position_reason=str(exc)
    profile={'supported':False,'reason':'not_requested'}
    if observed_hessian:
        if boundary:profile={'supported':False,'reason':'boundary'}
        elif position_rank<2:profile={'supported':False,'reason':'invalid_position_rank'}
        else:
            try:
                matrices=[hessian(residual,best.x,step) for step in (.002,.004)]
                if not np.isfinite(matrices).all():raise ValueError('nonfinite curvature')
                change=float(np.linalg.norm(matrices[0]-matrices[1])/max(np.linalg.norm(matrices[1]),np.finfo(float).tiny))
                info=(matrices[0]+matrices[0].T)/2
                profile={'supported':False,'hessians':matrices,'relative_step_change':change}
                if not np.isfinite(change) or change>.05:profile['reason']='unstable_profile_curvature'
                elif np.linalg.eigvalsh(info).min()<=0:profile['reason']='nonpositive_profile_curvature'
                elif np.linalg.eigvalsh(info).min()<=RCOND*np.linalg.eigvalsh(info).max():profile['reason']='rank_deficient_profile_curvature'
                else:
                    covariance=np.linalg.solve(info,np.eye(2))
                    if not np.isfinite(covariance).all() or np.linalg.eigvalsh(covariance).min()<=0:raise ValueError('invalid profile covariance')
                    profile.update(supported=True,covariance_px2=covariance)
            except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:profile={'supported':False,'reason':'profile_exception','detail':str(exc)}
    errors=out['per_frame_error_jy'];flux=out['per_frame_flux_jy']
    snr=np.full(len(flux),np.nan);np.divide(flux,errors,out=snr,where=errors>0)
    mode_audit=audit_final_modes(problem,anchor,best.x) if final_mode_audit else {'requested':False}
    reasons=[]
    if boundary:reasons.append('boundary')
    if position_rank<2 or position_cov is None:reasons.append('position_rank_or_covariance')
    if not converged:reasons.append('irls_not_converged')
    if final_mode_audit:
        if mode_audit['all_starts_failed']:reasons.append('final_mode_audit_failed')
        if mode_audit['better_than_point']:reasons.append('better_final_weight_mode')
        if mode_audit['near_best_count']>1:reasons.append('multiple_near_best_modes')
    else:reasons.append('final_mode_audit_not_requested')
    return {**out,'position':best.x.copy(),'dof':problem.dof,'chi2_raw':raw_chi2,'chi2_weighted':weighted_chi2,
            'mode':mode,'data_unit':str(problem.unit),'tilt_center_um':problem.tilt_center_um,'tilt_scale_um':problem.tilt_scale_um,
            'weights':[b[0].copy() for b in problem.blocks], 'start_reports':reports,'at_boundary':boundary,
            'position_rank':position_rank,'position_covariance_px2':position_cov,'position_covariance_reason':position_reason,
            'profile_hessian':profile,'negative_frame_flux':flux<0,'conditional_frame_snr':snr,
            'irls':{'iterations':iteration+1,'max_iterations':int(max_irls_iterations),'converged':converged,
                    'next_weight_max_difference':next_difference,'position_max_change':position_change,
                    'weight_tolerance':float(weight_tolerance),'position_tolerance_px':float(position_tolerance)},
            'final_mode_audit':mode_audit,'inference_supported':not reasons,'inference_reasons':reasons,
            'coefficient_provenance':[f['coefficient_provenance'] for f in problem.frames],
            'qualification':'algorithmic screening only; fixed final IRLS weights; conditional diagonal noise; no calibrated coverage or detection probability'}
