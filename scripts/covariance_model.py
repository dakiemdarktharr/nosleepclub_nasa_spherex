"""0.8 candidate: curved backgrounds, bounded ePSF width, empirical error envelope.

No truth enters centroid fitting or quality gates. The learned error envelope is
an empirical calibration diagnostic, not a posterior or a conformal guarantee.
"""
import numpy as np
from scipy.ndimage import gaussian_filter, spline_filter
from scipy.optimize import least_squares
from . import quality_model as previous

motion=previous.motion; joint=previous.joint
RULES={'version':'0.8.0','background_degree':2,'width_blur_native_px':.25,
    'width_mixture_bounds':[0.,1.],'initial_width_mixture':.25,
    'model_sensitivity_multiplier':.25,'error_floor_min_arcsec':.05,
    'calibration_probability':.68,'ellipse68_threshold':2.27886856637673,
    'ellipse95_threshold':5.99146454710798,'minimum_calibration_blocks':6,
    'minimum_calibration_fields':3,'scale_min':1.,'bias_subtraction':False}


def samples_for(frames,catalog,xy,anchor,target_id=None):
    samples=previous.samples_for(frames,catalog,xy,anchor,target_id)
    output=[]
    for s in samples:
        x,y=s['background'][:,1:3].T
        s={**s,'background':np.column_stack([s['background'],x*x,x*y,y*y])}
        frame=s['frame']; raw=np.asarray(frame['epsf_table']['EPSF'][s['zone']],float)
        over=frame['epsf_oversampling']; wide=gaussian_filter(raw,RULES['width_blur_native_px']*over)
        s['wide_epsf']=spline_filter(wide*over**2/wide.sum(),order=3)
        output.append(joint.prepare(s,s['neighbours']))
    return output


def at_width(sample,eta):
    return {**sample,'epsf':sample['epsf']+eta*(sample['wide_epsf']-sample['epsf'])}


def residual(sample,params,amplitude=False):
    return joint.residual_sample(at_width(sample,params[2]),params[:2],amplitude)


def solve(samples,anchor,initial,multistart):
    anchor=np.asarray(anchor,float); bound=previous.RULES['fit_bound_px']; h=previous.RULES['derivative_step_px']
    def fun(p):return np.concatenate([residual(s,p) for s in samples])
    def jac(p):return np.column_stack([(fun(p+v*h)-fun(p-v*h))/(2*h) for v in np.eye(3)])
    starts=[initial]
    if multistart:starts += [np.r_[anchor+v,RULES['initial_width_mixture']] for v in [(-.7,0),(.7,0),(0,-.7),(0,.7)]]
    fits=[least_squares(fun,p,jac=jac,bounds=(np.r_[anchor-bound,0.],np.r_[anchor+bound,1.]),
        ftol=1e-8,xtol=1e-8,gtol=1e-7,max_nfev=90) for p in starts]
    return min(fits,key=lambda f:float(f.fun@f.fun))


