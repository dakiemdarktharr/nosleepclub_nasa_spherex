"""Audit completed locked neighbor study and publish conditional diagnostics.

The only image-dependent replay evaluates the fixed semantic renderer at saved
positions; no nonlinear optimizer, new random draw, or new field is used.
"""
from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess

# Match the frozen study's CLI thread request before importing numerical
# libraries. Importing this module as a library never mutates the caller's env.
_THREAD_KEYS=('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','BLIS_NUM_THREADS','VECLIB_MAXIMUM_THREADS')
if __name__=='__main__':
    for _key in _THREAD_KEYS:os.environ[_key]='1'

import numpy as np
from astropy import units as u
from scipy.optimize import lsq_linear

from . import run_neighbor_intervention as study
from . import run_wise_linked_study as legacy
from . import neighbor_intervention_inputs as adapter
from . import wise_linked_inputs as inputs
from .science_jobs import atomic


ROOT=study.ROOT
RAW=study.OUTPUT
DESIGN=study.DESIGN
REAL_OUT=ROOT/'web/data/neighbor-intervention/development.json'
CONTROLS_OUT=ROOT/'web/data/neighbor-intervention/controls.json'
OVERVIEW_OUT=ROOT/'web/data/neighbor-intervention/overview.json'
COMMIT='32573ad53d6cafa47ef2cc79b0971b22bd3203bd'
DESIGN_SHA='119f7d628c716f7e372778bf9983ecbfc5c256c02b9b32aebc7972de819f57d6'
T=np.asarray(inputs.gaia.TRANSFORM,float)
ARMS=study.CONTROL_VARIANTS
RTOL=1e-7
ATOL=1e-9
MODE_COST_RTOL=2e-9
MODE_COST_ATOL=1e-7


def close(a,b,label,rtol=RTOL,atol=ATOL):
    a=np.asarray(a,float);b=np.asarray(b,float)
    if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all() or not np.allclose(a,b,rtol=rtol,atol=atol):
        raise ValueError('audit mismatch: '+label)


def recursive_equal(a,b,label):
    if isinstance(a,dict) and isinstance(b,dict):
        if set(a)!=set(b):raise ValueError('audit keys mismatch: '+label)
        for k in a:recursive_equal(a[k],b[k],label+'.'+k)
    elif isinstance(a,(list,tuple)) and isinstance(b,(list,tuple)):
        if len(a)!=len(b):raise ValueError('audit length mismatch: '+label)
        for i,(x,y) in enumerate(zip(a,b)):recursive_equal(x,y,label+'['+str(i)+']')
    elif isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)) and not isinstance(b,bool):
        close(a,b,label)
    elif a!=b:raise ValueError('audit mismatch: '+label)


def audit_keys(report):
    if not report.get('completed'):raise ValueError('study incomplete')
    rows=report['records'];expected=study.expected_keys()
    keyed={study.record_key(r):r for r in rows}
    if len(rows)!=len(expected) or len(keyed)!=len(rows) or set(keyed)!=expected:
        raise ValueError('incomplete, duplicate, or unknown study attempts')
    for row in rows:
        if row['record_sha256']!=sha256(legacy.encoded({k:v for k,v in row.items() if k!='record_sha256'})).hexdigest():
            raise ValueError('attempt checksum mismatch')
        if row['status'] not in ('fit_completed','fit_failed','preparation_failed') or (row['status']!='fit_completed' and not row.get('error')):
            raise ValueError('unknown status or missing error')
    counts={'planned':len(expected),'recorded':len(rows),'fit_completed':sum(x['status']=='fit_completed' for x in rows),
            'failed':sum(x['status']!='fit_completed' for x in rows)}
    if counts!=report['counts']:raise ValueError('attempt count mismatch')
    return keyed


def audit_modes(fit):
    audit=fit['final_mode_audit'];starts=audit['starts']
    if len(starts)!=9:raise ValueError('final mode starts missing')
    anchor=np.asarray(study.RULES['anchor'])
    for row,offset in zip(starts,study.model.START_OFFSETS):
        if row.get('stage')!='final_fixed_weights' or not isinstance(row.get('success'),bool):raise ValueError('final mode start status invalid')
        close(row['start'],anchor+offset,'final mode starting point')
    cost=float(fit['chi2_weighted']);close(audit['point_chi2'],cost,'mode point cost')
    successful=[r for r in starts if r['success']]
    candidates=[{'position':np.asarray(fit['position'],float),'chi2':cost,'origin':'point'}]
    for row in successful:
        pos=np.asarray(row['position'],float)
        if pos.shape!=(2,) or not np.isfinite(pos).all() or not np.isfinite(row['chi2']):raise ValueError('invalid mode candidate')
        candidates.append({'position':pos,'chi2':float(row['chi2']),'origin':'start'})
    candidates.sort(key=lambda x:x['chi2']);modes=[]
    for candidate in candidates:
        group=next((m for m in modes if np.linalg.norm(candidate['position']-m['position'])<=.15),None)
        if group is None:modes.append({**candidate,'member_count':1})
        else:group['member_count']+=1
    for m in modes:
        m['delta_chi2']=m['chi2']-modes[0]['chi2'];m['position']=m['position'].tolist()
    near=[m for m in modes if m['delta_chi2']<=5.991]
    recursive_equal(modes,audit['modes'],'final modes');recursive_equal(near,audit['near_best_modes'],'near modes')
    improvement=cost-min((r['chi2'] for r in successful),default=cost)
    close(improvement,audit['best_improvement_chi2'],'mode improvement')
    if (audit['all_starts_failed']!=(not successful) or audit['near_best_count']!=len(near)
            or audit['better_than_point']!=(improvement>1e-4)):
        raise ValueError('mode status mismatch')
    return {'near_best_count':len(near),'all_starts_failed':not successful,'better_than_point':improvement>1e-4,
            'failed_final_starts':len(starts)-len(successful)}


