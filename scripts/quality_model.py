"""Experimental IR deblending, Huber pixel weights and explicit quality gates.

All gates use fitted data/model diagnostics, never the known injected displacement.
Covariances remain conditional approximations, not calibrated discovery odds.
"""
import numpy as np
from astropy.time import Time
from scipy.optimize import least_squares
from . import benchmark_accuracy as bench
from . import joint_motion as joint
from . import release_analysis as release

motion=bench.motion;gaia=bench.gaia
RULES={'version':'0.7.0','neighbour_radius_px':8.,'target_match_radius_px':.35,
    'max_neighbours':24,'svd_relative_cut':1e-8,'fit_bound_px':2.5,'reference_bound_px':1.3,'derivative_step_px':.002,
    'huber_threshold':2.5,'irls_iterations':2,'chi2_max':3.,'core_rms_max':2.5,
    'core_radius_native_px':2.5,'core_coverage_min':.75,'core_usable_frame_fraction':.80,
    'outlier_sigma':5.,'core_outlier_fraction_max':.10,'epoch_snr_min':5.,
    'information_fraction_min':.05,'registration_mahalanobis_max':4.,
    'registration_scatter_floor_px':.02,'registration_sources_min':4,
    'model_disagreement_floor_px':.20,'model_disagreement_sigma':3.}


def positions(catalog,frames):
    output={};indices=[i for i,c in enumerate(catalog) if c['gaia']]
    stars=[catalog[i]['gaia'] for i in indices]
    if stars:
        ra0=np.deg2rad([s['ra'] for s in stars]);dec0=np.deg2rad([s['dec'] for s in stars])
        east=np.column_stack([-np.sin(ra0),np.cos(ra0),np.zeros(len(stars))])
        north=np.column_stack([-np.cos(ra0)*np.sin(dec0),-np.sin(ra0)*np.sin(dec0),np.cos(dec0)])
    for f in frames:
        sky=np.array([release.corrected_position(c['row'],c['correction'],f['mjd']) if not c['gaia'] else [0.,0.] for c in catalog])
        if stars:
            dt=Time(f['mjd'],format='mjd').tcb.jyear-np.array([s['ref_epoch'] for s in stars])
            earth=gaia.earth_position(float(f['mjd']));parallax=np.array([s['parallax'] for s in stars])
            de=np.array([s['pmra'] for s in stars])*dt-parallax*(east@earth)
            dn=np.array([s['pmdec'] for s in stars])*dt-parallax*(north@earth)
            sky[indices,0]=np.rad2deg(ra0)+de/(3.6e6*np.cos(dec0));sky[indices,1]=np.rad2deg(dec0)+dn/3.6e6
        output[f['record']['obs_id']]=np.column_stack(motion.WCS.world_to_pixel_values(sky[:,0],sky[:,1])) if len(catalog) else np.empty((0,2))
    return output


def samples_for(frames,catalog,xy,anchor,target_id=None):
    samples=[];anchor=np.asarray(anchor)
    for f in frames:
        s=motion.native_stamp(f,anchor);near=xy[f['record']['obs_id']]
        distance=np.linalg.norm(near-anchor,axis=1)
        keep=np.flatnonzero(distance<=RULES['neighbour_radius_px'])
        # Remove the catalog counterpart of a real target, not its companions.
        if target_id is not None:
            matched=[i for i in keep if catalog[i]['gaia'] and catalog[i]['gaia']['source_id']==target_id]
            if not matched and len(keep):
                nearest=int(keep[np.argmin(distance[keep])]);matched=[nearest] if distance[nearest]<RULES['target_match_radius_px'] else []
            keep=np.array([i for i in keep if i not in matched],int)
        keep=sorted(keep,key=lambda i:(catalog[i]['row']['w2mpro_pm'],catalog[i]['id']))[:RULES['max_neighbours']]
        neighbours=[(catalog[i]['id'],near[i]) for i in keep]
        s=joint.prepare(s,neighbours)
        s['original_error']=s['error'].copy()
        s['neighbours']=neighbours
        samples.append(s)
    return samples


