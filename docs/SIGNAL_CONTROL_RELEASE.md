# Signal-control release — PR #14

The native signal/template/blend/pixel-phase milestone is deployed publicly.
Scientific promotion and the 20-item production goal remain incomplete.

[Open the delivered report](https://nosleepclub-nasa-spherex.vercel.app/#signal-controls) ·
[PR #14](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/pull/14) ·
[Scientific results and next acceptance criteria](SIGNAL_CONTROL_RESULTS.md).

| Evidence | Result |
|---|---|
| Frozen experiment | `9894074fdacbba908b8816d3dbcac1df901731f1`, pushed before 640 scene/noise/fit outcomes |
| Tested PR head | `b47ccdd8570b9cfe17c421c5caa684be9fc8891f` |
| Delivered main | `73ea9a2f2012b30dea5e0b43dd88feccf6d622be`; Git tree equals tested head |
| Required CI | [41169034237](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/actions/runs/41169034237): both jobs succeed; 607 Python cases, 594 pass and 13 optional raw-cache/photutils skips; all six actual disposable Mongo checks pass; eight Node24 suites pass |
| Local regression | 607 Python cases, 601 pass and six actual Mongo fixtures deferred to CI; eight Node24 suites, compilation, syntax, whitespace and published-product integrity pass |
| Vercel | `dpl_FE6jQNxeRdMHDMBeSt6QxPLMVSyD`, READY, target production, canonical alias and merge SHA match |
| Canonical HTTP | 94 recorded responses: 91 HTTP200, two expected HTTP400 and one expected HTTP403. All 80 static artifacts match exact Git blobs; API commit matches main; all guest QA lifecycle/cleanup checks pass. No 5xx or retry in this bounded run |
| Public browser | Incoming hash opens the report; figures load at 1560×1014; truth/scene filters and identity/stress qualifiers work. Cards show 640/640, 70/128, 8/16 and 64/64. Desktop and 390px reflow have no body overflow |

Receipts: [CI](evidence/0.10/signal-ci-pr14-b47ccdd.json),
[deployment](evidence/0.10/signal-deployment-73ea9a2.json),
[all production HTTP responses](evidence/0.10/signal-production-73ea9a2.json),
[browser](evidence/0.10/signal-production-browser-73ea9a2.json).
Screenshots: [desktop](evidence/0.10/signal-production-73ea9a2.png),
[390px mobile](evidence/0.10/signal-production-mobile-73ea9a2.png).
The production verifier started from a clean worktree at the delivered commit;
these release receipts are archived afterward, separately from the deployed tree.

The independent audit verifies synthetic scenes, saved-point WLS and all
denominators; it does not prove a physical PSF or optimizer global optimum. The
absolute noiseless gate **fails 70/128**, while the relative preservation guard
passes 64/64. Neither the passing guard nor cloud READY establishes scientific
accuracy. The old failed calibration gate remains; **252 assessment cells and
30 prospective fields are unopened**. WISE 0855 measurements stay unchanged.

Next: freeze an attribution experiment separating solid-angle convention,
template mismatch and modeled/omitted companion signal loss on opened data.
Candidate-specific absolute fidelity, relative preservation, full calibration
and independent physical-PSF/uncertainty evidence must precede any proposed
reserved-data access. Recovery/rollback, representative load/SLO, orchestration
and full accessibility remain separate open acceptance items.
