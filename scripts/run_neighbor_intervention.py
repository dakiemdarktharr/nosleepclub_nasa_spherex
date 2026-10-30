"""Locked development factorial and independent-PSF conditional controls.

No prospective field queries. Design and all source/test/input hashes must be
committed before any real fit or control realization. Failures remain terminal
records; a completed study cannot be overwritten or selectively rerun.
"""
import argparse
import os
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import time

THREAD_ENV=('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','BLIS_NUM_THREADS','VECLIB_MAXIMUM_THREADS')
if __name__=='__main__':
    # CLI process only, before NumPy/Astropy import. Importing this module as a
    # library does not alter another caller's threading environment.
    for _thread_key in THREAD_ENV:os.environ[_thread_key]='1'

import astropy.units as u
from astropy.io import fits
import numpy as np

from . import run_wise_linked_study as legacy
from . import wise_linked_inputs as inputs
from . import neighbor_intervention_inputs as adapter
from . import neighbor_epoch_model as model
from . import independent_scene_control as control
from . import native_gain_binding as gain_binding
from . import audit_native_gain as gain_paths
from .wcs_pixel_area import wcs_pixel_area
from .science_jobs import locked, atomic


ROOT=legacy.ROOT
DESIGN=ROOT/'web/data/neighbor-intervention/design.json'
OUTPUT=ROOT/'data/raw/benchmark/neighbor-intervention.json'
VARIANTS=tuple({'id':f'{name}_{kind}_{constraint}', 'background_order':order,
    'epsf_kind':kind, 'nonnegative_neighbors':positive}
    for order,name in ((1,'plane'),(2,'quadratic')) for kind in ('nearest','bilinear')
    for positive,constraint in ((False,'free'),(True,'nonnegative')))
CONTROL_VARIANTS=('plane_nearest_free','plane_nearest_nonnegative')
CASES=tuple({'id':f'{background}_{int(flux*1e6)}uJy','target_flux_jy':flux,'background':background}
    for background in ('plane','quadratic') for flux in (.0003,.0006))
RULES={'version':'0.10.0-neighbor-intervention.1','scope':'development on opened 20 WISE wide cutouts; no new sky field',
    'thread_environment_request':{key:'1' for key in THREAD_ENV},
    'configurations':['broad','strict'],'variants':list(VARIANTS),
    'primary_contrast':['plane_nearest_free','plane_nearest_nonnegative'],
    'target_flux':'independent SIGNED Jy per frame; no external spectral ratio or positivity on target',
    'neighbor_flux':'same semantic native Jy columns, either signed or NNLS >=0; positions fixed from opened catalog',
    'selection':'reuse original strict SOURCE-only pixels/errors/catalog IDs; no frame, neighbor or hard case dropped',
    'spatial_psf':'nearest or bilinear mixture of individually normalized raw tables, fixed at anchor/catalog coordinates; full native phase normalization follows',
    'registration':'frozen Gaia offsets, fixed; no propagation of shared reference/calibration uncertainty',
    'anchor':[31.5,31.5],'position_bound_px':2.5,'start_offsets':list(model.START_OFFSETS),
    'max_irls_iterations':20,'final_mode_audit':'nine finite starts with fixed final weights; delta chi2 5.991 is heuristic',
    'time_model':'one position per epoch; within-season motion/parallax not yet fitted',
    'uncertainty':'no covariance/confidence/SNR returned for these active-constraint fits',
    'controls':{'configuration':'strict','cases':list(CASES),'draws_per_case':16,'variants':list(CONTROL_VARIANTS),
        'seed_prefix':20261031,'rng':'PCG64 SeedSequence([prefix,case_index,draw,epoch_index,frame_index])',
        'before_position':[31.73,31.31],'displacement_sky_px':[.55,.08],
        'target_sigma_xy_native':[.55,.70],'neighbor_sigma_xy_native':[.70,.60],
        'neighbor_flux_jy':'0.00015/(1+index) in frozen retained neighbor order',
        'background_plane_coefficients_mjysr':[.04,.015,-.01],
        'quadratic_coefficients_mjysr':[.025,.020,-.015],
        'psf':'axis-aligned pixel-integrated positive Gaussian; independent family from empirical ePSF, not telescope truth',
        'pixels':'same native geometry, original VARIANCE as diagonal Gaussian background-error scale; not injections on original noisy images',
        'source_noise':'exact ideal Poisson OLS ramp of target+neighbors using per-pixel bound gain and nominal header timing',
        'fitter_error':'oracle sqrt(original variance + known expected-source variance), conditional control only',
        'estimands':'all attempts/failures, all completed pair error/RMS, common-completed and common-screened pairs; no covariance coverage',
        'inference':'pilot on one opened geometry; no model selection, validation, coverage calibration or scientific promotion'},
    'promotion':False}
