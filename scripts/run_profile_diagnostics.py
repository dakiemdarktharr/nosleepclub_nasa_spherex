"""Compare covariance methods on the SAME opened-field Gaussian controls.

All source hashes must be committed before execution. This is development,
not an independent holdout, calibration, detection, or WISE 0855 remeasurement.
"""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import numpy as np
from . import diagnose_bias as diagnostic
from . import profile_uncertainty as profile

ROOT = diagnostic.ROOT
OUT = ROOT / "data/raw/benchmark/profile-gaussian64-development.json"
RULES = {"version": "0.10.0-profile-development.1", "fields": diagnostic.RULES["fields"],
         "cases": diagnostic.RULES["cases"], "draws": 64, "seed": diagnostic.RULES["seed"],
         "role": "paired development comparison on already opened layouts; matched ePSF Gaussian noise only",
         "ellipse68_threshold": 2.27886856637673, "ellipse95_threshold": 5.99146454710798}


def source_hashes():
    return {p:sha256((ROOT / p).read_bytes()).hexdigest() for p in
            ["scripts/run_profile_diagnostics.py", "scripts/profile_uncertainty.py", "scripts/diagnose_bias.py"]}


def save(report):
    diagnostic.save(OUT, report)


def run():
    sources = source_hashes()
    for path in sources:
        committed = subprocess.check_output(["git", "show", "HEAD:"+path], cwd=ROOT)
        if sha256(committed).hexdigest() != sources[path]:
            raise RuntimeError("Commit profile diagnostic sources before execution")
    previous = json.loads((ROOT / "data/raw/benchmark/bias-gaussian64-development.json").read_text())
    report = {"rules":RULES, "sources":sources, "profile_rules":profile.RULES,
              "paired_control_sha256":sha256((ROOT / "data/raw/benchmark/bias-gaussian64-development.json").read_bytes()).hexdigest(),
              "cases":[], "completed":False}
    if OUT.exists():
        report = json.loads(OUT.read_text())
        if report["sources"] != sources or report["rules"] != RULES:
            raise RuntimeError("Existing run belongs to different sources or rules")
        if report["completed"]:
            raise RuntimeError("Completed diagnostic already exists")
    for ident in RULES["fields"]:
        print("LOAD",ident,flush=True)
        _,opened,catalog,xy,before,after,_ = diagnostic.load_field(ident)
        old_field = next(f for f in previous["fields"] if f["id"] == ident)
        for wanted in RULES["cases"]:
            case = next((c for c in report["cases"] if c["field_id"]==ident and c["snr_per_frame"]==wanted["snr_per_frame"]),None)
            if case is not None and len(case["records"])==RULES["draws"]:
                continue
            old_case = next(c for c in old_field["cases"] if c["snr_per_frame"]==wanted["snr_per_frame"])
            anchor=old_case["anchor"];truth=np.asarray(wanted["motion"])
            planted=diagnostic.study.injected_frames(before,after,anchor,truth,wanted["snr_per_frame"],"nearest")
            signals=[[{**a,"data":a["data"]-o["data"]} for a,o in zip(added,original)] for added,original in zip(planted,[before,after])]
            if case is None:
                case={"field_id":ident,"snr_per_frame":wanted["snr_per_frame"],"truth_delta_px":truth.tolist(),"records":[]}
                report["cases"].append(case)
            rng=np.random.default_rng(RULES["seed"])
            for draw in range(RULES["draws"]):
                fs=[[{**f,"data":f["data"]+rng.normal(size=f["data"].shape)*np.sqrt(f["variance"])} for f in frames] for frames in signals]
                if draw<len(case["records"]):continue
                row={"draw":draw,"numeric_valid":False,"accepted":False}
                try:
                    fits=[diagnostic.fit_epoch(frames,catalog,xy,anchor) for frames in fs]
                    vector=diagnostic.study.gaia.TRANSFORM@(fits[1]["position"]-fits[0]["position"]-truth)
                    expected=np.asarray(old_case["independent_gaussian_controls"]["records"][draw]["error_east_north_arcsec"])
                    if np.max(np.abs(vector-expected))>1e-5:raise RuntimeError("Point estimator changed across covariance comparison")
                    registration=sum(diagnostic.study.bench.registration_covariance(frames) for frames in fs)
                    transform=diagnostic.study.gaia.TRANSFORM
                    gn=transform@(sum(f["covariance"] for f in fits)+registration)@transform.T
                    numeric=all(diagnostic.study.bench.valid_fit(f) for f in fits)
                    row.update(numeric_valid=bool(numeric),accepted=bool(numeric and all(f["quality"]["accepted"] for f in fits)),
                               error_east_north_arcsec=vector.tolist(),gauss_newton_covariance_arcsec2=gn.tolist(),
                               gauss_newton_q=float(vector@np.linalg.solve(gn,vector)))
                    candidate=[profile.covariance(f) for f in fits];row["epoch_curvature"]=candidate
                    if all(c["supported"] for c in candidate):
                        cov=transform@(sum(np.asarray(c["covariance_px2"]) for c in candidate)+registration)@transform.T
                        row.update(profile_covariance_arcsec2=cov.tolist(),profile_q=float(vector@np.linalg.solve(cov,vector)))
                    row["motion_likelihood"]=profile.motion_likelihood(fits,anchor,truth)
                except (ValueError,np.linalg.LinAlgError) as exc:
                    row["failure"]=type(exc).__name__
                case["records"].append(row)
                if (draw+1)%16==0:
                    save(report);print("DRAWS",ident,wanted["snr_per_frame"],draw+1,flush=True)
            save(report)
    report["completed"]=True;save(report)
    for case in report["cases"]:
        valid=[r for r in case["records"] if r["numeric_valid"]]
        p=[r for r in valid if "profile_q" in r];lr=[r for r in valid if r.get("motion_likelihood",{}).get("supported")]
        print("SUMMARY",case["field_id"],case["snr_per_frame"],"numeric",len(valid),
              "GN68",sum(r["gauss_newton_q"]<=RULES["ellipse68_threshold"] for r in valid),
              "profile68",sum(r["profile_q"]<=RULES["ellipse68_threshold"] for r in p),"/",len(p),
              "LR68",sum(r["motion_likelihood"]["delta_chi2"]<=RULES["ellipse68_threshold"] for r in lr),"/",len(lr),flush=True)


if __name__ == "__main__":
    run()
