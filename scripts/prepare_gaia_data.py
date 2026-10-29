"""Cache wider cutouts of the same exposures and a reproducible Gaia DR3 cone."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import io
import json
from pathlib import Path

from astropy.table import Table
import requests

try:
    from . import fetch_wise0855 as fetch
except ImportError:
    import fetch_wise0855 as fetch

ROOT = Path(__file__).resolve().parents[1]
OUT = fetch.RAW / "gaia-wide"
WIDTH_DEG = .32
ENDPOINT = "https://irsa.ipac.caltech.edu/TAP/sync"
CORRELATIONS = ["ra_dec", "ra_parallax", "ra_pmra", "ra_pmdec", "dec_parallax",
                "dec_pmra", "dec_pmdec", "parallax_pmra", "parallax_pmdec", "pmra_pmdec"]
COLUMNS = ["source_id", "ref_epoch", "ra", "dec", "parallax", "pmra", "pmdec",
           "ra_error", "dec_error", "parallax_error", "pmra_error", "pmdec_error",
           *[name+"_corr" for name in CORRELATIONS], "phot_g_mean_mag", "bp_rp", "ruwe",
           "astrometric_params_solved", "visibility_periods_used", "duplicated_source",
           "ipd_frac_multi_peak", "non_single_star", "phot_variable_flag"]
QUERY = ("SELECT "+", ".join(COLUMNS)+" FROM gaia_dr3_source WHERE "
         "CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',133.76037473328523,-7.242149767967145,0.25))=1 "
         "AND phot_g_mean_mag < 18.5 ORDER BY source_id")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    previous = json.loads((ROOT/"web/data/motion/results.json").read_text(encoding="utf-8"))
    broad = next(c for c in previous["configurations"] if c["id"]=="broad")
    selected=[]
    for pair in broad["spectral_pairs"]:
        for epoch in ["before", "after"]:
            record=pair[epoch]
            selected.append({k:record[k] for k in ["obs_id", "access_url", "mjd", "detector", "collection", "epoch"]})
            selected[-1].update(cache_subdir="gaia-wide", cutout_width_deg=WIDTH_DEG,
                cutout_center_ra=133.76037473328523, cutout_center_dec=-7.242149767967145)
    records=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for future in as_completed([pool.submit(fetch.download, row) for row in selected]):
            r=future.result();records.append(r)
            print(f"{len(records)}/{len(selected)} {r['obs_id']} {r['status']}", flush=True)
    if any(r["status"]!="downloaded" for r in records):
        raise RuntimeError("Incomplete wide cutout download; rerun to resume cache")
    path=OUT/"gaia-dr3.xml"
    if not path.exists():
        response=requests.get(ENDPOINT, params={"REQUEST":"doQuery", "LANG":"ADQL", "FORMAT":"votable", "QUERY":QUERY}, timeout=(20,120))
        response.raise_for_status()
        table=Table.read(io.BytesIO(response.content), format="votable", use_names_over_ids=True)
        if not set(COLUMNS)<=set(table.colnames):raise RuntimeError(response.text[:1000])
        path.write_bytes(response.content)
    table=Table.read(path, format="votable", use_names_over_ids=True)
    manifest={"records":sorted(records,key=lambda r:r["mjd"]), "cutout_width_deg":WIDTH_DEG,
        "calibrations":previous["calibrations"], "prior_results_sha256":sha256((ROOT/"web/data/motion/results.json").read_bytes()).hexdigest(),
        "gaia":{"endpoint":ENDPOINT, "query":QUERY, "table":"gaia_dr3_source", "release":"Gaia DR3",
                "path":str(path.relative_to(ROOT)).replace("\\","/"), "sha256":sha256(path.read_bytes()).hexdigest(), "rows":len(table)}}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(f"Cached {len(records)} wide cutouts and {len(table)} Gaia DR3 rows", flush=True)


if __name__=="__main__":main()
