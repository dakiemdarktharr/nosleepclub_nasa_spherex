# Goal: scientific and operational production readiness

Started 2026-10-30 from `d56a920`. Owner: Codex root. This is the execution ledger for the 20-item review, not a readiness certificate. The public product remains an exploratory observation tool until the scientific gates below pass.

The user authorized implementation, verification, repository updates and deployment. Use the agency-agents specialist methods; at most one supporting agent may be active, using `gpt-6.1-terra` at `xhigh`. Preserve all frozen 0.3–0.9 sources/products. New scientific work uses new modules, outputs and protocols. Never relabel opened fields as unseen validation. No paid service, expanded credential scope or public review sharing is implied.

## Acceptance ledger

| ID | Finding and chosen work | Acceptance evidence | State |
|---|---|---|---|
| 01 | RA/Dec query, time series, spectral/FOV controls and five challenge targets | SKY_EXPLORER.md; five live QR2 queries + ten FITS/PNG hashes; BROWSER_VERIFICATION.md local query/pin/blink; deployment pending | In progress |
| 02 | WISE 0855 scientific contract and uncertainty budget | Conditional/raw/calibrated uncertainty distinguished; target-like independent controls and successful release gate | Open |
| 03 | Per-exposure time model and identifiable motion/parallax | Design-rank checks and withheld-epoch predictions; unsupported parameters withheld | Open |
| 04 | Local spectral compatibility and chromatic null tests | Per-source CWAVE/CBAND audit, leave-band-out controls; response limits explicit | Open |
| 05 | ePSF uncertainty and spatial/temporal residual diagnostics | Independent reference-star tests, centroid normalization, measurable bias improvement | Open |
| 06 | Background bias and foreground/signal preservation | Original/model/residual/mask audit, interventions on opened data, signal-throughput tests; EBL science remains separately scoped | In progress |
| 07 | Missing/blended neighbors and source identity | Crowding/contrast stress tests with uncertain positions; unresolved cases abstain | In progress |
| 08 | Correlated reference-frame uncertainty | Joint sensitivity/block resampling and heldout spatial/color/time residual checks | Open |
| 09 | Robust-fit uncertainty, multimodality and S/N interpretation | Solver modes/boundaries and resampling include nuisance/weights; empirical coverage | In progress |
| 10 | Covariance calibration beyond S/N/MAD | Calibration-only observed features; field/cell 50/68/95% coverage, support and area tradeoff on sealed validation | Open |
| 11 | Realistic, independent injections | Source-noise propagation without double counting, PSF/SED/phase/motion diversity plus real-source controls | Open |
| 12 | Independent sampling and generalization | Field/time/exposure blocked splits, power calculation, blind external truth, untouched final holdout | Open |
| 13 | Non-tautological scientific promotion gates | Absolute bias/error and interval-precision gates, per-field failure cannot be pooled away, baseline self-comparison never certifies accuracy | Open |
| 14 | Blind detection, false alarms and optional vision ranking | Object-level completeness/precision and false alarms per area/visit; motion/variability/artifacts separated | Open |
| 15 | Isolated, resumable science jobs | Concurrent fields never share mutable WCS; bounded work, idempotent artifacts and visible failure states | Open |
| 16 | Reproducibility, release provenance and documentation | Clean-environment check, immutable input versions and release manifests; stale instructions corrected; license decision recorded | Open |
| 17 | Review lifecycle and scientific follow-through | Stable owner-scoped IDs, deletion across analysis versions, explicit expiry and review export/history | In progress: API specialist |
| 18 | Task-based accessible frontend | Clear current analysis, default matches primary config, archive separated; BROWSER_VERIFICATION.md local keyboard/mobile; full accessibility pending | In progress |
| 19 | Guest security and abuse resistance | Cross-owner/Origin/input tests, trustworthy rate identity, no secret logging, explicit guest limits | In progress: API specialist |
| 20 | CI, observability, load, recovery and release | Required automated checks, sanitized diagnostics, tested restore/rollback and measured service objectives | In progress: API specialist (logging) |

