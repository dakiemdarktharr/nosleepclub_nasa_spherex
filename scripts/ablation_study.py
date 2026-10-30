"""0.9: four fixed point models, then separate grouped covariance calibration.

Previously opened fields are explicitly development data. Only new geometric
fields are external validation, opened after the final code/parameter seal.
"""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import numpy as np
from . import covariance_study as prior
from . import ablation_model as model
from . import conditional_covariance as cc
from .prepare_ablation_data import VALIDATION_FIELDS

ROOT=prior.ROOT;OUT=ROOT/'web/data/ablation';old=prior.old;bench=prior.bench;motion=prior.motion;gaia=prior.gaia
KINDS=list(model.MODELS)
RULES={'version':'0.9.0','seed':20261030,'bootstrap_draws':2000,
    'development_fields':['v060m30','v150p45','v330p10','barnard','rw-aur'],
    'calibration_fields':['q030m10','q180p20','q300m30'],'validation_fields':[s[0] for s in VALIDATION_FIELDS],
    'development_positions_px':prior.RULES['validation_positions_px'],
    'calibration_positions_px':prior.RULES['calibration_positions_px'],
    'validation_positions_px':prior.RULES['validation_positions_px'],
    'snr_per_frame':[2.,4.],'motions_px':[[0.,0.],[.6,.05]],
    'development_truth_psfs':['nearest','isotropic_015px'],'calibration_truth_psfs':['nearest','isotropic_015px'],
    'validation_truth_psfs':['nearest','elliptical_006_022px'],
    'selection':{'baseline':'plane_fixed','minimum_group_common':4,'minimum_real_common':3,'minimum_pooled_rms_improvement':.05,
        'rule':'no higher paired numeric/accepted RMS or P90 and no fewer numeric/accepted fits in every field/SNR/PSF group and real-control field; otherwise retain simplest baseline',
        'tie_break':'pooled numeric RMS, then fixed ePSF width, then lower background degree; five leave-one-field-out selection diagnostics'},
    'promotion':{'coverage68_min':.55,'coverage68_max':.85,'minimum_supported':24,'minimum_supported_blocks':6,
        'minimum_supported_fraction':.8,'maximum_median_area_inflation':16.,'minimum_cell_supported':8,
        'rule':'pooled and every supported cell must meet 68% coverage band; all four cells need >=8 supported cases and >=2 spatial blocks; no point degradation vs plane_fixed'},
    'limits':['known-position local fitting; not blind detection','no source shot noise added',
        'three external fields; shared pixels/exposures make case counts correlated',
        'conditional routing uses observed fitted SNR and original masked background only',
        'fixed bins, pooled sparse cells and explicit out-of-support abstention; no conditional coverage guarantee',
        'no automatic WISE 0855 promotion']}
SOURCES=['ablation_study.py','ablation_model.py','conditional_covariance.py','prepare_ablation_data.py',*prior.SOURCES]


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sources():return {n:bench.digest(ROOT/'scripts'/n) for n in SOURCES}
def head():return prior.head()
def ensure_committed(name):
    expected=subprocess.check_output(['git','show','HEAD:web/data/ablation/'+name],cwd=ROOT)
    if expected!=(OUT/name).read_bytes():raise RuntimeError('Commit '+name+' before dependent phase')


