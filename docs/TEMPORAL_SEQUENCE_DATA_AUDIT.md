# Temporal Explorer data and sequence audit

Snapshot and direct archive checks: **2026-11-14**. The challenge's required task is to enter a sky coordinate and inspect SPHEREx images of the same patch across observation times. Its 102 spectral bands are wavelengths, not 102 time steps. The five target names are Barnard’s Star, Epsilon Indi B, WISE 0855, RW Aurigae and R Draconis; the challenge separately gives WISE 0855 at `133.79512917°, -7.24514722°`. Target coordinates in the app are field-search centers and are not measured source positions. See [challenge](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details), [repo target definitions](../web/data/challenge-targets.json), and [dataset catalog](DATASET_CATALOG.md).

## Archive query

Sequential, public SIA2 VOTable requests were made directly to `https://irsa.ipac.caltech.edu/SIA`, not through the app API. Parameters: collection `spherex_dr1` or `spherex_qr3`, `POS=CIRCLE` at each repository target center (radius 0.03°, except Epsilon Indi B 0.06°), `BAND=4.42e-6 5.0e-6` meters, `MAXREC=300`, `RESPONSEFORMAT=VOTABLE`. Rows were then filtered locally to detector D6 and deduplicated by observation ID and MJD rounded to 8 decimals. All responses had `QUERY_STATUS=OK`; none reached `MAXREC`. WISE 0855 was queried both at the repo search center and the official challenge coordinate. The bounds are cone-overlap metadata results; they do **not** establish valid pixels at the target, equal spectral response, source detection or usable photometry.

| Search center | DR1 D6 unique observations; MJD range | QR3 D6 unique observations; MJD range |
| --- | --- | --- |
| WISE 0855 repo `(133.76012139, -7.24212794)` | 45; `60800.700028–61171.096350` | 0 |
| WISE 0855 challenge `(133.79512917, -7.24514722)` | 45; `60800.700028–61171.096350` | 0 |
| Barnard `(269.44626689, 4.76822222)` | 41; `60902.864715–61165.082972` | 21; `61268.629319–61305.218876` |
| Epsilon Indi B `(331.04583333, -56.78333333)` | 63; `60794.063320–61164.116950` | 36; `61305.226906–61311.336624` |
| RW Aur `(76.95652603, 30.40143817)` | 38; `60929.677476–61101.563363` | 18; `61296.297591–61299.895897` |
| R Draconis `(248.16761083, 66.75497942)` | 70; `60811.955829–61173.247187` | 21; `61176.363744–61203.860905` |

SHA-256 below is for the raw VOTable response, not the FITS images. The same zero-row QR3 response was returned for both WISE centers.

| Query | SHA-256 |
| --- | --- |
| DR1 WISE repo center | `399fadd91e4b3e10e003bda9197c0ad3fbd69231ddc27ba5a54c01d4b758d027` |
| DR1 WISE challenge center | `24cab652f2e878bda7ec01d4823d7f95ceae74058c7de5f9bb97b4c2d74770a5` |
| DR1 Barnard | `7605cbb06ccde355ee8caa4e823f21f7b1d1802498f843b478f2eb0c084d8c60` |
| DR1 Epsilon Indi B | `aef6cac2307925d26d5e9ff50efdaa3ec14714ff005cfc1d3081241fa62e5485` |
| DR1 RW Aur | `b72ff43b23450cc9ca7602a708fefe26e0ccea1d27d7b73b16d7ea209d122b60` |
| DR1 R Draconis | `2e2ae47f765f8762f9990040f9add8608022cb9a6efddd0717add5b0cdab5cc5` |
| QR3 WISE (both centers) | `fa538a0a6daf723452a8645c90efb86c1d6ddc68903b280bed9fb13ca1cdd3bd` |
| QR3 Barnard | `6a635cffc3ecb891439f7a4f2ddb4e4ffb17f4276d27b1c85d1154fc18d1c191` |
| QR3 Epsilon Indi B | `0020a73a4e0d5ba1e3897948f82528e95057b38c689f0d0cef743955d370007b` |
| QR3 RW Aur | `790ac99f93ca373a1fd6a48bea829fbe97e9a24459c942d41759a25dc31f66a8` |
| QR3 R Draconis | `93ed8ec01eddd934b3996b4a942d4937c6405fe323ad3bd7bfdeffba64b65999` |

IRSA's current release guide identifies DR1 as Surveys 1–2 and QR3 as Surveys 3–4; its SIA2 collections are `spherex_dr1` and `spherex_qr3`. Spectral Images are per-exposure FITS products with calibrated image values in MJy/sr, masks/variance, WCS and WCS-WAVE. WCS-WAVE is a visualization aid; calibrated CWAVE/CBAND products are needed for science-grade spectral interpretation. See [release guide](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases/), [data access](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/) and [data products](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/).

