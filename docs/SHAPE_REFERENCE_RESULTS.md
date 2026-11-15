# ePSF Correction and Reference-Star Covariance — 2026-10-31

**The candidate ePSF has not been applied to the measurement.** The learning step passed information and shape checks, but the calibration position test found additional competing solutions for two stars. The gate blocked assessment of the remaining 252 cells. A separate covariance study is reproducible with independent algebra, but total uncertainty is not calibrated.

[Open demo](https://nosleepclub-nasa-spherex.vercel.app/#shape-validation) · [20 criteria](PRODUCTION_READINESS.md) · [MIT](../LICENSE) · [NOTICE](../NOTICE.md).

## Three steps locked before running

| Step | Protocol commit | Result |
|---|---|---|
| Learn three ePSF coefficients from calibration | `972c8b8723326bc60e99ebd8611e1beb6efd34b3` | 145 informative cells /168 planned; 22 lacked suitable images, one baseline was numerically rejected |
| Baseline covariance and reference frame | `b42515e3a4ac95df5e786d47f5ff18ad706b937b` | 357 cells with response /420; 61 lacked support and two rejected cells were retained |
| Fit positions with sealed ePSF coefficients | `31d07ab777628aecc90af3b244e882e2e6d95b93` | Calibration: 146 fits /168 cells, 22 old preparation failures. Gate failed; 252 assessment cells unopened |

All stars/images are from the WISE field already opened. The 14 training and seven heldout labels were assigned earlier; their baseline results had also been viewed. Within each season, the first six exposures by IMAGE MJD-AVG are used for learning and the final four are reserved for later assessment. This split separates data for the new experiment, but does not make an image-selected cohort an independent sky validation. The 30 prospective 12/12/6 field centers have not been queried or measured.

## Learning step: reduced dominance by one star, no proof of reduced bias

Preflight that did not use residual scores found that one bright star contributed up to 50.70% of information in one correction direction. Before coefficient learning, the estimator was changed to balance mean information per exposure for each star. This choice was made after inspecting development-set information and is disclosed in the [protocol](SHAPE_CALIBRATION_PROTOCOL.md). The 35% dominance threshold remains unchanged.

After balancing, the maximum contribution is **12.87%** and the three-dimensional information condition number is **1.052**. 13/14 stars contribute information. All 145 available samples pass moment, peak-change, and negative-wing checks. Coefficients were sealed in Git before position fitting:

| Coefficient | Value | Conditional standard error | Units |
|---|---:|---:|---|
| Width | −0.00830790 | 0.00568703 | native pixel² |
| X asymmetry | +0.000695585 | 0.000828389 | native pixel³ |
| Y asymmetry | +0.000807192 | 0.000807902 | native pixel³ |

The model family preserves total flux and the first two moments on the full native lattice before masking; target and all retained neighbors use the same corrected family. This fixes a numerical convention but does not identify the true optical center or instrument flux calibration. Covariance uses response over 20,327 distinct original pixels, summing overlapping-stamp contributions before propagating noise.

Errors are conditional on baseline position, Huber weights, source balancing, mask, catalog coordinates, and calibration. Balancing depends on noisy fitted amplitudes; variation in weights is not propagated. Do not treat coefficients or value/error ratios as an optical test or evidence of reduced bias.

## Position gate: two cases lost support

Do not relearn the coefficients. The fitter retains baseline pixels, observed errors, sloped plane, signed Jy flux, neighbor positions, nine starts, and Huber limit. Of 145 previously numerically supported cells, **143** remain supported. On these 143, the difference between actual and linearized predicted position changes has P90 **0.004593 common pixels** and maximum **0.025339 common pixels**, below budgets 0.02/0.05. The other two cells cause gate failure and remain in the denominator.

| Gaia source ID | Exposure | Old → new near-best solution count | Separation between new solutions |
|---|---|---:|---:|
| 5756942110218608640 | 2025W46_2A_0214_3 | 1 → 2 | 1.889921″ |
| 5756958431094222592 | 2025W46_2A_0214_3 | 1 → 2 | 3.378414″ |

These solutions were found in a nine-start audit using fixed final weights; Δχ² threshold 5.991 is heuristic. This does not prove all solutions were found or that baseline had no other solutions. Both Huber fits converged; this gate failure is due to competing position solutions, not iteration exhaustion.

**The 252 assessment cells, including 56 primary cells = seven stars × eight exposures, were not evaluated with the corrected model.** Primary gates in JSON are unmet because results are unavailable; this is not a conclusion that they were measured and failed. All IDs, errors, and deferred cells remain in the audit. Do not transfer the old source-acceptance threshold to the new PSF; the WISE 0855 measurement is unchanged.

Independent audit checked all 168 IDs/checksums, 146 native-pixel models, IRLS, and solution groups. **1,314/1,314** final objective functions were replayed by BVLS at saved positions: maximum χ² difference **2.274×10⁻¹³**, maximum model difference **1.776×10⁻¹⁵ MJy/sr**. Position was not re-optimized in the audit. Position Jacobian/rank has not been independently audited; this does not validate a physical PSF.

## Baseline covariance: correlations retained, calibration not achieved

This separate study uses the old nearest ePSF, **not** the coefficients just learned. Position response is evaluated at saved baseline fit points. One noise variable per exposure/native pixel preserves correlations between overlapping stamps; Gaia retains each star's shared five-parameter covariance across time. The matrix contains **49,294** distinct original pixels. The translation solution across 20 exposures uses training stars only, with 11–13 available per exposure. Heldout residual covariance retains cross-star terms and reference-frame solution terms.

| Conditional diagnostic | Usable cells | χ² | Degrees of freedom | χ² / d.f. |
|---|---:|---:|---:|---:|
| Training | 238 | 833.8641 | 436 | 1.9125 |
| Heldout | 119 | 407.4310 | 238 | 1.7119 |

Heldout star `5756959015209770112` has no available cells but remains as `0/20`; training star `5756962382464133248` is also retained. Do not remove outliers, add a floor, or arbitrarily scale covariance to force χ² to one. Nominal statistics show residuals do not fit this error model; the difference has not been attributed to bias, noise, blends, or missing components.

Independent QR audit over **357/357** points reconstructs data, errors, background, and neighbor design correctly. Maximum absolute difference in position response is **5.575×10⁻¹⁵**; in pixel covariance it is **2.082×10⁻¹⁷ pixel²**. Gaia matrices, GLS solutions, and heldout residuals were independently recomputed. Algebraic success does not establish complete covariance: masks, weights, ePSF, prior registration, and neighbor coordinates remain fixed; their noise dependence is not propagated. Different catalog stars are assumed independent. The cohort is already opened and upstream WCS/ePSF may share data. Overall coverage has not been validated.

## Inspectable products

| Product | Lightweight | Full audit |
|---|---|---|
| Coefficient learning | [Overview](../web/data/shape-correction/overview.json), [seal](../web/data/shape-correction/coefficient-seal.json) | [2.48 MB gzip](../web/data/shape-correction/calibration-records.json.gz) |
| Calibration fits and gate | [Overview](../web/data/shape-point-check/overview.json), [gate](../web/data/shape-point-check/calibration-gate.json), [independent audit](../web/data/shape-point-check/independent-audit.json) | [3.06 MB gzip](../web/data/shape-point-check/records.json.gz) |
| Baseline covariance | [Overview](../web/data/reference-covariance/overview.json), [independent audit](../web/data/reference-covariance/independent-audit.json) | [2.72 MB gzip](../web/data/reference-covariance/records.json.gz) |

Overviews record compressed/decompressed SHA-256, byte size, protocol commit, journal digest, audit source, and units. The web app loads only the three overviews on opening the section; archives are separate downloads. Original FITS remains in the Git-ignored cache; URL/hash/mask/version are in each record. Products 0.3–0.9 and the earlier 840/7,992-attempt studies remain unchanged.

[IRSA documentation](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/) and the [official tutorial](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/) recommend the new ePSF for QR2 images. Therefore, these two cases do not by themselves show that QR2/new-ePSF pairing is wrong. [Photutils](https://docs.astropy.org/projects/photutils/en/stable/user_guide/epsf_building.html) discusses sampling, center, and normalization; it does not validate this correction family.

## Next steps and criteria

Local regression ran **528 Python cases: 522 passed, six Mongo fixture cases skipped** because production credentials were not brought onto the machine. Six Node suites passed. [Source/log receipts](evidence/0.10/shape-reference-local-tests.json) and [desktop/mobile/keyboard checks](evidence/0.10/shape-local-browser.json) record the actual scope; this is not a full screen-reader/WCAG audit. CI Mongo and public deployment need separate release receipts.

Prioritize explaining the two competing solutions within one exposure: lock a positional-profile diagnostic for the two failed stars, same-image training stars, and neighboring images; save original/model/residual/mask and neighbor roles. Distinguish a mode already available but missed by the solver from a landscape change caused by the PSF correction. Retain every case and do not change thresholds to turn the gate green.

The milestone passes when the mechanism behind competition is reproducible and a prespecified estimator/support domain or refusal rule is tested for both signal preservation and blends. Then propagate full registration/neighbor-coordinate uncertainty and test coverage by observed S/N, background, and crowding on separate splits. Open the 30 prospective fields only after locking evaluator, absolute-error budget, power, overlap, and acceptance policy. Production backup/restore, representative load, SLO, and complete accessibility audit remain in the ledger; this milestone does not close them.
