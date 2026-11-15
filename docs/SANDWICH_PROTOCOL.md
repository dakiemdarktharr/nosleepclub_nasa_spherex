# Exposure-Cluster Sandwich Covariance Development Protocol

This protocol compares three covariance estimates at the **same fitted positions** from the locked 0.10 candidate. It does not change centroids, select a model using unseen results, or scientifically promote a method by comparing it with a baseline. This is a development experiment on three already opened fields, not astronomical validation or a new WISE 0855 measurement.

## Candidate, score, and support conditions

For each draw, refit the full padded candidate: five starts, two Huber IRLS iterations, flux/background/neighbor nuisance terms, mask/WCS, bounds, and the common single-source quality reference from 0.10. Only after fitting, with final IRLS weights fixed, calculate per exposure `u_i = ∂[r_iᵀr_i/2]/∂x` at the candidate position by central differences with 0.002 sky-pixel steps. The residual profiles source amplitude and projects out the plane and neighbors, so the score includes the profiled nuisance effects; do not replace it with `amplitude² × Fisher`. Also calculate `J_iᵀr_i` by residual differences and store its difference from the scalar score as a numerical check.

Calculate the observed Hessian `H = Σ_i ∂²[r_iᵀr_i/2]/∂x∂xᵀ` at steps of 0.002 and 0.004 sky pixels, and the meat `B = Σ_i u_i u_iᵀ`, without subtracting the mean score. The candidate is `C_sand = (N/(N−2)) H⁻¹ B H⁻ᵀ`, where `N` is the number of native exposures, evaluated separately for each epoch. The factor is properly called **CR1p**, with `p=2` for the two profiled centroid parameters. [clubSandwich documentation](https://jepusto.github.io/clubSandwich/reference/vcovCR.html) describes the `m/(m−p)` form; here it is a preselected empirical choice, not an exact correction for per-frame nuisance terms, Huber fitting, or correlated references. For N=10, the factor is 1.25. Do not adjust or tune this factor using results.

The `supported` status requires at least 8 distinct exposure IDs per epoch; successful solver; position not near a boundary; point rank=2; relative Frobenius change ≤5% between Hessians at 0.002 and 0.004; and positive-definite `H`, `B`, and `C_sand` with minimum/maximum eigenvalue ratio >1e-10. Do not use a pseudoinverse to hide rank deficiency. This calculation does not differentiate through IRLS-weight updates, guarantee that two IRLS iterations converged, or include correlations from shared references. About 10 exposures are few clusters; neither p-values nor CR1p guarantee finite-sample validity. Store total score, total score norm, scalar-vs-residual-Jacobian error, Hessian, meat, every score, and each unsupported reason. Do not add a χ² factor to sandwich covariance; GN and profile-H retain the frozen candidate's `max(1, reduced χ²)` rule, which must be stated when interpreting differences.

To inspect modes without changing the fitted position, after fitting rerun the five starts on the **target with final weights fixed**, without updating IRLS; store chi-square, solutions, number of modes separated by >0.15 sky pixels, start failures, and cases where a fixed solution has chi-square lower than the candidate point by more than 1e-4. These are final diagnostics; they do not replace the point estimator or turn the result into a new full-IRLS fit.

## Cases and denominators

Use fields `w350p35`, `w090p10`, and `w210m20`, patch 1, in two cases: stationary at SNR 2/frame and moving by `[0.6, 0.05]` sky pixels at SNR 4/frame. Truth retains the frozen nearest `source_image`, while the model uses the padded target: this is a known mismatch, not physical-PSF validation. Injected sources retain the per-exposure amplitude from `injected_frames`; no source shot noise is added.

Each case has **128 new Gaussian noise draws** using the original native variance and a separate seed per field/case. The seed is the first 64 bits, big-endian, of SHA-256 over `sandwich-development.1|field|integer_snr|motion_components`, where motion components use `.8g` formatting and are comma-separated; the design stores the seed as a decimal string to preserve all 64 bits. These seeds differ from the earlier seed `20261030`; within each draw, GN, H, and sandwich use the same point fit and same noise. The same field/exposure still represents only three already opened sky geometries, not 768 independent fields. In addition, six original-background source-injection checks are kept separate from the 128 Gaussian draws for each case.

Vector error is fitted displacement minus truth, transformed to east/north arcseconds. Report separately for each method:

1. `centroid_only`: total covariance from the two epoch fits, matching the conditional generator with registration offsets held fixed.
2. `plus_registration`: add frozen registration covariance for comparison with the older pipeline. The generator does not create registration-error realizations; do not call this branch nominal total coverage or registration-error validation.

For each field/case, retain every attempt, numeric/accepted point fit, rank, boundary, mode, failure, and method-specific support status. Report all attempts, numeric, accepted, common-supported, and common-accepted separately; for every subset, also record the denominator that actually has covariance ellipses. Record vector bias, RMS/P90 error for every numeric fit in the subset, 50/68/95% ellipses using χ²₂ thresholds 1.386294361, 2.278868566, and 5.991464547, truth counts, denominators, and 95% Wilson intervals for each case. These intervals measure Monte Carlo draw uncertainty within a case; they do not imply field independence or guarantee ellipse validity. Record median 68% ellipse area and median/P90 major semiaxis. Report unsupported/reasons by method and failed fits/modes; do not remove failures from the attempt denominator.

## Lock and run after review

```powershell
.venv/Scripts/python.exe -m unittest tests.test_exposure_sandwich -v
.venv/Scripts/python.exe -m scripts.run_sandwich_study --design
# After committing the hashed source, tests, documentation, and design:
.venv/Scripts/python.exe -m scripts.run_sandwich_study --run
# Cases can be resumed separately:
.venv/Scripts/python.exe -m scripts.run_sandwich_study --run --fields w350p35 --snrs 2
```

The design hashes code, tests, documentation, requirements, frozen sources, design/opened product, and baseline cache; `--design` refuses to overwrite. `--run` refuses to proceed if the design or source is not committed at HEAD, hashes differ, or a completed result already exists. The only output is Git-ignored `data/raw/benchmark/sandwich-development.json`, checkpointed after each draw. Resume regenerates the RNG stream from the beginning and checks draw continuity. No data are run while creating the design. Six cases × 128 draws require 768 paired fits plus six original-background cases; final mode diagnostics add five solves per epoch using fixed weights. There is no empirical runtime benchmark; monitor time/memory and use resume rather than promising a runtime.

This experiment may show undercoverage or overly large ellipses; both must be reported. Only an independently preregistered study with appropriate PSF/SED/noise/registration and unopened fields can support consideration of promotion.
