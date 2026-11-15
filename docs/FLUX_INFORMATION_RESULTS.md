# Flux-Information Diagnostic Results at Truth

Across three opened fields, the matched-Gaussian experiment at the truth position shows `JᵀJ` greater than the profile Fisher information `F`, close to prediction `G` from the locked numerical model. Mean Hessian values are generally near `F`, but the precision is insufficient to conclude that every epoch lies within the ±20% diagnostic band. These are results at the **truth position with fixed weights**; they are not position fits, coverage, RMS, astronomical confirmation, or a basis for promotion.

Protocol and sources were locked at commit `215dbfab9fb02ed8a1faec43639fd224ea52450d`; design SHA-256 `59d43f97fb2784760fd851f78a5f12fa13ac1b98904aee47f0778640ae1828c1`. Each case contains 64 Gaussian draws; the two epochs and two truth conditions use paired draw indices. Draws are noise realizations, **not independent sky fields**. There is no IRLS, reduced-χ² inflation, optimizer, source shot noise, or registration variation. The primary condition has padded truth matched to the template; the secondary condition retains the old nearest-neighbor truth and the same noise. The expectations `F`, `G`, and `V` apply directly only to the primary condition under the assumptions in the [English protocol](FLUX_INFORMATION_PROTOCOL.en.md) and [hash-locked original](FLUX_INFORMATION_PROTOCOL.md).

## Results by epoch

Ratios `M/F` in the table are `tr(F⁻¹M)/2`, dimensionless. Observed columns use **matched / old-nearest**; theoretical `G/F` and `V/F` values are for matched. The Hessian 95% CI is a 2,000-draw bootstrap at a 0.002 sky-pixel step for matched. Each group has 64/64 results, zero failures, and 64/64 Hessians stable under the 0.002/0.004 step check in **both** conditions. CIs are exploratory and not adjusted for multiple epochs/cases.

| Field | SNR/frame | Epoch | `JᵀJ/F` matched / old | `G/F` matched | `H/F` matched / old; matched CI | Cov(score)/F matched / old / `V/F` | Mean χ²/dof matched / old |
|---|---:|---|---:|---:|---|---:|---:|
| w350p35 | 2 | before | 1.476 / 1.476 | 1.501 | 0.911 / 0.910; [0.816, 1.010] | 1.273 / 1.273 / 1.250 | 0.9999 / 0.9999 |
| w350p35 | 2 | after | 1.540 / 1.540 | 1.501 | 1.025 / 1.024; [0.916, 1.133] | 1.217 / 1.217 / 1.250 | 1.0140 / 1.0140 |
| w350p35 | 4 | before | 1.115 / 1.115 | 1.125 | 0.967 / 0.966; [0.922, 1.015] | 1.124 / 1.124 / 1.063 | 0.9999 / 0.9999 |
| w350p35 | 4 | after | 1.140 / 1.140 | 1.125 | 1.008 / 1.008; [0.955, 1.059] | 1.054 / 1.054 / 1.063 | 1.0140 / 1.0140 |
| w090p10 | 2 | before | 1.529 / 1.529 | 1.509 | 0.982 / 0.981; [0.888, 1.078] | 1.356 / 1.356 / 1.254 | 1.0012 / 1.0012 |
| w090p10 | 2 | after | 1.497 / 1.496 | 1.508 | 1.003 / 1.003; [0.893, 1.112] | 1.096 / 1.096 / 1.254 | 0.9989 / 0.9989 |
| w090p10 | 4 | before | 1.140 / 1.140 | 1.127 | 0.994 / 0.994; [0.951, 1.037] | 1.092 / 1.092 / 1.064 | 1.0012 / 1.0012 |
| w090p10 | 4 | after | 1.127 / 1.127 | 1.126 | 1.021 / 1.020; [0.967, 1.074] | 0.924 / 0.923 / 1.063 | 0.9990 / 0.9990 |
| w210m20 | 2 | before | 1.559 / 1.560 | 1.501 | 1.140 / 1.140; [1.023, 1.260] | 1.452 / 1.452 / 1.251 | 0.9945 / 0.9945 |
| w210m20 | 2 | after | 1.493 / 1.493 | 1.501 | 0.939 / 0.939; [0.853, 1.027] | 1.475 / 1.475 / 1.251 | 1.0011 / 1.0011 |
| w210m20 | 4 | before | 1.157 / 1.157 | 1.125 | 1.070 / 1.070; [1.016, 1.124] | 1.206 / 1.206 / 1.063 | 0.9945 / 0.9945 |
| w210m20 | 4 | after | 1.123 / 1.123 | 1.125 | 0.970 / 0.970; [0.913, 1.031] | 0.973 / 0.973 / 1.063 | 1.0011 / 1.0011 |

Under the predefined diagnostic tolerance `[0.8, 1.2]`, the CI for `w210m20` SNR 2 before crosses the upper boundary, so this group is **inconclusive**; all other matched CIs lie fully within the band. This is not a formal equivalence test. Mean `H/F` at step 0.004 differs from step 0.002 by no more than 0.000029 across 24 condition–epoch groups. Cov(score) is the sample covariance after subtracting the mean; JSON stores the full matrix and a post hoc draw-bootstrap CI for its ratio, without multiple-comparison correction.