def design():
    path=OUT/'design.json'
    if path.exists():raise RuntimeError('Design already exists')
    previous=read(ROOT/'web/data/covariance/design.json');items={i['field']['id']:i for fs in previous['fields'].values() for i in fs}
    fields={'development':[],'calibration':[],'validation':[]}
    for phase in ['development','calibration']:
        for ident in RULES[phase+'_fields']:
            item=copy.deepcopy(items[ident]);role=next(k for k,v in previous['fields'].items() if any(i['field']['id']==ident for i in v))
            cache=ROOT/'web/data/covariance'/(role+'-'+ident+'.json')
            item['registration_cache']={'path':cache.relative_to(ROOT).as_posix(),'sha256':bench.digest(cache)}
            fields[phase].append(item)
    was=old.OUT;old.OUT=OUT
    try:fields['validation']=[old.prepare_item(spec[0],True) for spec in VALIDATION_FIELDS]
    finally:old.OUT=was
    exposures={k:sorted({p[e] for item in fs for p in item['pairs'] for e in ['before','after']}) for k,fs in fields.items()}
    for a,b in [('development','calibration'),('development','validation'),('calibration','validation')]:
        if set(exposures[a])&set(exposures[b]):raise RuntimeError('Exposure leakage across roles')
    bench.save(path,{'created_at_utc':prior.now(),'rules':RULES,'point_model_rules':model.RULES,'gate_rules':model.old.RULES,
        'covariance_rules':cc.RULES,'source_hashes':sources(),'fields':fields,'selected_exposure_ids':exposures,
        'selection':'geometric coordinates and catalog/image quality only; external centroids not yet fitted',
        'opened_data':'all development and calibration fields were opened in earlier versions; not new validation'})
    print('DESIGN',bench.digest(path),flush=True)


def check():
    d=read(OUT/'design.json')
    if d['source_hashes']!=sources() or d['rules']!=RULES or d['point_model_rules']!=model.RULES or d['covariance_rules']!=cc.RULES:raise RuntimeError('Source or rules changed after design')
    for fs in d['fields'].values():
        for i in fs:
            old.validate(i)
            if 'registration_cache' in i and bench.digest(ROOT/i['registration_cache']['path'])!=i['registration_cache']['sha256']:raise RuntimeError('Registration input changed')
    return d,bench.digest(OUT/'design.json')


def register(item,frames,catalog,xy):
    if len(item['pairs'])<2:raise RuntimeError('Fewer than two compatible spectral pairs')
    if 'registration_cache' in item:
        data=read(ROOT/item['registration_cache']['path']);regs=data['registrations'];training={'cache':item['registration_cache']}
    else:
        refs=[r for r in item['references'] if r['split']=='training'];measurements=old.training_measurements(frames,refs,catalog,xy)
        _,regs=old.calibrated(frames,[r for r in measurements if r['eligible']],True);training={'measurements':measurements}
    idx={r['obs_id']:r for r in regs}
    return [{**f,'offset':np.asarray(idx[f['record']['obs_id']]['offset_px']),'offset_cov':np.asarray(idx[f['record']['obs_id']]['covariance_px2'])} for f in frames],regs,training


def failed(reason,exception=None):
    return {'numeric_valid':False,'accepted':False,'quality_reasons':[reason],**({'reason':str(exception)} if exception is not None else {})}


def public(fit):
    return {'position_px':fit['position'].tolist(),'covariance_px2':fit['covariance'].tolist(),
        'effective_mjd':fit['effective_mjd'],'success':fit['success'],'at_boundary':fit['at_boundary'],
        'reduced_chi2':fit['reduced_chi2'],'quality':fit['quality'],'information_rank':fit['information_rank'],
        'width_mixture':fit.get('width_mixture'),'width_at_boundary':fit.get('width_at_boundary',False),
        'per_frame':[{k:d[k] for k in ['obs_id','snr','core_rms','core_coverage','core_outlier_fraction','information_fraction','downweighted_pixels']} for d in fit['per_frame']]}


