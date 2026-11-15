# Quality Gate and Crowded Sources — 0.7.0

**The criteria for replacing the default method were not met.** The new model lowered paired synthetic-source RMS in two fields and was nearly unchanged in the third; real-star errors and post-gate results did not improve consistently. Passing 59 software/provenance tests does not validate an astronomical measurement.

This experiment added quality checks, an infrared neighbor-source model, and reduced sensitivity to pixel outliers. Barnard, RW Aur, and R Dra fields from version 0.6.0 were used for development. Three new field centers — RA/Dec (30°, −10°), (180°, +20°), (300°, −30°) — were declared from geometry before inspecting results, then the configuration was locked before evaluation.

The WISE 0855 measurement currently served on the web remains unchanged. This check uses broad-band data and fits around known positions; it does not measure precision/recall for blind searches.

Checkpoint before evaluation: **`330449c`**. Protocol SHA-256: **`9ad4bbef5c980ef55c71735587479620a2b42289b9f27408256f4f69d72e8104`**. The three new fields contain **115 QR2 cutouts**, of which 58 spectrally compatible exposures were selected for this experiment; no exposures from the three development fields were reused.

## Model and gates

The [IRSA guide](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html) checks neighboring sources, pixel flags, residuals, and image background when evaluating SPHEREx fits. The official tool can fit amplitudes for multiple sources at fixed positions; this experiment also fits the target centroid and must not be described as an IRSA tool measurement.

The new model keeps the pinned D6 ePSF, uses CatWISE with tile corrections, and prioritizes quality Gaia positions. Each exposure has separate target amplitude, neighbor amplitudes, and a background plane. It does not constrain SPHEREx brightness from W2 or constrain the displacement vector from an external prediction.

Infrared sources within 8 sky-grid pixels are included, up to the 24 brightest in W2. The catalog source corresponding to the true target is removed from the nuisance model; other neighbors remain. SVD handles near-dependent nuisance columns. After the initial fit, two Huber IRLS iterations downweight pixels with large residuals; gate metrics are still evaluated on original residuals and noise, not only on downweighted residuals.

| Gate | Acceptance condition |
|---|---|
| Solution | Solver converges, is not within the outer 5% of the ±2.5-pixel bounds, and total amplitude is positive in each epoch |
| Signal | Model-based total S/N ≥5 in each epoch; a single-frame alignment star also needs S/N≥7 |
| Overall fit | χ²r≤3 |
| Source core | Residual/noise RMS≤2.5; ≥75% valid core pixels; fraction of residuals above 5×noise≤10%; must pass in ≥80% of frames |
| Crowding | At least 5% of target-amplitude information remains after nuisance projection in ≥80% of frames; this is not the centroid's 2D Fisher information |
| Model disagreement | Centroid separation ≤`max(0.20 pixel, 3√λmax(Σold+Σnew))` |
| Alignment | At least four stars after a median/MAD normalized-distance screen; heldout stars are not used |

Thresholds are locked development choices, not NASA/IRSA certification standards. Both fits share pixels, so the disagreement gate is not a probabilistic “3σ” test. Median/MAD distance is not interpreted as a Gaussian probability, despite the code parameter name `mahalanobis`.

## Validation design

The baseline is the single-source fitter from version 0.6.0. Apply the same gate to the baseline and new model; always report converged fits, accepted fits, and rejected fits.

- **Real stars:** compare the two-epoch vector with Gaia. The baseline uses the old Gaussian alignment; the new model uses IR centroids from training stars and a median/MAD gate. Heldout stars do not participate in alignment or ellipse recalibration.
- **Synthetic sources:** four fixed positions × designed per-frame S/N 2/4 × stationary/displacement `[0.6; 0.05]` pixels × original/broadened ePSF = **32 conditions per field**. Both models receive identical pixels and baseline alignment so the contrast isolates centroid/crowding fitting from frame changes.
- Broaden the ePSF with a Gaussian σ=0.15 native pixel. This is a hypothetical perturbation, not an independently calibrated physical PSF. Add no source shot noise.
- Paired RMS uses only attempts where both models produce a result. Post-gate RMS uses the intersection of attempts accepted by both. Also report RMS/P90 for all valid fits so that rescued or rejected attempts are not hidden.

For the full experiment to pass, at each field, S/N, and injected ePSF family, paired RMS must decrease, P90 must not increase, and neither the number of computed fits nor accepted fits may decrease. Real stars require at least three paired cases, non-increasing paired RMS, and no loss in fit/accept counts. Every field must pass; do not use the best field as the overall result. The 95% bootstrap resamples spatial positions and does not treat fits sharing a background as independent.

## Results on the three new fields

| RA/Dec field | Gaia queried | IR sources passing screen | Spectral pairs |
|---|---:|---:|---:|
| 30° / −10° | 189 | 1,011 | 10 |
| 180° / +20° | 150 | 823 | 9 |
| 300° / −30° | 1,506 | 2,722 | 10 |

### Synthetic sources: measure bias before quality rejection

There are 96 conditions across 12 spatial positions, with both models receiving each condition. Table rows pool two brightness levels, two vectors, and two injected ePSF families. “Computed” requires valid solver/bounds/flux; “accepted” adds quality checks. RMS is in arcseconds.