NEW_SOURCES=('scripts/run_neighbor_intervention.py','scripts/neighbor_intervention_inputs.py',
    'scripts/neighbor_epoch_model.py','scripts/constrained_linear_profile.py','scripts/independent_scene_control.py',
    'scripts/source_ramp_noise.py','scripts/audit_native_gain.py',
    'tests/test_neighbor_intervention_inputs.py','tests/test_neighbor_epoch_model.py',
    'tests/test_constrained_linear_profile.py','tests/test_independent_scene_control.py',
    'tests/test_neighbor_intervention_study.py','docs/NEIGHBOR_INTERVENTION_PROTOCOL.md')


def inventory():
    inherited=legacy.hashes()
    inherited['sources'].update({p:legacy.lab.digest(ROOT/p) for p in NEW_SOURCES})
    for p in (gain_paths.GAIN,gain_paths.LOOKUP):
        inherited['raw'][legacy.relative(p)]={'sha256':legacy.lab.digest(p),'bytes':p.stat().st_size}
    return inherited


def create_design():
    if DESIGN.exists():raise RuntimeError('design exists; refusing overwrite')
    data={'rules':RULES,**inventory(),'qualification':'opened data; legacy spectral archive in inherited inventory is context, not a flux constraint'}
    DESIGN.parent.mkdir(parents=True,exist_ok=True)
    with DESIGN.open('xb') as stream:stream.write(legacy.encoded(data))
    return data


def verify_design():
    design=json.loads(DESIGN.read_text(encoding='utf-8'))
    if design['rules']!=legacy.jsonable(RULES) or any(design.get(k)!=v for k,v in inventory().items()):
        raise RuntimeError('design/source/input mismatch')
    for p in (*design['sources'],*design['opened_products'],legacy.relative(DESIGN)):
        blob=subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT,stderr=subprocess.DEVNULL)
        if sha256(blob).hexdigest()!=legacy.lab.digest(ROOT/p):raise RuntimeError('uncommitted locked input: '+p)
    return design


def expected_keys():
    real={('real',c,v['id'],e) for c in RULES['configurations'] for v in VARIANTS for e in ('before','after')}
    simulated={('control',c['id'],str(d),v,e) for c in CASES for d in range(RULES['controls']['draws_per_case'])
               for v in CONTROL_VARIANTS for e in ('before','after')}
    return real|simulated


def record_key(row):
    if row['section']=='real':return ('real',row['configuration'],row['variant'],row['epoch'])
    if row['section']!='control':raise RuntimeError('unknown record section')
    return ('control',row['case'],str(row['draw']),row['variant'],row['epoch'])


def save(report):
    expected=expected_keys();keys=[record_key(r) for r in report['records']]
    if len(set(keys))!=len(keys) or not set(keys)<=expected:raise RuntimeError('duplicate or unknown attempt')
    for r in report['records']:
        if r['status'] not in ('fit_completed','fit_failed','preparation_failed') or (r['status']!='fit_completed' and not r.get('error')):
            raise RuntimeError('unknown terminal status or missing failure reason')
        if r['record_sha256']!=sha256(legacy.encoded({k:v for k,v in r.items() if k!='record_sha256'})).hexdigest():
            raise RuntimeError('record checksum mismatch')
    report['completed']=set(keys)==expected
    report['counts']={'planned':len(expected),'recorded':len(keys),
        'fit_completed':sum(r['status']=='fit_completed' for r in report['records']),
        'failed':sum(r['status']!='fit_completed' for r in report['records'])}
    atomic(OUTPUT,legacy.jsonable(report))


def descriptors(items):
    return [{**item['metadata'],'data_mjysr':item['data'].tolist(),'error_mjysr':item['error'].tolist(),
             'background_design':item['background_design'].tolist(),'neighbor_design_per_jy':item['neighbor_design'].tolist(),
             'neighbor_unit':item['neighbor_unit'],'neighbor_ids':item['neighbor_ids']} for item in items]