def measure(before,after,catalog,xy,anchors,kinds,source=None,truth=None):
    references=[]
    for fs,a in zip([before,after],anchors):
        try:references.append(motion.fit_position(fs,np.asarray(a),multistart=True))
        except (ValueError,np.linalg.LinAlgError):references.append(None)
    output={}
    for kind in kinds:
        try:
            a,b=[model.fit(fs,catalog,xy,anchor,kind,reference,target_id=source['source_id'] if source else None)
                for fs,anchor,reference in zip([before,after],anchors,references)]
            if source:
                expected=gaia.gaia_xy(source,b['effective_mjd'])-gaia.gaia_xy(source,a['effective_mjd'])
                jac=gaia.gaia_jacobian(source,b['effective_mjd'])-gaia.gaia_jacobian(source,a['effective_mjd'])
                catalog_cov=jac@gaia.gaia_covariance(source)@jac.T
            else:expected=np.asarray(truth);catalog_cov=np.zeros((2,2))
            delta=b['position']-a['position'];error=gaia.TRANSFORM@(delta-expected)
            c=gaia.TRANSFORM@(a['covariance']+b['covariance']+bench.registration_covariance(before)+bench.registration_covariance(after)+catalog_cov)@gaia.TRANSFORM.T
            numeric=bool(all(bench.valid_fit(f) for f in [a,b]))
            output[kind]={'numeric_valid':numeric,'accepted':bool(numeric and a['quality']['accepted'] and b['quality']['accepted']),
                'quality_reasons':sorted(set(a['quality']['reasons']+b['quality']['reasons'])),
                'before':public(a),'after':public(b),'observed_snr':float(min(a['quality']['epoch_snr'],b['quality']['epoch_snr'])),
                'measured_east_north_arcsec':(gaia.TRANSFORM@delta).tolist(),'expected_east_north_arcsec':(gaia.TRANSFORM@expected).tolist(),
                'error_east_north_arcsec':error.tolist(),'error_arcsec':float(np.linalg.norm(error)),
                'covariance_arcsec2':c.tolist(),'mahalanobis2_raw':float(error@np.linalg.pinv(c)@error)}
        except (ValueError,np.linalg.LinAlgError) as exc:output[kind]=failed('fit_exception',exc)
    return output


def injected_frames(before,after,anchor,delta,snr,truth_psf):
    output=[]
    for fs,shift in [(before,np.zeros(2)),(after,np.asarray(delta))]:
        copies=[]
        for f in fs:
            p=np.asarray(anchor)+shift;stamp=motion.native_stamp(f,p);d=motion.stamp_model(stamp,p)/stamp['error'][:,None]
            amplitude=snr*np.sqrt(np.linalg.pinv(d.T@d)[0,0])
            copies.append({**f,'data':f['data']+prior.source_image(f,p,amplitude,truth_psf)})
        output.append(copies)
    return output


def run_field(item,phase,digest,kinds,calibrator=None):
    old.validate(item);_,frames,catalog,screening=old.load(item)
    if [v['id'] for v in catalog]!=item['catalog_ids']:raise RuntimeError('Catalog selection changed')
    ids={p[e] for p in item['pairs'] for e in ['before','after']};frames=[f for f in frames if f['record']['obs_id'] in ids];xy=model.old.positions(catalog,frames)
    result={'field':item['field'],'phase':phase,'design_sha256':digest,'kinds':kinds,'catalog_screening':screening,'unavailable':None,'real_controls':[],'injections':[]}
    try:
        frames,regs,training=register(item,frames,catalog,xy);result.update(registrations=regs,training=training)
        index={f['record']['obs_id']:f for f in frames};before,after=[[index[p[e]] for p in item['pairs']] for e in ['before','after']]
    except RuntimeError as exc:before=None;after=None;result['unavailable']=str(exc)
    for ref in item['references']:
        if ref['split']!='heldout':continue
        source=ref['catalog'];r={'phase':phase,'field_id':item['field']['id'],'source_id':source['source_id']}
        if before is not None:
            anchors=[gaia.gaia_xy(source,float(np.mean([f['mjd'] for f in fs]))) for fs in [before,after]]
            backgrounds=[model.background(fs,xy,a) for fs,a in zip([before,after],anchors)]
            r['background']=combine_background(backgrounds);r['models']=measure(before,after,catalog,xy,anchors,kinds,source=source)
        else:r.update(background={'score':None},models={k:failed('registration_unavailable') for k in kinds})
        result['real_controls'].append(r);print(phase,item['field']['id'],'REAL',source['source_id'],flush=True)
    for patch,anchor in enumerate(RULES[phase+'_positions_px']):
        bg=combine_background([model.background(fs,xy,anchor) for fs in [before,after]]) if before is not None else {'score':None}
        for truth in RULES[phase+'_truth_psfs']:
            for snr in RULES['snr_per_frame']:
                for delta in RULES['motions_px']:
                    r={'phase':phase,'field_id':item['field']['id'],'patch_index':patch,'anchor':anchor,'truth_psf':truth,
                        'snr_per_frame':snr,'truth_delta_px':delta,'background':bg}
                    if before is None:r['models']={k:failed('registration_unavailable') for k in kinds}
                    else:
                        try:r['models']=measure(*injected_frames(before,after,anchor,delta,snr,truth),catalog,xy,[anchor,anchor],kinds,truth=delta)
                        except (ValueError,np.linalg.LinAlgError) as exc:r['models']={k:failed('input_exception',exc) for k in kinds}
                    result['injections'].append(r)
        print(phase,item['field']['id'],'PATCH',patch,'done',flush=True)
    if calibrator:
        for r in result['injections']+result['real_controls']:apply_record(r,calibrator)
    result['injection_summary']=summarize(result['injections'],kinds);result['real_summary']=summarize(result['real_controls'],kinds)
    return result