def independent_cost_at_position(samples,items,weights,position,nonnegative):
    """Solve each saved-pixel WLS by independent column-scaled SciPy BVLS.

    This profiles linear coefficients only at a given saved 2D position. It
    neither calls the frozen profile kernel nor optimizes the position.
    """
    if len(samples)!=len(items) or len(samples)!=len(weights) or not samples:
        raise ValueError('mode replay frame count mismatch')
    position=np.asarray(position,float)
    if position.shape!=(2,) or not np.isfinite(position).all():raise ValueError('mode replay invalid position')
    frame_costs=[]
    for sample,item,weight in zip(samples,items,weights):
        y=np.asarray(sample['data_mjysr'],float);error=np.asarray(sample['error_mjysr'],float)
        background=np.asarray(sample['background_design'],float);neighbor=np.asarray(sample['neighbor_design_per_jy'],float)
        w=np.asarray(weight,float)
        target=np.asarray(item['renderer'](position).to_value(u.MJy/u.sr/u.Jy),float)
        if y.ndim!=1 or background.ndim!=2 or neighbor.ndim!=2:
            raise ValueError('mode replay invalid frame dimensions')
        n=len(y);p=1+background.shape[1];q=neighbor.shape[1]
        if (not n or error.shape!=(n,) or w.shape!=(n,) or target.shape!=(n,)
                or background.shape[0]!=n or neighbor.shape[0]!=n
                or not all(np.isfinite(v).all() for v in (y,error,w,target,background,neighbor))
                or np.any(error<=0) or np.any(w<=0) or np.any(w>1)):
            raise ValueError('mode replay invalid frame arrays')
        white=np.sqrt(w)/error
        design=np.column_stack((target,background,neighbor))*white[:,None]
        # Normalize in two stages so tiny or large physical units do not
        # disappear in a norm. BVLS bounds then apply to the same physical
        # columns because every scale factor is strictly positive.
        maximum=np.max(np.abs(design),axis=0)
        if not np.isfinite(maximum).all() or np.any(maximum<=0):raise ValueError('mode replay zero design column')
        normalized=design/maximum;norms=np.linalg.norm(normalized,axis=0);normalized=normalized/norms
        singular=np.linalg.svd(normalized,compute_uv=False)
        if len(singular)!=p+q or singular[-1]<=1e-10*singular[0]:raise ValueError('mode replay rank deficient')
        wy=y*white;yscale=float(np.max(np.abs(wy)))
        if not np.isfinite(yscale):raise ValueError('mode replay invalid weighted data')
        if yscale==0:
            frame_costs.append(0.);continue
        lower=np.r_[np.full(p,-np.inf),np.zeros(q) if nonnegative else np.full(q,-np.inf)]
        try:
            solution=lsq_linear(normalized,wy/yscale,bounds=(lower,np.full(p+q,np.inf)),
                                method='bvls',tol=1e-12,max_iter=max(100,10*(p+q)))
        except (ValueError,np.linalg.LinAlgError) as exc:
            raise ValueError('independent mode BVLS failed') from exc
        if (not solution.success or not np.isfinite(solution.x).all() or not np.isfinite(solution.optimality)
                or solution.optimality>1e-8 or (nonnegative and np.any(solution.x[p:]<0))):
            raise ValueError('independent mode BVLS not optimal')
        residual=(wy/yscale-normalized@solution.x)*yscale
        cost=float(residual@residual)
        if not np.isfinite(cost):raise ValueError('independent mode cost invalid')
        frame_costs.append(cost)
    return float(sum(frame_costs)),frame_costs


def replay_final_starts(row,items):
    fit=row['fit'];starts=fit['final_mode_audit']['starts'];weights=[f['weights'] for f in fit['frames']]
    results=[]
    for index,start in enumerate(starts):
        if not start['success']:
            results.append({'index':index,'success':False,'replayed':False,
                            'failure_message':start.get('message')})
            continue
        cost,frames=independent_cost_at_position(row['samples'],items,weights,start['position'],fit['nonnegative_neighbors'])
        recorded=float(start['chi2']);difference=abs(cost-recorded)
        tolerance=MODE_COST_ATOL+MODE_COST_RTOL*abs(recorded)
        if difference>tolerance:
            raise ValueError(f'independent mode cost mismatch at start {index}: difference {difference} > {tolerance}')
        results.append({'index':index,'success':True,'replayed':True,'position':start['position'],
                        'recorded_chi2':recorded,'replayed_chi2':cost,'frame_chi2':frames,
                        'absolute_difference':difference,'tolerance':tolerance})
    successful=[r for r in results if r['success']]
    return {'successful_start_count':len(successful),'failed_start_count':len(results)-len(successful),
            'max_absolute_difference':max((r['absolute_difference'] for r in successful),default=None),
            'cost_rtol':MODE_COST_RTOL,'cost_atol':MODE_COST_ATOL,'starts':results,
            'qualification':'independent scaled BVLS at saved successful final-start positions; no positional optimization or mode replacement'}


