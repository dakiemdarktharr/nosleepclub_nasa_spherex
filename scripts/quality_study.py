"""Develop on opened fields, then lock before a new-field A/B evaluation."""
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter,map_coordinates,spline_filter

from . import quality_model as model
from . import benchmark_accuracy as bench
from . import prepare_quality_data as prepare

ROOT=bench.ROOT;RAW=ROOT/'data/raw/quality';OUT=ROOT/'web/data/quality'
motion=bench.motion;gaia=bench.gaia;release=model.release
RULES={'version':'0.7.0','spectral_configuration':'broad','spectral_mismatch_max':.5,
    'positions_px':[[5.5,5.5],[57.5,5.5],[5.5,57.5],[57.5,57.5]],'snr_per_frame':[2.,4.],
    'motions_px':[[0.,0.],[.6,.05]],'truth_psfs':['nearest','blurred_015px'],
    'gaussian_blur_native_px':.15,'ellipse_threshold':2.30,'recovery_tolerance_px':1.,
    'injection_frame':'identical Gaussian Gaia registration for both models; isolates centroid/deblending effect',
    'real_frame':'baseline Gaussian registration vs candidate IR-centroid training + median/MAD rejection',
    'gate':'each new field, SNR and truth PSF: paired numerical RMS lower, P90 no higher, no fewer numerical fits or quality-accepted fits; real Gaia paired RMS no higher with >=3 common, no fewer numerical/accepted fits; no default WISE promotion',
    'models':['baseline','ir_robust'],'minimum_common_per_group':4,'bootstrap_draws':2000,'seed':20261030,
    'limits':['known-position local fitting, not blind detection','no extra source shot noise',
        'blur is an assumed PSF perturbation, not independent physical calibration',
        'conditional IRLS covariance; no neighbour-position, PSF or shared-frame systematic covariance',
        'broad spectra only; default WISE 0855 measurement remains unchanged']}
SOURCE_FILES=['quality_study.py','quality_model.py','prepare_quality_data.py','benchmark_accuracy.py',
    'prepare_benchmark_data.py','release_analysis.py','joint_motion.py','gaia_motion.py','motion_analysis.py','build_demo.py']


def sources():return {name:bench.digest(ROOT/'scripts'/name) for name in SOURCE_FILES}


def load(item):
    old=bench.RAW;bench.RAW=(ROOT/item['manifest_path']).parent.parent
    try:manifest,frames,audit=bench.load(item['field']['id'])
    finally:bench.RAW=old
    release.RAW=RAW/item['field']['id'];catalog,screening=release.build_catalog(manifest)
    return manifest,frames,catalog,screening


def prepare_item(ident,new):
    path=(RAW if new else ROOT/'data/raw/benchmark')/ident/'manifest.json'
    manifest=json.loads(path.read_text());item={'field':manifest['field'],'manifest_path':path.relative_to(ROOT).as_posix(),
        'manifest_sha256':bench.digest(path),'input_manifest':manifest,'infrared':json.loads((RAW/ident/'infrared.json').read_text())}
    manifest,frames,catalog,screening=load(item)
    if new:
        pairs=bench.pairs(frames,RULES['spectral_mismatch_max']);used={f['record']['obs_id'] for p in pairs for f in p[:2]}
        selected=[f for f in frames if f['record']['obs_id'] in used]
        if selected:candidates,audit,image=gaia.candidate_references(selected,manifest)
        else:candidates=[];audit=[];image=None
        quadrants=[[] for _ in range(4)]
        for c in candidates:
            x,y=np.array(c['anchor'])-motion.TARGET_ANCHOR;quadrants[int(x>=0)+2*int(y>=0)].append(c)
        references=[]
        while len(references)<32 and any(quadrants):
            for q in quadrants:
                if q and len(references)<32:references.append(q.pop(0))
        references.sort(key=lambda r:sha256(r['catalog']['source_id'].encode()).hexdigest())
        for i,r in enumerate(references):r['split']='heldout' if i%3==0 else 'training'
        item.update(pairs=[{'before':a['record']['obs_id'],'after':b['record']['obs_id'],'mismatch':v} for a,b,v in pairs],references=references,selection_audit=audit)
        if image is not None:
            OUT.mkdir(parents=True,exist_ok=True);lo,hi=np.nanpercentile(image,[5,99.5]);bench.base.png_image(image,OUT/(ident+'.png'),lo,hi)
    else:
        old=next(i for i in json.loads((ROOT/'web/data/benchmark/protocol.json').read_text())['fields'] if i['field']['id']==ident)
        item.update(pairs=old['configurations']['broad'],references=old['references'])
        if 'positive_control' in old:item['positive_control']=old['positive_control']
    item['catalog_screening']=screening;item['catalog_ids']=[c['id'] for c in catalog]
    print('PREPARE',ident,len(item['pairs']),'pairs',len(item['references']),'references',screening['selected'],'IR',flush=True)
    return item