def combine_background(values):
    scores=[v['score'] for v in values]
    return {'score':float(max(scores)) if all(v is not None for v in scores) else None,'epochs':values}


def stats(rows,kind,selection):
    values=[r['models'][kind] for r in rows];valid=[r for r in values if r[selection]];reasons={}
    for r in values:
        for reason in r['quality_reasons']:reasons[reason]=reasons.get(reason,0)+1
    errors=np.asarray([r['error_east_north_arcsec'] for r in valid])
    return {'attempted':len(rows),'valid':len(valid),'reasons':reasons,
        'rms_arcsec':float(np.sqrt(np.mean(np.sum(errors**2,axis=1)))) if valid else None,
        'p90_arcsec':float(np.percentile(np.linalg.norm(errors,axis=1),90)) if valid else None,
        'bias_east_north_arcsec':errors.mean(axis=0).tolist() if valid else None,
        'width_boundary_epochs':sum(v[e]['width_at_boundary'] for v in valid for e in ['before','after']),
        'raw68_count':sum(r['mahalanobis2_raw']<=cc.RULES['ellipse68_threshold'] for r in valid)}


def paired(rows,kind,selection):
    baseline=RULES['selection']['baseline'];common=[r for r in rows if r['models'][kind][selection] and r['models'][baseline][selection]]
    result={'common':len(common),'attempted':len(rows)}
    for label,k in [('baseline',baseline),('candidate',kind)]:
        e=[r['models'][k]['error_arcsec'] for r in common]
        result[label+'_rms_arcsec']=float(np.sqrt(np.mean(np.square(e)))) if e else None
        result[label+'_p90_arcsec']=float(np.percentile(e,90)) if e else None
    return result


def summarize(rows,kinds):return {k:{s:stats(rows,k,s) for s in ['numeric_valid','accepted']} for k in kinds}


def point_check(rows,kind,minimum):
    old_kind=RULES['selection']['baseline'];a,b=[stats(rows,k,'numeric_valid') for k in [old_kind,kind]]
    aa,bb=[stats(rows,k,'accepted') for k in [old_kind,kind]];p=paired(rows,kind,'numeric_valid');q=paired(rows,kind,'accepted')
    def better(x):return x['common']>=minimum and x['candidate_rms_arcsec']<=x['baseline_rms_arcsec']+1e-8 and x['candidate_p90_arcsec']<=x['baseline_p90_arcsec']+1e-8
    return {'passed':bool(better(p) and better(q) and b['valid']>=a['valid'] and bb['valid']>=aa['valid']),
        'paired_numeric':p,'paired_accepted':q,'baseline':{'numeric':a,'accepted':aa},'candidate':{'numeric':b,'accepted':bb}}


