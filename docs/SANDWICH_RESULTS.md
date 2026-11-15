# Exposure-Level Sandwich Covariance Development Results

**The sandwich covariance is not ready for promotion.** In the three SNR 2/frame cases, the 68% centroid-only ellipses contained the truth in 73/128, 71/128, and 65/128 draws. Profile Hessian ellipses did so in 76/128, 73/128, and 63/128 draws. Median sandwich area exceeded Gauss–Newton area in all six cases, but coverage did not improve consistently over the profile Hessian. This is a conditional experiment on three previously opened fields, not independent calibration or astronomical validation.

The candidate uses the exact padded 0.10 point estimator. Each draw fits position once, then evaluates all three covariance estimates at that same position. The truth still uses the frozen nearest ePSF, so a known mismatch remains; native Gaussian noise uses a new seed for each field/case, with no source shot noise. The final Huber IRLS weights stay fixed for score and Hessian calculations; derivatives through IRLS, shared reference uncertainty, and cross-exposure correlations are not included. CR1p `N/(N−2)` is only an empirical correction with two profiled centroid parameters; it is not guaranteed to be appropriate with few exposures or many nuisance parameters. GN and profile-H retain the candidate's `max(1, reduced χ²)` inflation; the sandwich estimate has no such inflation. See the [protocol](SANDWICH_PROTOCOL.md).

## Centroid-only coverage by field and case

Each triplet is the number of ellipses containing truth at nominal **50 / 68 / 95%**. All three methods have 128/128 numerically valid points and 128/128 supported covariances in every case, so all-attempt, numeric, and common-supported selections are identical in this table. Each row has 128 noise realizations, **not 128 independent sky fields**. The χ² thresholds describe ellipses; they do not guarantee nominal coverage.

| Field | SNR/frame | GN: 50/68/95 | Profile H: 50/68/95 | Sandwich: 50/68/95 | Wilson 95% CI for sandwich 68% |
|---|---:|---:|---:|---:|---:|
| w350p35 | 2 | 38 / 54 / 97 | 52 / 76 / 110 | 56 / 73 / 105 | 48.4–65.3% |
| w350p35 | 4 | 60 / 88 / 120 | 60 / 94 / 123 | 66 / 85 / 118 | 57.9–74.0% |
| w090p10 | 2 | 41 / 64 / 98 | 54 / 73 / 111 | 52 / 71 / 104 | 46.8–63.8% |
| w090p10 | 4 | 50 / 81 / 114 | 58 / 84 / 116 | 57 / 86 / 115 | 58.7–74.7% |
| w210m20 | 2 | 43 / 49 / 90 | 48 / 63 / 108 | 45 / 65 / 104 | 42.2–59.3% |
| w210m20 | 4 | 57 / 78 / 113 | 59 / 88 / 119 | 60 / 87 / 117 | 59.5–75.4% |

Wilson intervals quantify Monte Carlo uncertainty for draws within each case. They do not account for dependence between fields, multiple-group inspection, or population generalization. These intervals are not total astronomical uncertainty.

The accepted and common-accepted samples also coincide because all three covariances are supported. This table reports the **same three levels** on the accepted sample; quality-rejected cases remain included in the all-attempt table above.

| Field | SNR/frame | Accepted / attempts | GN: 50/68/95 | Profile H: 50/68/95 | Sandwich: 50/68/95 |
|---|---:|---:|---:|---:|---:|
| w350p35 | 2 | 127 / 128 | 38 / 54 / 97 | 52 / 76 / 110 | 56 / 73 / 105 |
| w350p35 | 4 | 128 / 128 | 60 / 88 / 120 | 60 / 94 / 123 | 66 / 85 / 118 |
| w090p10 | 2 | 124 / 128 | 40 / 63 / 95 | 53 / 72 / 108 | 51 / 70 / 101 |
| w090p10 | 4 | 128 / 128 | 50 / 81 / 114 | 58 / 84 / 116 | 57 / 86 / 115 |
| w210m20 | 2 | 127 / 128 | 43 / 49 / 90 | 48 / 63 / 108 | 45 / 65 / 104 |
| w210m20 | 4 | 128 / 128 | 57 / 78 / 113 | 59 / 88 / 119 | 60 / 87 / 117 |

The JSON also records 50/68/95% coverage and intervals for all three methods with **centroid + registration**, by selection. Registration offsets were held fixed while noise was generated; adding registration covariance is a pipeline comparison, not a test of total coverage. Relative to centroid-only, the numeric selection has only three changed counts: w350p35 SNR 2 profile-H at 50% goes from 52 to 53; w350p35 SNR 4 sandwich at 68/95% goes from 85/118 to 86/119; and w210m20 SNR 4 GN at 50% goes from 57 to 58.

## Area and point error

Median 68% centroid-only ellipse area in arcsec² and RMS vector error across 128 numerically valid points:

