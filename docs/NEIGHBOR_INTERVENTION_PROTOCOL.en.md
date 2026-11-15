# Locked Experiment: Blended Sources, Background, and ePSF on Opened Data

*English translation of the hash-locked original protocol, [NEIGHBOR_INTERVENTION_PROTOCOL.md](NEIGHBOR_INTERVENTION_PROTOCOL.md). The original remains the canonical source used by the scientific evidence manifests; this translation is provided for readability.*

This is a development step after study cfb9d6a. **It does not open a new field or replace the default WISE measurement.** The preceding study had two competing solutions in the later strict epoch. Replay described their relationship to the nuisance span but did not identify the cause. This experiment changes one factor at a time on the same pixels to measure sensitivity and evaluate the constraint with synthetic-truth controls. Models are not selected by proximity to a published vector or by a smaller ellipse.

## Prespecified question and factorial design

Reuse the 20 opened wide-field QR2 cutouts, Gaia offsets, SOURCE-only mask, error map, anchor sky grid (31.5, 31.5), catalog/IDs, and opened neighbor ordering. Broad uses 10 images per epoch; strict uses two and is a subset of broad. Each frame has a **free signed target flux**, its own background, and its own neighbor fluxes. PRISM and reference color are not used to constrain the target in this experiment.

There are three factors, forming a complete 2×2×2 factorial with eight branches, two epochs, and two image configurations: **32 attempts**.

1. A plane background [1,x,y] or quadratic background [1,x,y,x²,xy,y²], using native x/y divided by the 6-pixel radius as in the earlier sample. “Plane” includes a gradient; it is not a constant-only background. The data retain IMAGE−ZODI−scalar; the fitted constant absorbs the scalar. Bias from subtracting the ZODI model has not been checked.
2. A spatial nearest-neighbor or bilinear ePSF from four raw tables, with each table normalized before interpolation. The target shape stays at the anchor; neighbor shapes stay at catalog positions. Shape is not differentiated with respect to fitted position. Positions outside the center grid are clamped to the edge and flagged; no new calibration is simulated.
3. Neighbor fluxes indexed by ID and expressed in Jy, either signed or constrained nonnegative with NNLS. **The constraint applies only to physical-source columns**, not to SVD-mixed source/background columns. Target and background remain signed. The primary comparison is plane_nearest_free versus plane_nearest_nonnegative.

Neighbors are reconstructed with the native renderer, explicit units, exact source WCS, and normalization over the full lattice before masking. Therefore, the new free branch is a bridge control, not a byte-identical replay of the earlier fit. Only the nonnegative-versus-free contrast with the same shape and background isolates the effect of the constraint.

All sources use the calibrated, hash-locked, signed 33×33 ePSF sampled at 5× SKY resolution. Active WCS A is checked against QR2 D6 metadata; no D6 flip is added. Source solid angle Ω is geometric WCS area; exact SAPM binding has not been established. No correction is applied from the ePSF table's moment centroid. [IRSA guidance on using a new ePSF with older QR2 data](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/) does not validate the WISE residual/bias or the new interpolation used here.

## Solver, active constraints, and refusal criteria

Profile each frame with column-scaled SVD for the free component, then apply NNLS to the nonnegative neighbor component after projection. Check rank and condition over the full design (relative singular-value cutoff 1e−10) and scaled KKT at 1e−8. Do not drop weak columns, use a pseudoinverse, or clip a negative fitted solution after the fact. Save all coefficients by ID, original residual/error, weights, active mask, and optimality diagnostics.

Use nine Cartesian starting offsets at −1.5/0/+1.5 pixels within anchor±2.5 bounds. Select the successful solver result with the lowest cost and retain each start's failure. Huber threshold is 2.5 based on the original residual/error, for at most 20 updates. After at least two updates, require the next maximum weight change to be ≤0.001 and maximum position change to be ≤1e−4 pixel.

Then audit all nine starts again using the final fixed weights and retain the selected point. Cluster solutions more than 0.15 pixel apart; record modes with Δχ²≤5.991 and any solution with a point estimate better by more than 1e−4. These thresholds are heuristics; likelihood coverage for robust constrained fits has not been established. Multiple modes, a better point, boundary contact, rank failure, nonconvergence, or final-start failure are numerical refusals.

Do not return covariance, ellipses, S/N, or detection probability. Active constraints make inference at the boundary different from unconstrained least squares; inverse curvature cannot be used to claim calibration. One position per epoch still omits within-season motion/parallax and shared alignment uncertainty. These issues must be resolved before out-of-sample scientific use.

