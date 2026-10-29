"""Matched-band coadds and independent native-pixel ePSF astrometry.

Positions are fitted separately for each epoch. The published proper motion is
used only to locate the search region and to predict a comparison vector later.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from astropy import log
from astropy.coordinates import get_body_barycentric
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.time import Time
import astropy.units as u
import numpy as np
from scipy.ndimage import map_coordinates, spline_filter
from scipy.optimize import least_squares, linear_sum_assignment
from scipy.sparse import coo_matrix, diags
from PIL import Image

try:
    from . import build_demo as base
except ImportError:
    import build_demo as base

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/raw/wise0855/coadd/manifest.json"
OUTPUT = ROOT / "web/data/motion"
WCS = base.grid_wcs()
TARGET_ANCHOR = np.array([31.5,31.5])
# Frozen before fitting the target. Strict is the primary configuration;
# the wider gate is a declared sensitivity check, not a replacement chosen by S/N.
CONFIGS = [("strict",.20),("broad",.50)]
WAVE_RANGE = (4.55,4.94)


def load_frames():
    manifest=json.loads(INPUT.read_text(encoding="utf-8"))
    with fits.open(ROOT/manifest["calibrations"]["spectral_wcs"]["path"]) as h:
        cwave=np.array(h["CWAVE"].data,float)
        cband=np.array(h["CBAND"].data,float)
    with fits.open(ROOT/manifest["calibrations"]["epsf"]["path"]) as h:
        epsf_table=np.array(h["EPSF"].data)
        over=float(h["EPSF"].header["OVSMPX"])
    frames=[]
    for record in manifest["records"]:
        if record["status"]!="downloaded":continue
        f=base.read_frame(record)
        with fits.open(ROOT/record["path"]) as h:
            parent=base.alternate_wcs(h["IMAGE"].header,h,"A")
        yy,xx=np.indices(f["data"].shape,dtype=float)
        gx,gy=parent.pixel_to_world_values(xx,yy)
        f["cwave_map"]=map_coordinates(cwave,[gy,gx],order=1,mode="constant",cval=np.nan)
        f["cband_map"]=map_coordinates(cband,[gy,gx],order=1,mode="constant",cval=np.nan)
        tx,ty=f["wcs"].world_to_pixel_values(*f["position"])
        cw=float(map_coordinates(f["cwave_map"],[[ty],[tx]],order=1)[0])
        cb=float(map_coordinates(f["cband_map"],[[ty],[tx]],order=1)[0])
        f.update({"visualization_wavelength_um":f["wavelength"],"wavelength":cw,"bandwidth":cb,
                  "parent_wcs":parent,"epsf_table":epsf_table,"epsf_oversampling":over,
                  "offset":np.zeros(2),"offset_cov":np.zeros((2,2))})
        frames.append(f)
    return frames,manifest


def select_pairs(frames,tolerance):
    before=[f for f in frames if f["record"]["epoch"]=="2025-11" and WAVE_RANGE[0]<=f["wavelength"]<=WAVE_RANGE[1]]
    after=[f for f in frames if f["record"]["epoch"]=="2026-04" and WAVE_RANGE[0]<=f["wavelength"]<=WAVE_RANGE[1]]
    mismatch=np.array([[abs(a["wavelength"]-b["wavelength"])/((a["bandwidth"]+b["bandwidth"])/2)
                       for b in after] for a in before])
    ii,jj=linear_sum_assignment(np.where(mismatch<=tolerance,mismatch,1e6))
    pairs=[(before[i],after[j],float(mismatch[i,j])) for i,j in zip(ii,jj) if mismatch[i,j]<=tolerance]
    if len(pairs)<2:raise RuntimeError("Fewer than two compatible independent spectral pairs")
    return sorted(pairs,key=lambda pair:pair[0]["wavelength"])


def projection_operator(frame):
    yy,xx=np.indices(base.SHAPE,dtype=float)
    ra,dec=WCS.pixel_to_world_values(xx+frame["offset"][0],yy+frame["offset"][1])
    x,y=frame["wcs"].world_to_pixel_values(ra,dec)
    x=x.ravel();y=y.ravel();finite=np.isfinite(x)&np.isfinite(y)
    x0=np.floor(np.where(finite,x,0)).astype(int);y0=np.floor(np.where(finite,y,0)).astype(int)
    dx,dy=x-x0,y-y0
    rows=[];cols=[];values=[]
    height,width=frame["data"].shape
    for ox,oy,w in ((0,0,(1-dx)*(1-dy)),(1,0,dx*(1-dy)),(0,1,(1-dx)*dy),(1,1,dx*dy)):
        sx,sy=x0+ox,y0+oy
        keep=finite&(sx>=0)&(sy>=0)&(sx<width)&(sy<height)
        safe_x=np.clip(sx,0,width-1);safe_y=np.clip(sy,0,height-1)
        keep&=frame["valid"][safe_y,safe_x]
        rows.extend(np.flatnonzero(keep));cols.extend((safe_y[keep]*width+safe_x[keep]).tolist());values.extend(w[keep])
    p=coo_matrix((values,(rows,cols)),shape=(4096,height*width)).tocsr()
    support=np.asarray(p.sum(axis=1)).ravel()
    p=diags(np.where(support>=.75,1/np.maximum(support,1e-12),0))@p
    return p.tocsr()


def coadd(frames,weights):
    operators=[projection_operator(f) for f in frames]
    valid=np.array([np.asarray(p.sum(axis=1)).ravel()>.99 for p in operators])
    weighted=weights[:,None]*valid
    support=weighted.sum(axis=0)
    coefficients=weighted/np.maximum(support,1e-15)
    image=np.zeros(4096);variance=np.zeros(4096);wave=np.zeros(4096);band=np.zeros(4096)
    for f,p,g in zip(frames,operators,coefficients):
        image+=g*(p@np.nan_to_num(f["data"]).ravel())
        variance+=g**2*(p.power(2)@np.nan_to_num(f["variance"]).ravel())
        wave+=g*(p@np.nan_to_num(f["cwave_map"]).ravel())
        band+=g*(p@np.nan_to_num(f["cband_map"]).ravel())
    good=support>.90*weights.sum()
    image[~good]=np.nan;variance[~good]=np.nan
    return {"image":image.reshape(base.SHAPE),"variance":variance.reshape(base.SHAPE),
        "valid":good.reshape(base.SHAPE),"wavelength":wave.reshape(base.SHAPE),"bandwidth":band.reshape(base.SHAPE),
        "operators":operators,"coefficients":coefficients,"frames":frames,"support":support.reshape(base.SHAPE)}


def aperture_snr(stack,position,comparison_mask=None):
    yy,xx=np.indices(base.SHAPE);r2=(xx-position[0])**2+(yy-position[1])**2
    disk=(r2<=2.5**2);ring=(r2>=4**2)&(r2<=6**2)
    good=stack["valid"].copy()
    if comparison_mask is not None:good&=comparison_mask
    # Missing pixels need not invalidate an aperture when the actual linear
    # statistic and its native-pixel noise are retained. Coverage is reported.
    if (disk&good).sum()<.75*disk.sum():return {"snr":None,"coverage":float((disk&good).sum()/disk.sum())}
    disk&=good;ring&=good
    if ring.sum()<20:return {"snr":None,"coverage":0.}
    # Cancel a fitted constant AND linear background, including asymmetric masks.
    design=np.column_stack([np.ones(ring.sum()),(xx-position[0])[ring],(yy-position[1])[ring]])
    disk_moments=np.array([disk.sum(),(xx-position[0])[disk].sum(),(yy-position[1])[disk].sum()])
    w=disk.astype(float)
    w[ring]=-(disk_moments@np.linalg.pinv(design.T@design)@design.T)
    signal=float(np.nansum(w*stack["image"]))
    variance=0.
    # Push aperture weights back to native pixels. This retains the covariance
    # introduced by interpolation without storing a 4096x4096 covariance matrix.
    for f,p,g in zip(stack["frames"],stack["operators"],stack["coefficients"]):
        native=p.T@(g*w.ravel())
        variance+=float(np.sum(native**2*np.nan_to_num(f["variance"]).ravel()))
    return {"snr":signal/np.sqrt(variance),"signal":signal,"noise":np.sqrt(variance),
            "coverage":float(disk.sum()/((r2<=2.5**2).sum())),
            "noise_method":"native-pixel adjoint propagation; independent input pixels/exposures assumed"}


def epsf_for(frame,native_x,native_y):
    gx,gy=frame["parent_wcs"].pixel_to_world_values(native_x,native_y)
    table=frame["epsf_table"]
    index=int(np.argmin((table["XCENTER"]-gx)**2+(table["YCENTER"]-gy)**2))
    data=np.asarray(table["EPSF"][index],float)
    data=data*frame["epsf_oversampling"]**2/data.sum()
    return spline_filter(data,order=3),index


def native_stamp(frame,anchor,radius=6):
    # The source coordinates are common sky-grid coordinates; reference-only
    # offsets translate them to the imperfect WCS of each original exposure.
    center=anchor+frame["offset"]
    world=WCS.pixel_to_world_values(*center)
    px,py=frame["wcs"].world_to_pixel_values(*world)
    ex=np.array(frame["wcs"].world_to_pixel_values(*WCS.pixel_to_world_values(center[0]+.01,center[1])))
    ey=np.array(frame["wcs"].world_to_pixel_values(*WCS.pixel_to_world_values(center[0],center[1]+.01)))
    jac=np.column_stack([(ex-[px,py])/.01,(ey-[px,py])/.01])
    yy,xx=np.indices(frame["data"].shape,dtype=float)
    keep=(np.abs(xx-px)<=radius)&(np.abs(yy-py)<=radius)&frame["valid"]
    if keep.sum()<35:raise ValueError("Too few valid native pixels")
    epsf,zone=epsf_for(frame,float(px),float(py))
    return {"frame":frame,"anchor":np.array(anchor),"native_center":np.array([px,py]),"jacobian":jac,
            "x":xx[keep],"y":yy[keep],"data":frame["data"][keep],"error":np.sqrt(frame["variance"][keep]),
            "epsf":epsf,"zone":zone,"background":np.column_stack([np.ones(keep.sum()),(xx[keep]-px)/6,(yy[keep]-py)/6])}


def stamp_model(sample,position):
    p=sample["native_center"]+sample["jacobian"]@(position-sample["anchor"])
    over=sample["frame"]["epsf_oversampling"]
    c=(np.array(sample["epsf"].shape)-1)/2
    psf=map_coordinates(sample["epsf"],[(sample["y"]-p[1])*over+c[0],(sample["x"]-p[0])*over+c[1]],
                        order=3,mode="constant",cval=0,prefilter=False)
    return np.column_stack([psf,sample["background"]])


def linear_fit(sample,position):
    design=stamp_model(sample,position)
    weighted=design/sample["error"][:,None]
    beta=np.linalg.lstsq(weighted,sample["data"]/sample["error"],rcond=None)[0]
    error=float(np.sqrt(np.linalg.pinv(weighted.T@weighted)[0,0]))
    residual=(design@beta-sample["data"])/sample["error"]
    return residual,beta,error


def fit_position(frames,anchor,bound=2.5,multistart=False,samples=None):
    if samples is None:
        samples=[native_stamp(f,np.asarray(anchor)) for f in frames]
    def residual(position):
        return np.concatenate([linear_fit(s,position)[0] for s in samples])
    starts=[np.asarray(anchor)]
    if multistart:
        starts.extend(np.asarray(anchor)+delta for delta in [(-.7,0),(.7,0),(0,-.7),(0,.7)])
    results=[least_squares(residual,start,bounds=(np.asarray(anchor)-bound,np.asarray(anchor)+bound),
                diff_step=1e-4,ftol=1e-8,xtol=1e-8,gtol=1e-7,max_nfev=90) for start in starts]
    fit=min(results,key=lambda result:np.sum(result.fun**2))
    dof=len(fit.fun)-4*len(samples)-2
    chi2=float(np.sum(fit.fun**2)/dof)
    covariance=np.linalg.pinv(fit.jac.T@fit.jac)*max(chi2,1.)
    details=[]
    for sample in samples:
        resid,beta,error=linear_fit(sample,fit.x)
        error*=max(1.,np.sqrt(np.mean(resid**2)))
        details.append({"obs_id":sample["frame"]["record"]["obs_id"],"mjd":sample["frame"]["mjd"],
                        "amplitude":float(beta[0]),"amplitude_error":error,"snr":float(beta[0]/error),"epsf_zone":sample["zone"]})
    weights=np.array([max(d["snr"],0)**2 for d in details])
    mean_time=float(np.average([d["mjd"] for d in details],weights=weights)) if weights.sum()>0 else float(np.mean([d["mjd"] for d in details]))
    return {"position":fit.x,"covariance":covariance,"reduced_chi2":chi2,"per_frame":details,
            "at_boundary":bool(np.any(np.abs(fit.x-anchor)>.95*bound)),"success":bool(fit.success),
            "effective_mjd":mean_time,"samples":samples,"nfev":fit.nfev}


def render_source(frame,position,amplitude=1.):
    ra,dec=WCS.pixel_to_world_values(*(np.asarray(position)+frame["offset"]))
    px,py=frame["wcs"].world_to_pixel_values(ra,dec)
    psf,_=epsf_for(frame,float(px),float(py))
    yy,xx=np.indices(frame["data"].shape,dtype=float)
    center=(np.array(psf.shape)-1)/2;over=frame["epsf_oversampling"]
    return amplitude*map_coordinates(psf,[(yy-py)*over+center[0],(xx-px)*over+center[1]],
                         order=3,mode="constant",cval=0,prefilter=False)


def real_background_controls(before,after):
    # A declared off-target location; these synthetic sources never enter demo
    # science images or reference fitting. Input noise maps stay unchanged.
    anchor=np.array([21.,35.]);output=[]
    for label,delta in [("stationary",np.array([0.,0.])),("moving",np.array([.6,.05]))]:
        a=[{**f,"data":f["data"]+render_source(f,anchor,.8)} for f in before]
        b=[{**f,"data":f["data"]+render_source(f,anchor+delta,.8)} for f in after]
        fa=fit_position(a,anchor,bound=1.5);fb=fit_position(b,anchor,bound=1.5)
        measured=fb["position"]-fa["position"]
        covariance=fa["covariance"]+fb["covariance"]
        error=measured-delta
        output.append({"kind":label,"injected_delta_px":delta.tolist(),"recovered_delta_px":measured.tolist(),
                       "error_mahalanobis":float(np.sqrt(error@np.linalg.pinv(covariance)@error)),
                       "covariance_px2":covariance.tolist(),"amplitude_per_frame":.8,
                       "note":"Synthetic control on real off-target background; fixed calibration; no added source shot noise; not a completeness benchmark."})
    return output


def reference_anchors(a,b):
    candidates=base.star_centers(a["image"])
    other=base.star_centers(b["image"])
    selected=[]
    for point in candidates:
        x,y=point
        if min(x,y,63-x,63-y)<7 or np.linalg.norm(point-TARGET_ANCHOR)<7:continue
        if not len(other) or np.min(np.linalg.norm(other-point,axis=1))>1.5:continue
        selected.append(point)
    selected.sort(key=lambda p:-a["image"][int(round(p[1])),int(round(p[0]))])
    if len(selected)<5:raise RuntimeError(f"Only {len(selected)} independent reference candidates; need >=5")
    return selected[:8]


def calibrate(frames,anchors,swap=False):
    training=anchors[1::2] if swap else anchors[::2]
    heldout=anchors[::2] if swap else anchors[1::2]
    if len(training)<3 or len(heldout)<2:raise RuntimeError("Insufficient disjoint reference sets")
    for frame in frames:
        frame["offset"]=np.zeros(2)
    for frame in frames:
        offsets=[];covariances=[]
        for anchor in training:
            fit=fit_position([frame],anchor,bound=1.5)
            if fit["per_frame"][0]["snr"]<7 or fit["at_boundary"]:continue
            offsets.append(fit["position"]-anchor);covariances.append(fit["covariance"])
        if len(offsets)<2:raise RuntimeError(f"Too few registration sources: {frame['record']['obs_id']}")
        precision=np.array([np.linalg.pinv(c+np.eye(2)*.01**2) for c in covariances])
        covariance=np.linalg.pinv(precision.sum(axis=0))
        offset=covariance@np.sum([p@d for p,d in zip(precision,offsets)],axis=0)
        frame["offset"]=offset;frame["offset_cov"]=covariance
    return training,heldout


def public_fit(fit):
    position=fit["position"]
    ra,dec=WCS.pixel_to_world_values(*position)
    return {"x":float(position[0]),"y":float(position[1]),"ra_deg":float(ra),"dec_deg":float(dec),
            "covariance_px2":fit["covariance"].tolist(),"sigma_x_arcsec":float(np.sqrt(fit["covariance"][0,0])*base.SCALE),
            "sigma_y_arcsec":float(np.sqrt(fit["covariance"][1,1])*base.SCALE),
            "effective_mjd":fit["effective_mjd"],"reduced_chi2":fit["reduced_chi2"],
            "success":fit["success"],"at_boundary":fit["at_boundary"],"per_frame":fit["per_frame"]}


def bootstrap_position(fit,count,seed):
    rng=np.random.default_rng(seed)
    positions=[];boundaries=0
    noise_scale=np.sqrt(max(fit["reduced_chi2"],1.))
    for _ in range(count):
        samples=[]
        for original in fit["samples"]:
            _,beta,_=linear_fit(original,fit["position"])
            sample={**original,"data":stamp_model(original,fit["position"])@beta+
                    rng.normal(size=len(original["data"]))*original["error"]*noise_scale}
            samples.append(sample)
        result=fit_position([],fit["position"],samples=samples)
        positions.append(result["position"]);boundaries+=int(result["at_boundary"])
    covariance=np.cov(np.array(positions).T,ddof=1)
    formal=fit["covariance"].copy()
    eigenvalues,eigenvectors=np.linalg.eigh(covariance-formal)
    fit["covariance"]=formal+eigenvectors@np.diag(np.maximum(eigenvalues,0))@eigenvectors.T
    return {"draws":count,"seed":seed,"covariance_px2":covariance.tolist(),"formal_covariance_px2":formal.tolist(),
            "mean_bias_px":(np.mean(positions,axis=0)-fit["position"]).tolist(),"boundary_fraction":boundaries/count,
            "note":"Conditional parametric native-pixel noise check; does not simulate calibration or ePSF systematics."}


def expected_motion(t1,t2):
    ra,dec=np.deg2rad(base.CENTER)
    east=np.array([-np.sin(ra),np.cos(ra),0])
    north=np.array([-np.cos(ra)*np.sin(dec),-np.sin(ra)*np.sin(dec),np.cos(dec)])
    delta=(get_body_barycentric("earth",Time(t2,format="mjd"))-get_body_barycentric("earth",Time(t1,format="mjd"))).xyz.to_value(u.au)
    parallax=-.454*np.array([delta@east,delta@north])
    proper=np.array([-8.06,.70])*(t2-t1)/365.25
    return {"east_arcsec":float((proper+parallax)[0]),"north_arcsec":float((proper+parallax)[1]),
            "proper_motion_component_arcsec":proper.tolist(),"parallax_component_arcsec":parallax.tolist(),
            "note":"External Luhman 2014 prediction plus builtin Earth ephemeris; not fitted to these two epochs."}


def run_config(frames,manifest,name,tolerance,bootstrap_draws=128):
    for frame in frames:frame["offset"]=np.zeros(2);frame["offset_cov"]=np.zeros((2,2))
    pairs=select_pairs(frames,tolerance)
    aa=[p[0] for p in pairs];bb=[p[1] for p in pairs]
    weights=np.array([1/(np.median(a["variance"][a["valid"]])+np.median(b["variance"][b["valid"]])) for a,b,_ in pairs])
    weights/=weights.sum()
    preliminary_a,preliminary_b=coadd(aa,weights),coadd(bb,weights)
    anchors=reference_anchors(preliminary_a,preliminary_b)
    print(f"{name}: {len(pairs)} spectral pairs, {len(anchors)} reference sources",flush=True)
    train,heldout=calibrate(aa+bb,anchors)
    a,b=coadd(aa,weights),coadd(bb,weights)
    target_a=fit_position(aa,TARGET_ANCHOR,multistart=True)
    target_b=fit_position(bb,TARGET_ANCHOR,multistart=True)
    print(f"{name}: checking centroid uncertainty with {bootstrap_draws} draws / epoch",flush=True)
    bootstrap_a=bootstrap_position(target_a,bootstrap_draws,20261030+(0 if name=="strict" else 2))
    bootstrap_b=bootstrap_position(target_b,bootstrap_draws,20261031+(0 if name=="strict" else 2))
    controls=[]
    for i,anchor in enumerate(heldout):
        fa=fit_position(aa,anchor,bound=1.5);fb=fit_position(bb,anchor,bound=1.5)
        controls.append({"id":f"H{i+1}","anchor":anchor.tolist(),"before":public_fit(fa),"after":public_fit(fb),
                         "delta_px":(fb["position"]-fa["position"]).tolist()})
    heldout_delta=np.array([c["delta_px"] for c in controls])
    # Conservative empirical term retains the mean bias as well as scatter.
    holdout_cov=heldout_delta.T@heldout_delta/len(heldout_delta)
    cal_a=np.mean([f["offset_cov"] for f in aa],axis=0)
    cal_b=np.mean([f["offset_cov"] for f in bb],axis=0)
    covariance=target_a["covariance"]+target_b["covariance"]+cal_a+cal_b+holdout_cov
    displacement=target_b["position"]-target_a["position"]
    transform=np.diag([-base.SCALE,base.SCALE])
    delta_arcsec=transform@displacement
    covariance_arcsec=transform@covariance@transform
    distance=float(np.linalg.norm(delta_arcsec))
    radial_error=float(np.sqrt(delta_arcsec@covariance_arcsec@delta_arcsec)/distance) if distance else None
    strength=float(np.sqrt(displacement@np.linalg.pinv(covariance)@displacement))
    snr_a=aperture_snr(a,target_a["position"]);snr_b=aperture_snr(b,target_b["position"])
    single_a=[aperture_snr(coadd([f],np.array([1.])),target_a["position"],a["valid"]) for f in aa]
    single_b=[aperture_snr(coadd([f],np.array([1.])),target_b["position"],b["valid"]) for f in bb]
    best_a=max([r["snr"] for r in single_a if r["snr"] is not None]);best_b=max([r["snr"] for r in single_b if r["snr"] is not None])
    original_offsets=[(f,f["offset"].copy(),f["offset_cov"].copy()) for f in aa+bb]
    alternate_delta=None;alternate_error=None
    try:
        calibrate(aa+bb,anchors,swap=True)
        alternate_a=fit_position(aa,TARGET_ANCHOR);alternate_b=fit_position(bb,TARGET_ANCHOR)
        alternate_delta=transform@(alternate_b["position"]-alternate_a["position"])
    except RuntimeError as exc:
        alternate_error=str(exc)
    finally:
        for f,offset,cov in original_offsets:f["offset"]=offset;f["offset_cov"]=cov
    report={"id":name,"tolerance_bandwidth":tolerance,"wavelength_selection_um":list(WAVE_RANGE),
        "frame_count_per_epoch":len(pairs),"common_spectral_weights":weights.tolist(),
        "spectral_pairs":[{"before":p[0]["record"],"after":p[1]["record"],"before_um":p[0]["wavelength"],
                           "after_um":p[1]["wavelength"],"mismatch_bandwidth":p[2],"weight":float(w)} for p,w in zip(pairs,weights)],
        "target_before":public_fit(target_a),"target_after":public_fit(target_b),
        "bootstrap_before":bootstrap_a,"bootstrap_after":bootstrap_b,
        "reference_swap_east_north_arcsec":alternate_delta.tolist() if alternate_delta is not None else None,
        "reference_swap_change_arcsec":float(np.linalg.norm(alternate_delta-delta_arcsec)) if alternate_delta is not None else None,
        "reference_swap_unavailable_reason":alternate_error,
        "training_reference_positions":[p.tolist() for p in train],"heldout_controls":controls,
        "holdout_rms_arcsec":float(np.sqrt(np.mean(np.sum(heldout_delta**2,axis=1)))*base.SCALE),
        "registration_covariance_px2":(cal_a+cal_b).tolist(),"holdout_covariance_px2":holdout_cov.tolist(),
        "east_arcsec":float(delta_arcsec[0]),"north_arcsec":float(delta_arcsec[1]),
        "displacement_arcsec":distance,"radial_error_arcsec":radial_error,"covariance_arcsec2":covariance_arcsec.tolist(),
        "mahalanobis_distance":strength,"predicted_motion":expected_motion(target_a["effective_mjd"],target_b["effective_mjd"]),
        "coadd_snr_before":snr_a,"coadd_snr_after":snr_b,"best_single_snr_before":best_a,"best_single_snr_after":best_b,
        "single_frame_aperture_snr_before":[{"obs_id":f["record"]["obs_id"],**v} for f,v in zip(aa,single_a)],
        "single_frame_aperture_snr_after":[{"obs_id":f["record"]["obs_id"],**v} for f,v in zip(bb,single_b)],
        "frame_registration":[{"obs_id":f["record"]["obs_id"],"offset_px":f["offset"].tolist(),
                               "covariance_px2":f["offset_cov"].tolist()} for f in aa+bb],
        "real_background_injection_controls":real_background_controls(aa,bb),
        "configuration_role":"primary_strict" if name=="strict" else "spectral_tolerance_sensitivity_check",
        "snr_note":"Aperture statistic conditional on fitted position; best individual comparison uses the coadd mask. Not a blind detection significance or total flux measurement.",
        "native_pixel_fit":True,"position_tied_to_expected_motion":False,"parallax_fitted":False,
        "status":"candidate_motion" if strength>=3 else "inconclusive",
        "uncertainty_note":"Conditional native-pixel fit covariance inflated by chi-square, plus conservative reference-calibration and heldout RMS terms. Not a calibrated discovery probability."}
    print(json.dumps({k:report[k] for k in ["id","frame_count_per_epoch","east_arcsec","north_arcsec","displacement_arcsec","radial_error_arcsec","mahalanobis_distance","holdout_rms_arcsec","best_single_snr_before","best_single_snr_after"]},indent=2),flush=True)
    print("COADD SNR",snr_a["snr"],snr_b["snr"],flush=True)
    return report,a,b


def effective_display_psf(stack,weights):
    model=np.zeros(4096)
    for frame,p,g in zip(stack["frames"],stack["operators"],stack["coefficients"]):
        model+=g*(p@render_source(frame,np.array([32.,32.])).ravel())
    kernel=np.maximum(model.reshape(base.SHAPE)[27:38,27:38],0)
    return kernel/kernel.sum()


def export_scene(report,a,b,calibrations):
    sid="coadd-"+report["id"];folder=ROOT/"web/data"/sid;folder.mkdir(parents=True,exist_ok=True)
    weights=np.array(report["common_spectral_weights"])
    pa,pb=effective_display_psf(a,weights),effective_display_psf(b,weights)
    image_a,var_a,support_a=base.smooth_with_psf(a["image"],a["variance"],pb)
    image_b,var_b,support_b=base.smooth_with_psf(b["image"],b["variance"],pa)
    valid=np.isfinite(image_a)&np.isfinite(image_b)&(support_a>.90)&(support_b>.90)
    x,y=np.indices(base.SHAPE)[1],np.indices(base.SHAPE)[0]
    fitmask=valid&((x-31.5)**2+(y-31.5)**2>7**2)
    gain,offset,ratios=base.calibration_from_stars(image_a,image_b,fitmask,[TARGET_ANCHOR])
    delta=image_b-gain*image_a-offset
    ratio=delta/np.sqrt(var_b+gain**2*var_a)
    _,median,scale=sigma_clipped_stats(ratio,mask=~fitmask)
    score=(ratio-median)/max(scale,1.)
    denominator=(a["bandwidth"]+b["bandwidth"])/2
    mismatch=np.divide(np.abs(a["wavelength"]-b["wavelength"]),denominator,
                       out=np.full(base.SHAPE,np.inf),where=denominator>0)
    valid&=mismatch<=report["tolerance_bandwidth"]
    values=np.concatenate([image_a[np.isfinite(image_a)],image_b[np.isfinite(image_b)]])
    # One shared faint-source stretch; bright field stars may saturate on screen.
    _,med,std=sigma_clipped_stats(values);low=med-2*std;high=med+12*std
    base.png_image(image_a,folder/"before.png",low,high);base.png_image(image_b,folder/"after.png",low,high)
    base.png_image(np.where(valid,score,np.nan),folder/"difference.png",-6,6,True)
    Image.fromarray(np.flipud((valid*255).astype(np.uint8))).save(folder/"valid.png")
    np.savez_compressed(folder/"arrays.npz",before=image_a,after=image_b,variance_before=var_a,variance_after=var_b,
                        coadd_before=a["image"],coadd_after=b["image"],difference=delta,score=score,valid=valid)
    hdus=[fits.PrimaryHDU(header=WCS.to_header())]
    hdus[0].header["OBJECT"]="WISE 0855 coadd motion candidate"
    hdus[0].header["NFRAMA"]=len(a["frames"]);hdus[0].header["NFRAMB"]=len(b["frames"])
    hdus[0].header["ANAVERS"]="0.2.0";hdus[0].header["HISTORY"]="Native-pixel ePSF astrometry; coadd display not used for centroid fit."
    for name,data in [("BEFORE",image_a),("AFTER",image_b),("VAR_BEFORE",var_a),("VAR_AFTER",var_b),
                      ("COADD_A",a["image"]),("COADD_B",b["image"]),("DIFFERENCE",delta),("EMP_SCORE",score),("VALID",valid.astype(np.uint8))]:
        h=fits.ImageHDU(data,header=WCS.to_header(),name=name)
        if name not in ["EMP_SCORE","VALID"]:h.header["BUNIT"]="(MJy/sr)^2" if name.startswith("VAR_") else "MJy/sr"
        hdus.append(h)
    fits.HDUList(hdus).writeto(folder/"comparison.fits",overwrite=True)
    (folder/"pixels.json").write_text(json.dumps({"before":base.json_array(image_a),"after":base.json_array(image_b),
        "score":base.json_array(np.where(valid,score,np.nan)),"valid":valid.astype(int).tolist()}),encoding="utf-8")
    def epoch_info(stack,key):
        fit=report["target_"+key];frames=stack["frames"]
        wav=float(sum(w*f["wavelength"] for f,w in zip(frames,weights)))
        return {"obs_id":f"{len(frames)} matched spectral exposures","inputs":[f["record"] for f in frames],
            "date":Time(fit["effective_mjd"],format="mjd").isot[:10],"mjd":fit["effective_mjd"],
            "date_start":Time(min(f["mjd"] for f in frames),format="mjd").isot[:10],
            "date_end":Time(max(f["mjd"] for f in frames),format="mjd").isot[:10],
            "wavelength_um":wav,"bandwidth_um":float(sum(w*f["bandwidth"] for f,w in zip(frames,weights))),
            "pipeline_version":", ".join(sorted(set(f["pipeline_version"] for f in frames))),
            "image":f"data/{sid}/{key}.png","sha256":sha256("".join(f["record"]["sha256"] for f in frames).encode()).hexdigest(),
            "sha256_kind":"SHA-256 of ordered concatenated input SHA-256 strings; not a raw FITS hash",
            "target_fit":{"aperture_snr_at_fitted_position":report["coadd_snr_"+key]["snr"]}}
    before=epoch_info(a,"before");after=epoch_info(b,"after")
    measured=[];prior=[]
    holdout_cov=np.array(report["holdout_covariance_px2"])/2
    for key,stack in [("before",a),("after",b)]:
        f=report["target_"+key]
        cal_cov=np.mean([frame["offset_cov"] for frame in stack["frames"]],axis=0)
        measured.append({"epoch":key,"x":f["x"],"y":f["y"],"covariance_px2":
                         (np.array(f["covariance_px2"])+cal_cov+holdout_cov).tolist()})
        p=base.expected_position(f["effective_mjd"]);px,py=WCS.world_to_pixel_values(*p)
        prior.append({"epoch":key,"x":float(px),"y":float(py),"ra_deg":p[0],"dec_deg":p[1]})
    candidate=base.residual_candidates(np.nan_to_num(score),valid,WCS)
    scene={"id":sid,"kind":"coadd","label":f"Cộng {report['frame_count_per_epoch']} ảnh / epoch",
        "shape":list(base.SHAPE),"pixel_scale_arcsec":base.SCALE,"before":before,"after":after,
        "baseline_days":after["mjd"]-before["mjd"],"target_wavelength_delta_nm":abs(before["wavelength_um"]-after["wavelength_um"])*1000,
        "wavelength_mismatch_channels":max(p["mismatch_bandwidth"] for p in report["spectral_pairs"]),
        "alignment":{"matched_stars":len(report["heldout_controls"]),"applied":True,
                     "rms_before_px":None,"rms_after_px":report["holdout_rms_arcsec"]/base.SCALE},
        "candidates":candidate,"target_prior":prior,"measured_positions":measured,"motion":report,
        "target_detection":report["status"],"photometric_gain":float(gain),"background_offset":float(offset),
        "valid_fraction":float(valid.mean()),"difference_image":f"data/{sid}/difference.png",
        "display_stretch":{"kind":"shared asinh, factor 8","low_mjy_sr":float(low),"high_mjy_sr":float(high),
                           "note":"Same limits for both epochs; bright field stars can clip. Display only."},
        "fits":f"data/{sid}/comparison.fits","arrays":f"data/{sid}/arrays.npz","array_json":f"data/{sid}/pixels.json",
        "wcs":{"center_ra_deg":base.CENTER[0],"center_dec_deg":base.CENTER[1],"orientation":"north up, east left"}}
    (folder/"evidence.json").write_text(json.dumps({"motion":report,"calibrations":calibrations},indent=2)+"\n",encoding="utf-8",newline="\n")
    return scene


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--only",choices=["strict","broad"])
    parser.add_argument("--bootstrap",type=int,default=128)
    args=parser.parse_args();log.setLevel("WARNING")
    if args.bootstrap<16:parser.error("--bootstrap requires at least 16 draws")
    OUTPUT.mkdir(parents=True,exist_ok=True)
    frames,manifest=load_frames()
    results=[];scenes=[]
    for name,tolerance in CONFIGS:
        if args.only and name!=args.only:continue
        report,a,b=run_config(frames,manifest,name,tolerance,args.bootstrap)
        results.append(report)
        scene=export_scene(report,a,b,manifest["calibrations"])
        report["scene_id"]=scene["id"]
        scenes.append(scene)
        np.savez_compressed(OUTPUT/f"{name}-coadds.npz",before=a["image"],after=b["image"],
                            variance_before=a["variance"],variance_after=b["variance"],
                            valid_before=a["valid"],valid_after=b["valid"])
    output={"analysis_version":"0.2.0","analysis_sha256":sha256(Path(__file__).read_bytes()).hexdigest(),
            "calibrations":manifest["calibrations"],"configurations":results}
    (OUTPUT/"results.json").write_text(json.dumps(output,indent=2,allow_nan=False)+"\n",encoding="utf-8",newline="\n")
    demo_path=ROOT/"web/data/manifest.json"
    demo=json.loads(demo_path.read_text(encoding="utf-8"))
    legacy=[scene for scene in demo["scenes"] if scene.get("kind")!="coadd"]
    demo["legacy_analysis_sha256"]=demo.get("legacy_analysis_sha256",demo["analysis_sha256"])
    demo["analysis_version"]="0.2.0"
    demo["analysis_sha256"]=sha256(Path(__file__).read_bytes()+Path(base.__file__).read_bytes()).hexdigest()
    demo["motion_results"]="data/motion/results.json"
    demo["scenes"]=sorted(scenes,key=lambda s:0 if s["motion"]["id"]=="broad" else 1)+legacy
    demo_path.write_text(json.dumps(demo,indent=2,allow_nan=False)+"\n",encoding="utf-8",newline="\n")


if __name__=="__main__":main()
