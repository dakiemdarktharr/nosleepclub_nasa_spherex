# Spectral Control: Real Data, No Flux Coefficient Ready for Image Fitting

Two public JWST/NIRSpec spectra of WISE 0855 from program 1230 are now available: [G395M](WISE0855_EXTERNAL_SED.md) and [PRISM](WISE0855_PRISM.md). Both are MAST pipeline products, not author-extracted Figure 4 tables or the paper's Spitzer calibration. Raw FITS, associations, and metadata remain in a Git-ignored cache. The repository records source URLs, hashes, and reports; it does not copy raw data into the web application.

## Recorded results

| Check | Result | Interpretation |
|---|---|---|
| G395M x1d | 1,233/1,254 usable rows; 335/335 in 4.4–5.0 µm | Technical mask; not a flux-accuracy certification |
| R7 lab response | 17 D6 channels × Cent/Allpix × 3 shifts = 102 conditions | Nominal channels; not matched to each QR2 pixel's response |
| V2 kernel on G395M | 102 computed; 102 partial; 0 full; 0 numerical failures | No extrapolation across DQ flags or outside the file domain |
| Missing absolute weight | 0.0136776–0.1592443% | Fraction of weight, not a flux offset or flux error |
| Additional PRISM data | 100/100 samples within the response domain; 102/102 including brackets | No convolution, spectrum merge, scaling, or LSF correction yet |

The final usable G395M sample is at 5.0930738449 µm; following samples have DQ flags. The original lab response extends to 5.104283 µm, and the largest shift extends to 5.110683 µm. Thus all 102 conditions have missing weight because of the final DQ-masked spectrum; 68 conditions also extend beyond the G395M file domain. Do not assume the small tails have zero flux. The mean over the supported part is recorded separately; all full-band means and ratios that require a full-band mean are null. Do not infer confidence intervals from potentially correlated flux samples.

Valid PRISM samples bracket the entire response domain within the 0.01 µm gap limit. This resolves sample availability for the supplemental data; it does not establish equivalent resolution or flux calibration. PRISM was not substituted for G395M in the 102 results above, and no merged SED was produced.

## Failure, configuration lock, and reproducibility

V1 `b3eb94c` stopped on the fourth condition because a rounded root fraction became 1 and lost the width of a small response lobe. The [failure receipt](evidence/0.10/spectral-reference-b3eb94c-aborted.json) and V1 source remain intact. V2 preserves both lobes with a stable analytic moment and does not clip signs. A numerical preflight examined the 102 development conditions before V2 was locked; this is not unseen validation.

The official run used commit `f5a1e518a4d0f28268337f42af0bbabdfc605e78`. [V2 design](../web/data/spectral-response/v2-design.json) SHA-256: `fd7c0c6141d7a8b204190b04ca140017e9b0316585df07d21d913937c37718c9`. [Report for 102 conditions](../web/data/spectral-response/v2-development-audit.json): 150,164 bytes, SHA-256 `21a07ae84771d4267c8afc992005a74eb82554c375e4c62cee21c3049187a97b`. Each curve and functional weight vector has a hash; the 35 CSV files that were read were not extracted to disk. Three product tests recalculate denominators, check hashes, and replay all conditions when raw data are available. The V2 kernel has 13 tests, including real-data regressions and independent integration checks; the lab parser has 3, G395M 3, and PRISM 5 tests.

## Before constraining flux in a WISE fit

1. Match the response by detector/pixel, wavelength, and release; verify flux convention, solid angle, and gain. R7 does not automatically replace QR2 calibration.
2. Define LSF handling, negative-response treatment, normalization, and PRISM/G395M covariance; report differences and limits instead of visually merging the spectra.
3. Lock the adapter and point model on development data; test S/N, centroid bias, modes, and uncertainty with independent source-noise/PSF controls before external calibration.

The [shared-flux core](LINKED_FLUX_MODEL.md) has passed arithmetic checks but does not yet connect these assumptions to real image pixels. The 30 prospective fields remain unmeasured. None of these results confirms motion or production readiness.
