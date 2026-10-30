"""Separate development, empirical calibration and prospectively locked validation.

Run --design, --develop, commit; then --calibrate, --seal, commit; then --validate.
All attempted fits, including failures and unavailable registration, are retained.
"""
import argparse
from datetime import datetime,timezone
import json
import subprocess
import numpy as np
from scipy.ndimage import gaussian_filter,map_coordinates,spline_filter
from . import quality_study as old
from . import covariance_model as model
from .prepare_covariance_data import VALIDATION_FIELDS

bench=old.bench;motion=old.motion;gaia=old.gaia;ROOT=old.ROOT;OUT=ROOT/'web/data/covariance'
RULES={'version':'0.8.0','seed':20261030,'bootstrap_draws':2000,
    'development_fields':['barnard','rw-aur'],
    'calibration_fields':['q030m10','q180p20','q300m30'],
    'validation_fields':[v[0] for v in VALIDATION_FIELDS],
    'calibration_positions_px':[[x,y] for y in [5.5,31.5,57.5] for x in [5.5,31.5,57.5] if [x,y]!=[31.5,31.5]],
    'validation_positions_px':[[5.5,5.5],[57.5,5.5],[5.5,57.5],[57.5,57.5]],
    'snr_per_frame':[2.,4.],'motions_px':[[0.,0.],[.6,.05]],
    'calibration_truth_psfs':['nearest','isotropic_015px'],
    'validation_truth_psfs':['nearest','elliptical_006_022px'],
    'calibration_blur_native_px':[.15,.15],'validation_blur_native_px':[.06,.22],
    'common_registration':'0.7 IR-centroid training + median/MAD clip for BOTH point models and injected pixels',
    'promotion':{'minimum_common_per_group':4,'minimum_real_common':3,'coverage68_min':.55,'coverage68_max':.85,
        'minimum_accepted_validation':24,'minimum_accepted_validation_blocks':6,'maximum_median_area_inflation':16.,
        'point_gate':'each field/SNR/PSF: paired numeric RMS and P90 no worse; no fewer numeric or accepted; real paired RMS no worse'},
    'limits':['local known-position fitting, not blind detection','no added source shot noise',
        'correlated exposure/patch trials; bootstrap uncertainty exploratory with only three fields',
        'calibration fields were opened in 0.7; only validation fields are newly held out',
        'shared epoch width mixture; fixed neighbour shapes/positions; width-bound Hessian approximate',
        'assumed PSF perturbations, not independent physical ePSF measurements',
        'broad spectra only; no automatic change of WISE 0855 measurement']}
SOURCES=['covariance_model.py','covariance_study.py','prepare_covariance_data.py',*old.SOURCE_FILES]


def sources():return {name:bench.digest(ROOT/'scripts'/name) for name in SOURCES}
def now():return datetime.now(timezone.utc).isoformat()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def head():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def check_design():
    p=OUT/'design.json';d=read(p)
    if d['source_hashes']!=sources() or d['rules']!=RULES or d['model_rules']!=model.RULES:raise RuntimeError('Code/rules changed after design lock')
    for role,items in d['fields'].items():
        for item in items:
            old.validate(item)
            cache=item.get('registration_cache')
            if cache and bench.digest(ROOT/cache['path'])!=cache['sha256']:raise RuntimeError('Registration cache changed')
    return d,bench.digest(p)