def solve(samples,anchor,starts=True,initial=None,bound=None):
    anchor=np.asarray(anchor,float);h=RULES['derivative_step_px'];bound=RULES['fit_bound_px'] if bound is None else bound
    def residual(pos):return np.concatenate([joint.residual_sample(s,pos) for s in samples])
    def derivative(pos):return np.column_stack([(residual(pos+v*h)-residual(pos-v*h))/(2*h) for v in np.eye(2)])
    start_points=[anchor if initial is None else initial]+([anchor+v for v in [(-.7,0),(.7,0),(0,-.7),(0,.7)]] if starts else [])
    fits=[least_squares(residual,p,jac=derivative,bounds=(anchor-bound,anchor+bound),
        ftol=1e-8,xtol=1e-8,gtol=1e-7,max_nfev=90) for p in start_points]
    return min(fits,key=lambda f:float(f.fun@f.fun))


def reweight(sample,weights):
    s={**sample,'error':sample['original_error']/np.sqrt(weights)}
    return {**joint.prepare(s,sample['neighbours']),'original_error':sample['original_error'],'neighbours':sample['neighbours']}


def diagnostics(samples,position):
    details=[];raw_sum=0.;dof=0
    for s in samples:
        residual,amplitude,amplitude_error=joint.residual_sample(s,position,True)
        raw=residual*s['error']/s['original_error'];raw_sum+=float(raw@raw);dof+=len(raw)-s['rank']-1
        p=motion.stamp_model(s,position)[:,0]/s['error'];projected=p-s['q']@(s['q'].T@p)
        information=float((projected@projected)/max(p@p,1e-20))
        center=s['native_center']+s['jacobian']@(position-s['anchor'])
        core=(s['x']-center[0])**2+(s['y']-center[1])**2<=RULES['core_radius_native_px']**2
        radius=RULES['core_radius_native_px']
        # Count the full geometric core, including pixels outside the cutout.
        # A truncated edge must not appear to have 100% valid coverage.
        yy,xx=np.meshgrid(np.arange(np.floor(center[1]-radius),np.ceil(center[1]+radius)+1),
            np.arange(np.floor(center[0]-radius),np.ceil(center[0]+radius)+1),indexing='ij')
        possible=((xx-center[0])**2+(yy-center[1])**2<=radius**2).sum()
        score=float(np.sqrt(np.mean(raw[core]**2))) if core.any() else 1e10
        chi=float(raw@raw/max(1,len(raw)-s['rank']-1));error=amplitude_error*max(1.,np.sqrt(chi))
        details.append({'obs_id':s['frame']['record']['obs_id'],'mjd':s['frame']['mjd'],'amplitude':float(amplitude),
            'amplitude_error':float(error),'snr':float(amplitude/error),'reduced_chi2':chi,'core_rms':score,
            'core_coverage':float(core.sum()/max(1,possible)),
            'core_outlier_fraction':float(np.mean(np.abs(raw[core])>RULES['outlier_sigma'])) if core.any() else 1.,
            'information_fraction':information,'neighbour_ids':s.get('neighbour_ids',[]),
            'downweighted_pixels':int(np.sum(s['error']>s['original_error']*1.001))})
    return details,raw_sum/max(1,dof-2)


def gate(fit):
    reasons=[];details=fit['per_frame']
    if not fit['success']:reasons.append('solver_failed')
    if fit['at_boundary']:reasons.append('centroid_at_boundary')
    if not details or sum(d['amplitude'] for d in details)<=0:reasons.append('nonpositive_flux')
    snr=float(np.sqrt(sum(max(d['snr'],0.)**2 for d in details)))
    if snr<RULES['epoch_snr_min']:reasons.append('low_epoch_snr')
    if fit['reduced_chi2']>RULES['chi2_max']:reasons.append('poor_global_fit')
    comparison=fit.get('model_comparison')
    if comparison and comparison['shift_px']>comparison['limit_px']:reasons.append('model_disagreement')
    required=int(np.ceil(RULES['core_usable_frame_fraction']*len(details)))
    checks=[('core_coverage','core_coverage_min',True,'insufficient_core_pixels'),
        ('core_rms','core_rms_max',False,'structured_core_residual'),
        ('core_outlier_fraction','core_outlier_fraction_max',False,'core_outliers'),
        ('information_fraction','information_fraction_min',True,'unresolved_blend')]
    for key,limit,minimum,label in checks:
        count=sum(d.get(key,1. if minimum else 0.)>=RULES[limit] if minimum else d.get(key,0.)<=RULES[limit] for d in details)
        if count<required:reasons.append(label)
    return {'accepted':not reasons,'reasons':reasons,'epoch_snr':snr,'required_good_frames':required,
        'model_comparison':comparison}