def attempt(report, row, items, error=None):
    if any(record_key(r)==record_key(row) for r in report['records']):return
    started=time.monotonic();stage='preparation'
    row['data_role']='measured IMAGE-ZODI-scalar' if row['section']=='real' else 'synthetic Gaussian PSF + ideal source Poisson + diagonal Gaussian background; original image supplies geometry/variance only'
    try:
        if error:raise ValueError(error)
        if not items or [x['obs_id'] for x in items]!=row['obs_ids']:
            raise ValueError('prepared frame identities/order differ from planned epoch')
        row['samples']=descriptors(items);stage='fit'
        variant=next(v for v in VARIANTS if v['id']==row['variant'])
        row['fit']=legacy.jsonable(model.fit_epoch(adapter.model_samples(items),RULES['anchor'],data_unit='MJy/sr',
            nonnegative_neighbors=variant['nonnegative_neighbors'],max_irls_iterations=RULES['max_irls_iterations']))
        if [x['obs_id'] for x in row['fit']['frames']]!=row['obs_ids']:
            raise ValueError('fit frame identities/order differ from planned epoch')
        row['status']='fit_completed'
    except Exception as exc:
        row.update(status='fit_failed' if stage=='fit' else 'preparation_failed',failure_stage=stage,
                   error=type(exc).__name__+': '+str(exc),start_reports=legacy.jsonable(getattr(exc,'start_reports',[])))
    row['elapsed_seconds']=time.monotonic()-started
    row['record_sha256']=sha256(legacy.encoded(row)).hexdigest();report['records'].append(row);save(report)
    print('CHECKPOINT',record_key(row),row['status'],round(row['elapsed_seconds'],2),flush=True)


def prepare_configuration(frames,label):
    groups,catalog,xy,_=inputs.configuration(frames,label)
    prepared=[];errors=[]
    for group in groups:
        try:prepared.append(inputs.prepared_samples(group,catalog,xy,np.asarray(RULES['anchor'])));errors.append(None)
        except Exception as exc:prepared.append([]);errors.append(type(exc).__name__+': '+str(exc))
    return groups,prepared,errors


def load_gain():
    with fits.open(gain_paths.GAIN,memmap=False) as h:
        return gain_binding.validate_calibration(h,legacy.lab.digest(gain_paths.GAIN),gain_paths.GAIN.stat().st_size,
                                                gain_paths.LOOKUP.read_bytes()).copy()


def control_geometry(original_prepared,semantics,gain):
    if not original_prepared or len(original_prepared)!=len(semantics):
        raise ValueError('control geometry frame count mismatch')
    result=[]
    for old,item in zip(original_prepared,semantics):
        if old['obs_id']!=item['obs_id']:raise ValueError('control geometry frame identity/order mismatch')
        sample=old['sample'];frame=sample['frame'];x,y=sample['x'],sample['y']
        if (not np.array_equal(x,item['metadata']['x']) or not np.array_equal(y,item['metadata']['y'])
                or len(item['data'])!=len(x) or len(item['error'])!=len(x)):
            raise ValueError('control geometry pixel identity/order mismatch')
        areas=[]
        for px,py in zip(x,y):
            value=wcs_pixel_area(frame['wcs'],[px,py],provenance=item['obs_id']+'|control pixel')
            if not value.supported:raise ValueError('control pixel area refinement failure')
            areas.append(value.solid_angle.to_value(u.sr))
        dx,dy=gain_binding.detector_indices(frame['image_header'],frame['primary_header'],frame['record']['collection'],x,y,frame['data'].shape)
        gains=gain_binding.bind_values(gain,dx,dy)
        result.append({'obs_id':item['obs_id'],'frame':frame,'x':x,'y':y,'omega':np.asarray(areas)*u.sr,'gain':gains,
                       'background':sample['background'],'error':old['error'],
                       'neighbors':item['metadata']['neighbors']})
    return result


