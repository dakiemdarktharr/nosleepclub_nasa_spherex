"""Frozen conditional point-model comparison on existing WISE development data."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from importlib.metadata import version
from pathlib import Path
import platform
import subprocess
import time

import astropy.units as u
import numpy as np

from . import linked_epoch_model as model
from . import wise_linked_inputs as inputs
from . import parse_wise0855_prism as prism
from . import lab_spectral_response as lab
from .science_jobs import locked, atomic


ROOT = inputs.ROOT
DESIGN = ROOT/'web/data/linked-flux/design.json'
OUTPUT = ROOT/'data/raw/benchmark/linked-wise-development.json'
VARIANTS = (
    {'id':'independent','mode':'independent'},
    {'id':'shared_r7_68_a0','mode':'shared','channels':68,'center_model':'r7','reference_alpha':0.},
    {'id':'tilt_r7_68_a0','mode':'shared_tilt','channels':68,'center_model':'r7','reference_alpha':0.},
    {'id':'shared_r7_68_am4','mode':'shared','channels':68,'center_model':'r7','reference_alpha':-4.},
    {'id':'shared_r7_68_ap4','mode':'shared','channels':68,'center_model':'r7','reference_alpha':4.},
    {'id':'shared_qr2_68_a0','mode':'shared','channels':68,'center_model':'qr2','reference_alpha':0.},
    {'id':'shared_r7_17_a0','mode':'shared','channels':17,'center_model':'r7','reference_alpha':0.})
RULES = {
    'version':'0.10.0-wise-linked-development.1',
    'scope':'20 already opened WISE QR2 wide cutouts; two overlapping frozen configurations, not 24 independent exposures or unseen fields',
    'configurations':['broad','strict'],'variants':list(VARIANTS),
    'primary_candidate':'shared_r7_68_a0','control':'independent',
    'anchor_sky_grid_px':[31.5,31.5], 'max_irls_iterations':20,
    'weight_tolerance':.001, 'position_tolerance_px':.0001,
    'final_fixed_weight_mode_audit':True,
    'tilt_center_um':4.75,'tilt_scale_um':.20,
    'spectral_normalization_jy':.0005,
    'spectrum':'MAST PRISM only; not merged, deconvolved, rescaled or made into astronomical truth',
    'response':'Cent channel curve shifted to nearest-source-pixel center; no width dilation or pixel-footprint response integration',
    'reference_spectrum':'Fnu(lambda)/Fnu(local)=(lambda/local)^alpha; explicitly hypothetical, not a verified SPHEREx convention',
    'registration':'reuse frozen Gaia frame offsets, fixed during fits; covariance excluded from reported centroid-only matrices',
    'covariance_cross_epoch':'zero conditional cross-epoch centroid covariance assumed when summing; no shared calibration/reference/PSF terms',
    'time_model':'one position per epoch; within-season proper motion/parallax not modeled in this isolated comparison',
    'selection':'all 28 epoch attempts retained, including preparation/fit failures; no model selected from results',
    'promotion':False,
    'qualifications':[
        'Independent control uses the same new renderer, pixels and nuisance span as linked fits; it is not the exact published 0.3 or 0.10 estimator.',
        'Raw/reference color, PRISM LSF, spectral variability, true per-pixel response, ePSF tails and shared systematics remain unvalidated.',
        'Point shifts are model sensitivity, not accuracy improvement. No RMS/coverage claim is available from one known object.',
        'GN/H covariance is conditional on final robust weights and diagonal native variance. No calibrated confidence or detection probability.',
        'Final-mode delta-chi2 threshold is a numerical heuristic; no nominal likelihood coverage is assigned.',
        'No prospective calibration/validation/holdout field is opened.'
    ]}
SOURCE_PATHS = tuple('scripts/'+name+'.py' for name in (
    'run_wise_linked_study','wise_linked_inputs','linked_epoch_model','native_flux_template',
    'wcs_pixel_area','sed_flux_coefficient','lab_pixel_binding','lab_spectral_response',
    'parse_wise0855_prism','spectral_bandpass_v2','native_gain_binding','science_mask_policy',
    'gaia_motion','motion_analysis','build_demo','joint_motion','release_analysis',
    'quality_model','benchmark_accuracy','profile_uncertainty','ablation_model',
    'covariance_model','conditional_covariance','science_jobs')) + (
    'tests/test_linked_epoch_model.py','tests/test_native_flux_template.py',
    'tests/test_wcs_pixel_area.py','tests/test_sed_flux_coefficient.py',
    'tests/test_lab_pixel_binding.py','tests/test_wise_linked_inputs.py',
    'tests/test_wise_linked_study.py',
    'docs/WISE_LINKED_PROTOCOL.md','requirements.txt')
PRODUCT_PATHS = ('web/data/gaia/results.json','web/data/release/protocol.json',
    'web/data/external/wise0855-prism-reference.json',
    'web/data/external/photometric-convention.json')


def relative(path):
    return Path(path).relative_to(ROOT).as_posix()


def jsonable(value):
    if isinstance(value,np.ndarray):return jsonable(value.tolist())
    if isinstance(value,np.generic):return jsonable(value.item())
    if isinstance(value,float) and not np.isfinite(value):return None
    if isinstance(value,dict):return {str(k):jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [jsonable(x) for x in value]
    return value


def encoded(value):
    return (json.dumps(jsonable(value),ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')


def hashes():
    manifest = json.loads(inputs.gaia.INPUT.read_text(encoding='utf-8'))
    raw = [inputs.gaia.INPUT,lab.ARCHIVE,prism.PATH]
    raw += [ROOT/x['path'] for x in (*manifest['records'],*manifest['calibrations'].values())]
    return {'sources':{p:lab.digest(ROOT/p) for p in SOURCE_PATHS},
        'opened_products':{p:lab.digest(ROOT/p) for p in PRODUCT_PATHS},
        'raw':{relative(p):{'sha256':lab.digest(p),'bytes':p.stat().st_size} for p in raw}}


def create_design():
    if DESIGN.exists():raise RuntimeError('design exists; refusing overwrite')
    document = {'rules':RULES,**hashes(),'status':'development comparison on opened data; no validation or promotion'}
    DESIGN.parent.mkdir(parents=True,exist_ok=True)
    with DESIGN.open('xb') as stream:stream.write(encoded(document))
    return document


def verify_design():
    document=json.loads(DESIGN.read_text(encoding='utf-8'))
    if document.get('rules')!=RULES or any(document.get(k)!=v for k,v in hashes().items()):
        raise RuntimeError('locked protocol/input hash mismatch')
    for name in (*SOURCE_PATHS,*PRODUCT_PATHS,relative(DESIGN)):
        try:raw=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT,stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as exc:raise RuntimeError('required source/design not committed: '+name) from exc
        if sha256(raw).hexdigest()!=lab.digest(ROOT/name):
            raise RuntimeError('uncommitted source/design: '+name)
    return document


def packed_samples(prepared,predictions,variant):
    indexed={p['obs_id']:p for p in predictions}
    if len(indexed)!=len(predictions):raise ValueError('duplicate spectral prediction ID')
    result=[]
    for item in prepared:
        prediction=indexed.get(item['obs_id'])
        if variant['mode']!='independent' and prediction is None:
            raise ValueError('missing spectral prediction for a linked exposure')
        frame={key:item[key] for key in ('data','error','nuisance','renderer')}
        frame['coefficient']=prediction['relative_coefficient'] if prediction else 1.
        frame['coefficient_provenance']=json.dumps(prediction,sort_keys=True,allow_nan=False) if prediction else 'independent free flux; no spectral constraint'
        if variant['mode']=='shared_tilt':frame['wavelength']=prediction['chosen_center_um']*u.um
        result.append(frame)
    return result


def pair_summaries(records):
    output=[]
    for config in RULES['configurations']:
        for variant in VARIANTS:
            matches=[x for x in records if x['configuration']==config and x['variant']==variant['id']]
            if len(matches)!=2:continue
            row={'configuration':config,'variant':variant['id'],'epoch_attempts':2,
                 'successful_epoch_fits':sum(x['status']=='fit_completed' for x in matches),
                 'solver_screening_both':False,'east_north_arcsec':None,
                 'covariance_assumption':RULES['covariance_cross_epoch']}
            if row['successful_epoch_fits']==2:
                before=next(x['fit'] for x in matches if x['epoch']=='before')
                after=next(x['fit'] for x in matches if x['epoch']=='after')
                T=inputs.gaia.TRANSFORM
                vector=T@(np.asarray(after['position'])-np.asarray(before['position']))
                row['east_north_arcsec']=vector.tolist()
                row['solver_screening_both']=bool(before['inference_supported'] and after['inference_supported'])
                for name,path in (('gn','position_covariance_px2'),('profile','profile_hessian')):
                    cov=[]
                    for fit in (before,after):
                        value=fit[path] if name=='gn' else fit[path].get('covariance_px2') if fit[path].get('supported') else None
                        if value is not None:cov.append(np.asarray(value,float))
                    if len(cov)==2:row[name+'_conditional_centroid_covariance_arcsec2']=(T@sum(cov)@T.T).tolist()
            output.append(row)
    for row in output:
        baseline=next((r for r in output if r['configuration']==row['configuration'] and r['variant']=='independent'),None)
        if baseline and row['east_north_arcsec'] is not None and baseline['east_north_arcsec'] is not None:
            row['change_from_independent_arcsec']=float(np.linalg.norm(np.asarray(row['east_north_arcsec'])-baseline['east_north_arcsec']))
    return output


def save_report(report):
    for row in report['records']:
        if row.get('record_sha256')!=sha256(encoded({k:v for k,v in row.items() if k!='record_sha256'})).hexdigest():
            raise RuntimeError('stored attempt checksum mismatch')
    report['pairs']=pair_summaries(report['records'])
    expected={(c,v['id'],e) for c in RULES['configurations'] for v in VARIANTS for e in ('before','after')}
    actual={(r['configuration'],r['variant'],r['epoch']) for r in report['records']}
    if len(actual)!=len(report['records']) or not actual.issubset(expected):raise RuntimeError('duplicate or unknown stored attempt')
    report['completed']=actual==expected
    report['counts']={'planned_epoch_attempts':len(expected),'recorded_epoch_attempts':len(actual),
        'fit_completed':sum(r['status']=='fit_completed' for r in report['records']),
        'failures':sum(r['status']!='fit_completed' for r in report['records']),
        'renderer_metadata_failures':sum(bool(r.get('renderer_metadata_failed')) for r in report['records'])}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    atomic(OUTPUT,jsonable(report))


def execution_runtime():
    packages={}
    for line in (ROOT/'requirements.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        name, expected=line.split('==')
        actual=version(name)
        if actual!=expected:raise RuntimeError('runtime package differs from pinned science requirements: '+name)
        packages[name]=actual
    return {'python':platform.python_version(),'platform':platform.platform(),'packages':packages}


def run(configurations,variants):
    protocol=verify_design();design_hash=lab.digest(DESIGN);runtime=execution_runtime()
    if OUTPUT.exists():
        report=json.loads(OUTPUT.read_text(encoding='utf-8'))
        if report.get('protocol_sha256')!=design_hash or report.get('rules')!=RULES:raise RuntimeError('checkpoint identity mismatch')
        if report.get('runtime')!=runtime:raise RuntimeError('checkpoint execution environment differs')
        if report.get('completed'):raise RuntimeError('study completed; refusing rerun/overwrite')
        save_report(report)
    else:
        report={'rules':RULES,'protocol_sha256':design_hash,'protocol_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'source_hashes':protocol['sources'],'input_hashes':protocol['raw'],'opened_products':protocol['opened_products'],
            'started_at_utc':datetime.now(timezone.utc).isoformat(),'runtime':runtime,'records':[]}
    frames,_=inputs.read_verified_frames()
    for label in configurations:
        config_failure=None
        try:
            groups,catalog,xy,previous=inputs.configuration(frames,label)
        except Exception as exc:
            groups=[[],[]];previous={};config_failure=type(exc).__name__+': '+str(exc)
        prepared=[];prep_errors=[]
        for group in groups:
            try:
                if config_failure:raise ValueError(config_failure)
                prepared.append(inputs.prepared_samples(group,catalog,xy,np.asarray(RULES['anchor_sky_grid_px'])))
                prep_errors.append(None)
            except Exception as exc:
                prepared.append([]);prep_errors.append(type(exc).__name__+': '+str(exc))
        for variant in variants:
            pending=[e for e in ('before','after') if not any(r['configuration']==label and r['variant']==variant['id'] and r['epoch']==e for r in report['records'])]
            if not pending:continue
            print('PREPARE',label,variant['id'],flush=True)
            for epoch,group,items,preparation_failure in zip(('before','after'),groups,prepared,prep_errors):
                if epoch not in pending:continue
                predictions,members=[],{}
                if not preparation_failure and variant['mode']!='independent':
                    try:
                        predictions,members=inputs.spectral_predictions(group,normalization_jy=RULES['spectral_normalization_jy'],
                            **{k:variant[k] for k in ('channels','center_model','reference_alpha')})
                    except Exception as exc:
                        preparation_failure='spectral_prediction '+type(exc).__name__+': '+str(exc)
                row={'configuration':label,'variant':variant['id'],'epoch':epoch,'obs_ids':[f['record']['obs_id'] for f in group],
                    'predictions':predictions,'calibration_members':members,
                    'literature_prior_context':previous.get('predicted_motion'),
                    'samples':[],
                    'data_contract':'MJy/sr; IMAGE-ZODI-scalar; fixed original Gaia offsets; strict SOURCE-only mask; fitted constant absorbs scalar'}
                start=time.monotonic();stage='sample_metadata'
                try:
                    row['samples']=[{'obs_id':x['obs_id'],'x':x['sample']['x'].tolist(),'y':x['sample']['y'].tolist(),
                        'error_mjysr':x['error'].tolist(),'epsf_zone':int(x['sample']['zone']),
                        'selected_pixels':len(x['data']),'nuisance_rank':x['nuisance'].shape[1],
                        'nuisance_provenance':x['nuisance_provenance'],
                        'renderer_provenance':x['renderer_provenance'],
                        'cutout_url':x['sample']['frame']['record']['cutout_url'],
                        'raw_sha256':x['sample']['frame']['record']['sha256']} for x in items]
                    stage='packing'
                    if preparation_failure:raise ValueError(preparation_failure)
                    packed=packed_samples(items,predictions,variant)
                    kwargs={'tilt_center':RULES['tilt_center_um']*u.um,'tilt_scale':RULES['tilt_scale_um']*u.um} if variant['mode']=='shared_tilt' else {}
                    stage='fit'
                    row['fit']=jsonable(model.fit_epoch(packed,RULES['anchor_sky_grid_px'],data_unit='MJy/sr',mode=variant['mode'],
                        observed_hessian=True,max_irls_iterations=RULES['max_irls_iterations'],weight_tolerance=RULES['weight_tolerance'],
                        position_tolerance=RULES['position_tolerance_px'],final_mode_audit=True,**kwargs))
                    row['status']='fit_completed'
                    stage='renderer_metadata'
                    for descriptor,item in zip(row['samples'],items):
                        descriptor['at_fitted_position']=item['describe_renderer'](row['fit']['position'])
                except Exception as exc:
                    if stage=='renderer_metadata' and 'fit' in row:
                        row['fit']['inference_supported']=False
                        row['renderer_metadata_failed']=True
                        terminal='fit_completed'
                    else:terminal='fit_failed' if stage=='fit' else 'preparation_failed'
                    row.update(status=terminal,failure_stage=stage,error=type(exc).__name__+': '+str(exc),
                        start_reports=jsonable(getattr(exc,'start_reports',[])))
                row['elapsed_seconds']=time.monotonic()-start
                row['record_sha256']=sha256(encoded(row)).hexdigest()
                report['records'].append(row);save_report(report)
                print('CHECKPOINT',label,variant['id'],epoch,row['status'],round(row['elapsed_seconds'],3),flush=True)
    save_report(report)
    print('COUNTS',report['counts'],'completed',report['completed'],flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--design',action='store_true');p.add_argument('--run',action='store_true')
    p.add_argument('--configurations',nargs='+',choices=RULES['configurations'],default=RULES['configurations'])
    p.add_argument('--variants',nargs='+',choices=[v['id'] for v in VARIANTS],default=[v['id'] for v in VARIANTS])
    args=p.parse_args()
    if args.design==args.run:p.error('choose exactly --design or --run')
    if args.design:create_design();print('DESIGN',relative(DESIGN),lab.digest(DESIGN))
    else:
        OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        with locked(OUTPUT.parent,name=OUTPUT.name+'.lock'):
            run(args.configurations,[v for v in VARIANTS if v['id'] in args.variants])


if __name__=='__main__':main()
