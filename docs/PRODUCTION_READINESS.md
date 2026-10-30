# Goal: scientific and operational production readiness

Started 2026-10-30 from `d56a920`. Owner: Codex root. This is the execution ledger for the 20-item review, not a readiness certificate. The public product remains an exploratory observation tool until the scientific gates below pass.

The user authorized implementation, verification, repository updates and deployment. Use the agency-agents specialist methods; at most one supporting agent may be active, using `gpt-6.1-terra` at `xhigh`. Preserve all frozen 0.3–0.9 sources/products. New scientific work uses new modules, outputs and protocols. Never relabel opened fields as unseen validation. No paid service, expanded credential scope or public review sharing is implied.

## Acceptance ledger

| ID | Finding and chosen work | Acceptance evidence | State |
|---|---|---|---|
| 01 | RA/Dec query, time series, spectral/FOV controls and five challenge targets | SKY_EXPLORER.md; five live QR2 queries + ten FITS/PNG hashes; BROWSER_VERIFICATION.md; production-c88fe57.json confirms real API/display assets. Spectral labels are detector metadata, not source-level band matching | Verified for observation/display workflow |
| 02 | WISE 0855 scientific contract and uncertainty budget | Conditional/raw/calibrated uncertainty distinguished; target-like independent controls and successful release gate | Open |
| 03 | Per-exposure time model and identifiable motion/parallax | ASTROMETRIC_TIME_MODEL.md; 31 real headers and synthetic withheld predictions; actual source fit with full covariance still pending | In progress |
| 04 | Local spectral compatibility and chromatic null tests | Per-source CWAVE/CBAND audit, leave-band-out controls; response limits explicit | Open |
| 05 | ePSF uncertainty and spatial/temporal residual diagnostics | Independent reference-star tests, centroid normalization, measurable bias improvement | Open |
| 06 | Background bias and foreground/signal preservation | Original/model/residual/mask audit, interventions on opened data, signal-throughput tests; EBL science remains separately scoped | In progress |
| 07 | Missing/blended neighbors and source identity | Crowding/contrast stress tests with uncertain positions; unresolved cases abstain | In progress |
| 08 | Correlated reference-frame uncertainty | Joint sensitivity/block resampling and heldout spatial/color/time residual checks | Open |
| 09 | Robust-fit uncertainty, multimodality and S/N interpretation | Solver modes/boundaries and resampling include nuisance/weights; empirical coverage | In progress |
| 10 | Covariance calibration beyond S/N/MAD | Calibration-only observed features; field/cell 50/68/95% coverage, support and area tradeoff on sealed validation | Open |
| 11 | Realistic, independent injections | SOURCE_RAMP_NOISE.md provides tested ideal source-only Poisson primitive; actual gain, independent PSF/SED/phase/motion and real-source controls pending | In progress |
| 12 | Independent sampling and generalization | INDEPENDENT_FIELD_SELECTION.md reserves 30 prospective fields (12/12/6), metadata geometry only. Full protocol, observation overlap, power and independent outcomes pending | In progress |
| 13 | Non-tautological scientific promotion gates | Absolute bias/error and interval-precision gates, per-field failure cannot be pooled away, baseline self-comparison never certifies accuracy | Open |
| 14 | Blind detection, false alarms and optional vision ranking | Object-level completeness/precision and false alarms per area/visit; motion/variability/artifacts separated | Open |
| 15 | Isolated, resumable science jobs | SCIENCE_JOBS.md; two real fields byte-identical serial/concurrent on Windows; timeout/cancel/death/recovery tests. Single host only, whole-job retry; production orchestration pending | In progress |
| 16 | Reproducibility, release provenance and documentation | Clean-environment check, immutable input versions and release manifests; stale instructions corrected; license decision recorded | Open |
| 17 | Review lifecycle and scientific follow-through | REVIEW_API_CONTRACT.md; real JS race tests and production-c88fe57.json verify stable IDs, expiry, cross-owner isolation, stale POST rejection and deletion. Guest sessions, no expert assignment or public sharing | Verified for private guest review lifecycle |
| 18 | Task-based accessible frontend | Clear current analysis, default matches primary config, archive separated; BROWSER_VERIFICATION.md local keyboard/mobile; full accessibility pending | In progress |
| 19 | Guest security and abuse resistance | Cross-owner/Origin/input tests, strict environment/IP contract, atomic owner/global limits; four real replica-set concurrency tests and production transaction smoke. Load/attack-volume behavior still pending | In progress |
| 20 | CI, observability, load, recovery and release | Two required CI jobs and branch protection verified; structured logs and production receipts. Restore/rollback/load/SLO still unverified | In progress |

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
- PR #1 then passed both required checks and merged at `63b1bd7`; production deployment `dpl_pHZ12WnQeRriKjmjezZPfA1rSPDF` is public. User-approved branch protection is active. An initial 24-response production smoke passed real Mongo review isolation/expiry/deletion and source hashes, after an earlier IRSA 504. A committed-verifier receipt with API commit headers is being added; no SLO is inferred from a smoke pass.
- Truth-point study `215dbfa` completed 384 draw IDs with matched/old truth conditions. At low SNR the matched GN/F trace is 1.476–1.559, near a prediction around 1.50; Hessian and score variance are reported separately. This is not centroid coverage or a complete explanation of pipeline error. See FLUX_INFORMATION_RESULTS.md.
- Offline single-host science jobs now isolate each cached-field audit in its own process, verify input/output identities, prevent duplicate publication, and handle timeout/cancel/parent death. Two real fields produced byte-identical concurrent/serial outputs on Windows. See SCIENCE_JOBS.md; distributed/cloud orchestration and host recovery remain open.
- The next covariance study is locked at `3995f2e`: 128 new noise draws per six opened-field cases, fixed-final-weight exposure sandwich, unchanged point fit, and separate centroid/registration covariance. No new validation fields have been opened.
- 158 local Python tests passed before the newly added flux-product and sandwich tests. Keyboard focus-ring remediation and partial contrast checks are recorded in ACCESSIBILITY_CHECK.md; a full screen-reader/reflow audit remains open.
- PR #2 passed 167 Python tests on Linux (four raw-cache skips) and both JS suites, then deployed `fbdc9b8` as `dpl_6PLkero2XYy2X9ZYGrGKJMUcFmKe`. The committed verifier passed 24 production response checks with matching API commit headers; immutable receipt: docs/evidence/0.10/production-fbdc9b8.json. The atomic-quota update is separate and still awaits real replica-set CI and deployment verification.
- PR #3 passed 182 Python tests (four raw-cache skips), including four real replica-set concurrency tests, and JavaScript checks. It deployed atomic quotas at `c88fe57` / `dpl_CWVm5qSJb2d7npBPv1ngV7vw3HGG`; 24 production checks passed with exact API commit headers and disposable QA cleanup. CI startup initially failed on an incompatible Linux kernel, then a procfs test race; both causes and corrections are recorded without suppressing checks. No M0 load/failover claim.
- The locked sandwich study completed 768 new-noise draws plus six separate original-background checks. All three covariance methods support 128/128 draws per case, but low-SNR sandwich 68% coverage remains 73/128, 71/128 and 65/128, not a scientific promotion. Full paired records, mode diagnostics, area and all selection denominators are in SANDWICH_RESULTS.md and the public audit JSON; the web uses a lightweight overview.
- A new pure time/GLS module and 31-header WISE audit distinguish absolute MJD-AVG from exposure start, reject degenerate designs and accept cross-exposure covariance. Synthetic recovery/withheld predictions are tested, including covariance validation across scales. This has not measured a source or replaced the frozen fit. The new SPIFF inventory is development reference data, not external astrometric validation.
- A source-only ideal Poisson ramp primitive now matches the official variance formula and independent OLS derivation for n=2/3/75. Six tests cover moments, units, masks and discrete Poisson support. It has not yet been matched to real gain maps or used in an image study; no claim that item 11 is closed.
- A deterministic geometry-only selection reserves 12 calibration, 12 validation and 6 final-holdout centers. Offsets 0–9 are excluded by cached-center proximity; +10 degrees is the first admissible global offset. No new field query/pixel/outcome was opened. Source/selection must be committed and verified before metadata acquisition; full analysis protocol and overlap/power gates remain separate.
- PR #4 passed 208 tests in CI (five raw-cache skips) and both required jobs, then deployed `c65d79b` / `dpl_EqFMcAJ6TgkqAYP6LwtJuApxrr5Z`. New table controls were verified in the public browser; 30 response checks validated all new static products, API commits and QA cleanup. A previous two-frame-502 failure receipt is retained; cause was not determined from the old aggregated category.
- A test-only Fernet/BSON backup primitive is restricted to disposable UUID loopback fixture databases, not production. Unit checks pass locally; real replica-set restore checks and the refined severity/error-code telemetry are awaiting CI/deployment. No production backup, deletion reconciliation, recovery objective or service load acceptance is claimed.
- Recovery fixture source `8f0afc0` passed both real Mongo restore tests in CI 41095342121, within 220 tests (five raw-cache skips). The first real run exposed an unsupported PyMongo keyword that fake tests missed; the API call was corrected, not skipped. Production backup and deletion reconciliation remain open.
- The new mask audit finds no FULLSAMPLE pixels in the 31 WISE cutouts, while confirming that the old policy incorrectly permitted that flag. Frame API 1.1 now excludes it and publishes mask policy/counts; mixed policies cannot be compared in the UI. Frozen science products remain unchanged. A separate background-only SOURCE exclusion is a proposal, not silently applied to a joint fit.
- Native-gain audit matches the header UUID to the official D6 QR2 file, units and hash. Thirty cutouts have positive gain at every target-mask pixel; one has a negative unflagged gain outside the prior target box. Orientation remains conditional on published R6 snapshots, and no centroid or injection study was rerun. This does not close scientific accuracy gates.
- Local suite after the mask/gain work ran 229 cases: 223 passed, six real-Mongo cases skipped locally. Eight mask/gain tests include replay of the 31 raw FITS; the actual explorer path returns correct 1335/34/0 pixel counts, and the JS test rejects mixed mask policies. New CI and release receipts remain necessary for the current head.