`Implemented` is not equivalent to `Verified`. An item closes only with its linked acceptance evidence. Failure to achieve a scientific threshold stays visible. Do not count a refusal/guard alone as reduced measurement bias.

## Execution order

1. Reproduce w350 and comparison-field failures without modifying 0.9. Diagnose masks, crowding, per-frame influence and centroid modes. Fix review lifecycle concurrently in the bounded specialist task.
2. Improve estimators/uncertainty using opened data only. Establish absolute scientific budgets, blocked splits, and a preregistered new validation protocol before touching its measurements.
3. Complete coordinate/time-series/review journeys and isolate science execution. Add target coverage and API/product contracts with real data.
4. Run scientific external validation and blind search evaluation. Publish all denominators/failures; promote only supported capabilities.
5. Verify security, CI, reproducibility, backup/restore, load and rollback. Deploy the verified milestone and record exact commit/deployment/hash receipts.

## Definition of done

All 20 acceptance items have evidence or an explicitly approved scope decision; the intended web workflow works from user coordinates; scientific performance is independently measured in a stated domain; unsupported claims/inputs abstain; the service meets its measured operating objectives. No completion based only on test counts, interface appearance, or cloud READY status.

## Current evidence

- Baseline: `d56a920`, public deployment and locked 0.9 products; scientific gate failed.
- `/goal` created and active. No token limit was requested.
- Supporting work is serial: review/API specialist followed by numerical/statistical specialist, both Terra xhigh. Root owns science acceptance, frontend and integration. At most one supporting agent is active.


## Checkpoint 0.10 in progress

- `a33dd64`: opened-field diagnostic runner and this ledger. `ecd61de`: profile-curvature comparison frozen before its Monte Carlo evaluation.
- `f138e11`: continuous target-ePSF candidate and paired development protocol committed before Monte Carlo. The diagnostic found finite jumps at the old template boundary; padding removes the sampled jumps, but that alone is not a physical PSF or uncertainty validation.
- The paired study completed 384 Gaussian draws plus six original-background checks. Hessian step instability fell from 304/768 to 0/768 epoch fits, while vector RMS increased slightly in all six matched groups. Low-SNR profile 68% coverage remains 31/64, 36/64 and 34/64. No scientific promotion. See CONTINUOUS_EPSF_RESULTS.md and the public paired rows.
- All five challenge targets: 43/42/57/36/89 D6 QR2 observations in the checked queries, ten real cutouts rendered. This verifies data access/display, not source motion or variability.
- Six opened-field cases replay exactly; 64 fresh Gaussian-noise draws/case show raw uncertainty undercoverage in all low-SNR groups. Profile-LR helps partially; full profile Hessian is often step-unstable. No point model/calibrator is promoted. See BIAS_DIAGNOSTICS.md.
- Backend lifecycle, API limits, source-provenance, and JS race controls implemented and tested locally. Review-store/explorer tests execute the real JS with DOM/HTTP test doubles. Full deployment, real Mongo quotas/expiry and browser evidence still being collected.
- 142 Python tests passed locally; both real JS lifecycle/race suites passed in V8. Local browser verified a 77-frame query, two real images with the same contrast, pin/blink, review save/delete, strict WISE default, archived deep link and mobile menu/layout. See BROWSER_VERIFICATION.md; these checks do not close cloud or scientific gates.
- Added CI and operational runbooks. Backup/restore/load/rollback and external scientific acceptance remain unverified. No paid infrastructure or credential scope changed.
- Preview `dpl_HWCYVwHC2banxM1wS1vx2wFHNKyZ` for `0da47d8` built successfully with the three Python functions; live observations and frame calls returned HTTP 200. The frame cutout hash matches local. JavaScript CI passed; Linux Python CI exposed a one-ulp float replay assertion, corrected with 1e-12 relative/absolute float tolerance while preserving exact schema, decisions, counts and hashes. A new full run is required before merge.