def validate(item):
    if bench.digest(ROOT/item['manifest_path'])!=item['manifest_sha256']:raise RuntimeError('Manifest changed')
    for r in item['input_manifest']['records']:
        if r['status']!='downloaded' or bench.digest(ROOT/r['path'])!=r['sha256']:raise RuntimeError('FITS changed or incomplete')
    for r in [item['input_manifest']['gaia'],*item['input_manifest']['calibrations'].values(),*item['infrared'].values()]:
        if bench.digest(ROOT/r['path'])!=r['sha256']:raise RuntimeError('Catalog/calibration changed')


def training_measurements(frames,references,catalog,xy):
    measured=[]
    for r in references:
        s=r['catalog'];entries=[]
        for f in frames:
            anchor=gaia.gaia_xy(s,f['mjd']);reason=None
            try:
                fit=model.fit([f],catalog,xy,anchor,target_id=s['source_id'],reference=True)
                if not fit['quality']['accepted']:reason='quality:'+','.join(fit['quality']['reasons'])
                elif fit['per_frame'][0]['snr']<gaia.RULES['reference_snr_min']:reason='low_reference_snr'
            except (ValueError,np.linalg.LinAlgError) as exc:reason=str(exc)
            e={'obs_id':f['record']['obs_id'],'epoch':f['record']['epoch'],'expected_px':anchor.tolist(),'rejection':reason}
            if reason is None:
                jac=gaia.gaia_jacobian(s,f['mjd']);e.update(delta_px=(fit['position']-anchor).tolist(),
                    covariance_px2=fit['covariance'].tolist(),gaia_covariance_px2=(jac@gaia.gaia_covariance(s)@jac.T).tolist())
            entries.append(e)
        eligible=sum(e['rejection'] is None for e in entries)>=np.ceil(.7*len(frames))
        eligible&=all(sum(e['rejection'] is None and e['epoch']==epoch for e in entries)>=3 for epoch in ['before','after'])
        measured.append({**r,'entries':entries,'eligible':bool(eligible)})
        print('IR TRAIN',s['source_id'],sum(e['rejection'] is None for e in entries),'/',len(frames),flush=True)
    return measured


def calibrated(frames,training,robust):
    output=[];registrations=[]
    for f in frames:
        r=model.registration(f,training) if robust else gaia.fit_registration(f,training)
        output.append({**f,'offset':r['offset'].copy(),'offset_cov':r['offset_covariance'].copy()})
        registrations.append({'obs_id':f['record']['obs_id'],'source_ids':r['source_ids'],'rejected_source_ids':r.get('rejected_source_ids',[]),
            'offset_px':r['offset'].tolist(),'covariance_px2':r['offset_covariance'].tolist()})
    return output,registrations