| Field | SNR/frame | GN | Profile H | Sandwich | Point RMS (″) |
|---|---:|---:|---:|---:|---:|
| w350p35 | 2 | 6.071 | 8.470 | 8.231 | 1.959 |
| w350p35 | 4 | 2.010 | 2.217 | 2.221 | 0.771 |
| w090p10 | 2 | 5.978 | 8.866 | 9.961 | 1.971 |
| w090p10 | 4 | 2.094 | 2.369 | 2.406 | 0.874 |
| w210m20 | 2 | 5.823 | 8.081 | 8.605 | 1.994 |
| w210m20 | 4 | 2.104 | 2.378 | 2.454 | 0.865 |

All covariance methods use the **same point estimate**, so sandwich covariance does not improve positional accuracy. The JSON also records east/north bias, P90 error, area, median/P90 major axis, Wilson intervals, and support for each selection. Area alone does not describe the ellipse shape: for example, at w350p35 SNR 2, the sandwich median major axis is 2.257″ versus 1.821″ for profile H, despite slightly smaller sandwich area.

There were 24 multimode epoch fits in the five-final-start test with fixed weights (13 at w350p35 SNR 2, 3 at w090p10 SNR 2, and 8 at w210m20 SNR 2); two starts failed at w350p35 SNR 2. In one w090p10 SNR 2 draw (35), a start found Δχ² = −0.20516 relative to the point at the final weights; that draw was quality-rejected. This does not establish that a different full-IRLS mode is better. There were no point-boundary hits or fit exceptions among 768 draws. The largest relative scalar-score difference from `Jᵀr` was about 5.24e−5.

## Six injections on the original images

These are one injection on the original image for each case, **not** part of the Gaussian draws. The table gives vector error and centroid-only q at the same candidate point. Baseline is the frozen earlier point model; these six values do not compare coverage.

| Field | SNR/frame | Baseline → candidate error (″) | q GN / H / sandwich |
|---|---:|---:|---:|
| w350p35 | 2 | 2.5895 → 2.6121 | 8.132 / 5.430 / 3.519 |
| w350p35 | 4 | 1.1922 → 1.1897 | 5.482 / 5.242 / 9.009 |
| w090p10 | 2 | 1.3384 → 1.4012 | 2.039 / 1.451 / 1.095 |
| w090p10 | 4 | 0.5436 → 0.5499 | 1.068 / 0.849 / 0.518 |
| w210m20 | 2 | 1.7322 → 1.7642 | 3.821 / 1.512 / 1.430 |
| w210m20 | 4 | 0.4438 → 0.4493 | 0.635 / 0.324 / 0.254 |

All six candidate fits on original images were accepted. The two epoch positions, vector errors, and GN covariance plus registration match cache f138. For the 768 draws using new seeds, there is no old point cache for draw-by-draw comparison. Point invariance across the three covariance methods follows from the locked implementation, not from replaying every draw with another fitter.

## Audit and reproducibility

[development-summary.json](../web/data/sandwich/development-summary.json) contains all 768 attempts, every quality state, positions, covariance/q, per-exposure scores, Hessian, meat, mode/start, and metadata. Per-frame arrays and scores are documented in `record_schema`; values are not rounded. The 8.2 MB file is smaller than the 25.3 MB raw input because it retains all evidence, not only summary statistics. Source, design, URLs, and source hashes are recorded with the product.

[overview.json](../web/data/sandwich/overview.json) is the compact UI version: it contains six audited summaries, field provenance, separate original-image injections, and modes with lower objectives. It does not contain the 768-draw arrays; its provenance records the full report hash and size.

The builder checks commit `3995f2e6d0279fda8bedff2b47af1d53129dcfef`, source and design hashes, and seeds. It recalculates meat from scores, Hessian, CR1p covariance, vector error, q, centroid/registration covariance, mode counts, every selection/coverage/Wilson interval/area, and compares against the raw summary. It separately compares the six original-image injections with cache. Total amplitude is not part of the frozen fitter's public epoch record, so numeric-valid status is carried forward from the original result rather than claiming a full gate can be independently reconstructed from summary values. Unit tests compare raw data when cached and independently recompute the main quantities.

```powershell
.venv/Scripts/python.exe -m scripts.build_sandwich_report
.venv/Scripts/python.exe -m unittest tests.test_sandwich_product tests.test_exposure_sandwich -v
```

- Raw report SHA-256: `9a6fa4ef30837ef4fee4b906b742d98b14747c7efb8ec93bebfe813fe82fd578`.
- Design SHA-256: `fe4ea22755062716f7aeea6d6240e0dffdb35fc7c70159e86424f8667081a386`.

Use these results to prespecify a test of robust weights, modes, and registration with new realizations and explicit error/coverage/area criteria; only then test on an independent unopened field. Do not turn development results into a WISE 0855 detection or a scientific certification.
