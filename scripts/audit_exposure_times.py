"""Audit cached WISE-field IMAGE header times/geometry without measuring sources."""
from __future__ import annotations
import json
from hashlib import sha256
from pathlib import Path
import numpy as np
from astropy.io import fits
from astropy.time import Time
from . import astrometric_time_model as model

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'data/raw/wise0855/coadd/manifest.json'
OUT=ROOT/'web/data/time-model/development-audit.json'
ASSUMPTIONS={'mu_east_arcsec_per_year':-8.06,'mu_north_arcsec_per_year':.70,'parallax_arcsec':.454,
             'source':'Luhman 2014 Tables 1–2, illustrative literature values, not a new fit',
             'source_url':'https://arxiv.org/pdf/1404.6501',
             'qualification':'linear proper motion and first-order Earth parallax only; unmodeled acceleration/systematics not bounded'}


def digest(path):return sha256(path.read_bytes()).hexdigest()


def condition(times,ref,ra,dec,kind):
    matrix,_=model.design_matrix(times,ref,ra,dec,kind)
    return model.inspect_design(matrix,np.eye(2*len(times)))


def spread(rows,ref,ra,dec):
    times=[v['time'] for v in rows];matrix,_=model.design_matrix(times,ref,ra,dec,'pm_parallax')
    params=np.array([0.,0.,ASSUMPTIONS['mu_east_arcsec_per_year'],ASSUMPTIONS['mu_north_arcsec_per_year'],ASSUMPTIONS['parallax_arcsec']])
    path=(matrix@params).reshape(-1,2);difference=np.linalg.norm(path[:,None,:]-path[None,:,:],axis=2)
    bound=[v['spacecraft_bound'].get('bound_arcsec') for v in rows]
    output={'exposure_count':len(rows),'first_mjd_tdb':float(min(t.tdb.mjd for t in times)),
            'last_mjd_tdb':float(max(t.tdb.mjd for t in times)),
            'midpoint_span_days':float(max(t.tdb.mjd for t in times)-min(t.tdb.mjd for t in times)),
            'earth_only_max_pairwise_illustrative_displacement_arcsec':float(difference.max())}
    if all(v is not None for v in bound):
        bounds=np.asarray(bound)
        output['spacecraft_omission_max_pairwise_bound_arcsec']=float(np.max(bounds[:,None]+bounds[None,:]))
        output['earth_model_plus_spacecraft_max_pairwise_upper_arcsec']=float(np.max(difference+bounds[:,None]+bounds[None,:]))
    else:output['spacecraft_omission_max_pairwise_bound_arcsec']=None
    output['qualification']='illustrative literature motion, fixed direction and first-order parallax; not a measured displacement or comprehensive bound'
    return output


def main():
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'));records=[r for r in manifest['records'] if r['status']=='downloaded']
    if not records:raise RuntimeError('No existing cached frames')
    field=(records[0]['cutout_center_ra'],records[0]['cutout_center_dec']);epochs={};rows=[]
    for record in records:
        if (record['cutout_center_ra'],record['cutout_center_dec'])!=field:raise RuntimeError('Mixed field centers')
        path=ROOT/record['path'];actual=digest(path)
        if actual!=record['sha256']:raise RuntimeError('Cached FITS hash mismatch: '+record['obs_id'])
        entry={'obs_id':record['obs_id'],'epoch':record['epoch'],'path':record['path'],'sha256':actual,
               'access_url':record.get('access_url'),'cutout_url':record.get('cutout_url')}
        try:
            with fits.open(path,memmap=False) as hd:
                header=hd['IMAGE'].header;exposure=model.parse_image_header(header)
                bound=model.spacecraft_parallax_bound(header,ASSUMPTIONS['parallax_arcsec'])
                entry.update(time=exposure.metadata(),spacecraft_parallax_bound=bound,
                             pipeline_version=str(hd[0].header.get('VERSION','unspecified')),
                             mjd_obs_header=header.get('MJD-OBS'),
                             avg_minus_obs_seconds=float((exposure.midpoint-Time(header['MJD-OBS'],format='mjd',scale=exposure.input_scale)).to_value('sec')) if 'MJD-OBS' in header else None)
            epochs.setdefault(record['epoch'],[]).append({'time':exposure.midpoint,'spacecraft_bound':bound})
        except (model.TimeMetadataError,ValueError,KeyError) as exc:entry['time_error']=str(exc)
        rows.append(entry)
    if not epochs:raise RuntimeError('No valid IMAGE-header times')
    all_times=[v['time'] for group in epochs.values() for v in group]
    ref=Time(float(np.median([t.tdb.mjd for t in all_times])),format='mjd',scale='tdb')
    assessments={}
    for name,group in epochs.items():
        times=[r['time'] for r in group]
        assessments[name]={'spread':spread(group,ref,*field),
            'design_geometry_identity_weights':{kind:condition(times,ref,*field,kind) for kind in ['pm_only','pm_parallax']}}
    combined={kind:condition(all_times,ref,*field,kind) for kind in ['pm_only','pm_parallax']}
    collapsed=[]
    for group in epochs.values():
        midpoint=Time(float(np.mean([v['time'].tdb.mjd for v in group])),format='mjd',scale='tdb')
        collapsed.extend([midpoint]*len(group))
    collapsed_design={kind:condition(collapsed,ref,*field,kind) for kind in ['pm_only','pm_parallax']}
    report={'role':'header and sampling geometry audit; no astrometric fit, source measurement or detection',
        'manifest_path':MANIFEST.relative_to(ROOT).as_posix(),'manifest_sha256':digest(MANIFEST),
        'source_hashes':{p:digest(ROOT/p) for p in ['scripts/astrometric_time_model.py','scripts/audit_exposure_times.py','requirements.txt']},
        'direction':{'ra_deg':field[0],'dec_deg':field[1],'source':'manifest cutout center; only defines tangent basis'},
        'illustrative_assumptions':ASSUMPTIONS,'exposures':rows,
        'valid_exposures':len(all_times),'attempted_exposures':len(rows),'reference_mjd_tdb':float(ref.mjd),
        'epochs':assessments,'combined_design_identity_weights':combined,
        'collapsed_two_season_design_identity_weights':collapsed_design,
        'qualification':'Identity weights assess numerical design only; rank/condition do not establish precision, independent epochs, or parallax measurement. Spacecraft axes not applied.'}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_bytes((json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8'))
    print('AUDIT',OUT,'sha256',digest(OUT),'valid',len(all_times),'attempts',len(rows),flush=True)
    print('EPOCHS',json.dumps(assessments,ensure_ascii=False),flush=True)
    print('COMBINED',json.dumps(combined),'COLLAPSED',json.dumps(collapsed_design),flush=True)


if __name__=='__main__':main()