def audit_frame(sample,frame,target,nonnegative,obs_id):
    data=np.asarray(sample['data_mjysr'],float);error=np.asarray(sample['error_mjysr'],float)
    bg=np.asarray(sample['background_design'],float);neigh=np.asarray(sample['neighbor_design_per_jy'],float)
    weights=np.asarray(frame['weights'],float);target=np.asarray(target,float)
    n=len(data);q=len(sample['neighbor_ids'])
    if (data.ndim!=1 or not n or error.shape!=(n,) or weights.shape!=(n,) or target.shape!=(n,)
            or bg.ndim!=2 or bg.shape[0]!=n or neigh.shape!=(n,q)
            or len(sample['x'])!=n or len(sample['y'])!=n or len(set(sample['neighbor_ids']))!=q):
        raise ValueError('frame shape or semantic ID mismatch')
    try:neighbor_unit=u.Unit(sample['neighbor_unit'])
    except (TypeError,ValueError) as exc:raise ValueError('invalid neighbor unit') from exc
    if neighbor_unit!=u.MJy/u.sr/u.Jy:raise ValueError('neighbor unit scale mismatch')
    if (not all(np.isfinite(x).all() for x in (data,error,weights,target,bg,neigh)) or np.any(error<=0)
            or np.any(weights<=0) or np.any(weights>1) or frame['obs_id']!=obs_id
            or frame['neighbor_ids']!=sample['neighbor_ids']):raise ValueError('invalid frame arrays or ID')
    close(frame['error'],error,'frame original error');close(frame['weights'],weights,'weights')
    target_flux=float(frame['target_flux_jy']);beta=np.asarray(frame['background_coefficients'],float)
    neighbor_flux=np.asarray(frame['neighbor_flux_jy'],float)
    if beta.shape!=(bg.shape[1],) or neighbor_flux.shape!=(q,) or not np.isfinite(target_flux):raise ValueError('frame coefficient shape')
    signal=target_flux*target+bg@beta+neigh@neighbor_flux
    residual=data-signal;raw=residual/error;whiten=np.sqrt(weights)/error;weighted=residual*whiten
    close(signal,frame['model'],'frame model');close(residual,frame['residual'],'frame residual')
    close(raw,frame['raw_standardized_residual'],'raw standardized residual')
    close(weighted,frame['weighted_residual'],'weighted residual')
    chi=float(weighted@weighted);close(chi,frame['chi2_weighted'],'frame chi2')
    if frame['negative_target_flux']!=(target_flux<0):raise ValueError('negative target flag mismatch')
    if nonnegative:
        active=np.asarray(frame['neighbor_active_mask'])
        if active.dtype!=np.dtype(bool) or active.shape!=(q,) or np.any(neighbor_flux<0) or not np.array_equal(active,neighbor_flux==0):
            raise ValueError('nonnegative neighbor/active mismatch')
    else:
        if frame['neighbor_active_mask'] is not None:raise ValueError('free neighbor cannot have active mask')
        active=np.zeros(q,bool)
    design=np.column_stack((target,bg,neigh))*whiten[:,None]
    norms=np.linalg.norm(design,axis=0)
    if not np.isfinite(norms).all() or np.any(norms<=0):raise ValueError('zero/invalid design column')
    X=design/norms;s=np.linalg.svd(X,compute_uv=False)
    if len(s)!=1+bg.shape[1]+q or s[-1]<=1e-10*s[0] or frame['linear_rank']!=len(s):raise ValueError('frame rank mismatch')
    close(frame['scaled_condition'],s[0]/s[-1],'condition')
    scale=float(np.max(np.abs(data*whiten)))
    gradient=X.T@(weighted/scale if scale else weighted)
    split=1+bg.shape[1] if nonnegative else len(gradient)
    close(gradient[:split],frame['scaled_gradient_free'],'free gradient')
    close(gradient[split:],frame['scaled_gradient_nonnegative'],'neighbor gradient')
    gf=float(np.max(np.abs(gradient[:split]))) if split else 0.
    g=gradient[split:];dual=float(np.max(np.maximum(g[active],0))) if np.any(active) else 0.
    interior=float(np.max(np.abs(g[~active]))) if len(g) and np.any(~active) else 0.
    neighbor_theta=neighbor_flux*norms[split:] if nonnegative else np.empty(0)
    denom=max(scale,float(np.max(neighbor_theta)) if len(neighbor_theta) else 0.)
    comp=float(np.max(np.abs(neighbor_theta/denom*g))) if len(g) and denom else 0.
    for name,value in [('scaled_free_stationarity_violation',gf),('scaled_bound_dual_violation',dual),
                       ('scaled_interior_stationarity_violation',interior),('scaled_complementarity_violation',comp)]:close(value,frame[name],name)
    if max(gf,dual,interior,comp)>1e-8+1e-12:raise ValueError('KKT violation')
    next_weight=np.minimum(1.,2.5/np.maximum(np.abs(raw),1e-300))
    return {'obs_id':frame['obs_id'],'raw_chi2':float(raw@raw),'weighted_chi2':chi,
            'next_weight_max_difference':float(np.max(np.abs(next_weight-weights))),
            'negative_target_flux':target_flux<0,'neighbor_count':q,'active_neighbor_count':int(active.sum()),
            'max_scaled_kkt_violation':max(gf,dual,interior,comp)}


