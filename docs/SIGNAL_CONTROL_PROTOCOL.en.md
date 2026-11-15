# Signal, Blend, Template, and Native-Phase Controls

*English translation of the hash-locked original protocol, [SIGNAL_CONTROL_PROTOCOL.md](SIGNAL_CONTROL_PROTOCOL.md). The original remains the canonical source used by the scientific evidence manifests; this translation is provided for readability.*

Version 0.10.0-signal-controls.1. Lock the code, tests, seeds, attempt list, and thresholds below in Git before generating scenes/noise or fitting the experiment. This is intentional development on opened data, not sky validation.

## Question and data domain

Measure position/flux bias and signal preservation for the two existing fitters while varying the truth template, subpixel phase, and blend information. Do not relearn the PSF, change the solver, revise old gates, or select a model from these results.

Use only the geometry of two training stars, 5756942110218608640 and 5756958431094222592, at the old exposure 2025W46_2A_0214_3. Both were selected after the old gate failed; they are two stamps in **one** image/field selected from the images. They are not independent fields. Before preparing inputs, the pipeline verifies parent protocol 704e3ef, inherited journal/source, and coefficient seal. Three public parent artifacts (overview, audit, and complete journal/checkpoint archive) are hash-bound and digest-checked before design or execution.

Keep the selected pixels, mask, original VARIANCE, WCS, and old registration fixed. Replace IMAGE with a **synthetic scene**; do not add the scene to the noisy real image or use real residuals as truth. Replace the original neighbor catalog with only the controlled companion; do not silently retain real stars in the synthetic mean.

The native target center is floor(registered Gaia center) plus one of four phases: (0.25,0.25), (0.25,0.75), (0.75,0.25), or (0.75,0.75). For every scene with a source, the fitter's search anchor remains the old Gaia position and does not know the injected position. For null only, use the common anchor transformed from the corresponding native phase; null has no source truth. Place the companion at (+1.5,0) native pixels from the target, with the same flux. Use forward/inverse WCS with offsets to convert coordinates, and check round-trip closure to 1e−7 pixel. Bias/separation is always measured in **native pixels**; do not multiply by the common-grid scale of 6.15″ to make it appear to be native.

## Locked factorial: 640 fits

| Part | Factorization | Fits |
| --- | --- | ---: |
| No noise | 2 geometries × 2 truths × 4 phases × 3 scenes × 2 fluxes × 2 fitters | 192 |
| With noise | 2 geometries × Gaussian truth × 2 phases × 3 scenes × 1 flux × 16 draws × 2 fitters | 384 |
| Null | 2 geometries × 2 phase anchors × 8 draws × 2 fitters | 64 |

Truth templates are (1) the original nearest-neighbor ePSF, matched to the model as a software check—this is an inverse crime and may include negative wings; and (2) a positive elliptical Gaussian integrated over pixels, with native-pixel σ=(0.55,0.70), rotated by 25°. The Gaussian is a different mathematical family from the fitter, not an independently measured SPHEREx PSF. The two fitter branches are the original nearest model and the nearest model plus exactly the sealed shape-correction vector, applied to both target and any fitted neighbor.

The three scenes are: isolated, with only the target; modeled, with a companion fitted at its true coordinates; and omitted, with the same target+companion/image/noise as modeled but with the companion column omitted from the fitter. Omitted is a model-mismatch stress case, not a sample on which to require clean-scene fidelity when the model intentionally omits a source. Do not select or discard it after seeing results.

Noiseless target fluxes are 600 and 1,200 µJy. Noisy trials use only Gaussian truth, 1,200 µJy, and phases 0 and 3. Null has neither target nor companion; phase only sets the corresponding anchor and is not a source-truth coordinate. Every fitter retains signed target/neighbor flux, plane background, nine starts, common ±2.5-pixel bounds, and at most 20 IRLS iterations as in the locked code.

## Normalization, background, and noise

The Gaussian has a plane-normalized density integrated using 12- and 24-point Gauss–Legendre quadrature on each pixel axis. Use the 24-point result and reject if the L1 difference exceeds 1e−12 + 1e−10 × selected_mass. Do not renormalize over the mask; save the flux inside and outside the selected pixels. Convert Jy to MJy/sr using each pixel's own Ω.

Matched truth and fitter retain the old renderer's Ω convention at the source center. Save target/companion center Ω and the minimum/maximum Ω(pixel)/Ω(center). Therefore, comparing the two truth families includes both shape differences **and** solid-angle-convention differences; do not attribute every discrepancy to the PSF. Do not modify the old renderer to create artificial agreement. The mean background is fixed by multiplying the three old plane columns by [0.04, 0.015, −0.01] MJy/sr.