## Tracked data inventory and image evidence

`git ls-files` counted **794 tracked files (229,459,479 bytes)** at this snapshot. The largest data-bearing groups are 218 JSON files (101,174,540 bytes), seven `.gz` files (107,503,059 bytes), seven FITS files (1,952,640 bytes), nine NPZ files (1,483,503 bytes), and static PNG/JPEG/WebP assets. The seven tracked FITS and nine NPZ are comparison/coadd products under `web/data/`, not the complete public archive. The gzip files are compressed experiment/evidence records, not SPHEREx images. JSON includes manifests, metadata, measurements, controls and audit records; role and provenance are recorded per product in [the project manifest](../web/data/manifest.json), [dataset catalog](DATASET_CATALOG.md), and the linked audit/receipt files. A repository file count is not an archive inventory, and many experiment products are not needed by the public Explorer.

The five `web/assets/mission/full-fields/*.webp` previews are single historical QR2 D6 exposures, downsampled from 2040² to 510² and independently stretched. They provide field context; they are not a time series and their brightness cannot be compared across previews. By contrast, the [saved Epsilon Indi B sequence](../web/assets/mission/epsilon-sequence/provenance.json) contains three real DR1 D6 FITS cutouts rendered on a shared grid and display scale. Its receipt records observation IDs `2025W18_1B_0081_3`, `2025W18_2B_0011_3`, `2025W19_1B_0344_3`, UTC times 2025-04-29, 2025-05-01 and 2025-05-07, per-cutout and PNG hashes, mask counts, and 99.755% common center-bandwidth overlap. That overlap is a display check, not calibrated photometry or a claim that Epsilon Indi B was resolved.

## Product gap and change

| Before | Now |
| --- | --- |
| A/B blink played two frames; the optional timeline used only already-opened images and required at least three. A result list did not make a selected 2- or 10-frame sequence. | A separate count selector prepares 2, 3, 5 or 10 images from the current single-release query. It samples the candidate epochs evenly across time, reports how many results were not loaded, downloads serially and plays the exact selected images in FITS MJD order. A/B blink remains available. |
| The user had to open images one by one; an IRSA 429 could stop a long serial load. | Each candidate must have the selected detector, a distinct MJD and observation ID, and a FITS URL. Failed frames can be retried without reloading successful frames. A 429 with a valid `Retry-After` waits once and can be canceled by changing the query. |
| Loaded images could be shown without a complete requested sequence. | Playback requires UTC FITS MJD, a valid query-center pixel, one release and detector, the same mask policy, and shared contrast/grid. When every selected FITS has center WCS-WAVE, their ranges must pass the overlap check. If none has center WCS-WAVE, playback is allowed as a nominal same-detector visual sequence with a warning that detailed spectral matching and photometry are unverified. A mixture of known and missing WCS-WAVE, or any invalid center pixel, blocks playback and the app explains why. Missing or incompatible selected frames are not silently dropped. |

## Live cutout check

The DR1 R Draconis D6 query returned 70 cone-overlap metadata rows. Five evenly sampled cutouts (`2025W20_2D_0243_1`, `2025W24_2D_0033_1`, `2026W01_1A_0534_4`, `2026W17_1B_0517_3`, `2026W20_1A_0795_3`) were fetched through the local app API successfully (HTTP 200); each had UTC MJD, one release/detector, common contrast and more than 1,200 valid pixels across the 37×37 cutout. However, all five returned `X-Frame-Center-Pixel-Status: missing` and no center WCS-WAVE. The query-center pixel is therefore not observed in these selected exposures, so the app correctly blocks this sequence even though other pixels in the cutouts are valid. This is a concrete example of why metadata count and total valid-pixel count alone cannot establish coverage of the requested point. It does not rule out usable nearby pixels or other dates/detectors.

Detector and epoch selection use bounded metadata only; cutouts are requested sequentially through `/api/frame`. A shared 0.02–0.12° TAN grid, north-up/east-left projection, mask and fixed MJy/sr contrast are reused. Playback is an inspection aid. Pixel changes alone do not establish motion, variability, source identity, astrometry or calibrated flux.

## Validation boundary

Metadata query completeness is bounded by the 300-row cap and SIA snapshot. Detector filtering occurs locally after the SIA response; users should narrow the date interval when the response is marked truncated. Cone overlap is not pixel-center validity. The three saved Epsilon Indi B frames are a reproducible visual example, not a five-target science validation. The public flow does not infer a moving-source track or variable-star light curve; those require independent astrometry/photometry and controls.
