"""Frozen A/B experiment: native-pixel target + fixed Gaia neighbours.

Independent nuisance fluxes in every exposure, no motion/flux prior. The old
0.3 products remain immutable. Positions below are declared before fitting.
"""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import argparse
import numpy as np
from scipy.optimize import least_squares
try:
    from . import gaia_motion as gaia
except ImportError:
    import gaia_motion as gaia

motion=gaia.motion
ROOT=Path(__file__).resolve().parents[1]
CONFIG={"version":"0.4.0", "stamp_radius_native_px":6, "neighbour_radius_sky_px":11,
        "derivative_step_sky_px":.002,"svd_relative_cut":1e-8,"fit_bound_px":1.5,
        "control_flux_scales":[.5,1.],"control_displacements_px":[[0.,0.],[.6,.05]],
        "heldout_positions_px":[[x,y] for y in [-12.,64.,88.] for x in [-12.,12.,52.,76.]],
        "seed":20261030,"bootstrap_draws":128}


def neighbour_positions(catalog, mjd, anchor):
    out=[]
    for source in catalog:
        if any(source.get(k) is None for k in ["pmra","pmdec","parallax"]):
            continue
        position=gaia.gaia_xy(source,mjd)
        if np.linalg.norm(position-anchor)<=CONFIG["neighbour_radius_sky_px"]:
            out.append((source["source_id"],position))
    return out


def prepare(sample, neighbours=()):
    """Marginalize linear nuisance amplitudes with a whitened SVD projector."""
    sample=dict(sample)
    columns=[sample["background"]];ids=[]
    for sid,position in neighbours:
        f=sample["frame"]
        px,py=f["wcs"].world_to_pixel_values(*motion.WCS.pixel_to_world_values(*(position+f["offset"])))
        epsf,_=motion.epsf_for(f,float(px),float(py))
        neighbour={**sample,"native_center":np.array([px,py]),"epsf":epsf,"anchor":position}
        psf=motion.stamp_model(neighbour,position)[:,0]
        if np.linalg.norm(psf/sample["error"])>1e-6:
            columns.append(psf[:,None]);ids.append(sid)
    nuisance=np.column_stack(columns)/sample["error"][:,None]
    u,s,_=np.linalg.svd(nuisance,full_matrices=False)
    rank=int(np.sum(s>s[0]*CONFIG["svd_relative_cut"]))
    sample.update(q=u[:,:rank],rank=rank,neighbour_ids=ids)
    return sample


def residual_sample(sample, position, return_amplitude=False):
    q=sample["q"]
    p=motion.stamp_model(sample,position)[:,0]/sample["error"]
    y=sample["data"]/sample["error"]
    p=p-q@(q.T@p);y=y-q@(q.T@y)
    information=p@p
    if information<1e-15:raise ValueError("unidentifiable_target")
    amplitude=(p@y)/information
    residual=amplitude*p-y
    return (residual,amplitude,1/np.sqrt(information)) if return_amplitude else residual


def fit(samples, anchor, multistart=True):
    anchor=np.asarray(anchor,float);h=CONFIG["derivative_step_sky_px"]
    def residual(pos):return np.concatenate([residual_sample(s,pos) for s in samples])
    def jacobian(pos):
        return np.column_stack([(residual(pos+np.eye(2)[i]*h)-residual(pos-np.eye(2)[i]*h))/(2*h) for i in range(2)])
    starts=[anchor]+([anchor+v for v in [(-.7,0),(.7,0),(0,-.7),(0,.7)]] if multistart else [])
    bound=CONFIG["fit_bound_px"]
    results=[least_squares(residual,start,jac=jacobian,bounds=(anchor-bound,anchor+bound),
             ftol=1e-8,xtol=1e-8,gtol=1e-7,max_nfev=100) for start in starts]
    result=min(results,key=lambda r:float(r.fun@r.fun))
    dof=len(result.fun)-sum(s["rank"]+1 for s in samples)-2
    chi2=float(result.fun@result.fun/dof)
    information=result.jac.T@result.jac
    covariance=np.linalg.pinv(information)*max(chi2,1.)
    details=[]
    for s in samples:
        _,a,e=residual_sample(s,result.x,True)
        details.append({"obs_id":s["frame"]["record"]["obs_id"],"mjd":s["frame"]["mjd"],
                        "amplitude":float(a),"amplitude_error":float(e),"snr":float(a/e),
                        "neighbour_ids":s["neighbour_ids"],"nuisance_rank":s["rank"]})
    w=np.array([max(0.,d["snr"])**2 for d in details])
    mjd=float(np.average([d["mjd"] for d in details],weights=w)) if w.sum() else float(np.mean([d["mjd"] for d in details]))
    return {"position":result.x,"covariance":covariance,"reduced_chi2":chi2,
            "success":bool(result.success),"at_boundary":bool(np.any(np.abs(result.x-anchor)>.95*bound)),
            "effective_mjd":mjd,"per_frame":details,"samples":samples}


