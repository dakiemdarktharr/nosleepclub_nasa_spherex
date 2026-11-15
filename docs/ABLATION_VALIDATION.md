# Background/ePSF Ablation and S/N/Background Calibration — 0.9.0

This version selects the point model before calibrating covariance. An ellipse containing more errors does not make the centroid more accurate. Earlier experiments remain unchanged; WISE 0855 still uses the 0.3.0 measurement and its motion has not been confirmed.

## Split and locked configuration

| Role | Fields | Data used |
|---|---|---|
| Development | v060m30, v150p45, v330p10, Barnard, RW Aur | All opened in earlier sessions; compare four point models and select the background-feature threshold |
| Calibration | q030m10, q180p20, q300m30 | Not used to select the point model; learn covariance for the selected model |
| External validation | w090p10, w210m20, w350p35 | New coordinates (90°, +10°), (210°, −20°), (350°, +35°); fit only after the final seal |

Fields were selected by coordinate before recovery errors were known. The three roles have no shared exposure IDs. Within each field, held-out Gaia stars are not used for alignment. Catalogs and star splits remain from image/catalog-based selection and were not reselected using truth errors.

Design checkpoint **`63e2b6b`**; `design.json` SHA-256: **`403dcadf4e75dd32219960d44eed3524e8600267f9a15d4a126ffd92c4cfcea7`**. After development, a checkpoint locks the model/background threshold before calibration, and a third checkpoint locks the calibrator before validation. [design.json](../web/data/ablation/design.json) stores URLs, queries, FITS hashes, catalogs, spectral WCS, ePSF, code, and data splits.

## Four point models on the same data

| Combination | Background per exposure | Target shape | Nonlinear parameters per epoch |
|---|---|---|---|
| `plane_fixed` | First-order tilted plane | Fixed ePSF | x, y |
| `quadratic_fixed` | Add x², xy, y² | Fixed ePSF | x, y |
| `plane_flexible` | First-order tilted plane | Mixture of original/broadened | x, y, η |
| `quadratic_flexible` | Add x², xy, y² | Mixture of original/broadened | x, y, η |

Broadened shape uses Gaussian σ=0.25 native pixels; η∈[0,1] is shared across exposures within an epoch. The D6 ePSF library remains pinned. Each exposure has its own target amplitude, neighbor amplitudes, and background nuisance terms; flux is not constrained by W2 or an external predicted motion. Neighbor shape/position stay fixed.

All four models receive the same pixels, injected sources, masks, error maps, offsets, and alignment covariance. Use the same **single-source baseline** for the positional-disagreement gate; unlike 0.8, do not change the comparison target across models. Solver starts share the same anchor and four neighboring points. Two Huber iterations downweight outliers; the gate checks residuals against the original noise. A model with insufficient information rank fails the measurement gate.

Each model catches its own errors, so a failed candidate does not discard a valid baseline. Raw covariance includes the Hessian marginalized over nuisance terms, alignment offsets, and Gaia covariance for the predicted vector. With η, use the full three-parameter Hessian inverse; when η is on a boundary, it remains an approximation. This ablation does not add a model-difference term to only one combination.

[IRSA](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html) describes local background processing with source masking and neighbor fitting. The official tool fits flux at fixed positions; the project's runner fits centroids separately and does not return an IRSA measurement.

The development set contains **160** synthetic sources (5 fields × 4 positions × 2 per-frame S/N levels × 2 vectors × 2 source shapes) and **55** held-out Gaia stars. Source shapes are either the original ePSF or isotropic blur σ=0.15 pixels. Cases share background/exposure and are correlated; the four models are not four independent samples.

## Model-selection rules

A more complex model may replace `plane_fixed` only if:

- Each field/SNR/source-shape group has at least 4 pairs that pass the gate in both models; paired RMS and P90 do not increase; and no additional valid/gate-passing fits are lost.
- Each Gaia-star field has at least 3 common pairs and also does not increase RMS/P90 or lose fits.
- Pooled paired RMS for synthetic sources decreases by at least 5%. Do not select from an average if any group worsens.
- If no candidate passes, retain the simpler baseline. This is a conservative choice, not proof that the baseline is correct. Run five leave-one-field-out selections to assess sensitivity to individual fields; this is an internal diagnostic on already opened data.

