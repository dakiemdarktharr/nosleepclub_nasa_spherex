"""Audit the locked sandwich study and publish recomputable paired results."""
import json
from hashlib import sha256
from pathlib import Path
import subprocess
import numpy as np
from . import diagnose_bias as d

ROOT=d.ROOT
RAW=ROOT/'data/raw/benchmark/sandwich-development.json'
DESIGN=ROOT/'web/data/sandwich/design.json'
BASE=ROOT/'data/raw/benchmark/bias-gaussian64-development.json'
CONTINUOUS=ROOT/'data/raw/benchmark/continuous-epsf-development.json'
OUT=ROOT/'web/data/sandwich/development-summary.json'
OVERVIEW=ROOT/'web/data/sandwich/overview.json'
COMMIT='3995f2e6d0279fda8bedff2b47af1d53129dcfef'
METHODS=['gauss_newton','profile_hessian','exposure_sandwich']
THRESHOLDS={'50':1.3862943611198906,'68':2.27886856637673,'95':5.99146454710798}


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def close(a,b,label,atol=1e-8):
    if not np.allclose(a,b,atol=atol,rtol=1e-8):raise ValueError('Audit mismatch: '+label)


def same(expected,actual,label):
    if isinstance(expected,dict) and isinstance(actual,dict):
        if set(expected)!=set(actual):raise ValueError('Summary keys mismatch '+label)
        for k in expected:same(expected[k],actual[k],label+'.'+k)
    elif isinstance(expected,(list,tuple)) and isinstance(actual,(list,tuple,np.ndarray)):
        if len(expected)!=len(actual):raise ValueError('Summary length mismatch '+label)
        for a,b in zip(expected,actual):same(a,b,label)
    elif isinstance(expected,(float,int)) and not isinstance(expected,bool):close(expected,actual,label)
    elif expected!=actual:raise ValueError('Summary value mismatch '+label)


def committed(path,expected):
    blob=subprocess.check_output(['git','show',COMMIT+':'+path],cwd=ROOT)
    if sha256(blob).hexdigest()!=expected:raise ValueError('Committed hash mismatch: '+path)


def wilson(k,n):
    if not n:return None
    z=1.959963984540054;p=k/n;den=1+z*z/n;c=(p+z*z/(2*n))/den;h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [float(max(0,c-h)),float(min(1,c+h))]


def summarize(rows):
    result={'attempts':len(rows),'numeric':sum(bool(r.get('numeric_valid')) for r in rows),'accepted':sum(bool(r.get('accepted')) for r in rows),
        'fit_failures':sum('failure' in r for r in rows),
        'boundary_epochs':sum(bool(e.get('at_boundary')) for r in rows for e in r.get('epochs',[])),
        'multimode_epochs':sum(e['mode_diagnostic']['distinct_modes_015px']>1 for r in rows for e in r.get('epochs',[])),
        'mode_start_failures':sum(not t['success'] for r in rows for e in r.get('epochs',[]) for t in e['mode_diagnostic']['trials']),
        'lower_fixed_objective_epochs':sum(any(t.get('delta_chi2_vs_fit',0.) < -1e-4 for t in e['mode_diagnostic']['trials']) for r in rows for e in r.get('epochs',[]))}
    predicates={'all_attempts':lambda r:True,'numeric':lambda r:r.get('numeric_valid',False),
       'accepted':lambda r:r.get('accepted',False),
       'common_supported':lambda r:r.get('numeric_valid',False) and all(r['methods'][k]['supported'] for k in METHODS),
       'common_accepted':lambda r:r.get('accepted',False) and all(r['methods'][k]['supported'] for k in METHODS)}
    result['selections']={}
    for name,predicate in predicates.items():
        chosen=[r for r in rows if predicate(r)];valid=[r for r in chosen if r.get('numeric_valid')]
        vectors=np.array([r['error_east_north_arcsec'] for r in valid],float).reshape(-1,2);error=np.linalg.norm(vectors,axis=1)
        group={'attempts':len(chosen),'numeric':len(valid),'bias_east_north_arcsec':vectors.mean(axis=0).tolist() if len(valid) else None,
               'rms_arcsec':float(np.sqrt(np.mean(error**2))) if len(valid) else None,'p90_arcsec':float(np.percentile(error,90)) if len(valid) else None,'methods':{}}
        for method in METHODS:
            supported=[r['methods'][method] for r in valid if r['methods'][method]['supported']]
            reasons=[k for r in valid if not r['methods'][method]['supported'] for k in r['methods'][method].get('reasons',[])]
            output={'supported':len(supported),'unsupported':len(valid)-len(supported),
                    'unsupported_reasons':{k:reasons.count(k) for k in sorted(set(reasons))}}
            for kind in ['centroid_only','plus_registration']:
                q=[m[kind]['q'] for m in supported];cov=[np.asarray(m[kind]['covariance_arcsec2']) for m in supported]
                coverage={}
                for level,cut in THRESHOLDS.items():
                    k=sum(v<=cut for v in q);coverage[level]={'inside':k,'denominator':len(q),'fraction':k/len(q) if q else None,'wilson_95':wilson(k,len(q))}
                areas=[float(np.pi*THRESHOLDS['68']*np.sqrt(np.linalg.det(c))) for c in cov]
                axes=[float(np.sqrt(THRESHOLDS['68']*np.linalg.eigvalsh(c).max())) for c in cov]
                output[kind]={'coverage':coverage,'median_ellipse68_area_arcsec2':float(np.median(areas)) if areas else None,
                              'median_ellipse68_semimajor_arcsec':float(np.median(axes)) if axes else None,
                              'p90_ellipse68_semimajor_arcsec':float(np.percentile(axes,90)) if axes else None}
            group['methods'][method]=output
        result['selections'][name]=group
    return result