def audit_fit(row,items):
    fit=row['fit'];samples=row['samples'];frames=fit['frames'];nonnegative=fit['nonnegative_neighbors']
    variant=next(v for v in study.VARIANTS if v['id']==row['variant'])
    if nonnegative!=variant['nonnegative_neighbors'] or fit['data_unit']!='MJy / sr':raise ValueError('fit mode or unit mismatch')
    if (not samples or len(samples)!=len(frames) or len(items)!=len(samples)
            or [x['obs_id'] for x in frames]!=row['obs_ids'] or [x['obs_id'] for x in items]!=row['obs_ids']):
        raise ValueError('frame count/order mismatch')
    position=np.asarray(fit['position'],float)
    if position.shape!=(2,) or not np.isfinite(position).all():raise ValueError('invalid point position')
    frame_audits=[]
    for sample,frame,item,obs_id in zip(samples,frames,items,row['obs_ids']):
        metadata=item['metadata']
        for key in ('x','y','neighbor_ids'):
            expected=item['neighbor_ids'] if key=='neighbor_ids' else metadata[key]
            if sample[key]!=expected:raise ValueError('semantic '+key+' mismatch')
        close(sample['background_design'],item['background_design'],'background design')
        close(sample['neighbor_design_per_jy'],item['neighbor_design'],'neighbor design')
        for key in ('raw_sha256','cutout_url','renderer_provenance'):
            # Renderer provenance appears in the old prepared item; semantic
            # metadata retains exact cutout provenance and the PSF descriptor.
            if key in metadata and sample[key]!=metadata[key]:raise ValueError('semantic '+key+' mismatch')
        for key in ('target_shape_anchor_sky_px','target_shape_native_xy','target_spatial_epsf','neighbors','spatial_epsf','background_degree'):
            if key in metadata:recursive_equal(sample[key],metadata[key],'semantic metadata '+key)
        if row['section']=='real':
            close(sample['data_mjysr'],item['data'],'real native data')
            close(sample['error_mjysr'],item['error'],'real native error')
        target=item['renderer'](position).to_value(u.MJy/u.sr/u.Jy)
        frame_audits.append(audit_frame(sample,frame,target,nonnegative,obs_id))
    close(sum(x['weighted_chi2'] for x in frame_audits),fit['chi2_weighted'],'total weighted chi2')
    close(sum(x['raw_chi2'] for x in frame_audits),fit['chi2_raw'],'total raw chi2')
    close(np.concatenate([np.asarray(f['weighted_residual']) for f in frames]),fit['weighted_residual'],'concatenated residual')
    next_diff=max(x['next_weight_max_difference'] for x in frame_audits)
    close(next_diff,fit['irls']['next_weight_max_difference'],'IRLS next weight')
    # The independently reconstructed weight delta is verified above. Apply
    # thresholds to the saved value to avoid flipping a boundary due only to
    # replay rounding inside the declared audit tolerance.
    irls=fit['irls'];converged=irls['next_weight_max_difference']<=.001 and irls['position_max_change']<=.0001
    if (irls['converged']!=converged or not 2<=irls['iterations']<=irls['max_iterations'] or irls['max_iterations']!=20
            or irls['weight_tolerance']!=.001 or irls['position_tolerance_px']!=.0001):
        raise ValueError('IRLS convergence mismatch')
    starts=fit['start_reports'];initial=starts[:9];updates=starts[9:]
    if len(initial)!=9 or len(updates)!=irls['iterations']:raise ValueError('start/IRLS attempt count mismatch')
    anchor=np.asarray(study.RULES['anchor'])
    for one,offset in zip(initial,study.model.START_OFFSETS):
        if one.get('stage')!='initial' or not isinstance(one.get('success'),bool):raise ValueError('initial start status invalid')
        close(one['start'],anchor+offset,'initial starting point')
    successful=[x for x in initial if x['success']]
    if not successful:raise ValueError('fit completed without successful initial start')
    selected=min(successful,key=lambda x:float(x['chi2']))
    previous=selected['position']
    for index,one in enumerate(updates,1):
        if one.get('stage')!='irls_'+str(index) or one.get('success') is not True:raise ValueError('IRLS attempt status mismatch')
        close(one['start'],previous,'IRLS start position');previous=one['position']
    close(previous,position,'final IRLS position')
    close(float(np.max(np.abs(np.asarray(updates[-1]['position'])-updates[-1]['start']))),irls['position_max_change'],'IRLS position difference')
    mode=audit_modes(fit)
    mode_replay=replay_final_starts(row,items)
    boundary=bool(np.any(np.abs(position-np.asarray(study.RULES['anchor']))>=.95*2.5))
    if fit['at_boundary']!=boundary or fit['position_rank'] not in (0,2):raise ValueError('boundary/rank mismatch')
    reasons=[]
    if boundary:reasons.append('boundary')
    if fit['position_rank']<2:reasons.append('position_rank')
    if not converged:reasons.append('irls_not_converged')
    if mode['all_starts_failed']:reasons.append('final_mode_audit_failed')
    if mode['better_than_point']:reasons.append('better_final_weight_mode')
    if mode['near_best_count']>1:reasons.append('multiple_near_best_modes')
    if fit['numerical_reasons']!=reasons or fit['numerical_support']!=(not reasons):raise ValueError('numerical support mismatch')
    return {'frames':frame_audits,'mode_audit':mode,'mode_objective_replay':mode_replay,
            'numerical_support':not reasons,'numerical_reasons':reasons,
            'next_weight_max_difference':next_diff,'qualification':'saved-point model/KKT and successful final-start objectives independently replayed; position Jacobian/rank not independently recomputed'}


def check_contrast(a,b):
    """Check fixed physical columns, pixels and data when both were saved."""
    sa=a.get('samples');sb=b.get('samples')
    if not sa or not sb:return False
    if a['obs_ids']!=b['obs_ids'] or len(sa)!=len(sb) or len(sa)!=len(a['obs_ids']):
        raise ValueError('paired frame order mismatch')
    keys=('x','y','data_mjysr','error_mjysr','background_design','neighbor_design_per_jy',
          'neighbor_unit','neighbor_ids','spatial_epsf','background_degree','raw_sha256','cutout_url')
    for x,y in zip(sa,sb):
        for key in keys:
            if x[key]!=y[key]:raise ValueError('paired fixed input differs: '+key)
        for key in ('target_shape_anchor_sky_px','target_shape_native_xy','target_spatial_epsf','neighbors'):
            if key in x or key in y:
                if x.get(key)!=y.get(key):raise ValueError('paired source shape differs: '+key)
    if a['section']=='control':
        if not a.get('control',{}).get('realization_sha256') or a['control']['realization_sha256']!=b.get('control',{}).get('realization_sha256'):
            raise ValueError('paired control realization mismatch')
    return True


