# WISE 0855: Epoch Coadds and Independent Astrometry

Run date: 2026-10-30. [Open the demo](http://127.0.0.1:8766/). Full values, covariance, observation IDs, URLs, and hashes are in [results.json](../web/data/motion/results.json), the [web manifest](../web/data/manifest.json), and configuration-specific evidence JSON.

This report predates Gaia anchoring. The expanded star-field step is complete; see [new Gaia results and remaining limits](WISE0855_GAIA.md). Products from this step are retained unchanged for comparison.

## Current results

A westward displacement signal has been measured for the source in the WISE 0855 region. Two positions were fit independently on original pixels without forcing the old motion vector. This measurement does not confirm astronomical motion because the systematic-error budget is incomplete.

| Configuration | Images per epoch | Best single-image → coadd S/N, before | Best single-image → coadd S/N, after | East / North | Displacement ± model error | Heldout-star RMS |
|---|---:|---:|---:|---|---|---|
| Strict spectrum, primary | 2 | 2.55 → 2.60 | 4.66 → 4.57 | −3.08″ / +1.05″ | 3.25″ ± 1.05″ | 0.53″, 3 stars |
| Broad spectrum, sensitivity check | 10 | 5.11 → 7.87 | 4.64 → 7.58 | −3.24″ / +0.03″ | 3.25″ ± 0.80″ | 0.66″, 4 stars |

The strict configuration does not clearly improve S/N; retain the result as is. The two configurations share some images and are not independent confirmations. The broad configuration is shown first on the web to demonstrate coaddition, but is clearly labeled as a sensitivity check.

S/N is an aperture statistic at the fitted position, not confidence in a blind detection. Before/after aperture coverage is 94.7% / 100% for strict and 84.2% / 100% for broad. Single images are compared at the same position and additionally use the valid mask from the coadd. This is not a total-flux measurement or evidence of brightness variability.

## Data and spectral selection

- Source: SPHEREx QR2, D6, 31 real cutouts in MJD windows [60989, 60994) and [61151, 61157), corresponding to November 2025 and April 2026. Each cutout is 0.12° wide, centered on the target region.
- Retain IMAGE, VARIANCE, FLAGS, ZODI, native WCS, and original detector WCS. Use the baseline quality mask and retain the SOURCE bit.
- Use the complete science CWAVE/CBAND map `cal-wcs-v4-2025-254`; baseline WCS-WAVE is for visualization only. Use ePSF `cal-epsf-v1-2026-191`, oversampling 5, convolved with pixel response. IRSA recommends the newer ePSF for QR2 images as well.
- Select target-region wavelengths within 4.55–4.94 µm. Match exposures one-to-one across epochs by `|Δλ| / mean spectral width`, using an assignment optimizer and no duplicated exposures. Strict gate ≤0.20; broad gate ≤0.50. Fix configuration before fitting the target.
- Strict uses two pairs per epoch near 4.572/4.578 and 4.606/4.611 µm. Broad has 10 pairs extending to about 4.94 µm. This is a weighted coadd of multiple spectral channels, not 10 images at the same wavelength.
- Each pair uses weights inversely proportional to the summed median variance of the two exposures. Normalize, then use the **same spectral weights in both epochs**. Apply local coverage normalization; retain pixels with at least 90% of total input weight. Matching central wavelength/width does not guarantee identical full spectral response.

The two calibration URLs and SHA-256 hashes are pinned in `prepare_motion_data.py`; raw data stays uncommitted under `data/raw/`. A future calibration file does not silently change this experiment.

## Coaddition and position measurement

1. Subtract ZODI and a sigma-clipped median background. Reproject each image to a 64×64 TAN grid at 6.15″/pixel using a sparse bilinear operator; propagate variance with squared weights. Missing support remains missing data.
2. Select bright stars present in both coadds, away from the target and edges. Alternate them into alignment and heldout sets: 3/3 or 4/4. Fit ePSFs to alignment stars in each exposure; require at least two stars with S/N ≥7 and no boundary hit. Fit translation only; do not fit high-order distortion with few stars.
3. Fit ePSF to original pixels in each epoch, with a shared centroid across exposures within the epoch; each exposure has its own amplitude and background plane. Do not constrain shared spectral color or flux. Both epochs use the same search region, 31.5 ±2.5 pixels; the predicted vector is not a position constraint.
4. Use multiple initial positions and check convergence/bounds. All target centroids converge and avoid bounds. Reduced chi-square is about 1.09–1.18. Position is the time-weighted mean within the epoch; effective MJD uses fitted S/N² weights. Motion is not fit across the <6-day window; old extrapolation suggests <0.14″ smear.
5. Centroid covariance comes from the Jacobian and is inflated when reduced chi-square >1. Also run 128 Gaussian-noise simulations on original pixels for each epoch/configuration with saved seeds. Use only the positive covariance increase from bootstrap; do not reduce formal error. No simulated fit hits a boundary.
6. Measure heldout-star displacements with the same method, independently of the alignment fit. Add the second moment of heldout residuals (including mean bias), plus the mean alignment covariance across both epochs, to the target displacement covariance. This term may count some noise twice and is retained conservatively.

| Configuration | Effective MJD before / after | RA, Dec before (degrees) | RA, Dec after (degrees) |
|---|---|---|---|
| Strict | 60989.366953 / 61153.061990 | 133.759831; −7.242381 | 133.758970; −7.242088 |
| Broad | 60990.692919 / 61154.178274 | 133.759818; −7.242080 | 133.758910; −7.242072 |

These are positions in the relatively aligned SPHEREx WCS, not anchored to an external astrometric frame. Full covariance is in JSON. The web displays per-axis σ with alignment and half the heldout-star term per epoch; the two covariance contributions sum to the displacement covariance. The 68% ellipse uses Δχ²=2.30 under a 2D Gaussian assumption. Uncertainty in vector length is first-order propagation along the vector direction, not absolute systematic accuracy.

For aperture S/N with 2.5-pixel radius and 4–6-pixel background annulus, aperture/background weights are propagated back through the reprojection operator to original pixels. This retains interpolation covariance in the aperture statistic, while still assuming independence between original pixels and exposures. Background-plane removal works with asymmetric masks.

## Prediction comparison and controls

External prediction uses [Luhman 2014, Tables 1–2](https://arxiv.org/pdf/1404.6501): μRA cos Dec = −8.06″/year, μDec = +0.70″/year, parallax 0.454″, plus Earth's barycentric displacement from Astropy's built-in ephemeris. For the broad configuration, predicted East/North is about −4.47″ / +0.54″ versus measured −3.24″ / +0.03″. This is a comparison; proper motion and parallax are not independently fit from two epochs. The dashed image annotation still shows the old linear extrapolation without parallax and is recorded separately to distinguish it from the vector in the plot.

Two-dimensional Mahalanobis displacement relative to zero is 3.18 (strict) and 4.34 (broad). **Do not convert these to Gaussian sigma, detection probability, or astronomical confirmation**, because systematic errors and source selection are not fully calibrated.

Synthetic ePSF sources were injected at off-target locations on real-data backgrounds; displayed data and alignment stars were not changed:

| Configuration | Stationary source: measured vector (pixel) | True-moving source `(0.60, 0.05)` pixel: measured vector | Mahalanobis error, stationary / moving |
|---|---|---|---|
| Strict | (0.008; −0.096) | (0.690; −0.025) | 0.87 / 1.10 |
| Broad | (0.008; −0.145) | (0.656; −0.088) | 2.59 / 2.77 |

The stationary source is still offset by 0.59″ / 0.89″. This control has one position and one amplitude, adds no source shot noise, and uses fixed calibration. It shows that background/blending effects may be substantial; do not use one-position results to tune the target error for a better-looking value. There is no completeness or false-positive benchmark.

An alignment/heldout-star swap was attempted but failed because `2025W46_1A_0090_3` no longer has two stars with S/N ≥7. Keep the threshold and record the reason in JSON/web. This robustness check **failed**; it is not a passed test.

The 18 offline tests cover stationary/moving centroid recovery at different pixel phases, aperture variance against Monte Carlo, background subtraction with missing pixels, WCS sign, PSF controls, hashes/provenance, disjoint star sets, positive covariance, and highlight masks. Software tests passing do not confirm astronomical motion.

## Demo and products

The demo retains two coadd configurations and three single-image pairs. Markers/ellipses are measurements; predicted overlays can be enabled separately. Compare side-by-side, wipe, blink, or difference; press **Zoom to selection** to inspect subpixel displacement. No automatic residual exceeds the current broad-configuration gates; the known-position source-region centroid is still measured independently as above. Do not label a residual highlight as WISE 0855 without source-identity evidence.

PNGs use the same asinh stretch in both epochs, clipped from median−2σ to median+12σ of the combined background; bright stars may be clipped on screen. Display images are cross-convolved with a local synthetic ePSF and corrected for gain/background. This is for viewing/residual inspection only; **smoothed images are not used to fit centroids**. Output variance is diagonal; full convolution covariance is not saved. EMP_SCORE is an empirical residual score.

FITS contains WCS and units for BEFORE/AFTER, VAR_BEFORE/VAR_AFTER, COADD_A/COADD_B, DIFFERENCE, EMP_SCORE, and VALID. Raw/calibration/centroid-covariance provenance remains in evidence JSON. Reproduce with the commands in the [README](../README.md).

## Limitations and next milestone

Current errors are conditional on the chosen ePSF, noise map, and reference-star set. ePSF error, correlated detector pixels, different spectral colors, blending, background-star proper motion, and external WCS error are not fully modeled. Bootstrap simulates noise only and does not cover these uncertainties. Both configurations share input images and are not independent. Two epochs cannot separate proper motion and parallax.

**Next milestone after this version: expand the reference-star field and compare with Gaia.** The goal is to test whether the approximately 3.25″ vector is stable under a changed astrometric frame. Acceptance conditions:

1. Add enough high-S/N reference stars, cross-match the catalog, propagate stellar positions to observation epochs, and record exclusion rules.
2. Run alignment-star swaps and leave-one-out checks on every exposure; report failures and keep an independent heldout set.
3. Use multi-position/brightness injections to measure bias and uncertainty-interval coverage. Raise confidence only if background residuals and vector changes remain within a prespecified error budget.

Then verify the full spectral response and add a third epoch to test a motion + parallax model. Once the baseline is stable enough, use real review and evaluated injections to build labels, benchmarks, and a vision model that ranks candidates for human review.

Official calibration references: [IRSA data products](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/) and the [ePSF guide](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/).
