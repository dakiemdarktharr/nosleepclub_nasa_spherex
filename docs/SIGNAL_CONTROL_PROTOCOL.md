# Signal, Blend, Template, and Native-Phase Controls

Version `0.10.0-signal-controls.1`. Lock code, tests, seeds, attempt list, and thresholds below in Git before generating scenes/noise or fitting the experiment. This is intentional development on opened data, not sky validation.

## Question and data domain

Measure positional/flux bias and signal preservation for the two existing fitters when truth template, subpixel phase, and blend information vary. Do not relearn the PSF, change the solver, revise old gates, or select a model from these results.

Use only the geometry of two training stars, `5756942110218608640` and `5756958431094222592`, at the old exposure `2025W46_2A_0214_3`. Both were selected after the old gate failed; they are two stamps in **one** image/field selected from images. They are not independent fields. Before preparing inputs, the pipeline verifies parent protocol `704e3ef`, inherited journal/source, and coefficient seal. Three public parent artifacts (overview, audit, complete journal/checkpoint archive) are hash-bound and digest-checked before design or execution.

Keep selected pixels, mask, original VARIANCE, WCS, and old registration fixed. Replace IMAGE with a **synthetic scene**; do not add it to real noisy images or use real residuals as truth. Replace the original neighbor catalog with the specified controlled sources; do not silently retain real stars in the synthetic mean scene.

Target native center is `floor(registered Gaia center)` plus one of four phases: `(.25,.25), (.25,.75), (.75,.25), (.75,.75)`. The fitter search anchor remains the old Gaia position for every source-containing scene and does not know the injected location. Null cases use a common anchor transformed from the corresponding native phase; null has no source truth. A blend is offset `(+1.5,0)` native pixels from target and has the same flux. Use forward/inverse WCS with offsets for coordinate conversion and verify round trip to `1e-7` pixel. All biases/separations are measured in **native pixels**; do not multiply by the 6.15″ common-grid scale and call the result native.

## Locked factorial: 640 fits

| Component | Product | Fits |
|---|---|---:|
| Noiseless | 2 geometries × 2 truths × 4 phases × 3 scenes × 2 fluxes × 2 fitters | 192 |
| Noisy | 2 geometries × Gaussian truth × 2 phases × 3 scenes × 1 flux × 16 draws × 2 fitters | 384 |
| Null | 2 geometries × 2 phase anchors × 8 draws × 2 fitters | 64 |

Truth cases: (1) original nearest ePSF, matched to the model as a software check — an inverse crime that may contain negative wings; (2) positive pixel-integrated elliptical Gaussian with σ=(0.55,0.70) native pixel, rotated 25°. Gaussian is a different mathematical family from the fitter, not an independently measured SPHEREx PSF. The fitters are original nearest and nearest plus exactly the sealed shape vector, applied to current target and neighbor.

Three scenes: `isolated` has target only; `modeled` has a companion fit at its true position; `omitted` uses the same target+companion/image/noise as modeled but omits the companion column from the fitter. Omitted is a model-misspecification stress test, not a sample where fidelity is required despite intentionally missing a source. Do not select/drop it after seeing results.

Noiseless uses 600 and 1,200 µJy; noisy uses Gaussian truth only at 1,200 µJy, phases 0 and 3. Null has neither target nor companion; phase only specifies the corresponding anchor, with no source-truth position. All fitters retain signed target/neighbor flux, a plane background, nine starts, ±2.5 common-pixel bounds, and up to 20 IRLS iterations as locked in code.

## Normalization, background, and noise

The Gaussian has full-plane normalized density, integrated with 12- and 24-point Gauss–Legendre quadrature per pixel/axis. Use the 24-point result; refuse if L1 disagreement exceeds `1e-12+1e-10*selected_mass`. Do not renormalize on the mask; save flux inside/outside selected pixels. Convert Jy to MJy/sr using per-pixel Ω.

Matched truth and fitter preserve the old renderer's source-center Ω convention. Save target/companion center Ω and min/max Ω(pixel)/Ω(center). Therefore, comparison between the two truth families includes both shape **and** solid-angle convention differences; do not attribute every error to PSF. Do not alter the old renderer to create artificial agreement. Fixed mean background is the three old plane columns times `[.04,.015,-.01]` MJy/sr.

