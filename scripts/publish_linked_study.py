"""Audit the frozen WISE linked study and publish a full record and overview.

This performs no image fit, spectrum calculation, new simulation or network
access. Reported covariance is conditional, not calibrated science support.
"""
from hashlib import sha256
from pathlib import Path
import json
import subprocess

import numpy as np

from . import run_wise_linked_study as study
from .science_jobs import atomic


ROOT=study.ROOT
RAW=ROOT/'data/raw/benchmark/linked-wise-development.json'
FULL=ROOT/'web/data/linked-flux/development.json'
OVERVIEW=ROOT/'web/data/linked-flux/overview.json'
MODES=ROOT/'web/data/linked-flux/mode-diagnostics.json'
MODE_SOURCE=ROOT/'scripts/diagnose_linked_modes.py'
RAW_SHA='a5bffe162ae8ccd88a6fc5311d1e8ddc279c56092b072a782652da5a7f1cfd0a'
COMMIT='cfb9d6a17ee37ca2c5c061a2cd44209d1093f4b7'
DESIGN_SHA='c5914ab5b3ef1e8fb0b0a41c0d35d0bab741cc562ea820b632ca902e4944b072'
CONFIGS=('broad','strict')
VARIANTS=study.VARIANTS
T=np.array(study.inputs.gaia.TRANSFORM,float)


def close(a,b,label,rtol=1e-9,atol=1e-12):
    a=np.asarray(a,float);b=np.asarray(b,float)
    if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all() or not np.allclose(a,b,rtol=rtol,atol=atol):
        raise ValueError('audit mismatch: '+label)


def equal(a,b,label):
    if isinstance(a,dict) and isinstance(b,dict):
        if set(a)!=set(b):raise ValueError('audit keys mismatch: '+label)
        for k in a:equal(a[k],b[k],label+'.'+k)
    elif isinstance(a,(list,tuple)) and isinstance(b,(list,tuple)):
        if len(a)!=len(b):raise ValueError('audit length mismatch: '+label)
        for i,(x,y) in enumerate(zip(a,b)):equal(x,y,label+'['+str(i)+']')
    elif isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)) and not isinstance(b,bool):
        close(a,b,label)
    elif a!=b:raise ValueError('audit mismatch: '+label)