def pair_result(before,after,catalog,xy,anchors,kind,source=None,truth=None,positive=False):
    target=source['source_id'] if source else None
    fits=[model.baseline_fit(fs,a) if kind=='baseline' else model.fit(fs,catalog,xy,a,target_id=target) for fs,a in zip([before,after],anchors)]
    a,b=fits
    if source:
        predict=bench.positive_xy if positive else gaia.gaia_xy
        expected=predict(source,b['effective_mjd'])-predict(source,a['effective_mjd'])
        jac=gaia.gaia_jacobian(source,b['effective_mjd'])-gaia.gaia_jacobian(source,a['effective_mjd'])
        catalog_cov=jac@gaia.gaia_covariance(source)@jac.T
    else:expected=np.array(truth);catalog_cov=np.zeros((2,2))
    delta=b['position']-a['position'];error=delta-expected
    covariance=a['covariance']+b['covariance']+bench.registration_covariance(before)+bench.registration_covariance(after)+catalog_cov
    numeric=all(bench.valid_fit(f) for f in fits)
    accepted=numeric and all(f['quality']['accepted'] for f in fits)
    return {'numeric_valid':bool(numeric),'accepted':bool(accepted),
        'quality_reasons':sorted(set(reason for f in fits for reason in f['quality']['reasons'])),
        'before':{**motion.public_fit(a),'quality':a['quality']},'after':{**motion.public_fit(b),'quality':b['quality']},
        'measured_east_north_arcsec':(gaia.TRANSFORM@delta).tolist(),'expected_east_north_arcsec':(gaia.TRANSFORM@expected).tolist(),
        'error_east_north_arcsec':(gaia.TRANSFORM@error).tolist(),'error_arcsec':float(np.linalg.norm(error)*bench.base.SCALE),
        'covariance_arcsec2':(gaia.TRANSFORM@covariance@gaia.TRANSFORM).tolist(),
        'within_68_ellipse':bool(error@np.linalg.pinv(covariance)@error<=RULES['ellipse_threshold']),
        'within_one_pixel':bool(np.linalg.norm(error)<=RULES['recovery_tolerance_px'])}


def safe_pair(*args,**kwargs):
    try:return pair_result(*args,**kwargs)
    except (ValueError,np.linalg.LinAlgError) as exc:return {'numeric_valid':False,'accepted':False,'quality_reasons':['fit_exception'],'reason':str(exc)}


def source_image(frame,position,amplitude,truth_psf):
    px,py=frame['wcs'].world_to_pixel_values(*motion.WCS.pixel_to_world_values(*(np.array(position)+frame['offset'])))
    psf,zone=motion.epsf_for(frame,float(px),float(py));over=frame['epsf_oversampling']
    if truth_psf!='nearest':
        raw=np.asarray(frame['epsf_table']['EPSF'][zone],float);blur=gaussian_filter(raw,RULES['gaussian_blur_native_px']*over)
        psf=spline_filter(blur*over**2/blur.sum(),order=3)
    yy,xx=np.indices(frame['data'].shape,dtype=float);center=(np.array(psf.shape)-1)/2
    return amplitude*map_coordinates(psf,[(yy-py)*over+center[0],(xx-px)*over+center[1]],order=3,mode='constant',cval=0,prefilter=False)


def stats(records,kind,selection):
    values=[r['models'][kind] for r in records];valid=[r for r in values if r[selection]]
    error=np.array([r['error_east_north_arcsec'] for r in valid])
    reasons={}
    for r in values:
        for reason in r['quality_reasons']:reasons[reason]=reasons.get(reason,0)+1
    return {'attempted':len(values),'valid':len(valid),'rejected':len(values)-len(valid),
        'rmse_arcsec':float(np.sqrt(np.mean(np.sum(error**2,axis=1)))) if valid else None,
        'p90_arcsec':float(np.percentile(np.linalg.norm(error,axis=1),90)) if valid else None,
        'bias_east_north_arcsec':error.mean(axis=0).tolist() if valid else None,
        'within_68_ellipse':sum(r['within_68_ellipse'] for r in valid),'reasons':reasons}


def paired(records,selection='numeric_valid'):
    common=[r for r in records if all(r['models'][k][selection] for k in RULES['models'])]
    def rms(kind,rows):return float(np.sqrt(np.mean([r['models'][kind]['error_arcsec']**2 for r in rows])))
    if not common:return {'common':0,'attempted':len(records),'baseline_rms':None,'candidate_rms':None,'improvement_percent':None,'ci95_percent':None}
    a,b=[rms(kind,common) for kind in RULES['models']]
    ci=None
    if all('patch_index' in r for r in common):
        blocks=sorted({r['patch_index'] for r in common});rng=np.random.default_rng(RULES['seed']);values=[]
        for _ in range(RULES['bootstrap_draws']):
            sample=[r for block in rng.choice(blocks,size=len(blocks),replace=True) for r in common if r['patch_index']==block]
            aa,bb=[rms(kind,sample) for kind in RULES['models']]
            if aa>0:values.append(100*(1-bb/aa))
        if values:ci=np.percentile(values,[2.5,97.5]).tolist()
    return {'common':len(common),'attempted':len(records),'baseline_rms':a,'candidate_rms':b,
        'improvement_percent':100*(1-b/a) if a>0 else None,'ci95_percent':ci}


