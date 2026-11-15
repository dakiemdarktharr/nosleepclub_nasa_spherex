# Image Background, ePSF, and Error Calibration — 0.8.0

This study addresses two separate questions: did the measured position vector become less biased, and does the error ellipse cover the actual error? Enlarging an ellipse does not make the position more accurate. The WISE 0855 measurement still uses version 0.3.0; motion is unconfirmed and no vision model has been trained.

## Splits and experiment lock

| Role | Fields | Purpose |
|---|---|---|
| Development | Barnard, RW Aur | Fields opened in earlier runs; inspect candidates and failure cases |
| Calibration | q030m10, q180p20, q300m30 | Fields opened in 0.7; learn an error floor and scale from synthetic sources |
| Validation | v060m30, v150p45, v330p10 | New coordinates (60°, −30°), (150°, +45°), (330°, +10°); fit only after coefficients were locked |

Downloaded **122 QR2 cutouts** across the three validation fields; selected **58 exposures** into 29 spectrally compatible pairs. Field centers were declared from geometry before measurements were viewed. Pair selection uses spectral WCS at the center, within 4.55–4.94 µm and at most 0.5 band widths apart; up to 10 pairs per field. Exposure IDs do not overlap across the three roles. A shared D6 calibration library still creates systematic dependence.

Within each field, Gaia stars were selected from catalog/images before fitting, up to 32 spread across quadrants. Sort IDs by SHA-256 and hold out every third star from alignment. Heldout stars are not used to learn covariance. Reuse exported 0.7 alignment offsets for previously opened fields; new fields use the same IR + median/MAD recipe. Both models receive the **same offsets, alignment covariance, and injected source pixels**.

Design checkpoint **`4e7a50c`**, SHA-256 of `design.json` **`1e5805754bd5afba8ed50cf7b7ddff4f1c18345fc34999de5c4d1f17e8889f7d`**, was committed before calibration. A second checkpoint locked the calibrator before validation fields were opened. FITS, catalog, spectral-WCS, ePSF, query-URL, and source-code-hash manifests are in [design.json](../web/data/covariance/design.json). The runner does not overwrite results.

## Position-model changes

[IRSA recommends using the new ePSF with QR2](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/). The project already used this library; 0.8 adds a width perturbation around the pinned ePSF. This is not a new ePSF supplied by NASA.

- Baseline: version 0.7 IR deblend + first-order plane background + two Huber iterations.
- Candidate: add `x²`, `xy`, and `y²` to per-exposure nuisance backgrounds. Source and neighbor amplitudes remain free under weighted SVD projection.
- Target ePSF is a mixture of the original and a Gaussian-blurred version with σ=0.25 native pixel. One shared η∈[0,1] is fit across exposures within each epoch. Do not shift the ePSF center to truth; neighbor shape/position remain fixed.
- Fit `(x,y,η)` jointly. Position covariance is the 2×2 block of the inverse full Hessian after marginalizing η; this remains an approximation at η boundaries.
- Retain 0.7 quality thresholds on original noise/residuals. Candidate disagreement is measured against **robust IR 0.7**; baseline 0.7 keeps its single-source-fit comparison. Because the disagreement references differ, gate counts do not reflect only the point-estimator change. Paired pre-gate RMS helps isolate position changes.
- Add `0.25·ddᵀ` to candidate covariance, where `d` is the 0.8−0.7 displacement-vector difference. This is a PSD model-sensitivity term by convention, not a probabilistic covariance inferred from two independent fits.

The [official IRSA spectrophotometry tool](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html) models image background and neighboring sources but fits flux at fixed positions. This runner fits its own centroid and does not report a measurement returned by the IRSA tool.

## Covariance calibration

The calibration set has 8 fixed background positions per field × per-frame S/N {2,4} × vector {stationary, [0.6; 0.05] pixel} × source shape {original ePSF, isotropic blur σ=0.15 pixel}: **192 attempts**. Both estimators receive the same injected images. No source shot noise is added; original noise/mask stay fixed. Retain attempts with too few pixels, nonconvergence, or gate rejection.

Only **candidate synthetic sources that pass the calibration gate** are used to learn two parameters:

