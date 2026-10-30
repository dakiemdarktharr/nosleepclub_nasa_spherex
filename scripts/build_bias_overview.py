"""Compact auditable derivative of opened-field diagnostic runs (no new fits)."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/benchmark"
OUT = ROOT / "web/data/diagnostics/bias-overview.json"


def compact(value):
    keys = ["numeric_valid", "accepted", "quality_reasons", "error_east_north_arcsec", "error_arcsec",
            "measured_east_north_arcsec", "expected_east_north_arcsec", "observed_snr", "covariance_arcsec2", "mahalanobis2_raw"]
    return {k: value[k] for k in keys if k in value}


def main():
    paths = [RAW / v for v in ["bias-w350-development.json", "bias-comparison-development.json", "bias-gaussian64-development.json"]]
    source_sha = sha256((ROOT / "scripts/diagnose_bias.py").read_bytes()).hexdigest()
    report = {"schema_version": 1, "role": "post-validation diagnostics; all three fields were already opened",
              "changes_point_model": False, "changes_calibrator": False, "scientific_promotion": False,
              "created_at": datetime.now(timezone.utc).isoformat(), "source_sha256": source_sha,
              "builder_sha256": sha256(Path(__file__).read_bytes()).hexdigest(), "inputs": [], "cases": [],
              "limits": ["same original exposures/noise are reused across injection cases",
                         "Gaussian controls use matched ePSF and original variance; not physical or external validation",
                         "random streams are paired between cases; do not pool case counts as independent trials",
                         "jackknife holds registration fixed; not total sampling covariance",
                         "fixed-final-weight mode costs are not posterior mode probabilities",
                         "SNR2 stationary and SNR4 moving cases change two factors; not a pure SNR ablation"]}
    cases = {}
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not data["completed"] or data["source_sha256"] != source_sha:
            raise RuntimeError("Incomplete or changed diagnostic source: " + str(path))
        report["inputs"].append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path.read_bytes()).hexdigest(),
                                 "noise_draws": data["noise_draws"], "jackknife": data["jackknife_requested"]})
        for field in data["fields"]:
            for case in field["cases"]:
                key = (field["id"], case["snr_per_frame"], tuple(case["truth_delta_px"]))
                item = cases.setdefault(key, {"field_id": field["id"], "source": field["source"], "patch_index": case["patch_index"],
                    "anchor": case["anchor"], "snr_per_frame": case["snr_per_frame"], "truth_delta_px": case["truth_delta_px"],
                    "original": compact(case["frozen_result"]), "signal_only_control": compact(case["signal_only_control"]),
                    "replay_max_vector_difference_arcsec": case["replay_max_vector_difference_arcsec"],
                    "point_model_interventions": {k: compact(v) for k, v in case["point_model_interventions"].items()},
                    "mode_profiles": [v["profile"] for v in case["epochs"]], "epochs": [{"fit":v["fit"], "frames":v["frames"]} for v in case["epochs"]]})
                if "exposure_influence" in case:
                    jack = case["exposure_influence"]
                    item["exposure_influence"] = {**{k: v for k, v in jack.items() if k != "trials"},
                        "trials": [{"epoch":v["epoch"], "removed_obs_id":v["removed_obs_id"],
                                    "vector_change_arcsec":v.get("vector_change_arcsec"), "result":compact(v["result"])} for v in jack["trials"]]}
                if data["noise_draws"] == 64:
                    noise = case["independent_gaussian_controls"]
                    values = [v for v in noise["records"] if v["numeric_valid"]]
                    item["gaussian_controls"] = {**{k:v for k,v in noise.items() if k != "records"},
                        "records": [compact(v) for v in noise["records"]],
                        "fraction_error_ge_original": float(np.mean([v["error_arcsec"] >= case["frozen_result"]["error_arcsec"] for v in values]))}
    report["cases"] = [cases[k] for k in sorted(cases)]
    if len(report["cases"]) != 6 or not all("gaussian_controls" in v and "exposure_influence" in v for v in report["cases"]):
        raise RuntimeError("Missing cases or diagnostic components")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    for item in report["cases"]:
        g=item["gaussian_controls"]
        print(item["field_id"], item["snr_per_frame"], "observed error",round(item["original"]["error_arcsec"],3),
              "Gaussian RMS",round(g["rms_numeric_arcsec"],3), "raw68",str(g["raw68_numeric"])+"/"+str(g["numeric"]),
              "larger Gaussian errors", round(g["fraction_error_ge_original"],3))
    print("SAVED", OUT, OUT.stat().st_size)


if __name__ == "__main__":
    main()
