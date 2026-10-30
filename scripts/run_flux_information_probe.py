"""Locked, fixed-weight truth-point flux-information development experiment."""
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np
from . import diagnose_bias as d
from . import continuous_epsf_model as candidate
from . import flux_information_probe as probe

ROOT=d.ROOT
DESIGN=ROOT/'web/data/flux-information/design.json'
OUTPUT=ROOT/'data/raw/benchmark/flux-information-development.json'
BIAS=ROOT/'data/raw/benchmark/bias-gaussian64-development.json'
CONTINUOUS=ROOT/'data/raw/benchmark/continuous-epsf-development.json'
RULES={'version':'0.10.0-flux-information-development.1','fields':d.RULES['fields'],
       'cases':d.RULES['cases'],'patch_index':1,'draws_per_case':64,'noise_seed':20261030,
       'bootstrap_seed':20261031,'bootstrap_draws':2000,
       'truth_conditions':['matched_padded_primary','old_nearest_secondary'],
       'derivative_step_sky_px':probe.DERIVATIVE_STEP,'hessian_steps_sky_px':list(probe.HESSIAN_STEPS),
       'hessian_relative_stability_max':.05,'fisher_rank_relative_cut':probe.RANK_RELATIVE,
       'amplitudes':'per-exposure SNR * sqrt(pinv(plane-only unpadded weighted design normal matrix)[0,0]); computed at true position',
       'noise':'same seed, full native array shapes and frame ordering as paired Gaussian cache; one noise stream shared by conditions',
       'weight':'original inverse variance, fixed; no IRLS and no chi-square inflation',
       'truth_point':'known injection location, per epoch; no optimizer or point-estimator/coverage claim',
       'qualification':'three already opened fields; synthetic noise, fixed nuisance positions, no source shot noise or physical PSF validation'}


def inputs():
    paths=['scripts/flux_information_probe.py','scripts/run_flux_information_probe.py',
           'tests/test_flux_information_probe.py','docs/FLUX_INFORMATION_PROTOCOL.md','requirements.txt',
           'scripts/continuous_epsf_model.py','scripts/run_continuous_epsf_study.py','scripts/diagnose_bias.py',
           'scripts/profile_uncertainty.py']+['scripts/'+v for v in d.study.sources()]
    products=['web/data/continuous-epsf/design.json','web/data/ablation/design.json']+[
        'web/data/ablation/validation-'+v+'.json' for v in RULES['fields']]
    return {p:d.digest(ROOT/p) for p in paths},{p:d.digest(ROOT/p) for p in products}


