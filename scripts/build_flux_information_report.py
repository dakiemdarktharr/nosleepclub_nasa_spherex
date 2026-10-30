"""Audit locked truth-point probe and publish its complete paired records."""
import json
from pathlib import Path
import subprocess
import numpy as np
from . import diagnose_bias as d
from . import run_flux_information_probe as locked_probe

ROOT=d.ROOT
DESIGN=ROOT/'web/data/flux-information/design.json'
RAW=ROOT/'data/raw/benchmark/flux-information-development.json'
BIAS=ROOT/'data/raw/benchmark/bias-gaussian64-development.json'
CONTINUOUS=ROOT/'data/raw/benchmark/continuous-epsf-development.json'
OUT=ROOT/'web/data/flux-information/development-summary.json'
COMMIT='215dbfab9fb02ed8a1faec43639fd224ea52450d'


def load(path):return json.loads(path.read_text(encoding='utf-8'))


def close(a,b,label):
    if not np.allclose(a,b,rtol=1e-9,atol=1e-9):raise ValueError('Audit mismatch: '+label)


def trace(f,m):return float(np.trace(np.linalg.solve(f,m))/2)


def committed(path,expected):
    blob=subprocess.check_output(['git','show',COMMIT+':'+path],cwd=ROOT)
    if d.sha256(blob).hexdigest()!=expected:raise ValueError('Commit hash mismatch: '+path)


def check_geom(geo):
    if not geo['supported']:return
    f=np.asarray(geo['fisher_effective']);known=np.asarray(geo['fisher_known']);g=np.asarray(geo['expected_jtj_matched']);v=np.asarray(geo['expected_score_covariance_matched'])
    if np.linalg.eigvalsh(f).min()<=0:raise ValueError('Fisher not positive definite')
    if np.linalg.eigvalsh(known-f).min()<-1e-8:raise ValueError('Known-flux information below profiled information')
    close(g,2*v-f,'identity G = 2V - F')
    close(geo['known_normalized_trace'],trace(f,known),'known trace')
    close(geo['expected_jtj_normalized_trace_matched'],trace(f,g),'G trace')
    close(geo['expected_mean_score_q_matched'],2*trace(f,v),'theoretical score q')
    if len(geo['amplitudes'])!=len(geo['observations']):raise ValueError('Amplitude count mismatch')
    dof=0
    for a,obs in zip(geo['amplitudes'],geo['observations']):
        close(obs['true_flux_snr_projected'],a*np.sqrt(obs['target_information']),'projected SNR')
        dof+=obs['native_pixels']-obs['nuisance_rank']-1
    if dof!=geo['dof']:raise ValueError('Degrees of freedom mismatch')


def validate_trial(geo,trial):
    if 'failure' in trial:return
    f=np.asarray(geo['fisher_effective']);score=np.asarray(trial['profile_score'])
    close(trial['score_q'],score@np.linalg.solve(f,score),'score quadratic')
    mats=np.asarray(trial['hessians']);change=np.linalg.norm(mats[0]-mats[1])/max(np.linalg.norm(mats[1]),1e-15)
    close(change,trial['hessian_relative_step_change'],'Hessian stability change')
    if trial['hessian_stable'] != bool(np.isfinite(mats).all() and change<=.05):raise ValueError('Hessian stability flag mismatch')
    if trial['dof']!=geo['dof'] or len(trial['profile_amplitudes'])!=len(geo['amplitudes']):raise ValueError('Trial degrees/amplitudes mismatch')
    if trial['profile_chi2']<0 or np.linalg.eigvalsh(trial['jtj']).min()<-1e-8:raise ValueError('Invalid chi2 or JtJ')


