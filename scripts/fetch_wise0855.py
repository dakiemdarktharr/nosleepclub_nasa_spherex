"""Download real IRSA D6 cutouts, keeping reproducible URLs and SHA-256 hashes."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import io
import json
from pathlib import Path
import time

import truststore

truststore.inject_into_ssl()

from astropy.io import fits
from astropy.table import Table
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "wise0855"
RA = 133.79512917
DEC = -7.24514722
QUERY = (
    "https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr2"
    f"&POS=circle+{RA}+{DEC}+0.05"
)


def download(row: dict) -> dict:
    url = row["access_url"]
    folder = RAW / row.get("cache_subdir", "")
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / Path(url).name
    center_ra = row.get("cutout_center_ra", RA)
    center_dec = row.get("cutout_center_dec", DEC)
    cutout_url = f"{url}?center={center_ra},{center_dec}&size=0.12"
    for attempt in range(3):
        try:
            if not destination.exists():
                response = requests.get(cutout_url, timeout=(20, 120))
                response.raise_for_status()
                if not response.content.startswith(b"SIMPLE"):
                    raise ValueError("IRSA did not return a FITS image")
                temporary = destination.with_suffix(".partial")
                temporary.write_bytes(response.content)
                with fits.open(temporary) as hdul:
                    if hdul["IMAGE"].data.ndim != 2:
                        raise ValueError("Invalid IMAGE extension")
                temporary.replace(destination)
            content = destination.read_bytes()
            with fits.open(destination) as hdul:
                shape = list(hdul["IMAGE"].data.shape)
            return {
                **row,
                "path": str(destination.relative_to(ROOT)).replace("\\", "/"),
                "cutout_url": cutout_url,
                "bytes": len(content),
                "sha256": sha256(content).hexdigest(),
                "shape": shape,
                "status": "downloaded",
            }
        except (requests.RequestException, OSError, ValueError) as exc:
            if attempt == 2:
                return {**row, "cutout_url": cutout_url, "status": "error", "error": str(exc)}
            time.sleep(1 + attempt)
    raise AssertionError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--obs-id", action="append", default=[])
    parser.add_argument("--target-centered", action="store_true")
    parser.add_argument("--demo", action="store_true", help="Download the six target-centered study cutouts")
    args = parser.parse_args()
    if args.demo:
        args.target_centered = True
        args.obs_id = ["2025W19_1B_0138_1", "2026W19_2A_0651_1", "2025W19_1B_0116_1",
                       "2026W20_1A_0033_1", "2025W46_1A_0090_3", "2026W17_1B_0634_1"]
    RAW.mkdir(parents=True, exist_ok=True)
    metadata = RAW / "metadata.xml"
    if not metadata.exists():
        response = requests.get(QUERY, timeout=(20, 90))
        response.raise_for_status()
        metadata.write_bytes(response.content)
    table = Table.read(io.BytesIO(metadata.read_bytes()), format="votable", use_names_over_ids=True)
    selected = []
    for row in table:
        if str(row["energy_bandpassname"]) != "SPHEREx-D6":
            continue
        selected.append({
            "obs_id": str(row["obs_id"]),
            "access_url": str(row["access_url"]),
            "mjd": float(row["t_min"]),
            "detector": 6,
            "collection": "spherex_qr2",
        })
    if args.obs_id:
        selected = [row for row in selected if row["obs_id"] in args.obs_id]
    if args.target_centered:
        for row in selected:
            row.update({"cache_subdir": "target-centered", "cutout_center_ra": 133.76037473328523,
                        "cutout_center_dec": -7.242149767967145})
    selected.sort(key=lambda row: row["mjd"])
    if args.limit:
        selected = selected[:args.limit]
    if not selected:
        raise SystemExit("No matching D6 observations for this selection")
    print(f"Selected {len(selected)} D6 observations; cutout width 0.12 deg", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(download, row) for row in selected]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{len(results)}/{len(selected)} {result['obs_id']} {result['status']}", flush=True)
    results.sort(key=lambda row: row["mjd"])
    manifest = {
        "query_url": QUERY,
        "center_ra_deg": RA,
        "center_dec_deg": DEC,
        "width_deg": 0.12,
        "collection": "spherex_qr2",
        "records": results,
    }
    output = RAW / "target-centered" if args.target_centered else RAW
    manifest["center_ra_deg"] = selected[0].get("cutout_center_ra", RA) if selected else RA
    manifest["center_dec_deg"] = selected[0].get("cutout_center_dec", DEC) if selected else DEC
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if not any(row["status"] == "downloaded" for row in results):
        raise SystemExit("No real FITS cutouts downloaded; see manifest errors")


if __name__ == "__main__":
    main()