def validate_epoch(epoch):
    score=epoch['sandwich'];n=score['n_exposures']
    if 'hessians' in score:
        h=np.array(score['hessians']);u=np.array([v['score'] for v in score['exposures']]);j=np.array([v['residual_jacobian_score'] for v in score['exposures']])
        if len(u)!=n or len({v['obs_id'] for v in score['exposures']})!=n:raise ValueError('Exposure count/order invalid')
        close(u.T@u,score['meat'],'meat');close(u.sum(axis=0),score['score_sum'],'score sum')
        close(np.linalg.norm(u,axis=1).sum(),score['score_norm_sum'],'score norm sum')
        difference=np.linalg.norm(u-j);close(difference,score['scalar_vs_residual_jacobian_difference'],'scalar/J difference')
        close(difference/max(1.,np.linalg.norm(u)),score['scalar_vs_residual_jacobian_relative'],'relative scalar/J difference')
        change=np.linalg.norm(h[0]-h[1])/max(np.linalg.norm(h[1]),1e-15)
        close(change,score['hessian_relative_step_change'],'H step change')
        close(n/(n-2),score['correction_factor'],'CR1p')
        if score['supported']:
            inv=np.linalg.inv(h[0]);cov=n/(n-2)*inv@(u.T@u)@inv.T
            close(cov,score['covariance_px2'],'sandwich covariance')
            if epoch['profile']['supported']:
                p=np.linalg.inv(h[0])*max(1.,epoch['reduced_chi2'])
                close(p,epoch['profile']['covariance_px2'],'profile vs sum of exposure Hessians',atol=1e-7)
    mode=epoch['mode_diagnostic'];distinct=[]
    for t in mode['trials']:
        if t['success'] and all(np.linalg.norm(np.asarray(t['position_sky_px'])-np.asarray(v))>.15 for v in distinct):distinct.append(t['position_sky_px'])
    if len(distinct)!=mode['distinct_modes_015px']:raise ValueError('Mode count mismatch')


def validate_row(row,truth):
    if 'failure' in row:return
    epochs=row['epochs'];transform=d.study.gaia.TRANSFORM
    if len(epochs)!=2:raise ValueError('Expected two epoch fits')
    for e in epochs:validate_epoch(e)
    error=transform@(np.asarray(epochs[1]['position_px'])-np.asarray(epochs[0]['position_px'])-np.asarray(truth))
    close(error,row['error_east_north_arcsec'],'error vector');close(np.linalg.norm(error),row['error_arcsec'],'error norm')
    if row['accepted']!=bool(row['numeric_valid'] and all(e['quality']['accepted'] for e in epochs)):raise ValueError('Accepted flag mismatch')
    registration=np.asarray(row['registration_covariance_sky_px2'])
    for name,m in row['methods'].items():
        if not m['supported']:continue
        if name=='gauss_newton':parts=[e['covariance_px2'] for e in epochs]
        elif name=='profile_hessian':parts=[e['profile']['covariance_px2'] for e in epochs]
        else:parts=[e['sandwich']['covariance_px2'] for e in epochs]
        for key,reg in [('centroid_only',np.zeros((2,2))),('plus_registration',registration)]:
            cov=transform@(sum(np.asarray(v) for v in parts)+reg)@transform.T
            close(cov,m[key]['covariance_arcsec2'],name+' '+key+' covariance')
            close(m[key]['q'],error@np.linalg.solve(cov,error),name+' '+key+' q')


