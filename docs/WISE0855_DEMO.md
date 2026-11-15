# WISE 0855: Real-Data Image Demo

Run date: 2026-10-30. [Open development demo](http://127.0.0.1:8766/).

This report covers the single-image baseline. The newer version coadds images by epoch and fits centroids independently; see [coadd and astrometry results](WISE0855_COADD.md). The conclusions below apply to the three single-image pairs retained in the demo.

## Completed work

- Queried IRSA and downloaded 43 D6 cutouts to inspect spectral WCS around the target region.
- Selected three pairs by time and wavelength; downloaded six more cutouts centered on WISE 0855's extrapolated position.
- Read IMAGE, FLAGS, VARIANCE, ZODI, PSF, and WCS-WAVE; retained the original detector association when selecting PSFs.
- Reprojected to a 64×64 TAN grid at 6.15 arcsec/pixel, north up and east left.
- Fit small shifts using background stars; cross-convolved with the measured PSFs from both images; corrected flux using background-star aperture ratios and background offsets.
- Exported before/after/difference, variance, valid-pixel mask, and empirical residual scores.
- Web UI compares four modes, zoom/highlighting, provenance, and local save/delete/export of annotations.

## Quantitative results

| Pair | Before → after date | Baseline | λ at expected position, before/after | Fixed-PSF S/N, before/after | Post-fit background-star RMS |
|---|---|---|---|---|---|
| 4.853 µm | 2025-05-05 → 2026-05-09 | 368.36 days | 4.853525 / 4.853311 µm | 2.97 / 4.69 | 0.237 px, 5 stars |
| 4.961 µm | 2025-05-05 → 2026-05-11 | 370.40 days | 4.961050 / 4.960913 µm | 1.06 / 2.65 | 0.265 px, 5 stars |
| 4.609 µm | 2025-11-10 → 2026-04-23 | 164.07 days | 4.606615 / 4.610911 µm | 4.46 / 5.28 | 0.210 px, 6 stars |

Machine-generated details are in the [manifest](../web/data/manifest.json). The first pair's spectral width is about 37.9 nm; the measured Δλ is about 0.214 nm. **WCS-WAVE is accurate to about 1 nm for visualization**, so smaller displayed digits should not be interpreted as measurement precision.

RMS is the residual on stars used to fit translation, not an independent star test set. The two images still have different QR2 processing versions (`6.4+psffix1` and `6.5.6` for the first pair); full-field correction does not remove every calibration/spectral-color difference.

## Current conclusion

The software can produce and highlight a difference region from real data. Numerical controls check registration and PSF cross-convolution. **WISE 0855 motion has not been independently verified from these pairs.**

The expected position comes from [Luhman 2014, Tables 1 and 2](https://arxiv.org/pdf/1404.6501): Spitzer coordinates at MJD 56677.3 and the paper's proper motion. Only linear extrapolation is used; parallax is not included and no SPHEREx centroid is fitted. Table S/N is fitted PSF amplitude at that position divided by its error, with error inflation when reduced χ² > 1. This is a prior-based check, not a blind detection.

Automatic highlights are extrema with |score| ≥ 3.5 in unmasked regions with enough support and local wavelength difference ≤ half the spectral width. Scores are normalized by the background-residual distribution and have no false-alarm-probability calibration. A residual may still be an artifact or a source color difference.

## Limitations to retain in the demo

- Wavelength variation may be mixed with time variation; WCS-WAVE is not a replacement for spectral-response calibration in precision science.
- Bilinear interpolation and convolution create correlated noise. Variance uses squared weights, but full covariance between output pixels is not retained.
- A local PSF near the target is used for a small field; spatial PSF variation can still produce residuals.
- Masked pixels use normalized support; regions without enough support are not highlighted.
- No blind centroid fit, parallax model, catalog matching, or injection/recovery on real SPHEREx backgrounds has been completed.
- This is a fixed, inspectable image set, not a tool for arbitrary-coordinate queries.
- Annotations are stored in browser localStorage with analysis/input hashes to avoid labeling the wrong version; there are no accounts or team synchronization.

## Checks performed

Nine tests in `tests/test_science.py` passed: bilinear variance, missing-data mask, SOURCE bit, registration sign, stationary-source control with different PSFs, simulated moving source producing a residual, prior direction, input hash, and consistency of WCS/real products.

The browser was tested directly: before/after, side by side, difference, pair switching, residual selection, save/reload annotation, delete test annotation, JSON export, and evidence dialog. Responsive check at 390×844 had no horizontal overflow; the console showed no error during the inspection. Test annotation was deleted.

Synthetic controls check arithmetic; they are not a recall/precision benchmark on real astronomical sources.

## Next steps after product review

**Priority: improve S/N and measure motion with uncertainty.**

1. Build a manifest of images with compatible spectral response in each epoch; inspect CWAVE/CBAND and quality flags. Do not coadd arbitrary spectral bands.
2. Coadd with weights and retain variance/coverage and contributing frames; measure whether S/N actually improves.
3. Fit PSF/centroid independently in both epochs; check against heldout background stars and include parallax in comparison with reference astrometry.
4. Run injection/recovery on real SPHEREx FITS backgrounds using stationary, moving, and varied-flux sources.

The next step is complete when there is a real epoch coadd, a centroid/error table, an independent-background check, and a clear statement of whether motion is resolved with the available data. Only then build a labeled dataset and measure the benefit of a real/noise CNN.

## Sources and products

- [IRSA: Data Access](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/)
- [IRSA: Cutouts and spectral WCS](https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts/)
- [IRSA: PSF in a cutout](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/)
- [IRSA: Photometry and bit flags](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html)
- [SPHEREx QR2 DOI](https://doi.org/10.26131/IRSA652)
- [Product image](wise0855-demo-desktop.jpg)

Raw FITS and downloaded manifests are in ignored `data/raw/wise0855/`. Small shareable products are in `web/data/`. Processed FITS downloads on the web preserve per-HDU WCS, variance, and processing metadata; `EMP_SCORE` is named to emphasize that it is an empirical score.
