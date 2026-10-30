"""Discover and cache new SPHEREx fields without inspecting fitted motions."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import io
import json
import time
from pathlib import Path
import argparse
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.table import Table
import requests
import truststore
from . import fetch_wise0855 as fetch
from .prepare_gaia_data import COLUMNS,ENDPOINT

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/benchmark'
TARGETS=[
    ('barnard','Barnard star','17 57 48.4984700685 +04 41 36.113879676','https://simbad.cds.unistra.fr/simbad/sim-basic?Ident=Barnard%27s+star'),
    ('rw-aur','RW Aur','05 07 49.5662483 +30 24 05.177426','https://simbad.cds.unistra.fr/simbad/sim-id?Ident=RW+Aur'),
    ('r-dra','R Dra','16 32 40.2265999080 +66 45 17.925901992','https://simbad.cds.unistra.fr/simbad/sim-id?Ident=%40376084&Name=V%2A+R+Dra&submit=submit'),
]


def cached(url,path,params=None):
    if not path.exists():
        for attempt in range(3):
            try:
                r=requests.get(url,params=params,timeout=(20,120));r.raise_for_status();path.write_bytes(r.content);break
            except requests.RequestException:
                if attempt==2:raise
                time.sleep(2+attempt)
    return path.read_bytes()


def probe(target):
    ident,name,coordinate,source=target;folder=RAW/ident;folder.mkdir(parents=True,exist_ok=True)
    try:
        position=SkyCoord(coordinate,unit=(u.hourangle,u.deg));ra=float(position.ra.deg);dec=float(position.dec.deg)
        result={'id':ident,'name':name,'ra':ra,'dec':dec,'coordinate_source':source,'coordinate_epoch':'J2000; field center only, not astrometric truth','collections':[]}
        for collection in ['spherex_qr2','spherex_qr3']:
            params={'COLLECTION':collection,'POS':f'circle {ra} {dec} 0.05'}
            content=cached('https://irsa.ipac.caltech.edu/SIA',folder/(collection+'.xml'),params)
            table=Table.read(io.BytesIO(content),format='votable',use_names_over_ids=True)
            selected=[{'obs_id':str(row['obs_id']),'access_url':str(row['access_url']),'mjd':float(row['t_min'])}
                      for row in table if str(row['energy_bandpassname'])=='SPHEREx-D6']
            result['collections'].append({'collection':collection,'query_url':requests.Request('GET','https://irsa.ipac.caltech.edu/SIA',params=params).prepare().url,
                'rows':len(table),'d6':sorted(selected,key=lambda r:r['mjd']),'sha256':sha256(content).hexdigest()})
        (folder/'coverage.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        return result
    except Exception as exc:return {'id':ident,'error':str(exc)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--download',action='store_true');args=parser.parse_args()
    truststore.inject_into_ssl();RAW.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(probe,TARGETS))
    (RAW/'coverage.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    for r in results:
        print(json.dumps({k:v for k,v in r.items() if k!='collections'}))
        for c in r.get('collections',[]):
            print(c['collection'],c['rows'],'D6',len(c['d6']),'MJD',[round(v['mjd'],2) for v in c['d6']])
    if args.download:
        calibrations=json.loads((ROOT/'data/raw/wise0855/gaia-wide/manifest.json').read_text())['calibrations']
        for field in results:
            if 'error' in field:continue
            folder=RAW/field['id'];rows=field['collections'][0]['d6'];clusters=[]
            for row in rows:
                if not clusters or row['mjd']-clusters[-1][-1]['mjd']>60:clusters.append([])
                clusters[-1].append(row)
            if len(clusters)<2:continue
            selected=[]
            for epoch,cluster in zip(['before','after'],clusters[:2]):
                for row in cluster:
                    selected.append({**row,'epoch':epoch,'detector':6,'collection':'spherex_qr2',
                        'cache_subdir':'../benchmark/'+field['id']+'/images','cutout_center_ra':field['ra'],
                        'cutout_center_dec':field['dec'],'cutout_width_deg':.32})
            with ThreadPoolExecutor(max_workers=3) as pool:
                records=[]
                for result in pool.map(fetch.download,selected):
                    records.append(result);print(field['id'],len(records),'/',len(selected),result['status'],flush=True)
            # Canonical paths stay inside the ignored raw cache.
            for row in records:
                if 'path' in row:row['path']=(ROOT/row['path']).resolve().relative_to(ROOT).as_posix()
            query=('SELECT '+', '.join(COLUMNS)+" FROM gaia_dr3_source WHERE CONTAINS(POINT('ICRS',ra,dec),"
                   +f"CIRCLE('ICRS',{field['ra']},{field['dec']},0.25))=1 AND phot_g_mean_mag < 18.5 ORDER BY source_id")
            content=cached(ENDPOINT,folder/'gaia-dr3.xml',{'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable','QUERY':query})
            table=Table.read(io.BytesIO(content),format='votable',use_names_over_ids=True)
            if not set(COLUMNS)<=set(table.colnames):raise RuntimeError(content[:500])
            manifest={'field':field,'records':records,'calibrations':calibrations,'selection':'first two seasons separated by >60 day gap; all D6 exposures',
                'gaia':{'path':(folder/'gaia-dr3.xml').relative_to(ROOT).as_posix(),'sha256':sha256(content).hexdigest(),'rows':len(table),'endpoint':ENDPOINT,'query':query}}
            (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
            print(field['id'],'Gaia',len(table),flush=True)


if __name__=='__main__':main()