def fit(frames,catalog,xy,anchor,target_id=None,old=None):
    if old is None:old=previous.fit(frames,catalog,xy,anchor,target_id)
    samples=samples_for(frames,catalog,xy,anchor,target_id)
    bound=previous.RULES['fit_bound_px']
    initial=np.r_[np.clip(old['position'],np.asarray(anchor)-.99*bound,np.asarray(anchor)+.99*bound),RULES['initial_width_mixture']]
    result=solve(samples,anchor,initial,True)
    for _ in range(previous.RULES['irls_iterations']):
        weighted=[]
        for s in samples:
            raw=residual(s,result.x)*s['error']/s['original_error']
            weights=np.minimum(1.,previous.RULES['huber_threshold']/np.maximum(np.abs(raw),1e-12))
            weighted.append(previous.reweight(s,weights))
        samples=weighted;result=solve(samples,anchor,result.x,False)
    effective=[at_width(s,result.x[2]) for s in samples]
    details,chi=previous.diagnostics(effective,result.x[:2])
    # One more nonlinear parameter than 0.7. Marginalize width with the full
    # inverse information; constraints at eta=0/1 remain an approximation.
    dof=sum(len(s['data'])-s['rank']-1 for s in samples)
    chi*=max(1,dof-2)/max(1,dof-3)
    full_cov=np.linalg.pinv(result.jac.T@result.jac)*max(1.,chi)
    covariance=full_cov[:2,:2]
    weights=np.array([max(d['snr'],0.)**2 for d in details]); times=[d['mjd'] for d in details]
    output={'position':result.x[:2],'covariance':covariance,'success':bool(result.success),
        'at_boundary':bool(np.any(np.abs(result.x[:2]-np.asarray(anchor))>.95*bound)),
        'reduced_chi2':float(chi),'per_frame':details,
        'effective_mjd':float(np.average(times,weights=weights)) if weights.sum() else float(np.mean(times)),
        'samples':effective,'width_mixture':float(result.x[2]),
        'width_at_boundary':bool(result.x[2]<.01 or result.x[2]>.99)}
    limit=max(previous.RULES['model_disagreement_floor_px'],previous.RULES['model_disagreement_sigma']*
        np.sqrt(max(np.linalg.eigvalsh(old['covariance']+covariance).max(),0.)))
    output['model_comparison']={'against':'0.7 IR robust','shift_px':float(np.linalg.norm(old['position']-output['position'])),'limit_px':float(limit)}
    output['quality']=previous.gate(output)
    return output


def positive_part(matrix):
    eig,vec=np.linalg.eigh((np.asarray(matrix)+np.asarray(matrix).T)/2)
    return (vec*np.maximum(eig,0.))@vec.T


def calibrate(records):
    """Equal weight per field and per spatial block; accepted-only calibration.

    Multiple SNR/motion/PSF trials on one patch share the same real pixels. They
    are not independent calibration draws. No validation record is accepted.
    """
    if any(r['phase']!='calibration' for r in records):raise ValueError('Calibration must not include validation/development')
    accepted=[r for r in records if r['models']['candidate']['accepted']]
    fields=sorted({r['field_id'] for r in accepted}); blocks=sorted({(r['field_id'],r['patch_index']) for r in accepted})
    if len(fields)<RULES['minimum_calibration_fields'] or len(blocks)<RULES['minimum_calibration_blocks']:
        raise ValueError('Insufficient accepted calibration fields/blocks')
    weights=[];excess=[]
    for r in accepted:
        key=(r['field_id'],r['patch_index']); n=sum((v['field_id'],v['patch_index'])==key for v in accepted)
        nblocks=sum(b[0]==r['field_id'] for b in blocks)
        weights.append(1/(len(fields)*nblocks*n))
        v=r['models']['candidate'];e=np.asarray(v['error_east_north_arcsec']);c=np.asarray(v['covariance_arcsec2'])
        excess.append(np.outer(e,e)-c)
    weights=np.asarray(weights);floor=positive_part(np.einsum('i,ijk->jk',weights,np.array(excess)))+np.eye(2)*RULES['error_floor_min_arcsec']**2
    scores=[]
    for r in accepted:
        v=r['models']['candidate'];e=np.asarray(v['error_east_north_arcsec']);c=np.asarray(v['covariance_arcsec2'])+floor
        scores.append(float(e@np.linalg.solve(c,e)))
    order=np.argsort(scores);cum=np.cumsum(weights[order]);rank=int(np.searchsorted(cum,RULES['calibration_probability'],side='left'));rank=min(rank,len(order)-1)
    scale2=max(RULES['scale_min']**2,scores[order[rank]]/RULES['ellipse68_threshold'])
    return {'formula':'C_cal = scale_squared * (C_raw + floor_arcsec2)','floor_arcsec2':floor.tolist(),
        'scale_squared':float(scale2),'accepted':len(accepted),'attempted':len(records),'fields':fields,
        'spatial_blocks':[list(b) for b in blocks],'weighting':'equal fields, equal accepted patches per field, equal trials within patch',
        'quantile':'weighted empirical 0.68 left inverse; no finite-sample coverage guarantee',
        'bias_subtraction':False,'fitted_from':'calibration injections only'}


def apply_covariance(covariance,calibrator):
    return calibrator['scale_squared']*(np.asarray(covariance)+np.asarray(calibrator['floor_arcsec2']))
