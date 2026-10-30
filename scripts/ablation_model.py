"""Fair 2x2 native-pixel ablation; independent failures, common quality reference."""
import numpy as np
from scipy.ndimage import gaussian_filter,spline_filter
from . import quality_model as old
from . import covariance_model as width

motion=old.motion;joint=old.joint
MODELS={'plane_fixed':{'degree':1,'flexible':False},'quadratic_fixed':{'degree':2,'flexible':False},
    'plane_flexible':{'degree':1,'flexible':True},'quadratic_flexible':{'degree':2,'flexible':True}}
RULES={'version':'0.9.0','models':MODELS,'width_blur_native_px':.25,'initial_eta':.25,
    'information_svd_relative_cut':1e-8,'comparison':'same single-source fit for every model',
    'background_annulus_native_px':[4.,9.],'background_neighbour_mask_native_px':2.5,
    'background_pixels_min':24,'background_clip_sigma':3.,'background_clip_iterations':3,
    'background_measure':'1.4826 median absolute deviation of original-noise-normalized plane residuals in catalog-masked annulus',
    'snr_measure':'minimum of the two fitted epoch SNR values; no injection SNR used for calibration routing',
    'model_sensitivity_covariance':False}


def prepare(frames,catalog,xy,anchor,target_id,kind):
    output=[];config=MODELS[kind]
    for s in old.samples_for(frames,catalog,xy,anchor,target_id):
        if config['degree']==2:
            x,y=s['background'][:,1:3].T;s={**s,'background':np.column_stack([s['background'],x*x,x*y,y*y])}
            s=joint.prepare(s,s['neighbours'])
        if config['flexible']:
            f=s['frame'];over=f['epsf_oversampling'];raw=np.asarray(f['epsf_table']['EPSF'][s['zone']],float)
            wide=gaussian_filter(raw,RULES['width_blur_native_px']*over)
            s['wide_epsf']=spline_filter(wide*over**2/wide.sum(),order=3)
        output.append(s)
    return output


def fit(frames,catalog,xy,anchor,kind,reference,target_id=None):
    samples=prepare(frames,catalog,xy,anchor,target_id,kind);flex=MODELS[kind]['flexible'];anchor=np.asarray(anchor)
    def solve(ss,initial=None,starts=False):
        if flex:return width.solve(ss,anchor,np.r_[anchor,RULES['initial_eta']] if initial is None else initial,starts)
        return old.solve(ss,anchor,starts=starts,initial=initial)
    residual=width.residual if flex else joint.residual_sample
    result=solve(samples,starts=True)
    for _ in range(old.RULES['irls_iterations']):
        weighted=[]
        for s in samples:
            r=residual(s,result.x)*s['error']/s['original_error'];w=np.minimum(1.,old.RULES['huber_threshold']/np.maximum(np.abs(r),1e-12))
            weighted.append(old.reweight(s,w))
        samples=weighted;result=solve(samples,result.x)
    position=result.x[:2];effective=[width.at_width(s,result.x[2]) for s in samples] if flex else samples
    details,chi=old.diagnostics(effective,position);dof=sum(len(s['data'])-s['rank']-1 for s in samples)
    if flex:chi*=max(1,dof-2)/max(1,dof-3)
    full=np.linalg.pinv(result.jac.T@result.jac)*max(1.,chi);covariance=full[:2,:2]
    singular=np.linalg.svd(result.jac,compute_uv=False);rank=int(np.sum(singular>singular[0]*RULES['information_svd_relative_cut']))
    weights=np.array([max(d['snr'],0.)**2 for d in details]);times=[d['mjd'] for d in details]
    output={'position':position,'covariance':covariance,'success':bool(result.success),
        'at_boundary':bool(np.any(np.abs(position-anchor)>.95*old.RULES['fit_bound_px'])),
        'reduced_chi2':float(chi),'per_frame':details,'samples':effective,
        'effective_mjd':float(np.average(times,weights=weights)) if weights.sum() else float(np.mean(times)),
        'information_rank':rank,'parameter_count':3 if flex else 2}
    if flex:output.update(width_mixture=float(result.x[2]),width_at_boundary=bool(result.x[2]<.01 or result.x[2]>.99))
    if reference is not None:
        limit=max(old.RULES['model_disagreement_floor_px'],old.RULES['model_disagreement_sigma']*
            np.sqrt(max(np.linalg.eigvalsh(reference['covariance']+covariance).max(),0.)))
        output['model_comparison']={'against':'common single-source','shift_px':float(np.linalg.norm(reference['position']-position)),'limit_px':float(limit)}
    output['quality']=old.gate(output)
    if reference is None:output['quality']['reasons'].append('comparison_unavailable')
    if rank<output['parameter_count'] or np.linalg.eigvalsh(covariance).min()<=0:output['quality']['reasons'].append('singular_information')
    output['quality']['accepted']=not output['quality']['reasons']
    return output


def background(frames,xy,anchor):
    """Observed scene feature on original pixels, before synthetic injection."""
    details=[];a=np.asarray(anchor,float);inner,outer=RULES['background_annulus_native_px']
    for f in frames:
        try:
            s=motion.native_stamp(f,a,radius=10);center=s['native_center'];r2=(s['x']-center[0])**2+(s['y']-center[1])**2
            keep=(r2>=inner**2)&(r2<=outer**2)
            for neighbour in xy[f['record']['obs_id']]:
                if np.linalg.norm(neighbour-a)>14:continue
                p=center+s['jacobian']@(neighbour-a)
                keep&=(s['x']-p[0])**2+(s['y']-p[1])**2>RULES['background_neighbour_mask_native_px']**2
            if keep.sum()<RULES['background_pixels_min']:raise ValueError('too_few_background_pixels')
            d=np.column_stack([np.ones(keep.sum()),(s['x'][keep]-center[0])/outer,(s['y'][keep]-center[1])/outer])/s['error'][keep,None]
            y=s['data'][keep]/s['error'][keep];use=np.ones(len(y),bool)
            for _ in range(RULES['background_clip_iterations']):
                beta=np.linalg.lstsq(d[use],y[use],rcond=None)[0];r=y-d@beta
                med=np.median(r);scale=max(1.,1.4826*np.median(np.abs(r-med)));new=np.abs(r-med)<=RULES['background_clip_sigma']*scale
                if new.sum()>=RULES['background_pixels_min']:use=new
            score=float(max(.05,1.4826*np.median(np.abs(r-np.median(r)))))
            details.append({'obs_id':f['record']['obs_id'],'score':score,'pixels':int(keep.sum())})
        except (ValueError,np.linalg.LinAlgError) as exc:details.append({'obs_id':f['record']['obs_id'],'score':None,'reason':str(exc)})
    valid=[v['score'] for v in details if v['score'] is not None]
    return {'score':float(np.median(valid)) if len(valid)>=np.ceil(.8*len(frames)) and valid else None,
        'usable_frames':len(valid),'frames':len(frames),'per_frame':details}
