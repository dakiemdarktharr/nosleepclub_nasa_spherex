# WISE 0855: QR3, CatWISE, and ePSF — Validation 0.5.0

Query date: 30 October 2026. Result: **the broad-spectrum configuration improved, but did not meet the gate for replacing the default method**. Keep Gaia 0.3.0 products and the conditional measurement 3.29″ ± 0.52″; do not turn this experiment into a motion confirmation.

## QR3/QR2: coverage comparison only; no same-exposure image pair

[IRSA Data Access](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/) provides QR2 and QR3 through SIA2, TAP, and cutouts. The SIA query `COLLECTION=spherex_qr3` within a 0.05° cone around RA 133.76037473328523°, Dec −7.242149767967145° returned **0 rows**. TAP on `spherex.artifact`/`spherex.plane`, with a footprint containing the exact coordinate and a QR3 URI, also returned **0 rows**. In this query snapshot, there is no D6 QR3 image or pair with the same observation ID for measuring QR2/QR3 differences at this point.

This is a coverage limit for the queried coordinate and time; it does not mean QR3 has not been released or does not exist across the sky. Do not infer that QR3 is better/worse from empty results. Do not fabricate QR3 images. The experiment below continues to use the same **20 QR2 exposures** from the prior version: 10 images/epoch for broad spectrum and 2 images/epoch for narrow spectrum. The configurations share data and are not independent detections.

URLs, ADQL, row counts, and SHA-256 values for both responses are stored in [protocol.json](../web/data/release/protocol.json). Raw FITS/full responses are in a Git-ignored cache; scripts can retrieve them again for checking.

## Infrared catalog with position corrections

CatWISE2020 query within 0.30°, W2<17, S/N≥5: **5,078 sources**. Apply the locked criteria: W2≤16, S/N≥10, reduced χ² W2≤2, artifact `00`, motion ≤0.3″/year. Sources without a Gaia match also require predicted 2026 position uncertainty ≤1″, with a diagnostic floor of 0.1″. Result: **1,783 sources**, including **508** with a quality-passing Gaia match within 2″ at catalog epoch; the remaining 1,275 use CatWISE.

