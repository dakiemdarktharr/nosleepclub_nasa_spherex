"""Audit and publish a compact, reproducible paired development summary."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import numpy as np
from . import diagnose_bias as d

ROOT=d.ROOT
DESIGN=ROOT/'web/data/continuous-epsf/design.json'
RAW=ROOT/'data/raw/benchmark/continuous-epsf-development.json'
BASE=ROOT/'data/raw/benchmark/bias-gaussian64-development.json'
PROFILE=ROOT/'data/raw/benchmark/profile-gaussian64-development.json'
OUT=ROOT/'web/data/continuous-epsf/development-summary.json'
COMMIT='f138e1109183bb7db2122384ec1cfcd8f5958488'
THRESHOLDS={'68':2.27886856637673,'95':5.99146454710798}


def close(a,b,label):
    if not np.allclose(a,b,rtol=1e-9,atol=1e-9):raise ValueError('Audit mismatch: '+label)


def load(path):return json.loads(path.read_text(encoding='utf-8'))


def committed(path,expected,commit=COMMIT):
    blob=subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)
    if d.sha256(blob).hexdigest()!=expected:raise ValueError('Committed content mismatch: '+path)


def validate_profile(p,epoch):
    if 'hessians' in p:
        matrices=np.asarray(p['hessians']);change=np.linalg.norm(matrices[0]-matrices[1])/max(np.linalg.norm(matrices[1]),1e-15)
        close(change,p['relative_step_change'],'Hessian step change')
        if p['supported']:
            if change>.05 or np.linalg.eigvalsh(matrices[0]).min()<=0:raise ValueError('Unsupported Hessian marked supported')
            close(np.asarray(p['covariance_px2']),np.linalg.inv(matrices[0])*max(1.,epoch['reduced_chi2']),'epoch profile covariance')
        elif p.get('reason')=='unstable_profile_curvature' and change<=.05:
            raise ValueError('Inconsistent unstable Hessian')


def check_pair(case,record,oldprofile):
    b,n=record['baseline'],record['candidate'];transform=d.study.gaia.TRANSFORM
    if b['numeric_valid']!=oldprofile['numeric_valid'] or b['accepted']!=oldprofile['accepted']:
        raise ValueError('Baseline/profile statuses mismatch')
    if b.get('numeric_valid'):
        close(b['error_east_north_arcsec'],oldprofile['error_east_north_arcsec'],'baseline profile error')
        close(b['covariance_arcsec2'],oldprofile['gauss_newton_covariance_arcsec2'],'baseline profile GN covariance')
        close(b['mahalanobis2_raw'],oldprofile['gauss_newton_q'],'baseline profile GN q')
        for epoch,p in zip(['before','after'],oldprofile.get('epoch_curvature',[])):
            validate_profile(p,b[epoch])
    registration=None
    for side,x in [('baseline',b),('candidate',n)]:
        if not x.get('numeric_valid'):continue
        pos0=np.asarray(x['before']['position_px']);pos1=np.asarray(x['after']['position_px'])
        error=transform@(pos1-pos0-np.asarray(case['truth_delta_sky_px']))
        close(error,x['error_east_north_arcsec'],side+' error vector')
        close(np.linalg.norm(error),x['error_arcsec'],side+' error magnitude')
        cov=np.asarray(x['covariance_arcsec2'] if side=='baseline' else x['gauss_newton_covariance_arcsec2'])
        if np.linalg.eigvalsh(cov).min()<=0:raise ValueError('Nonpositive covariance')
        q=x['mahalanobis2_raw' if side=='baseline' else 'gauss_newton_q']
        close(q,error@np.linalg.solve(cov,error),side+' q')
        fitcov=transform@(np.asarray(x['before']['covariance_px2'])+np.asarray(x['after']['covariance_px2']))@transform.T
        if side=='baseline':registration=cov-fitcov
        elif registration is not None:close(cov,fitcov+registration,'GN registration covariance')
    if n.get('numeric_valid'):
        for epoch in ['before','after']:validate_profile(n[epoch]['profile'],n[epoch])
        profiles=[n[k]['profile'] for k in ['before','after']]
        if all(p['supported'] for p in profiles):
            if 'profile_q' not in n:raise ValueError('Missing supported profile q')
            if registration is not None:
                cov=registration+transform@sum(np.asarray(p['covariance_px2']) for p in profiles)@transform.T
                close(cov,n['profile_covariance_arcsec2'],'profile registration covariance')
            close(n['profile_q'],np.asarray(n['error_east_north_arcsec'])@np.linalg.solve(n['profile_covariance_arcsec2'],n['error_east_north_arcsec']),'profile q')
        elif 'profile_q' in n:raise ValueError('Unsupported profile q present')
    if 'profile_q' in oldprofile:
        cov=np.asarray(oldprofile['profile_covariance_arcsec2'])
        error=np.asarray(b['error_east_north_arcsec'])
        close(oldprofile['profile_q'],error@np.linalg.solve(cov,error),'baseline profile q')
        if registration is not None:
            expected=registration+transform@sum(np.asarray(p['covariance_px2']) for p in oldprofile['epoch_curvature'])@transform.T
            close(cov,expected,'baseline profile covariance')


def compact(x,candidate=False):
    output={'valid':x['numeric_valid'],'accepted':x['accepted'],'reasons':x.get('quality_reasons',[])}
    if 'failure' in x:output.update(failure=x['failure'],detail=x.get('detail'))
    if 'error_east_north_arcsec' in x:
        output.update(error=x['error_east_north_arcsec'],point=[x[k]['position_px'] for k in ['before','after']],
                      covariance=x.get('gauss_newton_covariance_arcsec2') if candidate else x.get('covariance_arcsec2'),
                      q=x.get('gauss_newton_q') if candidate else x.get('mahalanobis2_raw'))
    if candidate:
        output['profile_covariance']=x.get('profile_covariance_arcsec2');output['profile_q']=x.get('profile_q')
        output['epoch_profile']=[compact_profile(x[k]['profile'])
            for k in ['before','after'] if k in x]
    return output


def areas(covariances):
    return [float(np.pi*THRESHOLDS['68']*np.sqrt(np.linalg.det(np.asarray(c)))) for c in covariances if c is not None]


def metrics(rows):
    result={'attempts':len(rows)}
    groups={'baseline_numeric':lambda b,c:b['valid'],'baseline_accepted':lambda b,c:b['accepted'],
            'candidate_numeric':lambda b,c:c['valid'],'candidate_accepted':lambda b,c:c['accepted'],
            'common_numeric':lambda b,c:b['valid'] and c['valid'],'common_accepted':lambda b,c:b['accepted'] and c['accepted']}
    for label,select in groups.items():
        pairs=[(r['baseline'],r['candidate']) for r in rows if select(r['baseline'],r['candidate'])]
        v={'count':len(pairs)}
        for key,side,qkey,covkey in [('baseline_gn',0,'q','covariance'),('baseline_profile',0,'profile_q','profile_covariance'),('candidate_gn',1,'q','covariance'),('candidate_profile',1,'profile_q','profile_covariance')]:
            selected=[p[side] for p in pairs if p[side]['valid'] and p[side].get(qkey) is not None]
            q=[r[qkey] for r in selected];area=areas([r[covkey] for r in selected])
            v[key]={'available':len(q),'within68':sum(x<=THRESHOLDS['68'] for x in q),
                    'within95':sum(x<=THRESHOLDS['95'] for x in q),
                    'median_area68_arcsec2':float(np.median(area)) if area else None}
        for key,idx in [('baseline',0),('candidate',1)]:
            error=[float(np.linalg.norm(p[idx]['error'])) for p in pairs if p[idx]['valid'] and 'error' in p[idx]]
            v[key+'_error']={'available':len(error),'rms_arcsec':float(np.sqrt(np.mean(np.square(error)))) if error else None,
                            'p90_arcsec':float(np.percentile(error,90)) if error else None}
        common=[p for p in pairs if p[0]['valid'] and p[1]['valid']]
        v['paired_rms_delta_arcsec']=float(np.sqrt(np.mean([np.dot(p[1]['error'],p[1]['error']) for p in common]))-
              np.sqrt(np.mean([np.dot(p[0]['error'],p[0]['error']) for p in common]))) if common else None
        v['paired_error_count']=len(common)
        result[label]=v
    return result


def compact_profile(v):
    return [v['supported'],v.get('reason'),v.get('relative_step_change')]


def build():
    design=load(DESIGN);raw=load(RAW);baseline=load(BASE);profile=load(PROFILE)
    if not raw['completed'] or not baseline['completed'] or not profile['completed']:raise ValueError('Incomplete inputs')
    design_sha=d.digest(DESIGN);baseline_sha=d.digest(BASE)
    if raw['design_sha256']!=design_sha or design['paired_baseline_sha256']!=baseline_sha or profile['paired_control_sha256']!=baseline_sha:raise ValueError('Provenance mismatch')
    if raw['rules']!=design['rules']:raise ValueError('Protocol mismatch')
    committed('web/data/continuous-epsf/design.json',design_sha)
    for group in ['source_hashes','opened_product_hashes']:
        for path,digest in design[group].items():
            if d.digest(ROOT/path)!=digest:raise ValueError('Disk hash mismatch '+path)
            committed(path,digest)
    for path,digest in profile['sources'].items():
        if d.digest(ROOT/path)!=digest:raise ValueError('Baseline profile source hash mismatch '+path)
        committed(path,digest)
    ablation=load(ROOT/'web/data/ablation/design.json')
    result={'version':'0.10.0-continuous-epsf-results.1','role':'opened-field development; not astronomical validation',
        'provenance':{'protocol_commit':COMMIT,'design_path':'web/data/continuous-epsf/design.json','design_sha256':design_sha,
          'raw_report_path':'data/raw/benchmark/continuous-epsf-development.json','raw_report_sha256':d.digest(RAW),
          'paired_baseline_sha256':baseline_sha,'baseline_profile_sha256':d.digest(PROFILE),'baseline_profile_source_hashes':profile['sources'],
          'builder_sha256':d.digest(__file__),'source_hashes':design['source_hashes'],'opened_product_hashes':design['opened_product_hashes']},
        'rules':raw['rules'],'ellipse_thresholds':THRESHOLDS,
        'record_schema':'error is east,north arcsec; point is before,after sky pixel; covariance and profile_covariance are displacement arcsec²; q is squared Mahalanobis; epoch_profile and baseline_epoch_profile elements are [supported, reason, relative_step_change] in before,after order',
        'field_provenance':{},'cases':[]}
    expected={(f,float(c['snr_per_frame']),tuple(c['motion'])) for f in design['rules']['fields'] for c in design['rules']['cases']}
    seen=set()
    for case in raw['cases']:
        key=(case['field'],float(case['snr_per_frame']),tuple(case['truth_delta_sky_px']))
        if key not in expected or key in seen:raise ValueError('Unexpected/duplicate case')
        seen.add(key)
        source=next(v for v in ablation['fields']['validation'] if v['field']['id']==case['field'])
        basefield=next(v for v in baseline['fields'] if v['id']==case['field'])
        oldcase=next(v for v in basefield['cases'] if v['snr_per_frame']==case['snr_per_frame'] and v['truth_delta_px']==case['truth_delta_sky_px'])
        pcase=next(v for v in profile['cases'] if v['field_id']==case['field'] and v['snr_per_frame']==case['snr_per_frame'] and v['truth_delta_px']==case['truth_delta_sky_px'])
        rows=case['records'];oldrows=oldcase['independent_gaussian_controls']['records'];prows=pcase['records']
        if len(rows)!=64 or len(oldrows)!=64 or len(prows)!=64 or [r['draw'] for r in rows]!=list(range(64)):raise ValueError('Draw count/index mismatch')
        if case['original_background']['baseline']!=oldcase['frozen_result'] or not case['baseline_replay']['status_matches'] or case['baseline_replay']['draw']!=0 or case['baseline_replay']['max_vector_difference_arcsec']>1e-5:raise ValueError('Baseline replay mismatch')
        original=case['original_background'];b=original['baseline']
        oldcheck={'numeric_valid':b['numeric_valid'],'accepted':b['accepted']}
        if b['numeric_valid']:
            oldcheck.update(error_east_north_arcsec=b['error_east_north_arcsec'],
                gauss_newton_covariance_arcsec2=b['covariance_arcsec2'],gauss_newton_q=b['mahalanobis2_raw'])
        check_pair(case,original,oldcheck)
        pairs=[]
        for row,old,pr in zip(rows,oldrows,prows):
            if row['baseline']!=old or row['draw']!=pr['draw']:raise ValueError('Baseline cache or profile pairing mismatch')
            check_pair(case,row,pr)
            old_compact=compact(row['baseline'])
            old_compact['profile_q']=pr.get('profile_q');old_compact['profile_covariance']=pr.get('profile_covariance_arcsec2')
            pairs.append({'draw':row['draw'],'baseline':old_compact, 'candidate':compact(row['candidate'],True),
                          'baseline_epoch_profile':[compact_profile(v) for v in pr.get('epoch_curvature',[])]})
        outmetrics=metrics(pairs)
        for group,record in case['summary'].items():
            if group=='attempts':
                if record!=outmetrics[group]:raise ValueError('Attempt mismatch')
                continue
            check=outmetrics[group]
            if record['count']!=check['count']:raise ValueError('Group denominator mismatch')
            for metric in ['baseline_gn','candidate_gn','candidate_profile']:
                if any(record[metric][k]!=check[metric][k] for k in ['available','within68','within95']):raise ValueError('Coverage mismatch')
            for metric in ['baseline_error','candidate_error']:
                if record[metric]['available']!=check[metric]['available']:raise ValueError('Error denominator mismatch')
                for k in ['rms_arcsec','p90_arcsec']:
                    if record[metric][k] is not None:close(record[metric][k],check[metric][k],group+' '+metric+' '+k)
        selected={p[e] for p in source['pairs'] for e in ['before','after']}
        input_manifest=source['input_manifest']
        provenance={'field':source['field'],'manifest_path':source['manifest_path'],'manifest_sha256':source['manifest_sha256'],
                    'calibrations':input_manifest['calibrations'],'gaia':input_manifest['gaia'],
                    'infrared':source['infrared'],'selected_pairs':source['pairs'],
                    'selected_records':[{k:v[k] for k in ['obs_id','access_url','cutout_url','mjd','epoch','detector','collection','path','sha256','status'] if k in v}
                                        for v in input_manifest['records'] if v['obs_id'] in selected]}
        result['field_provenance'][case['field']]=provenance
        result['cases'].append({'field':case['field'],'snr_per_frame':case['snr_per_frame'],
            'truth_delta_sky_px':case['truth_delta_sky_px'],'anchor_sky_px':case['anchor_sky_px'],
            'opened_result':case['source'],'baseline_replay':case['baseline_replay'],
            'gaussian_summary':outmetrics,
            'original_background':{side:compact(case['original_background'][side],side=='candidate') for side in ['baseline','candidate']},
            'paired_draws':pairs})
    if seen!=expected:raise ValueError('Missing case')
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_bytes((json.dumps(d.jsonable(result),ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8'))
    print('WROTE',OUT,'bytes',OUT.stat().st_size,'sha256',d.digest(OUT),flush=True)


if __name__=='__main__':build()
