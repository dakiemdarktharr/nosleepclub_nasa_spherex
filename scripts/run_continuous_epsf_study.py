"""Locked, resumable paired development study; never new validation."""
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np
from . import diagnose_bias as d
from . import continuous_epsf_model as candidate

ROOT = d.ROOT
DESIGN = ROOT/'web/data/continuous-epsf/design.json'
OUTPUT = ROOT/'data/raw/benchmark/continuous-epsf-development.json'
BASELINE = ROOT/'data/raw/benchmark/bias-gaussian64-development.json'
RULES = {'version':'0.10.0-continuous-epsf-development.1', 'fields':d.RULES['fields'],
    'cases':d.RULES['cases'], 'patch_index':1, 'draws_per_case':64, 'seed':20261030,
    'pad_oversampled_pixels_per_edge':16, 'truth_psf':'nearest frozen source_image',
    'backgrounds':['original exposure pixels', 'signal only plus independent Gaussian native-pixel noise'],
    'candidate':'plane_fixed target padding, fixed original neighbour templates',
    'ellipse68_threshold':2.27886856637673, 'ellipse95_threshold':5.99146454710798,
    'covariance':'candidate GN and observed profile Hessian with original registration covariance; no conditional calibration',
    'selection':'all attempts and common numeric/common accepted subsets, separately by field and case',
    'qualification':'opened fields and matched old truth only; diagnostic development, not independent validation or physical PSF proof'}


def inputs():
    paths = ['scripts/continuous_epsf_model.py', 'scripts/run_continuous_epsf_study.py',
             'scripts/diagnose_bias.py', 'scripts/profile_uncertainty.py',
             'tests/test_continuous_epsf.py', 'docs/CONTINUOUS_EPSF_PROTOCOL.md', 'requirements.txt']
    paths += ['scripts/'+name for name in d.study.sources()]
    products = ['web/data/ablation/design.json'] + ['web/data/ablation/validation-'+v+'.json' for v in RULES['fields']]
    return {p:d.digest(ROOT/p) for p in paths}, {p:d.digest(ROOT/p) for p in products}