def make_design():
    path=OUT/'design.json'
    if path.exists():raise RuntimeError('Design already exists; do not overwrite')
    quality=read(ROOT/'web/data/quality/protocol.json');development=read(ROOT/'web/data/quality/development-protocol.json')
    fields={'development':[],'calibration':[],'validation':[]}
    for role,ids,p in [('development',RULES['development_fields'],development),('calibration',RULES['calibration_fields'],quality)]:
        for ident in ids:
            item=next(v for v in p['fields'] if v['field']['id']==ident).copy()
            cache=ROOT/'web/data/quality'/('development-' if role=='development' else 'evaluation-')
            cache=cache.parent/(cache.name+ident+'.json')
            item['registration_cache']={'path':cache.relative_to(ROOT).as_posix(),'sha256':bench.digest(cache)}
            fields[role].append(item)
    previous_out=old.OUT;old.OUT=OUT
    try:fields['validation']=[old.prepare_item(v[0],True) for v in VALIDATION_FIELDS]
    finally:old.OUT=previous_out
    # No exposure can contribute to two roles. Shared ePSF library is expected.
    sets={role:{p[e] for v in items for p in v['pairs'] for e in ['before','after']} for role,items in fields.items()}
    for a,b in [('development','calibration'),('calibration','validation'),('development','validation')]:
        if sets[a]&sets[b]:raise RuntimeError('Exposure leakage across roles')
    for items in fields.values():
        for item in items:
            old.validate(item)
            train={r['catalog']['source_id'] for r in item['references'] if r['split']=='training'}
            held={r['catalog']['source_id'] for r in item['references'] if r['split']=='heldout'}
            if train&held:raise RuntimeError('Reference leakage')
    bench.save(path,{'created_at_utc':now(),'rules':RULES,'model_rules':model.RULES,'gate_rules':model.previous.RULES,
        'source_hashes':sources(),'fields':fields,'selected_exposure_ids':{k:sorted(v) for k,v in sets.items()},
        'selection':'coordinates and image/catalog geometry only, no validation centroid fitting',
        'calibration_recipe':'accepted candidate synthetic displacement errors only; PSD noncentral error floor + nonshrinking weighted empirical 68% scale',
        'coverage_gate':'pooled accepted validation 68% coverage 0.55..0.85, block bootstrap CI includes 0.68, >=24 fits and >=6 spatial blocks; median ellipse area inflation <=16',
        'disjointness':'no shared exposure IDs or fields between roles; shared QR2 calibrations are not independent'} )
    print('DESIGN',bench.digest(path),flush=True)


def register(item,frames,catalog,xy):
    if len(item['pairs'])<2:raise RuntimeError('Fewer than two compatible spectral pairs')
    cache=item.get('registration_cache')
    if cache:
        source=read(ROOT/cache['path']);regs=source.get('ir_robust_registrations')
        if not regs:raise RuntimeError('Cached 0.7 robust registration unavailable')
        training={'cache':cache,'eligible_count':sum(t['eligible'] for t in source['training']['ir_robust'])}
    else:
        refs=[r for r in item['references'] if r['split']=='training']
        measured=old.training_measurements(frames,refs,catalog,xy)
        eligible=[r for r in measured if r['eligible']]
        _,regs=old.calibrated(frames,eligible,True)
        training={'measurements':measured,'eligible_count':len(eligible)}
    index={r['obs_id']:r for r in regs};output=[]
    for f in frames:
        r=index[f['record']['obs_id']]
        output.append({**f,'offset':np.asarray(r['offset_px']),'offset_cov':np.asarray(r['covariance_px2'])})
    return output,regs,training


def public(fit):
    v={**motion.public_fit(fit),'quality':fit['quality']}
    if 'width_mixture' in fit:v.update(width_mixture=fit['width_mixture'],width_at_boundary=fit['width_at_boundary'])
    return v