def samples_for(frames,catalog,anchor,joint):
    return [prepare(motion.native_stamp(f,np.asarray(anchor),radius=CONFIG["stamp_radius_native_px"]),
                    neighbour_positions(catalog,f["mjd"],anchor) if joint else ()) for f in frames]


def bootstrap(result, seed):
    rng=np.random.default_rng(seed);positions=[];failed=0
    for _ in range(CONFIG["bootstrap_draws"]):
        samples=[]
        for s in result["samples"]:
            residual=residual_sample(s,result["position"])
            model=s["data"]+residual*s["error"]
            samples.append({**s,"data":model+rng.normal(size=len(model))*s["error"]})
        r=fit(samples,result["position"],False)
        if r["success"] and not r["at_boundary"]:positions.append(r["position"].tolist())
        else:failed+=1
    c=np.cov(np.asarray(positions).T)
    result["covariance"]=gaia.positive_envelope(result["covariance"],c)
    return {"draws":CONFIG["bootstrap_draws"],"accepted":len(positions),"failed_or_boundary":failed,
            "covariance_px2":c.tolist(),"positions_px":positions}


def experiment(frames,catalog,previous):
    index={f["record"]["obs_id"]:f for f in frames}
    before=[index[p["before"]["obs_id"]] for p in previous["spectral_pairs"]]
    after=[index[p["after"]["obs_id"]] for p in previous["spectral_pairs"]]
    training=[r for r in json.loads((gaia.CACHE/"references.json").read_text())["references"] if r["split"]=="training"]
    gaia.calibrate(before+after,training)
    output={"spectral_configuration":previous["spectral_configuration"],"models":{},"records":[]}
    for label,joint in [("single",False),("joint",True)]:
        a=fit(samples_for(before,catalog,motion.TARGET_ANCHOR,joint),motion.TARGET_ANCHOR)
        b=fit(samples_for(after,catalog,motion.TARGET_ANCHOR,joint),motion.TARGET_ANCHOR)
        boot_a=bootstrap(a,CONFIG["seed"]+1);boot_b=bootstrap(b,CONFIG["seed"]+2)
        vector=gaia.TRANSFORM@(b["position"]-a["position"])
        covariance=gaia.TRANSFORM@(a["covariance"]+b["covariance"])@gaia.TRANSFORM
        output["models"][label]={"target_before":motion.public_fit(a),"target_after":motion.public_fit(b),
            "east_arcsec":float(vector[0]),"north_arcsec":float(vector[1]),"displacement_arcsec":float(np.linalg.norm(vector)),
            "conditional_noise_covariance_arcsec2":covariance.tolist(),
            "conditional_noise_radial_arcsec":float(np.sqrt(vector@covariance@vector)/np.linalg.norm(vector)),
            "bootstrap_before":boot_a,"bootstrap_after":boot_b}
        print(f"{previous['id']} {label}: vector {vector.round(3)} arcsec",flush=True)
    # Both methods receive exactly the same injections, pixels and amplitudes.
    amplitudes={d["obs_id"]:d["amplitude"] for side in ["before","after"] for d in previous["target_"+side]["per_frame"]}
    for i,position in enumerate(CONFIG["heldout_positions_px"]):
        anchor=np.array(position)
        prepared={(label,epoch):samples_for(fs,catalog,anchor,joint)
                  for label,joint in [("single",False),("joint",True)] for epoch,fs in [(0,before),(1,after)]}
        for flux in CONFIG["control_flux_scales"]:
            for displacement in CONFIG["control_displacements_px"]:
                delta=np.array(displacement)
                for label in ["single","joint"]:
                    fits=[]
                    for epoch,fs in [(0,before),(1,after)]:
                        samples=[]
                        for s,f in zip(prepared[label,epoch],fs):
                            injected=motion.render_source(f,anchor+epoch*delta,flux*amplitudes[f["record"]["obs_id"]])
                            samples.append({**s,"data":s["data"]+injected[s["y"].astype(int),s["x"].astype(int)]})
                        fits.append(fit(samples,anchor))
                    a,b=fits;error=b["position"]-a["position"]-delta
                    covariance=a["covariance"]+b["covariance"]
                    valid=all(r["success"] and not r["at_boundary"] for r in fits)
                    output["records"].append({"position_index":i,"position_px":position,"flux_scale":flux,
                        "truth_delta_px":displacement,"model":label,"valid":valid,
                        "error_east_north_arcsec":(gaia.TRANSFORM@error).tolist(),
                        "within_68_ellipse":bool(valid and error@np.linalg.pinv(covariance)@error<=2.30),
                        "conditional_noise_covariance_px2":covariance.tolist()})
        print(f"{previous['id']}: heldout patch {i+1}/12",flush=True)
    output["groups"]=[]
    for label in ["single","joint"]:
        for flux in CONFIG["control_flux_scales"]:
            records=[r for r in output["records"] if r["model"]==label and r["flux_scale"]==flux]
            valid=[r for r in records if r["valid"]]
            errors=np.array([r["error_east_north_arcsec"] for r in valid])
            output["groups"].append({"model":label,"flux_scale":flux,"attempted":len(records),"valid":len(valid),
                "rms_arcsec":float(np.sqrt(np.mean(np.sum(errors**2,axis=1)))),
                "mean_bias_east_north_arcsec":np.mean(errors,axis=0).tolist(),
                "within_68_ellipse":sum(r["within_68_ellipse"] for r in records)})
    return output


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--configuration",choices=["broad","strict"],default="broad")
    args=parser.parse_args();destination=ROOT/"web/data/joint";destination.mkdir(parents=True,exist_ok=True)
    gaia.save_json(destination/"protocol.json",CONFIG)
    frames,manifest=gaia.load_frames();catalog=gaia.catalog_rows(manifest)
    previous=next(c for c in json.loads((gaia.OUTPUT/"results.json").read_text())["configurations"] if c["spectral_configuration"]==args.configuration)
    result=experiment(frames,catalog,previous)
    source=sha256(Path(__file__).read_bytes()).hexdigest()
    payload={"analysis_version":"0.4.0","source_sha256":source,"protocol":CONFIG,
             "gaia_analysis_sha256":json.loads((gaia.OUTPUT/"results.json").read_text())["analysis_sha256"],
             "gaia_catalog_sha256":manifest["gaia"]["sha256"],"result":result,
             "limits":["Diagnostic only; target noise covariance excludes registration, neighbour-position, PSF and background systematics.",
             "12 spatial patches were fixed before execution; four injections on a patch share background, exposures and fitted flux profile.",
             "Same ePSF family injects and fits; no extra source shot noise. This is not completeness or a false-positive rate.",
             "Neighbour positions from Gaia G<18.5 are fixed; infrared-only sources and extended galaxies are missing.",
             "No hyperparameters were selected using these heldout outcomes. Original 0.3 measurements remain the reference."]}
    gaia.save_json(destination/(args.configuration+".json"),payload)


if __name__=="__main__":main()
