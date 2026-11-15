# Fixed-Weight Profile Diagnostic Results

The diagnostic adds context to two multimode warnings in the ePSF fit, but **does not change the failed calibration gate**. On the sampled grid, low-cost regions for the two selected cases are connected at the stated levels. This does not prove that there is only one minimum, or that the two saved solutions are physical minima.

This post hoc study retains all **14 training sources**, two opened exposures, and four ePSF/weight combinations: **112 branches**, including 96 profiles with numeric results and 16 missing-input branches from two sources × two exposures × four combinations. Missing sources remain in the denominator. The 252 corrected assessment cells and 30 independent fields remain unopened.

## Context for the two focus cases

The two stars were selected after viewing the old gate. Both are in exposure `2025W46_2A_0214_3`. Under the published grouping rule based on nine starts, both changed from one to two near-best groups. With corrected ePSF and weights, the difference `F = rᵀr` between the alternative group and saved fit point is **0.357866** and **2.293230**. Their positions differ by **0.307305** and **0.549337 common pixels**, corresponding to approximately **1.8899″** and **3.3784″** at the nominal 6.15″/pixel grid scale. These are separations on the common grid, not confirmation of two astronomical sources.

The previous gate required every cell with old information to remain numerically supported. These two cells failed with `multiple_near_best_modes`, so assessment could not begin. Across the other 143 comparisons, linear differences had P90 **0.004593** and maximum **0.025339 common pixels**, below the respective limits 0.02 and 0.05. Meeting those two limits does not undo the numerical-support failure. See the [saved gate](../web/data/shape-point-check/calibration-gate.json).

## Four ePSF and weight combinations

G/H denote original/corrected ePSF; G/H weights are the two final Huber vectors saved from the original/corrected fit. Each row evaluates the same two corrected-fit positions. `ΔF` is the alternative minus fit-point cost **within that row**; do not compare F values across rows with different weights as a statistical test.

| Gaia DR3 source ID | ePSF | Weights | Fit-point F | Alternative-point F | ΔF |
|---|---|---|---:|---:|---:|
| 5756942110218608640 | G | G | 127.316034 | 127.889512 | 0.573478 |
| 5756942110218608640 | G | H | 127.316034 | 127.889512 | 0.573478 |
| 5756942110218608640 | H | G | 127.647706 | 128.005572 | 0.357866 |
| 5756942110218608640 | H | H | 127.647706 | 128.005572 | 0.357866 |
| 5756958431094222592 | G | G | 145.850797 | 148.007466 | 2.156669 |
| 5756958431094222592 | G | H | 145.853635 | 148.010295 | 2.156660 |
| 5756958431094222592 | H | G | 145.890409 | 148.183648 | 2.293239 |
| 5756958431094222592 | H | H | 145.893245 | 148.186475 | 2.293230 |

Direct comparison of saved weight vectors, where “changed pixel” means exact floating-point inequality with no post hoc tolerance:

| Source | Exposure | Pixel count | Pixels with changed weight | Max `|wG − wH|` |
|---|---|---:|---:|---:|
| 5756942110218608640 | `2025W46_2A_0214_2` | 144 | 1 | 3.15682×10⁻⁷ |
| 5756942110218608640 | `2025W46_2A_0214_3` | 141 | 0 | 0 |
| 5756958431094222592 | `2025W46_2A_0214_2` | 138 | 0 | 0 |
| 5756958431094222592 | `2025W46_2A_0214_3` | 130 | 1 | 1.06818×10⁻⁴ |

For the first focus at `_3`, the weight vectors are identical, so the two rows only differ by a label and use the same vector. For the second focus at `_3`, one weight changes slightly. Swapping the vectors shows cost sensitivity at the two saved positions; it does not isolate Huber, ePSF, or solver as the cause of the multimode warning.

## Gradient and curvature at the two saved positions

The following table uses **corrected ePSF + corrected weights** at exposure `_3`. “Fit point” is the saved corrected position; “alternative” is the other near-best point, not a new fit. The gradient is the direct finite difference of `F`, in `F/common pixel`; the two λ values are ascending eigenvalues of the direct finite-difference Hessian, in `F/(common pixel)²`. Each row reports the finite-difference step `h` in common pixels.

