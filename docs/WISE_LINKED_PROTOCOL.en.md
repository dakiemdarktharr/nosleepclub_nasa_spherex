# WISE 0855: Independent Flux and Spectrally Constrained Flux Controls

*English translation of the hash-locked original protocol, [WISE_LINKED_PROTOCOL.md](WISE_LINKED_PROTOCOL.md). The original remains the canonical source used by the scientific evidence manifests; this translation is provided for readability.*

This is a development experiment on **20 opened wide-field QR2 cutouts**, not a new validation or replacement of the reported measurement. Broad uses 10 exposures per epoch; strict uses two per epoch and is a subset of broad. The two configurations are not counted as 24 independent exposures. Code and inputs were locked before the new point-model run. WISE data and the old measured position had already been examined in earlier studies, so this is not an out-of-sample test.

## Hypothesis and controls

Fit around anchor sky grid (31.5, 31.5), with ±2.5-pixel bounds. Each epoch has its own position and free flux. The independent control has a separate Jy flux for each frame. The prespecified shared_r7_68_a0 candidate has one Jy amplitude per epoch multiplied by the PRISM spectral ratio. The comparison isolates the effect of reducing nuisance flux parameters; do not choose a candidate by proximity to a published vector or smaller covariance.

Both use the same pixels/mask, renderer, neighbor/background span, and frozen Gaia offset. The renderer uses the exact source WCS, QR3 ePSF zero-padded by 16, normalization over the full native lattice before masking, and source Ω computed from celestial WCS (2/4 subdivisions, refinement diagnostic ≤1e−4). This is a geometric center-Ω approximation, not evidence of exact SAPM binding or color calibration. The old nuisance model retains the plane and fixed-position/fixed-shape neighbors; only the linear span is reused. IMAGE−ZODI−scalar is retained; the fitted constant absorbs the scalar. SOURCE flags are allowed in the target mask; units and pixel ordering are checked explicitly.

The new control also changes WCS/normalization and may change the mask relative to the old estimator. Therefore, it is not described as a byte-identical replay of measurements 0.3/0.10.

## Seven prespecified variants, each run on broad and strict

1. Independent: separate flux in every frame, without a spectral ratio.
2. shared_r7_68_a0: primary candidate, 68-channel Cent, R7 center, α=0.
3. tilt_r7_68_a0: adds one shared spectral-slope nuisance per epoch, pivot 4.75 µm, scale 0.20 µm. With two frames at two distinct wavelengths, this flux basis may be exactly equivalent to the independent branch; this is an algebraic sanity check, not a third confirmation.
4. shared_r7_68_am4: same candidate with α=−4.
5. shared_r7_68_ap4: same candidate with α=+4.
6. shared_qr2_68_a0: use the center from QR2 CWAVE instead of the R7 center.
7. shared_r7_17_a0: use 17-channel Cent instead of 68.

PRISM is a separate MAST spectrum pipeline; do not combine it with G395M, scale Spitzer, or deconvolve the LSF. Shift Cent response from the CSV center to the center of the pixel nearest the anchor; do not rescale its width or integrate the response over the PSF footprint. The R7 channel map uses SKY directly; BC/BW use DEVICE, so these two maps alone require an x flip for D6. Every pixel map has its own HDU header/provenance; do not flip the entire package.

The assumed convention is photon-weighted Fν with reference Fν(λ)/Fν(λlocal)=(λ/λlocal)^α; **this has not been verified as the SPHEREx calibration convention**. If any absolute-response support is missing, refuse to prepare that branch; do not extrapolate or drop frames to improve the fit. The coefficient ratio divides by a fixed 0.0005 Jy for both epochs; this only changes the amplitude parameterization A and does not set A from JWST. Prepare each epoch separately; a failure in one epoch does not block fitting the other. The ratio is fixed at the anchor; response is not differentiated with respect to the fitted source position.

## Solver, modes, and uncertainty

Use five starts: the anchor and (±0.7, 0)/(0, ±0.7). Select the successful solver result with the smallest χ². Profile linear parameters with column-scaled SVD; do not use a pseudoinverse to hide rank deficiency. Huber threshold 2.5 uses the **original** residual/error and updates whitening and nuisance projection for at most 20 iterations. After at least two iterations, require position change ≤1e−4 pixel and next maximum weight change ≤1e−3. A nonconverged run retains its point and denominator but does not pass numerical screening.

Rerun all five starts using the final fixed weights, without updating IRLS or silently replacing the point estimate. Save modes more than 0.15 pixel apart, modes with χ² better than the selected point by >1e−4, and modes within Δχ²≤5.991 of the best. This is a heuristic for detecting competing solutions, with no likelihood-coverage guarantee.

Save GN and observed profile-H at steps 0.002/0.004 pixel; H is supported only if it is positive definite/full-rank and its relative change is ≤5%. Do not multiply by reduced χ². Covariance is **conditional centroid-only** on final weights and diagonal noise; it omits common registration, ePSF/SED/response/neighbor uncertainty, source variability, and calibration. Solver screening is not scientific validation. When adding the two epoch covariances, assume zero cross-epoch centroid covariance conditionally; this is not a complete error budget or an independent check of the epochs. Do not clip negative amplitudes or interpret fixed-position S/N as a detection probability.

## Denominator and limitations

Two configurations × seven variants × two epochs = **28 attempts**. Checkpoint after each epoch; retain failures and all starts/modes, along with native x/y, error, ePSF zone, mask selection, provenance, and Ω at the solution. Preparation failures are recorded for the affected configuration/epoch attempts; do not drop frames. A global hash/protocol/runtime/data-contract failure stops the whole run. Report every vector and its change from the control when both epochs have a point; the change is model sensitivity, not bias or accuracy. There is no independent truth for reporting RMS/coverage from a single object.

The model still uses one position per season and omits motion/parallax across the few-day interval; the Gaia offset is fixed and its covariance is not propagated. The assumed 2023 source spectrum may be wrong for 2025–2026; α sensitivity does not span calibration, variability, or LSF uncertainty. Do not promote the candidate or switch the default, even if it appears better. Next steps require real controls/alternative PSFs, appropriate noise, a time model, and separate calibration before opening 30 new fields.

    .venv/Scripts/python.exe -B -m unittest tests.test_linked_epoch_model tests.test_wise_linked_inputs -v
    .venv/Scripts/python.exe -B -m scripts.run_wise_linked_study --design
    # Commit all source/test/protocol/design inputs, then run:
    .venv/Scripts/python.exe -B -m scripts.run_wise_linked_study --run --configurations broad --variants independent
    .venv/Scripts/python.exe -B -m scripts.run_wise_linked_study --run

The design command hashes inputs only; it does not calculate coefficients or run fits. The run command checks design, source/metadata against Git HEAD, raw hashes, and then runs. It does not overwrite a completed study. The runner holds an OS lock for the command; process termination releases the lock, and a remaining lock file does not by itself prove a job is still running. Checkpoints are atomic and each attempt has a checksum. Resume checks runtime/package pins and checksums without mixing environments. Only one runner writes at a time. Resume skips recorded attempts, including failures; do not rerun difficult cases or change the protocol after seeing point estimates to improve results. Raw output is ignored by Git.
