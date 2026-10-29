"""Explicit production smoke test; uses only this test's disposable guest review."""
import json
from hashlib import sha256
from pathlib import Path
import requests
import truststore

URL='https://nosleepclub-nasa-spherex.vercel.app'


def main():
    truststore.inject_into_ssl()
    session=requests.Session();results={}
    response=session.get(URL,timeout=30);response.raise_for_status()
    results['public_site']=response.status_code
    assert response.url.startswith(URL+'/'), 'Unexpected authentication redirect'
    assert "script-src 'self'" in response.headers['Content-Security-Policy']
    manifest=session.get(URL+'/data/manifest.json',timeout=30).json()
    overview=session.get(URL+'/data/release/overview.json',timeout=30);overview.raise_for_status()
    local=Path(__file__).resolve().parents[1]/'web/data/release'
    assert overview.json()['protocol_sha256']==sha256((local/'protocol.json').read_bytes()).hexdigest()
    assert overview.json()['total_recoveries']==1440
    for name in ['broad','strict']:
        deployed=session.get(URL+'/data/release/'+name+'.json',timeout=30);deployed.raise_for_status()
        assert sha256(deployed.content).hexdigest()==sha256((local/(name+'.json')).read_bytes()).hexdigest()
    results['locked_science_products_match']=True
    for asset in ['brown-dwarf-canva.webp','compare-guide-canva.webp']:
        deployed=session.get(URL+'/assets/'+asset,timeout=30);deployed.raise_for_status()
        assert deployed.content.startswith(b'RIFF') and b'WEBP' in deployed.content[:16]
    results['canva_assets']=True
    fonts=Path(__file__).resolve().parents[1]/'web/assets/fonts'
    provenance=json.loads((fonts/'provenance.json').read_text())
    for record in provenance['files']:
        deployed=session.get(URL+'/assets/fonts/'+record['file'],timeout=30);deployed.raise_for_status()
        assert deployed.content.startswith(b'wOF2')
        assert sha256(deployed.content).hexdigest()==record['sha256']
    results['vietnamese_fonts_match']=True
    response=session.get(URL+'/api/reviews',timeout=30);results['storage_get']=response.status_code
    assert response.status_code==200, response.text
    assert response.json()['storage']=='mongodb'
    assert response.json()['reviews']==[]
    cookie=response.headers.get('Set-Cookie','')
    assert all(k in cookie for k in ['Secure','HttpOnly','SameSite=Strict','__Host-'])
    scene=manifest['scenes'][0]
    item={'scene_id':scene['id'],'selection':'target','status':'uncertain',
          'analysis_sha256':manifest['analysis_sha256'],'note':'Disposable deployment QA; remove after verification.'}
    headers={'Origin':URL}
    created=False
    try:
        response=session.post(URL+'/api/reviews',json=item,headers={'Origin':'https://unrelated.example'},timeout=30)
        results['cross_origin_rejected']=response.status_code
        assert response.status_code==403
        response=session.post(URL+'/api/reviews',json=item,headers=headers,timeout=30)
        results['write']=response.status_code
        assert response.status_code==200, response.text
        created=True
        fetched=session.get(URL+'/api/reviews',timeout=30).json()['reviews']
        assert len(fetched)==1 and fetched[0]['note']==item['note']
        results['read_back']=True
        stranger=requests.get(URL+'/api/reviews',timeout=30)
        assert stranger.status_code==200 and stranger.json()['reviews']==[]
        results['session_isolation']=True
        stale={**item,'analysis_sha256':'old'}
        response=session.post(URL+'/api/reviews',json=stale,headers=headers,timeout=30)
        results['stale_provenance_rejected']=response.status_code
        assert response.status_code==400
    finally:
        if created:
            response=session.delete(URL+'/api/reviews',json=item,headers=headers,timeout=30)
            results['delete_test_review']=response.status_code
            assert response.status_code==200
            assert session.get(URL+'/api/reviews',timeout=30).json()['reviews']==[]
            results['cleanup_verified']=True
    results['analysis_sha256']=manifest['analysis_sha256']
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
