# WISE 0855: Independent-Flux and Spectrally Constrained-Flux Controls

This is a development experiment on **20 previously opened wide-field QR2 cutouts**, not new validation and not a replacement for the published measurement. Broad uses 10 exposures per epoch; strict uses two per epoch and is a subset of broad. Do not treat the configurations as 24 independent exposures. Code/inputs were locked before the new point-model run; WISE data and earlier measured positions had already been viewed in prior studies, so this is not an out-of-sample experiment.

## Hypothesis and control

Fit around sky-grid anchor `(31.5,31.5)` with ±2.5-pixel bounds; each epoch has its own free position and flux. Do not constrain position with the motion vector or flux with JWST absolute flux. The `independent` control uses a separate Jy flux per frame. The prespecified `shared_r7_68_a0` candidate uses one Jy amplitude per epoch multiplied by the PRISM spectral ratio. This comparison isolates the effect of reducing flux nuisance parameters; do not select a candidate based on proximity to a published vector or smaller covariance.

Both branches use the same pixels/mask, renderer, neighbor/background span, and frozen Gaia offsets. The renderer uses exact source WCS, QR3 ePSF zero-padded by 16, normalizes over the full native lattice at each phase before masking, and computes source Ω from celestial WCS (2/4 subdivisions, refinement diagnostic ≤1e−4). This is a geometric center-Ω approximation, not exact SAPM binding or color calibration evidence. Existing nuisance terms include a plane and neighbors with fixed positions/shapes; only the linear span is reused. Preserve IMAGE−ZODI−scalar; the fitted constant absorbs the scalar. The SOURCE flag is allowed in the target mask; units and pixel order are checked explicitly.

The new control also changes WCS/normalization and may change the mask relative to the old estimator. Therefore it is not a byte-identical replay of the earlier 0.3/0.10 measurement.

## Seven prespecified branches, both broad and strict

1. `independent`: separate flux per frame, no spectral ratio.
2. `shared_r7_68_a0`: primary candidate, Cent 68 channels, R7 center, α=0.
3. `tilt_r7_68_a0`: add a shared per-epoch spectral tilt nuisance, pivot 4.75 µm, scale 0.20 µm. With two strict frames at different wavelengths, this flux basis can be exactly equivalent to the independent branch; that is an algebraic sanity check, not a third confirmation.
4. `shared_r7_68_am4`: same candidate with α=−4.
5. `shared_r7_68_ap4`: same candidate with α=+4.
6. `shared_qr2_68_a0`: use the center from CWAVE QR2 instead of R7.
7. `shared_r7_17_a0`: Cent 17 channels instead of 68.

PRISM is a separate MAST pipeline spectrum; do not merge with G395M, scale by Spitzer, or deconvolve the LSF. Translate the Cent response from its CSV center to the pixel nearest the anchor; do not rescale width or integrate the response across the PSF footprint. The R7 channel map uses SKY directly, whereas BC/BW use DEVICE, so D6 flips x only for those two maps. Each pixel map has per-HDU header/provenance; do not flip the whole package.

Assumed convention is photon-weighted Fν with reference `Fν(λ)/Fν(λlocal)=(λ/λlocal)^α`; **this has not been verified as SPHEREx's calibration convention**. If any absolute response support is missing, refuse branch preparation; do not extrapolate or drop frames to improve a fit. Divide the coefficient ratio by fixed 0.0005 Jy in both epochs; this changes parameterization A and does not set A from JWST. Prepare separately by epoch; an error in one epoch does not block fitting the other. The ratio is fixed at the anchor; response is not differentiated by fitted source position.

## Solver, modes, and uncertainty

Use five starts: anchor and (±0.7,0)/(0,±0.7); choose the successful solver result with lowest χ². Profile linear terms with column-scaled SVD; do not use a pseudoinverse to conceal rank problems. Huber threshold 2.5 uses **original** residual/error to update whitening and nuisance projection, for at most 20 iterations. After at least two iterations, require position change ≤1e−4 pixel and next maximum weight change ≤1e−3. Nonconvergence remains in the denominator/records but does not pass numerical screening.

Rerun all five starts at fixed final weights, without IRLS updates or silently replacing the selected point. Save modes separated by >0.15 pixel, any mode with χ² better than the selected point by >1e−4, and modes within Δχ²≤5.991 of the best. This threshold is a heuristic for competing solutions, not a likelihood-coverage guarantee.

Save GN and observed profile-H at steps 0.002/0.004 pixel; H is supported only if PD/rank pass and relative change ≤5%. Do not multiply by reduced χ². Covariance is **conditional centroid-only**, based on final weights and diagonal noise; it excludes shared registration, ePSF/SED/response/neighbor uncertainty, source variability, and calibration. Solver screening is not scientific validation. When adding epoch covariances, cross-epoch centroid covariance is assumed zero conditionally; this is not a total error budget or an independent two-epoch check. Do not clip negative amplitudes or interpret fixed-position S/N as detection probability.

## Denominator and limitations

Two configurations × seven branches × two epochs = **28 attempts**. Checkpoint after each epoch and retain failures and all starts/modes with native x/y, errors, ePSF zone, mask selection, provenance, and Ω at the solution. Save preparation failures per configuration/epoch for the affected attempts; do not drop frames. A global hash/protocol/runtime or data-contract failure stops the full run. Report all vectors and changes from control when both epochs have a solution; these are model sensitivity, not bias or accuracy. There is no independent truth for RMS/coverage from one object.

One position per season still omits motion/parallax over days; Gaia offsets remain fixed and covariance is not propagated. A 2023 spectral assumption may not hold in 2025–2026; α sensitivity does not cover calibration, variability, or LSF. Do not promote or switch the default even if the candidate looks better. Next, use real controls/different PSF, suitable noise, a time model, and separate calibration before opening 30 new fields.

```powershell
.venv/Scripts/python.exe -B -m unittest tests.test_linked_epoch_model tests.test_wise_linked_inputs -v
.venv/Scripts/python.exe -B -m scripts.run_wise_linked_study --design
# Commit all source/tests/protocol/design before running:
.venv/Scripts/python.exe -B -m scripts.run_wise_linked_study --run --configurations broad --variants independent
.venv/Scripts/python.exe -B -m scripts.run_wise_linked_study --run
```

`--design` hashes inputs only; it does not compute coefficients/fits. `--run` checks design, source/metadata against Git HEAD, and raw hashes; it does not overwrite completed studies. The runner holds an OS lock throughout the command; process termination releases it, and a leftover lock file alone is not evidence of a live job. Checkpoints write atomically and each attempt has a checksum. Resume checks runtime/package pins and checksums; do not mix environments. Only one runner may write at a time. Resume skips recorded attempts, including failures; do not rerun difficult cases or change protocol after viewing a point to make results look better. Raw output is Git-ignored.
