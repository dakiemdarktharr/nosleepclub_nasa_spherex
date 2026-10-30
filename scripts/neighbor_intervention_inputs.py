"""Semantic native-pixel designs for opened WISE neighbor interventions.

Uses the frozen WISE selection/data/error arrays; it does not choose pixels or
neighbors from new fits. Source amplitudes have Jy units before any projection.
Spatial ePSF interpolation is a declared diagnostic approximation, not a new
calibration or independent PSF truth. Nothing is loaded at import.
"""
import astropy.units as u
import numpy as np

from . import native_gain_binding as active_geometry
from . import wise_linked_inputs as original
from .native_flux_template import native_flux_template
from .wcs_pixel_area import wcs_pixel_area


def _vector(value, name, size=None):
    if isinstance(value,u.Quantity):raise ValueError(name+' must be numeric in declared native units')
    a=np.asarray(value)
    if a.ndim!=1 or a.dtype.kind not in 'iuf' or not np.isfinite(a).all() or (size is not None and len(a)!=size):
        raise ValueError(name+' must be a finite numeric vector')
    return a.astype(float)


def select_epsf(table, parent_xy, kind):
    """Select nearest or mix four normalized raw tables in active SKY pixels.

    A complete Cartesian grid is required. Bilinear interpolation clamps only
    outside the center grid and records those axes. It never re-centers tables,
    suppresses signed wings, or normalizes using a selected stamp/mask.
    """
    position=_vector(parent_xy,'active parent position',2)
    if kind not in ('nearest','bilinear'):raise ValueError('unknown ePSF spatial model')
    if np.any(position<-.5) or np.any(position>2039.5):raise ValueError('source outside active detector')
    x=_vector(table['XCENTER'],'ePSF grid x');y=_vector(table['YCENTER'],'ePSF grid y')
    if not len(x) or len(y)!=len(x):raise ValueError('empty or inconsistent ePSF table')
    xs=np.unique(x);ys=np.unique(y)
    mapping={(float(xx),float(yy)):i for i,(xx,yy) in enumerate(zip(x,y))}
    if len(mapping)!=len(x) or len(xs)*len(ys)!=len(x):raise ValueError('incomplete or duplicate ePSF grid')
    def bracket(values, point):
        if len(values)<2:raise ValueError('bilinear ePSF requires two centers per axis')
        clamp=bool(point<values[0] or point>values[-1])
        value=float(np.clip(point,values[0],values[-1]))
        index=int(np.clip(np.searchsorted(values,value,side='right')-1,0,len(values)-2))
        left,right=map(float,values[index:index+2]);fraction=(value-left)/(right-left)
        return [(left,1-fraction),(right,fraction)],clamp
    if kind=='nearest':
        i=int(np.argmin((x-position[0])**2+(y-position[1])**2))
        entries=[(i,1.)];clamped=[False,False]
    else:
        bx,cx=bracket(xs,position[0]);by,cy=bracket(ys,position[1]);clamped=[cx,cy]
        entries=[(mapping[(xx,yy)],float(wx*wy)) for xx,wx in bx for yy,wy in by if wx*wy>0]
    result=None
    for index,weight in entries:
        raw=np.asarray(table['EPSF'][index],float)
        total=float(raw.sum())
        if raw.shape!=(33,33) or not np.isfinite(raw).all() or not np.isfinite(total) or total<=0:
            raise ValueError('invalid selected raw ePSF table')
        if result is None:result=np.zeros_like(raw)
        result+=weight*(raw/total)
    if result is None or not np.isfinite(result).all() or abs(sum(w for _,w in entries)-1)>1e-12:
        raise ValueError('invalid spatial ePSF weights')
    return result,{'kind':kind,'active_parent_xy':position.tolist(),
                   'table_indices':[i for i,_ in entries],'table_weights':[w for _,w in entries],
                   'table_centers_xy':[[float(x[i]),float(y[i])] for i,_ in entries],
                   'clamped_axes':clamped,'raw_signed_sum':float(result.sum()),
                   'qualification':'shape fixed at supplied anchor/catalog position; phase normalization occurs on full native lattice'}


def background_design(original_background, order):
    if isinstance(original_background,u.Quantity):raise ValueError('background columns must be numeric dimensionless values')
    b=np.asarray(original_background)
    if (b.ndim!=2 or b.shape[1]!=3 or b.dtype.kind not in 'iuf' or not np.isfinite(b).all()
            or not np.array_equal(b[:,0],np.ones(len(b)))):
        raise ValueError('explicit dimensionless constant/x/y background required')
    if isinstance(order,(bool,np.bool_)) or order not in (1,2):raise ValueError('background degree must be 1 or 2')
    if order==1:return b.astype(float).copy()
    x,y=b[:,1],b[:,2]
    return np.column_stack((b,x*x,x*y,y*y))


