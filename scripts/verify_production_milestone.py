"""Bounded production checks; optional writes use disposable guest sessions only."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import time
import uuid
from urllib.parse import urlencode
from scripts.verify_public_data import versioned_location

import requests
import truststore

ROOT=Path(__file__).resolve().parents[1]
BASE='https://nosleepclub-nasa-spherex.vercel.app'
PINNED_FRAME='https://irsa.ipac.caltech.edu/ibe/data/spherex/qr2/level2/2025W26_2A/l2b-v20-2025-258/6/level2_2025W26_2A_0314_1D6_spx_l2b-v20-2025-258.fits'
PINNED_CUTOUT_SHA='514ac17f7c8d2b7de1f723e4464dfc85a1caacf666f868e70fd844c9d80de8a6'
ASSETS=('index.html','explorer.js','app.js','mission.js','quality.js','review-store.js','goal-dashboard.js','mission.css','linked-evidence.js','neighbor-evidence.js',
        'data/manifest.json','data/continuous-epsf/design.json',
        'data/continuous-epsf/development-summary.json','data/explorer-check/coverage.json',
        'data/sandwich/design.json','data/sandwich/overview.json','data/sandwich/development-summary.json',
        'data/time-model/development-audit.json','data/external/spiff-reference.json',
        'data/independent-fields/selection.json',
        'data/mask-audit/development-audit.json','data/native-gain/development-audit.json',
        'data/external/wise0855-sed-reference.json','data/spectral-response/v2-design.json',
        'data/spectral-response/v2-development-audit.json',
        'data/external/wise0855-prism-reference.json','data/external/photometric-convention.json',
        'data/linked-flux/design.json','data/linked-flux/overview.json','data/linked-flux/development.json',
        'data/linked-flux/mode-diagnostics.json','data/linked-flux/figures.json',
        'data/linked-flux/sensitivity-broad.svg','data/linked-flux/sensitivity-strict.svg',
        'data/neighbor-intervention/design.json','data/neighbor-intervention/development.json',
        'data/neighbor-intervention/controls.json','data/neighbor-intervention/overview.json',
        'data/neighbor-intervention/figures.json','data/neighbor-intervention/real-sensitivity-broad.svg',
        'data/neighbor-intervention/real-sensitivity-strict.svg','data/neighbor-intervention/control-error-pairs.svg',
        'reference-evidence.js','data/reference-stars/design.json','data/reference-stars/overview.json',
        'data/reference-stars/records.json.gz','data/source-presence/design.json',
        'data/source-presence/threshold.json','data/source-presence/overview.json','data/source-presence/records.json.gz',
        'calibration-evidence.js','data/shape-correction/design.json',
        'data/shape-correction/feasibility-unweighted.json','data/shape-correction/overview.json',
        'data/shape-correction/coefficient-seal.json','data/shape-correction/calibration-records.json.gz',
        'data/shape-point-check/design.json','data/shape-point-check/calibration-gate.json',
        'data/shape-point-check/overview.json','data/shape-point-check/independent-audit.json',
        'data/shape-point-check/records.json.gz','data/reference-covariance/design.json',
        'data/reference-covariance/overview.json','data/reference-covariance/independent-audit.json',
        'data/reference-covariance/records.json.gz',
        'navigation.js','profile-evidence.js','data/profile-landscape/design.json',
        'data/profile-landscape/overview.json','data/profile-landscape/independent-audit.json',
        'data/profile-landscape/figure-environment.json','data/profile-landscape/records.json.gz',
        'data/profile-landscape/profile-5756942110218608640-2025W46_2A_0214_2.png',
        'data/profile-landscape/profile-5756942110218608640-2025W46_2A_0214_3.png',
        'data/profile-landscape/profile-5756958431094222592-2025W46_2A_0214_2.png',
        'data/profile-landscape/profile-5756958431094222592-2025W46_2A_0214_3.png',
        'signal-evidence.js','workflow.css','draft-store.js','data-links.js','data-download.js','download.html','data/signal-controls/design.json','data/signal-controls/overview.json',
        'data/signal-controls/independent-audit.json','data/signal-controls/records.json.gz',
        'data/signal-controls/scene-example.png')


def require(condition, label):
    if not condition:raise RuntimeError(label)


def verify(write_smoke=False, report=None):
    truststore.inject_into_ssl()
    report={} if report is None else report
    report.update({'schema_version':1,'started_at_utc':datetime.now(timezone.utc).isoformat(),
            'base_url':BASE,'local_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'verifier_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'checks':[],
            'retry_policy':'One retry only for GET upstream 502/504; every response is retained.',
            'qualification':'Bounded software/data-access smoke, not scientific, recovery or load acceptance.'})
    report['worktree_dirty']=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    session=requests.Session()

    def committed(asset):
        # The deployed artifact is a Git blob. Windows working copies can still
        # contain CRLF or unrelated development edits; never certify those.
        return subprocess.check_output(['git','show','HEAD:web/'+asset],cwd=ROOT)

    def request(path, method='GET', client=session, **kwargs):
        attempts=2 if method=='GET' and path in ('/api/observations','/api/frame') else 1
        for attempt in range(attempts):
            start=time.monotonic()
            response=client.request(method,BASE+path,timeout=(10,100),allow_redirects=False,**kwargs)
            report['checks'].append({'path':path,'method':method,'attempt':attempt+1,'status':response.status_code,
                'elapsed_seconds':round(time.monotonic()-start,3),'request_id':response.headers.get('X-Request-Id'),
                'cache':response.headers.get('X-Vercel-Cache')})
            if response.status_code >= 400 and response.headers.get('Content-Type','').startswith('application/json'):
                try: error_code=response.json().get('error')
                except (ValueError,AttributeError): error_code=None
                if isinstance(error_code,str) and re.fullmatch(r'[a-z0-9_]{1,80}',error_code):
                    report['checks'][-1]['error_code']=error_code
            if response.status_code not in (502,504) or attempt==attempts-1:return response

    transport=json.loads(committed('api/_data_manifest.json'))
    for asset in ASSETS:
        path='/' if asset=='index.html' else '/'+asset
        expected=sha256(committed(asset)).hexdigest()
        response=request(path)
        if asset.startswith('data/'):
            entry=transport['assets'][asset]
            require(entry['sha256']==expected,'Mongo manifest differs from Git: '+asset)
            versioned='/api/data?'+urlencode({'path':asset,'v':entry['stored_sha256']})
            require(response.status_code==307 and versioned_location(response.headers.get('Location',''),asset,entry['stored_sha256']),'canonical Mongo route missing: '+asset)
            if entry['stored_bytes']>transport['direct_bytes']:
                response=request(versioned)
                require(response.status_code==307 and response.headers.get('Location','').startswith('/download.html?'),'multipart download route missing')
                response=request('/api/data',params={'path':asset,'v':entry['stored_sha256'],'meta':'1'})
                require(response.status_code==200,'multipart metadata unavailable')
                require(response.json()=={'path':asset,**entry},'multipart metadata differs from Git manifest')
                report['checks'][-1]['qualification']='Metadata/redirect only here; full exact bytes require separate all-213 public-data reconciliation.'
                continue
            response=request(versioned)
            require(response.headers.get('X-Data-Source')=='mongodb','Mongo source header missing')
        require(response.status_code==200,'public asset unavailable: '+asset)
        require(sha256(response.content).hexdigest()==expected,'static hash mismatch: '+asset)
        report['checks'][-1]['sha256']=expected
        report['checks'][-1]['worktree_bytes_match_commit']=sha256((ROOT/'web'/asset).read_bytes()).hexdigest()==expected
    manifest=json.loads(committed('data/manifest.json'))
    require("script-src 'self'" in response.headers.get('Content-Security-Policy',''),'CSP missing')
    response=request('/api/data',params={'path':'data/manifest.json','meta':'1'})
    require(response.status_code==200 and response.headers.get('X-App-Commit')==report['local_commit'],'Mongo reader API commit mismatch')
    response=request('/api/data_import',method='POST',data=b'')
    require(response.status_code==403,'public importer is not disabled without a capability')

    params={'ra':350,'dec':35,'radius':.03,'release':'qr2','detector':6,'maxrec':5,
            'band_min_um':4.42,'band_max_um':5.0}
    response=request('/api/observations',params=params)
    require(response.status_code==200,'production observations unavailable')
    require(response.headers.get('X-App-Commit')==report['local_commit'],'deployed API commit differs from expected Git commit')
    report['deployed_api_commit']=response.headers['X-App-Commit']
    value=response.json();require(value['returned_count']>0 and value['status'] in ['ok','truncated'],'metadata response contract')
    report['observations']={'returned_count':value['returned_count'],'truncated':value['truncated'],
        'response_sha256':value['provenance']['response_sha256'],'query_url':value['provenance']['query_url']}
    response=request('/api/observations',params={**params,'time_min_mjd':50000,'time_max_mjd':50001})
    require(response.status_code==200 and response.json()['status']=='no_data','no-data is not distinguished')
    response=request('/api/observations',params={**params,'ra':360})
    require(response.status_code==400,'invalid RA was not rejected')
    response=request('/api/frame',params={'url':PINNED_FRAME,'ra':350,'dec':35,'fov_deg':.06,'zodi':'subtract'})
    require(response.status_code==200 and response.content.startswith(b'\x89PNG\r\n\x1a\n'),'real frame unavailable')
    require(response.headers.get('X-App-Commit')==report['local_commit'],'frame API commit mismatch')
    require(response.headers.get('X-Frame-Cutout-SHA256')==PINNED_CUTOUT_SHA,'pinned cutout changed')
    require(response.headers.get('X-Frame-Unit')=='MJy/sr','frame unit mismatch')
    require(response.headers.get('X-Frame-Contract')=='1.1' and response.headers.get('X-Frame-Mask-Policy')=='source-only-allowlist-v2','frame mask contract mismatch')
    require(int(response.headers.get('X-Frame-Valid-Pixels','0'))>0,'frame has no valid pixels')
    require(sum(int(response.headers.get(k,'-1')) for k in ['X-Frame-Valid-Pixels','X-Frame-Masked-Pixels','X-Frame-Missing-Pixels'])
            ==int(response.headers.get('X-Frame-Grid-Size-Px','0'))**2,'frame mask counts mismatch')
    report['frame']={k:response.headers.get(k) for k in ['X-Frame-Cutout-SHA256','X-Frame-Cutout-URL',
        'X-Frame-Grid-Size-Px','X-Frame-Grid-Scale-Arcsec','X-Frame-Contrast-Low','X-Frame-Contrast-High','X-Frame-Valid-Pixels',
        'X-Frame-Contract','X-Frame-Mask-Policy','X-Frame-Masked-Pixels','X-Frame-Missing-Pixels']}
    report['frame']['png_sha256']=sha256(response.content).hexdigest()

    response=request('/api/reviews');require(response.status_code==200,'review GET unavailable')
    require(response.headers.get('X-App-Commit')==report['local_commit'],'review API commit mismatch')
    first=response.json();require(first['storage']=='mongodb' and first['contract_version']=='1.1','Mongo/review contract')
    require(first['reviews']==[],'fresh disposable session not empty')
    cookie=response.headers.get('Set-Cookie','')
    require(all(v in cookie for v in ['__Host-','Secure','HttpOnly','SameSite=Strict']),'guest cookie policy')
    require(re.fullmatch('[0-9a-f]{64}',first.get('session_scope','')) is not None,'scope label missing')
    if write_smoke:
        stranger=requests.Session();own_id=None;cleaned=False;write_attempted=False
        scene=next((s for s in manifest['scenes'] if (s.get('motion') or {}).get('spectral_configuration')=='strict'),manifest['scenes'][0])
        item={'scene_id':scene['id'],'selection':'target','status':'uncertain',
              'analysis_sha256':manifest['analysis_sha256'],'note':'Disposable goal QA '+uuid.uuid4().hex}
        headers={'Origin':BASE}
        try:
            response=request('/api/reviews',method='POST',json=item,headers={'Origin':'https://unrelated.example'})
            require(response.status_code==403,'cross-origin write accepted')
            write_attempted=True
            response=request('/api/reviews',method='POST',json=item,headers=headers)
            require(response.status_code==200,'disposable review write failed')
            saved=response.json();own_id=saved['review']['review_id']
            require(re.fullmatch('[0-9a-f]{64}',own_id) is not None,'stable review ID missing')
            require(saved['session_scope']==first['session_scope'],'owner scope changed during write')
            expiry=datetime.fromisoformat(saved['review']['expires_at'].replace('Z','+00:00'))
            require(0<(expiry-datetime.now(timezone.utc)).total_seconds()<=181*86400,'review expiry invalid')
            response=request('/api/reviews');rows=response.json()['reviews']
            require(len(rows)==1 and rows[0]['review_id']==own_id and rows[0]['note']==item['note'],'read-back mismatch')
            other=request('/api/reviews',client=stranger).json()
            require(other['reviews']==[] and other['session_scope']!=first['session_scope'],'guest isolation failed')
            response=request('/api/reviews',method='DELETE',client=stranger,json={'review_id':own_id},headers=headers)
            require(response.status_code==200,'cross-owner delete contract')
            response=request('/api/reviews');require(len(response.json()['reviews'])==1,'other owner deleted our review')
            response=request('/api/reviews',method='POST',json={**item,'analysis_sha256':'0'*64},headers=headers)
            require(response.status_code==400,'stale analysis accepted')
            response=request('/api/reviews',method='DELETE',json={'review_id':own_id},headers=headers)
            require(response.status_code==200,'ID-only deletion failed')
            response=request('/api/reviews');require(response.json()['reviews']==[],'cleanup not verified')
            cleaned=True
            report['review_lifecycle']={'stable_id':True,'expiry':True,'scope_isolation':True,
                'cross_origin_rejected':True,'cross_owner_delete_ineffective':True,'stale_post_rejected':True,
                'id_only_delete':True,'cleanup_verified':True}
        finally:
            if write_attempted and not cleaned:
                # Retry only our fresh session's disposable ID/key, even if POST
                # succeeded but its response was interrupted before reading ID.
                body={'review_id':own_id} if own_id else item
                cleanup=session.delete(BASE+'/api/reviews',json=body,headers=headers,timeout=30)
                require(cleanup.status_code==200 and session.get(BASE+'/api/reviews',timeout=30).json()['reviews']==[],
                        'disposable review cleanup failed; manual follow-up required')
            stranger.close()
    else:report['review_lifecycle']={'write_smoke':'not_requested'}
    report['completed_at_utc']=datetime.now(timezone.utc).isoformat();report['passed']=True
    session.close()
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-smoke',action='store_true',help='Create/read/delete one disposable production guest review')
    parser.add_argument('--output',type=Path,help='New receipt path; an existing file is never overwritten')
    args=parser.parse_args()
    args.output=args.output or ROOT/'data/raw/benchmark'/('production-smoke-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]+'.json')
    if args.output.exists():raise RuntimeError('Receipt exists; refusing overwrite')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    report={}
    try:verify(args.write_smoke,report)
    except Exception as exc:
        report.update(passed=False,failure_type=type(exc).__name__,failure_label=str(exc),completed_at_utc=datetime.now(timezone.utc).isoformat())
    with args.output.open('xb') as receipt:receipt.write((json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8'))
    print(json.dumps({'passed':report['passed'],'checks':len(report['checks']),'output':str(args.output),
                      'failure':report.get('failure_label'),'cleanup':report.get('review_lifecycle')},indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