def pair(before,after,catalog,xy,anchors,source=None,truth=None):
    target=source['source_id'] if source else None;fits={k:[] for k in ['previous','candidate']}
    for fs,a in zip([before,after],anchors):
        prev=model.previous.fit(fs,catalog,xy,a,target_id=target)
        fits['previous'].append(prev);fits['candidate'].append(model.fit(fs,catalog,xy,a,target_id=target,old=prev))
    output={}
    for name,(a,b) in fits.items():
        if source:
            expected=gaia.gaia_xy(source,b['effective_mjd'])-gaia.gaia_xy(source,a['effective_mjd'])
            jac=gaia.gaia_jacobian(source,b['effective_mjd'])-gaia.gaia_jacobian(source,a['effective_mjd'])
            catalog_cov=jac@gaia.gaia_covariance(source)@jac.T
        else:expected=np.asarray(truth);catalog_cov=np.zeros((2,2))
        delta=b['position']-a['position'];error=gaia.TRANSFORM@(delta-expected)
        c=a['covariance']+b['covariance']+bench.registration_covariance(before)+bench.registration_covariance(after)+catalog_cov
        sensitivity=np.zeros((2,2))
        if name=='candidate':
            old_delta=fits['previous'][1]['position']-fits['previous'][0]['position'];diff=delta-old_delta
            sensitivity=model.RULES['model_sensitivity_multiplier']*np.outer(diff,diff);c+=sensitivity
        c=gaia.TRANSFORM@c@gaia.TRANSFORM.T
        numeric=all(bench.valid_fit(f) for f in [a,b])
        output[name]={'numeric_valid':bool(numeric),'accepted':bool(numeric and all(f['quality']['accepted'] for f in [a,b])),
            'quality_reasons':sorted({r for f in [a,b] for r in f['quality']['reasons']}),
            'before':public(a),'after':public(b),'measured_east_north_arcsec':(gaia.TRANSFORM@delta).tolist(),
            'expected_east_north_arcsec':(gaia.TRANSFORM@expected).tolist(),'error_east_north_arcsec':error.tolist(),
            'error_arcsec':float(np.linalg.norm(error)),'covariance_arcsec2':c.tolist(),
            'model_sensitivity_arcsec2':(gaia.TRANSFORM@sensitivity@gaia.TRANSFORM.T).tolist(),
            'mahalanobis2_raw':float(error@np.linalg.pinv(c)@error)}
    return output


def failure(reason):return {k:{'numeric_valid':False,'accepted':False,'quality_reasons':[reason]} for k in ['previous','candidate']}
def safe_pair(*args,**kwargs):
    try:return pair(*args,**kwargs)
    except (ValueError,np.linalg.LinAlgError) as exc:return {k:{**v,'reason':str(exc)} for k,v in failure('fit_exception').items()}


def source_image(frame,position,amplitude,truth_psf):
    px,py=frame['wcs'].world_to_pixel_values(*motion.WCS.pixel_to_world_values(*(np.array(position)+frame['offset'])))
    psf,zone=motion.epsf_for(frame,float(px),float(py));over=frame['epsf_oversampling']
    if truth_psf!='nearest':
        raw=np.asarray(frame['epsf_table']['EPSF'][zone],float)
        sig=RULES['calibration_blur_native_px'] if truth_psf=='isotropic_015px' else RULES['validation_blur_native_px']
        wide=gaussian_filter(raw,np.asarray(sig)*over);psf=spline_filter(wide*over**2/wide.sum(),order=3)
    yy,xx=np.indices(frame['data'].shape,dtype=float);center=(np.array(psf.shape)-1)/2
    return amplitude*map_coordinates(psf,[(yy-py)*over+center[0],(xx-px)*over+center[1]],order=3,mode='constant',cval=0,prefilter=False)