1. Give equal total weight to each field, each background region with accepted samples within the field, and each scenario within that region. Set `F = PSD₊(Σw·(eeᵀ−Craw)) + (0.05″)²I`, where `e` is the [East, North] error vector and `Craw` includes fit noise, alignment, and model-sensitivity terms. `PSD₊` removes negative eigenvalues. Because this uses an uncentered moment, F also contains bias effects.
2. Compute `q=eᵀ(Craw+F)⁻¹e`. Set `s²=max(1, weighted_quantile68(q)/2.2788685664)`. Lock `Ccal=s²(Craw+F)` for all validation fields. Do not subtract centroid bias or shrink ellipses.

This is an **empirical error envelope**. The same calibration set learns F and s; there are only three fields and many synthetic sources share backgrounds. Do not interpret it as a posterior, detection probability, or guaranteed conformal coverage. [Oliveira et al., JMLR 2024](https://www.jmlr.org/papers/v25/23-1553.html) discuss the role of exchangeability assumptions; this experiment does not test the conditions required for a theoretical guarantee with dependent data.

## Prespecified validation

The validation set has 4 background positions per field × two S/N levels × two vectors × two source shapes: **96 attempts**. The second shape is anisotropic blur `(σy,σx)=(0.06;0.22)` pixel, different from the isotropic calibration blur family. This is a hypothetical shape stress test, not an independent physical ePSF measurement.

Locked criteria:

- Per field/SNR/shape: at least 4 numerically common fit pairs; RMS and P90 must not rise; neither valid-fit nor accepted-fit counts may fall. Real Gaia stars need at least 3 common pairs, non-increasing RMS, and no reduction in fit/accept counts.
- Newly gated synthetic sources: nominal 68% ellipse coverage in [55%,85%], bootstrap interval includes 68%, at least 24 fits and 6 background regions with accepted samples, across all three fields.
- Median calibrated/raw ellipse-area ratio ≤16. Each ellipse area is proportional to `√det(C)`; this is not a radius ratio.
- Continue only if both the position and covariance gates pass. Do not automatically replace the WISE 0855 result.

The hierarchical bootstrap resamples fields, then background regions, with 2,000 replicates and a fixed seed. It respects some within-region dependence, but three fields are too few for strong intervals or all-sky distribution-shift measurement. The 55–85% range and area cap are project development criteria, not NASA standards.

## Results and limitations

**The criteria for replacing the default were not met.** Synthetic-source RMS across 88 common pairs fell from 2.079→1.961″, but P90 rose from 2.222→2.372″ and RMS increased in two of three fields. The 59 pairs passing both gates had RMS 1.261→1.281″. The new model cannot be said to reduce bias consistently.

Checkpoint before validation: **`d7d92dc`**. Protocol SHA-256: **`a9f7a8d67b6119e016dac8ba503fbad51ab3f3b29802e8e3993fef4f8e5f1303`**. Code and parameters were unchanged after the new fields were opened.

| Field RA/Dec | Old → new synthetic RMS before gate | Candidate accepted / attempts | Raw → calibrated 68% coverage, accepted samples | Median area | New bias East; North |
|---|---:|---:|---:|---:|---:|
| 60° / −30° | 0.945 → 0.993″ (32 pairs) | 32/32 | 24/32 → 32/32 | ×3.58 | −0.409; −0.027″ |
| 150° / +45° | 1.368 → 1.418″ (24 pairs) | 21/32 | 9/21 → 18/21 | ×3.65 | −0.918; −0.692″ |
| 330° / +10° | 3.096 → 2.843″ (32 pairs) | 14/32 | 0/14 → 10/14 | ×3.62 | −0.122; 0.944″ |

Across candidate synthetic sources, **88/96** fits were valid and **67/96** passed the gate, across 9 background regions in three fields. 68% ellipse coverage rose from **33/67 (49.3%) to 60/67 (89.6%)**; 95% coverage rose from **55/67 to 65/67**. Median ellipse area increased **3.65×**. Coverage of 89.6% exceeds the locked 85% cap; the bootstrap interval **71.4–100%** also excludes 68%. The covariance gate **failed**. Undercoverage improved at v330 but v060 became over-conservative; a common floor is not stable across fields.

Learned F matrix in [East, North], in arcsec²:

```text
[[ 1.892692, -0.597693],
 [-0.597693,  0.886835]]
s² = 1
```

The calibration set had **146/192** accepted samples across **19** background regions. Its 68% coverage rose from **57/146 to 118/146** and median area increased ×3.26. The floor raised weighted coverage above target, so scale was bounded at 1 rather than reduced. This is fitting data, not independent evaluation.

| Heldout Gaia star field | Common fits / attempts | Old → new RMS | Candidate accepted / attempts | Median area |
|---|---:|---:|---:|---:|
| v060m30 | 10/11 | 0.943 → 0.909″ | 10/11 | ×8.58 |
| v150p45 | 5/11 | 0.862 → 0.658″ | 4/11 | ×62.74 |
| v330p10 | 10/11 | 0.304 → 0.312″ | 9/11 | ×31.20 |

All three per-field position gates failed across the full synthetic-source and Gaia groups. v060/v150 improved Gaia-star RMS; v330 rose slightly. The floor calibrated on low-S/N synthetic sources greatly expands ellipses for bright Gaia stars in some fields; do not use it as a validated covariance for bright stars.

Development-field Gaia RMS was 0.256→0.264″ in Barnard and 1.099→1.884″ in RW Aur. Development data had already indicated that extra parameters could destabilize centroids. This supports running ablations before selecting a point model; it is not a reason to alter the newly opened validation set.

**Attempt-ledger check:** the paired runner catches a shared exception for both models. A post-run audit independently refit baseline 0.7 for all **16** exception cases (8 synthetic and 8 Gaia) to check that valid baseline fits were not hidden. All 16 remained unfit due to insufficient valid pixels or an unidentifiable target. No baseline was restored; original data, fit parameters, and coverage were not changed. This is QA on opened data, not a new validation. [failure-audit.json](../web/data/covariance/failure-audit.json) contains input hashes and per-case results.

**All 73/73 offline tests passed**: centroid recovery with curved backgrounds/wide sources, non-shrinking PSD covariance, calibration/validation isolation, calibrator reconstruction from the correct set, complete attempt counts, metric/covariance/area comparison, and source/input hashes. These checks validate software/provenance; the scientific conclusion still fails its gate.

Remaining limits: fits start around known positions; similar broad spectra at the center do not imply identical spectral response for every source; neighbor position/shape, spatial background covariance, ePSF-library errors, and full offset/exposure correlations were not propagated. Bright Gaia stars lie outside the two synthetic-source S/N levels used for calibration; applying the same floor is an extrapolation stress test. Test calibration conditional on S/N and background before using it for a specific source.

## Reproduction

Use the Python science environment and hash-pinned raw caches described in the [0.7 guide](QUALITY_VALIDATION.md). Raw FITS files are Git-ignored under `data/raw/`. Do not delete the protocol/opened results and rerun them as a new validation. For a newly prespecified output directory and validation region:

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_covariance_data
.\.venv\Scripts\python.exe -m scripts.covariance_study --design
.\.venv\Scripts\python.exe -m scripts.covariance_study --develop
# Commit design and code before the next step.
.\.venv\Scripts\python.exe -m scripts.covariance_study --calibrate
.\.venv\Scripts\python.exe -m scripts.covariance_study --seal
# Commit calibrator and seal before validation.
.\.venv\Scripts\python.exe -m scripts.covariance_study --validate
.\.venv\Scripts\python.exe -m scripts.build_covariance_overview
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The runner checks source/input hashes and requires the seal to exist in HEAD before fitting validation. [calibrator.json](../web/data/covariance/calibrator.json), [validation-protocol.json](../web/data/covariance/validation-protocol.json), and [overview.json](../web/data/covariance/overview.json) link hashes to source products.

## Next steps and acceptance conditions

Use the **already opened fields** for a 2×2 ablation: plane/quadratic background × fixed/flexible ePSF. Keep pixels, alignment, neighbors, and gates identical; split sources/exposures in internal validation to avoid choosing a model based on the same noise it fit. Measure RMS, P90, bias, and stability by S/N, source density, detector position, and η boundary hits.

Select a candidate only if RMS/P90 do not rise in defined groups, no additional fits are lost, and average improvement does not come from a single field. Then test S/N- and background-conditional floors/covariances on a separate calibration set, with shrinkage/pooling so small groups cannot learn arbitrary floors. Lock the model, grouping rules, and coefficients **before** a new external set. Acceptance still requires position, two-sided coverage, and ellipse-area gates; do not apply the model to WISE 0855 merely because pooled RMS falls.
