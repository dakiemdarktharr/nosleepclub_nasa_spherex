# Fixed-Weight Profile Diagnostic

Version `0.10.0-profile-landscape.1`, locked before any new sampling. This is a post hoc diagnostic of the failed ePSF gate, not an independent validation set or an opportunity to change the old gate. Earlier results and sealed ePSF coefficients remain unchanged; no new positions are fit, Huber weights updated, covariance adjusted, or detection thresholds changed.

## Question and sample

Two cells at `2025W46_2A_0214_3` for Gaia stars `5756942110218608640` and `5756958431094222592` changed from one to two near-best solution groups after the ePSF correction. Groups are formed from nine starts, a separation of 0.15 common pixels, and a cost difference of 5.991. This rule does not establish that two physical minima exist. The solver may stop because the cost change or position step is small; a success status does not guarantee a small gradient or a global minimum.

Retain all 14 original training IDs, including stars without a fit. Use only the two exposures already included in calibration: `2025W46_2A_0214_2` and `_3`. Four branches per cell: original/corrected ePSF × final Huber weights from original/corrected fits. There are 112 planned branches. Record all preparation and profile errors; if either side of a pair is missing, the paired comparison is unavailable, not a negative result or a row to remove. The two stars rejected by the gate are identified as a sample selected after viewing the results; other stars are descriptive controls from the same field.

Keep native pixels, VARIANCE, mask, pixel area, Gaia/registration, neighbors, sloped plane background, and ±2.5 common-pixel bounds fixed. At every fixed position, solve signed Jy flux coefficients and background coefficients linearly. Read and swap the two saved weight vectors without re-estimating them. Apply the ePSF correction to both target and neighbors. For branches with matching ePSF/weight families, recheck the saved point and all successful final starts with `rtol=atol=1e-10` before the diagnostic. Any mismatch fails the branch; do not repair it silently.

## Locked quantities

- Full-domain grid: 51 × 51 over anchor ±2.5 common pixels, at 0.1-pixel spacing.
- For the two focus stars, a 21 × 21 grid with radius 0.2 pixels and 0.02-pixel spacing around every near-best candidate that differs from the exact coordinates of the two saved fit families. Record out-of-domain points as missing; do not clip positions or shift grid centers.
- Probe the fit point and every successful final start from both families. Deduplicate only exactly identical coordinates and retain all origins. Central finite differences use three fixed steps: 0.004 / 0.002 / 0.001 common pixels; stencils that cross a boundary are unavailable.
- Cost is `F=rᵀr`, with residuals normalized by original errors and multiplied by square-root weights. This is twice SciPy's `cost` convention.
- Keep separate the residual gradient `2Jᵀr`, direct finite-difference gradient of F, direct finite-difference Hessian of F, and Gauss–Newton `2JᵀJ`, along with eigenvalues, J column norms, and column-scaled J rank using singular-value ratio `1e-10`. Do not invert the Hessian into covariance or set a stationarity threshold after viewing results.
- Count 4- and 8-neighbor connected components at F levels relative to the minimum **on that grid** of 0.1 / 1 / 2.3 / 5.991. Record node counts, boundary contact, and contact with missing nodes. These levels do not represent coverage or confidence.
- No RNG, network queries, new pixels, or position optimization. Two shards follow source-ID order; each process requests one BLAS/OMP thread. This is an environment request, not a measurement of actual thread count. Template cache is limited to 8,192 positions per cell/ePSF and only shares renders across the two weight branches; it does not change the model or user-data cache.

## Seal and interpretation

The design contains hashes for new code, tests, this document, inherited science sources, sealed coefficients, the old gate, and original/corrected journal digests. Commit the design before running, using the full SHA. The immutable journal contains all 112 keys; resume must not overwrite results. The assessment directory must be absent before and after. The 252 corrected assessment cells and 30 independent fields remain unopened.

Analytic tests cover a quadratic with known gradient/Hessian, a double well with known cost barrier, an unidentifiable flat residual, error nodes, and out-of-bound stencils. Runner tests verify complete sample counts, correct weight swapping, cost replay, no optimizer calls, no assessment access, and immutable resume.

A finite grid may miss a narrow valley or curved connecting path; finite derivatives depend on step and interpolation. Multiple sampled components do not prove multiple minima, and one component does not rule them out. Fixed Huber weights are conditional on the image, not a calibrated likelihood; nuisance terms, registration, catalogs, PSF, and correlated noise retain their stated limitations. Even if the diagnostic indicates early solver termination, the old gate must not be changed to pass. Any next solver or screening changes require a new version, tests, and protocol before use on unopened data.

Method references: [SciPy least_squares 1.17](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.optimize.least_squares.html) documents stopping criteria and success; the project pins SciPy 1.17.1. [O'Leary and Rust, NIST](https://www.nist.gov/publications/variable-projection-nonlinear-least-squares-problems) describe variable projection for problems with both linear and nonlinear parameters. Keeping linear nuisance terms fixed here is a diagnostic of the current problem, not confirmation that the optical model is correct.