def summarize(records):
    return {'models':{k:{selection:stats(records,k,selection) for selection in ['numeric_valid','accepted']} for k in RULES['models']},
        'paired_numeric':paired(records),'paired_accepted':paired(records,'accepted')}


def run_field(item,phase,protocol_hash):
    validate(item);manifest,frames,catalog,screening=load(item)
    if [c['id'] for c in catalog]!=item['catalog_ids']:raise RuntimeError('Catalog selection changed')
    index={f['record']['obs_id']:f for f in frames};ids={p[e] for p in item['pairs'] for e in ['before','after']};frames=[index[o] for o in sorted(ids)]
    result={'field':item['field'],'phase':phase,'protocol_sha256':protocol_hash,'rules':RULES,'model_rules':model.RULES,
        'pairs':len(item['pairs']),'catalog_screening':screening,'real_controls':[],'injections':[],'unavailable':{},
        'planned_injections':len(RULES['positions_px'])*len(RULES['truth_psfs'])*len(RULES['snr_per_frame'])*len(RULES['motions_px'])}
    if len(item['pairs'])<2:result['unavailable']['all']='Fewer than two spectral pairs';return result
    xy=model.positions(catalog,frames);references=[r for r in item['references'] if r['split']=='training']
    baseline_training=bench.measure_training(frames,references);candidate_training=training_measurements(frames,references,catalog,xy)
    result['training']={'baseline':baseline_training,'ir_robust':candidate_training};registered={}
    for name,training in [('baseline',baseline_training),('ir_robust',candidate_training)]:
        eligible=[r for r in training if r['eligible']]
        try:
            registered[name],regs=calibrated(frames,eligible,name=='ir_robust');result[name+'_registrations']=regs
        except RuntimeError as exc:result['unavailable'][name]=str(exc)
    def epoch_frames(name):
        idx={f['record']['obs_id']:f for f in registered[name]}
        return [[idx[p[epoch]] for p in item['pairs']] for epoch in ['before','after']]
    heldout=[r for r in item['references'] if r['split']=='heldout']
    if item.get('positive_control'):heldout=heldout+[{'catalog':item['positive_control'],'positive':True}]
    for r in heldout:
        s=r['catalog'];record={'source_id':s['source_id'],'positive':r.get('positive',False),'models':{}}
        for kind in RULES['models']:
            if kind not in registered:record['models'][kind]={'numeric_valid':False,'accepted':False,'quality_reasons':['registration_unavailable']};continue
            before,after=epoch_frames(kind);predict=bench.positive_xy if r.get('positive') else gaia.gaia_xy
            anchors=[predict(s,float(np.mean([f['mjd'] for f in fs]))) for fs in [before,after]]
            record['models'][kind]=safe_pair(before,after,catalog,xy,anchors,kind,source=s,positive=r.get('positive',False))
        result['real_controls'].append(record);print(item['field']['id'],'REAL',s['source_id'],[(k,v.get('error_arcsec'),v['accepted']) for k,v in record['models'].items()],flush=True)
    if 'baseline' in registered:
        before,after=epoch_frames('baseline')
        for patch_index,anchor in enumerate(RULES['positions_px']):
            for truth_psf in RULES['truth_psfs']:
                for snr in RULES['snr_per_frame']:
                    for delta in RULES['motions_px']:
                        record={'patch_index':patch_index,'anchor':anchor,'truth_psf':truth_psf,'snr_per_frame':snr,'truth_delta_px':delta,'models':{}}
                        try:
                            injected=[]
                            for fs,shift in [(before,np.zeros(2)),(after,np.array(delta))]:
                                copies=[]
                                for f in fs:
                                    p=np.array(anchor)+shift;s=motion.native_stamp(f,p);design=motion.stamp_model(s,p)/s['error'][:,None]
                                    amplitude=snr*np.sqrt(np.linalg.pinv(design.T@design)[0,0])
                                    copies.append({**f,'data':f['data']+source_image(f,p,amplitude,truth_psf)})
                                injected.append(copies)
                            for kind in RULES['models']:record['models'][kind]=safe_pair(*injected,catalog,xy,[anchor,anchor],kind,truth=delta)
                        except (ValueError,np.linalg.LinAlgError) as exc:
                            record['models']={k:{'numeric_valid':False,'accepted':False,'quality_reasons':['input_exception'],'reason':str(exc)} for k in RULES['models']}
                        result['injections'].append(record)
            print(item['field']['id'],'PATCH',patch_index,'done',flush=True)
    result['real_summary']=summarize([r for r in result['real_controls'] if not r['positive']])
    result['injection_summary']=summarize(result['injections'])
    result['groups']=[]
    for truth in RULES['truth_psfs']:
        for snr in RULES['snr_per_frame']:
            rows=[r for r in result['injections'] if r['truth_psf']==truth and r['snr_per_frame']==snr]
            summary=summarize(rows);old,new=[summary['models'][k] for k in RULES['models']];paired_result=summary['paired_numeric']
            summary.update(truth_psf=truth,snr_per_frame=snr)
            summary['passed']=bool(paired_result['common']>=RULES['minimum_common_per_group'] and
                paired_result['candidate_rms']<paired_result['baseline_rms'] and
                new['numeric_valid']['p90_arcsec']<=old['numeric_valid']['p90_arcsec'] and
                new['numeric_valid']['valid']>=old['numeric_valid']['valid'] and new['accepted']['valid']>=old['accepted']['valid'])
            result['groups'].append(summary)
    real=result['real_summary'];a,b=[real['models'][k] for k in RULES['models']];common=real['paired_numeric']
    result['real_passed']=bool(common['common']>=3 and common['candidate_rms']<=common['baseline_rms'] and
        b['numeric_valid']['valid']>=a['numeric_valid']['valid'] and b['accepted']['valid']>=a['accepted']['valid'])
    result['passed']=not result['unavailable'] and result['real_passed'] and all(g['passed'] for g in result['groups'])
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--develop',action='store_true');parser.add_argument('--lock',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.develop:
        items=[prepare_item(ident,False) for ident in ['barnard','rw-aur','r-dra']]
        protocol={'phase':'development_opened_fields','rules':RULES,'model_rules':model.RULES,'source_hashes':sources(),'fields':items}
        bench.save(OUT/'development-protocol.json',protocol);path=OUT/'development-protocol.json'
    elif args.lock:
        path=OUT/'protocol.json'
        if path.exists():raise RuntimeError('Protocol already exists; cannot overwrite opened evaluation')
        items=[prepare_item(spec[0],True) for spec in prepare.NEW_FIELDS]
        for item in items:validate(item)
        bench.save(path,{'phase':'evaluation_new_fields','locked_at_utc':datetime.now(timezone.utc).isoformat(),
            'rules':RULES,'model_rules':model.RULES,'source_hashes':sources(),'catalog_rules':release.RULES,'fields':items})
        print('LOCK',bench.digest(path),flush=True);return
    else:
        path=OUT/'protocol.json';protocol=json.loads(path.read_text());items=protocol['fields']
        if protocol['source_hashes']!=sources() or protocol['rules']!=RULES or protocol['model_rules']!=model.RULES:raise RuntimeError('Code or rules changed after lock')
    protocol_hash=bench.digest(path);phase='development' if args.develop else 'evaluation'
    outputs=[]
    for item in items:
        result=run_field(item,phase,protocol_hash);bench.save(OUT/(phase+'-'+item['field']['id']+'.json'),result);outputs.append(result)
        print('RESULT',item['field']['id'],result.get('passed'),result['unavailable'],result.get('injection_summary'),flush=True)
    summary={'version':RULES['version'],'phase':phase,'protocol_sha256':protocol_hash,'current_measurement_changed':False,
        'passed':all(r.get('passed',False) for r in outputs),'fields':[]}
    for r in outputs:summary['fields'].append({k:v for k,v in r.items() if k not in ['real_controls','injections','training','baseline_registrations','ir_robust_registrations']})
    bench.save(OUT/(phase+'-summary.json'),summary)


if __name__=='__main__':main()
