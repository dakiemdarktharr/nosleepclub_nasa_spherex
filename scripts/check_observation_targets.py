"""Read-only IRSA coverage/image checks for the five challenge field centers.

Snapshots are discovery evidence, not photometry, motion, completeness or
astrometric validation. Downloads are serial and bounded by API safety limits.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import time
from urllib.parse import urlencode

from web.api import observations, frame

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/explorer-check"
OUT = ROOT / "web/data/explorer-check"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", action="store_true")
    parser.add_argument("--targets", nargs="+")
    args = parser.parse_args()
    # Use the platform trust roots on Windows, without disabling TLS checks.
    import truststore
    truststore.inject_into_ssl()
    targets = json.loads((ROOT / "web/data/challenge-targets.json").read_text(encoding="utf-8"))["targets"]
    RAW.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    report = {"version": "0.10.0", "role": "live discovery smoke on known fields; not science validation",
              "created_at": datetime.now(timezone.utc).isoformat(), "source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
              "targets_sha256": sha256((ROOT / "web/data/challenge-targets.json").read_bytes()).hexdigest(), "targets": []}
    for target in targets:
        if args.targets and target["id"] not in args.targets:
            continue
        started = time.monotonic(); ident = target["id"]
        p = observations.parse_params(urlencode({"ra": target["ra_deg"], "dec": target["dec_deg"],
                "radius": .001, "release": "qr2", "detector": 6, "maxrec": 300,
                "band_min_um": 4.42, "band_max_um": 5.0}))
        row = {"target": target, "query": p, "images": []};report["targets"].append(row)
        try:
            url = observations.upstream_url(p); content = observations.fetch(url)
            (RAW / (ident + ".xml")).write_bytes(content)
            records, truncated, scanned = observations.parse_votable(content, p)
            records.sort(key=lambda r: r["t_min_mjd"] if r["t_min_mjd"] is not None else float("inf"))
            row.update(query_url=url, response_sha256=sha256(content).hexdigest(), observations=records,
                       retrieved_at=datetime.now(timezone.utc).isoformat(), truncated=truncated, scanned=scanned)
            if args.images and records:
                limits = None
                for side, observation in [("first", records[0]), ("last", records[-1])]:
                    item = {"side": side, "observation": observation};row["images"].append(item)
                    try:
                        params = {"url": observation["access_url"], "ra": target["ra_deg"], "dec": target["dec_deg"],
                                  "fov_deg": target["fov_deg"], "zodi": "subtract"}
                        if limits:params.update(low=limits[0], high=limits[1])
                        fp = frame.parse_params(urlencode(params)); cutout = frame.cutout_url(fp)
                        data = frame.fetch(cutout); (RAW / (ident + "-" + side + ".fits")).write_bytes(data)
                        png, meta = frame.render(data, fp); path = OUT / (ident + "-" + side + ".png");path.write_bytes(png)
                        limits = (meta["low"], meta["high"])
                        item.update(image=path.relative_to(ROOT / "web").as_posix(), png_sha256=sha256(png).hexdigest(),
                                    cutout_url=cutout, raw_sha256=sha256(data).hexdigest(), bytes=len(data), display=meta)
                    except (ValueError, frame.FrameError) as exc:
                        item["error"] = getattr(exc, "code", type(exc).__name__)
            row["elapsed_seconds"] = time.monotonic() - started
        except (ValueError, observations.UpstreamError) as exc:
            row["error"] = getattr(exc, "code", type(exc).__name__)
        (OUT / "coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(ident, "rows", len(row.get("observations", [])), "images", sum("image" in r for r in row["images"]), "error", row.get("error"), flush=True)
    print("REPORT", OUT / "coverage.json", flush=True)


if __name__ == "__main__":
    main()