| Source | Position | h | Gradient `(x, y)` | Hessian eigenvalues `(λ₁, λ₂)` |
|---|---|---:|---|---|
| 5756942110218608640 | Fit point | 0.004 | (−0.001245; −0.001800) | (47.919409; 227.177855) |
| 5756942110218608640 | Fit point | 0.002 | (0.000218; −0.002493) | (47.916124; 227.191921) |
| 5756942110218608640 | Fit point | 0.001 | (0.000583; −0.002666) | (47.915303; 227.195440) |
| 5756942110218608640 | Alternative | 0.004 | (0.003087; −0.008810) | (16.790480; 189.379502) |
| 5756942110218608640 | Alternative | 0.002 | (0.004536; −0.007487) | (16.785640; 189.386218) |
| 5756942110218608640 | Alternative | 0.001 | (0.004898; −0.007156) | (16.784429; 189.387897) |
| 5756958431094222592 | Fit point | 0.004 | (0.003402; −0.006286) | (118.277264; 139.890628) |
| 5756958431094222592 | Fit point | 0.002 | (0.001796; −0.002395) | (118.271325; 139.885419) |
| 5756958431094222592 | Fit point | 0.001 | (0.001394; −0.001422) | (118.269839; 139.884116) |
| 5756958431094222592 | Alternative | 0.004 | (−0.009180; 0.006297) | (23.386575; 105.422728) |
| 5756958431094222592 | Alternative | 0.002 | (−0.006606; 0.003126) | (23.376405; 105.424600) |
| 5756958431094222592 | Alternative | 0.001 | (−0.005963; 0.002333) | (23.373861; 105.425068) |

These gradients and eigenvalues describe the locked finite-difference steps. No stationarity threshold was prespecified, so the table does not conclude that any point “is stationary.” The full Hessian also differs from Gauss–Newton. At `h=0.002`, for example, the Gauss–Newton eigenvalues at the alternative positions are `(99.624876; 179.548504)` and `(62.319367; 162.116370)` for the two sources, in the same curvature units. These matrices are not inverted to create covariance.

To compare all four combinations, the next table uses the same two corrected positions and `h=0.002`. `‖∇F‖∞` is in `F/common pixel`; eigenvalues are in `F/(common pixel)²`. Full tables for all three steps and probes are in the compressed record.

| Source | ePSF/weights | Position | `‖∇F‖∞` | Hessian `(λ₁, λ₂)` |
|---|---|---|---:|---|
| 5756942110218608640 | G/G | Fit point | 0.615427 | (64.819006; 228.889420) |
| 5756942110218608640 | G/G | Alternative | 0.652579 | (14.928862; 184.525387) |
| 5756942110218608640 | G/H | Fit point | 0.615427 | (64.819006; 228.889420) |
| 5756942110218608640 | G/H | Alternative | 0.652579 | (14.928862; 184.525387) |
| 5756942110218608640 | H/G | Fit point | 0.002493 | (47.916124; 227.191921) |
| 5756942110218608640 | H/G | Alternative | 0.007487 | (16.785640; 189.386218) |
| 5756942110218608640 | H/H | Fit point | 0.002493 | (47.916124; 227.191921) |
| 5756942110218608640 | H/H | Alternative | 0.007487 | (16.785640; 189.386218) |
| 5756958431094222592 | G/G | Fit point | 1.005548 | (131.762814; 139.481527) |
| 5756958431094222592 | G/G | Alternative | 1.809880 | (28.012712; 122.967736) |
| 5756958431094222592 | G/H | Fit point | 1.005466 | (131.761912; 139.481131) |
| 5756958431094222592 | G/H | Alternative | 1.809848 | (28.013368; 122.967760) |
| 5756958431094222592 | H/G | Fit point | 0.002499 | (118.272802; 139.885622) |
| 5756958431094222592 | H/G | Alternative | 0.006649 | (23.375360; 105.424538) |
| 5756958431094222592 | H/H | Fit point | 0.002395 | (118.271325; 139.885419) |
| 5756958431094222592 | H/H | Alternative | 0.006606 | (23.376405; 105.424600) |

Across all eight focus `_3` branches, the full 51×51 grid has one sampled connected component for both 4- and 8-neighbor connectivity at ΔF levels 0.1, 1, 2.3, and 5.991, measured from each branch's own grid minimum. These levels are not confidence regions. A finite grid can miss narrow structure or connecting paths; component counts do not prove the number of minima in continuous space.

## Audit and artifacts

