"""Small UI payload and spatial-cluster uncertainty for the frozen experiment."""
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
from . import gaia_motion as gaia

ROOT=Path(__file__).resolve().parents[1]
DIRECTORY=ROOT/'web/data/release'


def paired_interval(records,group,draws=2000):
    lookup={(r['position_index'],tuple(r['truth_delta_px'])):r for r in records if r['model']=='single_nearest' and r['truth_psf']==group['truth_psf'] and r['flux_scale']==group['flux_scale']}
    pairs=[]
    for r in records:
        if r['model']!=group['model'] or r['truth_psf']!=group['truth_psf'] or r['flux_scale']!=group['flux_scale']:continue
        b=lookup[r['position_index'],tuple(r['truth_delta_px'])]
        if r['valid'] and b['valid']:pairs.append([r['position_index'],sum(x*x for x in b['error_east_north_arcsec']),sum(x*x for x in r['error_east_north_arcsec'])])
    pairs=np.array(pairs);patches=np.unique(pairs[:,0]);rng=np.random.default_rng(20261031)
    estimates=[]
    for _ in range(draws):
        sample=np.concatenate([pairs[pairs[:,0]==p,1:] for p in rng.choice(patches,len(patches),replace=True)])
        estimates.append(100*(1-np.sqrt(sample[:,1].mean()/sample[:,0].mean())))
    return {'common_valid_pairs':len(pairs),'spatial_patches':len(patches),'improvement_95_interval_percent':np.quantile(estimates,[.025,.975]).tolist()}


def main():
    protocol=json.loads((DIRECTORY/'protocol.json').read_text());payloads=[json.loads((DIRECTORY/(name+'.json')).read_text()) for name in ['broad','strict']]
    summary={'source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'protocol_sha256':sha256((DIRECTORY/'protocol.json').read_bytes()).hexdigest(),
             'input_sha256':{name+'.json':sha256((DIRECTORY/(name+'.json')).read_bytes()).hexdigest() for name in ['broad','strict']},
             'bootstrap_draws':2000,'qualification':'Post-hoc paired common-valid diagnostic; bootstrap spatial patches; shared exposures and only one field. Not a detection significance.',
             'groups':[],'point_estimate_gate_passed':[]}
    for p in payloads:
        r=p['result']
        for g in r['groups']:
            if g['model']=='single_nearest':continue
            summary['groups'].append({'spectral_configuration':r['spectral_configuration'],**g,**paired_interval(r['records'],g)})
    for model in ['ir_nearest','ir_bilinear']:
        passed=True
        for p in payloads:
            for g in [g for g in p['result']['groups'] if g['model']==model]:
                b=next(b for b in p['result']['groups'] if b['model']=='single_nearest' and b['truth_psf']==g['truth_psf'] and b['flux_scale']==g['flux_scale'])
                passed &= g['paired_improvement_percent']>0 and g['valid']>=b['valid']
        if passed:summary['point_estimate_gate_passed'].append(model)
    gaia.save_json(DIRECTORY/'summary.json',summary)
    gaia.save_json(DIRECTORY/'overview.json',{'analysis_version':'0.5.0','locked_commit':'581de3342788563226368e567e86c413f29e0d0b','protocol_sha256':summary['protocol_sha256'],
        'catalog_screening':protocol['catalog_screening'],'positions_px':protocol['positions_px'],
        'source_coverage':{k:{q:v for q,v in protocol['discovery'][k].items() if q not in ['records','params']} for k in ['qr3','qr3-tap']},
        'rules':protocol['rules'],'total_recoveries':sum(len(p['result']['records']) for p in payloads),
        'point_estimate_gate_passed':summary['point_estimate_gate_passed']})
    print('Point-estimate gate:',summary['point_estimate_gate_passed'])
    for p in payloads:
        print(p['result']['spectral_configuration'])
        for g in p['result']['groups']:print(g['truth_psf'],g['flux_scale'],g['model'],'rms',round(g['rms_arcsec'],3),'valid',g['valid'],'paired%',round(g['paired_improvement_percent'],2),'coverage',g['within_68_ellipse'])


if __name__=='__main__':main()