def run_field(item,phase,design_hash,calibrator=None):
    old.validate(item);manifest,frames,catalog,screening=old.load(item)
    if [c['id'] for c in catalog]!=item['catalog_ids']:raise RuntimeError('Catalog changed')
    index={f['record']['obs_id']:f for f in frames};ids={p[e] for p in item['pairs'] for e in ['before','after']};frames=[index[o] for o in sorted(ids)]
    result={'field':item['field'],'phase':phase,'design_sha256':design_hash,'catalog_screening':screening,'real_controls':[],'injections':[],'unavailable':None}
    xy=model.previous.positions(catalog,frames)
    try:
        registered,regs,training=register(item,frames,catalog,xy)
        result.update(registrations=regs,training=training)
    except RuntimeError as exc:registered=None;result['unavailable']=str(exc)
    if registered:
        index={f['record']['obs_id']:f for f in registered}
        before,after=[[index[p[e]] for p in item['pairs']] for e in ['before','after']]
    for r in item['references']:
        if r['split']!='heldout':continue
        s=r['catalog'];v={'phase':phase,'field_id':item['field']['id'],'source_id':s['source_id']}
        if registered:
            anchors=[gaia.gaia_xy(s,float(np.mean([f['mjd'] for f in fs]))) for fs in [before,after]]
            v['models']=safe_pair(before,after,catalog,xy,anchors,source=s)
        else:v['models']=failure('registration_unavailable')
        result['real_controls'].append(v);print(phase,item['field']['id'],'REAL',s['source_id'],flush=True)
    if phase!='development':
        for patch,anchor in enumerate(RULES[phase+'_positions_px']):
            for truth_psf in RULES[phase+'_truth_psfs']:
                for snr in RULES['snr_per_frame']:
                    for delta in RULES['motions_px']:
                        v={'phase':phase,'field_id':item['field']['id'],'patch_index':patch,'anchor':anchor,'truth_psf':truth_psf,'snr_per_frame':snr,'truth_delta_px':delta}
                        if not registered:v['models']=failure('registration_unavailable')
                        else:
                            try:
                                injected=[]
                                for fs,shift in [(before,np.zeros(2)),(after,np.array(delta))]:
                                    copies=[]
                                    for f in fs:
                                        p=np.array(anchor)+shift;s=motion.native_stamp(f,p);d=motion.stamp_model(s,p)/s['error'][:,None]
                                        amplitude=snr*np.sqrt(np.linalg.pinv(d.T@d)[0,0])
                                        copies.append({**f,'data':f['data']+source_image(f,p,amplitude,truth_psf)})
                                    injected.append(copies)
                                v['models']=safe_pair(*injected,catalog,xy,[anchor,anchor],truth=delta)
                            except (ValueError,np.linalg.LinAlgError) as exc:v['models']={k:{**r,'reason':str(exc)} for k,r in failure('input_exception').items()}
                        result['injections'].append(v)
            print(phase,item['field']['id'],'PATCH',patch,'done',flush=True)
    if calibrator:
        for v in result['injections']+result['real_controls']:apply_record(v,calibrator)
    result['injection_summary']=summarize(result['injections']);result['real_summary']=summarize(result['real_controls'])
    return result


def apply_record(record,calibrator):
    v=record['models']['candidate']
    if 'covariance_arcsec2' not in v:return
    raw=np.asarray(v['covariance_arcsec2']);c=model.apply_covariance(raw,calibrator);e=np.asarray(v['error_east_north_arcsec'])
    v.update(calibrated_covariance_arcsec2=c.tolist(),mahalanobis2_calibrated=float(e@np.linalg.solve(c,e)),
        ellipse_area_inflation=float(np.sqrt(max(0.,np.linalg.det(c))/max(np.linalg.det(raw),1e-30))))


def stats(records,kind,selection):
    rows=[r['models'][kind] for r in records if r['models'][kind][selection]]
    errors=np.asarray([v['error_east_north_arcsec'] for v in rows]);reasons={}
    for r in records:
        for reason in r['models'][kind]['quality_reasons']:reasons[reason]=reasons.get(reason,0)+1
    v={'attempted':len(records),'valid':len(rows),'rejected':len(records)-len(rows),'reasons':reasons,
        'rms_arcsec':float(np.sqrt(np.mean(np.sum(errors**2,axis=1)))) if rows else None,
        'p90_arcsec':float(np.percentile(np.linalg.norm(errors,axis=1),90)) if rows else None,
        'bias_east_north_arcsec':errors.mean(axis=0).tolist() if rows else None,
        'raw68_count':sum(r['mahalanobis2_raw']<=model.RULES['ellipse68_threshold'] for r in rows),
        'raw95_count':sum(r['mahalanobis2_raw']<=model.RULES['ellipse95_threshold'] for r in rows)}
    if rows and all('mahalanobis2_calibrated' in r for r in rows):
        v.update(calibrated68_count=sum(r['mahalanobis2_calibrated']<=model.RULES['ellipse68_threshold'] for r in rows),
            calibrated95_count=sum(r['mahalanobis2_calibrated']<=model.RULES['ellipse95_threshold'] for r in rows),
            median_area_inflation=float(np.median([r['ellipse_area_inflation'] for r in rows])))
    return v