def spd(value,label):
    a=np.asarray(value,float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.isfinite(a).all():raise ValueError(label+' invalid matrix')
    scale=float(np.max(np.abs(a)))
    if scale<=0 or np.max(np.abs(a-a.T))>1e-10*scale or np.linalg.eigvalsh((a+a.T)/2).min()<=0:
        raise ValueError(label+' not symmetric positive definite')
    return a


def audit_mode(fit):
    audit=fit['final_mode_audit']
    if not audit['requested'] or len(audit['starts'])!=5:raise ValueError('missing final mode audit')
    point=np.asarray(fit['position'],float);cost=float(fit['chi2_weighted'])
    close(audit['point_chi2'],cost,'mode point cost')
    successful=[r for r in audit['starts'] if r['success']]
    if audit['all_starts_failed'] != (len(successful)==0):raise ValueError('mode failure flag mismatch')
    candidates=[{'position':point,'chi2':cost,'origin':'point'}]
    for r in successful:
        position=np.asarray(r['position'],float)
        if position.shape!=(2,) or not np.isfinite(position).all() or not np.isfinite(r['chi2']):raise ValueError('invalid mode result')
        candidates.append({'position':position,'chi2':float(r['chi2']),'origin':'start'})
    candidates.sort(key=lambda item:item['chi2'])
    modes=[]
    for candidate in candidates:
        found=next((m for m in modes if np.linalg.norm(candidate['position']-m['position'])<=.15),None)
        if found is None:modes.append({**candidate,'member_count':1})
        else:found['member_count']+=1
    for m in modes:
        m['delta_chi2']=m['chi2']-modes[0]['chi2'];m['position']=m['position'].tolist()
    near=[m for m in modes if m['delta_chi2']<=5.991]
    equal(modes,audit['modes'],'clustered modes')
    equal(near,audit['near_best_modes'],'near modes')
    if audit['near_best_count']!=len(near):raise ValueError('near-mode count mismatch')
    improvement=cost-min((float(r['chi2']) for r in successful),default=cost)
    close(improvement,audit['best_improvement_chi2'],'mode improvement')
    if audit['better_than_point'] != (improvement>1e-4):raise ValueError('better-mode flag mismatch')
    return {'near_best_count':len(near),'better_than_point':improvement>1e-4,
            'all_starts_failed':not successful,'failed_final_starts':sum(not r['success'] for r in audit['starts'])}


def audit_attempt(row,variant):
    if row.get('record_sha256')!=sha256(study.encoded({k:v for k,v in row.items() if k!='record_sha256'})).hexdigest():
        raise ValueError('attempt checksum mismatch')
    if row['status']!='fit_completed':
        if row['status'] not in ('preparation_failed','fit_failed') or not row.get('error'):
            raise ValueError('failure missing status or reason')
        return {'status':row['status'],'error':row['error']}
    fit=row['fit'];samples=row['samples'];obs=row['obs_ids'];n=len(obs)
    if not n or len(set(obs))!=n or [s['obs_id'] for s in samples]!=obs:
        raise ValueError('sample observation identity mismatch')
    if fit['mode']!=variant['mode'] or fit['data_unit']!='MJy / sr':raise ValueError('mode/unit mismatch')
    if len(fit['residuals'])!=n or len(fit['weights'])!=n or len(fit['nuisance_ranks'])!=n:
        raise ValueError('frame count mismatch')
    raw_chi=0.;weighted_chi=0.;recreated=[];next_diff=0.;frame_audit=[]
    for sample,residual,weight,rank in zip(samples,fit['residuals'],fit['weights'],fit['nuisance_ranks']):
        r=np.asarray(residual,float);w=np.asarray(weight,float);e=np.asarray(sample['error_mjysr'],float)
        if r.ndim!=1 or not len(r) or r.shape!=w.shape or r.shape!=e.shape or len(sample['x'])!=len(r) or len(sample['y'])!=len(r) or sample['selected_pixels']!=len(r):
            raise ValueError('invalid pixel vector shape')
        x=np.asarray(sample['x'],float);y=np.asarray(sample['y'],float)
        if (not np.isfinite(x).all() or not np.isfinite(y).all() or np.any(x<0) or np.any(y<0)
                or np.any(x!=np.rint(x)) or np.any(y!=np.rint(y))
                or any((y[i],x[i]) >= (y[i+1],x[i+1]) for i in range(len(x)-1))):
            raise ValueError('pixel coordinates not unique row-major integers')
        if (not np.isfinite(r).all() or not np.isfinite(e).all() or not np.isfinite(w).all()
                or np.any(e<=0) or np.any(w<=0) or np.any(w>1) or rank!=sample['nuisance_rank']):
            raise ValueError('invalid residual, error, weight or rank')
        standardized=r/e;wr=standardized*np.sqrt(w)
        raw_chi+=float(standardized@standardized);weighted_chi+=float(wr@wr);recreated.extend(wr)
        frame_audit.append({'obs_id':sample['obs_id'],'raw_chi2':float(standardized@standardized),
                            'weighted_chi2':float(wr@wr),'pixels':len(r)})
        next_w=np.minimum(1.,2.5/np.maximum(np.abs(standardized),1e-300))
        next_diff=max(next_diff,float(np.max(np.abs(next_w-w))))
    close(raw_chi,fit['chi2_raw'],'raw chi2');close(weighted_chi,fit['chi2_weighted'],'weighted chi2')
    close(recreated,fit['weighted_residual'],'weighted residual')
    close(next_diff,fit['irls']['next_weight_max_difference'],'next IRLS weight difference')
    k=n if variant['mode']=='independent' else 2 if variant['mode']=='shared_tilt' else 1
    dof=sum(s['selected_pixels'] for s in samples)-sum(fit['nuisance_ranks'])-k-2
    if dof<=0 or fit['dof']!=dof or fit['source_rank']!=k:raise ValueError('invalid rank or degrees of freedom')
    basis=np.asarray(fit['flux_basis'],float)
    if variant['mode']=='independent':expected=np.eye(n)
    else:
        predictions={p['obs_id']:p for p in row['predictions']}
        if len(predictions)!=n or set(predictions)!=set(obs):raise ValueError('prediction observation mismatch')
        coefficients=np.array([predictions[o]['relative_coefficient'] for o in obs])
        if variant['mode']=='shared':expected=coefficients[:,None]
        else:
            wavelength=np.array([predictions[o]['chosen_center_um'] for o in obs])
            expected=np.column_stack([coefficients,coefficients*(wavelength-fit['tilt_center_um'])/fit['tilt_scale_um']])
    close(basis,expected,'flux basis')
    parameters=np.asarray(fit['flux_parameters_jy'],float);C=spd(fit['flux_covariance_jy2'],'flux covariance')
    if parameters.shape!=(k,) or C.shape!=(k,k):raise ValueError('flux parameter shape mismatch')
    frame_flux=basis@parameters;frame_cov=basis@C@basis.T;err=np.sqrt(np.diag(frame_cov))
    close(frame_flux,fit['per_frame_flux_jy'],'frame flux',atol=1e-15)
    close(frame_cov,fit['per_frame_flux_covariance_jy2'],'frame covariance',atol=1e-20)
    close(err,fit['per_frame_error_jy'],'frame flux error',atol=1e-15)
    if np.any(err<=0):raise ValueError('nonpositive conditional flux error')
    close(frame_flux/err,fit['conditional_frame_snr'],'conditional frame snr')
    if list(frame_flux<0)!=fit['negative_frame_flux']:raise ValueError('negative flux flag mismatch')
    irls=fit['irls']
    converged=irls['next_weight_max_difference']<=irls['weight_tolerance'] and irls['position_max_change']<=irls['position_tolerance_px']
    if irls['converged']!=converged or not 1<=irls['iterations']<=irls['max_iterations']:
        raise ValueError('IRLS convergence mismatch')
    audit=audit_mode(fit)
    expected_boundary=bool(np.any(np.abs(np.asarray(fit['position'])-np.asarray(study.RULES['anchor_sky_grid_px']))>=.95*2.5))
    if fit['at_boundary']!=expected_boundary or fit['position_rank'] not in (0,1,2):raise ValueError('position boundary/rank mismatch')
    reasons=[]
    if fit['at_boundary']:reasons.append('boundary')
    if fit['position_rank']<2 or fit['position_covariance_px2'] is None:reasons.append('position_rank_or_covariance')
    if not converged:reasons.append('irls_not_converged')
    if audit['all_starts_failed']:reasons.append('final_mode_audit_failed')
    if audit['better_than_point']:reasons.append('better_final_weight_mode')
    if audit['near_best_count']>1:reasons.append('multiple_near_best_modes')
    metadata_failed=bool(row.get('renderer_metadata_failed'))
    if reasons!=fit['inference_reasons'] or fit['inference_supported']!= (not reasons and not metadata_failed):raise ValueError('solver screening mismatch')
    if metadata_failed:reasons.append('renderer_metadata_failed')
    if fit['position_covariance_px2'] is not None:spd(fit['position_covariance_px2'],'position covariance')
    profile=fit['profile_hessian']
    if profile['supported']:
        h=np.asarray(profile['hessians'],float)
        if h.shape!=(2,2,2):raise ValueError('invalid profile Hessians')
        difference=float(np.linalg.norm(h[0]-h[1])/max(np.linalg.norm(h[1]),np.finfo(float).tiny))
        close(difference,profile['relative_step_change'],'Hessian step agreement')
        if difference>.05:raise ValueError('unstable supported Hessian')
        info=spd(h[0],'profile Hessian')
        eigenvalues=np.linalg.eigvalsh(info)
        if eigenvalues[0]<=1e-10*eigenvalues[-1]:raise ValueError('poorly conditioned supported Hessian')
        close(np.linalg.inv(info),profile['covariance_px2'],'profile covariance')
    return {'status':row['status'],'raw_chi2':raw_chi,'weighted_chi2':weighted_chi,
            'next_weight_max_difference':next_diff,'dof':dof,'frames':frame_audit,'mode_audit':audit,
            'solver_screening_passed':fit['inference_supported'],'solver_screening_reasons':reasons,
            'at_boundary':fit['at_boundary'],'position_rank':fit['position_rank'],
            'irls_converged':converged,'negative_frame_flux_count':int(np.sum(frame_flux<0)),
            'profile_hessian_supported':profile['supported'],'profile_hessian_reason':profile.get('reason')}


def audit_records(records):
    expected={(c,v['id'],e) for c in CONFIGS for v in VARIANTS for e in ('before','after')}
    bykey={(r['configuration'],r['variant'],r['epoch']):r for r in records}
    if len(records)!=len(expected) or len(bykey)!=len(records) or set(bykey)!=expected:
        raise ValueError('all 28 distinct attempts required')
    audits=[]
    for key in sorted(bykey):
        row=bykey[key];variant=next(v for v in VARIANTS if v['id']==key[1])
        audits.append({'configuration':key[0],'variant':key[1],'epoch':key[2],**audit_attempt(row,variant)})
    pair_rows=[];configs=[]
    for config in CONFIGS:
        available=[]
        for variant in VARIANTS:
            rows=[bykey[(config,variant['id'],e)] for e in ('before','after')]
            good=[r for r in rows if r['status']=='fit_completed']
            pair={'configuration':config,'variant':variant['id'],'epoch_attempts':2,'successful_epoch_fits':len(good),
                  'solver_screening_both':False,'east_north_arcsec':None,
                  'covariance_assumption':study.RULES['covariance_cross_epoch']}
            if len(good)==2:
                b,a=[r['fit'] for r in rows];vector=T@(np.asarray(a['position'])-np.asarray(b['position']))
                pair['east_north_arcsec']=vector.tolist();pair['solver_screening_both']=bool(b['inference_supported'] and a['inference_supported'])
                for name in ('gn','profile'):
                    matrices=[f['position_covariance_px2'] if name=='gn' else f['profile_hessian'].get('covariance_px2') if f['profile_hessian'].get('supported') else None for f in (b,a)]
                    if all(x is not None for x in matrices):pair[name+'_conditional_centroid_covariance_arcsec2']=(T@(np.asarray(matrices[0])+np.asarray(matrices[1]))@T.T).tolist()
                available.append(pair)
            pair_rows.append(pair)
        baseline=next((p for p in available if p['variant']=='independent'),None)
        if baseline:
            for p in available:p['change_from_independent_arcsec']=float(np.linalg.norm(np.asarray(p['east_north_arcsec'])-baseline['east_north_arcsec']))
        distances=[(float(np.linalg.norm(np.asarray(a['east_north_arcsec'])-b['east_north_arcsec'])),a['variant'],b['variant']) for i,a in enumerate(available) for b in available[i+1:]]
        farthest=max(distances,key=lambda item:item[0]) if distances else None
        frame_counts={}
        for epoch in ('before','after'):
            ids=[tuple(bykey[(config,v['id'],epoch)]['obs_ids']) for v in VARIANTS if bykey[(config,v['id'],epoch)]['obs_ids']]
            if ids and any(x!=ids[0] for x in ids):raise ValueError('different exposure order across variants')
            matched=[bykey[(config,v['id'],epoch)]['samples'] for v in VARIANTS if bykey[(config,v['id'],epoch)]['status']=='fit_completed']
            keys=('obs_id','x','y','error_mjysr','epsf_zone','nuisance_rank','nuisance_provenance','renderer_provenance','cutout_url','raw_sha256')
            if matched:
                reference=[{k:s[k] for k in keys} for s in matched[0]]
                for samples in matched[1:]:
                    if [{k:s[k] for k in keys} for s in samples]!=reference:raise ValueError('different fixed pixels or nuisance provenance across variants')
            frame_counts[epoch]=len(ids[0]) if ids else None
        configs.append({'configuration':config,'frames_per_epoch':frame_counts,'available_pairs':len(available),
                        'max_pairwise_spread_arcsec':farthest[0] if farthest else None,
                        'max_pairwise_variants':list(farthest[1:]) if farthest else None,
                        'spread_basis':'all completed pair vectors regardless of solver screening; exploratory model sensitivity',
                        'maximum_change_from_independent_arcsec':max((p['change_from_independent_arcsec'] for p in available if 'change_from_independent_arcsec' in p),default=None)})
    counts={'planned_epoch_attempts':len(expected),'recorded_epoch_attempts':len(records),
            'fit_completed':sum(r['status']=='fit_completed' for r in records),
            'failures':sum(r['status']!='fit_completed' for r in records),
            'renderer_metadata_failures':sum(bool(r.get('renderer_metadata_failed')) for r in records)}
    return {'counts':counts,'attempt_audits':audits,'pairs':pair_rows,'configurations':configs}


def mode_reference(records):
    data=json.loads(MODES.read_text(encoding='utf-8'))
    if (data['raw_study_sha256']!=RAW_SHA or data['protocol_sha256']!=DESIGN_SHA
            or data['protocol_commit']!=COMMIT or data['diagnostic_source_sha256']!=study.lab.digest(MODE_SOURCE)):
        raise ValueError('post-hoc mode diagnostic provenance mismatch')
    output=[]
    for row in data['variants']:
        source=[r for r in records if r['configuration']=='strict' and r['epoch']=='after' and r['variant']==row['variant']]
        if len(source)!=1 or source[0]['record_sha256']!=row['record_sha256'] or len(row['modes'])!=2:
            raise ValueError('mode diagnostic attempt mismatch')
        saved=source[0]['fit']['final_mode_audit']['near_best_modes']
        fit=source[0]['fit']
        limits={'point_weighted_chi2_abs_diff':abs(fit['chi2_weighted']),
                'flux_parameters_jy_max_abs_diff':max(map(abs,fit['flux_parameters_jy'])),
                'frame_flux_jy_max_abs_diff':max(map(abs,fit['per_frame_flux_jy'])),
                'frame_error_jy_max_abs_diff':max(map(abs,fit['per_frame_error_jy'])),
                'weighted_residual_max_abs_diff':max(map(abs,fit['weighted_residual'])),
                'mode_0_weighted_chi2_abs_diff':abs(saved[0]['chi2']),
                'mode_1_weighted_chi2_abs_diff':abs(saved[1]['chi2'])}
        if set(row['position_replay'])!=set(limits):raise ValueError('post-hoc replay fields mismatch')
        for key,delta in row['position_replay'].items():
            if not np.isfinite(delta) or delta<0 or delta>1e-8+1e-7*limits[key]:raise ValueError('post-hoc replay check failed')
        for actual,expected in zip(row['modes'],saved):
            close(actual['position_sky_px'],expected['position'],'mode diagnostic position')
            close(actual['replayed_weighted_chi2'],expected['chi2'],'mode diagnostic chi2')
            if len(actual['frames'])!=len(source[0]['samples']):raise ValueError('mode diagnostic frame count mismatch')
            for index,frame in enumerate(actual['frames']):
                p=frame['selected_pixels'];w=np.asarray(p['final_irls_weight'],float);r=np.asarray(p['raw_standardized_residual'],float)
                if w.shape!=r.shape or len(w)!=frame['selected_pixel_count'] or len(p['x'])!=len(w) or len(p['y'])!=len(w):raise ValueError('mode diagnostic pixels mismatch')
                original=source[0]['samples'][index]
                if frame['obs_id']!=original['obs_id'] or frame['raw_sha256']!=original['raw_sha256'] or frame['cutout_url']!=original['cutout_url']:
                    raise ValueError('mode diagnostic exposure provenance mismatch')
                for key in ('x','y','error_mjysr'):
                    close(p[key],original[key],'mode diagnostic '+key)
                close(w,source[0]['fit']['weights'][index],'mode diagnostic fixed weights')
                close(float(np.sum(w*r*r)),frame['weighted_chi2'],'mode diagnostic frame chi2')
                pos=np.asarray(frame['native_position_xy']);x=np.asarray(p['x']);y=np.asarray(p['y'])
                core=(x-pos[0])**2+(y-pos[1])**2<=frame['core']['radius_native_px']**2
                if int(core.sum())!=frame['core']['selected_count']:raise ValueError('mode diagnostic core count mismatch')
                if core.any():close(np.sqrt(np.mean(r[core]**2)),frame['core']['raw_standardized_residual_rms'],'mode diagnostic core rms')
            close(sum(f['weighted_chi2'] for f in actual['frames']),actual['replayed_weighted_chi2'],'mode diagnostic sum')
        for i,delta in enumerate(row['frame_deltas']):
            a=row['modes'][0]['frames'][i];b=row['modes'][1]['frames'][i]
            if a['obs_id']!=b['obs_id'] or delta['obs_id']!=a['obs_id']:raise ValueError('mode diagnostic exposure mismatch')
            close(b['weighted_chi2']-a['weighted_chi2'],delta['weighted_chi2_mode1_minus_mode0'],'mode diagnostic delta')
        output.append({'variant':row['variant'],'record_sha256':row['record_sha256'],
                       'modes':[{'position_sky_px':x['position_sky_px'],'weighted_chi2':x['replayed_weighted_chi2']} for x in row['modes']],
                       'frame_deltas':row['frame_deltas'],'replay_max_abs_diff':max(row['position_replay'].values())})
    if {x['variant'] for x in output}!={'independent','shared_r7_68_a0'}:raise ValueError('mode diagnostic variants mismatch')
    return {'path':'web/data/linked-flux/mode-diagnostics.json','sha256':study.lab.digest(MODES),
            'bytes':MODES.stat().st_size,'stage':data['stage'],
            'qualification':'post hoc fixed-weight replay, not source classification or validation', 'variants':output}


def verify_lock(raw):
    if study.lab.digest(RAW)!=RAW_SHA:raise ValueError('raw report hash mismatch')
    design=study.verify_design()
    if study.lab.digest(study.DESIGN)!=DESIGN_SHA or raw['protocol_sha256']!=DESIGN_SHA or raw['protocol_commit']!=COMMIT:
        raise ValueError('design or commit mismatch')
    if raw['source_hashes']!=design['sources'] or raw['input_hashes']!=design['raw'] or raw['opened_products']!=design['opened_products'] or raw['rules']!=design['rules']:
        raise ValueError('raw provenance or protocol mismatch')
    manifest=json.loads(study.inputs.gaia.INPUT.read_text(encoding='utf-8'))
    entries={r['obs_id']:r for r in manifest['records']}
    if len(entries)!=len(manifest['records']):raise ValueError('duplicate manifest exposure')
    variants={v['id']:v for v in VARIANTS}
    for row in raw['records']:
        for sample in row.get('samples',[]):
            source=entries.get(sample['obs_id'])
            if source is None or sample['raw_sha256']!=source['sha256'] or sample['cutout_url']!=source['cutout_url']:
                raise ValueError('exposure provenance mismatch')
        for prediction in row.get('predictions',[]):
            spec=variants[row['variant']]
            if (prediction['obs_id'] not in row['obs_ids'] or prediction['center_model']!=spec['center_model']
                    or prediction['reference_alpha']!=spec['reference_alpha'] or prediction['r7_binding']['channels']!=spec['channels']):
                raise ValueError('spectral metadata mismatch')
            close(prediction['common_normalization_jy'],raw['rules']['spectral_normalization_jy'],'spectral normalization')
            close(prediction['relative_coefficient'],prediction['sed_coefficient_jy']/prediction['common_normalization_jy'],'spectral coefficient')
            member=row['calibration_members'].get(prediction['curve_member'])
            if member is None or member.get('sha256')!=prediction['curve_sha256']:raise ValueError('spectral curve provenance mismatch')
    # HEAD verification alone is not proof that the reported frozen commit had
    # these bytes; verify the actual design and every source/product at COMMIT.
    committed={**design['sources'],**design['opened_products'],'web/data/linked-flux/design.json':DESIGN_SHA}
    for path,digest in committed.items():
        blob=subprocess.check_output(['git','show',COMMIT+':'+path],cwd=ROOT,stderr=subprocess.DEVNULL)
        if sha256(blob).hexdigest()!=digest:raise ValueError('frozen commit mismatch: '+path)
    return design


def build():
    raw=json.loads(RAW.read_text(encoding='utf-8'))
    verify_lock(raw)
    if not raw['completed']:raise ValueError('study incomplete')
    audit=audit_records(raw['records'])
    equal(audit['counts'],raw['counts'],'counts')
    equal(audit['pairs'],raw['pairs'],'pair summaries')
    posthoc=mode_reference(raw['records'])
    source=Path(__file__)
    provenance={'raw_report_path':'data/raw/benchmark/linked-wise-development.json','raw_report_sha256':RAW_SHA,
                'raw_report_bytes':RAW.stat().st_size,'design_path':'web/data/linked-flux/design.json',
                'design_sha256':DESIGN_SHA,'protocol_commit':COMMIT,
                'source_hashes':raw['source_hashes'],'input_hashes':raw['input_hashes'],
                'opened_product_hashes':raw['opened_products'],'runtime':raw['runtime'],
                'publisher_source_sha256':study.lab.digest(source)}
    return {'schema':'wise-linked-development-1','schema_version':1,'role':'opened-data conditional model comparison, not validation',
            'provenance':provenance,'rules':raw['rules'],'counts':audit['counts'],
            'attempt_audits':audit['attempt_audits'],'records':raw['records'],
            'pairs':audit['pairs'],'configurations':audit['configurations'],
            'posthoc_mode_diagnostic':posthoc,
            'audit_limitations':['GN position covariance cannot be recomputed from this report alone because its position Jacobian was not saved.',
                'Per-frame chi-square, conditional flux covariance and H covariance are algebraically audited; PSF and sky truth are not.',
                'Solver screening is an algorithmic flag, never scientific validation or a detection probability.']}


def make_overview(full,full_sha,full_bytes):
    attempts={(r['configuration'],r['variant'],r['epoch']):r for r in full['attempt_audits']}
    pairs=[]
    for p in full['pairs']:
        row=dict(p)
        row['epoch_status_and_screening']={e:{'status':attempts[(p['configuration'],p['variant'],e)]['status'],
             'solver_screening_passed':attempts[(p['configuration'],p['variant'],e)].get('solver_screening_passed',False),
             'reasons':attempts[(p['configuration'],p['variant'],e)].get('solver_screening_reasons',[]),
             'failure':attempts[(p['configuration'],p['variant'],e)].get('error'),
             'at_boundary':attempts[(p['configuration'],p['variant'],e)].get('at_boundary'),
             'irls_converged':attempts[(p['configuration'],p['variant'],e)].get('irls_converged'),
             'negative_frame_flux_count':attempts[(p['configuration'],p['variant'],e)].get('negative_frame_flux_count'),
             'near_best_mode_count':attempts[(p['configuration'],p['variant'],e)].get('mode_audit',{}).get('near_best_count'),
             'profile_hessian_supported':attempts[(p['configuration'],p['variant'],e)].get('profile_hessian_supported'),
             'profile_hessian_reason':attempts[(p['configuration'],p['variant'],e)].get('profile_hessian_reason')}
             for e in ('before','after')}
        pairs.append(row)
    sources={}
    for record in full['records']:
        for item in record.get('samples',[]):
            value={'obs_id':item['obs_id'],'cutout_url':item['cutout_url'],'raw_sha256':item['raw_sha256']}
            if item['obs_id'] in sources and sources[item['obs_id']]!=value:raise ValueError('inconsistent exposure provenance')
            sources[item['obs_id']]=value
    return {'schema':'wise-linked-overview-1','schema_version':1,'role':full['role'],
            'provenance':{**full['provenance'],'public_report_path':'web/data/linked-flux/development.json',
                          'public_report_sha256':full_sha,'public_report_bytes':full_bytes},
            'rules':full['rules'],'counts':full['counts'],'configurations':full['configurations'],
            'pairs':pairs,'exposure_sources':[sources[k] for k in sorted(sources)],
            'posthoc_mode_diagnostic':full['posthoc_mode_diagnostic'],
            'audit_limitations':full['audit_limitations']}


def main():
    full=build()
    FULL.parent.mkdir(parents=True,exist_ok=True)
    atomic(FULL,full)
    overview=make_overview(full,study.lab.digest(FULL),FULL.stat().st_size)
    atomic(OVERVIEW,overview)
    print('FULL',FULL.relative_to(ROOT),study.lab.digest(FULL),FULL.stat().st_size)
    print('OVERVIEW',OVERVIEW.relative_to(ROOT),study.lab.digest(OVERVIEW),OVERVIEW.stat().st_size)
    print('COUNTS',full['counts'],'CONFIGURATIONS',full['configurations'])


if __name__=='__main__':main()
