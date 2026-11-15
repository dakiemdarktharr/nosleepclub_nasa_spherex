# WISE 0855: Spectral Constraints Do Not Resolve Position

All **28/28** fits completed under the protocol locked at `cfb9d6a17ee37ca2c5c061a2cd44209d1093f4b7`. This is development on **20 already opened QR2 exposures**: broad uses 10 images per epoch; strict uses two per epoch and is a subset of broad. No new validation field was opened. The results do not establish reduced bias, accuracy, coverage, or an astronomical detection.

[Interactive demo](https://nosleepclub-nasa-spherex.vercel.app/#linked-flux) lets users switch image sets, inspect plots, all seven vectors, and reasons each epoch was blocked. The [protocol](WISE_LINKED_PROTOCOL.md), [overview](../web/data/linked-flux/overview.json), and [all 28 attempts](../web/data/linked-flux/development.json) retain sources, units, runtime, mask/pixels, ePSF zone, spectral coefficient, every start/mode, weights, and conditional covariance. The WISE estimator and manifest currently shown in the workspace were not replaced.

## Results for all branches

Units are arcseconds. Δ is Euclidean distance between a branch's vector and its control vector **within the same image set**; it is not error against truth. “Screen” is an arithmetic check of both epochs, not science acceptance.

| Branch | Broad East / North | Broad Δ | Broad screen | Strict East / North | Strict Δ | Strict screen |
|---|---:|---:|---|---:|---:|---|
| 1 · Independent brightness per frame | −3.067 / +0.087 | 0 | 2/2 | −2.535 / +0.501 | 0 | 1/2 |
| 2 · R7 spectrum 68, α=0 · prespecified candidate | −3.029 / −0.023 | 0.116 | 2/2 | −3.122 / +2.704 | 2.280 | 1/2 |
| 3 · Spectrum + free tilt | −3.322 / +0.226 | 0.290 | 2/2 | −2.535 / +0.501 | ≈0 | 1/2 |
| 4 · Reference α=−4 | −3.029 / −0.023 | 0.116 | 2/2 | −3.122 / +2.705 | 2.281 | 1/2 |
| 5 · Reference α=+4 | −3.030 / −0.023 | 0.116 | 2/2 | −3.121 / +2.703 | 2.279 | 1/2 |
| 6 · QR2 center, R7 68 shape | −2.859 / −0.082 | 0.268 | 2/2 | −3.133 / +2.692 | 2.272 | 1/2 |
| 7 · R7 17-channel response | −3.028 / −0.026 | 0.120 | 2/2 | −3.122 / +2.703 | 2.279 | 1/2 |

Maximum separation between **any pair** of vectors is **0.555861″ broad** (branches 3 and 6) and **2.280631″ strict** (branches 3 and 4). Maximum broad change relative to control alone is 0.290400″; do not substitute it for total spread. Include branches that fail screening in spread calculations. The two image sets share data and are not independent validations.

Branch 3 has two flux parameters and two different wavelengths in strict, so its linear span is equivalent to two independent fluxes. The vector matching control is an algebraic check, not another astronomical evidence source.

## Two solutions in strict's later epoch

All seven strict branches converge under IRLS but are blocked by `multiple_near_best_modes` in the `after` epoch. This is not a timeout or preparation failure. In the control, the two best solutions have weighted χ² 272.823844 and 272.861320, a difference of **0.037476**. For the primary candidate, the difference is **0.568008**. The mode-audit Δχ² threshold is heuristic; no probability distribution or coverage has been demonstrated for this robust fit.

The [post hoc replay](WISE_LINKED_MODE_DIAGNOSTICS.md) recalculates the linear profile at saved positions and weights; it does not refit, reselect a model, or open data. On the current runtime, saved-point cost, flux/error, and residual match exactly. In the control, the two exposures contribute Δχ² **+0.554247** and **−0.516770**, nearly canceling. In the shared branch, both images determine the common amplitude; do not interpret per-exposure χ² parts as independent measurements.

The core mask is fully selected at inspected modes. Each image has three catalog templates in the nuisance model. One template is near the modes; projected source information falls more at the mode near the template. This is a geometric model diagnostic. It does not prove that the template causes multimodality, identify a separate astronomical source, or determine which solution is more correct.

## Checks and gaps

- R7 channel maps have `DETCOORD=sky`, while center/bandwidth maps have `DETCOORD=DEVICE`: the binder applies orientation per HDU and avoids a double flip. The [photometric-convention audit](PHOTOMETRIC_CONVENTION_AUDIT.md) records verified and unverified details.
- The renderer normalizes across the full finite native lattice before masking, retains signed negative ePSF wings, uses exact source WCS, and uses Ω with units. Ω convergence is not a physical error bound; the correct SAPM UUID has not been matched from processing history. Normalization does not make the ePSF independent truth.
- The 2023 MAST PRISM pipeline is used separately; it is not merged with G395M, scaled by Spitzer, or LSF-deconvolved. Reference α=0, ±4 are explicit assumptions, not verified SPHEREx calibration. The QR2 row center still uses R7 68 response shape; this is not a full comparison of QR2 and QR3 pipelines.
- Spectral ratio is fixed at the pixel nearest the anchor; response is not integrated over the ePSF footprint or differentiated by fitted source position. Spectral uncertainty, variability, LSF, response-shape, PSF tails, and QR3 ePSF applied to QR2 images are not propagated.
- One position per epoch does not model within-season motion/parallax. Gaia offsets and background-source positions/shapes are fixed; covariance omits these shared effects and cross-frame/cross-epoch terms. Do not add shared-frame S/N in quadrature because frames share one amplitude parameter.
- GN/profile-H describe curvature around one solution at final weights. Do not arbitrarily enlarge covariance to cover another mode or use it as a calibrated ellipse. Position Jacobians were not saved, so the publication auditor cannot independently recompute GN from the report; PD checks and covariance transformations are available.
- The publisher recomputes per-pixel χ², flux basis/covariance, IRLS/mode flags, vectors, spread, and profile-H inverse. This is arithmetic auditing, not validation of PSF/noise/astrometric truth or estimator accuracy.

## Reproduction and provenance

Closed raw checkpoint: 4,788,083 bytes, SHA-256 `a5bffe162ae8ccd88a6fc5311d1e8ddc279c56092b072a782652da5a7f1cfd0a`. Design SHA-256 `c5914ab5b3ef1e8fb0b0a41c0d35d0bab741cc562ea820b632ca902e4944b072`. The public report has original records/checksums plus additional audit data; overview records its hash/byte size. Raw FITS and large checkpoints are Git-ignored under `data/raw/`. [Figure manifest](../web/data/linked-flux/figures.json) records sources and package/font hashes and plotted coordinates.

```powershell
.venv/Scripts/python.exe -B -m unittest tests.test_linked_publication -v
.venv/Scripts/python.exe -B -m scripts.publish_linked_study
# Optional; offline science figures only, without changing pinned science requirements:
.venv/Scripts/python.exe -B -m pip install -r requirements-figures.txt
.venv/Scripts/python.exe -B -m scripts.plot_linked_study
node tests/linked-evidence.test.cjs
.venv/Scripts/python.exe -B -m scripts.serve_app --port 8767
# Open http://127.0.0.1:8767/#linked-flux
```

The original runner refuses to overwrite a completed study. A new intervention requires a different module/design/output; do not change protocol after viewing these modes.

## Next milestone and acceptance conditions

Lock a blend/ePSF experiment on **already opened development data**. Compare on the same pixels/alignment and retain every mode: current nuisance model; neighbors with physical constraints and position/shape uncertainty; and ePSF evaluated on reference stars held out from PSF construction. Add independent phase, SED, PSF/noise controls; do not choose a model because it is closer to the published vector. Evaluate RMS/bias, failures/abstentions, and uncertainty budget; smaller covariance or lower χ² alone does not pass.

Then add an exposure-level time model and shared alignment uncertainty. Open **12 calibration / 12 validation / 6 final holdout fields** only after locking evaluator, exposure/pixel overlap, power, absolute gates, and out-of-domain policy. This experiment does not meet those conditions; production work remains in progress.