def prepare_semantic(prepared, anchor, *, background_order=1, epsf_kind='nearest'):
    """Create meaningful target/background/neighbor columns with provenance.

    ``prepared`` comes from wise_linked_inputs.prepared_samples after verified
    frame loading. Per-frame target and neighbor coefficients will be Jy;
    dimensionless background columns have coefficients in MJy/sr. No color,
    positive target flux, or fixed catalog-flux prior is imposed.
    """
    anchor=_vector(anchor,'anchor',2)
    if not prepared:raise ValueError('nonempty original prepared sample list required')
    output=[];seen=set()
    for item in prepared:
        if item.get('data_unit')!='MJy/sr':raise ValueError('validated native data units required')
        obs=item['obs_id']
        if not isinstance(obs,str) or not obs or obs in seen:raise ValueError('duplicate or invalid exposure ID')
        seen.add(obs)
        sample=item['sample'];frame=sample['frame'];selection=np.asarray(item['selection_mask'])
        if selection.dtype.kind!='b' or selection.shape!=frame['data'].shape:raise ValueError('explicit selection mask required')
        sy,sx=np.nonzero(selection)
        if not np.array_equal(sx,sample['x']) or not np.array_equal(sy,sample['y']):raise ValueError('original pixel selection/order differs')
        data=_vector(item['data'],'native data',len(sx));error=_vector(item['error'],'native error',len(sx))
        if np.any(error<=0):raise ValueError('positive native errors required')
        over=frame['epsf_oversampling']
        if isinstance(over,(bool,np.bool_)) or over!=5:raise ValueError('only verified 5x ePSF supported')
        active=active_geometry.validate_image(frame['image_header'],frame['primary_header'],frame['record']['collection'])
        provenance=item['renderer_provenance'];table=frame['epsf_table'];epsf_provenance=frame['epsf_provenance']
        anchor_native=original.native_position(frame,anchor)
        target_raw,target_description=select_epsf(table,active.pixel_to_world_values(*anchor_native),epsf_kind)
        def render(position, *, frame=frame, raw=target_raw, mask=selection.copy(), provenance=provenance,
                   epsf_provenance=epsf_provenance):
            native=original.native_position(frame,position)
            area=wcs_pixel_area(frame['wcs'],native,provenance=provenance)
            if not area.supported:raise ValueError('target WCS area fails refinement diagnostic')
            return native_flux_template(raw,oversampling_x=5,oversampling_y=5,
                source_xy=native,selection_mask=mask,source_omega=area.solid_angle,
                source_omega_provenance=provenance+'|geometric WCS area, not exact SAPM',
                epsf_provenance=epsf_provenance).template_per_jy
        ids=list(sample['neighbour_ids'])
        if len(ids)!=len(set(ids)) or any(not isinstance(sid,str) or not sid for sid in ids):
            raise ValueError('unique semantic neighbor IDs required')
        neighbors={sid:np.asarray(position,float) for sid,position in sample['neighbours']}
        if len(neighbors)!=len(sample['neighbours']) or not set(ids)<=set(neighbors):
            raise ValueError('retained neighbor identity/position mismatch')
        columns=[];descriptions=[]
        for sid in ids:
            sky=_vector(neighbors[sid],'neighbor position',2);native=original.native_position(frame,sky)
            raw,description=select_epsf(table,active.pixel_to_world_values(*native),epsf_kind)
            area=wcs_pixel_area(frame['wcs'],native,provenance=provenance+'|'+sid)
            if not area.supported:raise ValueError('neighbor WCS area fails refinement diagnostic')
            rendered=native_flux_template(raw,oversampling_x=5,oversampling_y=5,
                source_xy=native,selection_mask=selection,source_omega=area.solid_angle,
                source_omega_provenance=provenance+'|'+sid+'|geometric WCS area, not exact SAPM',
                epsf_provenance=epsf_provenance)
            column=rendered.template_per_jy.to_value(u.MJy/u.sr/u.Jy)
            if not np.any(column!=0):raise ValueError('retained neighbor has zero semantic template: '+sid)
            columns.append(column)
            descriptions.append({'id':sid,'sky_grid_xy':sky.tolist(),'native_xy':native.tolist(),
                'spatial_epsf':description,'omega_sr':float(area.solid_angle.to_value(u.sr)),
                'omega_refinement_relative_difference':area.relative_difference,
                'signed_selected_psf_fraction':rendered.signed_selected_sum,
                'support_truncated_by_image':rendered.support_truncated_by_image})
        output.append({'obs_id':obs,'data':data.copy(),'error':error.copy(),
            'background_design':background_design(sample['background'],background_order),
            'neighbor_design':np.column_stack(columns) if columns else np.empty((len(data),0)),
            'neighbor_unit':str(u.MJy/u.sr/u.Jy),'neighbor_ids':ids,'renderer':render,
            'metadata':{'background_degree':int(background_order),'spatial_epsf':epsf_kind,
                'target_shape_anchor_sky_px':anchor.tolist(),'target_shape_native_xy':anchor_native.tolist(),
                'target_spatial_epsf':target_description,'neighbors':descriptions,
                'data_unit':'MJy/sr','source_coefficient_unit':'Jy','background_coefficient_unit':'MJy/sr',
                'x':sx.tolist(),'y':sy.tolist(),'cutout_url':frame['record']['cutout_url'],
                'raw_sha256':frame['record']['sha256'],'epsf_provenance':epsf_provenance,
                'subtraction_provenance':item['subtraction_provenance'],
                'qualification':'same frozen pixels/catalog selection; new semantic native neighbor templates; no flux prior, covariance calibration or astrometric truth'}})
    return output


def model_samples(prepared_semantic):
    keys=('obs_id','data','error','background_design','neighbor_design','neighbor_unit','neighbor_ids','renderer')
    return [{key:item[key] for key in keys} for item in prepared_semantic]