Noisy/null trials add independent Gaussian noise scaled by the original observed VARIANCE; there is no source Poisson term or oracle variance. VARIANCE reflects the already observed image; this is only a conditional model and does not validate detector noise, background correlation, or real-source flux. Each draw uses PCG64/SeedSequence [2026103102, draw] to create a bank over the full exposure shape, in C order. The same physical pixel and draw use the same Z across both stamps, all phases/scenes/fluxes/fitters; null uses the first eight banks. Draws are conditionally independent; branches/strata are paired and are not independent of one another.

## Metrics and prespecified thresholds

Retain every preparation failure, fit failure, and completed fit refused by numerical screening. For every stratum, report planned/completed/supported counts, signed dx/dy, radial error/RMS/P90/max, Fhat/Ftrue, and bias. Report all-completed and supported-completed separately; do not use a signed mean to hide bias cancellation across phases. Flux-ratio MCSE describes Monte Carlo noise over completed draws only; it does not handle missingness or astronomical covariance. For baseline/corrected comparisons, report both the planned and missing pair counts.

- **Clean noiseless:** all **128 isolated/modeled fits** must complete, be numerically supported, have radial error ≤0.1 native pixel, and Fhat/Ftrue in [0.9, 1.1]. One failure makes the overall guard fail; do not pool it with other phases to hide the failure.
- **Clean noisy:** each of the **16 geometry×phase×scene×fitter strata** has 16 draws; at least 15 must simultaneously complete, be supported, have Fhat>0, radial error ≤0.5 native pixel, and Fhat/Ftrue in [0.5, 1.5]. This is an **observed-sample threshold**, not certification of a population rate. Failure/missing counts as not meeting the criterion in the denominator of 16.
- **Signal preservation after correction:** all **64 clean noiseless pairs** must complete, with no new numerical refusal, radial error increase ≤0.02 native pixel, and |Fhat/Ftrue−1| increase ≤0.02. This guard does not replace the fidelity gate above.
- For omitted trials, report all bias, companion confusion, and support/failure outcomes; do not require clean-scene fidelity or select a model based on favorable stress cases.
- For null, report signed flux and the count of fits that are both supported and positive-flux, with Clopper–Pearson intervals. There is no radial truth, flux ratio, calibrated detection/false-alarm rate, and the old source-acceptance threshold must not be reused for this PSF.

These budgets are necessary development checks for finding signal loss and source confusion, not NASA requirements or certification of physical accuracy. Calculate two-sided 95% binomial intervals separately for each fixed stratum; do not pool paired strata as IID. At N=16, even 16/16 gives a lower bound of about 0.794; 15/16 gives about 0.698. P(pass at least 15/16 | p=0.9) is about 0.515, so this pilot lacks power to certify 90% population recovery. For null N=8, even zero outcomes has an upper bound of about 0.369. Publish all strata and uncertainty; do not select passing subsets and call them a validated domain.

## Isolation and publication

The design records hashes of code/tests/documentation, pinned sources/raw inputs, the old gate, the seal, and exactly 640 keys. Commit/push before running. Split into two geometry shards and request one BLAS/OMP thread per process; this is not a measurement of actual thread count. The journal keeps terminal records immutable and resume does not change results. The assessment directory must be absent before and after. Prepare each fitter/companion branch lazily and separately; a correction or companion failure must not discard unrelated baseline/single-source cases. Matched truth depends only on the required original template; Gaussian truth does not depend on the fitter model.

Even if every new guard passes, **the old gate still fails**; this study does not open the 252 reserved cells or 30 new fields. No model selection or promotion is allowed.

An independent audit will check scene/seed/units, the objective at saved positions, and the gate/denominator before publication. The UI must clearly label synthetic images and must not call an injected source a remeasurement of WISE 0855. The next experiment needs a new protocol, physically independent source data, real-background evaluation, and covariance; do not relax thresholds after this study.

Method sources: [Gaussian2D, Astropy](https://docs.astropy.org/en/stable/api/astropy.modeling.functional_models.Gaussian2D.html), [quadrature, NumPy](https://numpy.org/doc/stable/reference/generated/numpy.polynomial.legendre.leggauss.html), and [exact binomial interval, SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html). Code uses the versions pinned in requirements; do not upgrade packages based on the current documentation pages.
