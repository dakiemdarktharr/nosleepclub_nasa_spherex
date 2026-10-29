"""Cache epoch cutouts and official D6 calibration products for the motion study."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import json
from pathlib import Path

import requests
import fetch_wise0855 as fetch

ROOT = Path(__file__).resolve().parents[1]
CAL = ROOT / "data/raw/wise0855/calibration"
BUCKET = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"


def calibration_file(key, expected_hash):
    # Pin the products selected from the official bucket on 2026-10-30, so a
    # future calibration release does not silently change this experiment.
    path = CAL / Path(key).name
    if not path.exists():
        content = requests.get(BUCKET+key,timeout=(20,120))
        content.raise_for_status()
        if not content.content.startswith(b"SIMPLE"):
            raise RuntimeError("Calibration response is not FITS")
        path.write_bytes(content.content)
    digest=sha256(path.read_bytes()).hexdigest()
    if digest!=expected_hash:raise RuntimeError(f"Calibration checksum mismatch: {path.name}")
    return {"url":BUCKET+key,"path":str(path.relative_to(ROOT)).replace("\\","/"),
            "sha256":digest,"bytes":path.stat().st_size,
            "selection":"pinned official D6 calibration selected on 2026-10-30"}


def main():
    CAL.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((fetch.RAW/"manifest.json").read_text())
    selected=[]
    for row in manifest["records"]:
        mjd=row["mjd"]
        if 60989<=mjd<60994 or 61151<=mjd<61157:
            selected.append({"obs_id":row["obs_id"],"access_url":row["access_url"],"mjd":mjd,
                "detector":6,"collection":"spherex_qr2","cache_subdir":"coadd",
                "cutout_center_ra":133.76037473328523,"cutout_center_dec":-7.242149767967145,
                "epoch":"2025-11" if mjd<61000 else "2026-04"})
    records=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for future in as_completed([pool.submit(fetch.download,row) for row in selected]):
            result=future.result();records.append(result)
            print(f"{len(records)}/{len(selected)} {result['obs_id']} {result['status']}",flush=True)
    calibrations={
        "spectral_wcs":calibration_file(
            "qr2/spectral_wcs/cal-wcs-v4-2025-254/6/spectral_wcs_D6_spx_cal-wcs-v4-2025-254.fits",
            "8872df333578ac80c308c7077bb86e4d3d2a639ee53c75f0f2fe94ee04ab6a96"),
        "epsf":calibration_file(
            "qr3/epsf/cal-epsf-v1-2026-191/6/epsf_D6_spx_cal-epsf-v1-2026-191.fits",
            "52f85faeb93d67ed2020b68a628fc947c1f0b78cbf9282ca193ec6d588ac1a36"),
    }
    output={"records":sorted(records,key=lambda r:r["mjd"]),"calibrations":calibrations,
        "epoch_bounds_mjd":[[60989,60994],[61151,61157]],"source_manifest": "data/raw/wise0855/manifest.json"}
    (fetch.RAW/"coadd/manifest.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"cutouts":len(records),"calibrations":calibrations},indent=2),flush=True)


if __name__=="__main__":
    main()
