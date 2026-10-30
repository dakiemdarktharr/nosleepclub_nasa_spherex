"""Post-run accounting audit; never changes sealed fit rules or original results.

The paired runner catches exceptions around both models. Re-run the 0.7 model
alone on every such record so a candidate exception cannot erase a valid
baseline. This is bookkeeping QA on opened data, not a new validation sample.
"""
from pathlib import Path
import numpy as np
from . import covariance_study as s


def main():
    design,_=s.check_design();out=s.OUT/'failure-audit.json'
    if out.exists():raise RuntimeError('Audit already exists')
    corrections=[];inputs={}
    for item in design['fields']['validation']:
        ident=item['field']['id'];path=s.OUT/('validation-'+ident+'.json');original=s.read(path);inputs[path.name]=s.bench.digest(path)
        todo=[(group,i,r) for group in ['real_controls','injections'] for i,r in enumerate(original[group]) if 'fit_exception' in r['models']['previous']['quality_reasons']]
        if not todo:continue
        _,frames,catalog,_=s.old.load(item);regs={r['obs_id']:r for r in original['registrations']}
        index={f['record']['obs_id']:{**f,'offset':np.asarray(regs[f['record']['obs_id']]['offset_px']),
            'offset_cov':np.asarray(regs[f['record']['obs_id']]['covariance_px2'])} for f in frames if f['record']['obs_id'] in regs}
        before,after=[[index[p[e]] for p in item['pairs']] for e in ['before','after']];xy=s.model.previous.positions(catalog,list(index.values()))
        for group,i,r in todo:
            source=None;truth=None;fs=[before,after]
            if group=='real_controls':
                source=next(v['catalog'] for v in item['references'] if v['catalog']['source_id']==r['source_id'])
                anchors=[s.gaia.gaia_xy(source,float(np.mean([f['mjd'] for f in epoch]))) for epoch in fs]
            else:
                truth=r['truth_delta_px'];anchor=r['anchor'];anchors=[anchor,anchor];fs=[]
                for epoch,shift in [(before,np.zeros(2)),(after,np.asarray(truth))]:
                    copies=[]
                    for f in epoch:
                        p=np.asarray(anchor)+shift;stamp=s.motion.native_stamp(f,p);d=s.motion.stamp_model(stamp,p)/stamp['error'][:,None]
                        amplitude=r['snr_per_frame']*np.sqrt(np.linalg.pinv(d.T@d)[0,0])
                        copies.append({**f,'data':f['data']+s.source_image(f,p,amplitude,r['truth_psf'])})
                    fs.append(copies)
            value=s.old.safe_pair(*fs,catalog,xy,anchors,'ir_robust',source=source,truth=truth)
            if 'covariance_arcsec2' in value:
                e=np.asarray(value['error_east_north_arcsec']);c=np.asarray(value['covariance_arcsec2']);value['mahalanobis2_raw']=float(e@np.linalg.pinv(c)@e)
            corrections.append({'field_id':ident,'group':group,'index':i,'previous_audited':value,
                'original_reason':r['models']['previous'].get('reason'),'baseline_recovered':bool(value['numeric_valid'])})
            print('AUDIT',ident,group,i,value['numeric_valid'],value.get('reason'),flush=True)
    s.bench.save(out,{'purpose':'independent baseline exception accounting on already-opened validation data',
        'source_sha256':s.bench.digest(Path(__file__)),'input_sha256':inputs,'corrections':corrections,
        'recovered_baseline':sum(r['baseline_recovered'] for r in corrections),'original_results_modified':False})


if __name__=='__main__':main()