def paired(records,selection):
    rows=[r for r in records if all(v[selection] for v in r['models'].values())]
    v={'common':len(rows),'attempted':len(records)}
    for kind in ['previous','candidate']:
        values=[r['models'][kind]['error_arcsec'] for r in rows]
        v[kind+'_rms_arcsec']=float(np.sqrt(np.mean(np.square(values)))) if values else None
        v[kind+'_p90_arcsec']=float(np.percentile(values,90)) if values else None
    return v


def summarize(records):
    return {'models':{k:{s:stats(records,k,s) for s in ['numeric_valid','accepted']} for k in ['previous','candidate']},
        'paired_numeric':paired(records,'numeric_valid'),'paired_accepted':paired(records,'accepted')}


def coverage_gate(records):
    rows=[r for r in records if r['models']['candidate']['accepted']];blocks=sorted({(r['field_id'],r['patch_index']) for r in rows})
    fields=sorted({r['field_id'] for r in rows});rng=np.random.default_rng(RULES['seed']);values=[]
    def covered(rs):return np.mean([r['models']['candidate']['mahalanobis2_calibrated']<=model.RULES['ellipse68_threshold'] for r in rs])
    if rows:
        for _ in range(RULES['bootstrap_draws']):
            sample=[]
            for f in rng.choice(fields,len(fields),replace=True):
                patches=[b[1] for b in blocks if b[0]==f]
                for p in rng.choice(patches,len(patches),replace=True):sample.extend(r for r in rows if (r['field_id'],r['patch_index'])==(f,p))
            values.append(float(covered(sample)))
    ci=np.percentile(values,[2.5,97.5]).tolist() if values else None;fraction=float(covered(rows)) if rows else None
    area=float(np.median([r['models']['candidate']['ellipse_area_inflation'] for r in rows])) if rows else None
    p=RULES['promotion'];passed=bool(rows and len(rows)>=p['minimum_accepted_validation'] and len(blocks)>=p['minimum_accepted_validation_blocks'] and len(fields)==3 and
        p['coverage68_min']<=fraction<=p['coverage68_max'] and ci[0]<=.68<=ci[1] and area<=p['maximum_median_area_inflation'])
    return {'passed':passed,'accepted':len(rows),'attempted':len(records),'spatial_blocks':len(blocks),'fields':len(fields),
        'fraction68':fraction,'hierarchical_block_bootstrap95':ci,'median_area_inflation':area,
        'qualification':'exploratory hierarchical field/patch bootstrap, only three fields; not independent binomial trials'}


def point_gate(result):
    groups=[];p=RULES['promotion']
    for truth in RULES['validation_truth_psfs']:
        for snr in RULES['snr_per_frame']:
            rows=[r for r in result['injections'] if r['truth_psf']==truth and r['snr_per_frame']==snr];s=summarize(rows);pair=s['paired_numeric']
            a,b=[s['models'][k] for k in ['previous','candidate']]
            passed=bool(pair['common']>=p['minimum_common_per_group'] and pair['candidate_rms_arcsec']<=pair['previous_rms_arcsec'] and
                pair['candidate_p90_arcsec']<=pair['previous_p90_arcsec'] and b['numeric_valid']['valid']>=a['numeric_valid']['valid'] and b['accepted']['valid']>=a['accepted']['valid'])
            groups.append({'truth_psf':truth,'snr_per_frame':snr,'passed':passed,**s})
    s=result['real_summary'];v=s['paired_numeric'];a,b=[s['models'][k] for k in ['previous','candidate']]
    real_passed=bool(v['common']>=p['minimum_real_common'] and v['candidate_rms_arcsec']<=v['previous_rms_arcsec'] and
        b['numeric_valid']['valid']>=a['numeric_valid']['valid'] and b['accepted']['valid']>=a['accepted']['valid'])
    return {'passed':real_passed and all(v['passed'] for v in groups) and not result['unavailable'],'real_passed':real_passed,'groups':groups}


