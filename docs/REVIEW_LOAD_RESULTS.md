# Small-Load Baseline for the Review API

Protocol and code were locked at `d7fd8f93595301e4f8a3f7b5700af5bc046ce2dc` before the single run from **21:21:16 to 21:23:18 UTC on 30 October 2026**. The public target remained API commit `80324933bfab21a73a0a2e3f05c447b99f2a81d2`; no credentials were exposed, MongoDB was not changed, access was not opened, and existing review data was not used.

The [full receipt](evidence/0.10/review-load-8032493.json) retains all 60 requests and independently recalculated percentiles, concurrency, spacing between batches, and source hash at the locked commit. Raw SHA-256: `e9245bd39cf2af3b036dcc2b70f0c0cba792094211fd36456d0716428fe4c0c7`.

| Measurement | Result | Pre-locked gate |
|---|---:|---:|
| API HTTP 200, correct contract and commit | 60/60 | 60/60 |
| GET, including new sessions | p95 1.937 s, n=36 | ≤3 s |
| POST | p95 0.203 s, n=12 | ≤5 s |
| DELETE | p95 0.141 s, n=12 | ≤5 s |
| POST and DELETE combined | p95 0.188 s, n=24 | ≤5 s |
| QA sessions verified empty afterward | 12/12 | 12/12 |
| Additional cleanup requests / unexpected errors | 0 / 0 | No retry required |

**The predefined baseline passed.** Twelve independent guest sessions ran in four groups of three, with five GET–POST–GET–DELETE–GET cycles per group. No more than three requests were in flight at once; the next group began at least six seconds after the previous one finished. Only 12 QA reviews with random content were created, with no more than three existing at once; each was deleted by its test-created ID. The receipt contains no cookie, note, review ID, or raw scope. The script did not retry to improve latency.

This is an observation of about two minutes at average load below 0.5 requests/s from one client. It does not measure high concurrency, quota saturation, near-full storage, users in multiple regions, failover, or an SLO over time. IRSA 502/504 errors from the previous release remain documented; this baseline measures only the review API, not IRSA or frames. Backup, production recovery, deletion reconciliation, and rollback remain open criteria. Do not infer maximum throughput or uptime from 60 requests.

Next operational step: define a representative workload and longer observation window, then measure each endpoint/load level and error rate before setting an SLO. Also prepare a recovery drill in a database sandbox with encrypted storage, key custody, retention, and RPO/RTO defined. This baseline does not remove those gates.

See the [protocol](REVIEW_LOAD_PROTOCOL.md), [20 criteria](PRODUCTION_READINESS.md), and [runbook](OPERATIONS.md).
