"""Prospective geometry-only field selection; never query or open new fields."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import math
from numbers import Real
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'
OUT=ROOT/'web/data/independent-fields/selection.json'
SCRIPT=Path(__file__).resolve()
BASE_RA=[12,48,84,120,156,192,228,264,300,336]
DECLINATIONS=[-45,0,45]
OFFSETS=list(range(36))
SALT='nosleepclub-independent-fields-20261030-v1'
MIN_DEGREES=6.0
ANGLE_ROUNDOFF_DEG=1e-12


def digest(path):return sha256(Path(path).read_bytes()).hexdigest()


def coordinates(ra,dec,label):
    if isinstance(ra,bool) or isinstance(dec,bool) or not isinstance(ra,Real) or not isinstance(dec,Real):raise ValueError('non-numeric direction: '+label)
    ra=float(ra);dec=float(dec)
    if not math.isfinite(ra) or not math.isfinite(dec) or not -90<=dec<=90:raise ValueError('invalid direction: '+label)
    return ra%360.,dec


def separation_deg(ra1,dec1,ra2,dec2):
    """Great-circle distance with wrapped RA, stable at zero/antipode."""
    a,b=coordinates(ra1,dec1,'first');c,d=coordinates(ra2,dec2,'second')
    a,b,c,d=map(math.radians,(a,b,c,d));x=math.sin((d-b)/2)**2+math.cos(b)*math.cos(d)*math.sin((c-a)/2)**2
    return math.degrees(2*math.atan2(math.sqrt(max(0.,min(1.,x))),math.sqrt(max(0.,1-min(1.,x)))))


def discover_manifests(raw_root=RAW,workspace=ROOT):
    """Read local JSON manifests only; no FITS, catalog, or network access."""
    raw_root=Path(raw_root);workspace=Path(workspace)
    if not raw_root.is_dir():raise ValueError('cached data/raw directory is missing')
    paths=sorted((p for p in raw_root.rglob('*.json') if 'manifest' in p.name.lower()),key=lambda p:p.as_posix())
    output=[]
    for path in paths:
        data=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data,dict):raise ValueError('manifest is not an object: '+str(path))
        grouped={}
        def add(container,ra_key,dec_key,pointer):
            has_ra=ra_key in container;has_dec=dec_key in container
            if has_ra!=has_dec:raise ValueError('partial direction in '+str(path)+' '+pointer)
            if not has_ra:return
            ra,dec=coordinates(container[ra_key],container[dec_key],str(path)+' '+pointer)
            grouped.setdefault((ra,dec),[]).append(pointer)
        field=data.get('field')
        if isinstance(field,dict):add(field,'ra','dec','/field/{ra,dec}')
        add(data,'center_ra_deg','center_dec_deg','/{center_ra_deg,center_dec_deg}')
        records=data.get('records',[])
        if records is not None and not isinstance(records,list):raise ValueError('manifest records is not a list: '+str(path))
        for index,record in enumerate(records or []):
            if not isinstance(record,dict):raise ValueError('manifest record is not an object: '+str(path))
            add(record,'cutout_center_ra','cutout_center_dec',f'/records/{index}/{{cutout_center_ra,cutout_center_dec}}')
        if grouped:
            try:relative=path.relative_to(workspace).as_posix()
            except ValueError as exc:raise ValueError('manifest outside workspace') from exc
            output.append({'path':relative,'sha256':digest(path),
                'centers':[{'ra_deg':ra,'dec_deg':dec,'json_pointers':pointers} for (ra,dec),pointers in sorted(grouped.items())]})
    if not output:raise ValueError('no cached astronomical manifest centers found')
    return output


def field_id(ra,dec):
    return f'r{ra:03d}{"p" if dec>=0 else "m"}{abs(dec):02d}'


def grid(offset):
    if isinstance(offset,bool) or not isinstance(offset,int) or offset not in OFFSETS:raise ValueError('invalid RA offset')
    return [{'id':field_id((ra+offset)%360,dec),'ra_deg':(ra+offset)%360,'dec_deg':dec}
            for dec in DECLINATIONS for ra in BASE_RA]


def all_distances(fields,manifests):
    old=[];between=[]
    for a in fields:
        for manifest in manifests:
            for center in manifest['centers']:
                old.append({'kind':'cached_center','candidate_id':a['id'],'candidate_ra_deg':a['ra_deg'],'candidate_dec_deg':a['dec_deg'],
                  'cached_ra_deg':center['ra_deg'],'cached_dec_deg':center['dec_deg'],'manifest_path':manifest['path'],
                  'manifest_sha256':manifest['sha256'],'distance_deg':separation_deg(a['ra_deg'],a['dec_deg'],center['ra_deg'],center['dec_deg'])})
    for i,a in enumerate(fields):
        for b in fields[i+1:]:
            between.append({'kind':'candidate_pair','candidate_id':a['id'],'other_candidate_id':b['id'],
                            'distance_deg':separation_deg(a['ra_deg'],a['dec_deg'],b['ra_deg'],b['dec_deg'])})
    return old,between


def separation_conflicts(fields,manifests):
    old,between=all_distances(fields,manifests)
    # Previous centers require >=6°; distinct new centers require >6°.
    old_conflicts=[v for v in old if v['distance_deg']<MIN_DEGREES and not math.isclose(v['distance_deg'],MIN_DEGREES,rel_tol=0.,abs_tol=ANGLE_ROUNDOFF_DEG)]
    new_conflicts=[v for v in between if v['distance_deg']<MIN_DEGREES or math.isclose(v['distance_deg'],MIN_DEGREES,rel_tol=0.,abs_tol=ANGLE_ROUNDOFF_DEG)]
    return sorted(old_conflicts+new_conflicts,
                  key=lambda v:(v['distance_deg'],v['kind'],v['candidate_id'],v.get('manifest_path',''),v.get('other_candidate_id','')))


def assign_roles(fields):
    out=[]
    for dec in DECLINATIONS:
        group=[dict(v) for v in fields if v['dec_deg']==dec]
        if len(group)!=10 or len({v['id'] for v in group})!=10:raise ValueError('each declination ring must have 10 distinct fields')
        for f in group:f['split_sha256']=sha256((SALT+'|'+f['id']).encode('utf-8')).hexdigest()
        group.sort(key=lambda f:(f['split_sha256'],f['id']))
        for i,f in enumerate(group):f['role']='calibration' if i<4 else 'validation' if i<8 else 'final_holdout'
        out.extend(group)
    return out


def select(manifests,source_sha256):
    if not manifests:raise ValueError('no exclusion centers')
    rejected=[];chosen=None
    for offset in OFFSETS:
        fields=grid(offset);conflicts=separation_conflicts(fields,manifests)
        if conflicts:rejected.append({'offset_deg':offset,'nearest_conflict':conflicts[0],'conflict_count':len(conflicts)})
        else:chosen=(offset,fields);break
    if chosen is None:raise ValueError('No global RA offset in 0..35 satisfies separation; no selection written')
    offset,fields=chosen;old,between=all_distances(fields,manifests)
    return {'stage':'field_selection_only','status':'prospective_geometry_only',
        'source_path':'scripts/select_independent_fields.py','source_sha256':source_sha256,
        'rules':{'base_ra_deg':BASE_RA,'declination_deg':DECLINATIONS,'ra_offset_candidates_deg':OFFSETS,
            'offset_choice':'first offset in ascending order satisfying both separation rules using cached center metadata only',
            'cached_center_minimum_deg_inclusive':MIN_DEGREES,'new_field_minimum_deg_exclusive':MIN_DEGREES,
            'distance':'spherical great-circle; RA wraps modulo 360; 1e-12 degree roundoff treated as equality',
            'split_sha256_input':SALT+'|field_id', 'split_per_declination_ring':{'calibration':4,'validation':4,'final_holdout':2},
            'field_id':'r{RA:03d}{p|m}{abs(Dec):02d}; coordinates integer degrees',
            'old_fields_role':'development', 'evidence':'cached manifests only; no outcomes, images, spectra or new-field queries'},
        'chosen_ra_offset_deg':offset,'rejected_offsets':rejected,
        'nearest_cached_center':min(old,key=lambda v:(v['distance_deg'],v['candidate_id'],v['manifest_path'])),
        'nearest_new_field_pair':min(between,key=lambda v:(v['distance_deg'],v['candidate_id'],v['other_candidate_id'])),
        'exclusion_manifests':manifests,'fields':assign_roles(fields),
        'limitations':['field selection only; not a sealed analysis/calibration protocol or independent validation',
            'geometry alone does not establish nonoverlapping exposures, pixels, sources, instrument systematics or time',
            'before measurement, lock evaluator, absolute gates, power, PSF/SED/gain truth, support routing and exposure/time/source disjointness',
            'future metadata queries require committed selection and source guard; compare exact observation IDs before any measurements']}


def encode(selection):return (json.dumps(selection,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')


def write_once(path,selection):
    path=Path(path);value=encode(selection)
    if path.exists():
        if path.read_bytes()!=value:raise FileExistsError('Existing selection differs; refusing overwrite')
        return False
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        with path.open('xb') as handle:handle.write(value)
    except FileExistsError:raise FileExistsError('Selection appeared concurrently; refusing overwrite')
    return True


def verify_before_metadata_query(selection_path=OUT):
    """Guard for a future query workflow; this module has no query function."""
    path=Path(selection_path);selection=json.loads(path.read_text(encoding='utf-8'))
    if selection.get('stage')!='field_selection_only' or selection['source_sha256']!=digest(SCRIPT):raise ValueError('Selection/source hash mismatch')
    for file in [SCRIPT,path]:
        try:relative=file.resolve().relative_to(ROOT).as_posix()
        except ValueError as exc:raise ValueError('Guarded file outside workspace') from exc
        try:committed=subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT,stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as exc:raise ValueError('Required source or selection is not committed: '+relative) from exc
        if sha256(committed).hexdigest()!=digest(file):raise ValueError('Uncommitted changes to '+relative)
    if discover_manifests()!=selection['exclusion_manifests']:raise ValueError('Cached manifest evidence changed; re-evaluate separation before query')
    expected=select(selection['exclusion_manifests'],digest(SCRIPT))
    if selection!=expected:raise ValueError('Selection no longer matches deterministic rule')
    return {'verified':True,'scope':'source and field selection only; no analysis protocol or metadata query authorized'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--select',action='store_true');group.add_argument('--verify-committed',action='store_true')
    args=parser.parse_args()
    if args.select:
        result=select(discover_manifests(),digest(SCRIPT));written=write_once(OUT,result)
        print('SELECTION',OUT,'written',written,'sha256',digest(OUT),'offset',result['chosen_ra_offset_deg'],flush=True)
    else:print(json.dumps(verify_before_metadata_query(),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
