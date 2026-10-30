"""Compact UI views of immutable ablation and sealed external-validation data."""
from pathlib import Path
from . import ablation_study as s


def comparison(rows,selected):
    out=s.uncertainty_summary(rows,selected)
    for cell,value in out['cells'].items():
        common=[r for r in rows if r.get('calibration_cell')==cell and all(r['models'][selected].get(k,{}).get('supported') for k in ['global_calibration','conditional_calibration'])]
        value['common_supported']={k:s.calibration_stats(common,selected,name) for k,name in [('global','global_calibration'),('conditional','conditional_calibration')]}
    return out


def diagnostic_patch(rows,fields,selected):
    groups={}
    for r in rows:
        v=r['models'][selected]
        if v['accepted'] and v.get('conditional_calibration',{}).get('supported'):groups.setdefault((r['field_id'],r['patch_index']),[]).append(r)
    if not groups:return None
    def score(item):
        return sum(r['models'][selected]['conditional_calibration']['mahalanobis2']<=s.cc.RULES['ellipse68_threshold'] for r in item[1])/len(item[1]),-len(item[1])
    (ident,patch),trials=min(groups.items(),key=score);anchor=trials[0]['anchor'];errors=[r['models'][selected]['error_arcsec'] for r in trials]
    return {'field':next(f['field'] for f in fields if f['field']['id']==ident),'patch_index':patch,'anchor_px':anchor,
        'map_center_px':[anchor[0]+64.5,127.5-anchor[1]],'map_shape':[192,192],
        'attempted_accepted_supported':len(trials),'covered68':sum(r['models'][selected]['conditional_calibration']['mahalanobis2']<=s.cc.RULES['ellipse68_threshold'] for r in trials),
        'error_range_arcsec':[min(errors),max(errors)],'qualification':'post-validation undercoverage diagnostic, original background image without injected source; correlated trials on one patch'}


def main():
    out=s.OUT;names=['design.json','selection.json','calibrator.json','validation-protocol.json','development-summary.json','calibration-summary.json','validation-summary.json']
    source={n:s.read(out/n) for n in names};selected=source['selection.json']['selected_model'];development=[];validation=[];all_dev=[]
    real_dev=[];val_rows=[];val_real=[]
    for item in source['design.json']['fields']['development']:
        name='development-'+item['field']['id']+'.json';r=s.read(out/name);names.append(name);all_dev.extend(r['injections']);real_dev.extend(r['real_controls'])
        development.append({'field':r['field'],'samples':{sample:{k:{'summary':s.stats(r[key],k,'numeric_valid'),
            'accepted':s.stats(r[key],k,'accepted'),'paired':s.paired(r[key],k,'numeric_valid')} for k in s.KINDS}
            for sample,key in [('injections','injections'),('real','real_controls')]}})
    samples={sample:{k:{'summary':s.stats(rows,k,'numeric_valid'),'accepted':s.stats(rows,k,'accepted'),'paired':s.paired(rows,k,'numeric_valid')}
        for k in s.KINDS} for sample,rows in [('injections',all_dev),('real',real_dev)]}
    for item in source['design.json']['fields']['validation']:
        name='validation-'+item['field']['id']+'.json';r=s.read(out/name);names.append(name);val_rows.extend(r['injections']);val_real.extend(r['real_controls'])
        validation.append({'field':r['field'],'injections':comparison(r['injections'],selected),'real':comparison(r['real_controls'],selected),
            'point_injections':s.point_check(r['injections'],selected,8),'point_real':s.point_check(r['real_controls'],selected,3),
            'unavailable':r['unavailable']})
    payload={'version':'0.9.0','selected_model':selected,'selection':source['selection.json'],'ablation':{'all':samples,'fields':development},
        'calibrator':source['calibrator.json'],'calibration_summary':source['calibration-summary.json'],
        'validation':{'fields':validation,'injections':comparison(val_rows,selected),'real':comparison(val_real,selected)},
        'diagnostic_patch':diagnostic_patch(val_rows,validation,selected),
        'passed':source['validation-summary.json']['passed'],'coverage_gate':source['validation-summary.json']['coverage_gate'],
        'point_passed':source['validation-summary.json']['point_passed'],'lock_commit':source['validation-summary.json']['lock_commit'],
        'validation_protocol_sha256':source['validation-summary.json']['validation_protocol_sha256'],
        'current_measurement_changed':False,'input_sha256':{n:s.bench.digest(out/n) for n in names},'source_sha256':s.bench.digest(Path(__file__)),
        'guard_sha256':s.bench.digest(s.ROOT/'scripts/run_ablation.py')}
    s.bench.save(out/'overview.json',payload)


if __name__=='__main__':main()
