# Goal: scientific and operational production readiness

Started 2026-10-30 from `d56a920`. Owner: Codex root. This is the execution ledger for the 20-item review, not a readiness certificate. The public product remains an exploratory observation tool until the scientific gates below pass.

The user authorized implementation, verification, repository updates and deployment. Use the agency-agents specialist methods; at most one supporting agent may be active, using `gpt-6.1-terra` at `xhigh`. Preserve all frozen 0.3–0.9 sources/products. New scientific work uses new modules, outputs and protocols. Never relabel opened fields as unseen validation. No paid service, expanded credential scope or public review sharing is implied.

## Acceptance ledger

| ID | Finding and chosen work | Acceptance evidence | State |
|---|---|---|---|
| 01 | RA/Dec query, time series, spectral/FOV controls and five challenge targets | Coordinate parsing/coverage tests, actual IRSA data, browser journeys including no-data states | Open |
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
| 18 | Task-based accessible frontend | Clear current analysis, default matches primary config, archive separated; keyboard/mobile/browser evidence | Open |
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
- Supporting agent: review/API backend specialist, Terra xhigh, limited to API/tests/contract. Root owns science, frontend and integration.