def realize(geometries,semantics,case,case_index,draw,epoch_index):
    if not geometries or len(geometries)!=len(semantics):raise ValueError('realization frame count mismatch')
    if [g['obs_id'] for g in geometries]!=[s['obs_id'] for s in semantics]:raise ValueError('realization frame identity/order mismatch')
    truth=np.asarray(RULES['controls']['before_position'])+epoch_index*np.asarray(RULES['controls']['displacement_sky_px'])
    output=[];metadata=[]
    for index,(geo,item) in enumerate(zip(geometries,semantics)):
        target=inputs.native_position(geo['frame'],truth)
        sources=[{'native_xy':target,'flux':case['target_flux_jy']*u.Jy,'sigma_xy':RULES['controls']['target_sigma_xy_native']}]
        sources.extend({'native_xy':n['native_xy'],'flux':(.00015/(1+i))*u.Jy,
                        'sigma_xy':RULES['controls']['neighbor_sigma_xy_native']} for i,n in enumerate(geo['neighbors']))
        scene=control.expected_scene(sources,geo['x'],geo['y'],geo['omega'])
        b=geo['background'];background=b@np.asarray(RULES['controls']['background_plane_coefficients_mjysr'])
        if case['background']=='quadratic':background+=np.column_stack((b[:,1]**2,b[:,1]*b[:,2],b[:,2]**2))@np.asarray(RULES['controls']['quadratic_coefficients_mjysr'])
        seed=[RULES['controls']['seed_prefix'],case_index,draw,epoch_index,index]
        rng=np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed)))
        realized=control.draw_scene(scene['expected_source'],background*(u.MJy/u.sr),geo['error']*(u.MJy/u.sr),
            geo['gain'],geo['frame']['image_header'],rng,gain_provenance={'source':gain_paths.URL,'sha256':gain_binding.GAIN_SHA256,
                'orientation':'conditional public R6 source binding, not exact private patch proof'},
            source_provenance={'source':'locked independent analytic Gaussian scene','case':case['id'],'draw':draw,'seed':seed})
        data=realized['data'].to_value(u.MJy/u.sr);error=realized['error'].to_value(u.MJy/u.sr)
        output.append({**item,'data':data,'error':error})
        metadata.append({'obs_id':item['obs_id'],'seed':seed,'per_source':scene['per_source'],'provenance':realized['provenance'],
            'expected_source_mjysr':scene['expected_source'].value.tolist(),'background_mjysr':background.tolist(),
            'gain_mjysr_per_electron_rate':geo['gain'].to_value(control.GAIN).tolist(),
            'pixel_omega_sr':geo['omega'].value.tolist(),'source_noise_mjysr':realized['source_noise'].value.tolist(),
            'added_variance_mjysr2':realized['added_variance'].value.tolist()})
    return output,{'truth_position_sky_px':truth.tolist(),'frames':metadata,
                   'realization_sha256':sha256(legacy.encoded([{'obs_id':x['obs_id'],'data':x['data'],'error':x['error']} for x in output])).hexdigest()}


def verify_checkpoint(report,design,runtime,design_hash):
    if (report['protocol_sha256']!=design_hash or report['runtime']!=runtime
            or report['rules']!=legacy.jsonable(RULES) or report['source_hashes']!=design['sources']
            or report['input_hashes']!=design['raw'] or report['opened_products']!=design['opened_products']):
        raise RuntimeError('checkpoint protocol/runtime/provenance mismatch')
    verify_frozen_commit(report['protocol_commit'],design,design_hash)


def verify_frozen_commit(commit,design,design_hash):
    if not isinstance(commit,str) or len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):
        raise RuntimeError('invalid frozen commit')
    sources={**design['sources'],**design['opened_products'],legacy.relative(DESIGN):design_hash}
    for path,digest in sources.items():
        blob=subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT,stderr=subprocess.DEVNULL)
        if sha256(blob).hexdigest()!=digest:raise RuntimeError('frozen commit bytes mismatch: '+path)