def create_design():
    if DESIGN.exists(): raise RuntimeError('Design exists; refusing overwrite')
    previous=json.loads(BASELINE.read_text(encoding='utf-8'))
    if not previous.get('completed') or previous['noise_draws'] != RULES['draws_per_case']:
        raise RuntimeError('Baseline cache is incomplete')
    for ident in RULES['fields']:
        field=next(v for v in previous['fields'] if v['id']==ident)
        for wanted in RULES['cases']:
            case=next(v for v in field['cases'] if v['snr_per_frame']==wanted['snr_per_frame'] and v['truth_delta_px']==wanted['motion'])
            if len(case['independent_gaussian_controls']['records']) != RULES['draws_per_case']:
                raise RuntimeError('Baseline draw count mismatch')
    sources, products=inputs()
    document={'rules':RULES,'source_hashes':sources,'opened_product_hashes':products,
                    'paired_baseline_path':str(BASELINE.relative_to(ROOT)).replace('\\','/'),
                    'paired_baseline_sha256':d.digest(BASELINE), 'status':'development protocol, not calibration or validation'}
    DESIGN.parent.mkdir(parents=True,exist_ok=True)
    DESIGN.write_bytes((json.dumps(d.jsonable(document),ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8'))
    print('DESIGN',DESIGN,'sha256',d.digest(DESIGN),flush=True)


def verify_design():
    protocol=json.loads(DESIGN.read_text(encoding='utf-8'))
    sources,products=inputs()
    if protocol['rules'] != RULES or protocol['source_hashes'] != sources or protocol['opened_product_hashes'] != products or protocol['paired_baseline_sha256'] != d.digest(BASELINE):
        raise RuntimeError('Protocol or input hash mismatch')
    for path in [*sources,*products,str(DESIGN.relative_to(ROOT)).replace('\\','/')]:
        try: committed=subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT,stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as exc: raise RuntimeError('Required source or design not committed: '+path) from exc
        if d.sha256(committed).hexdigest() != d.digest(ROOT/path): raise RuntimeError('Uncommitted source or design changes: '+path)
    return protocol


def public(fit):
    return {**d.study.public(fit),'profile':fit['profile']}


def measure(fs, catalog, xy, anchor, truth):
    try:
        refs=[]
        for frames in fs:
            try:refs.append(d.motion.fit_position(frames,np.asarray(anchor),multistart=True))
            except (ValueError,np.linalg.LinAlgError):refs.append(None)
        fits=[candidate.fit(frames,catalog,xy,anchor,ref) for frames,ref in zip(fs,refs)]
        transform=d.study.gaia.TRANSFORM
        error=transform@(fits[1]['position']-fits[0]['position']-truth)
        registration=sum(d.study.bench.registration_covariance(frames) for frames in fs)
        cov=transform@(sum(f['covariance'] for f in fits)+registration)@transform.T
        valid=all(candidate.numeric_valid(f) for f in fits)
        row={'numeric_valid':valid,'accepted':bool(valid and all(f['quality']['accepted'] for f in fits)),
             'quality_reasons':sorted(set(sum([f['quality']['reasons'] for f in fits],[]))),
             'before':public(fits[0]),'after':public(fits[1]),'error_east_north_arcsec':error.tolist(),
             'error_arcsec':float(np.linalg.norm(error)),'gauss_newton_covariance_arcsec2':cov.tolist()}
        if valid and np.isfinite(cov).all() and np.linalg.eigvalsh(cov).min()>0:
            row['gauss_newton_q']=float(error@np.linalg.solve(cov,error))
        if valid and all(f['profile']['supported'] for f in fits):
            cov=transform@(sum(np.asarray(f['profile']['covariance_px2']) for f in fits)+registration)@transform.T
            if np.isfinite(cov).all() and np.linalg.eigvalsh(cov).min()>0:
                row['profile_covariance_arcsec2']=cov.tolist();row['profile_q']=float(error@np.linalg.solve(cov,error))
        return row
    except (ValueError,np.linalg.LinAlgError) as exc:
        return {'numeric_valid':False,'accepted':False,'failure':type(exc).__name__,'detail':str(exc)}


def summarize(rows):
    summary={'attempts':len(rows)}
    for label,selector in [('baseline_numeric',lambda b,c:b.get('numeric_valid')),
        ('baseline_accepted',lambda b,c:b.get('accepted')),
        ('candidate_numeric',lambda b,c:c.get('numeric_valid')),
        ('candidate_accepted',lambda b,c:c.get('accepted')),
        ('common_numeric',lambda b,c:b.get('numeric_valid') and c.get('numeric_valid')),
        ('common_accepted',lambda b,c:b.get('accepted') and c.get('accepted'))]:
        paired=[(r['baseline'],r['candidate']) for r in rows if selector(r['baseline'],r['candidate'])]
        value={'count':len(paired)}
        for name, qname in [('baseline_gn','mahalanobis2_raw'),('candidate_gn','gauss_newton_q'),('candidate_profile','profile_q')]:
            idx=0 if name=='baseline_gn' else 1
            q=[p[idx][qname] for p in paired if p[idx].get('numeric_valid') and p[idx].get(qname) is not None]
            value[name]={'available':len(q),'within68':sum(x<=RULES['ellipse68_threshold'] for x in q),
                         'within95':sum(x<=RULES['ellipse95_threshold'] for x in q)}
        for name,idx in [('baseline',0),('candidate',1)]:
            errors=[p[idx]['error_arcsec'] for p in paired if p[idx].get('numeric_valid') and p[idx].get('error_arcsec') is not None]
            value[name+'_error']={'available':len(errors),'rms_arcsec':float(np.sqrt(np.mean(np.square(errors)))) if errors else None,
                                  'p90_arcsec':float(np.percentile(errors,90)) if errors else None}
        summary[label]=value
    return summary


def save_report(report):
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary=OUTPUT.with_name(OUTPUT.name+'.tmp')
    d.save(temporary,report)
    temporary.replace(OUTPUT)


def run(fields,snrs):
    protocol=verify_design(); baseline=json.loads(BASELINE.read_text(encoding='utf-8'))
    identity=d.digest(DESIGN)
    if OUTPUT.exists():
        report=json.loads(OUTPUT.read_text(encoding='utf-8'))
        if report.get('completed'):raise RuntimeError('Completed output already exists; no overwrite')
        if report['design_sha256'] != identity:raise RuntimeError('Existing output belongs to different design')
        for case in report['cases']:
            records=case['records']
            if len(records)>RULES['draws_per_case'] or [r['draw'] for r in records]!=list(range(len(records))):
                raise RuntimeError('Existing output has noncontiguous draw records')
    else:report={'design_sha256':identity,'rules':protocol['rules'],'cases':[],'completed':False}
    for ident in fields:
        print('LOAD',ident,flush=True)
        _,opened,catalog,xy,before,after,source=d.load_field(ident)
        oldfield=next(v for v in baseline['fields'] if v['id']==ident)
        for wanted in RULES['cases']:
            if wanted['snr_per_frame'] not in snrs:continue
            oldcase=next(v for v in oldfield['cases'] if v['snr_per_frame']==wanted['snr_per_frame'] and v['truth_delta_px']==wanted['motion'])
            case=next((v for v in report['cases'] if v['field']==ident and v['snr_per_frame']==wanted['snr_per_frame']),None)
            if case is None:
                case={'field':ident,'source':source,'snr_per_frame':wanted['snr_per_frame'],
                      'truth_delta_sky_px':wanted['motion'],'anchor_sky_px':oldcase['anchor'], 'records':[]}
                report['cases'].append(case)
            anchor=oldcase['anchor'];truth=np.asarray(wanted['motion'])
            planted=d.study.injected_frames(before,after,anchor,truth,wanted['snr_per_frame'],'nearest')
            if 'original_background' not in case:
                case['original_background']={'baseline':oldcase['frozen_result'],
                    'candidate':measure(planted,catalog,xy,anchor,truth)}
                save_report(report)
            signals=[[{**a,'data':a['data']-o['data']} for a,o in zip(added,original)] for added,original in zip(planted,[before,after])]
            rng=np.random.default_rng(RULES['seed'])
            for draw in range(RULES['draws_per_case']):
                fs=[[{**f,'data':f['data']+rng.normal(size=f['data'].shape)*np.sqrt(f['variance'])} for f in frames] for frames in signals]
                if draw == 0 and 'baseline_replay' not in case:
                    replay=d.pair(fs,catalog,xy,anchor,truth)['plane_fixed']
                    saved=oldcase['independent_gaussian_controls']['records'][0]
                    if replay['numeric_valid'] != saved['numeric_valid'] or replay['accepted'] != saved['accepted']:
                        raise RuntimeError('Baseline draw 0 status mismatch')
                    difference=None
                    if saved['numeric_valid']:
                        difference=float(np.max(np.abs(np.asarray(replay['error_east_north_arcsec'])-saved['error_east_north_arcsec'])))
                        if difference>1e-5:raise RuntimeError('Baseline draw 0 replay mismatch')
                    case['baseline_replay']={'draw':0,'max_vector_difference_arcsec':difference,'status_matches':True}
                    save_report(report)
                if draw < len(case['records']):continue
                row={'draw':draw,'baseline':oldcase['independent_gaussian_controls']['records'][draw],
                     'candidate':measure(fs,catalog,xy,anchor,truth)}
                case['records'].append(row);case['summary']=summarize(case['records']);save_report(report)
                print('DRAW',ident,wanted['snr_per_frame'],draw+1,flush=True)
    report['completed']=len(report['cases'])==len(RULES['fields'])*len(RULES['cases']) and all(len(c['records'])==RULES['draws_per_case'] and 'original_background' in c for c in report['cases'])
    save_report(report)
    print('COMPLETED',report['completed'],flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--design',action='store_true');group.add_argument('--run',action='store_true')
    parser.add_argument('--fields',nargs='+',choices=RULES['fields'],default=RULES['fields'])
    parser.add_argument('--snrs',nargs='+',type=float,choices=[2.,4.],default=[2.,4.])
    args=parser.parse_args()
    if args.design:create_design()
    else:run(args.fields,args.snrs)


if __name__=='__main__':main()
