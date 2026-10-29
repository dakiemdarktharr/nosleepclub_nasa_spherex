"""Gaia-referenced validation of WISE 0855 motion on the same native exposures.

The old coadd analysis remains a frozen comparison. Catalog/quality rules and
cross-validation splits below do not use the fitted target displacement.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
from hashlib import sha256
import json
import inspect
from pathlib import Path

from astropy import log
from astropy.coordinates import get_body_barycentric
from astropy.io import fits
from astropy.table import Table
from astropy.time import Time
import astropy.units as u
import numpy as np
from scipy.ndimage import map_coordinates
from scipy.spatial.distance import cdist

try:
    from . import motion_analysis as motion
except ImportError:
    import motion_analysis as motion

base=motion.base
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/"data/raw/wise0855/gaia-wide/manifest.json"
CACHE=ROOT/"data/processed/gaia"
OUTPUT=ROOT/"web/data/gaia"
WIDE_SHAPE=(192,192)
WIDE_WCS=base.grid_wcs(WIDE_SHAPE)
GRID_OFFSET=(WIDE_SHAPE[0]-64)/2
TRANSFORM=np.diag([-base.SCALE,base.SCALE])
RULES={"ruwe_max":1.4,"visibility_periods_min":9,"ipd_frac_multi_peak_max":2,
       "proper_motion_max_mas_yr":300.,"absolute_parallax_max_mas":20.,
       "gaia_neighbour_min_arcsec":18.,"image_neighbour_min_px":3.5,
       "match_max_px":1.,"target_exclusion_px":8.,"reference_snr_min":7.,
       "reference_chi2_max":3.,"valid_frame_fraction_min":.70,"max_references":32,
       "training_sources_per_exposure_min":4,"seed":20261030}
PARAMETERS=["ra","dec","parallax","pmra","pmdec"]
PAIRS=[(i,j) for i in range(5) for j in range(i+1,5)]


def save_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n",encoding="utf-8",newline="\n")


def load_frames():
    manifest=json.loads(INPUT.read_text(encoding="utf-8"))
    with fits.open(ROOT/manifest["calibrations"]["spectral_wcs"]["path"]) as h:
        cwave=np.array(h["CWAVE"].data,float);cband=np.array(h["CBAND"].data,float)
    with fits.open(ROOT/manifest["calibrations"]["epsf"]["path"]) as h:
        table=np.array(h["EPSF"].data);over=float(h["EPSF"].header["OVSMPX"])
    frames=[]
    for record in manifest["records"]:
        f=base.read_frame(record)
        with fits.open(ROOT/record["path"]) as h:parent=base.alternate_wcs(h["IMAGE"].header,h,"A")
        yy,xx=np.indices(f["data"].shape,dtype=float);gx,gy=parent.pixel_to_world_values(xx,yy)
        f["cwave_map"]=map_coordinates(cwave,[gy,gx],order=1,mode="constant",cval=np.nan)
        f["cband_map"]=map_coordinates(cband,[gy,gx],order=1,mode="constant",cval=np.nan)
        tx,ty=f["wcs"].world_to_pixel_values(*f["position"])
        f.update(parent_wcs=parent,epsf_table=table,epsf_oversampling=over,
                 offset=np.zeros(2),offset_cov=np.zeros((2,2)),
                 wavelength=float(map_coordinates(f["cwave_map"],[[ty],[tx]],order=1)[0]),
                 bandwidth=float(map_coordinates(f["cband_map"],[[ty],[tx]],order=1)[0]))
        frames.append(f)
    return frames,manifest


def wide_detection_stack(frames):
    """Wide inverse-diagonal-variance stack for selecting references, not science S/N."""
    yy,xx=np.indices(WIDE_SHAPE,dtype=float);ra,dec=WIDE_WCS.pixel_to_world_values(xx,yy)
    numerator=np.zeros(WIDE_SHAPE);weight=np.zeros(WIDE_SHAPE)
    for f in frames:
        x,y=f["wcs"].world_to_pixel_values(ra,dec)
        image,var,support=base.bilinear(f["data"],f["variance"],f["valid"],x,y)
        good=np.isfinite(image)&np.isfinite(var)&(var>0)
        w=np.divide(1.,var,out=np.zeros_like(var),where=good)
        numerator+=np.nan_to_num(image)*w;weight+=w
    return np.divide(numerator,weight,out=np.full(WIDE_SHAPE,np.nan),where=weight>0)


@lru_cache(maxsize=128)
def earth_position(mjd):
    return get_body_barycentric("earth",Time(mjd,format="mjd")).xyz.to_value(u.au)


def gaia_xy(source,mjd,perturbation=None):
    """First-order barycentric proper motion + observer parallax; units mas, mas/yr.

    Perturbations use alpha*cos(delta), delta, parallax, mu_alpha*, mu_delta.
    Radial/perspective terms are neglected for the bounded low-motion references.
    """
    delta=np.zeros(5) if perturbation is None else np.asarray(perturbation)
    ra0=np.deg2rad(float(source["ra"]));dec0=np.deg2rad(float(source["dec"]))
    dt=Time(mjd,format="mjd").tcb.jyear-float(source["ref_epoch"])
    east=np.array([-np.sin(ra0),np.cos(ra0),0.])
    north=np.array([-np.cos(ra0)*np.sin(dec0),-np.sin(ra0)*np.sin(dec0),np.cos(dec0)])
    parallax=float(source["parallax"])+delta[2]
    de=delta[0]+(float(source["pmra"])+delta[3])*dt-parallax*(earth_position(float(mjd))@east)
    dn=delta[1]+(float(source["pmdec"])+delta[4])*dt-parallax*(earth_position(float(mjd))@north)
    ra=float(source["ra"])+de/(3.6e6*np.cos(dec0))
    dec=float(source["dec"])+dn/3.6e6
    return np.array(motion.WCS.world_to_pixel_values(ra,dec))


def gaia_covariance(source):
    errors=np.array([float(source[k+"_error"]) for k in PARAMETERS])
    correlation=np.eye(5)
    for i,j in PAIRS:
        correlation[i,j]=correlation[j,i]=float(source[f"{PARAMETERS[i]}_{PARAMETERS[j]}_corr"])
    covariance=errors[:,None]*correlation*errors[None,:]
    return (covariance+covariance.T)/2


def gaia_jacobian(source,mjd):
    identity=np.eye(5)
    return np.column_stack([(gaia_xy(source,mjd,v)-gaia_xy(source,mjd,-v))/2 for v in identity])


def catalog_rows(manifest):
    table=Table.read(ROOT/manifest["gaia"]["path"],format="votable",use_names_over_ids=True)
    rows=[]
    for row in table:
        result={}
        for key in table.colnames:
            value=row[key]
            result[key]=None if np.ma.is_masked(value) else value.item() if isinstance(value,np.generic) else value
        result["source_id"]=str(result["source_id"])
        rows.append(result)
    return rows


def catalog_quality(source):
    required=[*PARAMETERS,*[k+"_error" for k in PARAMETERS],"ruwe","ref_epoch"]
    if any(source.get(k) is None or not np.isfinite(source[k]) for k in required):return "missing_astrometry"
    if source["astrometric_params_solved"] not in [31,95]:return "no_proper_motion_solution"
    if source["ruwe"]>RULES["ruwe_max"]:return "ruwe"
    if source["visibility_periods_used"]<RULES["visibility_periods_min"]:return "visibility_periods"
    if source["duplicated_source"] or source["non_single_star"]:return "catalog_flag"
    if source["ipd_frac_multi_peak"]>RULES["ipd_frac_multi_peak_max"]:return "multiple_peaks"
    if np.hypot(source["pmra"],source["pmdec"])>RULES["proper_motion_max_mas_yr"]:return "large_motion"
    if abs(source["parallax"])>RULES["absolute_parallax_max_mas"]:return "nearby_star"
    if any(source.get(f"{PARAMETERS[i]}_{PARAMETERS[j]}_corr") is None for i,j in PAIRS):return "missing_covariance"
    return None


def candidate_references(frames,manifest):
    image=wide_detection_stack(frames);peaks=base.star_centers(image)-GRID_OFFSET
    rows=catalog_rows(manifest);mean_time=float(np.mean([f["mjd"] for f in frames]))
    xy=np.array([gaia_xy(s,mean_time) if s.get("pmra") is not None and s.get("pmdec") is not None and s.get("parallax") is not None
                 else motion.WCS.world_to_pixel_values(s["ra"],s["dec"]) for s in rows])
    neighbours=cdist(xy,xy);np.fill_diagonal(neighbours,np.inf)
    peak_neighbours=cdist(peaks,peaks);np.fill_diagonal(peak_neighbours,np.inf)
    matches=cdist(peaks,xy);candidates=[];audit=[];used=set()
    for i,p in enumerate(peaks):
        j=int(np.argmin(matches[i]));s=rows[j];reason=catalog_quality(s)
        if matches[i,j]>RULES["match_max_px"]:reason="no_close_gaia_match"
        elif neighbours[j].min()*base.SCALE<RULES["gaia_neighbour_min_arcsec"]:reason="gaia_neighbour"
        elif peak_neighbours[i].min()<RULES["image_neighbour_min_px"]:reason="image_neighbour"
        elif np.linalg.norm(p-motion.TARGET_ANCHOR)<RULES["target_exclusion_px"]:reason="target_region"
        elif s["source_id"] in used:reason="duplicate_match"
        audit.append({"peak_px":p.tolist(),"source_id":s["source_id"],"separation_arcsec":float(matches[i,j]*base.SCALE),"rejection":reason})
        if reason is None:
            used.add(s["source_id"])
            bright=float(image[int(round(p[1]+GRID_OFFSET)),int(round(p[0]+GRID_OFFSET))])
            candidates.append({"catalog":s,"anchor":xy[j].tolist(),"brightness":bright,"match_arcsec":float(matches[i,j]*base.SCALE)})
    candidates.sort(key=lambda r:-r["brightness"])
    return candidates,audit,image


def measure_references(frames,candidates):
    measurements=[]
    for i,reference in enumerate(candidates):
        source=reference["catalog"];entries=[]
        for f in frames:
            anchor=gaia_xy(source,f["mjd"]);px,py=f["wcs"].world_to_pixel_values(*motion.WCS.pixel_to_world_values(*anchor))
            reason=None
            if min(px,py,f["data"].shape[1]-1-px,f["data"].shape[0]-1-py)<7:reason="edge"
            if reason is None:
                try:
                    fit=motion.fit_position([f],anchor,bound=1.3)
                    if not fit["success"] or fit["at_boundary"]:reason="fit_boundary_or_failure"
                    elif fit["per_frame"][0]["snr"]<RULES["reference_snr_min"]:reason="low_snr"
                    elif fit["reduced_chi2"]>RULES["reference_chi2_max"]:reason="poor_psf_fit"
                except (ValueError,np.linalg.LinAlgError) as exc:reason=type(exc).__name__
            entry={"obs_id":f["record"]["obs_id"],"epoch":f["record"]["epoch"],"expected_px":anchor.tolist(),"rejection":reason}
            if reason is None:
                jac=gaia_jacobian(source,f["mjd"])
                entry.update(measured_px=fit["position"].tolist(),delta_px=(fit["position"]-anchor).tolist(),
                    covariance_px2=fit["covariance"].tolist(),gaia_jacobian=jac.tolist(),
                    gaia_covariance_px2=(jac@gaia_covariance(source)@jac.T).tolist(),
                    snr=fit["per_frame"][0]["snr"],reduced_chi2=fit["reduced_chi2"])
            entries.append(entry)
        accepted=sum(e["rejection"] is None for e in entries)
        eligible=accepted>=np.ceil(RULES["valid_frame_fraction_min"]*len(frames))
        for epoch in ["2025-11","2026-04"]:
            eligible&=sum(e["rejection"] is None and e["epoch"]==epoch for e in entries)>=3
        measurements.append({**reference,"entries":entries,"valid_frames":accepted,"eligible":bool(eligible)})
        print(f"Reference {i+1}/{len(candidates)} {source['source_id']}: {accepted}/{len(frames)} usable",flush=True)
    return measurements


def select_master(measurements):
    eligible=[r for r in measurements if r["eligible"]]
    quadrants=[[] for _ in range(4)]
    for r in eligible:
        x,y=np.array(r["anchor"])-motion.TARGET_ANCHOR
        quadrants[int(x>=0)+2*int(y>=0)].append(r)
    selected=[]
    while len(selected)<RULES["max_references"] and any(quadrants):
        for group in quadrants:
            if group and len(selected)<RULES["max_references"]:selected.append(group.pop(0))
    selected.sort(key=lambda r:sha256(r["catalog"]["source_id"].encode()).hexdigest())
    for i,r in enumerate(selected):r["split"]="heldout" if i%3==0 else "training"
    return selected


def reference_fingerprint(manifest):
    functions=[load_frames,wide_detection_stack,gaia_xy,gaia_covariance,gaia_jacobian,
               catalog_rows,catalog_quality,candidate_references,measure_references]
    source="\n".join(inspect.getsource(f) for f in functions).encode()
    return sha256(source+json.dumps({"rules":RULES,"inputs":manifest},sort_keys=True).encode()
                  +Path(motion.__file__).read_bytes()+Path(base.__file__).read_bytes()).hexdigest()


def design_at(point,model="translation"):
    if model=="translation":return np.eye(2)
    x,y=(np.asarray(point)-motion.TARGET_ANCHOR)/90.
    return np.array([[1,0,x,y,0,0],[0,1,0,0,x,y]],float)


def usable_entry(reference,obs_id):
    return next((e for e in reference["entries"] if e["obs_id"]==obs_id and e["rejection"] is None),None)


def fit_registration(frame,references,model="translation",multiplicity=None,gaia_draw=None):
    dimension=2 if model=="translation" else 6
    normal=np.zeros((dimension,dimension));rhs=np.zeros(dimension);used=[]
    for r in references:
        sid=r["catalog"]["source_id"];entry=usable_entry(r,frame["record"]["obs_id"])
        count=1 if multiplicity is None else multiplicity.get(sid,0)
        if entry is None or count==0:continue
        h=design_at(entry["expected_px"],model)
        covariance=np.array(entry["covariance_px2"])+np.array(entry["gaia_covariance_px2"])+np.eye(2)*.01**2
        precision=np.linalg.inv(covariance)*count
        delta=np.array(entry["delta_px"])
        if gaia_draw is not None:delta-=np.array(entry["gaia_jacobian"])@gaia_draw[sid]
        normal+=h.T@precision@h;rhs+=h.T@precision@delta
        used.append((sid,h,precision,delta))
    minimum=RULES["training_sources_per_exposure_min"] if model=="translation" else 6
    if len(used)<minimum or np.linalg.matrix_rank(normal)<dimension:
        raise RuntimeError(f"{frame['record']['obs_id']}: only {len(used)} usable references for {model}")
    covariance=np.linalg.inv(normal);theta=covariance@rhs
    chi2=float(sum((d-h@theta)@p@(d-h@theta) for _,h,p,d in used)/max(1,2*len(used)-dimension))
    covariance*=max(1.,chi2)
    target=design_at(motion.TARGET_ANCHOR,model)
    return {"model":model,"parameters":theta,"covariance":covariance,"offset":target@theta,
            "offset_covariance":target@covariance@target.T,"reduced_chi2":chi2,
            "source_ids":[sid for sid,*_ in used],"condition_number":float(np.linalg.cond(normal))}


def calibrate(frames,references,model="translation"):
    registrations={}
    for frame in frames:
        fit=fit_registration(frame,references,model)
        frame["offset"]=fit["offset"].copy();frame["offset_cov"]=fit["offset_covariance"].copy()
        registrations[frame["record"]["obs_id"]]=fit
    return registrations


def epoch_target_fit(frames,baseline=None,registrations=None):
    # Calibration perturbations must move the model on the SAME observed pixels.
    # Re-cutting the stamp can add/drop edge pixels and creates a spurious jump
    # in a finite-difference calibration derivative or a leave-one-out check.
    samples=None
    if baseline is not None:
        samples=[]
        for original in baseline["samples"]:
            delta=original["frame"]["offset"]-original["calibration_offset"]
            jacobian=original["jacobian"]
            if registrations is not None:
                reg=registrations[original["frame"]["record"]["obs_id"]]
                if reg["model"]=="affine":
                    p=reg["parameters"]
                    jacobian=jacobian@(np.eye(2)+np.array([[p[2],p[3]],[p[4],p[5]]])/90.)
            samples.append({**original,"native_center":original["native_center"]+original["jacobian"]@delta,
                            "jacobian":jacobian})
    fit=motion.fit_position(frames,motion.TARGET_ANCHOR,multistart=True,samples=samples)
    if baseline is None:
        for sample in fit["samples"]:sample["calibration_offset"]=sample["frame"]["offset"].copy()
    return fit


def mean_and_covariance(values,covariances):
    precision=[np.linalg.inv(c) for c in covariances]
    covariance=np.linalg.inv(sum(precision))
    return covariance@sum(p@v for p,v in zip(precision,values)),covariance


def heldout_validation(before,after,references,registrations):
    controls=[]
    for r in references:
        means=[];variances=[];counts=[]
        for frames in [before,after]:
            values=[];cov=[]
            for frame in frames:
                obs=frame["record"]["obs_id"];e=usable_entry(r,obs)
                if e is None:continue
                reg=registrations[obs];h=design_at(e["expected_px"],reg["model"])
                values.append(np.array(e["delta_px"])-h@reg["parameters"])
                cov.append(np.array(e["covariance_px2"])+h@reg["covariance"]@h.T+np.array(e["gaia_covariance_px2"]))
            counts.append(len(values))
            if not values:break
            mean,var=mean_and_covariance(values,cov);means.append(mean);variances.append(var)
        if len(means)!=2:continue
        controls.append({"id":r["catalog"]["source_id"],"anchor":r["anchor"],
            "delta_px":(means[1]-means[0]).tolist(),"epoch_residuals_px":[m.tolist() for m in means],
            "covariance_px2":(variances[0]+variances[1]).tolist(),"usable_frames_per_epoch":counts})
    if len(controls)<3:raise RuntimeError("Fewer than three heldout references with both epochs")
    delta=np.array([c["delta_px"] for c in controls])
    return controls,delta.T@delta/len(delta)


def target_offset_response(frames,baseline):
    """Gauss-Newton influence consistent with the conditional centroid covariance.

    Each exposure's offset enters its residual exactly like a source-position
    offset. Thus R_k = -(sum J.T J)^-1 J_k.T J_k. Using fixed-pixel residual
    Jacobians avoids optimizer/stamp-edge jumps from differencing refitted
    coordinates. The response to a common translation is exactly minus identity.
    """
    blocks=[];position=baseline["position"]
    for original in baseline["samples"]:
        central=motion.linear_fit(original,position)[0];columns=[]
        for axis in range(2):
            step=1e-4*max(abs(position[axis]),1.)
            perturbed=position.copy();perturbed[axis]+=step
            columns.append((motion.linear_fit(original,perturbed)[0]-central)/step)
        jac=np.column_stack(columns);blocks.append(jac.T@jac)
    inverse=np.linalg.pinv(sum(blocks))
    return [-inverse@block for block in blocks]


def positive_envelope(formal,empirical):
    values,vectors=np.linalg.eigh((empirical-formal+empirical.T-formal.T)/2)
    return formal+vectors@np.diag(np.maximum(values,0))@vectors.T


def registration_uncertainty(before,after,training,registrations,response_a,response_b,draws=256):
    # One catalog draw per star is shared across all exposures and both epochs.
    # Star-resampling counts are paired across epochs as well.
    rng=np.random.default_rng(RULES["seed"]+88);samples=[];epoch_samples=[];failed=0
    ids=[r["catalog"]["source_id"] for r in training]
    for _ in range(draws):
        counts=rng.multinomial(len(training),np.full(len(training),1/len(training)))
        multiplicity=dict(zip(ids,counts.tolist()))
        gaia_draw={r["catalog"]["source_id"]:rng.multivariate_normal(np.zeros(5),gaia_covariance(r["catalog"])) for r in training}
        shifts=[]
        try:
            for frames,response in [(before,response_a),(after,response_b)]:
                shift=np.zeros(2)
                for frame,jac in zip(frames,response):
                    reg=fit_registration(frame,training,multiplicity=multiplicity,gaia_draw=gaia_draw)
                    shift+=jac@(reg["offset"]-registrations[frame["record"]["obs_id"]]["offset"])
                shifts.append(shift)
            samples.append(shifts[1]-shifts[0])
            epoch_samples.append(shifts)
        except RuntimeError:failed+=1
    if len(samples)<draws*.8:raise RuntimeError("Too many calibration bootstrap failures")
    empirical=np.cov(np.array(samples).T,ddof=1)
    formal=np.zeros((2,2));formal_epochs=[]
    for frames,response in [(before,response_a),(after,response_b)]:
        epoch_formal=np.zeros((2,2))
        for frame,jac in zip(frames,response):
            epoch_formal+=jac@registrations[frame["record"]["obs_id"]]["offset_covariance"]@jac.T
        formal+=epoch_formal;formal_epochs.append(epoch_formal)
    covariance=positive_envelope(formal,empirical)
    epoch_covariances=[positive_envelope(f,np.cov(np.array(epoch_samples)[:,i,:].T,ddof=1)) for i,f in enumerate(formal_epochs)]
    return covariance,{"draws":draws,"accepted":len(samples),"failed":failed,
        "formal_covariance_px2":formal.tolist(),"paired_bootstrap_covariance_px2":empirical.tolist(),
        "used_covariance_px2":covariance.tolist(),
        "epoch_covariances_px2":[c.tolist() for c in epoch_covariances],
        "mean_shift_px":np.mean(samples,axis=0).tolist(),
        "response_sum_before":np.sum(response_a,axis=0).tolist(),"response_sum_after":np.sum(response_b,axis=0).tolist(),
        "note":"Paired resampling of training sources; one correlated Gaia 5-parameter draw per source shared across all epochs. Positive covariance envelope with the formal independent-exposure estimate. Conditional on measured centroids and ePSF."}


def fit_variant(before,after,training,heldout,baseline_vector,label,baseline_a,baseline_b,model="translation"):
    try:
        regs=calibrate(before+after,training,model)
        a=epoch_target_fit(before,baseline_a,regs);b=epoch_target_fit(after,baseline_b,regs)
        controls,cov=heldout_validation(before,after,heldout,regs)
        delta=TRANSFORM@(b["position"]-a["position"])
        return {"label":label,"model":model,"success":bool(a["success"] and b["success"] and not a["at_boundary"] and not b["at_boundary"]),
            "east_arcsec":float(delta[0]),"north_arcsec":float(delta[1]),"change_arcsec":float(np.linalg.norm(delta-baseline_vector)),
            "holdout_rms_arcsec":float(np.sqrt(np.trace(cov))*base.SCALE),
            "minimum_reference_count":min(len(v["source_ids"]) for v in regs.values())}
    except (RuntimeError,ValueError,np.linalg.LinAlgError) as exc:
        return {"label":label,"model":model,"success":False,"reason":str(exc)}


def run_configuration(frames,selected,previous,draws=128):
    index={f["record"]["obs_id"]:f for f in frames}
    before=[index[p["before"]["obs_id"]] for p in previous["spectral_pairs"]]
    after=[index[p["after"]["obs_id"]] for p in previous["spectral_pairs"]]
    training=[r for r in selected if r["split"]=="training"]
    heldout=[r for r in selected if r["split"]=="heldout"]
    registrations=calibrate(before+after,training)
    a=epoch_target_fit(before);b=epoch_target_fit(after)
    print(f"{previous['id']}: native target fits ready; validating uncertainty",flush=True)
    bootstrap_a=motion.bootstrap_position(a,draws,RULES["seed"]+11)
    bootstrap_b=motion.bootstrap_position(b,draws,RULES["seed"]+12)
    controls,holdout_cov=heldout_validation(before,after,heldout,registrations)
    response_a=target_offset_response(before,a);response_b=target_offset_response(after,b)
    cal_cov,cal_bootstrap=registration_uncertainty(before,after,training,registrations,response_a,response_b)
    stat_cov=a["covariance"]+b["covariance"]
    covariance=stat_cov+cal_cov+holdout_cov
    vector=TRANSFORM@(b["position"]-a["position"])
    covariance_arcsec=TRANSFORM@covariance@TRANSFORM
    distance=float(np.linalg.norm(vector));radial=float(np.sqrt(vector@covariance_arcsec@vector)/distance)
    swapped=fit_variant(before,after,heldout,training,vector,"swap",a,b)
    affine=fit_variant(before,after,training,heldout,vector,"affine",a,b,model="affine")
    leave_one_out=[]
    for r in training:
        sid=r["catalog"]["source_id"]
        leave_one_out.append(fit_variant(before,after,[v for v in training if v is not r],heldout,vector,sid,a,b))
    registrations=calibrate(before+after,training)
    weights=np.array(previous["common_spectral_weights"])
    coadd_a=motion.coadd(before,weights);coadd_b=motion.coadd(after,weights)
    snr_a=motion.aperture_snr(coadd_a,a["position"]);snr_b=motion.aperture_snr(coadd_b,b["position"])
    single_a=[motion.aperture_snr(motion.coadd([f],np.array([1.])),a["position"],coadd_a["valid"]) for f in before]
    single_b=[motion.aperture_snr(motion.coadd([f],np.array([1.])),b["position"],coadd_b["valid"]) for f in after]
    old=np.array([previous["east_arcsec"],previous["north_arcsec"]])
    report={**previous,"id":"gaia-"+previous["id"],"spectral_configuration":previous["id"],"gaia_reference":True,
        "target_before":motion.public_fit(a),"target_after":motion.public_fit(b),
        "bootstrap_before":bootstrap_a,"bootstrap_after":bootstrap_b,"calibration_bootstrap":cal_bootstrap,
        "training_source_ids":[r["catalog"]["source_id"] for r in training],
        "heldout_source_ids":[r["catalog"]["source_id"] for r in heldout],
        "training_reference_positions":[r["anchor"] for r in training],"heldout_controls":controls,
        "holdout_covariance_px2":holdout_cov.tolist(),"holdout_rms_arcsec":float(np.sqrt(np.trace(holdout_cov))*base.SCALE),
        "registration_covariance_px2":cal_cov.tolist(),"statistical_covariance_px2":stat_cov.tolist(),
        "east_arcsec":float(vector[0]),"north_arcsec":float(vector[1]),"displacement_arcsec":distance,
        "radial_error_arcsec":radial,"covariance_arcsec2":covariance_arcsec.tolist(),
        "mahalanobis_distance":float(np.sqrt(vector@np.linalg.inv(covariance_arcsec)@vector)),
        "previous_east_north_arcsec":old.tolist(),"change_from_previous_arcsec":float(np.linalg.norm(vector-old)),
        "predicted_motion":motion.expected_motion(a["effective_mjd"],b["effective_mjd"]),
        "reference_swap":swapped,"affine_sensitivity":affine,"leave_one_out":leave_one_out,
        "reference_swap_east_north_arcsec":[swapped["east_arcsec"],swapped["north_arcsec"]] if swapped["success"] else None,
        "reference_swap_change_arcsec":swapped.get("change_arcsec"),"reference_swap_unavailable_reason":swapped.get("reason"),
        "frame_registration":[{"obs_id":obs,"offset_px":v["offset"].tolist(),"covariance_px2":v["offset_covariance"].tolist(),
            "source_ids":v["source_ids"],"reduced_chi2":v["reduced_chi2"]} for obs,v in registrations.items()],
        "coadd_snr_before":snr_a,"coadd_snr_after":snr_b,
        "best_single_snr_before":max(v["snr"] for v in single_a if v["snr"] is not None),
        "best_single_snr_after":max(v["snr"] for v in single_b if v["snr"] is not None),
        "single_frame_aperture_snr_before":[{"obs_id":f["record"]["obs_id"],**v} for f,v in zip(before,single_a)],
        "single_frame_aperture_snr_after":[{"obs_id":f["record"]["obs_id"],**v} for f,v in zip(after,single_b)],
        "spectral_pairs":[{**p,"before":fa["record"],"after":fb["record"]} for p,fa,fb in zip(previous["spectral_pairs"],before,after)],
        "status":"candidate_motion_unconfirmed","fixed_target_pixel_sets_for_calibration_checks":True,
        "uncertainty_note":"Conditional centroid noise + calibration covariance + conservative second-moment heldout term; not a discovery probability or full systematic-error budget."}
    predicted=np.array([report["predicted_motion"]["east_arcsec"],report["predicted_motion"]["north_arcsec"]])
    report["difference_from_external_prediction_arcsec"]=float(np.linalg.norm(vector-predicted))
    epoch_position_cov=[]
    for i,fit in enumerate([a,b]):
        residuals=np.array([c["epoch_residuals_px"][i] for c in controls])
        field_cov=residuals.T@residuals/len(residuals)
        epoch_position_cov.append((fit["covariance"]+np.array(cal_bootstrap["epoch_covariances_px2"][i])+field_cov).tolist())
    report["epoch_position_covariances_px2"]=epoch_position_cov
    # Avoid carrying single-position controls from the previous calibration.
    report.pop("real_background_injection_controls",None)
    print(json.dumps({k:report[k] for k in ["id","east_arcsec","north_arcsec","radial_error_arcsec","holdout_rms_arcsec","change_from_previous_arcsec"]}),flush=True)
    print("SWAP",swapped,"AFFINE",affine,flush=True)
    return report,coadd_a,coadd_b,a,b


INJECTION_POSITIONS=[[17.,19.],[27.,17.],[43.,19.],[46.,34.],[41.,47.],[25.,47.],[14.,39.],[35.,40.]]


def injection_diagnostics(before,after,target_a,target_b,report):
    """Fixed off-target grid, two flux scales, stationary and moving controls.

    Uses the target's measured per-exposure flux profile only as a conditional
    injection SED. It does not add sources to downloadable science images.
    """
    records=[]
    additional=np.array(report["registration_covariance_px2"])+np.array(report["holdout_covariance_px2"])
    for location in INJECTION_POSITIONS:
        anchor=np.array(location)
        for scale in [.5,1.]:
            for kind,delta in [("stationary",np.zeros(2)),("moving",np.array([.6,.05]))]:
                injected=[]
                for frames,fit,pos in [(before,target_a,anchor),(after,target_b,anchor+delta)]:
                    flux={v["obs_id"]:max(v["amplitude"],0.)*scale for v in fit["per_frame"]}
                    injected.append([{**f,"data":f["data"]+motion.render_source(f,pos,flux[f["record"]["obs_id"]])} for f in frames])
                row={"anchor_px":location,"flux_scale":scale,"kind":kind,"injected_delta_px":delta.tolist()}
                try:
                    a=motion.fit_position(injected[0],anchor,bound=1.5,multistart=True)
                    b=motion.fit_position(injected[1],anchor,bound=1.5,multistart=True)
                    measured=b["position"]-a["position"];error=measured-delta
                    stat=a["covariance"]+b["covariance"];total=stat+additional
                    dm=float(np.sqrt(error@np.linalg.pinv(total)@error))
                    row.update(recovered_delta_px=measured.tolist(),error_arcsec=(TRANSFORM@error).tolist(),
                        error_mahalanobis=dm,statistical_mahalanobis=float(np.sqrt(error@np.linalg.pinv(stat)@error)),
                        within_68_percent_ellipse=bool(dm**2<=2.30),at_boundary=bool(a["at_boundary"] or b["at_boundary"]),
                        success=bool(a["success"] and b["success"]),reduced_chi2=[a["reduced_chi2"],b["reduced_chi2"]])
                except (ValueError,np.linalg.LinAlgError) as exc:row.update(success=False,reason=str(exc))
                records.append(row)
    groups=[]
    for scale in [.5,1.]:
        for kind in ["stationary","moving"]:
            rows=[r for r in records if r["flux_scale"]==scale and r["kind"]==kind]
            usable=[r for r in rows if r.get("success") and not r.get("at_boundary")]
            errors=np.array([r["error_arcsec"] for r in usable])
            groups.append({"flux_scale":scale,"kind":kind,"attempted":len(rows),"valid":len(usable),
                "failed_or_boundary":len(rows)-len(usable),
                "within_68_percent_ellipse":sum(r["within_68_percent_ellipse"] for r in usable),
                "coverage_among_all_attempts":sum(r["within_68_percent_ellipse"] for r in usable)/len(rows),
                "mean_error_east_north_arcsec":np.mean(errors,axis=0).tolist() if len(errors) else None,
                "rms_error_arcsec":float(np.sqrt(np.mean(np.sum(errors**2,axis=1)))) if len(errors) else None})
    return {"positions_px":INJECTION_POSITIONS,"records":records,"groups":groups,
        "note":"Fixed real-background grid, shared input images and matched injection/fit ePSF. Flux profile conditional on WISE 0855 fits; no added shot noise. Calibration kept fixed. These correlated small-sample diagnostics are not completeness, false-positive rate, or independent coverage calibration."}


def export_gaia_scene(report,a,b,manifest):
    report["scene_id"]="coadd-"+report["id"]
    scene=motion.export_scene(report,a,b,manifest["calibrations"])
    scene["label"]="Gaia · "+scene["label"]
    scene["gaia_evidence"]="data/gaia/results.json"
    for point,cov in zip(scene["measured_positions"],report["epoch_position_covariances_px2"]):
        point["covariance_px2"]=cov
        point["note"]="Epoch position covariance; shared reference errors correlate epochs, so motion covariance is reported separately."
    return scene


def export_products(manifest,selected,audit,measurements,image,reports,scenes,fingerprint):
    OUTPUT.mkdir(parents=True,exist_ok=True)
    valid=image[np.isfinite(image)];_,med,std=base.sigma_clipped_stats(valid)
    base.png_image(image,OUTPUT/"reference-field.png",med-2*std,med+15*std)
    file_hashes={name:sha256((ROOT/"scripts"/name).read_bytes()).hexdigest() for name in
                 ["gaia_motion.py","prepare_gaia_data.py","motion_analysis.py","build_demo.py","fetch_wise0855.py"]}
    analysis_sha=sha256(json.dumps(file_hashes,sort_keys=True).encode()).hexdigest()
    for scene in scenes:
        with fits.open(ROOT/"web"/scene["fits"],mode="update") as h:
            h[0].header["ANAVERS"]="0.3.0"
            h[0].header["ASTREF"]="Gaia DR3"
            h[0].header["ANAHASH"]=analysis_sha
            h[0].header["GACATHSH"]=manifest["gaia"]["sha256"]
            h[0].header["EVIDENCE"]="data/gaia/results.json"
    summary={"analysis_version":"0.3.0","analysis_sha256":analysis_sha,"source_sha256":file_hashes,
        "rules":RULES,"gaia_catalog":manifest["gaia"],"calibrations":manifest["calibrations"],
        "cutout_width_deg":manifest["cutout_width_deg"],"wide_grid_shape":list(WIDE_SHAPE),
        "wide_grid_pixel_scale_arcsec":base.SCALE,"grid_offset_px":GRID_OFFSET,
        "reference_field_image":"data/gaia/reference-field.png","reference_cache_sha256":fingerprint,
        "catalog_count":manifest["gaia"]["rows"],"candidate_count":len(measurements),
        "selected_count":len(selected),"references":selected,"matching_audit":audit,"configurations":reports,
        "limitations":["Gaia also contributes to the SPHEREx input WCS: heldout means excluded from this local fit, not independent of the mission calibration.",
            "Catalog-quality and signal cuts select brighter isolated stars; infrared-only blends can remain.",
            "Five-parameter first-order propagation with Earth observer; perspective and Gaia global systematics are not modeled.",
            "Calibration covariance is conditional on fixed ePSFs and measured reference centroids; heldout floor is a conservative second moment with only seven stars.",
            "Two target epochs cannot separate proper motion and parallax; broad/strict configurations share exposures."]}
    summary["reference_screening"]=[]
    for r in measurements:
        counts={}
        for entry in r["entries"]:
            if entry["rejection"] is not None:counts[entry["rejection"]]=counts.get(entry["rejection"],0)+1
        summary["reference_screening"].append({"source_id":r["catalog"]["source_id"],"valid_frames":r["valid_frames"],
            "eligible":r["eligible"],"selected":any(v["catalog"]["source_id"]==r["catalog"]["source_id"] for v in selected),"rejections":counts})
    summary["limitations"].append("Optical Gaia and infrared photocentres can differ with colour or unresolved neighbours; the reference-star floor need not describe this very red target.")
    save_json(OUTPUT/"results.json",summary)
    # Compact map/table payload keeps the main manifest small.
    map_rows=[]
    for r in selected:
        s=r["catalog"]
        row={"source_id":s["source_id"],"x":r["anchor"][0]+GRID_OFFSET,"y":r["anchor"][1]+GRID_OFFSET,
             "split":r["split"],"ra_deg":s["ra"],"dec_deg":s["dec"],"ruwe":s["ruwe"],
             "g_mag":s["phot_g_mean_mag"],"valid_frames":r["valid_frames"],"match_arcsec":r["match_arcsec"],
             "catalog_ref_epoch_jyear_tcb":s["ref_epoch"]}
        for c in reports:
            control=next((v for v in c["heldout_controls"] if v["id"]==s["source_id"]),None)
            if control:row[c["spectral_configuration"]+"_residual_arcsec"]=(TRANSFORM@np.array(control["delta_px"])).tolist()
        map_rows.append(row)
    save_json(OUTPUT/"map.json",{"image":"data/gaia/reference-field.png","shape":list(WIDE_SHAPE),
        "references":map_rows,"target":{"x":motion.TARGET_ANCHOR[0]+GRID_OFFSET,"y":motion.TARGET_ANCHOR[1]+GRID_OFFSET}})
    path=ROOT/"web/data/manifest.json";demo=json.loads(path.read_text(encoding="utf-8"))
    demo["coadd_analysis_sha256"]=demo.get("coadd_analysis_sha256",demo["analysis_sha256"])
    demo["analysis_version"]="0.3.0";demo["analysis_sha256"]=analysis_sha
    demo["gaia_results"]="data/gaia/results.json";demo["gaia_map"]="data/gaia/map.json"
    legacy=[s for s in demo["scenes"] if not s.get("motion",{}).get("gaia_reference")]
    demo["scenes"]=sorted(scenes,key=lambda s:0 if s["motion"]["spectral_configuration"]=="broad" else 1)+legacy
    save_json(path,demo)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references-only",action="store_true")
    parser.add_argument("--publish",action="store_true",help="Export science products and update the static demo manifest")
    args=parser.parse_args();log.setLevel("WARNING")
    frames,manifest=load_frames();CACHE.mkdir(parents=True,exist_ok=True)
    candidates,audit,image=candidate_references(frames,manifest)
    print(f"{len(candidates)} isolated Gaia matches before native-pixel quality screening",flush=True)
    cache_path=CACHE/"reference-measurements.json"
    fingerprint=reference_fingerprint(manifest)
    if cache_path.exists() and json.loads(cache_path.read_text())["fingerprint"]==fingerprint:
        measured=json.loads(cache_path.read_text())["measurements"]
    else:
        measured=measure_references(frames,candidates)
        save_json(cache_path,{"fingerprint":fingerprint,"measurements":measured})
    selected=select_master(measured)
    save_json(CACHE/"references.json",{"rules":RULES,"matching_audit":audit,"references":selected})
    np.savez_compressed(CACHE/"wide-field.npz",image=image)
    print(f"Selected {len(selected)} references: {sum(r['split']=='training' for r in selected)} training / {sum(r['split']=='heldout' for r in selected)} heldout",flush=True)
    if args.references_only:return
    prior=json.loads((ROOT/"web/data/motion/results.json").read_text(encoding="utf-8"))
    reports=[];scenes=[]
    for old in prior["configurations"]:
        report,a,b,fit_a,fit_b=run_configuration(frames,selected,old)
        if args.publish:
            report["injection_diagnostics"]=injection_diagnostics(a["frames"],b["frames"],fit_a,fit_b,report)
            # Short compatibility summary, all controls remain in the diagnostic JSON.
            report["real_background_injection_controls"]=[r for r in report["injection_diagnostics"]["records"] if r["flux_scale"]==1.]
            scenes.append(export_gaia_scene(report,a,b,manifest))
        reports.append(report)
        save_json(CACHE/(report["id"]+".json"),report)
    if args.publish:export_products(manifest,selected,audit,measured,image,reports,scenes,fingerprint)


if __name__=="__main__":main()