def run_phase(phase):
    design,design_hash=check_design();calibrator=None;seal=None
    if phase=='validation':
        seal=read(OUT/'validation-protocol.json');calibrator=read(OUT/'calibrator.json')
        if seal['design_sha256']!=design_hash or seal['calibrator_sha256']!=bench.digest(OUT/'calibrator.json'):raise RuntimeError('Sealed inputs changed')
        committed=subprocess.check_output(['git','show','HEAD:web/data/covariance/validation-protocol.json'],cwd=ROOT)
        if committed!=(OUT/'validation-protocol.json').read_bytes():raise RuntimeError('Commit validation seal before opening fields')
    else:
        # Development can run before design commit. Calibration cannot.
        if phase=='calibration':
            committed=subprocess.check_output(['git','show','HEAD:web/data/covariance/design.json'],cwd=ROOT)
            if committed!=(OUT/'design.json').read_bytes():raise RuntimeError('Commit design before calibration')
    results=[]
    for item in design['fields'][phase]:
        path=OUT/(phase+'-'+item['field']['id']+'.json')
        if path.exists():raise RuntimeError('Refusing to overwrite opened field result: '+str(path))
        result=run_field(item,phase,design_hash,calibrator)
        if phase=='validation':result.update(validation_protocol_sha256=bench.digest(OUT/'validation-protocol.json'),lock_commit=head(),point_gate=point_gate(result))
        bench.save(path,result);results.append(result)
    records=[r for v in results for r in v['injections']]
    if phase=='calibration':
        calibrator=model.calibrate(records);calibrator.update(design_sha256=design_hash,created_at_utc=now(),design_lock_commit=head(),
            source_results={v['field']['id']:bench.digest(OUT/(phase+'-'+v['field']['id']+'.json')) for v in results})
        bench.save(OUT/'calibrator.json',calibrator)
        for v in results:
            for r in v['injections']+v['real_controls']:apply_record(r,calibrator)
            v['injection_summary']=summarize(v['injections']);v['real_summary']=summarize(v['real_controls'])
        # Raw calibration products stay immutable; summary applies the calibrator.
    summary={'phase':phase,'version':RULES['version'],'design_sha256':design_hash,'current_measurement_changed':False,
        'injection_summary':summarize(records),'real_summary':summarize([r for v in results for r in v['real_controls']]),
        'fields':[{k:v for k,v in r.items() if k not in ['injections','real_controls','training','registrations']} for r in results]}
    if phase=='validation':
        summary.update(coverage_gate=coverage_gate(records),point_passed=all(r['point_gate']['passed'] for r in results),
            validation_protocol_sha256=bench.digest(OUT/'validation-protocol.json'),lock_commit=head())
        summary['passed']=summary['coverage_gate']['passed'] and summary['point_passed']
    bench.save(OUT/(phase+'-summary.json'),summary);print('SUMMARY',phase,json.dumps(summary['injection_summary']),flush=True)


def seal():
    design,digest=check_design();path=OUT/'validation-protocol.json'
    if path.exists():raise RuntimeError('Validation protocol already exists')
    cal=read(OUT/'calibrator.json')
    if cal['design_sha256']!=digest:raise RuntimeError('Calibration design mismatch')
    for ident,h in cal['source_results'].items():
        if bench.digest(OUT/('calibration-'+ident+'.json'))!=h:raise RuntimeError('Calibration source changed')
    bench.save(path,{'sealed_at_utc':now(),'design_sha256':digest,'calibrator_sha256':bench.digest(OUT/'calibrator.json'),
        'calibration_summary_sha256':bench.digest(OUT/'calibration-summary.json'),'source_hashes':sources(),
        'fields':RULES['validation_fields'],'parameters':cal,'rules':RULES,'requirement':'commit this protocol before --validate'})
    print('SEAL',bench.digest(path),flush=True)


def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    for v in ['design','develop','calibrate','seal','validate']:group.add_argument('--'+v,action='store_true')
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    if args.design:make_design()
    elif args.develop:run_phase('development')
    elif args.calibrate:run_phase('calibration')
    elif args.seal:seal()
    else:run_phase('validation')


if __name__=='__main__':main()
