# Locked Blend, Background, and ePSF Experiment on Opened Data

This is a development step after study `cfb9d6a`; **no new field is opened** and the default WISE measurement is unchanged. The previous study had two competing solutions in the later strict epoch. Replay described their relation to the nuisance span but did not identify the cause. The new experiment changes factors on the same pixels to measure sensitivity and evaluate constraints against synthetic-truth controls. Do not select a model because it is closer to a published vector or has a smaller ellipse.

## Questions and prespecified factorial design

Reuse the 20 wide-field QR2 cutouts, Gaia offsets, SOURCE-only mask, errors, sky-grid anchor `(31.5, 31.5)`, catalog/IDs, and opened neighbor order. Broad uses 10 images per epoch; strict uses two and is a subset of broad. Each frame has a **free signed** target flux, background, and separate neighbor fluxes; PRISM/reference color is not used to constrain the target in this experiment.

Three factors give 2×2×2 = eight branches, across two epochs and two image sets: **32 attempts**.

1. Plane background `[1,x,y]` or quadratic `[1,x,y,x²,xy,y²]`, with native x/y divided by the 6-pixel radius as in the old sample. “Plane” includes gradients; it is not only a constant. Data remain IMAGE−ZODI−scalar; the fitted constant absorbs the scalar, but bias from the subtracted ZODI model is not tested.
2. Nearest or bilinear spatial ePSF interpolation from four raw tables, normalizing each table separately before mixing. Keep target shape at the anchor and neighbors at catalog positions; do not differentiate shape by fitted position. Clamp outside the grid center and record a flag; do not simulate a new calibration.
3. Neighbor fluxes are identified by ID and measured in Jy. Allow signed values or impose nonnegative values with NNLS. **Apply constraints only to physical source columns**, not to SVD-mixed source/background columns; target/background remain signed. The main comparison is `plane_nearest_free` versus `plane_nearest_nonnegative`.

Neighbors are rebuilt with a native renderer using units, exact source WCS, and normalization across the full lattice before masking. Therefore the new free branch is a bridge control, not a byte-identical replay of the old fit. Only the nonnegative/free contrast with the same shape/background isolates the constraint effect.

All sources use the hashed calibration's signed 5×, 33×33 SKY ePSF. Active WCS A was checked against QR2 D6 metadata; do not add another D6 flip. Source Ω is the geometric WCS area; exact SAPM binding is not available. Do not apply a correction derived from the ePSF-table moment centroid. [IRSA recommends the new ePSF for older QR2 images](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/); that recommendation does not validate WISE residual/bias or this new interpolation.

## Solver, active constraints, and refusal reasons

Profile each frame with column-scaled SVD for free parameters, followed by NNLS for nonnegative neighbors after projection. Check rank/conditioning of the full design (relative singular-value cutoff 1e−10) and scaled KKT at 1e−8. Do not drop weak columns, use a pseudoinverse, or clip a negative fitted solution afterward. Save coefficients by ID, original residual/error, weights, active mask, and optimality diagnostics.

Use nine Cartesian starts at offsets −1.5/0/+1.5 pixels within anchor±2.5. Select the lowest-cost successful solver result and retain every start failure. Huber 2.5 uses original residual/error for at most 20 updates. After at least two updates, require next maximum weight change≤0.001 and position maximum change≤1e−4 pixel. Then audit all nine starts again with the final weights fixed, retaining the selected point. Cluster solutions separated by >0.15 pixel; record modes with Δχ²≤5.991 and any solution better than the selected point by >1e−4. These are heuristics; there is no likelihood coverage for this robust constrained fit. Multiple modes, a better point, boundary, rank failure, nonconvergence, and final-start failure are numerical refusals.

Do not report covariance, ellipse, S/N, or detection probability. Active constraints change boundary inference relative to free least squares; do not claim calibration by inverting curvature. One position per epoch still omits within-season motion/parallax and shared alignment uncertainty. These issues remain before out-of-sample science.

## Independent PSF control and conditional source Poisson noise

