# Profile Diagnostic Release — 2026-10-31

[Open the product](https://nosleepclub-nasa-spherex.vercel.app/#profile-landscape), select star A/B and **Image rejected by the gate**, then compare it with **Previous image**. Four plots separate original/corrected ePSF and the two saved weight vectors. The numeric table opens with Enter; the separate archive contains both full journals. README/NOTICE were updated. Source code uses MIT; data, font, and Canva rights remain separate.

This milestone was deployed and checked. The overall production goal is still incomplete; no new scientific measurement or error model was accepted.

## Commit, CI, and deployment

- [PR #13](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/pull/13) merged after two required checks. Checked head: `57ba06c9a01812625f869d09307ca39c27285d72`; production main: `da79c6b9b3cb06dfea0126bd88b153d7ce73e89b`. The two Git trees are identical.
- [CI run 41164187761](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/actions/runs/41164187761): 564 Python cases, 551 passed and 13 optional raw-cache/photutils skips. All six real Mongo replica-set cases passed; seven Node suites passed. [CI receipt](evidence/0.10/ci-pr13-57ba06c.json).
- Local run: 564 cases, 558 passed and six Mongo cases reserved for CI. Additional figure-metadata assertions were rechecked with three product cases, then CI checked the full tree. [Local receipt](evidence/0.10/profile-landscape-local-tests.json).
- Vercel production `dpl_7549bc8xMUnG2yV2ukQBQYUirgAp`, configured region `sin1`, READY with the public alias on the expected commit. [Deployment receipt](evidence/0.10/deployment-da79c6b.json). Preview metadata was inspected only; no fetch or share link was created.

The [88 production responses](evidence/0.10/production-da79c6b.json) confirm 74 artifacts byte-for-byte against Git, commits for all three APIs, the FITS/mask contract, and a fresh QA cycle. There were 85 HTTP 200, two HTTP 400, and one HTTP 403 responses under prespecified rejection cases; no 5xx or retry occurred in this run. Checks for stable IDs, expiry, owner separation, Origin, stale analysis, deletion by ID, and cleanup all passed. The worktree was clean when verification began. Mongo credentials were not downloaded locally or into CI; QA used a new session against the production API.

Two earlier 502 errors remain in the old receipt. New telemetry adds only phase/error-type enums; it does not retry or cache. Fault paths were tested offline; this production run did not trigger an upstream error that could confirm an actual cloud failure event. A single successful smoke test does not establish the cause or reliability.

## Science and interface evidence

Protocol `704e3ef` was locked before 112 branches. There are 96 profile branches and 16 missing-input branches; all 14 stars remain in the sample. An independent WLS audit checked 2,760 selected nodes, three-step stencils at 192 fit points, and 480 saved objectives. Source, design, journal, and image files are hashed. See the [English results](PROFILE_LANDSCAPE_RESULTS.en.md) and [hash-locked original results](PROFILE_LANDSCAPE_RESULTS.md).

Positive Hessians and connected regions on a grid do not certify physical solutions, establish coverage, or remove the old gate. The 252 assessment cells and 30 prospective fields remain unopened. No improvement in astronomical accuracy has been demonstrated.

The public browser showed `96/112`, `16`, the unopened reserved section, and a 1,404 px PNG loaded successfully. [Public evidence](evidence/0.10/profile-production-browser-da79c6b.json) and [screenshot](evidence/0.10/profile-production-da79c6b.png) supplement HTTP checks. Local verification checked star/image selection, Enter, Tab, and 390 px reflow; the table has its own horizontal scroll area without page overflow. This is not a complete screen-reader/accessibility audit.

The existing figure dependency file was preserved byte-for-byte. A temporary edit was reverted before release CI; figure inspection metadata was corrected accordingly, with the [receipt](evidence/0.10/profile-figure-environment-correction.json) and Git history retained. Figures were not rerendered and the science journal/gate was not changed.

## Next milestone

Lock a native control for signal, blends, template, and pixel phase using independent synthetic sources. Before running it, specify bias/signal-recovery budgets, source identification, refusal conditions, seeds, and denominators for every condition. Acceptance requires reproducing every attempt, auditing truth/units/masks, reporting failures, and meeting the locked budget; do not use reserved data to select a model.

Production recovery, representative load/SLO, full uncertainty coverage, independent sky validation, and remaining items are still open in the [20-item checklist](PRODUCTION_READINESS.md). Release receipts are stored in a later documentation commit after verification; the public API remains at `da79c6b`, and does not follow the HEAD of the evidence-storage branch automatically.
