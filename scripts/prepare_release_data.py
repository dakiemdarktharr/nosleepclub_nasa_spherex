"""Discover QR3 coverage and infrared-catalog schema without changing old data."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import io
import json
from pathlib import Path
from astropy.table import Table
import requests
from . import fetch_wise0855 as fetch

ROOT=Path(__file__).resolve().parents[1]
OUT=fetch.RAW/'release-study'
TAP='https://irsa.ipac.caltech.edu/TAP/sync'


def cache_query(name,url,params):
    path=OUT/(name+'.xml');OUT.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        r=requests.get(url,params=params,timeout=(20,120));r.raise_for_status()
        Table.read(io.BytesIO(r.content),format='votable',use_names_over_ids=True)
        path.write_bytes(r.content)
    table=Table.read(path,format='votable',use_names_over_ids=True)
    meta={'url':url,'params':params,'path':str(path.relative_to(ROOT)).replace('\\','/'),
          'sha256':sha256(path.read_bytes()).hexdigest(),'rows':len(table)}
    return table,meta


def main():
    jobs=[('qr3', 'https://irsa.ipac.caltech.edu/SIA',{'COLLECTION':'spherex_qr3','POS':'circle 133.76037473328523 -7.242149767967145 0.05'}),
          ('ir-schema',TAP,{'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable','QUERY':
            "SELECT table_name,column_name,datatype,unit,description FROM TAP_SCHEMA.columns WHERE table_name='catwise_2020'"}),
          ('catwise',TAP,{'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable','QUERY':
            "SELECT source_name,ra,dec,ra_pm,dec_pm,sigra_pm,sigdec_pm,pmra,pmdec,sigpmra,sigpmdec,meanobsmjd,w1mpro_pm,w2mpro_pm,w2snr_pm,w2rchi2_pm,cc_flags,ab_flags FROM catwise_2020 WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',133.76037473328523,-7.242149767967145,0.30))=1 AND w2mpro_pm<17.0 AND w2snr_pm>=5 ORDER BY source_name"}),
          ('catwise-identifiers',TAP,{'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable','QUERY':
            "SELECT source_name,source_id FROM catwise_2020 WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',133.76037473328523,-7.242149767967145,0.30))=1 AND w2mpro_pm<17.0 AND w2snr_pm>=5"}),
          ('qr3-tap',TAP,{'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable','QUERY':
            "SELECT a.uri,p.time_bounds_lower,p.energy_bandpassname,p.provenance_version FROM spherex.artifact a JOIN spherex.plane p ON a.planeid=p.planeid WHERE CONTAINS(POINT('ICRS',133.76037473328523,-7.242149767967145),p.poly)=1 AND a.uri LIKE '%/qr3/%'"})]
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda j:cache_query(*j),jobs))
    output={}
    for (name,_,_), (table,meta) in zip(jobs,results):
        output[name]=meta
        if name=='qr3':
            rows=[{'obs_id':str(r['obs_id']),'access_url':str(r['access_url']),'mjd':float(r['t_min']),
                   'detector':6,'collection':'spherex_qr3'} for r in table if str(r['energy_bandpassname'])=='SPHEREx-D6']
            output['qr3']['records']=rows
            old=json.loads((fetch.RAW/'gaia-wide/manifest.json').read_text())
            shared=set(r['obs_id'] for r in old['records'])&set(r['obs_id'] for r in rows)
            print('QR3 D6:',len(rows),'same-exposure matches:',len(shared),'MJD range:',[min([r['mjd'] for r in rows],default=None),max([r['mjd'] for r in rows],default=None)],flush=True)
        elif name=='ir-schema':
            for row in table:
                if any(s in row['column_name'].lower() for s in ['pm','mjd','flag','name','snr','epoch']):
                    print(row['column_name'],row['unit'],str(row['description'])[:160])
        else:
            print(name,len(table),table[:3],flush=True)
    path=OUT/'catwise-corrections.tbl'
    url='https://irsa.ipac.caltech.edu/data/WISE/CatWISE/gator_docs/CatWISE2020_Table1_20201012.tbl'
    if not path.exists():
        r=requests.get(url,timeout=(20,120));r.raise_for_status();path.write_bytes(r.content)
    output['catwise_corrections']={'url':url,'path':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':sha256(path.read_bytes()).hexdigest()}
    print(path.read_text()[:1400],flush=True)
    (OUT/'discovery.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
