# Fixed-Weight Profile Diagnostic

*English translation of the hash-locked original protocol, [PROFILE_LANDSCAPE_PROTOCOL.md](PROFILE_LANDSCAPE_PROTOCOL.md). The original remains the canonical source used by the scientific evidence manifests; this translation is provided for readability.*

Version 0.10.0-profile-landscape.1 was locked before any new sampling. This is a post hoc diagnostic of the failed ePSF gate, not an independent validation set or an opportunity to change the old gate. Earlier results and sealed ePSF coefficients remain unchanged: no new positions are fit, Huber weights updated, covariance adjusted, or detection thresholds changed.

## Question and sample

Two cells at 2025W46_2A_0214_3, for Gaia stars 5756942110218608640 and 5756958431094222592, changed from one to two near-best solution groups after the ePSF correction. Groups are formed from nine starts, a separation of 0.15 common pixels, and a cost difference of 5.991. This rule does not establish that two physical minima exist. The solver may stop because the cost change or position step is small; a success status does not guarantee a small gradient or a global minimum.

Retain all 14 original training IDs, including stars without a fit. Use only the two exposures already included in calibration: 2025W46_2A_0214_2 and _3. There are four branches per cell: original/corrected ePSF × final Huber weights from original/corrected fits, for 112 planned branches. Record all preparation and profile errors. If either side of a pair is missing, the paired comparison is unavailable; it is neither a negative result nor a row to remove. The two stars rejected by the gate are identified as a sample selected after viewing the results; the other stars are descriptive controls from the same field.

Keep native pixels, VARIANCE, mask, pixel area, Gaia/registration, neighbors, tilted-plane background, and common ±2.5-pixel bounds fixed. Solve signed Jy flux coefficients and background linearly at each fixed position. Read and swap the two weight vectors; do not re-estimate them. Apply the ePSF correction to both target and neighbors. For a branch using ePSF and weights from the same family, recheck the saved-point cost and every successful final start with rtol=atol=1e−10 before the diagnostic. A mismatch makes the branch fail; do not silently repair it.

## Locked quantities

- A full-domain 51 × 51 grid over the common anchor ±2.5 pixels, with 0.1-pixel spacing.
- For the two focus stars, a 21 × 21 grid with 0.2-pixel radius and 0.02-pixel spacing around every near-best candidate whose coordinates are not exactly those of the two saved fit families. Record out-of-domain cells as missing; do not clip positions or recenter the grid.
- Probe the fitted point and every successful final start from both fit families. Merge only identical coordinates, retaining all origins. Use central finite differences at common fixed steps of 0.004 / 0.002 / 0.001 pixel; a stencil crossing a boundary is unavailable.
- Cost is F = rᵀr, with residuals normalized by the original error and multiplied by the square root of the weight. This is twice SciPy's cost convention.
- Keep separate: the residual-derived gradient 2Jᵀr, the direct finite-difference gradient of F, the finite-difference Hessian of F, and the Gauss–Newton matrix 2JᵀJ. Also retain eigenvalues, column norms of J, and rank of column-scaled J using singular-value ratio 1e−10. Do not invert the Hessian into a covariance or set a stationarity pass threshold after seeing results.
- Count 4- and 8-connected components on the **grid itself** at levels F minus minimum of 0.1 / 1 / 2.3 / 5.991. Record node counts, boundary contact, and contact with missing nodes. These levels do not represent coverage or confidence.
- Use no RNG, network queries, new pixels, or position optimization. Split work into two shards ordered by source ID; each process requests one BLAS/OMP thread. This is an environment request, not a measurement of the actual thread count. Limit the template cache to 8,192 positions per cell/ePSF; it shares renders between the two weight branches and does not change the model or user-data cache.

## Seal and interpretation

The design contains hashes for new code/tests, this document, inherited scientific sources, sealed coefficients, the old gate, and digests of the original/corrected journals. Commit the design before running, and record the full commit SHA. The immutable journal contains all 112 keys; resume must not overwrite results. The assessment directory must be absent both before and after. The 252 corrected-assessment cells and 30 independent fields remain unopened.

Analytic tests cover a quadratic with known gradient/Hessian, a double well with a known cost barrier, a flat unidentifiable residual, an error node, and an out-of-bounds stencil. Runner tests confirm the complete sample, correct weight swaps, cost replay, no optimizer calls, no assessment access, and immutable resume.

A finite grid can miss a narrow valley or curved connecting path; finite-difference derivatives depend on step size and interpolation. Multiple sampled components do not prove multiple minima, and one component does not rule them out. Fixed Huber weights are conditional on the image and are not a calibrated likelihood; nuisance parameters, registration, catalog, PSF, and correlated-noise limitations remain. Even if this diagnostic indicates an early solver stop, the old gate must not be changed to a pass. Any subsequent solver or screening change needs a new version, tests, and protocol before use on an unopened set.

Method sources: [SciPy least_squares 1.17](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.optimize.least_squares.html) documents stopping criteria and success; the project environment uses SciPy 1.17.1. [O'Leary and Rust, NIST](https://www.nist.gov/publications/variable-projection-nonlinear-least-squares-problems) describes variable projection for problems with both linear and nonlinear parameters. Keeping linear nuisance parameters fixed here is a diagnostic of the current problem, not confirmation that the optical model is correct.
