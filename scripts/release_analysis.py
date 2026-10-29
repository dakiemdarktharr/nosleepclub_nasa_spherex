"""Locked CatWISE/ePSF experiment on 30 previously unopened spatial patches."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
from astropy.table import Table
from scipy.ndimage import spline_filter, map_coordinates
from . import gaia_motion as gaia
from . import joint_motion as joint

motion=gaia.motion
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/wise0855/release-study'
OUT=ROOT/'web/data/release'
RULES={'version':'0.5.0','w2_magnitude_max':16.,'w2_snr_min':10.,'w2_chi2_max':2.,
       'artifact_flags':'00','proper_motion_max_arcsec_yr':.3,'position_error_2026_max_arcsec':1.,
       'gaia_match_arcsec':2.,'catwise_epoch_mjd':57170.,'neighbour_radius_px':11.,
       'patch_count':30,'patch_separation_px':20.,'old_patch_exclusion_px':20.,
       'minimum_native_stamp_pixels':100,'flux_scales':[.5,1.],
       'truth_displacements_px':[[0.,0.],[.6,.05]],'truth_psfs':['nearest','bilinear'],
       'models':['single_nearest','ir_nearest','ir_bilinear'],'seed':20261031,
       'bootstrap_draws':128,'release_gate':'both flux scales AND both truth PSFs AND both spectra: paired RMSE lower, no extra failed/boundary fits; no post-hoc model selection'}


def table_rows(path):
    table=Table.read(path,format='votable',use_names_over_ids=True)
    return [{k:None if np.ma.is_masked(r[k]) else r[k].item() if isinstance(r[k],np.generic) else r[k]
             for k in table.colnames} for r in table]


def corrected_position(row, correction, mjd):
    """Official additive tile corrections; PMRA is angular alpha*cos(delta)."""
    dec=float(row['dec_pm']);cosdec=np.cos(np.deg2rad(dec))
    dt=(mjd-RULES['catwise_epoch_mjd'])/365.25
    return [float(row['ra_pm'])+float(correction['offsetra_ta'])/cosdec+
            (float(row['pmra'])+float(correction['offsetpmra']))*dt/(3600*cosdec),
            dec+float(correction['offsetdec'])+(float(row['pmdec'])+float(correction['offsetpmdec']))*dt/3600]


def build_catalog(manifest):
    rows=table_rows(RAW/'catwise.xml');identifiers={r['source_name']:r['source_id'] for r in table_rows(RAW/'catwise-identifiers.xml')}
    corrections={str(r['tile']):dict(r) for r in Table.read(RAW/'catwise-corrections.tbl',format='ascii.ipac')}
    gaia_rows=[r for r in gaia.catalog_rows(manifest) if gaia.catalog_quality(r) is None]
    gxy=np.array([gaia.gaia_xy(r,RULES['catwise_epoch_mjd']) for r in gaia_rows])
    selected=[];rejections={}
    for r in rows:
        reason=None
        required=['ra_pm','dec_pm','pmra','pmdec','sigra_pm','sigdec_pm','sigpmra','sigpmdec','w2mpro_pm','w2snr_pm','w2rchi2_pm']
        if any(r.get(k) is None or not np.isfinite(r[k]) for k in required):reason='missing_value'
        elif r['w2mpro_pm']>RULES['w2_magnitude_max'] or r['w2snr_pm']<RULES['w2_snr_min']:reason='faint_ir'
        elif r['ab_flags']!=RULES['artifact_flags'] or r['w2rchi2_pm']>RULES['w2_chi2_max']:reason='artifact_or_poor_fit'
        c=corrections.get(str(identifiers[r['source_name']])[:8])
        if c is None:reason='missing_tile_correction'
        if reason is None:
            pm=np.hypot(r['pmra']+c['offsetpmra'],r['pmdec']+c['offsetpmdec'])
            if pm>RULES['proper_motion_max_arcsec_yr']:reason='large_motion'
        if reason is not None:rejections[reason]=rejections.get(reason,0)+1;continue
        sky=corrected_position(r,c,RULES['catwise_epoch_mjd'])
        xy=np.array(motion.WCS.world_to_pixel_values(*sky));distance=np.linalg.norm(gxy-xy,axis=1)*gaia.base.SCALE
        j=int(np.argmin(distance));match=gaia_rows[j] if distance[j]<=RULES['gaia_match_arcsec'] else None
        dt=(61200-RULES['catwise_epoch_mjd'])/365.25
        error=float(np.sqrt(max(r['sigra_pm']**2+dt**2*r['sigpmra']**2,r['sigdec_pm']**2+dt**2*r['sigpmdec']**2)+.1**2))
        if match is None and error>RULES['position_error_2026_max_arcsec']:
            rejections['uncertain_ir_position']=rejections.get('uncertain_ir_position',0)+1;continue
        selected.append({'id':r['source_name'],'row':r,'tile':str(c['tile']),
                         'correction':{k:float(c[k]) for k in ['offsetra_ta','offsetdec','offsetpmra','offsetpmdec']},
                         'gaia':match,'gaia_match_arcsec':float(distance[j]) if match else None,
                         'catalog_position_error_2026_arcsec':error})
    # Multiple IR entries assigned to one Gaia star would create duplicate nuisance PSFs.
    used=set();unique=[]
    for s in sorted(selected,key=lambda s:s['row']['w2mpro_pm']):
        sid=s['gaia']['source_id'] if s['gaia'] else s['id']
        if sid in used:rejections['duplicate_gaia_match']=rejections.get('duplicate_gaia_match',0)+1;continue
        used.add(sid);unique.append(s)
    return unique,{'queried':len(rows),'selected':len(unique),'gaia_positions':sum(s['gaia'] is not None for s in unique),'rejections':rejections}


def ir_positions(catalog,mjd):
    sky=[];result=[]
    for s in catalog:
        if s['gaia']:result.append(gaia.gaia_xy(s['gaia'],mjd))
        else:
            position=corrected_position(s['row'],s['correction'],mjd)
            result.append(motion.WCS.world_to_pixel_values(*position))
    return np.array(result)


def epsf(frame,x,y,kind):
    if kind=='nearest':return motion.epsf_for(frame,x,y)
    gx,gy=frame['parent_wcs'].pixel_to_world_values(x,y);table=frame['epsf_table']
    xs=np.unique(table['XCENTER']);ys=np.unique(table['YCENTER'])
    def bracket(values,v):
        i=int(np.clip(np.searchsorted(values,v)-1,0,len(values)-2));a,b=values[i:i+2]
        fraction=float(np.clip((v-a)/(b-a),0,1));return [(a,1-fraction),(b,fraction)]
    value=np.zeros(table['EPSF'][0].shape)
    for xx,wx in bracket(xs,gx):
        for yy,wy in bracket(ys,gy):
            i=int(np.flatnonzero((table['XCENTER']==xx)&(table['YCENTER']==yy))[0])
            p=np.asarray(table['EPSF'][i],float);value+=wx*wy*p/p.sum()
    return spline_filter(value*frame['epsf_oversampling']**2,order=3),-1


def make_samples(frames,catalog,positions,anchor,model):
    samples=[];kind='bilinear' if model=='ir_bilinear' else 'nearest'
    for f in frames:
        s=motion.native_stamp(f,anchor);x,y=s['native_center'];s['epsf'],s['zone']=epsf(f,x,y,kind)
        columns=[s['background']];ids=[]
        if model!='single_nearest':
            xy=positions[f['record']['obs_id']]
            for i in np.flatnonzero(np.linalg.norm(xy-anchor,axis=1)<=RULES['neighbour_radius_px']):
                px,py=f['wcs'].world_to_pixel_values(*motion.WCS.pixel_to_world_values(*(xy[i]+f['offset'])))
                p,z=epsf(f,float(px),float(py),kind)
                n={**s,'native_center':np.array([px,py]),'anchor':xy[i],'epsf':p}
                rendered=motion.stamp_model(n,xy[i])[:,0]
                if np.linalg.norm(rendered/s['error'])>1e-6:columns.append(rendered[:,None]);ids.append(catalog[i]['id'])
        nuisance=np.column_stack(columns)/s['error'][:,None]
        u,v,_=np.linalg.svd(nuisance,full_matrices=False);rank=int(np.sum(v>v[0]*joint.CONFIG['svd_relative_cut']))
        samples.append({**s,'q':u[:,:rank],'rank':rank,'neighbour_ids':ids})
    return samples


def render(frame,position,amplitude,kind):
    p,q=frame['wcs'].world_to_pixel_values(*motion.WCS.pixel_to_world_values(*(position+frame['offset'])))
    psf,_=epsf(frame,float(p),float(q),kind);over=frame['epsf_oversampling'];center=(np.array(psf.shape)-1)/2
    yy,xx=np.indices(frame['data'].shape,dtype=float)
    return amplitude*map_coordinates(psf,[(yy-q)*over+center[0],(xx-p)*over+center[1]],order=3,mode='constant',cval=0,prefilter=False)


def sources():
    return {p.name:sha256(p.read_bytes()).hexdigest() for p in
            [Path(__file__),ROOT/'scripts/prepare_release_data.py',ROOT/'scripts/joint_motion.py',ROOT/'scripts/gaia_motion.py',ROOT/'scripts/motion_analysis.py',ROOT/'scripts/build_demo.py']}


def lock(frames,manifest):
    if (OUT/'protocol.json').exists():raise RuntimeError('Protocol already locked; do not overwrite after seeing outcomes')
    old=np.array([[17,19],[27,17],[43,19],[46,34],[41,47],[25,47],[14,39],[35,40]]+
                 [[x,y] for y in [-12,64,88] for x in [-12,12,52,76]]+[[31.5,31.5]])
    eligible=[]
    for y in range(-50,117,11):
        for x in range(-50,117,11):
            p=np.array([x,y],float)
            if np.min(np.linalg.norm(old-p,axis=1))<RULES['old_patch_exclusion_px']:continue
            try:
                if all(len(motion.native_stamp(f,p)['data'])>=RULES['minimum_native_stamp_pixels'] for f in frames):eligible.append(p.tolist())
            except ValueError:pass
    # Packing uses only sky geometry and validity masks, never fitted pixels/truth.
    selected=[]
    for attempt in range(1000):
        candidate=np.array(eligible);np.random.default_rng(RULES['seed']+attempt).shuffle(candidate);picked=[]
        for p in candidate:
            if not picked or np.min(np.linalg.norm(np.array(picked)-p,axis=1))>=RULES['patch_separation_px']:picked.append(p.tolist())
        if len(picked)>=RULES['patch_count']:selected=picked[:RULES['patch_count']];break
    if len(selected)!=RULES['patch_count']:raise RuntimeError(f'Cannot pack 30 disjoint patches from {len(eligible)} geometry candidates')
    catalog,screening=build_catalog(manifest)
    discovery=json.loads((RAW/'discovery.json').read_text())
    payload={'locked_at_utc':datetime.now(timezone.utc).isoformat(),'rules':RULES,'positions_px':selected,
             'excluded_old_positions_px':old.tolist(),'catalog_screening':screening,'catalog':catalog,
             'source_sha256':sources(),'discovery':discovery,'calibrations':manifest['calibrations'],
             'qr2_inputs':manifest['records'],'solver':joint.CONFIG,
             'note':'Locked before target fits and before injections on these 30 patches. One field, shared exposures; not 30 independent sky surveys.'}
    gaia.save_json(OUT/'protocol.json',payload)
    print('LOCKED',sha256((OUT/'protocol.json').read_bytes()).hexdigest(),screening,flush=True)


def validate_lock():
    p=json.loads((OUT/'protocol.json').read_text())
    if p['source_sha256']!=sources() or p['rules']!=RULES:raise RuntimeError('Code/rules changed after lock; cannot label new outcomes as pre-registered')
    return p


def run(frames,manifest,spectral):
    protocol=validate_lock();catalog=protocol['catalog'];positions={f['record']['obs_id']:ir_positions(catalog,f['mjd']) for f in frames}
    previous=next(c for c in json.loads((gaia.OUTPUT/'results.json').read_text())['configurations'] if c['spectral_configuration']==spectral)
    index={f['record']['obs_id']:f for f in frames};before=[index[p['before']['obs_id']] for p in previous['spectral_pairs']];after=[index[p['after']['obs_id']] for p in previous['spectral_pairs']]
    refs=json.loads((gaia.CACHE/'references.json').read_text())['references'];gaia.calibrate(before+after,[r for r in refs if r['split']=='training'])
    output={'spectral_configuration':spectral,'models':{},'records':[]}
    for model in RULES['models']:
        a=joint.fit(make_samples(before,catalog,positions,motion.TARGET_ANCHOR,model),motion.TARGET_ANCHOR)
        b=joint.fit(make_samples(after,catalog,positions,motion.TARGET_ANCHOR,model),motion.TARGET_ANCHOR)
        ba=joint.bootstrap(a,RULES['seed']+1);bb=joint.bootstrap(b,RULES['seed']+2)
        delta=gaia.TRANSFORM@(b['position']-a['position']);cov=gaia.TRANSFORM@(a['covariance']+b['covariance'])@gaia.TRANSFORM
        output['models'][model]={'target_before':motion.public_fit(a),'target_after':motion.public_fit(b),'east_arcsec':float(delta[0]),'north_arcsec':float(delta[1]),
             'displacement_arcsec':float(np.linalg.norm(delta)),'noise_radial_arcsec':float(np.sqrt(delta@cov@delta)/np.linalg.norm(delta)),
             'noise_covariance_arcsec2':cov.tolist(),'bootstrap_before':ba,'bootstrap_after':bb}
        print(spectral,model,delta.round(3),flush=True)
    amplitudes={d['obs_id']:d['amplitude'] for side in ['before','after'] for d in previous['target_'+side]['per_frame']}
    for i,anchor in enumerate(np.array(protocol['positions_px'])):
        samples={(model,e):make_samples(fs,catalog,positions,anchor,model) for model in RULES['models'] for e,fs in [(0,before),(1,after)]}
        for truth in RULES['truth_psfs']:
            for flux in RULES['flux_scales']:
                for delta in np.array(RULES['truth_displacements_px']):
                    injections={(e,f['record']['obs_id']):render(f,anchor+e*delta,amplitudes[f['record']['obs_id']]*flux,truth) for e,fs in [(0,before),(1,after)] for f in fs}
                    for model in RULES['models']:
                        fits=[]
                        for e in [0,1]:
                            trial=[{**s,'data':s['data']+injections[e,s['frame']['record']['obs_id']][s['y'].astype(int),s['x'].astype(int)]} for s in samples[model,e]]
                            fits.append(joint.fit(trial,anchor))
                        a,b=fits;error=b['position']-a['position']-delta;cov=a['covariance']+b['covariance'];valid=all(r['success'] and not r['at_boundary'] for r in fits)
                        output['records'].append({'position_index':i,'model':model,'truth_psf':truth,'flux_scale':flux,'truth_delta_px':delta.tolist(),'valid':valid,
                             'error_east_north_arcsec':(gaia.TRANSFORM@error).tolist(),'within_68_ellipse':bool(valid and error@np.linalg.pinv(cov)@error<=2.30)})
        print(spectral,'patch',i+1,'/30',flush=True)
    output['groups']=[]
    for truth in RULES['truth_psfs']:
        for flux in RULES['flux_scales']:
            for model in RULES['models']:
                records=[r for r in output['records'] if r['model']==model and r['truth_psf']==truth and r['flux_scale']==flux];valid=[r for r in records if r['valid']]
                errors=np.array([r['error_east_north_arcsec'] for r in valid])
                baseline=[r for r in output['records'] if r['model']=='single_nearest' and r['truth_psf']==truth and r['flux_scale']==flux]
                pairs=[(r,next(b for b in baseline if b['position_index']==r['position_index'] and b['truth_delta_px']==r['truth_delta_px'])) for r in valid]
                pairs=[(r,b) for r,b in pairs if b['valid']]
                base_rmse=float(np.sqrt(np.mean([np.sum(np.array(b['error_east_north_arcsec'])**2) for r,b in pairs])))
                new_rmse=float(np.sqrt(np.mean([np.sum(np.array(r['error_east_north_arcsec'])**2) for r,b in pairs])))
                output['groups'].append({'model':model,'truth_psf':truth,'flux_scale':flux,'attempted':len(records),'valid':len(valid),
                    'rms_arcsec':float(np.sqrt(np.mean(np.sum(errors**2,axis=1)))),'bias_east_north_arcsec':np.mean(errors,axis=0).tolist(),
                    'within_68_ellipse':sum(r['within_68_ellipse'] for r in records),'paired_valid':len(pairs),'paired_baseline_rms_arcsec':base_rmse,'paired_model_rms_arcsec':new_rmse,
                    'paired_improvement_percent':100*(1-new_rmse/base_rmse)})
    gaia.save_json(OUT/(spectral+'.json'),{'analysis_version':RULES['version'],'protocol_sha256':sha256((OUT/'protocol.json').read_bytes()).hexdigest(),'source_sha256':sources(),'result':output,
       'limits':['QR3 not available at queried position in SIA and TAP; QR2-only image experiment.',
       '30 disjoint patches in one field share the same exposures; paired injections and spectra are correlated.',
       'No extra shot noise; crossed nearest/bilinear truth PSFs are a limited mismatch test, not an independent physical PSF calibration.',
       'Reported target errors cover conditional noise only; frame, neighbour-position, chromatic PSF and detector correlation uncertainties remain.',
       'CatWISE-only positions use corrected linear motion without parallax; Gaia propagation is preferred on quality matches. No flux or motion prior on target.']})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--lock',action='store_true');parser.add_argument('--configuration',choices=['broad','strict']);args=parser.parse_args()
    frames,manifest=gaia.load_frames()
    if args.lock:lock(frames,manifest)
    elif args.configuration:run(frames,manifest,args.configuration)
    else:parser.error('Choose --lock or --configuration')


if __name__=='__main__':main()