def fit(frames,catalog,xy,anchor,target_id=None,reference=False):
    original=samples_for(frames,catalog,xy,anchor,target_id);samples=original
    bound=RULES['reference_bound_px'] if reference else RULES['fit_bound_px']
    result=solve(samples,anchor,not reference,bound=bound)
    for _ in range(RULES['irls_iterations']):
        weighted=[]
        for s in samples:
            residual=joint.residual_sample(s,result.x)*s['error']/s['original_error']
            weights=np.minimum(1.,RULES['huber_threshold']/np.maximum(np.abs(residual),1e-12))
            weighted.append(reweight(s,weights))
        samples=weighted
        # Original search region is unchanged across IRLS iterations.
        result=solve(samples,anchor,False,initial=result.x,bound=bound)
    details,chi2=diagnostics(samples,result.x)
    covariance=np.linalg.pinv(result.jac.T@result.jac)*max(1.,chi2)
    weights=np.array([max(d['snr'],0.)**2 for d in details]);times=[d['mjd'] for d in details]
    output={'position':result.x,'covariance':covariance,'success':bool(result.success),
        'at_boundary':bool(np.any(np.abs(result.x-np.asarray(anchor))>.95*bound)),
        'reduced_chi2':float(chi2),'per_frame':details,'effective_mjd':float(np.average(times,weights=weights)) if weights.sum() else float(np.mean(times)),
        'samples':samples}
    baseline=motion.fit_position(frames,np.asarray(anchor),bound=bound,multistart=not reference)
    limit=max(RULES['model_disagreement_floor_px'],RULES['model_disagreement_sigma']*
        np.sqrt(max(np.linalg.eigvalsh(baseline['covariance']+covariance).max(),0.)))
    output['model_comparison']={'shift_px':float(np.linalg.norm(baseline['position']-result.x)),'limit_px':float(limit)}
    output['quality']=gate(output)
    return output


def baseline_fit(frames,anchor):
    output=motion.fit_position(frames,np.asarray(anchor),multistart=True)
    samples=[]
    for s in output['samples']:
        prepared=joint.prepare(s);prepared.update(original_error=s['error'],neighbours=[]);samples.append(prepared)
    details,chi2=diagnostics(samples,output['position'])
    output['per_frame']=details;output['quality']=gate(output)
    return output


def registration(frame,training):
    usable=[]
    for r in training:
        entry=gaia.usable_entry(r,frame['record']['obs_id'])
        if entry is not None:usable.append((r,entry))
    if len(usable)<RULES['registration_sources_min']:raise RuntimeError(f"only {len(usable)} usable references")
    delta=np.array([e['delta_px'] for _,e in usable]);theta=np.median(delta,axis=0)
    scatter=np.maximum(1.4826*np.median(np.abs(delta-theta),axis=0),RULES['registration_scatter_floor_px'])
    distance=np.linalg.norm((delta-theta)/scatter,axis=1)
    accepted=distance<=RULES['registration_mahalanobis_max']
    if accepted.sum()<RULES['registration_sources_min']:raise RuntimeError(f"only {accepted.sum()} references after robust gate")
    selected=[]
    for (r,e),keep in zip(usable,accepted):
        if keep:selected.append(r)
    result=gaia.fit_registration(frame,selected)
    result['rejected_source_ids']=[r['catalog']['source_id'] for (r,_),keep in zip(usable,accepted) if not keep]
    return result