def run(sections,configurations,variant_ids):
    design=verify_design();runtime=execution_runtime();design_hash=legacy.lab.digest(DESIGN)
    if OUTPUT.exists():
        report=json.loads(OUTPUT.read_text(encoding='utf-8'))
        verify_checkpoint(report,design,runtime,design_hash)
        if report['completed']:raise RuntimeError('study completed; refusing overwrite')
        save(report)
    else:report={'rules':RULES,'protocol_sha256':design_hash,'protocol_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_hashes':design['sources'],'input_hashes':design['raw'],'opened_products':design['opened_products'],
        'runtime':runtime,'started_at_utc':datetime.now(timezone.utc).isoformat(),'records':[]}
    frames,_=inputs.read_verified_frames()
    cache={}
    for config in set(configurations)|({'strict'} if 'controls' in sections else set()):
        try:cache[config]=(*prepare_configuration(frames,config),None)
        except Exception as exc:cache[config]=([[],[]],[[],[]],[None,None],type(exc).__name__+': '+str(exc))
    if 'real' in sections:
        for config in configurations:
            groups,prepared,errors,config_error=cache[config]
            for v in VARIANTS:
                if v['id'] not in variant_ids:continue
                for epoch_index,epoch in enumerate(('before','after')):
                    row={'section':'real','configuration':config,'variant':v['id'],'epoch':epoch,
                         'obs_ids':[f['record']['obs_id'] for f in groups[epoch_index]]}
                    if any(record_key(r)==record_key(row) for r in report['records']):continue
                    try:
                        if config_error or errors[epoch_index]:raise ValueError(config_error or errors[epoch_index])
                        items=adapter.prepare_semantic(prepared[epoch_index],RULES['anchor'],background_order=v['background_order'],epsf_kind=v['epsf_kind'])
                        error=None
                    except Exception as exc:items=[];error=type(exc).__name__+': '+str(exc)
                    attempt(report,row,items,error)
    if 'controls' in sections:
        groups,prepared,errors,config_error=cache['strict'];base=[];geometries=[];prep_errors=[]
        try:gain=load_gain();gain_error=None
        except Exception as exc:gain=None;gain_error=type(exc).__name__+': '+str(exc)
        for epoch_index in range(2):
            try:
                if config_error or errors[epoch_index] or gain_error:raise ValueError(config_error or errors[epoch_index] or gain_error)
                items=adapter.prepare_semantic(prepared[epoch_index],RULES['anchor'],background_order=1,epsf_kind='nearest')
                base.append(items);geometries.append(control_geometry(prepared[epoch_index],items,gain));prep_errors.append(None)
            except Exception as exc:base.append([]);geometries.append([]);prep_errors.append(type(exc).__name__+': '+str(exc))
        for case_index,case in enumerate(CASES):
            for draw in range(RULES['controls']['draws_per_case']):
                for epoch_index,epoch in enumerate(('before','after')):
                    pending=[v for v in CONTROL_VARIANTS if v in variant_ids and not any(record_key(r)==('control',case['id'],str(draw),v,epoch) for r in report['records'])]
                    if not pending:continue
                    try:
                        if prep_errors[epoch_index]:raise ValueError(prep_errors[epoch_index])
                        items,metadata=realize(geometries[epoch_index],base[epoch_index],case,case_index,draw,epoch_index);error=None
                    except Exception as exc:items=[];metadata={};error=type(exc).__name__+': '+str(exc)
                    for variant in pending:
                        same_draw=[r for r in report['records'] if r['section']=='control' and
                            (r['case'],r['draw'],r['epoch'])==(case['id'],draw,epoch) and r.get('control',{}).get('realization_sha256')]
                        if metadata and any(r['control']['realization_sha256']!=metadata['realization_sha256'] for r in same_draw):
                            raise RuntimeError('paired control realization differs on resume')
                        row={'section':'control','case':case['id'],'draw':draw,'variant':variant,'epoch':epoch,
                             'configuration':'strict','control':metadata,'obs_ids':[f['record']['obs_id'] for f in groups[epoch_index]]}
                        attempt(report,row,items,error)
    save(report);print('COUNTS',report['counts'],'completed',report['completed'],flush=True)


def execution_runtime():
    runtime=legacy.execution_runtime()
    actual={key:os.environ.get(key) for key in THREAD_ENV}
    if actual!=RULES['thread_environment_request']:raise RuntimeError('run in fresh CLI with declared single-thread environment')
    return {**runtime,'thread_environment':actual,
            'thread_qualification':'environment requests recorded before CLI imports; not independent verification of every backend thread'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--design',action='store_true');p.add_argument('--run',action='store_true')
    p.add_argument('--sections',nargs='+',choices=('real','controls'),default=['real','controls'])
    p.add_argument('--configurations',nargs='+',choices=RULES['configurations'],default=RULES['configurations'])
    p.add_argument('--variants',nargs='+',choices=[v['id'] for v in VARIANTS],default=[v['id'] for v in VARIANTS])
    a=p.parse_args()
    if a.design==a.run:p.error('choose --design or --run')
    if a.design:create_design();print('DESIGN',legacy.relative(DESIGN),legacy.lab.digest(DESIGN),flush=True)
    else:
        OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        with locked(OUTPUT.parent,name=OUTPUT.name+'.lock'):run(a.sections,a.configurations,a.variants)


if __name__=='__main__':main()