def audit_summary(geo,rows,raw_summary,indices):
    good=[r for r in rows if 'failure' not in r];f=np.asarray(geo['fisher_effective'])
    if raw_summary['attempts']!=len(rows) or raw_summary['successful']!=len(good) or raw_summary['failures']!=len(rows)-len(good):raise ValueError('Draw denominator mismatch')
    reasons={k:sum(r.get('failure')==k for r in rows) for k in sorted({r['failure'] for r in rows if 'failure' in r})}
    if raw_summary['failure_reasons']!=reasons:raise ValueError('Failure reasons mismatch')
    for r in good:validate_trial(geo,r)
    if not good:return {'attempts':len(rows),'successful':0,'failures':len(rows),'failure_reasons':reasons}
    for name,key in [('jtj',None),('hessian_002',0),('hessian_004',1)]:
        matrices=np.array([r['jtj'] if key is None else r['hessians'][key] for r in good])
        values=np.array([trace(f,m) for m in matrices]);target=raw_summary[name]
        close(matrices.mean(axis=0),target['mean_matrix'],name+' mean matrix')
        close(values.mean(),target['normalized_trace'],name+' trace mean')
        if len(good)==len(rows):close(np.quantile(values[indices].mean(axis=1),[.025,.975]),target['draw_bootstrap_95'],name+' CI')
        elif target['draw_bootstrap_95'] is not None:raise ValueError('CI emitted despite failed draw')
    scores=np.array([r['profile_score'] for r in good]);mean=scores.mean(axis=0);cov=np.cov(scores,rowvar=False)
    close(mean,raw_summary['mean_score'],'score mean');close(cov,raw_summary['score_covariance'],'score covariance')
    close(np.mean([r['score_q'] for r in good]),raw_summary['mean_score_q'],'mean score q')
    close(np.mean([r['profile_chi2'] for r in good]),raw_summary['mean_chi2'],'chi2 mean')
    close(raw_summary['mean_chi2']/geo['dof'],raw_summary['mean_reduced_chi2'],'chi2/dof')
    if raw_summary['hessian_stable']!=sum(r['hessian_stable'] for r in good) or raw_summary['dof']!=geo['dof']:raise ValueError('Stability or dof mismatch')
    if len(good)==len(rows):close(np.quantile(scores[indices].mean(axis=1),[.025,.975],axis=0),raw_summary['mean_score_draw_bootstrap_95'],'score CI')
    elif raw_summary['mean_score_draw_bootstrap_95'] is not None:raise ValueError('Score CI emitted despite failed draw')
    covariance_ci=None
    if len(good)==len(rows):
        bootstrap=[trace(f,np.cov(scores[index],rowvar=False)) for index in indices]
        covariance_ci=np.quantile(bootstrap,[.025,.975]).tolist()
    return {'score_covariance_normalized_trace':trace(f,cov),
            'expected_score_covariance_normalized_trace_matched':trace(f,geo['expected_score_covariance_matched']),
            'score_covariance_draw_bootstrap_95_posthoc':covariance_ci,
            'score_covariance_ci_note':'post hoc exploratory draw bootstrap; not multiple-comparison adjusted'}


def paired_diagnostic(geo,matched,old,indices):
    if any('failure' in a or 'failure' in b for a,b in zip(matched,old)):
        return {'count':sum('failure' not in a and 'failure' not in b for a,b in zip(matched,old)),
                'note':'paired CI omitted because there were failed draws'}
    f=np.asarray(geo['fisher_effective']);out={'count':len(matched),'note':'post hoc old-nearest minus matched-padded paired draw bootstrap'}
    for label,func in [('jtj',lambda r:r['jtj']),('hessian_002',lambda r:r['hessians'][0]),('hessian_004',lambda r:r['hessians'][1])]:
        delta=np.array([trace(f,func(b))-trace(f,func(a)) for a,b in zip(matched,old)])
        out[label]={'mean':float(delta.mean()),'draw_bootstrap_95':np.quantile(delta[indices].mean(axis=1),[.025,.975]).tolist()}
    return out


def audit_reconstructed_geometry(case,epochs,replay):
    """Re-derive contributions after the run using frozen geometry and inputs."""
    for k,v in replay.items():close(v,case['signal_variance_replay'][k],'native input replay '+k)
    output=[]
    for epoch,raw in zip(epochs,case['geometry']):
        geometry=epoch['geometry']
        if geometry is None or not raw['supported']:raise ValueError('Unsupported geometry')
        sums={name:np.zeros((2,2)) for name in ['F','known','G','V']}
        contributions=[]
        if len(geometry['entries'])!=len(raw['observations']):raise ValueError('Exposure count changed')
        for e,obs,a in zip(geometry['entries'],raw['observations'],raw['amplitudes']):
            obs_id=e['sample']['frame']['record']['obs_id'];amp=e['amplitude'];info=e['I']
            if obs_id!=obs['obs_id']:raise ValueError('Exposure ordering changed')
            close(amp,a,'injected amplitude');close(info,obs['target_information'],'target information')
            s=e['transverse'].T@e['transverse'];t=e['D'].T@e['D']
            sums['F']+=amp**2*s;sums['known']+=amp**2*t
            sums['G']+=(amp**2+2/info)*s;sums['V']+=(amp**2+1/info)*s
            contributions.append({'obs_id':obs_id,'amplitude':amp,'target_information':info,
                'projected_derivative_gram':s,'known_flux_derivative_gram':t})
        for k,target in [('F','fisher_effective'),('known','fisher_known'),('G','expected_jtj_matched'),('V','expected_score_covariance_matched')]:
            close(sums[k],raw[target],'reconstructed '+target)
        output.append({'method':'post-run deterministic reconstruction using commit 215dbfa and hash-validated cached inputs; not a new draw or independent derivative implementation',
                       'per_exposure':contributions,'recomputed_matrices':sums})
    return output