## Calibration features

**Observed S/N** is the smaller S/N of the two epochs from the selected fit. Do not use the injected source's labeled S/N to choose groups. The S/N=10 threshold was declared in advance.

**Background roughness** is measured on original pixels before synthetic sources are added: native 4–9 pixel annulus, excluding the target core and masking catalog neighbors within 2.5 pixels. At least 24 pixels are required per frame. Fit a weighted plane with three rounds of 3σ clipping; compute `1.4826 × MAD` of the residual divided by original noise. Each epoch needs a feature from at least 80% of frames; take the median, then the larger value of the two epochs. This dimensionless index is not a background value in MJy/sr.

Background threshold is the median across fields/regions of the **development-set feature**, not fit error, motion label, or injected source. It is saved in `selection.json` and committed before calibration. Split into four cells: low/high S/N × smooth/structured background. Missing or mispositioned catalog sources can bias the feature; measured S/N in a blended region can also differ from the injected source's true S/N.

## Calibration and pooling for small samples

Calibration contains **192** synthetic sources at eight positions per field. Even-indexed regions train F; odd-indexed regions train α and s. Positions do not overlap, but still share exposure and calibration library; do not call them independent samples.

Using equal weights by field and then background region, F is the PSD part of the error moment `eeᵀ−Craw`, without subtracting mean bias. Fit a group separately only if **each partition** has at least 12 cases, 3 background regions, and 2 fields. Blend a group-specific F with its parent F using weight `B/(B+8)`, where B is the number of background regions used to learn F. Groups with insufficient data pool to the same S/N group, then to the full dataset, rather than fitting a matrix from very few cases.

On the odd partition, choose the smallest α in {0, 0.1, …, 1} whose weighted coverage reaches 68%. If α=1 still undercovers, learn s² from the Mahalanobis quantile. Always require s²≥1:

```text
Ccal = s² · (Craw + (0.05″)² I + α F)
```

Do not shrink `Craw` or subtract bias from the vector. If the raw ellipse is already too conservative, the algorithm cannot fix overcoverage by shrinking it. Compare **global** and **grouped** methods on the same model, calibration split, and validation set supported by both.

Support range uses min–max S/N and background values from the group that learned the parameters, with predefined multiplicative tolerance **1.25**. This is an empirical tolerance, not an extrapolation guarantee. Outside the range or with missing features, do not issue calibrated covariance; retain the trial and raw fit in the product. The demo reports in-range counts against quality-gated counts so difficult samples are not hidden to improve coverage.

