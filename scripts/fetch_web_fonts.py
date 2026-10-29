"""Vendor the Vietnamese and Latin Be Vietnam Pro subsets with source/license."""
from hashlib import sha256
import json
from pathlib import Path
import re
import requests
import truststore

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'web/assets/fonts'
CSS_URL='https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap'
LICENSE_URL='https://raw.githubusercontent.com/google/fonts/main/ofl/bevietnampro/OFL.txt'


def main():
    truststore.inject_into_ssl();OUT.mkdir(parents=True,exist_ok=True)
    response=requests.get(CSS_URL,headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'},timeout=30)
    response.raise_for_status();faces=[];records=[]
    for subset,block in re.findall(r'/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{.*?\})',response.text,re.S):
        if subset not in ['latin','vietnamese']:continue
        weight=re.search(r'font-weight:\s*(\d+)',block).group(1)
        url=re.search(r'url\((https://fonts\.gstatic\.com/[^)]+)\)',block).group(1)
        result=requests.get(url,timeout=30);result.raise_for_status()
        if not result.content.startswith(b'wOF2'):raise ValueError('Expected WOFF2 from Google Fonts')
        name=f'be-vietnam-pro-{weight}-{subset}.woff2';(OUT/name).write_bytes(result.content)
        faces.append(f'/* {subset} */\n'+block.replace(url,'./'+name))
        records.append({'file':name,'subset':subset,'weight':int(weight),'source':url,'sha256':sha256(result.content).hexdigest(),'bytes':len(result.content)})
    if len(records)!=10:raise ValueError(f'Expected ten static font subsets, got {len(records)}: {response.text[:700]}')
    license=requests.get(LICENSE_URL,timeout=30);license.raise_for_status();(OUT/'OFL.txt').write_bytes(license.content)
    (OUT/'be-vietnam-pro.css').write_text('\n\n'.join(faces)+'\n',encoding='utf-8',newline='\n')
    (OUT/'provenance.json').write_text(json.dumps({'family':'Be Vietnam Pro','stylesheet_source':CSS_URL,'license_source':LICENSE_URL,
        'license_sha256':sha256(license.content).hexdigest(),'files':records},indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'Vendored {len(records)} font subsets, {sum(r["bytes"] for r in records)} bytes; SIL OFL included')


if __name__=='__main__':main()
