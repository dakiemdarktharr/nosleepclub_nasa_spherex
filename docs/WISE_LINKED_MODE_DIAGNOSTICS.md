# Post Hoc Replay of WISE 0855 Modes

This is a **post hoc** diagnostic after development results were viewed; it is not a prespecified test, independent validation, or astronomical detection evidence. It recalculates the linear profile only at two saved modes from `strict/after`, using each branch's exact pixels, offsets, nuisance terms, spectral coefficient, and final IRLS weights. It does not re-optimize positions, run Monte Carlo, or open new fields. Each difference below is the second mode minus the mode with the lowest χ² **within that branch**; the two branches order their positional modes differently.

Source checkpoint SHA-256 `a5bffe162ae8ccd88a6fc5311d1e8ddc279c56092b072a782652da5a7f1cfd0a`, protocol commit `cfb9d6a`. [JSON table](../web/data/linked-flux/mode-diagnostics.json) retains design/source/input hashes, URL/hash for both exposures, native coordinates, full unrounded values, and replay checks. The script refuses to publish unless cost and flux replay pass relative tolerance 1e−7 and absolute tolerance 1e−8. On the current runtime, checked differences for χ², amplitude, flux, error, and weighted residual at saved points are all **0**; χ² for both modes also matches the saved values exactly.

| Branch | Best mode (sky pixel x,y) | Competing mode (x,y) | Total weighted Δχ² |
|---|---:|---:|---:|
| independent | (32.381675; 31.470075) | (32.532657; 31.883726) | +0.037476 |
| shared R7 68 α=0 | (32.481646; 31.844229) | (32.405766; 31.531498) | +0.568008 |

Signed contributions to weighted Δχ² have opposite signs:

| Exposure | independent | shared R7 68 α=0 |
|---|---:|---:|
| 2026W17_1B_0507_3 | +0.554247 | −0.283609 |
| 2026W17_1B_0634_1 | −0.516770 | +0.851617 |

In the independent branch, the two contributions nearly cancel; in the shared branch, 0634_1 has the larger absolute contribution. Each independent amplitude is profiled separately, whereas the shared amplitude is profiled using **both exposures**; therefore the shared table does not represent two independent measurements or identify which exposure causes multimodality. This compares costs at saved positions; it does not measure a causal effect from removing an exposure or changing the model.

In the independent branch, the fraction of squared source-template norm remaining after weighted nuisance projection falls from 0.3813 to 0.0826 for 0507_3 and from 0.5135 to 0.1636 for 0634_1 when moving to the competing mode. Profile flux rises from 399.6 to 792.2 µJy and from 722.7 to 1368.2 µJy; all remain positive. This indicates position/flux sensitivity to the nuisance span, but does not show that a specific neighbor or ePSF is the cause. JSON S/N is conditional amplitude S/N at fixed positions; the two shared S/N values refer to the same flux parameter and are not separate detection evidence.

Each exposure retains three catalog templates as nuisance terms. Entry `J085501.95-071428.2` is about 0.735 and 0.322 sky-grid pixels from the two independent modes; corresponding distances at shared modes are 0.386 and 0.670 pixels. The design-column proximity is consistent with lower projected source information at the mode near this entry. It does not establish that the entry is a distinct astronomical source, cause multimodality, or replace an ablation test/independent data.

With native core radius 2.5 pixels, all four positions in each branch have 100% of geometrically selected core pixels, and no core pixels are FULLSAMPLE; SOURCE appears across the full core. Original residual/error RMS in the core is about 0.80–0.96 for 0507_3 and 1.17–1.22 for 0634_1. A complete core mask does not rule out background, neighbor, or ePSF error; RMS describes the same selected data and is not an independent test.

The two QR3 ePSF zones are 312 and 291: `NSTAR` 433 and 414, `NEFF_MEAN` 5.097 and 5.083, `CWAVE` 4.5832 and 4.6112 µm. The fraction of absolute-summed **raw table** values that are negative is 0.463% and 0.361%; signed table centroids are (−0.0720; −0.0174) and (−0.0913; −0.0163) native pixels. These are signed-table statistics, not corrections or measured physical biases. The native table after interpolation/normalization sums to 1 over the full finite support; raw normalization before division and the selected masked portion are saved per mode. PSF wings, color, SAPM, and QR3-ePSF versus QR2-image differences remain unverified.

Profile-H and Gauss–Newton covariance at one mode describe local curvature under final weights; they do not integrate probability across competing modes, include shared systematics, or have calibrated coverage. This diagnostic provides no basis to call the modes two astronomical sources, decide which position is correct, replace the old measurement, or promote a model to production.
