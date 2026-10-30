"""Post-validation interventions on OPENED 0.9 fields; never new validation.

Replays frozen cases, examines final-weight likelihood modes, and measures
exposure influence. Original sky/noise, signal-only, and new Gaussian-noise
controls distinguish mechanisms without treating repeated trials as new skies.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import time

import numpy as np

from . import ablation_study as study

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web/data/diagnostics"
model = study.model
motion = study.motion
joint = model.joint
RULES = {
    "version": "0.10.0-diagnostic.1",
    "role": "post-validation development on already opened fields",
    "fields": ["w350p35", "w090p10", "w210m20"],
    "patch_index": 1,
    "truth_psf": "nearest",
    "cases": [{"snr_per_frame": 2., "motion": [0., 0.]},
              {"snr_per_frame": 4., "motion": [.6, .05]}],
    "centroid_starts_px": [[0., 0.], [-1.4, 0.], [1.4, 0.], [0., -1.4],
                            [0., 1.4], [-1., -1.], [1., 1.], [-1., 1.], [1., -1.]],
    "mode_separation_px": .15,
    "interpretation": "shared original exposures/noise: trial counts are NOT independent replication",
    "controls": "signal-only and independent native-pixel Gaussian noise are solver diagnostics; matched ePSF, not physical validation",
    "seed": 20261030,
}


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def jsonable(value):
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value, np.generic):
        return jsonable(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jsonable(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_field(ident):
    design = study.read(study.OUT / "design.json")
    item = next(v for v in design["fields"]["validation"] if v["field"]["id"] == ident)
    path = study.OUT / ("validation-" + ident + ".json")
    opened = study.read(path)
    study.old.validate(item)
    _, frames, catalog, screening = study.old.load(item)
    lookup = {r["obs_id"]: r for r in opened["registrations"]}
    frames = [{**f, "offset": np.asarray(lookup[f["record"]["obs_id"]]["offset_px"]),
               "offset_cov": np.asarray(lookup[f["record"]["obs_id"]]["covariance_px2"])}
              for f in frames if f["record"]["obs_id"] in lookup]
    xy = model.old.positions(catalog, frames)
    by_id = {f["record"]["obs_id"]: f for f in frames}
    before, after = [[by_id[p[e]] for p in item["pairs"]] for e in ["before", "after"]]
    return item, opened, catalog, xy, before, after, {"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path)}


def fit_epoch(frames, catalog, xy, anchor, kind="plane_fixed"):
    ref = motion.fit_position(frames, np.asarray(anchor), multistart=True)
    return model.fit(frames, catalog, xy, anchor, kind, ref)


def summarize_fit(fit):
    return {"position_px": fit["position"], "covariance_px2": fit["covariance"],
            "quality": fit["quality"], "reduced_chi2": fit["reduced_chi2"],
            "at_boundary": fit["at_boundary"], "information_rank": fit["information_rank"]}


def pair(fs, catalog, xy, anchor, truth, kinds=("plane_fixed",)):
    return study.measure(*fs, catalog, xy, [anchor, anchor], list(kinds), truth=truth)


def profile_modes(fit, anchor):
    # Same final IRLS weights for all starts. This diagnoses likelihood modes,
    # not the sampling distribution of the robust estimator.
    samples = fit["samples"]
    starts = []
    for delta in RULES["centroid_starts_px"]:
        try:
            result = model.old.solve(samples, np.asarray(anchor), starts=False,
                                     initial=np.asarray(anchor) + delta)
            starts.append({"position_px": result.x.tolist(), "cost": float(result.fun @ result.fun),
                           "success": bool(result.success)})
        except (ValueError, np.linalg.LinAlgError) as exc:
            starts.append({"failure": type(exc).__name__})
    valid = sorted([v for v in starts if v.get("success")], key=lambda v: v["cost"])
    modes = []
    for value in valid:
        if all(np.linalg.norm(np.asarray(value["position_px"]) - m["position_px"]) > RULES["mode_separation_px"] for m in modes):
            modes.append({**value, "delta_cost": value["cost"] - valid[0]["cost"]})
    return {"starts": starts, "distinct_modes": modes, "weights": "fixed at final full-fit IRLS weights"}


def frame_features(frames, catalog, xy, anchor, fit):
    output = []
    for f, s, detail in zip(frames, fit["samples"], fit["per_frame"]):
        near = xy[f["record"]["obs_id"]]
        distance = np.linalg.norm(near - np.asarray(anchor), axis=1)
        r, amp, amp_error = joint.residual_sample(s, fit["position"], True)
        output.append({"obs_id": f["record"]["obs_id"], "mjd": f["mjd"],
                       "detector_xy_native": s["native_center"], "epsf_zone": s["zone"],
                       "wavelength_um_at_field_center": f["wavelength"], "bandwidth_um_at_field_center": f["bandwidth"],
                       "valid_stamp_pixels": len(s["data"]), "core_coverage": detail["core_coverage"],
                       "core_rms": detail["core_rms"], "information_fraction": detail["information_fraction"],
                       "fitted_amplitude": amp, "amplitude_error": amp_error, "snr": detail["snr"],
                       "neighbors_in_2_native_px": int(np.sum(distance < 2.)),
                       "nearest_catalog_arcsec": float(distance.min() * study.bench.base.SCALE) if len(distance) else None,
                       "downweighted_pixels": detail["downweighted_pixels"]})
    return output


def jackknife(fs, catalog, xy, anchor, truth, full):
    output = []
    full_vector = np.asarray(full["measured_east_north_arcsec"])
    for epoch, frames in enumerate(fs):
        for index, frame in enumerate(frames):
            reduced = [list(v) for v in fs]
            reduced[epoch] = frames[:index] + frames[index + 1:]
            value = pair(reduced, catalog, xy, anchor, truth)["plane_fixed"]
            row = {"epoch": ["before", "after"][epoch], "removed_obs_id": frame["record"]["obs_id"], "result": value}
            if value.get("numeric_valid"):
                row["vector_change_arcsec"] = float(np.linalg.norm(np.asarray(value["measured_east_north_arcsec"]) - full_vector))
            output.append(row)
    shifts = [v["vector_change_arcsec"] for v in output if "vector_change_arcsec" in v]
    return {"trials": output, "valid": len(shifts), "maximum_vector_change_arcsec": max(shifts) if shifts else None,
            "median_vector_change_arcsec": float(np.median(shifts)) if shifts else None,
            "qualification": "reference translations held fixed; this is exposure sensitivity, not total jackknife covariance"}


def run_case(opened, catalog, xy, before, after, wanted, run_jackknife, noise_draws):
    row = next(r for r in opened["injections"] if r["patch_index"] == RULES["patch_index"]
               and r["truth_psf"] == RULES["truth_psf"] and r["snr_per_frame"] == wanted["snr_per_frame"]
               and r["truth_delta_px"] == wanted["motion"])
    anchor = row["anchor"]; truth = row["truth_delta_px"]
    fs = study.injected_frames(before, after, anchor, truth, row["snr_per_frame"], row["truth_psf"])
    fits = [fit_epoch(v, catalog, xy, anchor) for v in fs]
    values = pair(fs, catalog, xy, anchor, truth, kinds=tuple(model.MODELS))
    saved = row["models"]["plane_fixed"]
    replay_error = float(np.max(np.abs(np.asarray(values["plane_fixed"]["measured_east_north_arcsec"]) - saved["measured_east_north_arcsec"])))
    if replay_error > 1e-5:
        raise RuntimeError("Frozen case did not reproduce: " + str(replay_error))
    result = {"patch_index": row["patch_index"], "anchor": anchor, "snr_per_frame": row["snr_per_frame"],
              "truth_psf": row["truth_psf"], "truth_delta_px": truth,
              "frozen_result": saved, "replay_max_vector_difference_arcsec": replay_error,
              "point_model_interventions": values,
              "epochs": [{"fit": summarize_fit(fit), "profile": profile_modes(fit, anchor),
                          "frames": frame_features(frames, catalog, xy, anchor, fit)} for frames, fit in zip(fs, fits)]}
    # An oracle control removes the original sky AND its original noise. It is
    # deliberately not an estimator available for real unknown sources.
    signals = [[{**planted, "data": planted["data"] - original["data"]}
                for original, planted in zip(originals, added)]
               for originals, added in zip([before, after], fs)]
    result["signal_only_control"] = pair(signals, catalog, xy, anchor, truth)["plane_fixed"]
    noise_results = []; rng = np.random.default_rng(RULES["seed"])
    for _ in range(noise_draws):
        noisy = [[{**f, "data": f["data"] + rng.normal(size=f["data"].shape) * np.sqrt(f["variance"])} for f in frames] for frames in signals]
        noise_results.append(pair(noisy, catalog, xy, anchor, truth)["plane_fixed"])
    if noise_results:
        valid = [r for r in noise_results if r.get("numeric_valid")]
        accepted = [r for r in valid if r["accepted"]]
        result["independent_gaussian_controls"] = {"draws": noise_draws, "numeric": len(valid), "accepted": len(accepted),
            "rms_numeric_arcsec": float(np.sqrt(np.mean([r["error_arcsec"] ** 2 for r in valid]))) if valid else None,
            "raw68_numeric": sum(r["mahalanobis2_raw"] <= study.cc.RULES["ellipse68_threshold"] for r in valid),
            "records": noise_results, "qualification": RULES["controls"]}
    if run_jackknife:
        result["exposure_influence"] = jackknife(fs, catalog, xy, anchor, truth, values["plane_fixed"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fields", nargs="+", choices=RULES["fields"], default=RULES["fields"])
    parser.add_argument("--jackknife", action="store_true")
    parser.add_argument("--noise-draws", type=int, default=0)
    parser.add_argument("--output", type=Path, default=OUT / "bias-audit.json")
    args = parser.parse_args()
    if not 0 <= args.noise_draws <= 256:
        parser.error("noise-draws must be in [0,256]")
    started = time.monotonic()
    result = {"rules": RULES, "source_sha256": digest(__file__), "frozen_sources": study.sources(),
              "design_sha256": digest(study.OUT / "design.json"), "noise_draws": args.noise_draws,
              "jackknife_requested": args.jackknife, "completed": False, "fields": []}
    for ident in args.fields:
        print("LOAD", ident, flush=True)
        item, opened, catalog, xy, before, after, source = load_field(ident)
        field = {"id": ident, "source": source, "cases": [], "exposure_count": len(before) + len(after),
                 "epoch_mjd_ranges": [[min(f["mjd"] for f in v), max(f["mjd"] for f in v)] for v in [before, after]]}
        result["fields"].append(field)
        for wanted in RULES["cases"]:
            print("CASE", ident, wanted, flush=True)
            case = run_case(opened, catalog, xy, before, after, wanted, args.jackknife, args.noise_draws)
            field["cases"].append(case); result["elapsed_seconds"] = time.monotonic() - started
            save(args.output, result)
            print("REPLAY", ident, case["replay_max_vector_difference_arcsec"],
                  "ORIGINAL_ERROR", case["frozen_result"]["error_arcsec"],
                  "SIGNAL_ONLY_ERROR", case["signal_only_control"].get("error_arcsec"), flush=True)
    result["completed"] = True; result["elapsed_seconds"] = time.monotonic() - started
    save(args.output, result)
    print("COMPLETE", args.output, result["elapsed_seconds"], flush=True)


if __name__ == "__main__":
    main()
