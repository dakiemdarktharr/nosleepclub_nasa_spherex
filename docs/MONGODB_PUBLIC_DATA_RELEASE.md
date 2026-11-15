# Public Data Migration to MongoDB — 31 October 2026

Production: [open demo](https://nosleepclub-nasa-spherex.vercel.app/#home), commit `20bf9ae79c9cc50898d71afbf6778f3f8af26078`, deployment `dpl_6uuZugMniSWj2of6AE59DX5ZTfSM`. Source was merged through [PR #16](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/pull/16), [#17](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/pull/17), [#18](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/pull/18), and [#19](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/pull/19).

## Measured results

| Area | Result |
|---|---|
| Public data | 213 Git blobs, 212,215,160 original bytes |
| Mongo transport | 426 parts, 127,478,741 compressed bytes |
| Canonical public | 213/213 byte/hash matches; 607 responses: 213 × 307, 394 × 200; no retries |
| Vercel static output | 41 files, 615,668 bytes; no `data/` |
| Mongo database | About 170 MB logical, 339 MB allocated; one M0, no new cluster/tier |
| Final software CI | 623 Python cases: 610 passed, 13 optional raw-cache/photutils skips; all six real Mongo fixture cases passed; 11 Node programs passed |
| Production smoke | 173 contract-passing responses; 84 payloads hash-checked, three large audits metadata/redirect-checked in smoke and full-byte checked in canonical reconciliation |

[Canonical receipt](evidence/0.10/mongo-canonical-20bf9ae.json), [smoke](evidence/0.10/mongo-production-20bf9ae.json), [CI](evidence/0.10/mongo-ci-chain.json), [capacity](evidence/0.10/mongo-capacity-after-import.json), [remote build](evidence/0.10/mongo-deployment-20bf9ae.json).

Smoke included 99 HTTP 200s, 70 redirects 307, two intentional 400s, and two intentional 403s; no retries. QA reviews were created/read/deleted; checks covered stable IDs, expiry, scope/Origin isolation, stale analysis, and cleanup. HTTP 200 counts do not establish astronomical accuracy or uptime.

## Two flows and audit download

WISE was tested from data selection → R01 selection → limits → Mongo-only save → JSON export → QA review deletion; history was 0 at start and end. A draft was tested across reload before saving in phase 1; draft logic did not change during cutover. Residual did not incorrectly show the WISE vector.

IRSA reused the already opened region RA 350°, Dec 35°, QR2/D6, 1–30 June 2025: 18 observations. Select `2025W26_2A_0314_1` / `_2`, inspect limits, write a note, and export JSON in the final build. Blinking and query/date/pair draft across reload were tested in phase 1. Final build shows both UTC date/time and image A/B; IRSA notes are not sent to the WISE review API. QA draft was deleted. The 30 reserved fields were not queried.

The signal-control audit was downloaded in the browser as 20 parts; Save was enabled only after per-part/full-file hashes matched. The downloaded file contains 10,046,627 bytes, SHA-256 `ef757d6c605f623ecfae35c0c4ebdc43b8ab3e1308adb741bc9be7d8d2d555a0`, matching the locked Git product. Desktop and 390 × 844 viewport were checked; the 375/375 px document did not overflow horizontally and the canvas was not covered by the continue button. Viewport was reset. [Browser evidence](evidence/0.10/mongo-browser-20bf9ae.json).

## Import permissions and retained failures

Mongo URI remains only in production Vercel. The repository owner approved a temporary GitHub Actions capability; the permit is tied to the manifest hash, accepts only pinned public bytes, is insert-only, and lasts at most 45 minutes. Permit was removed at 14:21:17 UTC; the old key returns 403, and the GitHub Secret and local key file were deleted. [Revocation receipt](evidence/0.10/mongo-import-revocation.json).

- The connector rejected a large batch with 413 before import. Local transfer timed out; a 512 KiB block later took 41.312 seconds. Upload was moved to a runner under authorization; Mongo credentials were not moved into CI.
- [Import](evidence/0.10/mongo-import-41208174465.json) completed all 426 parts, but [initial reconciliation](evidence/0.10/mongo-initial-reconciliation-41208174465.json) stopped after 32 products because the CDN gzip-compressed NPZ data. The verifier was corrected for HTTP negotiation while retaining MIME/encoding and byte/hash checks. [Pre-cutover](evidence/0.10/mongo-reader-before-cutover.json) passed 213 products with 396 attempt records, including two retained read timeouts and two retries. [Source binding](evidence/0.10/mongo-reader-source-binding.json) matched the verifier file in commit `1862358`; the file was still in the working tree when run.
- Cutover `7efcf6b` had a [400 smoke failure](evidence/0.10/mongo-production-7efcf6b-failed.json) and [canonical failure](evidence/0.10/mongo-canonical-7efcf6b-failed.json). Wildcard rewrite was incompatible with the parser; the exact internal query was not recorded. It was rolled back to static `2f1442a`, the manifest HTTP 200 was verified, and then 213 specific redirects by hash were used. Query validation was not relaxed.

Failures were retained, not replaced with a successful run. Final smoke compared Git blob and API commit; `worktree_dirty` was due to an uncommitted copy of the failure receipt, not a runtime-source change. The documentation/evidence archive was committed after production to avoid a deployment cycle just to store receipts.

## Limits and next milestone

The **static output of the new build** was reduced; datasets were not removed from Git/source checkout or older deployments retained for rollback. Python functions still show bundle warnings of 261–297 MB before optimization; final deployed byte size per function has not been measured. Do not add the 616 KB static shell as if it were the total Vercel project size.

M0 has no large-load, failover, long-term SLO, or production-recovery certification. Agent browser checks do not replace a study with real newcomers, screen-reader testing, or a full browser/device matrix. IRSA remains visual image comparison only; WISE measurements retain uncalibrated model error. Do not change threshold/PSF/covariance, open the 252 assessment cells or 30 reserved fields, or claim a detection.

Proposed next milestone: separate reader/review dependencies from FITS processing to reduce the Python bundle. Accept based on before/after Vercel bundle sizes, reader/review without unnecessary Astropy/Pillow, and all bytes/hashes, private-review lifecycle, and two end-to-end flows passing. Then lock a load test to decide scaling from measured latency/cache/memory rather than duplicating clusters by intuition.