The independent audit confirmed all 112 checkpoints: **96 verified, 16 verified-unavailable**, with no mismatch or unverified study failure. Comparisons included **2,760** prespecified nodes, **192** probes at saved fit positions × 3 steps, **480** same-family objective replays, **1,916** probes and position origins, and **40** local focus grids. Missing cells remain explicitly marked. Maximum absolute differences between independent WLS and saved results were **1.364×10⁻¹²** for grid cost, **2.274×10⁻⁷** for cost Hessian, **1.844×10⁻⁹** for Gauss–Newton, and **1.137×10⁻¹³** for same-family replay cost. This is a computational audit, not an accuracy test.

Main sources and traceability:

- [Locked protocol](PROFILE_LANDSCAPE_PROTOCOL.md), commit `704e3efc806dddef7906b032ba917745f80442a1`; design SHA-256 `6896060318db83a09d9b917f2ced0d4b5f930116d2cbdef2b046c22440b4ef56`.
- [Overview](../web/data/profile-landscape/overview.json) and [independent audit receipt](../web/data/profile-landscape/independent-audit.json); journal digest `fe1105b90c176412e22b837e13c6b7573ea1d9f3ace4e3dc7723648a4a2bb270`, receipt-content checksum `35156d08b0f8198e28eb6e01aff14e73a7749f7f9d07bf47eab3712818964ec3`.
- Audit code [audit_profile_landscape.py](../scripts/audit_profile_landscape.py), SHA-256 `90eaa6f825a91526bfe3ed049349e40d4d813f1b778d6b4e80b42f85d037e24e`; publisher [publish_profile_landscape.py](../scripts/publish_profile_landscape.py), SHA-256 `d3fb8ef80ed49ccb7af6d0dd68fd10f5e9c1d60571748f00b811f9265c4a77ac`.
- [112 profile records, 112 audit checkpoints, and two compressed headers](../web/data/profile-landscape/records.json.gz): **3,885,257 bytes** (about 3.885 MB decimal), SHA-256 `5e0c5798333a0533dd495d73131e2830ecf45b2a502b55c95ac87859877b91c4`.
- Four figures: source `5756942110218608640` at [exposure _2](../web/data/profile-landscape/profile-5756942110218608640-2025W46_2A_0214_2.png) and [exposure _3](../web/data/profile-landscape/profile-5756942110218608640-2025W46_2A_0214_3.png); source `5756958431094222592` at [exposure _2](../web/data/profile-landscape/profile-5756958431094222592-2025W46_2A_0214_2.png) and [exposure _3](../web/data/profile-landscape/profile-5756958431094222592-2025W46_2A_0214_3.png). Colors are clipped at ΔF=6 for display only; original costs are in the compressed file.
- [Figure environment](../web/data/profile-landscape/figure-environment.json) records package versions, DejaVu font hash, and hashes of four PNGs checked after rendering. [Figure dependencies](../requirements-figures.txt) are separate from Vercel runtime. This is not a byte-for-byte reproduction certificate on a different clean platform.

The figures are post hoc profile diagnostics on a cohort selected from the images. Weights, registration, and neighbor positions are held fixed conditionally; there is no independent physical PSF truth, calibrated total covariance, or source confirmation. The eight branches for each source with missing input do not become negative results. Focus samples were selected after viewing the gate, and both grids and finite differences are finite.

## Proposed next milestone

Before using deferred data, lock a protocol to **validate signal, blends, templates, and native pixel phase** using independent signal injections on prespecified native geometry. Every injection needs ground-truth position/flux, an identified PSF and neighbors, documented noise source and mask, and a complete record of attempts and failures. Prespecify cases for subpixel phase, brightness, blend separation, and template-family mismatch.

Completion criteria: reproduce injections from locked seeds and provenance; pass prespecified **signal-preservation** and **model/source-identity** gates across the full denominator; report position/flux error and failures by condition; and show that the pipeline refuses unsupported cases rather than dropping them. Set numeric thresholds in the protocol before running. A new protocol may compare two approaches: keep the existing ePSF with separately validated multimode screening, or use an independent alternative template and test signal preservation. Do not loosen the old gate, choose a model after viewing results, or promise lower error before measurement.

The telemetry branch adds classification logs only, with no retries. 41 offline tests were reported as passing; older evidence did not identify the root cause of two 502 errors. The full local test suite was reported as **564 cases: 558 passed, 6 skipped because MongoDB was unavailable**. Local browser checks confirmed star/image switching, opening the table with Enter, and horizontal scrolling at a 390 px viewport without page overflow. CI and production receipts are recorded separately in the release PR; test counts and cloud READY status do not replace science gates or recovery/SLO requirements.