def choose(fields):
    candidates={};allrows=[r for f in fields for r in f['injections']];rule=RULES['selection'];baseline=rule['baseline']
    for kind in KINDS:
        groups=[]
        for f in fields:
            for truth in RULES['development_truth_psfs']:
                for snr in RULES['snr_per_frame']:
                    rs=[r for r in f['injections'] if r['truth_psf']==truth and r['snr_per_frame']==snr]
                    groups.append({'field_id':f['field']['id'],'truth_psf':truth,'snr_per_frame':snr,**point_check(rs,kind,rule['minimum_group_common'])})
            groups.append({'field_id':f['field']['id'],'real':True,**point_check(f['real_controls'],kind,rule['minimum_real_common'])})
        p=paired(allrows,kind,'numeric_valid');improvement=1-p['candidate_rms_arcsec']/p['baseline_rms_arcsec'] if p['common'] and p['baseline_rms_arcsec'] else None
        eligible=bool(kind!=baseline and all(g['passed'] for g in groups) and improvement is not None and improvement>=rule['minimum_pooled_rms_improvement'])
        candidates[kind]={'eligible_to_replace':eligible,'passed_groups':sum(g['passed'] for g in groups),'groups':groups,
            'pooled_paired_numeric':p,'improvement_fraction':improvement}
    eligible=[k for k in KINDS if candidates[k]['eligible_to_replace']]
    selected=min(eligible,key=lambda k:(candidates[k]['pooled_paired_numeric']['candidate_rms_arcsec'],int(model.MODELS[k]['flexible']),model.MODELS[k]['degree'])) if eligible else baseline
    return {'selected_model':selected,'retained_baseline':selected==baseline,'candidates':candidates,
        'reason':'No more complex model met all paired group/count criteria' if selected==baseline else 'Candidate passed every predeclared development group and pooled improvement threshold'}


def feature_thresholds(fields):
    patches=[]
    for f in fields:
        unique={r['patch_index']:r['background']['score'] for r in f['injections'] if r['background']['score'] is not None}
        for key,value in unique.items():patches.append({'field':f['field']['id'],'patch':key,'value':value,'weight':1/len(unique)})
    if not patches:raise RuntimeError('No development background features')
    patches.sort(key=lambda p:p['value']);w=np.array([p['weight'] for p in patches]);w/=w.sum()
    index=min(len(patches)-1,int(np.searchsorted(np.cumsum(w),.5)))
    return {'snr_cut':cc.RULES['snr_cut'],'background_cut':float(patches[index]['value'])}


def apply_record(r,calibrator):
    kind=calibrator['selected_model'];v=r['models'][kind]
    features={'observed_snr':v.get('observed_snr'),'background_score':r['background']['score']}
    r['calibration_features']=features;r['calibration_cell']=cc.classify(features,calibrator['thresholds'])
    if 'covariance_arcsec2' not in v:return
    e=np.asarray(v['error_east_north_arcsec']);raw=np.asarray(v['covariance_arcsec2'])
    for name,conditional in [('global_calibration',False),('conditional_calibration',True)]:
        value=cc.apply(raw,features,calibrator,conditional)
        if value['supported']:
            c=np.asarray(value['covariance_arcsec2']);value.update(mahalanobis2=float(e@np.linalg.solve(c,e)),
                area_inflation=float(np.sqrt(max(0.,np.linalg.det(c))/max(np.linalg.det(raw),1e-30))))
        v[name]=value


def calibration_stats(rows,selected,name):
    accepted=[r for r in rows if r['models'][selected]['accepted']]
    supported=[r for r in accepted if r['models'][selected].get(name,{}).get('supported')]
    values=[r['models'][selected][name] for r in supported];n=len(values)
    return {'attempted':len(rows),'accepted':len(accepted),'supported':n,'unsupported':len(accepted)-n,
        'covered68':sum(v['mahalanobis2']<=cc.RULES['ellipse68_threshold'] for v in values),
        'covered95':sum(v['mahalanobis2']<=cc.RULES['ellipse95_threshold'] for v in values),
        'fraction68':float(np.mean([v['mahalanobis2']<=cc.RULES['ellipse68_threshold'] for v in values])) if n else None,
        'median_area_inflation':float(np.median([v['area_inflation'] for v in values])) if n else None,
        'pooled_count':sum(v.get('pooled',False) for v in values),
        'blocks':len({(r['field_id'],r.get('patch_index',r.get('source_id'))) for r in supported}),
        'fields':len({r['field_id'] for r in supported})}


