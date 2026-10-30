"""Fixed-final-weight per-exposure sandwich at a frozen candidate point."""
import numpy as np
from . import joint_motion as joint
from . import profile_uncertainty as profile

RULES={'minimum_exposures_per_epoch':8,'position_parameters':2,'steps_sky_px':[.002,.004],
       'maximum_hessian_relative_change':.05,'matrix_eigen_relative_cut':1e-10,
       'correction':'CR1p N/(N-2) for two profiled centroid parameters; empirical after nuisance profiling'}


def positive_full_rank(matrix):
    matrix=np.asarray(matrix,float)
    if matrix.shape!=(2,2) or not np.isfinite(matrix).all():return False
    eig=np.linalg.eigvalsh((matrix+matrix.T)/2)
    return bool(eig[-1]>0 and eig[0]>RULES['matrix_eigen_relative_cut']*eig[-1])


def compute(fit):
    """Return unsupported instead of inverting singular/unstable information."""
    samples=fit['samples'];n=len(samples);position=np.asarray(fit['position'],float)
    result={'supported':False,'n_exposures':n}
    if n<RULES['minimum_exposures_per_epoch']:return {**result,'reason':'too_few_exposures'}
    if not fit['success']:return {**result,'reason':'solver_failed'}
    if fit['at_boundary']:return {**result,'reason':'centroid_at_boundary'}
    if fit.get('information_rank',0)<2 or not np.isfinite(position).all():return {**result,'reason':'singular_point_information'}
    obs_ids=[s['frame']['record']['obs_id'] for s in samples]
    if len(set(obs_ids))!=n:return {**result,'reason':'duplicate_exposure'}
    h=RULES['steps_sky_px'][0];axes=np.eye(2)*h
    scores=[];jac_scores=[];hessians=[np.zeros((2,2)),np.zeros((2,2))];ids=[]
    try:
        for sample in samples:
            residual=lambda p:joint.residual_sample(sample,p)
            center=residual(position)
            plus=[residual(position+v) for v in axes];minus=[residual(position-v) for v in axes]
            score=np.array([(a@a-b@b)/(4*h) for a,b in zip(plus,minus)])
            jac=np.column_stack([(a-b)/(2*h) for a,b in zip(plus,minus)])
            scores.append(score);jac_scores.append(jac.T@center)
            ids.append(sample['frame']['record']['obs_id'])
            for j,step in enumerate(RULES['steps_sky_px']):hessians[j]+=profile.hessian(residual,position,step)
    except (ValueError,np.linalg.LinAlgError) as exc:return {**result,'reason':'score_or_hessian_exception','detail':str(exc)}
    scores=np.asarray(scores);jac_scores=np.asarray(jac_scores);change=float(np.linalg.norm(hessians[0]-hessians[1])/max(np.linalg.norm(hessians[1]),1e-15))
    meat=scores.T@scores
    difference=float(np.linalg.norm(scores-jac_scores));relative=difference/max(1.,float(np.linalg.norm(scores)))
    result.update(hessians=hessians,hessian_relative_step_change=change,meat=meat,
                  score_sum=scores.sum(axis=0),score_norm_sum=float(np.linalg.norm(scores,axis=1).sum()),
                  scalar_vs_residual_jacobian_difference=difference,scalar_vs_residual_jacobian_relative=relative,
                  exposures=[{'obs_id':ident,'score':score,'residual_jacobian_score':js} for ident,score,js in zip(ids,scores,jac_scores)],
                  correction_factor=n/(n-RULES['position_parameters']))
    if not np.isfinite(change) or change>RULES['maximum_hessian_relative_change']:return {**result,'reason':'unstable_profile_curvature'}
    if not positive_full_rank(hessians[0]):return {**result,'reason':'nonpositive_or_singular_hessian'}
    if not positive_full_rank(meat):return {**result,'reason':'nonpositive_or_singular_meat'}
    inverse=np.linalg.inv(hessians[0]);cov=result['correction_factor']*inverse@meat@inverse.T
    cov=(cov+cov.T)/2
    if not positive_full_rank(cov):return {**result,'reason':'nonpositive_or_singular_covariance'}
    return {**result,'supported':True,'covariance_px2':cov}
