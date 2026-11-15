# Real Reference Stars and Source-Presence Checks

Two experiments are complete, but **they are not sufficient to replace the WISE 0855 measurement model or provide a calibrated motion uncertainty**. ePSF interpolation does not improve all metrics on real stars. The source-acceptance rule met its prespecified criterion at 600 µJy in a conditional simulation; recovery at 300 µJy remains very low.

[Open the web report](https://nosleepclub-nasa-spherex.vercel.app/#reference-presence). The **Real stars** tab compares positions with Gaia; **Source or noise?** shows both no-target cases and simulated sources. Full gzip files are downloaded only when their links are selected.

## Configuration locked before the experiments

| Step | Commit | Scope |
|---|---|---|
| Reference-star lock | `71f63ca4bab85e9ee51c539cd46ae5bfd50c8bc2` | 21 stars × 20 exposures × 2 ePSFs; 840 attempts |
| Source-acceptance rule lock | `627fe211bd144d0d0e9f9b5b2042316418c54788` | Two separate random sets, all 7,992 attempts, and prespecified criteria |
| Threshold seal | `6fc5b7c7506333c0f320405718f08ca7d9cfa693` | All 1,998 null calibrations, before validation was generated |
| Export and audit code | `1cac567` | BVLS at saved solutions; QR and score recomputation from saved data |

The lock commits were created locally before their corresponding steps, then added to GitHub history with the release. This is not an external study preregistration. Both experiments use WISE images already opened; **no queries, pixel downloads, or measurements were made for the 30 new calibration/validation/holdout fields**. Earlier 0.3–0.9, linked-flux, and neighbor-intervention products remain unchanged.

Detailed protocols: [real stars](REFERENCE_STAR_PROTOCOL.md), [source presence](SOURCE_PRESENCE_PROTOCOL.md). The design hashes source, tests, protocol, opened products, and raw inputs. The pinned packages are used at runtime; each CLI worker requests one numerical thread. This is a configuration request, not a measurement of the number of threads used by every backend.

## 1. Positions of real stars

All 21 stars previously selected from the images and all 20 D6 QR2 exposures were retained. Each star was measured independently in each exposure with the nearest and interpolated ePSF. Both branches use the same pixels, original VARIANCE, neighbor list, and background plane. Target and neighbor fluxes are fit with signed values; no WISE spectral constraint is used.

Gaia positions were propagated to IMAGE MJD-AVG UTC. For the 14 stars that had participated in alignment, the evaluated star was excluded from its own translation solution; the seven with the old heldout label use the old training stars. The old labels are retained for provenance, **but these are not unopened validation stars**. Catalog five-parameter errors retain temporal correlation across the 20 times in each separate 40×40 matrix; this is not total centroid/alignment covariance.

| Denominator | Result |
|---|---:|
| Prespecified attempts / terminal records | 840 / 840 |
| Completed fits / failed fits | 718 / 0 |
| Preparation failures retained | 122 |
| Star × image pairs with both branches complete | 359 / 420 |
| Pairs passing the numerical screen in both branches | 357 / 420 |
| Stars with at least one completed pair | 19 / 21 |

The 122 failed attempts comprise **116 cutouts without enough image margin** and **6 without valid pixels around the predicted center**. They correspond to 61 rejected pairs; no replacement stars were selected and no easier conditions were rerun. The two stars without results retain `0/20` rows and undefined values in the web/JSON tables. One star has only two valid pairs; its temporal stability cannot be inferred.

| Same 359 completed pairs | Nearest ePSF | Interpolated ePSF |
|---|---:|---:|
| Radial RMS against Gaia (″) | 0.934327 | 0.924057 |
| Radial median (″) | 0.380255 | 0.345538 |
| Radial P90 (″) | 0.876152 | 0.942167 |
| East / north mean (″) | −0.017431 / 0.073362 | −0.022827 / 0.082513 |

Interpolation slightly lowers RMS and median but **increases P90**, so it was not selected as the new ePSF. Switching between the two ePSFs shifts position by a median of **0.066879″**, with a maximum of **0.431565″**. This is model sensitivity in the inspected sample, not an independent WISE 0855 error estimate.

On only the same 357 pairs that pass the numerical screen, RMS is **0.603717″ / 0.588622″** and P90 is **0.859338″ / 0.897138″**. The two numerically rejected pairs remain part of the 359; the default interface retains every completed pair. Passing the numerical screen does not establish source identity, as shown by the 16.8″ failure in the [earlier pilot](NEIGHBOR_INTERVENTION_RESULTS.md).

The audit reconstructs samples and templates at saved positions, model/residual, linear-system KKT conditions, IRLS path, and costs for successful final starts using independent BVLS. Preparation failures are replayed; optimizer failures retain their input/provenance and are not retried. Position Jacobian/rank has not been independently recomputed. Complete records, reconstructable models, and astronomical accuracy are distinct claims.

The [additional science audit](evidence/0.10/reference-presence-science-audit.json) confirms that **6,459 successful final starts** were replayed and **3 failed final starts** were retained. The largest cost difference is `4.55e-13`, and the largest column-scaled KKT violation is `8.47e-15`. These are numerical differences, not positional errors.

Remaining limits include a single previously opened field, stars selected from images earlier, varying numbers of images per star, and shared errors between stars/exposures. Do not treat 718 fits as 718 independent observations. Upstream WCS/ePSF may use Gaia; membership of the upstream training set is unknown. Position propagation uses first-order Earth parallax/proper motion, without a complete observer/perspective/radial-velocity model. Residuals include those effects, alignment, and image modeling; they cannot all be attributed to ePSF.

## 2. Threshold calibration and source-presence validation

The experiment uses an already opened strict layout with two before and two after images. For each ePSF branch, it searches a fixed grid of 441 positions. Signed scores are computed after projecting out background/neighbor nuisance terms; the threshold-learning step jointly includes all searches, both epochs, and both ePSFs. This tests target presence, not centroid or linked motion.

Calibration contains 999 nulls per background type, **1,998/1,998** total, with no errors. The threshold is the maximum across both null cases: **17.70381304535502**. It is not S/N, a sigma level, or a detection probability. The seal records `validation_generated: false` as the state **at the time of sealing**, before validation; that field is not changed after study completion.

The separate validation set contains **5,994/5,994** attempts, with no errors. Each case below has denominator 999, uses a PCG64 stream distinct from calibration and earlier studies:

| Validation scene | Accepted /999 | Observed rate | One-sided 97.5% bound | Prespecified criterion |
|---|---:|---:|---:|---|
| Plane, no target | 0 | 0% | False alarm ≤0.3686% | Pass ≤1% |
| Quadratic, no target | 0 | 0% | False alarm ≤0.3686% | Pass ≤1% |
| Plane, 300 µJy | 46 | 4.6046% | Recovery ≥3.3906% | Report only |
| Plane, 600 µJy | 928 | 92.8929% | Recovery ≥91.1196% | Pass ≥80% |
| Quadratic, 300 µJy | 55 | 5.5055% | Recovery ≥4.1741% | Report only |
| Quadratic, 600 µJy | 870 | 87.0871% | Recovery ≥84.8479% | Pass ≥80% |

No observed false alarms does not mean the true false-alarm rate is zero. Binomial bounds are calculated for each case. The two null 97.5% bounds support a simultaneous statement of at least 95% across the two prespecified null cases; **they do not combine all four gates into one 95% confidence claim**. An error counts as a false accept for a null case and a miss for a positive case, so results cannot be improved by dropping failed attempts.

This is a step forward for the conditional simulation rule at 600 µJy. Most 300 µJy sources are missed, and false alarms on the real sky have not been validated. **This threshold is not applied to confirm or filter detections in the WISE workspace.**

Gaussian truth is pixel-integrated and comes from a different family than the fitter. Noise uses a Gaussian scale from observed VARIANCE, and the source/neighbor Poisson ramp is idealized and conditionally bound to gain. The scorer uses **the original observed VARIANCE**, not the generator's oracle error. That VARIANCE may already include photon noise from real sources; it is not a validated decomposition of detector noise. Null cases have no target but retain neighbors.

The independent audit reconstructs templates/native geometry, uses QR to check the SVD projection, and recalculates all **7,992/7,992** scores, winning grid positions, and decisions from saved vectors. Data, source/gain/background hashes, and seeds are checked. The audit **does not regenerate noise from the RNG**, measure covariance coverage, or make 7,992 noise realizations into 7,992 independent sky fields.

The closest validation score is **0.0091881** score units from the threshold; no decision is close to the threshold within the rounding-level replay difference of QR.

## Data and verification

- Real stars: [overview](../web/data/reference-stars/overview.json), [design](../web/data/reference-stars/design.json), [840 records/audits and catalog covariance](../web/data/reference-stars/records.json.gz), **14,164,757-byte gzip**.
- Source presence: [overview](../web/data/source-presence/overview.json), [design](../web/data/source-presence/design.json), [threshold seal](../web/data/source-presence/threshold.json), [all 7,992 attempts and geometry](../web/data/source-presence/records.json.gz), **71,148,124-byte gzip**.
- Compressed and decompressed SHA-256 hashes are recorded in each overview. Raw FITS and per-attempt journals stay in Git-ignored `data/raw/`. The browser downloads only the two overviews when the section is opened; it does not automatically extract or download the larger audits.

With raw cache files carrying the expected provenance, rerun the checks/export from saved results:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.publish_reference_stars --protocol-commit 71f63ca4bab85e9ee51c539cd46ae5bfd50c8bc2
.\.venv\Scripts\python.exe -B -m scripts.publish_presence_study --protocol-commit 627fe211bd144d0d0e9f9b5b2042316418c54788 --threshold-commit 6fc5b7c7506333c0f320405718f08ca7d9cfa693
```

These commands do not refit positions, generate new noise, or open new fields. Runtime/parameters must match the journal. [Product tests](../tests/test_reference_presence_products.py) check hashes/streamed extraction, locked source, and denominators without needing raw FITS.

## Next milestone and acceptance conditions

The next milestone is **to learn a constrained ePSF correction on a separate development star set, then test it on stars held out from training, with shared alignment covariance included**. Lock the basis/complexity, split by source/exposure as appropriate, and preserve masks before fitting. Do not choose a model solely because its aggregate RMS looks better.

Conditions for proceeding: report the full denominator/abstentions; improve both absolute error and distribution tails on an independent test set; preserve sources and flux in signal-preservation controls; model temporal/alignment correlations and test covariance coverage. Stars/fields already viewed remain development data. Only after locking the evaluator, power, error budget, support domain, and overlap may the reserved **12 calibration, 12 validation, and 6 holdout fields** be opened.

The [20-item readiness table](PRODUCTION_READINESS.md) remains open. Production recovery/rollback, representative load, SLOs, and source licensing also remain to be completed; passing a simulated gate does not close them.
