# Workflow UI release — PR #15

[Open the delivered app](https://nosleepclub-nasa-spherex.vercel.app/#home) ·
[PR #15](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/pull/15) ·
[Workflow and capability boundaries](WORKFLOW_UI.md).

The four-screen Data → Compare → Check → Record interface is deployed. Research
reports are a separate, explicitly selected view. This is a verified UI milestone,
not scientific promotion or completion of the production-readiness goal.

| Evidence | Result |
|---|---|
| Tested PR head | `35c7015dd7ecc5aec13d32511c1cde396f7157e2` |
| Delivered main | `ccde9faf914f04e5c9c2b8c9b5f23307787a7966`; tree equals tested head |
| Required CI | [41180088430](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/actions/runs/41180088430): both jobs succeed, 609 Python cases (596 pass, 13 optional raw-cache/photutils skips), all six real disposable Mongo fixture checks pass, ten Node24 programs pass |
| Local regression | 609 Python cases (603 pass, six actual Mongo fixtures deferred to CI), ten Node programs; source syntax, whitespace and frontend/source-product contracts pass |
| Vercel | `dpl_9yCNGvu4VbFcNRrA8j9ZkSzMvYJg`, READY, production target, canonical alias and merge SHA match |
| Public HTTP | 98 retained responses: 94 HTTP200, one upstream HTTP502, two expected HTTP400 and one expected HTTP403. All 83 static artifacts match exact Git blobs; API commit and guest QA lifecycle/cleanup checks pass |
| Retry qualification | One `/api/observations` response was `502 upstream_unavailable`; its single allowed retry returned HTTP200. Root cause is not established. Both responses/request IDs remain; this run is not an uptime or reliability certificate |
| Public browser | Four-screen WISE flow, residual context/overlay isolation, Mongo-connected review UI, legacy profile report/focus, real thumbnails and 390px reflow verified. Mobile canvas ends before the fixed action bar; no horizontal body overflow |
| Real local IRSA flow | 77 observations at already-opened RA350°/Dec35°; exposure pair `2025W26_2A_0314_1` / `_2`; four steps, blink preserving pair, guide preserving source and actual JSON export verified. No WISE review POST is used for IRSA |

Receipts: [CI](evidence/0.10/workflow-ci-pr15-35c7015.json),
[deployment](evidence/0.10/workflow-deployment-ccde9fa.json),
[all production HTTP attempts](evidence/0.10/workflow-production-ccde9fa.json),
[public browser](evidence/0.10/workflow-production-browser-ccde9fa.json),
[local task checks](evidence/0.10/workflow-local-browser.json).
Screenshots: [desktop](evidence/0.10/workflow-production-ccde9fa.png),
[mobile compare](evidence/0.10/workflow-production-mobile-ccde9fa.png).

The verifier starts at the deployed merge commit with a clean worktree. These
receipts are archived afterward in a separate documentation commit; they do not
claim that this later archive commit is the production API SHA. Protected preview
links and credential scopes were not changed.

WISE scientific products, thresholds and source hashes remain unchanged. IRSA
cutouts have display WCS and shared contrast, not new registered astrometry or a
motion fit. Residuals do not inherit WISE motion/SNR, and historical reports do
not analyze the currently selected IRSA images. All 252 assessment cells and
30 prospective fields remain unopened. Private WISE review lifecycle remains;
IRSA drafts are per-query/pair in memory and must be exported before reload.

Next UX acceptance: three astronomy newcomers complete both workflows without
being coached, preserve context while going back, and save/export the correct
record. Full screen-reader/WCAG review, independent scientific acceptance and
operational recovery/load/SLO remain open.
