"""Paired, spatial-cluster bootstrap of the frozen A/B diagnostics.

Post-hoc uncertainty summary, not a new test set or a hyperparameter search.
"""
from hashlib import sha256
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
DIRECTORY=ROOT/'web/data/joint'


def summarize(payload,draws=2000):
    records=payload['result']['records'];groups=[]
    for flux in payload['protocol']['control_flux_scales']:
        pairs=[]
        for single in records:
            if single['model']!='single' or single['flux_scale']!=flux:continue
            other=next(r for r in records if r['model']=='joint' and r['flux_scale']==flux
                       and r['position_index']==single['position_index'] and r['truth_delta_px']==single['truth_delta_px'])
            if single['valid'] and other['valid']:
                pairs.append((single['position_index'],np.sum(np.array(single['error_east_north_arcsec'])**2),
                              np.sum(np.array(other['error_east_north_arcsec'])**2)))
        pairs=np.array(pairs);patches=np.unique(pairs[:,0]);rng=np.random.default_rng(20261030)
        single=float(np.sqrt(pairs[:,1].mean()));joint=float(np.sqrt(pairs[:,2].mean()))
        bootstrap=[]
        for _ in range(draws):
            selection=rng.choice(patches,len(patches),replace=True)
            sample=np.concatenate([pairs[pairs[:,0]==p,1:] for p in selection])
            bootstrap.append(100*(1-np.sqrt(sample[:,1].mean()/sample[:,0].mean())))
        groups.append({'flux_scale':flux,'common_valid_pairs':len(pairs),'spatial_patches':len(patches),
            'single_paired_rms_arcsec':single,'joint_paired_rms_arcsec':joint,
            'relative_rms_improvement_percent':100*(1-joint/single),
            'spatial_bootstrap_95_interval_percent':np.quantile(bootstrap,[.025,.975]).tolist()})
    return {'spectral_configuration':payload['result']['spectral_configuration'],'groups':groups}


def main():
    paths=[DIRECTORY/(name+'.json') for name in ['broad','strict']]
    output={'source_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
            'input_sha256':{p.name:sha256(p.read_bytes()).hexdigest() for p in paths},
            'draws':2000,'method':'paired common-valid fits; resample spatial patches, not individual injections',
            'qualification':'Post-hoc diagnostic interval with only 12 correlated patches; failures reported separately; not a significance test or population guarantee.',
            'configurations':[summarize(json.loads(p.read_text())) for p in paths]}
    (DIRECTORY/'summary.json').write_text(json.dumps(output,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(output['configurations'],indent=2))


if __name__=='__main__':main()
