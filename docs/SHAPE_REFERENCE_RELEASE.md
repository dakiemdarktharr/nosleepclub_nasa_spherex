# Release receipt — MIT and gated shape/reference checkpoint

The [public demo](https://nosleepclub-nasa-spherex.vercel.app/#shape-validation)
serves main **57e7bb1fe34c21685bb3b84e1bde466aeeddde5d**. This receipt is
archived after verification; committing documentation does not mean that
documentation commit was the deployed application revision.

[PR #12](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/pull/12)
merged tested head `595f9a80b1d6299b0383824fb10f15340d633a6d` into main.
Owner-approved MIT applies to original code/documentation; NOTICE keeps
external materials separate. Maintainer write delegation was disabled.
Required checks and branch protection were preserved.

- [CI 41158995062](evidence/0.10/ci-pr12-595f9a8.json): 528 Python cases,
  515 passes and 13 optional raw-cache/photutils skips; all six actual Mongo
  fixture cases passed. Six Node 24 suites passed.
- [Production metadata](evidence/0.10/deployment-57e7bb1.json):
  `dpl_ECAECDR8B766cSq1nTkGeQueaXwH` READY with the canonical public alias
  and exact main source SHA. Preview READY metadata was observed; no protected
  preview was fetched or share link created.
- [Public verifier](evidence/0.10/production-57e7bb1.json): **79 responses**,
  including **63 exact Git-blob assets**, all API commit headers and a fresh
  QA review's stable ID, expiry, owner/Origin isolation, stale-analysis
  rejection and deletion. QA cleanup was verified; checkout was clean at launch.
- Both initial upstream GETs, `/api/observations` and `/api/frame`, returned
  **502 / upstream_unavailable**, then succeeded on the one allowed retry each.
  All responses and request IDs remain in the receipt. Passing a retry-aware
  smoke is not an uptime, latency SLO or upstream-reliability acceptance.
- [Public browser](evidence/0.10/shape-production-browser-57e7bb1.json) shows
  the refused calibration, all 252 assessment cells deferred, seven unevaluated
  sources, two mode-failure rows and nominal reference chi²/dof 1.71. The
  [screenshot](evidence/0.10/shape-production-57e7bb1.png) preserves this state.
  [Local keyboard/mobile checks](evidence/0.10/shape-local-browser.json)
  include Enter disclosure controls and ArrowRight table scrolling without
  page-wide overflow; viewport was reset. No full screen-reader/WCAG claim.

The scientific conclusion remains [SHAPE_REFERENCE_RESULTS.md](SHAPE_REFERENCE_RESULTS.md):
one conditional shape candidate is **refused**, not promoted. The separate
baseline covariance is numerically reproducible but omits noise dependence
of legacy registration and neighboring-source geometry. WISE measurements,
the prior presence threshold and earlier frozen products remain unchanged.
All 30 prospective fields remain unopened. The 20-item goal is incomplete;
scientific generalization, total calibrated uncertainty, production recovery,
representative load/SLO and complete accessibility are still outstanding.

Immediate follow-up: distinguish genuine profile basins from finite-start
solver/flat-region effects for the two competing cells using frozen native
pixels and same-exposure/adjacent-exposure controls. Separately diagnose the
two transient upstream failures before choosing transport/caching changes.