Use only strict geometry and four already opened frames. Two target fluxes 300/600 µJy × two background truths (plane/quadratic) × **16 noise draws per case** produce 64 independently seeded scenes on the same geometry. Two primary branches and two epochs give **256 control attempts**, for **288 attempts** total. Draws on one geometry are not independent sky fields.

Truth target before `(31.73, 31.31)`, displacement after `(+0.55, +0.08)` sky pixel. Target Gaussian σ native `(0.55, 0.70)`, neighbor `(0.70, 0.60)`; neighbor flux in fixed order is 150/(1+i) µJy. Integrate the Gaussian over each pixel using the CDF; do not use ePSF or window normalization. Save each pixel's Ω and flux missing outside the window. This is a synthetic PSF family different from the fitter, not a measured instrument PSF or WISE spectrum.

Deterministic background has plane coefficients in MJy/sr `(0.04, 0.015, −0.01)`. The quadratic case adds `(0.025, 0.020, −0.015)` for x²/xy/y². Independent Gaussian background noise uses original VARIANCE as its error scale; **do not add noise again to an already noisy image** and do not call this an injection into the real sky. VARIANCE is conditional on original processing and may already include photon noise from real sources and other processing components. This does not prove that the Gaussian scale contains only sky/read noise, or that synthetic-source Poisson variance avoids physically double-counting a component. This is an empirical-noise-scale/oracle stress control; it does not cleanly separate detector-noise/covariance budgets.

The full positive scene (target + neighbors) gets an ideal source Poisson ramp from the OLS-checked module, with real gain bound to the same UUID/hash, active-pixel mapping, and nominal timing header. Gain/history/units are checked; a bad pixel gain fails the epoch and is not dropped to rescue the sample. Orientation is based on public R6 and has not been proven for the private patch; Poisson/background/noise remain control assumptions. The fitter receives oracle `sqrt(original variance + known expected-source variance)`; this is not presented as an observed-data uncertainty estimator.

RNG is PCG64/SeedSequence `[20261031,case_index,draw,epoch_index,frame_index]`; both branches receive identical data/errors. Resume must match realization hashes against saved branches. Save expected/noise/variance/gain/Ω, RNG states, input hashes, and every attempt, including preparation/fit failures.

Prespecified outputs: counts across all attempts; displacement errors/RMS for every completed pair, common-completed pairs, and common numerically supported pairs; negative target flux counts, neighbor bounds, modes, and failures. Keep all four cases separate; do not pool to hide a difficult case. This is a 16-draw-per-case pilot, insufficient for production-model selection or coverage calibration; do not report coverage without covariance. Do not promote a model even if a contrast looks better.

## Lock and reproduction

Design hashes rules/source/tests/previous opened products/raw inputs and the new gain/lookup used for controls. Inventory inherits the previous study's spectral archive for lineage auditing; those archives do not constrain flux in this study. Commit everything before any real-fit or control draw. Checkpoints include per-record checksums, OS lock, atomic writes, and runtime/package pins; resume must not rerun terminal failures or overwrite a completed study. Do not edit locked sources to rescue cases after seeing data.

The new CLI requires OpenBLAS/OMP/MKL/BLIS/vecLib thread variables to be set to 1 before importing NumPy/Astropy, only within the CLI process; importing as a library does not change the caller's environment. Requested values are saved in runtime metadata; actual thread use by every backend is not independently measured.

```powershell
.venv/Scripts/python.exe -B -m unittest tests.test_constrained_linear_profile tests.test_neighbor_epoch_model tests.test_neighbor_intervention_inputs tests.test_independent_scene_control tests.test_neighbor_intervention_study -v
.venv/Scripts/python.exe -B -m scripts.run_neighbor_intervention --design
# Commit source/tests/protocol/design before the next commands:
.venv/Scripts/python.exe -B -m scripts.run_neighbor_intervention --run --sections real
.venv/Scripts/python.exe -B -m scripts.run_neighbor_intervention --run --sections controls
```

This is not a protocol for 12 calibration / 12 validation / 6 final holdout fields. After results, identify degeneracy/abstention regions, test real-star PSFs and a time model, then lock evaluator, power, absolute gates, and overlap before opening 30 fields.
