"""Post-hoc fixed-weight profile replay at saved strict-after modes only.

No optimization, new Monte Carlo, spectral prediction, or new fields. The
published result is descriptive and conditional, not astrometric truth.
"""
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import numpy as np
from astropy import units as u

from . import linked_epoch_model as model
from . import run_wise_linked_study as study
from . import wise_linked_inputs as inputs
from .native_flux_template import native_flux_template
from .wcs_pixel_area import wcs_pixel_area


ROOT=study.ROOT
RAW=ROOT/'data/raw/benchmark/linked-wise-development.json'
OUT=ROOT/'web/data/linked-flux/mode-diagnostics.json'
RAW_SHA='a5bffe162ae8ccd88a6fc5311d1e8ddc279c56092b072a782652da5a7f1cfd0a'
VARIANTS=('independent','shared_r7_68_a0')
RTOL=1e-7
ATOL=1e-8


def verify_close(actual, expected, label):
    a=np.asarray(actual,float); b=np.asarray(expected,float)
    if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all() or not np.allclose(a,b,rtol=RTOL,atol=ATOL):
        raise ValueError('replay mismatch: '+label)
    return float(np.max(np.abs(a-b))) if a.size else 0.


def calibration_summary(sample):
    frame=sample['frame']; zone=int(sample['zone'])
    row=frame['epsf_table'][zone]; raw=np.asarray(row['EPSF'],float)
    scale=float(frame['epsf_oversampling']); total=float(raw.sum());absolute=float(np.abs(raw).sum())
    if not np.isfinite(raw).all() or not np.isfinite([scale,total,absolute]).all() or total<=0 or absolute<=0:
        raise ValueError('invalid ePSF table')
    yy,xx=np.indices(raw.shape);cx=(raw.shape[1]-1)/2;cy=(raw.shape[0]-1)/2
    return {'zone':zone,'calibration_source':json.loads(frame['epsf_provenance']),
            'nstar':int(row['NSTAR']),'neff_mean':float(row['NEFF_MEAN']),
            'cwave_um':float(row['CWAVE']),'cband_um':float(row['CBAND']),
            'oversampling':scale,'raw_signed_sum':total,
            'raw_negative_absolute_fraction':float(np.abs(raw[raw<0]).sum()/absolute),
            'raw_signed_centroid_native_px':[float(np.sum((xx-cx)*raw)/total/scale),
                                             float(np.sum((yy-cy)*raw)/total/scale)],
            'qualification':'signed table centroid and negative fraction, not a physical centroid correction'}