def check_control(row,geometries):
    if not row.get('samples'):
        return {'available':False,'reason':'no prepared control samples'}
    meta=row['control'];samples=row['samples'];epoch=0 if row['epoch']=='before' else 1
    truth=np.asarray(study.RULES['controls']['before_position'])+epoch*np.asarray(study.RULES['controls']['displacement_sky_px'])
    close(meta['truth_position_sky_px'],truth,'control truth')
    if len(samples)!=len(geometries) or len(meta['frames'])!=len(samples) or len(row['obs_ids'])!=len(samples):
        raise ValueError('control frame count mismatch')
    realized=[{'obs_id':obs,'data':s['data_mjysr'],'error':s['error_mjysr']} for obs,s in zip(row['obs_ids'],samples)]
    if sha256(legacy.encoded(realized)).hexdigest()!=meta['realization_sha256']:raise ValueError('control realization hash mismatch')
    case_index=next(i for i,c in enumerate(study.CASES) if c['id']==row['case']);case=study.CASES[case_index]
    for index,(s,m,g,obs) in enumerate(zip(samples,meta['frames'],geometries,row['obs_ids'])):
        if m['obs_id']!=obs or g['obs_id']!=obs:raise ValueError('control frame identity mismatch')
        seed=[study.RULES['controls']['seed_prefix'],case_index,row['draw'],epoch,index]
        if m['seed']!=seed or m['provenance']['rng_bit_generator']!='PCG64':raise ValueError('control seed provenance mismatch')
        initial=legacy.jsonable(np.random.PCG64(np.random.SeedSequence(seed)).state)
        if m['provenance']['rng_state_before']!=initial or m['provenance']['source_ramp']['rng_state_before']!=initial:
            raise ValueError('control initial RNG state mismatch')
        close(m['pixel_omega_sr'],g['omega'].to_value(u.sr),'control pixel omega',atol=1e-20)
        close(m['gain_mjysr_per_electron_rate'],g['gain'].to_value(study.control.GAIN),'control pixel gain')
        source=m['per_source']
        if len(source)!=1+len(g['neighbors']):raise ValueError('control source count mismatch')
        position=inputs.native_position(g['frame'],truth)
        close(source[0]['native_xy'],position,'control target position')
        close(source[0]['flux_jy'],case['target_flux_jy'],'control target flux',atol=1e-15)
        close(source[0]['sigma_xy_native_pixels'],study.RULES['controls']['target_sigma_xy_native'],'target Gaussian sigma')
        for i,(one,neighbor) in enumerate(zip(source[1:],g['neighbors'])):
            close(one['native_xy'],neighbor['native_xy'],'control neighbor position')
            close(one['flux_jy'],.00015/(1+i),'control neighbor flux',atol=1e-15)
            close(one['sigma_xy_native_pixels'],study.RULES['controls']['neighbor_sigma_xy_native'],'neighbor Gaussian sigma')
        specification=[{'native_xy':x['native_xy'],'flux':x['flux_jy']*u.Jy,'sigma_xy':x['sigma_xy_native_pixels']} for x in source]
        expected=study.control.expected_scene(specification,g['x'],g['y'],g['omega'])
        close(expected['expected_source'].to_value(u.MJy/u.sr),m['expected_source_mjysr'],'Gaussian expected source')
        recursive_equal(expected['per_source'],source,'Gaussian finite-window flux')
        base=g['background'];background=base@np.asarray(study.RULES['controls']['background_plane_coefficients_mjysr'])
        if case['background']=='quadratic':
            background+=np.column_stack((base[:,1]**2,base[:,1]*base[:,2],base[:,2]**2))@np.asarray(study.RULES['controls']['quadratic_coefficients_mjysr'])
        close(background,m['background_mjysr'],'control mean background')
        header=study.control.ramp._header_values(g['frame']['image_header'])
        recursive_equal(header,m['provenance']['source_ramp']['header'],'control ramp timing')
        expected_source=np.asarray(m['expected_source_mjysr']);gain=np.asarray(m['gain_mjysr_per_electron_rate'])
        source_noise=np.asarray(m['source_noise_mjysr'],float)
        observed=np.asarray(s['data_mjysr'],float)
        if source_noise.shape!=observed.shape or not np.isfinite(source_noise).all() or not np.isfinite(observed).all():
            raise ValueError('invalid recorded synthetic source noise')
        implied_background_noise=observed-expected_source-background-source_noise
        if not np.isfinite(implied_background_noise).all():raise ValueError('invalid implied background noise')
        ramp_meta=m['provenance']['source_ramp']
        if (ramp_meta['source_values_sha256']!=study.control.ramp._digest_array(expected_source[None,:],'<f8')
                or ramp_meta['gain_values_sha256']!=study.control.ramp._digest_array(gain[None,:],'<f8')
                or ramp_meta['valid_mask_sha256']!=study.control.ramp._digest_array(np.ones((1,len(gain)),bool),'u1')):
            raise ValueError('control ramp input hashes mismatch')
        variance=study.control.ramp.poisson_factor(header['n'])*gain*expected_source/header['nominal_pipeline_integration_seconds']
        close(variance,m['added_variance_mjysr2'],'oracle source variance',atol=1e-15)
        close(np.hypot(g['error'],np.sqrt(variance)),s['error_mjysr'],'oracle fitting errors')
    return {'available':True,'realization_sha256':meta['realization_sha256'],
            'qualification':'no RNG redrawn; source mean, gain, per-pixel omega, ramp variance, error and stored realization hash checked'}


