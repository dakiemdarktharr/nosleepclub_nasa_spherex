# Continuous Target ePSF Boundary: Development Results

**Result: insufficient basis for changing the scientific method.** Across the three opened fields, padding the target ePSF made the profile Hessian more stable, but vector-error RMS did not decrease in any of the six Gaussian cases. At SNR 2/frame, the profile 68% ellipses contained truth in only 31/64, 36/64, and 34/64 trials. These are frequencies from conditional trials, not precise estimates of coverage for all sky sources.

The protocol and model code were locked at commit `f138e1109183bb7db2122384ec1cfcd8f5958488`; design SHA-256: `ea41e9e83133329c04f9d648d193941053a84ca4805cdfd35c746634b6dfec5a`. Trial truth still uses the frozen nearest ePSF, while the candidate pads only the target ePSF; neighbor ePSF, mask, WCS, noise, and nuisance projection follow the protocol. There was no independent physical-PSF validation, no added source shot noise, no new independent field, and no new WISE 0855 measurement. See the [protocol](CONTINUOUS_EPSF_PROTOCOL.md) for data generation, assumptions, and limits.

## Gaussian controls by field and case

Each row contains 64 noise-independent Gaussian draws on the same geometry/exposure for one case, not 64 independent sky fields. All fits in both branches were numerically valid: common-numeric denominator = 64. The table reports raw Gauss–Newton (GN) and observed profile Hessian (H) ellipses, before group calibration; coverage values show truth-containing ellipses divided by available covariances. RMS uses the same 64 pairs; ΔRMS = candidate minus baseline.

| Field | SNR/frame | Common accepted | RMS baseline → candidate (″) | GN 68% baseline → candidate | GN 95% baseline → candidate | H 68% baseline → candidate | H 95% baseline → candidate |
|---|---:|---:|---:|---:|---:|---:|---:|
| w350p35 | 2 | 62/64 | 2.2905 → 2.3115 | 24/64 → 22/64 | 43/64 → 43/64 | 9/20 → 31/64 | 18/20 → 56/64 |
| w350p35 | 4 | 64/64 | 0.8029 → 0.8031 | 39/64 → 42/64 | 61/64 → 61/64 | 16/28 → 44/64 | 25/28 → 61/64 |
| w090p10 | 2 | 64/64 | 1.9428 → 1.9477 | 28/64 → 28/64 | 48/64 → 48/64 | 11/21 → 36/64 | 16/21 → 53/64 |
| w090p10 | 4 | 64/64 | 0.7822 → 0.7904 | 39/64 → 39/64 | 61/64 → 60/64 | 14/25 → 41/64 | 23/25 → 62/64 |
| w210m20 | 2 | 63/64 | 2.0948 → 2.1003 | 22/64 → 23/64 | 47/64 → 47/64 | 13/23 → 34/64 | 19/23 → 51/64 |
| w210m20 | 4 | 64/64 | 0.8541 → 0.8545 | 36/64 → 35/64 | 60/64 → 61/64 | 13/25 → 39/64 | 24/25 → 61/64 |

Baseline and candidate accepted counts were 62, 64, 64, 64, 63, and 64/64, respectively, in row order; in this data the accepted subsets for both branches match. **The baseline H sample is smaller because Hessians that failed the criteria were excluded; its coverage must not be compared directly with candidate H coverage as if both used the same population.** Counts, RMS, P90, coverage, and paired ΔRMS are recorded separately in JSON for baseline-numeric, baseline-accepted, candidate-numeric, candidate-accepted, common-numeric, and common-accepted subsets.

The Hessian uses steps of 0.002 and 0.004 sky pixels. Of 768 Gaussian epoch fits, 304 baseline Hessians changed by more than 5% relatively; none of the candidate Hessians did. The candidate had valid profiles at both epochs in all 384 draws. This confirms numerical stability in the completed experiment; it does not establish calibrated uncertainty or a physically accurate padded PSF.

The 68% ellipse area is `π × 2.278868566 × sqrt(det(C))`, in arcsec². Medians on the common-numeric subset for GN baseline → candidate were 5.773 → 6.063; 1.982 → 2.041; 6.056 → 6.108; 2.025 → 2.069; 5.814 → 5.902; and 2.010 → 2.048. Candidate profile medians were 8.554; 2.307; 8.321; 2.342; 8.687; and 2.231. JSON also records baseline profile areas and their denominators. Because selection differs, do not treat the area ratios as paired comparisons.

## Original-background images: six separate trials

The values below are arcsecond vector errors for **one injected source on each original-background image**. They are separate from the 64 Gaussian draws and are not six new detections:

| Field | SNR/frame | Baseline (″) | Candidate (″) |
|---|---:|---:|---:|
| w350p35 | 2 | 2.5895 | 2.6121 |
| w350p35 | 4 | 1.1922 | 1.1897 |
| w090p10 | 2 | 1.3384 | 1.4012 |
| w090p10 | 4 | 0.5436 | 0.5499 |
| w210m20 | 2 | 1.7322 | 1.7642 |
| w210m20 | 4 | 0.4438 | 0.4493 |

## Audit and reproducibility

The public [development-summary.json](../web/data/continuous-epsf/development-summary.json) retains all 384 pairs, before/after positions, error vectors, covariance, q, quality status, profile covariance, and per-epoch support flags. Stored values are not rounded; the table above is rounded for readability. Metadata includes hashes for all locked sources, selected image/calibration URLs and SHA-256 values, exposure pairs, Gaia data, and field provenance.

The builder checks that all 384 baseline pairs match the cache, all six baseline original-background trials match, and six draw-0 replays have matching status and zero-arcsecond vector difference. It rechecks vectors from positions and truth, q from covariance, GN/profile covariance with shared registration, Hessian stability, and recomputes denominators/RMS/coverage. File/source comparisons use SHA-256 and the locked commit. Independent tests recompute q, area, and subsets from JSON, and compare against the cache when present:

```powershell
.venv/Scripts/python.exe -m scripts.build_continuous_epsf_report
.venv/Scripts/python.exe -m unittest tests.test_continuous_epsf_products -v
```

- Raw report SHA-256: `1bc935bed7871a6b71e1163047828c75712bd072d023321c265126409420e270`.
- Baseline cache SHA-256: `98d284e521f6b188435e49c4af701da55fc25b55a17fc3b29639456bbc209d30`.
- Baseline profile report SHA-256: `97c3cd54857cc7297415485c7bbb5c0d4a0d981eef32a9e9cf4ecb4509ed81ff`.

Next, diagnose bias and missing uncertainty sources on already opened data, and pre-register an error budget plus field/exposure/time split for independent validation. Consider promotion only after absolute error, coverage, ellipse area, and failure/abstention rates meet pre-registered thresholds on unopened fields. Do not promote this result to an astronomical detection.
