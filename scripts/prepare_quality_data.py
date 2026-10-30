"""Cache IR neighbours for development and three geometry-selected new fields.

The new centers are declared before inspecting any fitted positions or injections.
Metadata and masks may be inspected before the final evaluation protocol is locked.
"""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import argparse
import io
import json
from pathlib import Path
import shutil

from astropy.table import Table
import requests
import truststore
from . import prepare_benchmark_data as old
from . import fetch_wise0855 as fetch
from .prepare_gaia_data import COLUMNS,ENDPOINT

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/quality'
NEW_FIELDS=[('q030m10',30.,-10.),('q180p20',180.,20.),('q300m30',300.,-30.)]
CAT_COLUMNS='source_name,ra,dec,ra_pm,dec_pm,sigra_pm,sigdec_pm,pmra,pmdec,sigpmra,sigpmdec,meanobsmjd,w1mpro_pm,w2mpro_pm,w2snr_pm,w2rchi2_pm,cc_flags,ab_flags'


def table_query(folder,name,query):
    params={'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable','QUERY':query}
    content=old.cached(ENDPOINT,folder/(name+'.xml'),params)
    table=Table.read(io.BytesIO(content),format='votable',use_names_over_ids=True)
    return {'endpoint':ENDPOINT,'query':query,'path':(folder/(name+'.xml')).relative_to(ROOT).as_posix(),
        'sha256':sha256(content).hexdigest(),'rows':len(table)}


def infrared(field):
    folder=RAW/field['id'];folder.mkdir(parents=True,exist_ok=True)
    where=f"CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{field['ra']},{field['dec']},0.30))=1 AND w2mpro_pm<17 AND w2snr_pm>=5"
    result={}
    for name,columns in [('catwise',CAT_COLUMNS),('catwise-identifiers','source_name,source_id')]:
        result[name]=table_query(folder,name,f'SELECT {columns} FROM catwise_2020 WHERE '+where+' ORDER BY source_name')
    correction=ROOT/'data/raw/wise0855/release-study/catwise-corrections.tbl'
    destination=folder/'catwise-corrections.tbl';shutil.copyfile(correction,destination)
    result['corrections']={'path':destination.relative_to(ROOT).as_posix(),'sha256':sha256(destination.read_bytes()).hexdigest(),
        'url':'https://irsa.ipac.caltech.edu/data/WISE/CatWISE/gator_docs/CatWISE2020_Table1_20201012.tbl'}
    (folder/'infrared.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(field['id'],'CatWISE',result['catwise']['rows'],flush=True)


def new_field(spec):
    ident,ra,dec=spec;folder=RAW/ident;folder.mkdir(parents=True,exist_ok=True)
    params={'COLLECTION':'spherex_qr2','POS':f'circle {ra} {dec} 0.05'}
    content=old.cached('https://irsa.ipac.caltech.edu/SIA',folder/'qr2.xml',params)
    table=Table.read(io.BytesIO(content),format='votable',use_names_over_ids=True)
    rows=sorted([{'obs_id':str(r['obs_id']),'access_url':str(r['access_url']),'mjd':float(r['t_min'])}
        for r in table if str(r['energy_bandpassname'])=='SPHEREx-D6'],key=lambda r:r['mjd'])
    field={'id':ident,'name':f'RA {ra:g}° / Dec {dec:+g}°','ra':ra,'dec':dec,
        'coordinate_source':'predeclared geometric centers, not selected by fitted errors',
        'sia':{'url':'https://irsa.ipac.caltech.edu/SIA','params':params,'sha256':sha256(content).hexdigest(),'rows':len(table),'d6_rows':len(rows)}}
    clusters=[]
    for row in rows:
        if not clusters or row['mjd']-clusters[-1][-1]['mjd']>60:clusters.append([])
        clusters[-1].append(row)
    selected=[]
    for epoch,cluster in zip(['before','after'],clusters[:2]):
        for row in cluster:selected.append({**row,'epoch':epoch,'detector':6,'collection':'spherex_qr2',
            'cache_subdir':'../quality/'+ident+'/images','cutout_center_ra':ra,'cutout_center_dec':dec,'cutout_width_deg':.32})
    with ThreadPoolExecutor(max_workers=3) as pool:
        records=[]
        for result in pool.map(fetch.download,selected):
            records.append(result);print(ident,len(records),'/',len(selected),result['status'],flush=True)
    for record in records:
        if 'path' in record:record['path']=(ROOT/record['path']).resolve().relative_to(ROOT).as_posix()
    gaia=table_query(folder,'gaia-dr3','SELECT '+', '.join(COLUMNS)+f" FROM gaia_dr3_source WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra},{dec},0.25))=1 AND phot_g_mean_mag<18.5 ORDER BY source_id")
    gaia.update(table='gaia_dr3_source',release='Gaia DR3')
    cal=json.loads((ROOT/'data/raw/wise0855/gaia-wide/manifest.json').read_text())['calibrations']
    manifest={'field':field,'records':records,'calibrations':cal,'gaia':gaia,'selection':'first two QR2 seasons separated by >60 day gap; all D6, no outcome selection'}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    infrared(field)
    return manifest


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--new',action='store_true');args=parser.parse_args()
    truststore.inject_into_ssl();RAW.mkdir(parents=True,exist_ok=True)
    if args.new:
        for spec in NEW_FIELDS:new_field(spec)
    else:
        for ident in ['barnard','rw-aur','r-dra']:
            m=json.loads((ROOT/'data/raw/benchmark'/ident/'manifest.json').read_text());infrared(m['field'])


if __name__=='__main__':main()