def frame_diagnostic(problem, prepared, record, frame_index, position, profile):
    item=prepared[frame_index]; sample=item['sample']; frame=sample['frame']; base=problem.frames[frame_index]
    native=inputs.native_position(frame,position)
    area=wcs_pixel_area(frame['wcs'],native,provenance=item['renderer_provenance'])
    if not area.supported:raise ValueError('WCS area refinement unsupported at saved mode')
    rendered=native_flux_template(frame['epsf_table']['EPSF'][sample['zone']],
        oversampling_x=int(frame['epsf_oversampling']),oversampling_y=int(frame['epsf_oversampling']),
        source_xy=native,selection_mask=item['selection_mask'],source_omega=area.solid_angle,
        source_omega_provenance=item['renderer_provenance'],epsf_provenance=frame['epsf_provenance'])
    residual=profile['residuals'][frame_index]; standardized=residual/base['error']
    weights=problem.blocks[frame_index][0]
    x=np.asarray(sample['x']);y=np.asarray(sample['y']); radius=2.5
    core=(x-native[0])**2+(y-native[1])**2<=radius**2
    gy,gx=np.mgrid[int(np.floor(native[1]-radius)):int(np.ceil(native[1]+radius))+1,
                   int(np.floor(native[0]-radius)):int(np.ceil(native[0]+radius))+1]
    geometric=(gx-native[0])**2+(gy-native[1])**2<=radius**2
    inside=geometric&(gx>=0)&(gy>=0)&(gx<frame['data'].shape[1])&(gy<frame['data'].shape[0])
    fullsample=np.zeros_like(inside);source=np.zeros_like(inside)
    flags=frame['flags'][gy[inside],gx[inside]].astype(np.uint64)
    fullsample[inside]=(flags & np.uint64(1<<12))!=0
    source[inside]=(flags & np.uint64(1<<21))!=0
    _,white,q,_,_,_=problem.blocks[frame_index]
    template=rendered.template_per_jy.to_value(u.MJy/u.sr/u.Jy)*white
    projection=template-q@(q.T@template)
    norm=float(template@template)
    if norm<=0:raise ValueError('nonpositive source information')
    absolute=float(np.abs(rendered.normalized_lattice).sum())
    flux=float(profile['per_frame_flux_jy'][frame_index]);err=float(profile['per_frame_error_jy'][frame_index])
    if not np.isfinite([flux,err,absolute]).all() or err<=0 or absolute<=0:
        raise ValueError('invalid frame diagnostics')
    retained=set(sample['neighbour_ids'])
    neighbours=[{'id':str(sid),'sky_grid_xy':np.asarray(xy,float).tolist(),
                 'distance_to_mode_sky_px':float(np.linalg.norm(np.asarray(xy,float)-position))}
                for sid,xy in sample['neighbours'] if sid in retained]
    return {'obs_id':item['obs_id'],'cutout_url':record['cutout_url'],'raw_sha256':record['raw_sha256'],
            'native_position_xy':native.tolist(),'selected_pixel_count':len(x),
            'selected_pixels':{'x':x.astype(int).tolist(),'y':y.astype(int).tolist(),
                               'error_mjysr':base['error'].tolist(),'final_irls_weight':weights.tolist(),
                               'raw_standardized_residual':standardized.tolist()},
            'weighted_chi2':float(np.sum(weights*standardized**2)),
            'raw_chi2':float(np.sum(standardized**2)),
            'flux_jy':flux,'conditional_flux_error_jy':err,'conditional_flux_snr':flux/err,
            'core':{'radius_native_px':radius,'geometric_count':int(geometric.sum()),
                    'in_image_count':int(inside.sum()),'selected_count':int(core.sum()),
                    'coverage':float(core.sum()/geometric.sum()),
                    'raw_standardized_residual_rms':float(np.sqrt(np.mean(standardized[core]**2))) if core.any() else None,
                    'fullsample_flag_count_in_image_core':int(fullsample.sum()),
                    'source_flag_count_in_image_core':int(source.sum())},
            'nuisance_rank':int(profile['nuisance_ranks'][frame_index]),
            'fixed_neighbours':neighbours,
            'fixed_weight_projected_source_information_fraction':float(projection@projection/norm),
            'epsf':calibration_summary(sample),
            'rendering':{'full_lattice_signed_sum':float(rendered.normalized_lattice.sum()),
                         'full_lattice_negative_absolute_fraction':float(np.abs(rendered.normalized_lattice[rendered.normalized_lattice<0]).sum()/absolute),
                         'native_sum_before_normalization':rendered.native_sum_before_normalization,
                         'signed_selected_fraction':rendered.signed_selected_sum,
                         'solid_angle_sr':float(area.solid_angle.to_value(u.sr)),
                         'area_refinement_relative_difference':area.relative_difference,
                         'support_truncated_by_image':rendered.support_truncated_by_image}}


