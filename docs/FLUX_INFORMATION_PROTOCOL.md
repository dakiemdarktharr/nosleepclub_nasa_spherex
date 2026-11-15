# Flux-Information Diagnostic Protocol at the Truth Position

This is a conditional numerical experiment on already opened fields. It does not fit centroids, calculate positional RMS or coverage, validate astronomy, or select a production model. Run only after code, tests, documentation, and design are committed; `--run` checks the commit and hashes before reading a field. Do not change frozen code/products.

## Question and calculations

For each exposure, whiten by the original pixel errors and project out nuisance terms `Q`, comprising a flat background and fixed neighbor ePSFs. At the injected position, let the projected template be `p`, its derivatives along the two sky-pixel axes be `D`, `I = pᵀp`, `P = 1 − ppᵀ/I`, and the truth amplitude be `a`. Calculate and sum over exposures:

- Fisher information with amplitude profiled out: `F = Σ a² DᵀPD`.
- Fisher information if amplitude were known: `F_known = Σ a² DᵀD`.
- For a correctly matched Gaussian model, the expectation of the full profiled `JᵀJ`: `G = Σ (a² + 2/I) DᵀPD`.
- Covariance of the profile score under the same conditions: `V_score = Σ (a² + 1/I) DᵀPD`. The score has zero expectation; its distribution need not be Gaussian at finite SNR.

For each draw, fit an unconstrained linear amplitude at truth (negative values are allowed), with residual `r = âp − y` and `â = pᵀy/I`. The full Jacobian is `J = âPD − p(Dᵀr)/I`. Calculate `JᵀJ`, score `Jᵀr`, score quadratic `scoreᵀF⁻¹score`, `rᵀr`, and the Hessian of half the sum of squared residuals at steps of 0.002 and 0.004 sky pixels. Template derivatives use central differences at 0.00025 sky pixels; Fisher must be positive definite with minimum/maximum eigenvalue ratio > 1e-10. Finite-difference Hessians are considered stable if relative Frobenius change is ≤5%; this is a numerical-quality diagnostic, not an astronomical-discovery gate. Do not use IRLS or estimate/multiply by a reduced-chi-square factor. `Q` and weights are fixed at the original error map.

Residual degrees of freedom are `Σ(n_valid − rank(Q) − 1)`: subtract one free flux per exposure and do not subtract a centroid because none is fit. For a matched Gaussian model with fixed rank, `rᵀr` has expectation equal to the degrees of freedom; the score quadratic is not assumed to follow χ²(2) at finite SNR. `E[H_truth] = F` for a correctly matched model/projection and fixed weights, while `E[JᵀJ] = G`; do not infer from `G>F` that the Hessian or whole pipeline must under-cover. This formula follows from profile-residual algebra; [NIST on variable projection](https://www.nist.gov/publications/variable-projection-nonlinear-least-squares-problems) describes elimination of linear parameters.

## Data and regeneration

Use fields `w350p35`, `w090p10`, and `w210m20`, patch 1, SNR/frame 2 stationary and SNR/frame 4 moving by `[0.6, 0.05]` sky pixels; 64 draws per case, seed `20261030`, and the same before/after order, exposures, and native-array dimensions as the 0.10 Gaussian cache. One noise vector is shared by both conditions in each draw:

1. **Primary matched-padded:** on selected native pixels, the mean is exactly `a_i × p_padded(x_truth)` before whitening/projection. Reconstruct each exposure amplitude `a_i` from `injected_frames`: `SNR × sqrt(pinv(DᵀD)[0,0])`, where `D` is the original ePSF + plane design divided by error at truth. Do not estimate `a_i` from a fit or use a shared flux.
2. **Secondary old-nearest:** retain the mean from the frozen nearest `source_image` and use the same noise. Because the old truth differs from the padded template, the matched-model expectations above are not assumed to hold for this condition; differences are diagnostic of mismatch only.

Before the experiment, compare the injected image minus the original image against `source_image` reconstructed using `a_i`, and compare each sample's `error²` with native variance. For each draw, verify the noise at selected pixels against the generated RNG sample; store the maximum error and reject it if it exceeds tolerance. Samples retain the linear WCS, mask, neighbor positions, and candidate `Q`. Injected signal minus the original image contains no original background/sky source; synthetic pixel noise is independent Gaussian noise, with no source shot noise. No random registration offset is generated. Neighbor ePSFs still come from the frozen model, not real sky data.

## Predefined report and interpretation

Report each field/case and epoch separately: attempts/successes/failures and reasons, rank, amplitudes, truth-projected SNR, `F`, `F_known`, `G`, `V_score`, mean Hessian at each step, mean `JᵀJ`, χ² and degrees of freedom, mean score, and score covariance/quadratic. The matrix comparison statistic is `tr(F⁻¹M)/2`; for matched truth, `F` corresponds to 1 and `G` is the geometry-specific prediction. Use 2,000 bootstrap draw resamples with seed `20261031` for 95% intervals for mean trace and score. Bootstrap the same draw indices across two epochs; do not pool epochs or the six cases as independent fields. Retain every failed draw; if any failure occurs, do not report a CI as if the successful subset were an unselected random sample.

Lock interpretation before viewing results: for the primary condition, a 95% CI for mean `JᵀJ` trace above 1 is exploratory evidence of inflation relative to Fisher information; also compare this interval with the predicted trace `G`, and do not infer a misspecified mechanism merely because the interval excludes the prediction. For the Hessian, `[0.8, 1.2]` is a predefined approximate diagnostic tolerance for mean trace: a CI fully inside supports agreement at this precision, a CI fully outside indicates a difference under this criterion, and a CI crossing a boundary is inconclusive. This is not a formal equivalence test or production threshold; 12 epochs/case are multiple exploratory views and do not support simultaneous significance or generalization across three fields. Failure to reject the expectation does not prove a fully correct model. Report both Hessian steps, full matrices, and denominators.

## Operation

```powershell
.venv/Scripts/python.exe -m unittest tests.test_flux_information_probe -v
.venv/Scripts/python.exe -m scripts.run_flux_information_probe --design
# After review and committing all code, tests, documentation, and design:
.venv/Scripts/python.exe -m scripts.run_flux_information_probe --run
# Resume by field/case after committing:
.venv/Scripts/python.exe -m scripts.run_flux_information_probe --run --fields w350p35 --snrs 2
```

The design hashes all source files, tests, protocol, opened products, and both noise caches. `--design` refuses to overwrite and checks all 384 baseline-cache pairs against the candidate report. `--run` refuses to proceed if the design/source is uncommitted or hashes differ, and refuses to overwrite a completed result. Results are written only to Git-ignored `data/raw/benchmark/flux-information-development.json`, checkpointed after each draw, with resume support. One `w350p35` SNR 2 smoke test ran without writing output: setup took 7.52 seconds and one draw with two conditions/two epochs took 0.05 seconds on the current machine. This is not a 64-draw result. Estimated runtime is one to several minutes plus I/O; actual runtime depends on the machine.

Any study of fitted positions, IRLS, mode selection, physical mismatch, or empirical coverage must be designed and locked separately after this experiment.