The [official CatWISE definitions](https://irsa.ipac.caltech.edu/data/WISE/CatWISE/gator_docs/catwise_colDescriptions.html) describe tile-dependent systematic offsets; the [correction table](https://irsa.ipac.caltech.edu/data/WISE/CatWISE/gator_docs/CatWISE2020_Table1_20201012.tbl) specifies **adding** the offset to catalog values. Tile was retrieved from the first eight characters of `source_id`, position/proper motion were corrected, and `ra_pm/dec_pm` at MJD 57170 was used with proper motion in arcsec/year and a cos(Dec) factor when converting angular RA. Units were verified from TAP_SCHEMA and separate tests.

Gaia-matched sources use the prior implementation's proper-motion/parallax/covariance propagation; CatWISE-only sources use linear motion, without parallax. Catalog matching remains nearest-neighbor with a quality gate, not probabilistic association. Optical/IR photocenters may differ. Catalog position errors were not propagated into centroid-fit covariance. Do not use W2 brightness to constrain SPHEREx flux; each image has free flux. An infrared catalog may also omit faint sources or extended galaxies.

## Three models and ePSF check

1. `single_nearest`: target + plane background, nearest-zone ePSF baseline.
2. `ir_nearest`: add IR sources within 11 sky-grid pixels of the fit region, using nearest-zone ePSFs.
3. `ir_bilinear`: same catalog/model, bilinear interpolation of four ePSF zones, normalizing each zone before blending.

The [IRSA ePSF notebook](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/) recommends updated ePSFs and permits using this calibration for older QR2 images. The demo already used the D6 `cal-epsf-v1-2026-191` file from a prior milestone. **This is not the first replacement of an old PSF with an ePSF.** Four-zone interpolation is a separate experiment and is not claimed as an IRSA-validated method. Numerical tests check normalization, blend values, and continuity; they do not prove that it is a more physically accurate ePSF everywhere.

All three models use the same native pixels, bad-pixel flags, noise map, fit window, and multi-start solver. SVD eliminates background-source amplitudes and the linear plane; target centroid is free for each epoch and is not constrained to the Luhman vector. Frame translation retains Gaia 0.3.0 alignment; **reference stars were not refit using the interpolated ePSF**, so this is not a fully consistent astrometric calibration for the new models.

## Locked before testing 30 regions

Git checkpoint **`581de3342788563226368e567e86c413f29e0d0b`** was created before target fits and injections. Protocol SHA-256: **`79803094b4aeee039e589f8b3ceb3af5fcfbcc61bd929c89cc2ed26fbf51fac1`**. The protocol locks code for six modules, data, calibration, catalog, solver, gates, and 30 positions. Hashes are checked again before running. Do not change code/rules after locking.

Choose positions only by geometry and valid masks: new centers at least 20 pixels apart, at least 20 pixels from old positions/target, and at least 100 valid native pixels in each stamp across all exposures. These are **30 small regions within one field**, not 30 independent sky fields. Old trials cannot be relabeled as new holdouts.

30 regions × two brightnesses (0.5×/1×) × two truth vectors (stationary/[0.6, 0.05] pixels) × two injected ePSF families (nearest/interpolated) × three models × two spectral configurations = **1,440 recoveries**, corresponding to 2,880 centroid fits across epochs. Add 128 noise-bootstrap draws per epoch/model/configuration for the real target. The two injected ePSF families check one type of mismatch; they are not independent physical PSFs or a complete coverage simulation. No source shot noise is added; trials/configurations share background/exposure.

The pre-locked gate requires paired RMSE to decrease and failures/boundary hits not to increase for both brightnesses, both injected ePSFs, and both spectral configurations. Do not select the model based on proximity to an external motion prediction. The 30-region set has now been opened and is not an unseen set for the next experiment.

A parallel broad/strict run failed due to memory allocation after the seventh region. The entire broad run was repeated **sequentially with the same code/protocol**, without dropping regions or changing conditions. Both final result files contain all 720 records; results were not selected from the interrupted run.

## Results: local improvement, stable improvement not established

The table uses nearest-ePSF injected sources and the new `ir_bilinear` model. RMS units are arcseconds. Paired column includes only trials where both methods were valid; the all-new-fits column retains fits newly rescued from old failure/boundary conditions.

| Spectrum / brightness | Old → new RMS on common pairs | Common pairs | Valid fits old → new | RMS all new fits | Within 68% noise ellipse |
|---|---:|---:|---:|---:|---:|
| Broad / 0.5× | 3.133 → 1.980 | 50/60 | 50/60 → 60/60 | 2.413 | 28/60 |
| Broad / 1× | 0.622 → 0.607 | 52/60 | 52/60 → 60/60 | 0.616 | 41/60 |
| Narrow / 0.5× | 3.976 → 3.529 | 49/60 | 50/60 → 59/60 | 4.291 | 28/60 |
| Narrow / 1× | 1.184 → 1.202 | 52/60 | 52/60 → 60/60 | 2.126 | 38/60 |

For broad/0.5×, IR+interpolation reduces paired positional RMSE by **36.8%**, but a post hoc 2,000-draw bootstrap **by spatial region**, using only common-valid pairs, gives a diagnostic 95% interval of **[−31.4%, +64.2%]**. Broad/1× improves by 2.49%, interval **[−3.13%, +7.30%]**. Both intervals include no improvement; do not treat them as confirmatory tests.

With interpolated-ePSF injection, broad paired RMSE is 3.144→1.981″ at 0.5× and 0.624→0.600″ at 1×; narrow/1× remains worse. The IR+nearest-ePSF model also fails the narrow/1× gate. **No model passes all gates.**

Coverage for faint sources is only about 45–47% for nominal 68% ellipses, evidence that noise-only covariance does not describe all errors well. Region bootstrap does not remove exposure correlation or field-level shared bias. Do not report completeness, false-positive rate, Gaussian confidence, or a calibrated total systematic-error value.

Real target with broad spectrum: IR+interpolation gives vector **east −3.187″, north +0.224″**, length **3.195″**, projected noise σ **0.742″**. This is a conditional experimental result; do not compare this noise σ directly with Gaia version's total 0.52″. It does not confirm motion, separate proper motion/parallax, or resolve the difference with the external prediction.

## Products and reproduction

- [Locked protocol](../web/data/release/protocol.json), [broad](../web/data/release/broad.json), [strict](../web/data/release/strict.json).
- [Paired bootstrap and full groups](../web/data/release/summary.json); [small UI payload](../web/data/release/overview.json).
- UI has spectral/source-family filters, failed-fit counts, RMS across all new fits, a map of the 30 test centers, and JSON download. Keep real sources separate from Canva illustrations.

```powershell
python -m scripts.prepare_release_data
# Use only when creating the protocol for the first time, before any experiment:
python -m scripts.release_analysis --lock
# For a protocol already in the repository, the script checks hashes and reuses it:
python -m scripts.release_analysis --configuration broad
python -m scripts.release_analysis --configuration strict
python -m scripts.summarize_release
python -m unittest discover -s tests -v
```

Run broad and strict sequentially on low-memory machines. Gaia/QR2 caches from prior milestones are required. `--lock` refuses to overwrite an existing protocol. A new model requires a new protocol, a documented change, and an unseen validation set; do not edit locked results to make them look better.

## Next milestone

Prioritize **covariance calibration and a consistent scene model**: refit reference stars using the same ePSF, check residuals by position/color/source density, and model neighbor-position/background uncertainty before increasing confidence. Use opened regions for development; do not reuse them as new holdouts.

Lock the configuration before a new multi-field set, add PSF perturbations outside the fitting family, and add source noise using verified calibration/units. Report bias, paired RMSE, fit failures, and coverage by brightness; require stable improvement, not only one favorable point estimate. When QR3 covers the same exposure, compare that same image before combining release versions. A third epoch/independent data is a later step for separating proper motion and parallax.