def build():
    design=load(DESIGN);raw=load(RAW);identity=d.digest(DESIGN)
    if not raw['completed'] or raw['design_sha256']!=identity or raw['rules']!=design['rules']:raise ValueError('Incomplete or incompatible report')
    if d.digest(BIAS)!=design['bias_control_sha256'] or d.digest(CONTINUOUS)!=design['continuous_control_sha256']:raise ValueError('Paired cache hashes differ')
    committed(DESIGN.relative_to(ROOT).as_posix(),identity)
    for group in ['source_hashes','opened_product_hashes']:
        for path,sha in design[group].items():
            if d.digest(ROOT/path)!=sha:raise ValueError('Source changed: '+path)
            committed(path,sha)
    boot=np.random.default_rng(design['rules']['bootstrap_seed']).integers(0,64,size=(design['rules']['bootstrap_draws'],64))
    expected={(f,float(c['snr_per_frame']),tuple(c['motion'])) for f in design['rules']['fields'] for c in design['rules']['cases']}
    seen=set()
    result={'version':'0.10.0-flux-information-results.1','role':'opened-field truth-point conditional numerical diagnostic',
        'provenance':{'protocol_commit':COMMIT,'design_path':DESIGN.relative_to(ROOT).as_posix(),'design_sha256':identity,
          'raw_report_path':RAW.relative_to(ROOT).as_posix(),'raw_report_sha256':d.digest(RAW),
          'bias_control_sha256':design['bias_control_sha256'],'continuous_control_sha256':design['continuous_control_sha256'],
          'source_hashes':design['source_hashes'],'opened_product_hashes':design['opened_product_hashes'],
          'builder_sha256':d.digest(__file__)},'rules':design['rules'],
        'limitations':['No centroid fit or coverage evaluation',
          'Per-exposure derivative matrices are a post-run deterministic reconstruction from cached native inputs using the same frozen implementation; raw report did not record them',
          'same RNG draw index shared between conditions and epochs; 64 draws are not independent fields',
          'old-nearest mean differs from matched-padded; matched theory is not assumed for secondary'],
        'field_provenance':{},'cases':[]}
    loaded={}
    for case in raw['cases']:
        key=(case['field'],float(case['snr_per_frame']),tuple(case['truth_delta_sky_px']))
        if key in seen or key not in expected:raise ValueError('Unexpected or duplicated case')
        seen.add(key);rows=case['records']
        if len(rows)!=64 or [r['draw'] for r in rows]!=list(range(64)):raise ValueError('Invalid draw sequence')
        if len(case['geometry'])!=2:raise ValueError('Epoch count mismatch')
        for g in case['geometry']:check_geom(g)
        if case['field'] not in loaded:
            print('RECONSTRUCT',case['field'],flush=True)
            loaded[case['field']]=d.load_field(case['field'])
        item,_,catalog,xy,before,after,source=loaded[case['field']]
        if source!=case['source']:raise ValueError('Opened field source mismatch')
        epochs,replay=locked_probe.prepare_case(before,after,catalog,xy,case['anchor_sky_px'],
                                               np.asarray(case['truth_delta_sky_px']),case['snr_per_frame'])
        reconstructed=audit_reconstructed_geometry(case,epochs,replay)
        manifest=item['input_manifest'];selected={p[e] for p in item['pairs'] for e in ['before','after']}
        result['field_provenance'][case['field']]={'field':item['field'],'manifest_path':item['manifest_path'],
            'manifest_sha256':item['manifest_sha256'],'calibrations':manifest['calibrations'],'gaia':manifest['gaia'],
            'infrared':item['infrared'],'selected_pairs':item['pairs'],
            'selected_records':[{k:r[k] for k in ['obs_id','access_url','cutout_url','mjd','epoch','detector','collection','path','sha256','status'] if k in r}
                                for r in manifest['records'] if r['obs_id'] in selected]}
        diagnostics={}
        for condition in design['rules']['truth_conditions']:
            diagnostics[condition]=[]
            for epoch,g in enumerate(case['geometry']):
                samples=[row['conditions'][condition][epoch] for row in rows]
                if not g['supported']:raise ValueError('Unsupported geometry retained; public build requires explicit audit')
                diagnostics[condition].append(audit_summary(g,samples,case['summaries'][condition][epoch],boot))
        paired=[paired_diagnostic(g,[r['conditions']['matched_padded_primary'][e] for r in rows],
                                  [r['conditions']['old_nearest_secondary'][e] for r in rows],boot) for e,g in enumerate(case['geometry'])]
        result['cases'].append({**case,'post_run_geometry_audit':reconstructed,
                                'additional_diagnostics':diagnostics,'paired_old_minus_matched':paired})
    if seen!=expected:raise ValueError('Missing case')
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_bytes((json.dumps(d.jsonable(result),ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8'))
    print('WROTE',OUT,'bytes',OUT.stat().st_size,'sha256',d.digest(OUT),flush=True)


if __name__=='__main__':build()