def build():
    if study.lab.digest(RAW)!=RAW_SHA:raise ValueError('raw study SHA-256 mismatch')
    protocol=study.verify_design()
    raw=json.loads(RAW.read_text(encoding='utf-8'))
    if not raw['completed'] or raw['counts']['recorded_epoch_attempts']!=28:
        raise ValueError('raw study is incomplete')
    if raw['protocol_sha256']!=study.lab.digest(study.DESIGN) or raw['source_hashes']!=protocol['sources']:
        raise ValueError('study design/source provenance mismatch')
    records=[]
    for variant in VARIANTS:
        rows=[r for r in raw['records'] if r['configuration']=='strict' and r['epoch']=='after' and r['variant']==variant]
        if len(rows)!=1 or rows[0]['status']!='fit_completed':raise ValueError('saved target attempt missing')
        r=rows[0]
        if r['record_sha256']!=sha256(study.encoded({k:v for k,v in r.items() if k!='record_sha256'})).hexdigest():
            raise ValueError('saved record checksum mismatch')
        records.append(r)
    frames,_=inputs.read_verified_frames()
    groups,catalog,xy,_=inputs.configuration(frames,'strict')
    prepared=inputs.prepared_samples(groups[1],catalog,xy,np.asarray(study.RULES['anchor_sky_grid_px']))
    output=[]
    for record in records:
        fit=record['fit'];variant=next(v for v in study.VARIANTS if v['id']==record['variant'])
        if len(prepared)!=2 or [p['obs_id'] for p in prepared]!=record['obs_ids']:
            raise ValueError('epoch observation list mismatch')
        for item,old in zip(prepared,record['samples']):
            if (item['obs_id']!=old['obs_id'] or int(item['sample']['zone'])!=old['epsf_zone']
                    or item['sample']['frame']['record']['sha256']!=old['raw_sha256']
                    or item['sample']['frame']['record']['cutout_url']!=old['cutout_url']):
                raise ValueError('sample identity/provenance mismatch')
            for a,b,name in [(item['sample']['x'],old['x'],'x'),(item['sample']['y'],old['y'],'y'),
                             (item['error'],old['error_mjysr'],'error')]:
                if not np.array_equal(a,b):raise ValueError('sample '+name+' mismatch')
        packed=study.packed_samples(prepared,record['predictions'],variant)
        problem=model.EpochProblem(packed,data_unit='MJy/sr',mode=variant['mode'])
        problem.set_weights(fit['weights'])
        modes=fit['final_mode_audit']['near_best_modes']
        if len(modes)!=2:raise ValueError('expected exactly two saved near-best modes')
        point=problem.profile(fit['position'])
        residual=point['weighted_residual'];point_chi=float(residual@residual)
        replay={'point_weighted_chi2_abs_diff':verify_close(point_chi,fit['chi2_weighted'],'point chi2'),
                'flux_parameters_jy_max_abs_diff':verify_close(point['flux_parameters_jy'],fit['flux_parameters_jy'],'point flux parameters'),
                'frame_flux_jy_max_abs_diff':verify_close(point['per_frame_flux_jy'],fit['per_frame_flux_jy'],'point frame flux'),
                'frame_error_jy_max_abs_diff':verify_close(point['per_frame_error_jy'],fit['per_frame_error_jy'],'point frame error'),
                'weighted_residual_max_abs_diff':verify_close(point['weighted_residual'],fit['weighted_residual'],'point residual')}
        results=[]
        for index,mode in enumerate(modes):
            position=np.asarray(mode['position'],float)
            prof=problem.profile(position)
            chi=float(prof['weighted_residual']@prof['weighted_residual'])
            replay['mode_'+str(index)+'_weighted_chi2_abs_diff']=verify_close(chi,mode['chi2'],'mode chi2')
            row={'position_sky_px':position.tolist(),'saved_weighted_chi2':mode['chi2'],'replayed_weighted_chi2':chi,
                 'saved_delta_chi2':mode['delta_chi2'],'frames':[
                     frame_diagnostic(problem,prepared,s,i,position,prof) for i,s in enumerate(record['samples'])]}
            verify_close(sum(f['weighted_chi2'] for f in row['frames']),chi,'frame chi2 sum')
            results.append(row)
        frame_deltas=[]
        for first,second in zip(results[0]['frames'],results[1]['frames']):
            if first['obs_id']!=second['obs_id']:raise ValueError('mode frame mismatch')
            frame_deltas.append({'obs_id':first['obs_id'],
                'weighted_chi2_mode1_minus_mode0':second['weighted_chi2']-first['weighted_chi2'],
                'raw_chi2_mode1_minus_mode0':second['raw_chi2']-first['raw_chi2']})
        output.append({'variant':record['variant'],'record_sha256':record['record_sha256'],
                       'position_replay':replay,'modes':results,'frame_deltas':frame_deltas})
    source=Path(__file__)
    return {'stage':'posthoc_fixed_weight_saved_mode_replay','raw_study_sha256':RAW_SHA,
            'protocol_sha256':raw['protocol_sha256'],'protocol_commit':raw['protocol_commit'],
            'frozen_source_hashes':raw['source_hashes'],'input_hashes':raw['input_hashes'],
            'diagnostic_source_sha256':study.lab.digest(source),
            'diagnostic_git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'tolerance':{'rtol':RTOL,'atol':ATOL},'configuration':'strict','epoch':'after',
            'qualification':['Post hoc on already opened data; only two saved near-best modes per variant.',
                'Fixed final IRLS weights, diagonal noise, profiled nuisance and flux; no optimization or new Monte Carlo.',
                'Per-frame chi-square differences can cancel; shared flux couples exposures, so contributions do not prove causation.',
                'ePSF QR3 table shape/centroid and negative wings are descriptive, not physical truth or a correction.',
                'Fixed-weight local curvature does not integrate or calibrate uncertainty over competing modes.'],
            'variants':output}


def main():
    result=build()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_bytes(study.encoded(result))
    print('wrote',OUT.relative_to(ROOT),'sha256',study.lab.digest(OUT))


if __name__=='__main__':main()