## Independent PSF control and conditional source Poisson noise

Use only the strict configuration's opened geometry: four frames. Two target fluxes (300/600 µJy) × two true background models (plane/quadratic) × **16 noise draws per case** produce 64 independently seeded scenes on the same geometry. The two primary branches and two epochs yield **256 control attempts**, for **288 attempts total** in the study. Draws on one geometry are not independent sky fields.

The target truth starts at (31.73, 31.31) and is displaced by (+0.55, +0.08) sky pixels. The target Gaussian has native σ (0.55, 0.70); a neighbor has (0.70, 0.60). Neighbor fluxes follow a fixed order at 150/(1+i) µJy. Integrate the Gaussian over each pixel using the CDF, without using the ePSF or window normalization. Save each pixel's Ω and the flux missing outside the window. This is a synthetic PSF family different from the fitter; it is neither a measured instrument PSF nor a WISE spectrum.

The deterministic background has plane coefficients (0.04, 0.015, −0.01) MJy/sr. The quadratic case adds (0.025, 0.020, −0.015) for x²/xy/y². Independent Gaussian background noise uses the original VARIANCE as its error scale; **do not add noise again to an already noisy image**, and do not call this an injection onto the real sky. The original VARIANCE is conditional on the original processing and may already include photon noise from real sources and processing components. It therefore does not establish that the Gaussian scale contains only sky/read noise, or that the added synthetic-source Poisson variance avoids double-counting a physical source component. This is an empirical noise-scale/oracle stress control; it does not cleanly separate detector-noise and covariance budgets.

The complete positive scene (target + neighbors) receives an ideal source-Poisson ramp from the OLS-checked module, using the actual gain with matching UUID/hash, active-pixel mapping, and nominal timing header. Gain/history/units are checked; a bad pixel gain makes the whole epoch fail and is not dropped to preserve the sample. Orientation is based on public R6 and has not been proven correct for the private patch. Poisson/background/noise remain control assumptions. The fitter uses the **oracle** sqrt(original variance + known expected-source variance); this is not presented as an observed-data uncertainty estimator.

RNG is PCG64/SeedSequence [20261031, case_index, draw, epoch_index, frame_index]; both branches receive exactly the same data/error. Resume must match the realization hash of the saved branch. Save expected/noise/variance/gain/Ω, RNG states, input hashes, and every attempt, including preparation and fit failures.

Prespecified outputs: counts over all attempts; vector error/RMS for every completed pair, commonly completed pairs, and commonly numerically supported pairs; counts of negative target fluxes, bound neighbors, modes, and failures. Keep the four cases separate; do not pool them to hide a difficult case. This is a 16-draw-per-case pilot, insufficient across fields or parameter space to select a production model or calibrate coverage. Do not report coverage when covariance is unavailable. Do not promote a model even if one contrast appears better.

## Locking and reproduction

The design hashes rules/source/tests/previously opened products/raw inputs, as well as the new gain/lookup used by the control. The inventory inherits the previous study's spectral archives for lineage auditing; those archives do not impose flux constraints in this new study. Commit everything before any real-data fit or control draw. Checkpoints checksum each record and use an OS lock, atomic writes, and pinned runtime/packages. Resume must not rerun a terminal failure or overwrite a completed study. Do not change locked sources to rescue a case after looking at the data.

The new CLI requires OpenBLAS/OMP/MKL/BLIS/vecLib thread variables to be set to 1 before importing NumPy/Astropy, only inside the CLI process. Importing it as a library does not change the caller's environment. Required values are recorded in runtime metadata; this is not an independent measurement of the threads actually used by every backend.

    .venv/Scripts/python.exe -B -m unittest tests.test_constrained_linear_profile tests.test_neighbor_epoch_model tests.test_neighbor_intervention_inputs tests.test_independent_scene_control tests.test_neighbor_intervention_study -v
    .venv/Scripts/python.exe -B -m scripts.run_neighbor_intervention --design
    # Commit source/tests/protocol/design first:
    .venv/Scripts/python.exe -B -m scripts.run_neighbor_intervention --run --sections real
    .venv/Scripts/python.exe -B -m scripts.run_neighbor_intervention --run --sections controls

This is not the protocol for 12 calibration / 12 validation / 6 final holdout fields. After the results, identify degenerate/abstention regions, check stellar PSFs and the time model, then lock the evaluator, power, absolute gate, and overlap before opening 30 fields.
