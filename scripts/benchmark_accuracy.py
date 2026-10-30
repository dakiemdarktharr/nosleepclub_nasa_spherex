"""Locked external-field diagnostics of the current native-pixel centroid fitter.

No training, tuning or replacement of the published WISE 0855 measurement.
Gaia controls test local astrometry; injections test recovery at known positions.
Neither is a blind moving-object detection benchmark.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from astropy.io import fits
from astropy.coordinates import SkyCoord,Distance
from astropy.time import Time
import astropy.units as u
import numpy as np
from scipy.ndimage import map_coordinates
from scipy.optimize import linear_sum_assignment

from . import gaia_motion as gaia
from . import motion_analysis as motion

base=motion.base
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/benchmark'
OUT=ROOT/'web/data/benchmark'
PROTOCOL=OUT/'protocol.json'
MODULES=['benchmark_accuracy.py','prepare_benchmark_data.py','gaia_motion.py','motion_analysis.py','build_demo.py']
RULES={'version':'0.6.0','configurations':{'strict':.20,'broad':.50},'max_pairs':10,
       'wave_range_um':[4.55,4.94],'max_candidates':32,'split':'sha256(source_id) sorted; every third is heldout, before fitting',
       'positions_px':[[5.5,5.5],[57.5,5.5],[5.5,57.5],[57.5,57.5]],'injection_snr_per_frame':[2.,4.],
       'motions_px':[[0.,0.],[.6,.05]],'minimum_pixels_per_stamp':100,
       'recovery_tolerance_px':1.,'ellipse_68_threshold':2.30,'ellipse_9973_threshold':11.829,
       'target_bound_px':2.5,'reference_rules':gaia.RULES,
       'covariance':'formal centroid + independent frame translation covariance; Gaia differential covariance for real controls; no heldout recalibration',
       'injection_psf':'same official nearest-zone ePSF as fitter; no extra noise or shot noise added',
       'positive_control':{'field':'barnard','minimum_pm_mas_yr':5000,'selection':'highest Gaia proper motion, before any image fit',
           'radial_velocity_km_s':-110.11,'rv_source':'https://simbad.cds.unistra.fr/simbad/sim-basic?Ident=Barnard%27s+star',
           'propagation':'Astropy space motion with perspective acceleration, first-order observer parallax; RV uncertainty omitted'},
       'scope':'three new sky fields; QR2 only; known-position local fitting; not blind detection or full uncertainty calibration'}


def digest(path):return sha256(path.read_bytes()).hexdigest()


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def context(field):
    center=(field['ra'],field['dec'])
    motion.WCS=base.grid_wcs(center=center)
    gaia.WIDE_WCS=base.grid_wcs(gaia.WIDE_SHAPE,center=center)
    # Adapter only: original source files remain byte-for-byte frozen.
    base.expected_position=lambda mjd:center


def positive_xy(source,mjd):
    c=SkyCoord(ra=source['ra']*u.deg,dec=source['dec']*u.deg,distance=Distance(parallax=source['parallax']*u.mas),
        pm_ra_cosdec=source['pmra']*u.mas/u.yr,pm_dec=source['pmdec']*u.mas/u.yr,
        radial_velocity=RULES['positive_control']['radial_velocity_km_s']*u.km/u.s,
        obstime=Time(source['ref_epoch'],format='jyear',scale='tcb')).apply_space_motion(Time(mjd,format='mjd').tcb)
    ra=c.ra.rad;dec=c.dec.rad;earth=gaia.earth_position(float(mjd))
    east=np.array([-np.sin(ra),np.cos(ra),0]);north=np.array([-np.cos(ra)*np.sin(dec),-np.sin(ra)*np.sin(dec),np.cos(dec)])
    # plx in degrees: distance[pc]^-1 arcsec / 3600.
    parallax_deg=1/c.distance.to_value(u.pc)/3600
    return np.array(motion.WCS.world_to_pixel_values(c.ra.deg-parallax_deg*(earth@east)/np.cos(dec),c.dec.deg-parallax_deg*(earth@north)))


def load(field):
    manifest=json.loads((RAW/field/'manifest.json').read_text());context(manifest['field'])
    with fits.open(ROOT/manifest['calibrations']['spectral_wcs']['path']) as h:
        cwave=np.array(h['CWAVE'].data,float);cband=np.array(h['CBAND'].data,float)
    with fits.open(ROOT/manifest['calibrations']['epsf']['path']) as h:
        table=np.array(h['EPSF'].data);over=float(h['EPSF'].header['OVSMPX'])
    frames=[];audit=[]
    for r in manifest['records']:
        if r['status']!='downloaded':audit.append({'obs_id':r['obs_id'],'reason':'download_failed'});continue
        if digest(ROOT/r['path'])!=r['sha256']:raise RuntimeError('FITS checksum mismatch')
        try:
            f=base.read_frame(r)
            with fits.open(ROOT/r['path']) as h:parent=base.alternate_wcs(h['IMAGE'].header,h,'A')
            yy,xx=np.indices(f['data'].shape,dtype=float);gx,gy=parent.pixel_to_world_values(xx,yy)
            cw=map_coordinates(cwave,[gy,gx],order=1,mode='constant',cval=np.nan)
            cb=map_coordinates(cband,[gy,gx],order=1,mode='constant',cval=np.nan)
            tx,ty=f['wcs'].world_to_pixel_values(manifest['field']['ra'],manifest['field']['dec'])
            wave=float(map_coordinates(cw,[[ty],[tx]],order=1,mode='constant',cval=np.nan)[0])
            bandwidth=float(map_coordinates(cb,[[ty],[tx]],order=1,mode='constant',cval=np.nan)[0])
            f.update(parent_wcs=parent,epsf_table=table,epsf_oversampling=over,cwave_map=cw,cband_map=cb,
                wavelength=wave,bandwidth=bandwidth,offset=np.zeros(2),offset_cov=np.zeros((2,2)))
            if not np.isfinite(wave+bandwidth) or bandwidth<=0:raise ValueError('invalid wavelength at field center')
            frames.append(f)
        except (ValueError,IndexError) as exc:audit.append({'obs_id':r['obs_id'],'reason':str(exc)})
    return manifest,frames,audit


def pairs(frames,tolerance):
    epochs=[[f for f in frames if f['record']['epoch']==epoch and RULES['wave_range_um'][0]<=f['wavelength']<=RULES['wave_range_um'][1]] for epoch in ['before','after']]
    if not all(epochs):return []
    mismatch=np.array([[abs(a['wavelength']-b['wavelength'])/((a['bandwidth']+b['bandwidth'])/2) for b in epochs[1]] for a in epochs[0]])
    ii,jj=linear_sum_assignment(np.where(mismatch<=tolerance,mismatch,1e6))
    result=[(epochs[0][i],epochs[1][j],float(mismatch[i,j])) for i,j in zip(ii,jj) if mismatch[i,j]<=tolerance]
    result=sorted(result,key=lambda p:(p[2],p[0]['record']['obs_id'],p[1]['record']['obs_id']))[:RULES['max_pairs']]
    return sorted(result,key=lambda p:p[0]['wavelength'])


def lock():
    if PROTOCOL.exists():raise RuntimeError('Protocol exists; cannot overwrite an opened benchmark')
    OUT.mkdir(parents=True,exist_ok=True)
    fields=[]
    for field in json.loads((RAW/'coverage.json').read_text()):
        ident=field['id'];manifest,frames,audit=load(ident)
        configurations={name:pairs(frames,tol) for name,tol in RULES['configurations'].items()}
        used={f['record']['obs_id'] for group in configurations.values() for p in group for f in p[:2]}
        selected=[f for f in frames if f['record']['obs_id'] in used]
        if selected:candidates,selection_audit,image=gaia.candidate_references(selected,manifest)
        else:candidates=[];selection_audit=[];image=None
        # Spatial round-robin is based on pre-fit image brightness only.
        quadrants=[[] for _ in range(4)]
        for c in candidates:
            x,y=np.array(c['anchor'])-motion.TARGET_ANCHOR;quadrants[int(x>=0)+2*int(y>=0)].append(c)
        chosen=[]
        while len(chosen)<RULES['max_candidates'] and any(quadrants):
            for group in quadrants:
                if group and len(chosen)<RULES['max_candidates']:chosen.append(group.pop(0))
        chosen.sort(key=lambda r:sha256(r['catalog']['source_id'].encode()).hexdigest())
        for i,c in enumerate(chosen):c['split']='heldout' if i%3==0 else 'training'
        injections=[]
        for anchor in RULES['positions_px']:
            counts=[]
            for f in selected:
                try:counts.append(len(motion.native_stamp(f,np.array(anchor))['data']))
                except ValueError:counts.append(0)
            injections.append({'anchor':anchor,'valid_pixels':counts,'eligible':bool(counts and min(counts)>=RULES['minimum_pixels_per_stamp'])})
        item={'field':field,'manifest_path':(RAW/ident/'manifest.json').relative_to(ROOT).as_posix(),
            'manifest_sha256':digest(RAW/ident/'manifest.json'),'input_manifest':manifest,'selected_obs_ids':sorted(used),
            'configurations':{name:[{'before':a['record']['obs_id'],'after':b['record']['obs_id'],'mismatch':v,'wavelength_um':[a['wavelength'],b['wavelength']]} for a,b,v in group] for name,group in configurations.items()},
            'references':chosen,'selection_audit':selection_audit,'load_audit':audit,'injection_positions':injections}
        if ident==RULES['positive_control']['field']:
            positive=[s for s in gaia.catalog_rows(manifest) if s.get('pmra') is not None and s.get('pmdec') is not None and s.get('parallax') is not None and s['parallax']>0 and np.hypot(s['pmra'],s['pmdec'])>RULES['positive_control']['minimum_pm_mas_yr']]
            item['positive_control']=max(positive,key=lambda s:np.hypot(s['pmra'],s['pmdec'])) if positive else None
        fields.append(item)
        if image is not None:
            lo,hi=np.nanpercentile(image,[5,99.5]);base.png_image(image,OUT/(ident+'.png'),lo,hi)
        print('LOCK',ident,{k:len(v) for k,v in configurations.items()},'references',len(chosen),'injections',sum(p['eligible'] for p in injections),flush=True)
    save(PROTOCOL,{'rules':RULES,'source_hashes':{name:digest(ROOT/'scripts'/name) for name in MODULES},'fields':fields})
    print('Protocol SHA256',digest(PROTOCOL),flush=True)


def measure_training(frames,references):
    measured=[]
    for reference in references:
        source=reference['catalog'];entries=[]
        for f in frames:
            anchor=gaia.gaia_xy(source,f['mjd']);reason=None;fit=None
            px,py=f['wcs'].world_to_pixel_values(*motion.WCS.pixel_to_world_values(*anchor))
            if min(px,py,f['data'].shape[1]-1-px,f['data'].shape[0]-1-py)<7:reason='edge'
            if reason is None:
                try:
                    fit=motion.fit_position([f],anchor,bound=1.3)
                    if not fit['success'] or fit['at_boundary']:reason='fit_boundary_or_failure'
                    elif fit['per_frame'][0]['snr']<gaia.RULES['reference_snr_min']:reason='low_snr'
                    elif fit['reduced_chi2']>gaia.RULES['reference_chi2_max']:reason='poor_psf_fit'
                except (ValueError,np.linalg.LinAlgError) as exc:reason=type(exc).__name__
            entry={'obs_id':f['record']['obs_id'],'epoch':f['record']['epoch'],'expected_px':anchor.tolist(),'rejection':reason}
            if reason is None:
                jac=gaia.gaia_jacobian(source,f['mjd'])
                entry.update(delta_px=(fit['position']-anchor).tolist(),covariance_px2=fit['covariance'].tolist(),
                    gaia_covariance_px2=(jac@gaia.gaia_covariance(source)@jac.T).tolist())
            entries.append(entry)
        eligible=sum(e['rejection'] is None for e in entries)>=np.ceil(gaia.RULES['valid_frame_fraction_min']*len(frames))
        eligible&=all(sum(e['rejection'] is None and e['epoch']==epoch for e in entries)>=3 for epoch in ['before','after'])
        measured.append({**reference,'entries':entries,'eligible':bool(eligible)})
        print('TRAIN',source['source_id'],sum(e['rejection'] is None for e in entries),'/',len(frames),flush=True)
    return measured


def valid_fit(fit):
    return fit['success'] and not fit['at_boundary'] and sum(p['amplitude'] for p in fit['per_frame'])>0


def registration_covariance(frames):
    # Approximation: equal epoch weights, independent frames. Shared catalog/frame
    # correlations and spatial systematics are explicitly outside this diagnostic.
    return sum(f['offset_cov'] for f in frames)/len(frames)**2


def evaluate_pair(before,after,anchors,truth=None,source=None,positive=False):
    a=motion.fit_position(before,np.array(anchors[0]),multistart=True)
    b=motion.fit_position(after,np.array(anchors[1]),multistart=True)
    if source is not None:
        predict=positive_xy if positive else gaia.gaia_xy
        expected=predict(source,b['effective_mjd'])-predict(source,a['effective_mjd'])
        jac=gaia.gaia_jacobian(source,b['effective_mjd'])-gaia.gaia_jacobian(source,a['effective_mjd'])
        catalog_cov=jac@gaia.gaia_covariance(source)@jac.T
    else:expected=np.array(truth);catalog_cov=np.zeros((2,2))
    error=b['position']-a['position']-expected
    covariance=a['covariance']+b['covariance']+registration_covariance(before)+registration_covariance(after)+catalog_cov
    mahal=float(error@np.linalg.pinv(covariance)@error)
    return {'valid':bool(valid_fit(a) and valid_fit(b)),'before':motion.public_fit(a),'after':motion.public_fit(b),
        'measured_east_north_arcsec':(gaia.TRANSFORM@(b['position']-a['position'])).tolist(),
        'expected_east_north_arcsec':(gaia.TRANSFORM@expected).tolist(),
        'expected_delta_px':expected.tolist(),'error_east_north_arcsec':(gaia.TRANSFORM@error).tolist(),
        'error_arcsec':float(np.linalg.norm(error)*base.SCALE),'covariance_arcsec2':(gaia.TRANSFORM@covariance@gaia.TRANSFORM).tolist(),
        'mahalanobis_squared':mahal,'within_68_ellipse':bool(mahal<=RULES['ellipse_68_threshold']),
        'outside_9973_ellipse':bool(mahal>RULES['ellipse_9973_threshold']),
        'within_one_pixel':bool(np.linalg.norm(error)<=RULES['recovery_tolerance_px'])}


def summarize(records):
    valid=[r for r in records if r.get('valid')];errors=np.array([r['error_east_north_arcsec'] for r in valid])
    return {'attempted':len(records),'valid':len(valid),'failed':len(records)-len(valid),
        'rmse_arcsec':float(np.sqrt(np.mean(np.sum(errors**2,axis=1)))) if valid else None,
        'median_error_arcsec':float(np.median(np.linalg.norm(errors,axis=1))) if valid else None,
        'p90_error_arcsec':float(np.percentile(np.linalg.norm(errors,axis=1),90)) if valid else None,
        'bias_east_north_arcsec':errors.mean(axis=0).tolist() if valid else None,
        'within_68_ellipse':sum(r['within_68_ellipse'] for r in valid),
        'outside_9973_ellipse':sum(r['outside_9973_ellipse'] for r in valid),
        'within_one_pixel':sum(r['within_one_pixel'] for r in valid)}


def run():
    protocol=json.loads(PROTOCOL.read_text());protocol_hash=digest(PROTOCOL)
    for name,expected in protocol['source_hashes'].items():
        if digest(ROOT/'scripts'/name)!=expected:raise RuntimeError('Frozen source changed: '+name)
    outputs=[]
    for item in protocol['fields']:
        ident=item['field']['id'];manifest_path=ROOT/item['manifest_path']
        if digest(manifest_path)!=item['manifest_sha256']:raise RuntimeError('Manifest changed')
        manifest,frames,audit=load(ident);index={f['record']['obs_id']:f for f in frames};frames=[index[o] for o in item['selected_obs_ids']]
        for c in manifest['calibrations'].values():
            if digest(ROOT/c['path'])!=c['sha256']:raise RuntimeError('Calibration changed')
        if digest(ROOT/manifest['gaia']['path'])!=manifest['gaia']['sha256']:raise RuntimeError('Gaia checksum mismatch')
        training=measure_training(frames,[r for r in item['references'] if r['split']=='training'])
        eligible=[r for r in training if r['eligible']]
        result={'field':item['field'],'protocol_sha256':protocol_hash,'training':training,'training_eligible':len(eligible),'configurations':[]}
        for config,pair_list in item['configurations'].items():
            before=[index[p['before']] for p in pair_list];after=[index[p['after']] for p in pair_list]
            group={'configuration':config,'pairs':len(pair_list),'real_controls':[],'injections':[]}
            if len(pair_list)<2:group['unavailable_reason']='Fewer than two spectrally matched pairs';result['configurations'].append(group);continue
            try:registrations=gaia.calibrate(before+after,eligible)
            except RuntimeError as exc:group['unavailable_reason']=str(exc);result['configurations'].append(group);continue
            group['registrations']=[{'obs_id':obs,'offset_px':r['offset'].tolist(),'covariance_px2':r['offset_covariance'].tolist(),'source_ids':r['source_ids']} for obs,r in registrations.items()]
            group['epoch_mjd_ranges']=[[min(f['mjd'] for f in fs),max(f['mjd'] for f in fs)] for fs in [before,after]]
            if item.get('positive_control'):
                s=item['positive_control'];record={'source_id':s['source_id'],'name':'Barnard star'}
                try:
                    anchors=[positive_xy(s,float(np.mean([f['mjd'] for f in fs]))) for fs in [before,after]]
                    record.update(evaluate_pair(before,after,anchors,source=s,positive=True))
                except (ValueError,np.linalg.LinAlgError) as exc:record.update(valid=False,reason=str(exc))
                group['positive_control']=record;print(ident,config,'POSITIVE',record,flush=True)
            for r in [v for v in item['references'] if v['split']=='heldout']:
                s=r['catalog'];record={'source_id':s['source_id']}
                try:
                    anchors=[gaia.gaia_xy(s,float(np.mean([f['mjd'] for f in fs]))) for fs in [before,after]]
                    record.update(evaluate_pair(before,after,anchors,source=s))
                except (ValueError,np.linalg.LinAlgError) as exc:record.update(valid=False,reason=str(exc))
                group['real_controls'].append(record)
                print(ident,config,'HELDOUT',s['source_id'],record.get('error_arcsec'),record['valid'],flush=True)
            for patch in item['injection_positions']:
                for snr in RULES['injection_snr_per_frame']:
                    for truth in RULES['motions_px']:
                        record={'anchor':patch['anchor'],'snr_per_frame':snr,'truth_delta_px':truth}
                        if not patch['eligible']:record.update(valid=False,reason='insufficient pixels at locked patch')
                        else:
                            try:
                                injected=[]
                                for fs,delta in [(before,np.zeros(2)),(after,np.array(truth))]:
                                    copy=[]
                                    for f in fs:
                                        p=np.array(patch['anchor'])+delta;s=motion.native_stamp(f,p);design=motion.stamp_model(s,p)/s['error'][:,None]
                                        noise=float(np.sqrt(np.linalg.pinv(design.T@design)[0,0]));amplitude=snr*noise
                                        copy.append({**f,'data':f['data']+motion.render_source(f,p,amplitude)})
                                    injected.append(copy)
                                record.update(evaluate_pair(*injected,[patch['anchor'],patch['anchor']],truth=truth))
                            except (ValueError,np.linalg.LinAlgError) as exc:record.update(valid=False,reason=str(exc))
                        group['injections'].append(record)
                print(ident,config,'PATCH',patch['anchor'],'complete',flush=True)
            group['real_summary']=summarize(group['real_controls']);group['injection_summary']=summarize(group['injections'])
            group['injection_groups']=[{'snr_per_frame':snr,'stationary':stationary,**summarize([r for r in group['injections'] if r['snr_per_frame']==snr and (np.linalg.norm(r['truth_delta_px'])==0)==stationary])} for snr in RULES['injection_snr_per_frame'] for stationary in [True,False]]
            result['configurations'].append(group)
            print('SUMMARY',ident,config,group['real_summary'],group['injection_summary'],flush=True)
            save(OUT/(ident+'.json'),result)
        outputs.append(result);save(OUT/(ident+'.json'),result)
    summary={'version':RULES['version'],'protocol_sha256':protocol_hash,'fields':[],'current_measurement_changed':False}
    for r in outputs:
        summary['fields'].append({'field':r['field'],'training_eligible':r['training_eligible'],'configurations':[{k:v for k,v in g.items() if k in ['configuration','pairs','unavailable_reason','epoch_mjd_ranges','real_summary','injection_summary','injection_groups','positive_control']} for g in r['configurations']]})
    save(OUT/'summary.json',summary)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--lock',action='store_true');args=parser.parse_args()
    if args.lock:lock()
    else:run()