Matched mean score and 95% draw-bootstrap CIs, in sky-grid x/y order and sky-pixel⁻¹ units:

| Field / SNR | Epoch | Mean score x; CI | Mean score y; CI |
|---|---|---|---|
| w350p35 / 2 | before | 1.459; [−0.654, 3.569] | −1.792; [−4.140, 0.461] |
| w350p35 / 2 | after | −1.201; [−3.257, 0.751] | 0.598; [−1.521, 2.763] |
| w350p35 / 4 | before | 2.696; [−1.232, 6.693] | −2.918; [−7.193, 1.110] |
| w350p35 / 4 | after | −0.268; [−3.382, 2.836] | 0.338; [−3.932, 4.929] |
| w090p10 / 2 | before | 0.129; [−2.258, 2.491] | −0.345; [−2.583, 1.938] |
| w090p10 / 2 | after | −0.997; [−2.986, 0.948] | −0.691; [−2.549, 1.136] |
| w090p10 / 4 | before | −0.376; [−4.638, 3.828] | −0.178; [−4.335, 3.975] |
| w090p10 / 4 | after | 1.063; [−3.067, 4.897] | −0.110; [−3.094, 2.874] |
| w210m20 / 2 | before | 0.950; [−1.231, 3.179] | −0.021; [−2.384, 2.409] |
| w210m20 / 2 | after | 0.001; [−2.300, 2.260] | 0.068; [−2.508, 2.708] |
| w210m20 / 4 | before | 1.957; [−1.786, 5.913] | −0.544; [−4.935, 3.869] |
| w210m20 / 4 | after | −2.746; [−6.267, 0.858] | 2.168; [−1.975, 6.173] |

All intervals above include zero, but that does not prove the mean score is zero. The maximum absolute paired old-nearest minus matched difference across 12 groups is 0.000109 for `JᵀJ/F` and 0.000696 for `H/F`; these comparisons and CIs are post hoc and do not validate a physical PSF. Degrees of freedom are calculated per exposure: valid pixels minus nuisance rank minus one amplitude, with no centroid subtraction because centroids are not fit.

## Audit and public data

[development-summary.json](../web/data/flux-information/development-summary.json) retains all **unrounded** values for 384 draws × two conditions × two epochs: `JᵀJ`, both Hessians, score, score quadratic, χ²/dof, profiled amplitudes, stability flags, failures, and metadata. Summaries/CIs are recalculated from draws and compared with raw results; post hoc bootstrap analyses are added for score covariance and matched/old differences. Metadata includes hashes for code, protocol, source data, URLs, calibration, catalog, and selected exposures.

The raw report stores only aggregate matrices `F`, `F_known`, `G`, and `V`, plus amplitude, target information, pixel, and rank per exposure; it does **not** store per-exposure derivative matrices. The builder post hoc reconstructs `DᵀPD` and `DᵀD` matrices from cached native inputs using the same frozen code, verifies manifest/FITS/calibration/catalog hashes, and sums them to check all four aggregate matrices. These contributions are public under `post_run_geometry_audit`; this is deterministic reconstruction using the same implementation, not a new measurement or independent validation of the derivative formula. The raw report remains unchanged.

```powershell
.venv/Scripts/python.exe -m scripts.build_flux_information_report
.venv/Scripts/python.exe -m unittest tests.test_flux_information_products tests.test_flux_information_probe -v
```

- Raw report SHA-256: `e21a60352a8f04291e13a370126322b178edb78c8c49f8508248e57c79aa5100`.
- Design SHA-256: `59d43f97fb2784760fd851f78a5f12fa13ac1b98904aee47f0778640ae1828c1`.

The audit recalculates q, mean matrices, draw-level CIs, χ²/dof, and totals from each exposure. The largest difference when recreating the prior mean is `7.05e-17` native-image units; selected-pixel noise is `5.56e-17`. These checks do not measure physical error or validate centroid coverage.

## Two next directions require separate designs

- **Exposure-cluster sandwich:** test `H⁻¹ V H⁻¹` at fitted positions, with score grouped by exposure, Huber/nuisance refitting, and a pre-specified finite-sample correction. There are only about 10 exposures per epoch, fitted scores are constrained, and shared references may be correlated; a naive meat estimator may be biased, and reference covariance must retain cross-covariance. Compare with the existing profile H on **new noise realizations with seeds locked in advance**, then validate on independent fields. Report failures, bias, 50/68/95% coverage, and area using the same denominator.
- **Full-refit parametric bootstrap:** generate new noise from the model fitted to observed data and refit centroid, flux, nuisance terms, starting points, and both IRLS iterations; for total uncertainty, also model shared registration/reference terms. Compute cost is high; PSF/SED misspecification, sky residuals, modes, and plug-in bootstrap assumptions may still cause undercoverage. Lock seeds, inner/outer counts, thresholds, and runtime in advance; check on new realizations and unopened fields; report all failures and areas.

The theoretical relation `V = F + Σ (1/I_i)D_iᵀP_iD_i` motivates the sandwich estimator as a hypothesis to test. This experiment does not show that `H⁻¹VH⁻¹` achieves nominal coverage, removes all error, or explains the full pipeline.