def attempt_compact(row,audit=None):
    out={'status':row['status'],'record_sha256':row['record_sha256'],'obs_ids':row['obs_ids'],
         'error':row.get('error'),'failure_stage':row.get('failure_stage')}
    if row['section']=='control':
        out['realization_sha256']=row.get('control',{}).get('realization_sha256')
        out['truth_position_sky_px']=(np.asarray(study.RULES['controls']['before_position'])+
            (row['epoch']=='after')*np.asarray(study.RULES['controls']['displacement_sky_px'])).tolist()
    if row['status']=='fit_completed':
        f=row['fit'];out.update(position_sky_px=f['position'],numerical_support=f['numerical_support'],
            numerical_reasons=f['numerical_reasons'],irls=f['irls'],at_boundary=f['at_boundary'],
            position_rank=f['position_rank'],mode_audit=f['final_mode_audit'],
            frames=[{'obs_id':v['obs_id'],'target_flux_jy':v['target_flux_jy'],
                     'negative_target_flux':v['negative_target_flux'],'neighbor_ids':v['neighbor_ids'],
                     'neighbor_flux_jy':v['neighbor_flux_jy'],'neighbor_active_mask':v['neighbor_active_mask']} for v in f['frames']],
            audit=audit)
    else:out['start_reports']=row.get('start_reports',[])
    return out


def real_summary(keyed):
    out=[]
    for config in study.RULES['configurations']:
        pairs=[]
        for variant in study.VARIANTS:
            before=keyed[('real',config,variant['id'],'before')];after=keyed[('real',config,variant['id'],'after')]
            successes=before['status']=='fit_completed' and after['status']=='fit_completed'
            vector=(T@(np.asarray(after['fit']['position'])-before['fit']['position'])).tolist() if successes else None
            supported=bool(successes and before['fit']['numerical_support'] and after['fit']['numerical_support'])
            pairs.append({'variant':variant['id'],'background_order':variant['background_order'],
                'epsf_kind':variant['epsf_kind'],'nonnegative_neighbors':variant['nonnegative_neighbors'],
                'before_status':before['status'],'after_status':after['status'],
                'before_reasons':before['fit']['numerical_reasons'] if before['status']=='fit_completed' else [before.get('error')],
                'after_reasons':after['fit']['numerical_reasons'] if after['status']=='fit_completed' else [after.get('error')],
                'epochs':{e:{'status':r['status'],'failure':r.get('error'),'failure_stage':r.get('failure_stage'),
                             'numerical_support':r['fit']['numerical_support'] if r['status']=='fit_completed' else False,
                             'numerical_reasons':r['fit']['numerical_reasons'] if r['status']=='fit_completed' else []}
                          for e,r in [('before',before),('after',after)]},
                'east_north_arcsec':vector,'numerical_support_both':supported})
        points=[p for p in pairs if p['east_north_arcsec'] is not None]
        baseline=next((p for p in points if p['variant']==study.CONTROL_VARIANTS[0]),None)
        for p in pairs:
            p['change_from_primary_control_arcsec']=(float(np.linalg.norm(np.asarray(p['east_north_arcsec'])-baseline['east_north_arcsec']))
                if baseline and p['east_north_arcsec'] is not None else None)
        distances=[(float(np.linalg.norm(np.asarray(x['east_north_arcsec'])-y['east_north_arcsec'])),x['variant'],y['variant']) for i,x in enumerate(points) for y in points[i+1:]]
        maximum=max(distances,key=lambda x:x[0]) if distances else None
        epoch_counts={}
        for e in ('before','after'):
            groups=[tuple(keyed[('real',config,v['id'],e)]['obs_ids']) for v in study.VARIANTS if keyed[('real',config,v['id'],e)]['obs_ids']]
            if groups and any(x!=groups[0] for x in groups):raise ValueError('real frame selection differs across variants')
            epoch_counts[e]=len(groups[0]) if groups else None
        reason_counts={}
        for v in study.VARIANTS:
            for e in ('before','after'):
                r=keyed[('real',config,v['id'],e)]
                labels=r['fit']['numerical_reasons'] if r['status']=='fit_completed' else [r['status']]
                for label in labels:reason_counts[label]=reason_counts.get(label,0)+1
        out.append({'configuration':config,'frames_per_epoch':epoch_counts,'pairs':pairs,
                    'complete_pairs':len(points),'numerical_supported_pairs':sum(p['numerical_support_both'] for p in pairs),
                    'refusal_counts':reason_counts,'refusal_counts_are_nonexclusive':True,
                    'max_pairwise_spread_arcsec':maximum[0] if maximum else None,
                    'max_pairwise_variants':list(maximum[1:]) if maximum else None,
                    'spread_basis':'all completed pairs, including numerical refusals; model sensitivity only'})
    return out


def _metrics(values):
    if not values:return {'n':0,'rms_arcsec':None,'p90_arcsec':None,'mean_error_east_north_arcsec':None}
    x=np.asarray(values,float);radial=np.linalg.norm(x,axis=1)
    return {'n':len(x),'rms_arcsec':float(np.sqrt(np.mean(radial**2))),
            'p90_arcsec':float(np.percentile(radial,90)),'mean_error_east_north_arcsec':x.mean(axis=0).tolist()}