[Braun et al., ICML 2026](https://proceedings.mlr.press/v306/braun26c.html) distinguishes conditional coverage diagnostics from average coverage. This version uses a simple grouping table; it does not implement the paper's ERT method and has no conformal/conditional-coverage guarantee. Small samples, selection/gating, and distribution shift across fields remain the main limits.

## Predefined external validation

Three new fields contain 96 synthetic sources and 33 Gaia stars held out from alignment. The second source shape is elliptical blur `(σy,σx)=(0.06,0.22)` pixels, different from the isotropic blur used for development/calibration. This is an assumed stress-test shape, not an independently measured physical ePSF. No source shot noise is added; original noise map/mask remain unchanged.

Covariance gate requires: 68% coverage in [55%, 85%] pooled and in all four cells; at least 8 in-range cases and 2 background regions per cell; at least 24 cases and 6 background regions overall across all three fields; at least 80% of quality-gated cases in range; median ellipse area ≤16 times raw; and a bootstrap interval containing 68%. The hierarchical bootstrap samples fields then regions, 2,000 draws; it remains weak with only three fields.

The positional gate compares the selected model with `plane_fixed` on the same cases, including pre/post-gate RMS/P90 and fit counts. Consider further use only if both position and covariance gates pass; do not automatically update WISE 0855.

## Results

**Retain `plane_fixed`: flat background + fixed ePSF.** No complex combination met all criteria. All five leave-one-field-out selections also retained the baseline. This is a conservative selection on opened data, not certification that the baseline is stable for every source.

Model/threshold selection checkpoint **`1f1dae2`**; external-field seal checkpoint **`8c7ad54`**. Protocol SHA-256 **`f6545377be850ce1c5d7e015326747be6f7e47790da01bc816b8b62c9938d83f`**. The three external fields have **135 QR2 cutouts**; **60 exposures** were selected as 30 spectral pairs. Code/threshold/calibrator were not adjusted after opening them.

| Development combination | Valid fits / trials | Paired RMS / P90 vs baseline | Gate-passing / trials | Groups passing / tested |
|---|---:|---:|---:|---:|
| Flat background / fixed ePSF | 152/160 | 3.110 / 2.751″ | 111/160 | 21/25 |
| Quadratic background / fixed ePSF | 152/160 | 1.967 / 2.660″ | 108/160 | 8/25 |
| Flat background / flexible ePSF | 152/160 | 3.086 / 2.843″ | 108/160 | 6/25 |
| Quadratic background / flexible ePSF | 152/160 | 3.080 / 2.661″ | 109/160 | 6/25 |

Quadratic background/fixed ePSF lowers pooled RMS by about 36.7%, but passes only 8/25 groups and loses 3 additional gate-passing fits. It was not selected based on the average. Baseline has 21/25 groups eligible for self-comparison; four groups lack the minimum common gate-passing cases. Do not interpret “selected” as proof of correctness in all 25 groups.

The locked background threshold is **1.016051688**; S/N threshold is 10. Most background indices are near noise level; “low/high” is relative to the development set, not a physical label for presence/absence of diffuse background.

Calibration has **140/192** usable gate-passing cases: 82 cases/11 background regions in the even partition train F; 58 cases/9 regions in the odd partition train α/s. Two low-background cells have only 4 cases in one region, one field in the odd partition, so they pool by S/N. Both high-background cells have enough data for group fitting. The s² factors for low S/N groups are about 2.61–2.75; high S/N groups equal 1 with α=0.6–0.7. Across calibration, both global/grouped methods cover 114/140; median area changes from ×5.00 to ×4.30. This is a fitted set, not independent validation.

**External validation: covariance gate not passed.** **88/96** synthetic sources fit successfully; **69/96** passed the quality gate; all 69 were within support for both calibration methods, across **9** background regions. Raw 68% ellipses contain **28/69 (40.6%)** true vectors. Global calibration reaches **54/69 (78.3%)**, and grouped reaches **57/69 (82.6%)**, but results vary across fields/cells. Median ellipse area relative to raw drops from **×5.15 to ×2.23** when changing global to grouped. Both coverage values fall within the pooled range, but three of four cells exceed the 85% upper limit; do not pass based only on a better pooled result. The field/region bootstrap interval is very wide: **12.5–100%**.

| External field | Quality-gated / trials | RMS / P90 · gated sample | 68% coverage global → grouped | Median area global → grouped |
|---|---:|---:|---:|---:|
| w090p10 | 30/32 | 1.525 / 2.375″ | 29/30 → 30/30 | ×5.11 → ×2.24 |
| w210m20 | 31/32 | 1.489 / 2.298″ | 24/31 → 26/31 | ×5.17 → ×2.23 |
| w350p35 | 8/32 | 2.065 / 2.748″ | 1/8 → 1/8 | ×4.23 → ×3.81 |

| Observed-feature cell | In range / quality-gated | 68% coverage global → grouped | Median area global → grouped | Cases using pooled factors |
|---|---:|---:|---:|---:|
| snr_low_bg_smooth | 11/11 | 11/11 (100.0%) → 11/11 (100.0%) | ×3.43 → ×7.15 | 11 |
| snr_low_bg_structured | 22/22 | 11/22 (50.0%) → 19/22 (86.4%) | ×3.28 → ×6.57 | 0 |
| snr_high_bg_smooth | 12/12 | 12/12 (100.0%) → 12/12 (100.0%) | ×5.95 → ×2.15 | 12 |
| snr_high_bg_structured | 24/24 | 20/24 (83.3%) → 15/24 (62.5%) | ×5.67 → ×1.81 | 0 |

`w350p35` has only one background region with 8 gate-passing cases. Only 1/8 falls inside the 68% ellipse under either calibration method, even though S/N and background are within range. Errors are 1.19–2.95″, with mean bias [−1.098, −1.568]″. The eight cases share background/exposure and are not eight independent validations. This shows that S/N/background support checks do not protect against every bias; the physical cause is unknown. The demo marks this background region on the original image and clearly states that it has no injected source. Selecting a difficult case is a post-validation diagnostic; it was not used to reselect the model/factor.

Real Gaia stars: **27/33** numerically valid fits, **23/33** passed the quality gate, with RMS **0.412″** on the gate-passing subset. Only **5/23** are within covariance support; **18** are reported out of range instead of extrapolating a floor to bright stars. Coverage of 5/5 in the small supported subset must not be called “100% accuracy.”

`point_passed=true` for external validation because the retained model is the baseline itself, with enough cases and unchanged self-comparison. This does not prove more accurate positions; the overall result is still false and WISE 0855 is not upgraded. Per-field JSON contains failed cases and reasons.

**All 95/95 offline tests passed**, including four combinations, exception isolation, truth-independent routing, region-level floor/quantile split, pooling, PSD without shrinking, out-of-range refusal, selection/calibrator reconstruction, all denominators, and the hash chain. This validates software/provenance, not astronomical claims.

## Reproduction and limits

Raw FITS/cache files are Git-ignored under `data/raw/`; manifests/hashes are in `design.json`. With the scientific environment installed and matching cache hashes:

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_ablation_data
.\.venv\Scripts\python.exe -m scripts.run_ablation design
# Commit the design and code.
.\.venv\Scripts\python.exe -m scripts.run_ablation develop
# Commit development results and selection.json.
.\.venv\Scripts\python.exe -m scripts.run_ablation calibrate
.\.venv\Scripts\python.exe -m scripts.run_ablation seal
# Commit the calibrator and seal before validation.
.\.venv\Scripts\python.exe -m scripts.run_ablation validate
.\.venv\Scripts\python.exe -m scripts.build_ablation_overview
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The `run_ablation` wrapper blocks overwriting a phase when its corresponding selection, calibrator, seal, or completed summary exists. Field results are reused when resuming an interrupted phase; source/rule hashes must match. The `ablation_study` core is retained according to its source hash; use the wrapper to avoid accidentally rewriting summary/metadata by calling the core directly. Do not describe opened data as “new”; a new experiment requires a new output/protocol and external fields.

The web app remains static HTML/CSS/JS; only review APIs use Python/MongoDB. Scientific fitting runs offline. Remaining limits include known positions, a broad spectrum at the center, incomplete covariance of noise/offset correlations, fixed neighbors/ePSF, and few fields. Passing software tests is not equivalent to confirming astronomical motion.

## Next steps and acceptance criteria

Before opening more fields, diagnose the `w350p35` region and development outliers on **already opened data**: inspect blended sources, residuals, multiple centroid solutions, masks, detector position, and leave-one-exposure-out sensitivity. Do not tune a factor to the truth vector of one case and call it a general improvement.

Test additional observed features for source overlap, remaining centroid/amplitude information, and sensitivity across leave-one-exposure-out runs. Check whether they predict external miscoverage beyond S/N/background using internal field-level validation and predefined pooling/abstention rules. Add diverse calibration fields so each low-background group has at least three regions and two fields in each partition, rather than learning scale from one region only.

Lock a new external run only after reproducible improvement across multiple regions/fields: RMS/P90 no worse, no under/overcoverage by field or group, no reduction in in-range cases to hide difficult samples, and no unnecessary ellipse inflation. Lock the thresholds and new set before fitting. The goal is to address structured bias, not merely make pooled coverage closer to 68%.
