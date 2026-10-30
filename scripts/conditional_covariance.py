"""Empirical S/N/background calibration with disjoint floor/quantile patches.

No distribution-free conditional-coverage guarantee is claimed. Unsupported
features cause abstention; labels and known errors never enter routing.
"""
import numpy as np
from .covariance_model import positive_part

RULES={'version':'0.9.0','snr_cut':10.,'background_cut':1.5,'probability':.68,
    'background_cut_source':'feature-only development patch median, frozen in selection; default used only in standalone controls',
    'ellipse68_threshold':2.27886856637673,'ellipse95_threshold':5.99146454710798,
    'minimum_rows_per_partition':12,'minimum_blocks_per_partition':3,'minimum_fields_per_partition':2,
    'shrinkage_pseudo_blocks':8.,'minimum_floor_arcsec':.05,'floor_strength_grid':[i/10 for i in range(11)],
    'support_multiplicative_margin':1.25,'floor_patch_parity':0,'quantile_patch_parity':1,
    'bias_subtraction':False,'covariance_shrinking':False}
CELLS=['snr_low_bg_smooth','snr_low_bg_structured','snr_high_bg_smooth','snr_high_bg_structured']


def classify(features,cuts=None):
    cuts=RULES if cuts is None else cuts
    snr=features.get('observed_snr');bg=features.get('background_score')
    if snr is None or bg is None or not np.isfinite(snr+bg) or min(snr,bg)<=0:return None
    return ('snr_low' if snr<cuts['snr_cut'] else 'snr_high')+('_bg_smooth' if bg<cuts['background_cut'] else '_bg_structured')


def subset(rows,node,cuts=None):
    if node=='global':return rows
    return [r for r in rows if classify(r['features'],cuts)==node or node in ['snr_low','snr_high'] and classify(r['features'],cuts).startswith(node+'_')]


def support(rows):
    return {'rows':len(rows),'blocks':len({(r['field_id'],r['patch_index']) for r in rows}),
        'fields':len({r['field_id'] for r in rows})}


def enough(rows):
    s=support(rows)
    return s['rows']>=RULES['minimum_rows_per_partition'] and s['blocks']>=RULES['minimum_blocks_per_partition'] and s['fields']>=RULES['minimum_fields_per_partition']


def weights(rows):
    fields=sorted({r['field_id'] for r in rows});blocks={(r['field_id'],r['patch_index']) for r in rows}
    return np.array([1/(len(fields)*sum(b[0]==r['field_id'] for b in blocks)*sum(v['field_id']==r['field_id'] and v['patch_index']==r['patch_index'] for v in rows)) for r in rows])


def raw_floor(rows):
    excess=[np.outer(r['error'],r['error'])-np.asarray(r['covariance']) for r in rows]
    return positive_part(np.einsum('i,ijk->jk',weights(rows),np.asarray(excess)))


def matrix(raw,parameters):
    return parameters['scale_squared']*(np.asarray(raw)+np.eye(2)*RULES['minimum_floor_arcsec']**2+
        parameters['floor_strength']*np.asarray(parameters['floor_arcsec2']))


def scores(rows,parameters):
    return np.array([np.asarray(r['error'])@np.linalg.solve(matrix(r['covariance'],parameters),r['error']) for r in rows])


def fit_quantile(rows,floor):
    w=weights(rows);parameters={'floor_arcsec2':np.asarray(floor).tolist(),'floor_strength':1.,'scale_squared':1.}
    for alpha in RULES['floor_strength_grid']:
        parameters['floor_strength']=alpha
        if np.sum(w*(scores(rows,parameters)<=RULES['ellipse68_threshold']))>=RULES['probability']:break
    else:
        q=scores(rows,parameters);order=np.argsort(q);rank=min(len(q)-1,int(np.searchsorted(np.cumsum(w[order]),RULES['probability'])))
        parameters['scale_squared']=max(1.,float(q[order[rank]]/RULES['ellipse68_threshold']))
    return parameters


def fit(records,selected,thresholds=None):
    if any(r['phase']!='calibration' for r in records):raise ValueError('Only calibration records may fit uncertainty')
    rows=[];cuts={k:RULES[k] for k in ['snr_cut','background_cut']} if thresholds is None else thresholds
    if any(not np.isfinite(cuts[k]) or cuts[k]<=0 for k in ['snr_cut','background_cut']):raise ValueError('Invalid observed-feature thresholds')
    for r in records:
        v=r['models'][selected];features={'observed_snr':v.get('observed_snr'),'background_score':r['background']['score']}
        if not v['accepted'] or classify(features,cuts) is None:continue
        rows.append({'field_id':r['field_id'],'patch_index':r['patch_index'],'features':features,
            'error':v['error_east_north_arcsec'],'covariance':v['covariance_arcsec2']})
    nodes={}
    for node in ['global','snr_low','snr_high',*CELLS]:
        population=subset(rows,node,cuts);floor_rows=[r for r in population if r['patch_index']%2==RULES['floor_patch_parity']]
        scale_rows=[r for r in population if r['patch_index']%2==RULES['quantile_patch_parity']]
        parent=None if node=='global' else ('global' if node in ['snr_low','snr_high'] else node.split('_bg_')[0])
        if enough(floor_rows) and enough(scale_rows):
            local=raw_floor(floor_rows);strength=1. if parent is None else support(floor_rows)['blocks']/(support(floor_rows)['blocks']+RULES['shrinkage_pseudo_blocks'])
            floor=local if parent is None else strength*local+(1-strength)*np.asarray(nodes[parent]['parameters']['floor_arcsec2'])
            params=fit_quantile(scale_rows,floor);source=node;domain=population
        elif parent is not None:
            params=nodes[parent]['parameters'].copy();strength=0.;source=nodes[parent]['parameter_source'];domain=subset(rows,source,cuts)
        else:raise ValueError('Insufficient calibration floor/quantile fields and blocks')
        ranges={key:[float(min(r['features'][key] for r in domain)),float(max(r['features'][key] for r in domain))] for key in ['observed_snr','background_score']}
        nodes[node]={'parameters':params,'parameter_source':source,'parent':parent,'local_fitted':source==node,
            'local_floor_weight':float(strength),'floor_support':support(floor_rows),'quantile_support':support(scale_rows),
            'feature_ranges':ranges,'population_support':support(population)}
    return {'version':RULES['version'],'selected_model':selected,'rules':RULES,'thresholds':cuts,'accepted_usable':len(rows),'attempted':len(records),'nodes':nodes,
        'formula':'C_cal = scale_squared * (C_raw + 0.05^2 I + floor_strength F)',
        'partition':'even spatial patch indices fit floor; odd patch indices fit strength/scale; shared exposures remain correlated',
        'qualification':'empirical grouped calibration, not a conformal or astronomical detection guarantee'}


def apply(raw,features,calibrator,conditional=True):
    cell=classify(features,calibrator['thresholds'])
    if cell is None:return {'supported':False,'reason':'missing_observed_features','cell':None}
    node=calibrator['nodes'][cell if conditional else 'global'];margin=RULES['support_multiplicative_margin']
    outside=[key for key,(lo,hi) in node['feature_ranges'].items() if not lo/margin<=features[key]<=hi*margin]
    if outside:return {'supported':False,'reason':'outside_calibration_range','outside_features':outside,'cell':cell,'parameter_source':node['parameter_source']}
    return {'supported':True,'cell':cell,'parameter_source':node['parameter_source'],
        'pooled':node['parameter_source']!=cell if conditional else False,'covariance_arcsec2':matrix(raw,node['parameters']).tolist()}