def control_summary(keyed,audits):
    cases=[];public=[];truth=np.asarray(study.RULES['controls']['displacement_sky_px']);truth_en=T@truth
    for case in study.CASES:
        draws=[]
        for draw in range(study.RULES['controls']['draws_per_case']):
            arm_results={}
            for arm in ARMS:
                rows=[keyed[('control',case['id'],str(draw),arm,e)] for e in ('before','after')]
                complete=all(r['status']=='fit_completed' for r in rows)
                supported=bool(complete and all(r['fit']['numerical_support'] for r in rows))
                error=(T@(np.asarray(rows[1]['fit']['position'])-rows[0]['fit']['position']-truth)).tolist() if complete else None
                arm_results[arm]={'completed':complete,'numerical_support_both':supported,
                    'error_east_north_arcsec':error,'error_arcsec':float(np.linalg.norm(error)) if complete else None,
                    'epochs':{e:attempt_compact(r,audits.get(study.record_key(r))) for e,r in zip(('before','after'),rows)}}
            draws.append({'case':case['id'],'draw':draw,'truth_displacement_sky_px':truth.tolist(),
                          'truth_displacement_east_north_arcsec':truth_en.tolist(),'arms':arm_results})
        common=[d for d in draws if all(d['arms'][a]['completed'] for a in ARMS)]
        supported=[d for d in draws if all(d['arms'][a]['numerical_support_both'] for a in ARMS)]
        arms=[]
        for arm in ARMS:
            selected=[d for d in draws if d['arms'][arm]['completed']]
            epoch_records=[d['arms'][arm]['epochs'][e] for d in draws for e in ('before','after')]
            completed_epochs=[r for r in epoch_records if r['status']=='fit_completed']
            attempts={'planned_pairs':len(draws),'planned_epochs':len(epoch_records),
                      'completed_epochs':len(completed_epochs),'failed_epochs':len(epoch_records)-len(completed_epochs),
                      'completed_pairs':len(selected),'numerically_supported_pairs':sum(d['arms'][arm]['numerical_support_both'] for d in draws),
                      'negative_target_frame_count':sum(f['negative_target_flux'] for r in completed_epochs for f in r['frames']),
                      'active_neighbor_coefficient_count':sum(sum(f['neighbor_active_mask'] or []) for r in completed_epochs for f in r['frames']),
                      'epochs_with_multiple_near_modes':sum(r['mode_audit']['near_best_count']>1 for r in completed_epochs)}
            arms.append({'variant':arm,'attempts':attempts,'selections':{
                'all_completed':_metrics([d['arms'][arm]['error_east_north_arcsec'] for d in selected]),
                'common_completed':_metrics([d['arms'][arm]['error_east_north_arcsec'] for d in common]),
                'common_numerically_supported':_metrics([d['arms'][arm]['error_east_north_arcsec'] for d in supported])}})
        paired={}
        for name,selection in [('common_completed',common),('common_numerically_supported',supported)]:
            if selection:
                a=np.asarray([d['arms'][ARMS[0]]['error_east_north_arcsec'] for d in selection]);b=np.asarray([d['arms'][ARMS[1]]['error_east_north_arcsec'] for d in selection])
                delta_rms=float(np.sqrt(np.mean(np.sum(b*b,axis=1)))-np.sqrt(np.mean(np.sum(a*a,axis=1))))
                delta_radial=float(np.mean(np.linalg.norm(b,axis=1)-np.linalg.norm(a,axis=1)))
            else:delta_rms=delta_radial=None
            paired[name]={'n':len(selection),'rms_difference_nonnegative_minus_free_arcsec':delta_rms,
                          'mean_paired_radial_error_difference_arcsec':delta_radial}
        cases.append({'case':case['id'],'target_flux_jy':case['target_flux_jy'],'background_truth':case['background'],
                      'planned_draws':study.RULES['controls']['draws_per_case'],'arms':arms,'paired':paired})
        public.extend(draws)
    return {'cases':cases,'p90_method':'numpy percentile, linear interpolation',
            'qualification':'16 paired noise draws per case on one opened geometry; Gaussian PSF and oracle noise, not independent sky validation'},public


def verify_lock(raw,expected_sha):
    if not isinstance(expected_sha,str) or len(expected_sha)!=64 or any(c not in '0123456789abcdef' for c in expected_sha):
        raise ValueError('explicit completed raw SHA-256 required')
    if legacy.lab.digest(RAW)!=expected_sha:raise ValueError('completed raw report SHA-256 mismatch')
    if legacy.lab.digest(DESIGN)!=DESIGN_SHA:raise ValueError('design SHA-256 mismatch')
    design=json.loads(DESIGN.read_text(encoding='utf-8'))
    if design['rules']!=legacy.jsonable(study.RULES) or any(design.get(k)!=v for k,v in study.inventory().items()):
        raise ValueError('design/source/raw input mismatch')
    if (raw['protocol_commit']!=COMMIT or raw['protocol_sha256']!=DESIGN_SHA
            or raw['rules']!=design['rules'] or raw['source_hashes']!=design['sources']
            or raw['input_hashes']!=design['raw'] or raw['opened_products']!=design['opened_products']):
        raise ValueError('raw provenance mismatch')
    study.verify_frozen_commit(COMMIT,design,DESIGN_SHA)
    runtime=raw['runtime'];current=legacy.execution_runtime()
    for key in ('python','platform','packages'):
        if runtime.get(key)!=current[key]:raise ValueError('recorded/current runtime mismatch: '+key)
    if runtime.get('thread_environment')!=study.RULES['thread_environment_request']:
        raise ValueError('recorded thread environment mismatch')
    if {key:os.environ.get(key) for key in study.THREAD_ENV}!=runtime['thread_environment']:
        raise ValueError('auditor thread environment differs; use the fresh CLI entry point')
    if runtime.get('thread_qualification')!='environment requests recorded before CLI imports; not independent verification of every backend thread':
        raise ValueError('recorded threading qualification mismatch')
    return design


class SavedRendererCache:
    """Load checked inputs once and render only requested saved positions."""
    def __init__(self):
        frames,_=inputs.read_verified_frames()
        self.prepared={};self.cache={};self.geometry={}
        for configuration in study.RULES['configurations']:
            try:
                groups,original,errors=study.prepare_configuration(frames,configuration)
                self.prepared[configuration]=(groups,original,errors)
            except Exception as exc:
                self.prepared[configuration]=(None,None,[type(exc).__name__+': '+str(exc)]*2)

    def get(self,configuration,epoch,variant):
        e=0 if epoch=='before' else 1
        spec=next(v for v in study.VARIANTS if v['id']==variant)
        key=(configuration,e,spec['background_order'],spec['epsf_kind'])
        if key not in self.cache:
            _,original,errors=self.prepared[configuration]
            if errors[e]:raise ValueError('cannot reconstruct saved semantic frame: '+errors[e])
            self.cache[key]=adapter.prepare_semantic(original[e],study.RULES['anchor'],
                background_order=spec['background_order'],epsf_kind=spec['epsf_kind'])
        return self.cache[key]

    def control_geometry(self,epoch):
        if epoch not in self.geometry:
            e=0 if epoch=='before' else 1
            _,original,errors=self.prepared['strict']
            if errors[e]:raise ValueError('cannot reconstruct control geometry: '+errors[e])
            items=self.get('strict',epoch,ARMS[0])
            if not hasattr(self,'gain'):self.gain=study.load_gain()
            self.geometry[epoch]=study.control_geometry(original[e],items,self.gain)
        return self.geometry[epoch]