def uncertainty_summary(rows,selected):
    common=[r for r in rows if all(r['models'][selected].get(k,{}).get('supported') for k in ['global_calibration','conditional_calibration'])]
    return {'raw':stats(rows,selected,'accepted'),
        'global':calibration_stats(rows,selected,'global_calibration'),'conditional':calibration_stats(rows,selected,'conditional_calibration'),
        'common_supported':{'global':calibration_stats(common,selected,'global_calibration'),'conditional':calibration_stats(common,selected,'conditional_calibration')},
        'cells':{cell:{'global':calibration_stats([r for r in rows if r.get('calibration_cell')==cell],selected,'global_calibration'),
            'conditional':calibration_stats([r for r in rows if r.get('calibration_cell')==cell],selected,'conditional_calibration')} for cell in cc.CELLS}}


def coverage_gate(rows,selected):
    summary=uncertainty_summary(rows,selected);s=summary['conditional'];p=RULES['promotion']
    supported=[r for r in rows if r['models'][selected]['accepted'] and r['models'][selected].get('conditional_calibration',{}).get('supported')]
    fields=sorted({r['field_id'] for r in supported});blocks=sorted({(r['field_id'],r['patch_index']) for r in supported});values=[];rng=np.random.default_rng(RULES['seed'])
    if supported:
        for _ in range(RULES['bootstrap_draws']):
            sample=[]
            for f in rng.choice(fields,len(fields),replace=True):
                patches=[b[1] for b in blocks if b[0]==f]
                for patch in rng.choice(patches,len(patches),replace=True):sample.extend(r for r in supported if (r['field_id'],r['patch_index'])==(f,patch))
            values.append(np.mean([r['models'][selected]['conditional_calibration']['mahalanobis2']<=cc.RULES['ellipse68_threshold'] for r in sample]))
    ci=np.percentile(values,[2.5,97.5]).tolist() if values else None
    cells={key:bool(v['conditional']['supported']>=p['minimum_cell_supported'] and v['conditional']['blocks']>=2 and
        p['coverage68_min']<=v['conditional']['fraction68']<=p['coverage68_max']) for key,v in summary['cells'].items()}
    passed=bool(s['supported']>=p['minimum_supported'] and s['blocks']>=p['minimum_supported_blocks'] and s['fields']==3 and
        s['accepted'] and s['supported']/s['accepted']>=p['minimum_supported_fraction'] and
        p['coverage68_min']<=s['fraction68']<=p['coverage68_max'] and ci[0]<=.68<=ci[1] and
        s['median_area_inflation']<=p['maximum_median_area_inflation'] and all(cells.values()))
    return {'passed':passed,'summary':summary,'cells_passed':cells,'hierarchical_bootstrap95':ci,
        'qualification':'supported-only coverage with support fraction gate; three fields and shared exposures, not a coverage guarantee'}


def field_compact(r):return {k:v for k,v in r.items() if k not in ['injections','real_controls','training','registrations']}


