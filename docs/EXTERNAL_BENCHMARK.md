# Validation on a New Dataset — 0.6.0

Run date: 30 October 2026. **The pipeline is not stable enough to publish one general “accuracy” rate.** Gaia-star measurements are good in one field, but outliers, faint-source bias, and a field with too few alignment stars remain. Keep the WISE 0855 measurement and all earlier science products unchanged.

## Data retrieved and actually used

Queried the [official SPHEREx SIA/cutout service at IRSA](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/) using J2000 field coordinates from SIMBAD. These coordinates identify image regions only; checked-star positions were propagated from Gaia DR3 to observation dates. J2000 coordinates were not used as truth for 2026.

| New field | D6 QR2 cutouts downloaded | Gaia G<18.5 | Images selected | Observation seasons in cache |
|---|---:|---:|---:|---|
| [Barnard's Star](https://simbad.cds.unistra.fr/simbad/sim-basic?Ident=Barnard%27s+star) | 42 | 3,952 | 20 | 15–27 Aug 2025; 19 Mar–5 May 2026 |
| [RW Aur](https://simbad.cds.unistra.fr/simbad/sim-id?Ident=RW+Aur) | 36 | 2,413 | 20 | 11–20 Sep 2025; 20 Feb–2 Mar 2026 |
| [R Draconis](https://simbad.cds.unistra.fr/simbad/sim-id?Ident=%40376084&Name=V%2A+R+Dra&submit=submit) | 51 | 371 | 16 | 16 May–12 Jun 2025; 26 Dec 2025–13 Jan 2026 |

Total: **129 real FITS/cutouts**, 6,736 Gaia rows, and 56 exposures selected by wavelength. Measurement ran on 40 exposures from two fields; 16 R Dra exposures stopped at the alignment gate. Date ranges in the table describe the full cache; dates of images actually selected are in each JSON result. The three fields are more than 10° apart, differ from WISE 0855, and use different exposures.

SIA also returned 19 D6 QR3 images near Barnard and 19 near RW Aur; R Dra returned zero. **QR3 was not downloaded or run**: these are different epochs/exposures, not same-exposure pairs for a QR2/QR3 calibration comparison. A possible additional dataset is [unTimely/time-resolved unWISE](https://arxiv.org/abs/2209.14327), W1/W2 with a longer baseline; it was not run in this report and needs separate PSF, mask, noise, and bandpass adapters.

## Method locked before viewing results

Checkpoint **`8aa2536`**, protocol SHA-256 **`58d1860a985ef0475309d710621039d75078ce95cea1c2b4a0665363411250f3`**. [Protocol](../web/data/benchmark/protocol.json) contains code hashes, complete input manifest, URL/FITS hashes, catalog/query/calibration hashes, image pairs, reference stars, and injected-source positions. Solver, thresholds, and splits were not changed after results were opened.

- Use the deployed ePSF fitter on native pixels and the version's Gaia translation alignment. The adapter changes field coordinates and epoch labels; previously locked science modules remain unchanged.
- Retain detector D6, 4.55–4.94 µm, wavelength mismatch ≤0.20 or ≤0.50 bandwidth; at most 10 pairs per configuration. Select the first two QR2 seasons separated by a gap >60 days; do not select seasons by fit outcome.
- Select sources by catalog, geometry, and exploratory images; cap at 32 and split by SHA-256 source ID **before fitting**: every third source is held out from alignment. Apply the existing quality gate to alignment training stars; do not use held-out stars to tune frame alignment or covariance.
- Barnard: 21 training sources selected, 9 eligible; 11 held out. RW Aur: 21 training, 14 eligible; 11 held out. R Dra: 15 training, only 3 eligible; 8 held out but not measured because a frame requires at least 4 stars.
- For each runnable configuration: four pre-locked positions × per-frame design S/N 2/4 × stationary/moving by `[0.6, 0.05]` pixels = 16 recoveries. Fit center is free within ±2.5 pixels. Do not choose positions based on post-fit error.

Here, `valid` means solver convergence, no boundary hit, and positive total amplitude at both epochs. It **does not mean the model describes the image well**; all χ² values and outliers remain. Do not add a post hoc quality cut to reduce RMS.

## Held-out real-star results

These are **two-epoch displacement vectors** relative to Gaia, not absolute positional errors. Rows below use the broad spectral configuration.

| Field | Measured / attempted | RMS | Median | P90 | Result |
|---|---:|---:|---:|---:|---|
| Barnard | 11/11 | **1.921″** | 0.336″ | 0.447″ | Retain one 6.309″ outlier |
| RW Aur | 11/11 | **0.182″** | 0.105″ | 0.162″ | Largest error is 0.512″ |
| R Dra | — | — | — | — | Only 3 alignment stars eligible; at least 4 required |

Barnard outlier Gaia ID `4472836876874287744`, with reduced χ² 2.37/5.79 across the two epochs. Small median/P90 but large RMS shows the influence of the error tail; this source remains in the report. RW Aur rows are **Gaia stars in the field around RW Aur**, not verified variability of RW Aur itself.

Barnard's narrow and broad configurations select the **same 10 pairs** and produce identical results. RW Aur and R Dra do not have enough pairs passing the narrow spectral threshold; the gate was not relaxed. The two Barnard configurations are not independent validation sets.

## Synthetic sources on real image backgrounds

| Field, broad spectrum | Valid fits / attempted | RMS of valid fits | P90 | Within 1 pixel / attempted | Within 68% ellipse / attempted |
|---|---:|---:|---:|---:|---:|
| Barnard | 15/16 | **2.103″** | 3.896″ | 15/16 | 7/16 |
| RW Aur | 13/16 | **6.009″** | 12.142″ | 11/16 | 8/16 |

One pixel spans 6.15″. “Within 1 pixel” is a coarse positional-recovery threshold, not a correct-detection rate. RMS includes only valid fits; failures and every denominator remain. Do not use bright-star RMS to represent faint-source accuracy.

| Field / design S/N per frame | Stationary RMS | Moving RMS | Valid fits / 8 |
|---|---:|---:|---:|
| Barnard / 2 | 1.594″ | 3.022″ | 7/8 |
| Barnard / 4 | 0.700″ | 2.249″ | 8/8 |
| RW Aur / 2 | 8.990″ | 10.448″ | 5/8 |
| RW Aur / 4 | 1.072″ | 1.010″ | 8/8 |

There are 48 synthetic-source trials across three runnable configurations, but only **32 unique cases** because Barnard narrow/broad results duplicate exactly. Likewise, there are 33 held-out fit trials but only 22 unique stars. Stamps in a field and trials on the same stamp are correlated. Do not derive statistical confidence intervals by treating all trials as independent.

## Large-motion control: Barnard's Star

Gaia DR3 `4472832130942575872`; propagated with Astropy using radial velocity −110.11 km/s from SIMBAD, including perspective acceleration and first-order observed parallax. This is an external prediction, not a constraint on the image fit.

- Measured vector (east; north): **[+0.394; +3.138]″**.
- Predicted vector at the two fit effective MJDs: **[+0.575; +5.760]″**.
- Vector discrepancy **2.628″**; reduced χ² **334.30 / 202.57**.

The solver converged, but the model fits the image poorly; small formal covariance does not describe this bias. Do not call this a successful verification of Barnard's motion. Residuals, pixel flags, source shape, spectrum, and within-epoch position variation need checking; the cause has not been identified as saturation or any other specific factor.

## Limits of this measurement

This is a benchmark of **local fitting at known positions**; it does not measure blind-search precision, recall, completeness, or false-positive rate. Web highlighting/blinking assists viewers; no vision model has been trained. Do not publish “the website is X% accurate.”

Diagnostic covariance uses formal centroid covariance plus mean translation covariance under an independent-frame assumption; Gaia differential covariance is added for real stars. It **does not reproduce the full 0.3.0 error budget**, does not run 128/256 bootstrap draws for each new source/calibration, and does not add held-out scatter to the ellipse before evaluating coverage on the same held-out set. Missing terms include frame correlations, spatial systematics, ePSF/spectrum/background-source errors; Barnard's predicted covariance is approximate and omits radial-velocity uncertainty.

Synthetic sources use the **same nearest ePSF** as the fitter, without added shot noise or independent PSF perturbations. S/N 2/4 are design values from the noise map and linear model, not post-fit measured S/N, and do not simulate WISE 0855's spectrum. These conditions may make the test optimistic; bias on image backgrounds is still visible. Two measured fields are too small to represent the sky; R Dra's failure to run is a relevant availability failure and is not ignored.

## View and reproduce

- [Web: new benchmark](https://nosleepclub-nasa-spherex.vercel.app/#external-benchmark).
- [Summary JSON](../web/data/benchmark/summary.json), [Barnard](../web/data/benchmark/barnard.json), [RW Aur](../web/data/benchmark/rw-aur.json), [R Dra](../web/data/benchmark/r-dra.json).
- Raw FITS and catalog responses are in Git-ignored `data/raw/benchmark/`; versioned input manifest/hashes are in the protocol.

The D6 calibration already downloaded by the earlier WISE 0855 workflow is required. Then:

```powershell
python -m scripts.prepare_benchmark_data --download
# --lock is for first-time use only, before evaluation; it does not overwrite an existing protocol.
python -m scripts.benchmark_accuracy
python -m unittest discover -s tests -v
```

The script checks code, calibration, Gaia, manifest, and FITS hashes before running. If upstream data change, restore the matching cache/hashes or create a new protocol version; do not overwrite the opened version. The initial download encountered a CDS timeout and IRSA HTTP 504; coordinates were checked on SIMBAD, IRSA was retried, and all 129 FITS files eventually downloaded successfully.

## Next steps

Prioritize **model-quality gates and outlier handling**: clearly show when the solver converges but χ² is high, reject measurements without enough alignment stars, and check residuals/blending before assigning confidence. Use the three opened fields for development; do not reuse them as new holdouts.

Then lock the model and revalidate on unseen fields with independent PSF perturbations. Criteria: enough alignment stars for each exposure; report every failure; reduce RMS/P90 on faint sources; check coverage with systematics simulated; and match the real-motion control to its prediction within a reasonable error budget. Do not increase confidence in WISE 0855 based on this benchmark.