def build(expected_sha):
    # Digest before parsing and again after all read-only work to detect changes.
    if legacy.lab.digest(RAW)!=expected_sha:raise ValueError('raw SHA-256 mismatch')
    raw=json.loads(RAW.read_text(encoding='utf-8'))
    verify_lock(raw,expected_sha)
    keyed=audit_keys(raw)
    contrast_checks=[]
    for config in study.RULES['configurations']:
        for order_name in ('plane','quadratic'):
            for kind in ('nearest','bilinear'):
                for e in ('before','after'):
                    available=check_contrast(keyed[('real',config,order_name+'_'+kind+'_free',e)],
                                             keyed[('real',config,order_name+'_'+kind+'_nonnegative',e)])
                    contrast_checks.append({'section':'real','configuration':config,'background':order_name,
                                            'spatial_epsf':kind,'epoch':e,'available':available})
    for case in study.CASES:
        for draw in range(study.RULES['controls']['draws_per_case']):
            for e in ('before','after'):
                available=check_contrast(keyed[('control',case['id'],str(draw),ARMS[0],e)],
                                         keyed[('control',case['id'],str(draw),ARMS[1],e)])
                contrast_checks.append({'section':'control','case':case['id'],'draw':draw,'epoch':e,'available':available})
    cache=SavedRendererCache();audits={};control_checks={}
    for key,row in keyed.items():
        if row['status']=='fit_completed':
            items=cache.get(row['configuration'],row['epoch'],row['variant'])
            audits[key]=audit_fit(row,items)
        if row['section']=='control':
            control_checks[key]=check_control(row,cache.control_geometry(row['epoch'])) if row.get('samples') else {'available':False,'reason':'no prepared control samples'}
    if legacy.lab.digest(RAW)!=expected_sha:raise ValueError('raw report changed during audit')
    configs=real_summary(keyed)
    summary,groups=control_summary(keyed,audits)
    real_records=[r for r in raw['records'] if r['section']=='real']
    provenance={'protocol_commit':COMMIT,'design_sha256':DESIGN_SHA,
                'raw_report_path':legacy.relative(RAW),'raw_report_sha256':expected_sha,'raw_report_bytes':RAW.stat().st_size,
                'source_hashes':raw['source_hashes'],'input_hashes':raw['input_hashes'],
                'opened_products':raw['opened_products'],'runtime':raw['runtime'],
                'publisher_source_sha256':legacy.lab.digest(Path(__file__))}
    counts={**raw['counts'],'real_attempts':32,'control_attempts':256}
    limitations=['Opened WISE geometry and development-only synthetic Gaussian truth; no independent sky validation or science promotion.',
                 'Control background uses empirical original VARIANCE, which may already contain original source shot noise; added synthetic Poisson does not establish a physical noise budget.',
                 'Control errors use oracle expected-source variance; no confidence interval, coverage or detection probability.',
                 'Renderer and linear KKT replayed at saved fit positions; successful final-start costs checked independently by linear BVLS, without positional optimization. Position Jacobian/rank is not independently recomputed.',
                 'No statistical model winner is selected; 16 draws per case share one opened geometry.']
    real={'schema':'neighbor-intervention-real-1','schema_version':1,'provenance':provenance,'rules':raw['rules'],
          'counts':counts,'configurations':configs,'records':real_records,
          'attempt_audits':[{'key':list(key),'audit':audits[key]} for key in audits if key[0]=='real'],
          'contrast_audits':[x for x in contrast_checks if x['section']=='real'],
          'limitations':limitations}
    controls={'schema':'neighbor-intervention-controls-1','schema_version':1,'provenance':provenance,'rules':raw['rules'],
              'counts':counts,'summary':summary,'paired_draws':groups,
              'control_replay_checks':[{'key':list(k),'audit':v} for k,v in control_checks.items()],
              'contrast_audits':[x for x in contrast_checks if x['section']=='control'],
              'limitations':limitations}
    return real,controls


def make_overview(real,controls,real_hash,real_bytes,controls_hash,controls_bytes):
    return {'schema':'neighbor-intervention-overview-1','schema_version':1,
            'provenance':{**real['provenance'],
                'real_report':{'path':legacy.relative(REAL_OUT),'sha256':real_hash,'bytes':real_bytes},
                'controls_report':{'path':legacy.relative(CONTROLS_OUT),'sha256':controls_hash,'bytes':controls_bytes}},
            'rules':real['rules'],'counts':real['counts'],'real':{'configurations':real['configurations']},
            'controls':controls['summary'],'limitations':real['limitations']}


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--raw-sha256',required=True,help='independently recorded SHA-256 of completed raw study')
    args=parser.parse_args()
    real,controls=build(args.raw_sha256)
    REAL_OUT.parent.mkdir(parents=True,exist_ok=True)
    atomic(REAL_OUT,real);atomic(CONTROLS_OUT,controls)
    overview=make_overview(real,controls,legacy.lab.digest(REAL_OUT),REAL_OUT.stat().st_size,
                           legacy.lab.digest(CONTROLS_OUT),CONTROLS_OUT.stat().st_size)
    atomic(OVERVIEW_OUT,overview)
    for path in (REAL_OUT,CONTROLS_OUT,OVERVIEW_OUT):print(legacy.relative(path),legacy.lab.digest(path),path.stat().st_size,flush=True)


if __name__=='__main__':main()