def compact_epoch(e):
    # Per-frame arrays and score arrays preserve every value with shorter keys.
    out={k:v for k,v in e.items() if k not in ['per_frame','sandwich']}
    keys=['obs_id','snr','core_rms','core_coverage','core_outlier_fraction','information_fraction','downweighted_pixels']
    out['per_frame']=[[v[k] for k in keys] for v in e['per_frame']]
    s=e['sandwich'];out['sandwich']={k:v for k,v in s.items() if k!='exposures'}
    if 'exposures' in s:out['sandwich']['exposures']=[[v['obs_id'],v['score'],v['residual_jacobian_score']] for v in s['exposures']]
    return out


def compact_row(row):
    return {**{k:v for k,v in row.items() if k!='epochs'},**({'epochs':[compact_epoch(e) for e in row['epochs']]} if 'epochs' in row else {})}


def build_overview(report,report_sha,report_bytes):
    """Keep summary/source provenance, not the 768 individual draw records."""
    overview={'version':'0.10.0-sandwich-overview.1','role':report['role'],
        'provenance':{**report['provenance'],'public_report_path':OUT.relative_to(ROOT).as_posix(),
                      'public_report_sha256':report_sha,'public_report_bytes':report_bytes},
        'rules':report['rules'],'limitations':report['limitations'],
        'field_provenance':report['field_provenance'],'cases':[],
        'aggregate_note':'Counts sum paired noise draws across six opened-field cases, not independent sky fields.'}
    count_keys=['attempts','numeric','accepted','fit_failures','boundary_epochs','multimode_epochs',
                'mode_start_failures','lower_fixed_objective_epochs']
    overview['aggregate_counts']={k:sum(c['summary'][k] for c in report['cases']) for k in count_keys}
    for case in report['cases']:
        source=case['original_background'];candidate=source['candidate'];baseline=source['frozen_baseline']
        original={'frozen_baseline':{k:baseline.get(k) for k in ['numeric_valid','accepted','quality_reasons','error_east_north_arcsec','error_arcsec']},
                  'candidate':{k:candidate.get(k) for k in ['numeric_valid','accepted','quality_reasons','error_east_north_arcsec','error_arcsec','methods']},
                  'candidate_epoch_positions_px':[e['position_px'] for e in candidate.get('epochs',[])],
                  'point_replay':case['original_point_replay']}
        anomalies=[]
        for row in case['records']:
            for i,epoch in enumerate(row.get('epochs',[])):
                better=[t for t in epoch['mode_diagnostic']['trials'] if t.get('delta_chi2_vs_fit',0.) < -1e-4]
                if better:
                    best=min(better,key=lambda t:t['delta_chi2_vs_fit'])
                    anomalies.append({'draw':row['draw'],'epoch':['before','after'][i],'accepted':row['accepted'],
                        'fitted_position_px':epoch['position_px'],'alternative_position_px':best['position_sky_px'],
                        'delta_chi2_fixed_final_weights':best['delta_chi2_vs_fit']})
        overview['cases'].append({k:case[k] for k in ['field','source','snr_per_frame','anchor_sky_px','truth_delta_sky_px','noise_seed','summary']}
                                 | {'original_background':original,'lower_objective_mode_anomalies':anomalies})
    return overview