def create_design():
    if DESIGN.exists():raise RuntimeError('Existing design cannot be overwritten')
    bias=json.loads(BIAS.read_text(encoding='utf-8'));continuous=json.loads(CONTINUOUS.read_text(encoding='utf-8'))
    if not bias['completed'] or bias['noise_draws']!=64 or not continuous['completed']:
        raise RuntimeError('Paired caches incomplete')
    if continuous['design_sha256']!=d.digest(ROOT/'web/data/continuous-epsf/design.json'):
        raise RuntimeError('Continuous protocol mismatch')
    for ident in RULES['fields']:
        field=next(f for f in bias['fields'] if f['id']==ident)
        for wanted in RULES['cases']:
            case=next(c for c in field['cases'] if c['patch_index']==RULES['patch_index'] and c['truth_psf']=='nearest'
                      and c['snr_per_frame']==wanted['snr_per_frame'] and c['truth_delta_px']==wanted['motion'])
            recorded=next(c for c in continuous['cases'] if c['field']==ident and c['snr_per_frame']==wanted['snr_per_frame']
                          and c['truth_delta_sky_px']==wanted['motion'])
            if len(case['independent_gaussian_controls']['records'])!=64 or len(recorded['records'])!=64:
                raise RuntimeError('Incomplete paired case')
            if [r['draw'] for r in recorded['records']]!=list(range(64)) or any(
                    a['baseline']!=b for a,b in zip(recorded['records'],case['independent_gaussian_controls']['records'])):
                raise RuntimeError('Paired baseline cache mismatch')
    sources,products=inputs()
    document={'rules':RULES,'source_hashes':sources,'opened_product_hashes':products,
              'bias_control_sha256':d.digest(BIAS),'continuous_control_sha256':d.digest(CONTINUOUS),
              'status':'locked prospective numerical diagnostic on opened fields; not validation'}
    DESIGN.parent.mkdir(parents=True,exist_ok=True)
    DESIGN.write_bytes((json.dumps(d.jsonable(document),ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8'))
    print('DESIGN',DESIGN,d.digest(DESIGN),flush=True)


def verify_design():
    protocol=json.loads(DESIGN.read_text(encoding='utf-8'));sources,products=inputs()
    if protocol['rules']!=RULES or protocol['source_hashes']!=sources or protocol['opened_product_hashes']!=products:
        raise RuntimeError('Design, source or opened product hash mismatch')
    if protocol['bias_control_sha256']!=d.digest(BIAS) or protocol['continuous_control_sha256']!=d.digest(CONTINUOUS):
        raise RuntimeError('Paired control cache mismatch')
    for path in [*sources,*products,DESIGN.relative_to(ROOT).as_posix()]:
        try:blob=subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT,stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as exc:raise RuntimeError('Required source or design not committed: '+path) from exc
        if d.sha256(blob).hexdigest()!=d.digest(ROOT/path):raise RuntimeError('Source or design differs from HEAD: '+path)
    return protocol


def amplitude(frame,truth,snr):
    stamp=d.motion.native_stamp(frame,np.asarray(truth))
    matrix=d.motion.stamp_model(stamp,np.asarray(truth))/stamp['error'][:,None]
    return float(snr*np.sqrt(np.linalg.pinv(matrix.T@matrix)[0,0]))


def prepare_case(before,after,catalog,xy,anchor,truth,snr):
    planted=d.study.injected_frames(before,after,anchor,truth,snr,'nearest')
    signals=[[{**a,'data':a['data']-o['data']} for a,o in zip(added,original)] for added,original in zip(planted,[before,after])]
    epochs=[];maximum_mean_error=0.;maximum_variance_error=0.
    for e,frames in enumerate(signals):
        position=np.asarray(anchor)+np.asarray(truth)*e
        originals=[before,after][e]
        samples=candidate.prepare(frames,catalog,xy,anchor)
        amps=[amplitude(f,position,snr) for f in originals]
        for sample,original,amp in zip(samples,originals,amps):
            ix=sample['x'].astype(int);iy=sample['y'].astype(int)
            expected=d.study.prior.source_image(original,position,amp,'nearest')[iy,ix]
            maximum_mean_error=max(maximum_mean_error,float(np.max(np.abs(sample['data']-expected))))
            maximum_variance_error=max(maximum_variance_error,float(np.max(np.abs(sample['error']**2-original['variance'][iy,ix]))))
            if not np.allclose(sample['data'],expected,rtol=1e-8,atol=1e-9):raise RuntimeError('Frozen source mean replay mismatch')
            if not np.allclose(sample['error']**2,original['variance'][iy,ix],rtol=1e-12,atol=1e-12):raise RuntimeError('Variance replay mismatch')
        try:geometry=probe.geometry(samples,position,amps);failure=None
        except (ValueError,np.linalg.LinAlgError) as exc:geometry=None;failure=type(exc).__name__+': '+str(exc)
        epochs.append({'frames':frames,'samples':samples,'truth_position':position,'amplitudes':amps,'geometry':geometry,'failure':failure})
    return epochs,{'max_abs_old_truth_mean_difference_native':maximum_mean_error,
                   'max_abs_variance_difference_native2':maximum_variance_error}


def serialize_geometry(epoch):
    geom=epoch['geometry']
    if geom is None:return {'supported':False,'failure':epoch['failure'],'amplitudes':epoch['amplitudes']}
    f=geom['fisher_effective']
    return {'supported':True,'amplitudes':epoch['amplitudes'],'truth_position_sky_px':epoch['truth_position'],
            'fisher_effective':f,'fisher_known':geom['fisher_known'],'expected_jtj_matched':geom['expected_jtj'],
            'expected_score_covariance_matched':geom['expected_score_covariance'],
            'expected_mean_score_q_matched':2*probe.normalized_trace(f,geom['expected_score_covariance']),
            'known_normalized_trace':probe.normalized_trace(f,geom['fisher_known']),
            'expected_jtj_normalized_trace_matched':probe.normalized_trace(f,geom['expected_jtj']),
            'dof':geom['dof'],'observations':[{'obs_id':e['sample']['frame']['record']['obs_id'],
             'native_pixels':len(e['p']),'nuisance_rank':e['sample']['rank'],'target_information':e['I'],
             'true_flux_snr_projected':e['amplitude']*np.sqrt(e['I'])} for e in geom['entries']]}


def evaluate_draw(epochs,rng,calculate=True):
    output={name:[] for name in RULES['truth_conditions']};maximum_noise_replay=0.
    for epoch in epochs:
        draw=[rng.normal(size=f['data'].shape)*np.sqrt(f['variance']) for f in epoch['frames']]
        if not calculate:continue
        old=[];matched=[]
        for f,s,amp,noise in zip(epoch['frames'],epoch['samples'],epoch['amplitudes'],draw):
            ix=s['x'].astype(int);iy=s['y'].astype(int)
            actual=(f['data']+noise)[iy,ix];selected_noise=actual-s['data']
            maximum_noise_replay=max(maximum_noise_replay,float(np.max(np.abs(selected_noise-noise[iy,ix]))))
            if not np.allclose(selected_noise,noise[iy,ix],rtol=1e-8,atol=1e-9):raise RuntimeError('Noise replay mismatch')
            old.append(actual)
            matched.append(amp*d.motion.stamp_model(s,epoch['truth_position'])[:,0]+selected_noise)
        for name,arrays in [('matched_padded_primary',matched),('old_nearest_secondary',old)]:
            if epoch['geometry'] is None:result={'failure':epoch['failure']}
            else:
                try:result=probe.trial(epoch['geometry'],arrays)
                except (ValueError,np.linalg.LinAlgError) as exc:result={'failure':type(exc).__name__+': '+str(exc)}
            output[name].append(result)
    return output,maximum_noise_replay


def save(report):
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    tmp=OUTPUT.with_name(OUTPUT.name+'.tmp');d.save(tmp,report);tmp.replace(OUTPUT)


def run(fields,snrs):
    protocol=verify_design();design_hash=d.digest(DESIGN)
    base=json.loads(BIAS.read_text(encoding='utf-8'))
    if OUTPUT.exists():
        report=json.loads(OUTPUT.read_text(encoding='utf-8'))
        if report['completed']:raise RuntimeError('Completed report cannot be overwritten')
        if report['design_sha256']!=design_hash:raise RuntimeError('Report belongs to different protocol')
        for c in report['cases']:
            if [v['draw'] for v in c['records']]!=list(range(len(c['records']))) or len(c['records'])>64:raise RuntimeError('Noncontiguous draws')
    else:report={'design_sha256':design_hash,'rules':protocol['rules'],'cases':[],'completed':False}
    boot=np.random.default_rng(RULES['bootstrap_seed']).integers(0,64,size=(RULES['bootstrap_draws'],64))
    for ident in fields:
        print('LOAD',ident,flush=True)
        _,_,catalog,xy,before,after,source=d.load_field(ident)
        field=next(f for f in base['fields'] if f['id']==ident)
        for wanted in RULES['cases']:
            if wanted['snr_per_frame'] not in snrs:continue
            old=next(c for c in field['cases'] if c['snr_per_frame']==wanted['snr_per_frame'] and c['truth_delta_px']==wanted['motion'])
            anchor=old['anchor'];truth=np.asarray(wanted['motion']);snr=wanted['snr_per_frame']
            epochs,replay=prepare_case(before,after,catalog,xy,anchor,truth,snr)
            case=next((c for c in report['cases'] if c['field']==ident and c['snr_per_frame']==snr),None)
            if case is None:
                case={'field':ident,'source':source,'snr_per_frame':snr,'anchor_sky_px':anchor,
                      'truth_delta_sky_px':truth,'signal_variance_replay':replay,
                      'geometry':[serialize_geometry(e) for e in epochs],'records':[]}
                report['cases'].append(case);save(report)
            rng=np.random.default_rng(RULES['noise_seed'])
            for draw in range(64):
                result,noise_error=evaluate_draw(epochs,rng,calculate=draw>=len(case['records']))
                if draw<len(case['records']):continue
                case['records'].append({'draw':draw,'conditions':result,'noise_replay_max_abs':noise_error})
                save(report)
                print('DRAW',ident,snr,draw+1,flush=True)
            case['summaries']={}
            for condition in RULES['truth_conditions']:
                result=[]
                for e,epoch in enumerate(epochs):
                    if epoch['geometry'] is None:result.append({'attempts':64,'successful':0,'failures':64,'failure':epoch['failure']})
                    else:result.append(probe.summarize(epoch['geometry'],[r['conditions'][condition][e] for r in case['records']],boot))
                case['summaries'][condition]=result
            save(report)
    report['completed']=len(report['cases'])==len(RULES['fields'])*len(RULES['cases']) and all(len(c['records'])==64 and 'summaries' in c for c in report['cases'])
    save(report);print('COMPLETED',report['completed'],flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--design',action='store_true');group.add_argument('--run',action='store_true')
    parser.add_argument('--fields',nargs='+',choices=RULES['fields'],default=RULES['fields'])
    parser.add_argument('--snrs',nargs='+',choices=[2.,4.],type=float,default=[2.,4.])
    args=parser.parse_args()
    if args.design:create_design()
    else:run(args.fields,args.snrs)


if __name__=='__main__':main()