| Field | Paired / attempts | Old → new RMS before gate | Point-estimator improvement; 95% bootstrap | Old → new accepted |
|---|---:|---:|---:|---:|
| 30° / −10° | 24/32 | **1.826 → 1.471″** | +19.4%; [2.9%; 53.8%] | 24 → 20 /32 |
| 180° / +20° | 32/32 | **1.989 → 1.991″** | −0.08%; [−0.57%; 1.04%] | 28 → 28 /32 |
| 300° / −30° | 32/32 | **5.279 → 3.725″** | +29.4%; [−17.4%; 63.9%] | 8 → 8 /32 |

Each model computed 88/96 vectors. Attempts that could not be computed still have records. Do not interpret 88/96 as completeness for astronomical searches. The bootstrap has only four spatial blocks per field and shares exposures; these are post hoc diagnostics, not evidence of all-sky improvement.

### Bias remains after the gate

| Field | Both accepted / attempts | Old → new RMS on those same pairs |
|---|---:|---:|
| 30° / −10° | 20/32 | 1.593 → 1.513″ |
| 180° / +20° | 28/32 | 2.096 → 2.098″ |
| 300° / −30° | 8/32 | **4.397 → 5.282″** |

At 300°/−30°, all eight jointly accepted attempts come from one position. The post-gate bootstrap is therefore degenerate; its narrow interval in JSON is not strong evidence. At this field, RMS among accepted fits also rises by about 20%. This is why pre-gate results, rejection counts, and per-position data must all be retained.

Only **8/56** synthetic-source fits accepted by the new model fall within the nominal 68% ellipse; the last two fields have 0/28 and 0/8. The quality gate has not calibrated the error budget. Do not use this ellipse as a detection probability or label a result “reliable” merely because it passes the gate.

### Gaia stars held out from alignment

| Field | Computed pairs / attempts | Old → new RMS | Old → new accepted |
|---|---:|---:|---:|
| 30° / −10° | 10/11 | 0.929 → 0.969″ | 9 → 9 /11 |
| 180° / +20° | 11/11 | 1.111 → 1.054″ | 10 → 11 /11 |
| 300° / −30° | 11/11 | 0.200 → 0.228″ | 7 → 8 /11 |

Real-star results are worse in two fields. The 300°/−30° field passes four injection groups but fails the real-star requirement. The 30°/−10° field loses four accepted cases and fails two faint-source groups. The 180°/+20° field is nearly unchanged on injections and passes no injection groups. **No field meets all criteria; the default WISE 0855 fitter is unchanged.**

## Open development cases

- A Gaia outlier in the Barnard field drops from **6.309 → 0.283″** but still fails the gate because the overall fit remains poor.
- Barnard's Star reduces the prediction difference from **2.628 → 1.102″** but is still rejected for residuals, a masked core, and poor model fit.
- A star in RW Aur changes from about **0.105″** error to **3.598″** despite χ²r near 1. The model-disagreement gate rejects it. Low residual alone does not establish a correct position.
- In R Dra, the new model measures all eight heldout stars and six pass the gate; the baseline lacks alignment stars, so no paired comparison or fair injection comparison is available. Do not call a rescued fit proof of higher accuracy.

These examples were used to develop the gate and are not new validation. Final changes were rerun on all development fields; development protocol and code hashes match the locked version. Solver, thresholds, and sample selection were not changed after the three evaluation fields were opened.

## Products

- [Quality-gate demo](https://nosleepclub-nasa-spherex.vercel.app/#quality-validation).
- [Locked protocol](../web/data/quality/protocol.json), [evaluation results](../web/data/quality/evaluation-summary.json), [UI payload and hashes](../web/data/quality/overview.json).
- [Development results](../web/data/quality/development-summary.json) are separate from the new evaluation.

## Limitations

IRLS covariance and alignment remain conditional and do not fully describe neighbor-position errors, color, ePSF, or inter-frame correlations. Passing the gate does not prove source identity or confirm motion. The PSF-broadening test covers only one type of mismatch. Three fields do not represent the full sky; faint, variable, extended, and high-motion sources need separate controls.

The new gate ran fully in this benchmark. For the older WISE 0855 image pair shown in the comparison interface, the web checks only solver/bounds/χ²/S/N recorded in the exported product and says that the full new gate was not run. Do not label that old measurement “reliable” based on diagnostics that were not computed.

## Reproduction

The 0.6.0 image/calibration cache is required. FITS, XML catalogs, and new logs are in Git-ignored `data/raw/quality/` and `data/raw/benchmark/`. Versioned protocols retain manifests, URLs, queries, hashes, star lists, splits, and rules.

```powershell
python -m scripts.prepare_quality_data
python -m scripts.prepare_quality_data --new
python -m scripts.quality_study --develop
# First run only, before a new evaluation:
python -m scripts.quality_study --lock
# An existing protocol is hash-checked and not overwritten:
python -m scripts.quality_study
python -m scripts.build_quality_overview
python -m unittest discover -s tests -v
```

Do not change code or rules after locking and call the results unseen heldout data. After this run, the evaluation set is development data for the next version.

## Next steps

Prioritize **the error budget and image-background model**. Use opened fields to test residuals against position, source density, color, and detector region; distinguish background, ePSF, missing catalog sources, and pixel correlations. The current gate explains rejection reasons but is not a replacement for a sound error model.

Separate covariance calibration from evaluation. After locking the next changes, use unseen fields and different PSF perturbations to check bias, RMS/P90, rejected fits, and brightness-conditional coverage. Promote a default method only if improvement holds on new data without changing denominators and real-star controls do not get worse. This experiment does not confirm WISE 0855 motion.