def build():
    design=read(DESIGN);raw=read(RAW);baseline=read(BASE);continuous=read(CONTINUOUS);design_sha=d.digest(DESIGN)
    if not raw['completed'] or raw['design_sha256']!=design_sha or raw['rules']!=design['rules']:raise ValueError('Incomplete or incompatible report')
    if d.digest(BASE)!=design['baseline_sha256'] or d.digest(CONTINUOUS)!=design['continuous_sha256']:raise ValueError('Control cache hash mismatch')
    committed(DESIGN.relative_to(ROOT).as_posix(),design_sha)
    for group in ['source_hashes','opened_product_hashes']:
        for path,expected in design[group].items():
            if d.digest(ROOT/path)!=expected:raise ValueError('Source or product changed: '+path)
            committed(path,expected)
    protocol=read(ROOT/'web/data/ablation/design.json')
    expected={(f,float(c['snr_per_frame']),tuple(c['motion'])) for f in design['rules']['fields'] for c in design['rules']['cases']};seen=set()
    result={'version':'0.10.0-sandwich-results.1','role':'opened-field fixed-weight empirical covariance development',
      'provenance':{'protocol_commit':COMMIT,'design_path':DESIGN.relative_to(ROOT).as_posix(),'design_sha256':design_sha,
        'raw_report_path':RAW.relative_to(ROOT).as_posix(),'raw_report_sha256':d.digest(RAW),'baseline_sha256':design['baseline_sha256'],
        'continuous_sha256':design['continuous_sha256'],'source_hashes':design['source_hashes'],
        'opened_product_hashes':design['opened_product_hashes'],'builder_sha256':d.digest(__file__)},
      'rules':design['rules'],'record_schema':{'per_frame':['obs_id','snr','core_rms','core_coverage','core_outlier_fraction','information_fraction','downweighted_pixels'],
        'sandwich_exposure':['obs_id','profile_scalar_score_xy','residual_jacobian_score_xy']},
      'limitations':['Point estimates unchanged by covariance method; new-noise point fits have no previous paired cache',
        'quality and point validity are retained from frozen fitter; total amplitude is not present in its public epoch record',
        'conditional on final IRLS weights; no physical PSF validation, source shot noise, or simulated registration errors'],
      'field_provenance':{},'cases':[]}
    for case in raw['cases']:
        key=(case['field'],float(case['snr_per_frame']),tuple(case['truth_delta_sky_px']))
        if key not in expected or key in seen:raise ValueError('Unexpected or duplicate case')
        seen.add(key)
        if case['noise_seed']!=design['rules']['noise_seeds'][case['field']][str(int(case['snr_per_frame']))]:raise ValueError('Seed mismatch')
        seed_text='sandwich-development.1|'+case['field']+'|'+str(int(case['snr_per_frame']))+'|'+','.join(format(float(x),'.8g') for x in case['truth_delta_sky_px'])
        if case['noise_seed']!=str(int.from_bytes(sha256(seed_text.encode('utf-8')).digest()[:8],'big')):raise ValueError('Seed derivation mismatch')
        if len(case['records'])!=128 or [r['draw'] for r in case['records']]!=list(range(128)):raise ValueError('Draw sequence mismatch')
        for row in case['records']:validate_row(row,case['truth_delta_sky_px'])
        validate_row(case['original_background']['candidate'],case['truth_delta_sky_px'])
        f=next(v for v in baseline['fields'] if v['id']==case['field'])
        old=next(v for v in f['cases'] if v['snr_per_frame']==case['snr_per_frame'] and v['truth_delta_px']==case['truth_delta_sky_px'])
        if case['original_background']['frozen_baseline']!=old['frozen_result']:raise ValueError('Original-background baseline mismatch')
        prior=next(v for v in continuous['cases'] if v['field']==case['field'] and v['snr_per_frame']==case['snr_per_frame'])['original_background']['candidate']
        orig=case['original_background']['candidate']
        for i,key2 in enumerate(['before','after']):close(orig['epochs'][i]['position_px'],prior[key2]['position_px'],'original point replay')
        close(orig['error_east_north_arcsec'],prior['error_east_north_arcsec'],'original error replay')
        close(orig['methods']['gauss_newton']['plus_registration']['covariance_arcsec2'],prior['gauss_newton_covariance_arcsec2'],'original GN replay')
        recomputed=summarize(case['records']);same(case['summary'],recomputed,'raw summary')
        item=next(v for v in protocol['fields']['validation'] if v['field']['id']==case['field']);manifest=item['input_manifest']
        selected={p[e] for p in item['pairs'] for e in ['before','after']}
        result['field_provenance'][case['field']]={'field':item['field'],'manifest_path':item['manifest_path'],'manifest_sha256':item['manifest_sha256'],
            'calibrations':manifest['calibrations'],'gaia':manifest['gaia'],'infrared':item['infrared'],'selected_pairs':item['pairs'],
            'selected_records':[{k:r[k] for k in ['obs_id','access_url','cutout_url','mjd','epoch','detector','collection','path','sha256','status'] if k in r}
                                for r in manifest['records'] if r['obs_id'] in selected]}
        result['cases'].append({**{k:v for k,v in case.items() if k not in ['records','summary','original_background']},
          'summary':recomputed,'records':[compact_row(r) for r in case['records']],
          'original_background':{'frozen_baseline':case['original_background']['frozen_baseline'],'candidate':compact_row(orig)},
          'original_point_replay':'both epoch positions, error and GN total covariance equal f138 cache within numerical tolerance'})
    if seen!=expected:raise ValueError('Missing case')
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_bytes((json.dumps(d.jsonable(result),ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8'))
    print('WROTE',OUT,'bytes',OUT.stat().st_size,'sha256',d.digest(OUT),flush=True)
    overview=build_overview(result,d.digest(OUT),OUT.stat().st_size)
    OVERVIEW.write_bytes((json.dumps(d.jsonable(overview),ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8'))
    print('WROTE',OVERVIEW,'bytes',OVERVIEW.stat().st_size,'sha256',d.digest(OVERVIEW),flush=True)


if __name__=='__main__':build()
