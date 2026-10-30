"""Exploratory ePSF support-boundary diagnostic on opened-field controls.

Replays draw zero, with frozen fits and final IRLS nuisance projections. Padding is
an intervention on the target template only, not a proposed science calibration.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates, spline_filter

from . import diagnose_bias as d
from . import profile_uncertainty as profile

STEPS = [.00025, .0005, .001, .002, .004, .008, .016]
PAD = 8
EPS = 1e-8
ROOT = d.ROOT
OUT = ROOT / 'data/raw/benchmark/epsf-boundary-development.json'


def objective(residual, p):
    r = residual(p)
    return float(r @ r / 2)


def hessian_objective(fun, point, h):
    """Central difference Hessian for scalar half-chi-square."""
    x = np.asarray(point, float)
    a, b = np.eye(2) * h
    c = fun(x)
    return np.array([[(fun(x+a)-2*c+fun(x-a))/h**2,
                      (fun(x+a+b)-fun(x+a-b)-fun(x-a+b)+fun(x-a-b))/(4*h*h)],
                     [(fun(x+a+b)-fun(x+a-b)-fun(x-a+b)+fun(x-a-b))/(4*h*h),
                      (fun(x+b)-2*c+fun(x-b))/h**2]])


def target_psf(sample, point, padded=False):
    p = sample['native_center'] + sample['jacobian'] @ (np.asarray(point)-sample['anchor'])
    over = sample['frame']['epsf_oversampling']
    coeff = sample['epsf']
    if padded:
        raw = np.asarray(sample['frame']['epsf_table']['EPSF'][sample['zone']], float)
        raw = raw * over**2 / raw.sum()
        coeff = spline_filter(np.pad(raw, PAD), order=3)
    center = (np.array(coeff.shape)-1)/2
    return map_coordinates(coeff, [(sample['y']-p[1])*over+center[0],
                                   (sample['x']-p[0])*over+center[1]],
                           order=3, mode='constant', cval=0, prefilter=False)


def residual(samples, point, padded=False):
    out = []
    for sample in samples:
        q = sample['q']
        p = target_psf(sample, point, padded) / sample['error']
        y = sample['data'] / sample['error']
        p = p-q@(q.T@p); y = y-q@(q.T@y)
        info = p@p
        if info < 1e-15:
            raise ValueError('unidentifiable_target')
        out.append((p@y)/info*p-y)
    return np.concatenate(out)


def crossings(samples, point, direction, limit=.016):
    """Find all support-edge intersections along a sky-pixel displacement."""
    result=[]
    for sample in samples:
        p=sample['native_center']+sample['jacobian']@(point-sample['anchor'])
        over=sample['frame']['epsf_oversampling']
        size=np.array(sample['epsf'].shape)
        coords=np.stack([(sample['y']-p[1])*over+(size[0]-1)/2,
                         (sample['x']-p[0])*over+(size[1]-1)/2])
        velocity=-(sample['jacobian']@direction)[[1,0]]*over
        for axis in range(2):
            if abs(velocity[axis]) < 1e-12: continue
            for side, edge in [('low',0.),('high',float(size[axis]-1))]:
                t=(edge-coords[axis])/velocity[axis]
                other=coords[1-axis]+t*velocity[1-axis]
                hit=np.flatnonzero((np.abs(t)<=limit)&(other>=0)&(other<=size[1-axis]-1))
                for i in hit:
                    result.append({'offset_sky_px':float(t[i]), 'obs_id':sample['frame']['record']['obs_id'],
                        'pixel_xy_native':[float(sample['x'][i]),float(sample['y'][i])],
                        'axis_kernel_yx':axis,'side':side,'other_kernel_coordinate':float(other[i]),
                        'zone':int(sample['zone'])})
    return sorted(result,key=lambda v:abs(v['offset_sky_px']))


def edge_stats(sample):
    over=sample['frame']['epsf_oversampling']
    raw=np.asarray(sample['frame']['epsf_table']['EPSF'][sample['zone']],float)
    raw=raw*over**2/raw.sum()
    edge=np.r_[raw[0,:],raw[-1,:],raw[1:-1,0],raw[1:-1,-1]]
    return {'zone':int(sample['zone']), 'kernel_shape':list(raw.shape), 'oversampling':float(over),
            'edge_abs_max':float(np.max(np.abs(edge))), 'edge_abs_median':float(np.median(np.abs(edge))),
            'kernel_abs_max':float(np.max(np.abs(raw))), 'edge_nonzero_count':int(np.count_nonzero(edge)),
            'edge_count':int(len(edge))}


def inspect_fit(fit):
    samples=fit['samples']; point=np.asarray(fit['position'])
    base=lambda p:residual(samples,p,False)
    padded=lambda p:residual(samples,p,True)
    reference=profile.residual_for(samples)
    discrepancy=float(np.max(np.abs(base(point)-reference(point))))
    if discrepancy > 1e-10: raise RuntimeError('Diagnostic does not reproduce frozen residual')
    hess=[]
    for h in STEPS:
        a=hessian_objective(lambda p:objective(base,p),point,h)
        b=profile.hessian(reference,point,h)
        c=hessian_objective(lambda p:objective(padded,p),point,h)
        hess.append({'step_sky_px':h,'original':a.tolist(),'padded':c.tolist(),
                     'max_formula_difference':float(np.max(np.abs(a-b)))})
    directions={'x':[1.,0.],'y':[0.,1.],'x_plus_y':[1.,1.],'x_minus_y':[1.,-1.]}
    events={}
    for name, vector in directions.items():
        direction=np.array(vector); hits=crossings(samples,point,direction)
        examples=[]
        # Closest events with distinct positions, excluding coincident events.
        for hit in hits:
            t=hit['offset_sky_px']
            if any(abs(t-v['offset_sky_px']) < 4*EPS for v in examples): continue
            left=point+(t-EPS)*direction; right=point+(t+EPS)*direction
            a=objective(base,left); b=objective(base,right)
            ap=objective(padded,left); bp=objective(padded,right)
            sample=next(s for s in samples if s['frame']['record']['obs_id']==hit['obs_id'])
            idx=np.flatnonzero((sample['x']==hit['pixel_xy_native'][0])&(sample['y']==hit['pixel_xy_native'][1]))[0]
            examples.append({**hit,'epsilon_sky_px':EPS,'objective_left':a,'objective_right':b,
                'original_objective_right_minus_left':b-a,'padded_objective_right_minus_left':bp-ap,
                'original_template_left_right':[float(target_psf(sample,left)[idx]),float(target_psf(sample,right)[idx])],
                'padded_template_left_right':[float(target_psf(sample,left,True)[idx]),float(target_psf(sample,right,True)[idx])]})
            if len(examples)>=3:break
        events[name]={'crossing_pixel_count':len(hits),'closest':examples}
    derivative={}
    for name, direction in {'x':np.array([1.,0.]),'y':np.array([0.,1.])}.items():
        derivative[name]=[{'step_sky_px':h,
            'original':(objective(base,point+h*direction)-objective(base,point-h*direction))/(2*h),
            'padded':(objective(padded,point+h*direction)-objective(padded,point-h*direction))/(2*h)} for h in STEPS]
    return {'position_sky_px':point.tolist(),'residual_replay_max_abs':discrepancy,
            'samples':[{'obs_id':s['frame']['record']['obs_id'],'valid_pixels':len(s['data']),**edge_stats(s)} for s in samples],
            'hessians':hess,'directional_derivatives':derivative,'boundary_events':events}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fields',nargs='+',choices=d.RULES['fields'],default=d.RULES['fields'])
    parser.add_argument('--snrs',nargs='+',type=float,choices=[2.,4.],default=[2.,4.])
    parser.add_argument('--output',type=Path,default=OUT)
    args=parser.parse_args()
    previous_path=ROOT/'data/raw/benchmark/bias-gaussian64-development.json'
    previous=json.loads(previous_path.read_text(encoding='utf-8'))
    report={'version':'0.10.0-epsf-boundary-exploratory.1','completed':False,
            'source_sha256':d.digest(__file__),'frozen_sources':d.study.sources(),
            'previous_controls_sha256':d.digest(previous_path),'design_sha256':d.digest(d.study.OUT/'design.json'),
            'seed':d.RULES['seed'],'draw_index':0,'steps_sky_px':STEPS,'pad_oversampled_pixels':PAD,
            'qualification':'Exploratory paired analysis of already opened fields; fixed-final-IRLS weights and nuisance projections. Padding target only does not validate a physical PSF or yield coverage.', 'cases':[]}
    for ident in args.fields:
        print('LOAD',ident,flush=True)
        _,opened,catalog,xy,before,after,source=d.load_field(ident)
        oldfield=next(f for f in previous['fields'] if f['id']==ident)
        for wanted in d.RULES['cases']:
            if wanted['snr_per_frame'] not in args.snrs:continue
            oldcase=next(c for c in oldfield['cases'] if c['snr_per_frame']==wanted['snr_per_frame'])
            anchor=oldcase['anchor']; truth=np.asarray(wanted['motion'])
            planted=d.study.injected_frames(before,after,anchor,truth,wanted['snr_per_frame'],'nearest')
            signals=[[{**a,'data':a['data']-o['data']} for a,o in zip(added,original)] for added,original in zip(planted,[before,after])]
            rng=np.random.default_rng(d.RULES['seed'])
            fs=[[{**f,'data':f['data']+rng.normal(size=f['data'].shape)*np.sqrt(f['variance'])} for f in frames] for frames in signals]
            print('FIT',ident,wanted['snr_per_frame'],flush=True)
            fits=[d.fit_epoch(frames,catalog,xy,anchor) for frames in fs]
            vector=d.study.gaia.TRANSFORM@(fits[1]['position']-fits[0]['position']-truth)
            expected=np.asarray(oldcase['independent_gaussian_controls']['records'][0]['error_east_north_arcsec'])
            error=float(np.max(np.abs(vector-expected)))
            if error>1e-5:raise RuntimeError('Control replay differs: '+str(error))
            case={'field':ident,'source':source,'snr_per_frame':wanted['snr_per_frame'],'truth_delta_sky_px':truth.tolist(),
                  'anchor_sky_px':anchor,'error_replay_max_arcsec':error,'epochs':[inspect_fit(f) for f in fits]}
            report['cases'].append(case);d.save(args.output,report)
            print('DONE',ident,wanted['snr_per_frame'],flush=True)
    report['completed']=True;d.save(args.output,report)
    print('COMPLETE',args.output,flush=True)


if __name__=='__main__':main()
