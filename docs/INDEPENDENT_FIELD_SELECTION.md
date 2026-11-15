# Candidate Field Selection — Geometry Only

[selection.json](../web/data/independent-fields/selection.json) is a list of candidate fields, **not** a locked analysis/calibration protocol, a measured validation set, or accuracy evidence. Do not query new metadata, read FITS pixels, measure sources, or use outcomes, spectra, or fits to select fields. Previously opened fields and products remain development data.

## Rules and input evidence

The base grid uses RA `[12,48,84,120,156,192,228,264,300,336]` degrees × Dec `[-45,0,+45]` degrees. Before measurement, test integer **global RA offsets** from 0 through 35 degrees in ascending order; wrap RA modulo 360. Choose the first offset for which every new center is at least 6° from every cached center and each pair of new centers is **more than** 6° apart. Distances are great-circle distances on the sphere; 1e-12 degrees is treated as rounding error equal to the threshold. Do not alter fields individually or use measurement outcomes. If no offset is valid, the command fails without writing a selection.

Exclusion sources are all JSON files with `manifest` in the filename under `data/raw` that contain `field.ra/dec`, an original `center_ra_deg/center_dec_deg` pair, or `records[].cutout_center_ra/dec`. For each oriented manifest, record the path, SHA-256, coordinates, and original JSON pointer; skip job manifests without coordinates. A center missing one coordinate or containing invalid values causes failure. Do not open FITS files or catalogs. This check depends on the completeness of local manifests; do not infer that every dataset ever seen in another source is listed.

In the local snapshot, 16 manifests have known centers. Offsets **0–9°** fail; the JSON contains the nearest conflict and number of conflicts for each offset. Offsets 0–2 conflict near field `v150p45`; offsets 3–9 conflict near the Barnard field. The first valid offset is **+10°**: the nearest old center is **6.531843°** away, and the nearest pair of new fields is **25.242833°** apart. This checks geometry only and does not ensure exposure/pixel independence.

## Preassigned roles

After choosing the offset, field IDs use the integer-degree format `r{RA:03d}{p|m}{|Dec|:02d}`. Within each Dec ring, calculate SHA-256 of `nosleepclub-independent-fields-20261030-v1|field_id` and sort by digest ascending: the first four are calibration, the next four validation, and the last two final holdout. Total: **12/12/6**; order and digest for each field are stored in JSON.

| Dec | Calibration | Validation | Final holdout |
|---:|---|---|---|
| −45° | r238m45, r166m45, r130m45, r022m45 | r202m45, r094m45, r274m45, r346m45 | r310m45, r058m45 |
| 0° | r238p00, r274p00, r346p00, r310p00 | r058p00, r094p00, r130p00, r022p00 | r166p00, r202p00 |
| +45° | r130p45, r058p45, r274p45, r094p45 | r022p45, r202p45, r166p45, r346p45 | r238p45, r310p45 |

The list is a stratified geometric grid, not a probability sample representative of the full sky. `final_holdout` is an intended role; publishing coordinates here does not permit opening results early or using them to tune the model.

## Reproduction and next steps

```powershell
.venv/Scripts/python.exe -m scripts.select_independent_fields --select
.venv/Scripts/python.exe -m unittest tests.test_independent_field_selection -v
# Only after committing the source and selection, check the guard before a future metadata workflow:
.venv/Scripts/python.exe -m scripts.select_independent_fields --verify-committed
```

`--select` does not overwrite a different selection; if the current version is byte-identical, it leaves it unchanged. `--verify-committed` checks source and selection SHA values against Git HEAD, then rereads local manifests to detect new/changed sources and recomputes the selection rules. The module has no query capability; a future metadata workflow must call this guard before querying and must not treat the guard as analysis approval.

Before measuring any new field, write and commit a **separate analysis protocol**: evaluator, absolute-error budget, gates and denominators, sample size/power, PSF/SED/gain truth, source noise, and support routing. Once metadata is authorized, compare exact observation IDs, footprints/pixels, times, and sources across splits; a 6° center separation does not prove exposure or systematic-error independence. Separate calibration from validation and preserve final holdout for one assessment after choices are fixed. If there is overlap, insufficient support, or inadequate power, stop and record it; do not relax criteria after viewing results.