def run(phase):
    d,digest=check();cal=None;selected=None
    if phase=='development':kinds=KINDS
    else:
        selection=read(OUT/'selection.json');selected=selection['selected_model'];kinds=list(dict.fromkeys(['plane_fixed',selected]));ensure_committed('selection.json')
        if selection['design_sha256']!=digest:raise RuntimeError('Selection design mismatch')
        if phase=='validation':
            seal=read(OUT/'validation-protocol.json');cal=read(OUT/'calibrator.json');ensure_committed('validation-protocol.json')
            if seal['design_sha256']!=digest or seal['calibrator_sha256']!=bench.digest(OUT/'calibrator.json') or seal['selection_sha256']!=bench.digest(OUT/'selection.json'):raise RuntimeError('Sealed inputs changed')
    ensure_committed('design.json');results=[]
    for item in d['fields'][phase]:
        path=OUT/(phase+'-'+item['field']['id']+'.json')
        if path.exists():
            result=read(path)
            if result['design_sha256']!=digest or result['kinds']!=kinds:raise RuntimeError('Existing opened field belongs to a different protocol')
        else:
            result=run_field(item,phase,digest,kinds,cal)
            if phase=='validation':result.update(validation_protocol_sha256=bench.digest(OUT/'validation-protocol.json'),lock_commit=head())
            bench.save(path,result)
        results.append(result)
    rows=[r for f in results for r in f['injections']];real=[r for f in results for r in f['real_controls']]
    summary={'phase':phase,'version':RULES['version'],'design_sha256':digest,'models':kinds,'fields':[field_compact(f) for f in results],
        'injection_summary':summarize(rows,kinds),'real_summary':summarize(real,kinds),'current_measurement_changed':False}
    if phase=='development':
        selection=choose(results);selection.update(design_sha256=digest,development_lock_commit=head(),feature_thresholds=feature_thresholds(results),
            source_results={f['field']['id']:bench.digest(OUT/('development-'+f['field']['id']+'.json')) for f in results},
            leave_one_field_out=[{'excluded_field':f['field']['id'],'selected_model':choose([v for v in results if v is not f])['selected_model']} for f in results])
        bench.save(OUT/'selection.json',selection);summary['selection']=selection
    elif phase=='calibration':
        cal=cc.fit(rows,selected,selection['feature_thresholds']);cal.update(design_sha256=digest,selection_sha256=bench.digest(OUT/'selection.json'),
            created_at_utc=prior.now(),selection_lock_commit=head(),source_results={f['field']['id']:bench.digest(OUT/('calibration-'+f['field']['id']+'.json')) for f in results})
        bench.save(OUT/'calibrator.json',cal)
        for r in rows+real:apply_record(r,cal)
        summary.update(selected_model=selected,injection_uncertainty=uncertainty_summary(rows,selected),real_uncertainty=uncertainty_summary(real,selected))
    else:
        for f in results:
            f['uncertainty']=uncertainty_summary(f['injections'],selected);f['real_uncertainty']=uncertainty_summary(f['real_controls'],selected)
            f['point_check']=point_check(f['injections'],selected,8)
        summary.update(fields=[field_compact(f) for f in results],selected_model=selected,injection_uncertainty=uncertainty_summary(rows,selected),
            real_uncertainty=uncertainty_summary(real,selected),coverage_gate=coverage_gate(rows,selected),
            point_passed=all(f['point_check']['passed'] and point_check(f['real_controls'],selected,3)['passed'] for f in results),
            validation_protocol_sha256=bench.digest(OUT/'validation-protocol.json'),lock_commit=head())
        summary['passed']=summary['point_passed'] and summary['coverage_gate']['passed']
    bench.save(OUT/(phase+'-summary.json'),summary);print('SUMMARY',phase,summary.get('selected_model',summary.get('selection',{}).get('selected_model')),summary.get('passed'),flush=True)


def seal():
    _,digest=check();path=OUT/'validation-protocol.json'
    if path.exists():raise RuntimeError('Seal already exists')
    selection=read(OUT/'selection.json');cal=read(OUT/'calibrator.json')
    if selection['design_sha256']!=digest or cal['design_sha256']!=digest or cal['selection_sha256']!=bench.digest(OUT/'selection.json'):raise RuntimeError('Selection/calibration mismatch')
    for ident,h in cal['source_results'].items():
        if bench.digest(OUT/('calibration-'+ident+'.json'))!=h:raise RuntimeError('Calibration product changed')
    bench.save(path,{'sealed_at_utc':prior.now(),'design_sha256':digest,'selection_sha256':bench.digest(OUT/'selection.json'),
        'calibrator_sha256':bench.digest(OUT/'calibrator.json'),'source_hashes':sources(),'selected_model':selection['selected_model'],
        'rules':RULES,'covariance_rules':cc.RULES,'parameters':cal,'requirement':'commit before external validation'})
    print('SEAL',bench.digest(path),flush=True)


def main():
    parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group(required=True)
    for name in ['design','develop','calibrate','seal','validate']:g.add_argument('--'+name,action='store_true')
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    if args.design:design()
    elif args.develop:run('development')
    elif args.calibrate:run('calibration')
    elif args.seal:seal()
    else:run('validation')


if __name__=='__main__':main()
