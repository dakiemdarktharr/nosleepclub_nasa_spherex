"""Small, hashed UI view of immutable quality-study results; no metric tuning."""
from hashlib import sha256
import json
from pathlib import Path
from . import benchmark_accuracy as bench

ROOT=bench.ROOT;OUT=ROOT/'web/data/quality'


def main():
    names=['evaluation-summary.json','development-summary.json','development-barnard.json','development-rw-aur.json']
    payloads={name:json.loads((OUT/name).read_text()) for name in names}
    evaluation=payloads['evaluation-summary.json'];development=payloads['development-summary.json']
    barnard=payloads['development-barnard.json']['real_controls']
    cases=[]
    for filename,ident,label in [('development-barnard.json','4472836876874287744','Sao đối chứng từng lệch 6,31″'),
            ('development-barnard.json','4472832130942575872','Barnard’s Star'),
            ('development-rw-aur.json','156339871888234752','Hai mô hình bất đồng trong trường RW Aur')]:
        record=next(r for r in payloads[filename]['real_controls'] if r['source_id']==ident)
        cases.append({'source_id':ident,'label':label,'models':{kind:{k:v for k,v in r.items() if k in
            ['numeric_valid','accepted','quality_reasons','error_arcsec']} for kind,r in record['models'].items()}})
    overview={'version':'0.7.0','protocol_sha256':evaluation['protocol_sha256'],'passed':evaluation['passed'],
        'default_measurement_changed':False,'fields':evaluation['fields'],'development_fields':development['fields'],'development_cases':cases,
        'input_sha256':{name:bench.digest(OUT/name) for name in names},'source_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
    bench.save(OUT/'overview.json',overview)


if __name__=='__main__':main()
