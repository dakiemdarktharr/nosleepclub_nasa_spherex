"""Fixed-weight truth-point information probe; no centroid fitting."""
import numpy as np
from . import continuous_epsf_model as candidate
from . import profile_uncertainty as profile

DERIVATIVE_STEP = 0.00025
HESSIAN_STEPS = (0.002, 0.004)
RANK_RELATIVE = 1e-10


def projected_template(sample, point):
    p=candidate.baseline.motion.stamp_model(sample,np.asarray(point))[:,0]/sample['error']
    q=sample['q']
    return p-q@(q.T@p)


def geometry(samples, point, amplitudes):
    point=np.asarray(point,float);amplitudes=np.asarray(amplitudes,float)
    if point.shape!=(2,) or len(samples)!=len(amplitudes) or not len(samples):raise ValueError('invalid geometry input')
    entries=[];effective=np.zeros((2,2));known=np.zeros((2,2));expected_gn=np.zeros((2,2));score_cov=np.zeros((2,2));dof=0
    for sample, amplitude in zip(samples,amplitudes):
        p=projected_template(sample,point);information=float(p@p)
        if not np.isfinite(information) or information<1e-15 or not np.isfinite(amplitude):raise ValueError('unidentifiable target')
        delta=np.eye(2)*DERIVATIVE_STEP
        derivative=np.column_stack([(projected_template(sample,point+v)-projected_template(sample,point-v))/(2*DERIVATIVE_STEP) for v in delta])
        transverse=derivative-np.outer(p,p@derivative/information)
        matrix=transverse.T@transverse
        effective+=amplitude**2*matrix
        known+=amplitude**2*(derivative.T@derivative)
        expected_gn+=(amplitude**2+2/information)*matrix
        score_cov+=(amplitude**2+1/information)*matrix
        degree=len(p)-sample['rank']-1
        if degree<=0:raise ValueError('nonpositive residual degrees of freedom')
        dof+=degree
        entries.append({'sample':sample,'p':p,'D':derivative,'I':information,'transverse':transverse,'amplitude':float(amplitude)})
    eig=np.linalg.eigvalsh(effective)
    if not np.isfinite(eig).all() or eig[-1]<=0 or eig[0]<=RANK_RELATIVE*eig[-1]:raise ValueError('rank deficient Fisher information')
    return {'entries':entries,'point':point,'fisher_effective':effective,'fisher_known':known,
            'expected_jtj':expected_gn,'expected_score_covariance':score_cov,'dof':dof}


def residual(sample, point, data):
    p=projected_template(sample,point);q=sample['q']
    y=data/sample['error'];y=y-q@(q.T@y)
    info=p@p
    if not np.isfinite(info) or info<1e-15:raise ValueError('unidentifiable target')
    amplitude=(p@y)/info
    return amplitude*p-y


def trial(geom, data):
    if len(data)!=len(geom['entries']):raise ValueError('data length mismatch')
    arrays=[np.asarray(y,float) for y in data]
    blocks=[];jac=[];amplitudes=[]
    for entry,yraw in zip(geom['entries'],arrays):
        sample=entry['sample'];q=sample['q'];y=yraw/sample['error'];y=y-q@(q.T@y)
        p=entry['p'];D=entry['D'];info=entry['I'];a=float(p@y/info)
        r=a*p-y
        J=a*entry['transverse']-np.outer(p,D.T@r/info)
        blocks.append(r);jac.append(J);amplitudes.append(a)
    r=np.concatenate(blocks);J=np.concatenate(jac,axis=0)
    fun=lambda x:np.concatenate([residual(e['sample'],x,y) for e,y in zip(geom['entries'],arrays)])
    matrices=[profile.hessian(fun,geom['point'],h) for h in HESSIAN_STEPS]
    change=float(np.linalg.norm(matrices[0]-matrices[1])/max(np.linalg.norm(matrices[1]),1e-15))
    score=J.T@r
    return {'jtj':J.T@J,'hessians':matrices,'hessian_relative_step_change':change,
            'hessian_stable':bool(np.isfinite(matrices).all() and change<=.05),
            'profile_score':score,'score_q':float(score@np.linalg.solve(geom['fisher_effective'],score)),
            'profile_chi2':float(r@r),'dof':geom['dof'],
            'profile_amplitudes':amplitudes}


def normalized_trace(fisher,matrix):
    return float(np.trace(np.linalg.solve(fisher,matrix))/2)


def summarize(geom, rows, indices):
    """Quantities and bootstrap intervals for independent draw-level indices."""
    successful=[r for r in rows if 'failure' not in r]
    output={'attempts':len(rows),'successful':len(successful),'failures':len(rows)-len(successful),
            'failure_reasons':{k:sum(r.get('failure')==k for r in rows) for k in sorted({r['failure'] for r in rows if 'failure' in r})}}
    if not successful:return output
    fisher=geom['fisher_effective']
    for key in ['jtj','hessian_002','hessian_004']:
        if key=='jtj':mat=np.array([r['jtj'] for r in successful])
        else:mat=np.array([r['hessians'][0 if key=='hessian_002' else 1] for r in successful])
        traces=np.array([normalized_trace(fisher,m) for m in mat])
        # indices are generated once per case/condition and shared across epochs.
        valid_indices=indices if len(successful)==len(rows) else None
        interval=np.quantile(traces[valid_indices].mean(axis=1),[.025,.975]).tolist() if valid_indices is not None else None
        output[key]={'mean_matrix':mat.mean(axis=0),'normalized_trace':float(traces.mean()),'draw_bootstrap_95':interval}
    scores=np.array([r['profile_score'] for r in successful]);chi=np.array([r['profile_chi2'] for r in successful])
    score_interval=np.quantile(scores[indices].mean(axis=1),[.025,.975],axis=0) if len(successful)==len(rows) else None
    output.update(mean_score=scores.mean(axis=0), score_covariance=np.cov(scores,rowvar=False),
                  mean_score_draw_bootstrap_95=score_interval,
                  mean_score_q=float(np.mean([r['score_q'] for r in successful])),
                  mean_chi2=float(chi.mean()),mean_reduced_chi2=float(chi.mean()/geom['dof']),
                  hessian_stable=sum(r['hessian_stable'] for r in successful),dof=geom['dof'],
                  bootstrap_note='draw-level bootstrap uses shared resampling indices across both epochs; omitted if any draw failed')
    return output