Noisy/null scenes add independent Gaussian noise scaled by observed VARIANCE; no source Poisson or oracle variance. VARIANCE reflects observed images; this is only a conditional model and does not validate detector noise, background correlations, or real source flux. Each draw uses PCG64/SeedSequence `[2026103102, draw]` to generate a bank across the full exposure shape in C order. The same physical pixel and draw use the same Z across both stamps and every phase/scene/flux/fitter; null uses the first eight banks. Draws are conditionally independent; branches/strata are paired and not independent of one another.

## Metrics and prespecified thresholds

Retain all preparation failures, fit errors, and completed fits rejected numerically. For each stratum report planned/completed/supported, signed dx/dy, radial/RMS/P90/max, Fhat/Ftrue, and bias. Report all-completed and supported-completed separately; do not use a signed mean to hide cancellation across phases. MCSE for flux ratios describes Monte Carlo noise over completed draws only; it does not address missingness or astronomical covariance. For baseline/corrected pairs, report expected and missing counts.

- **Clean noiseless:** all **128 fits** in isolated/modeled cases must complete, be numerically supported, have radial≤0.1 native pixel and Fhat/Ftrue∈[0.9,1.1]. One failing case makes the shared guard fail; do not pool across phases to erase failures.
- **Clean noisy:** each of the **16 strata** (geometry×phase×scene×fitter) has 16 draws; at least 15 must jointly complete, be supported, have Fhat>0, radial≤0.5 native pixel, and Fhat/Ftrue∈[0.5,1.5]. These are **observed-sample** thresholds, not population certification. A failed/missing attempt does not pass within denominator 16.
- **Signal preservation after correction:** all **64 clean noiseless pairs** must complete; there must be no new numerical refusal, radial error must not rise by more than 0.02 native pixels, and `|Fhat/Ftrue−1|` must not increase by more than 0.02. This guard does not replace the fidelity gate above.
- Omitted cases report all bias, companion confusion, support, and errors; they are not required to pass clean-scene fidelity and must not be used to select a model from a favorable stress case.
- Null reports signed flux and the count jointly supported with positive flux, with Clopper–Pearson intervals. There is no radial truth, flux ratio, calibrated detection, or false-alarm rate; do not reuse the old source-acceptance threshold for this PSF.

Budgets are development conditions for detecting signal damage and source confusion; they are not NASA requirements or certification of physical accuracy. Two-sided 95% binomial intervals are calculated separately for each fixed stratum; do not pool paired strata as IID. With N=16, even 16/16 gives a lower bound ≈0.794; 15/16 gives ≈0.698. `P(pass≥15/16 | p=.9)≈.515`, so this pilot is underpowered to certify 90% population recovery. Null N=8 with zero outcomes still has an upper bound ≈0.369. Report every stratum and uncertainty; do not select only passing cases and call them the validated domain.

## Isolation and publication

Design records hashes for code/tests/document, pinned source/raw data, old gate/seal, and exactly 640 keys. Commit/push before running; shards are split by geometry and each process requests one BLAS/OMP thread (actual thread count is not measured). Journal keeps immutable terminal records and resume cannot replace results. The assessment directory must be absent before/after. Prepare each fitter/companion branch lazily; a correction/companion error must not erase unrelated baseline/single-source cases. Matched truth depends only on the required original template; Gaussian truth does not depend on the fitter model. Even if all new guards pass, **the old gate still fails**; this study does not open the 252 reserved cells or 30 new fields. No model selection or promotion follows.

Independent audit will check scene, seed, units, objective at saved positions, gate, and denominators before publication. UI must clearly identify synthetic images and never call simulated sources a remeasurement of WISE 0855. A future experiment needs a new protocol, independent physical source data, real-background evaluation, and covariance; do not relax thresholds after this run.

Method references: [Gaussian2D, Astropy](https://docs.astropy.org/en/stable/api/astropy.modeling.functional_models.Gaussian2D.html), [quadrature, NumPy](https://numpy.org/doc/stable/reference/generated/numpy.polynomial.legendre.leggauss.html), [exact binomial interval, SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html). Code uses the versions pinned in requirements; it does not automatically upgrade packages based on current documentation pages.
