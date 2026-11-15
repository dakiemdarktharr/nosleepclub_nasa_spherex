# Blend, Background, and ePSF Results: No Model Can Yet Be Selected

**All 288/288 epoch fits completed; controls do not show consistent improvement.** Nonnegative neighbor-flux constraints lowered RMS in three of four synthetic cases but worsened the faint-source case on curved background. One draw passing all numerical screens still had **16.8″** truth error. The WISE measurement is unchanged; no calibrated covariance or production model was accepted; the 30 reserved fields were not opened.

[Open table and plots](https://nosleepclub-nasa-spherex.vercel.app/#neighbor-intervention) · [English protocol](NEIGHBOR_INTERVENTION_PROTOCOL.en.md) · [Original hash-locked protocol](NEIGHBOR_INTERVENTION_PROTOCOL.md) · [Design](../web/data/neighbor-intervention/design.json) · [53 KB summary](../web/data/neighbor-intervention/overview.json).

## Locked configuration and scope

Study locked at `32573ad53d6cafa47ef2cc79b0971b22bd3203bd`, before any fit or new draw. Design SHA-256: `119f7d628c716f7e372778bf9983ecbfc5c256c02b9b32aebc7972de819f57d6`. All images, Gaia offsets, and catalogs are WISE development data already opened.

- **32 real-data fits:** broad/strict image sets × eight combinations of plane/quadratic background, nearest/bilinear ePSF, and signed/nonnegative neighbor flux × two epochs. Broad has 10 images per epoch; strict has two and is a subset.
- Target flux/background are always signed; only physical neighbor columns keyed by ID receive NNLS constraints. Neighbor positions/alignment remain fixed. ePSF interpolation is spatial interpolation, not PSF learning from real stars.
- **256 control fits:** four plane/quadratic-background × target-flux 300/600 µJy cases, 16 draws each, with two plane/nearest branches and two epochs. Gaussian truth is pixel-integrated and from a different family than the fitter; branches share each realization. All controls use one previously opened strict geometry, not 64 independent fields.

The neighbor renderer was rebuilt with units and native WCS; the new free branch is a bridge control, not a byte-identical replay of the old model. Comparing NNLS/free with the same new background/ePSF isolates the constraint. This experiment does not use a spectrum to constrain target flux; its spread cannot be used to claim superiority over the linked-flux study with seven different spectral assumptions.

## Real images: changing assumptions changes the vector

Values are the two-epoch vector components in arcseconds. This is model sensitivity on opened data, not error relative to a known true position.

| Background / ePSF / neighbors | Broad East / North (″) | Strict East / North (″) | Strict, both epochs numerically supported |
|---|---:|---:|---|
| Plane / nearest / signed | −3.066 / +0.088 | −2.534 / +0.500 | No: multiple modes in after |
| Plane / nearest / nonnegative | −3.028 / +0.017 | −2.207 / +0.176 | Yes |
| Plane / bilinear / signed | −3.218 / +0.220 | −2.545 / +0.491 | No: multiple modes in after |
| Plane / bilinear / nonnegative | −3.134 / +0.087 | −2.276 / +0.174 | Yes |
| Quadratic / nearest / signed | −3.197 / +0.174 | −3.051 / +0.936 | No: multiple modes in after |
| Quadratic / nearest / nonnegative | −3.150 / +0.076 | −2.667 / +0.587 | Yes |
| Quadratic / bilinear / signed | −3.350 / +0.310 | −3.083 / +0.933 | No: multiple modes in after |
| Quadratic / bilinear / nonnegative | −3.261 / +0.155 | −2.746 / +0.598 | Yes |

Broad had **8/8** pairs passing numerical checks; strict had **4/8**. All four strict free branches have multiple near-best modes in the later epoch. The constraint changes position and mode structure; it does not establish which remaining mode is the true source. The primary plane/nearest NNLS−free vector contrast is **0.080076″** broad and **0.460337″** strict. Maximum separation across all completed vectors is **0.434865″** broad and **1.158115″** strict. Retain rejected vectors when calculating spread.

## Independent controls: inconsistent improvement and large errors

Every case has 16/16 pairs fit in both branches. No outliers or numerically rejected fits are removed from this table. RMS/P90 are vector errors against Gaussian displacement truth; each pair is ordered **free → NNLS**.

| Synthetic truth | Pairs fit per branch | RMS (″) | P90 (″) | Pairs passing numerical screen in both /16 |
|---|---:|---:|---:|---:|
| Plane · 300 µJy | 16/16 | 14.535 → 14.263 | 21.357 → 20.766 | 1/16 |
| Plane · 600 µJy | 16/16 | 3.661 → 3.358 | 5.082 → 4.641 | 7/16 |
| Quadratic · 300 µJy | 16/16 | 12.742 → 13.741 | 19.927 → 19.932 | 0/16 |
| Quadratic · 600 µJy | 16/16 | 2.511 → 2.189 | 3.712 → 3.098 | 8/16 |

For quadratic/300 µJy, NNLS RMS rises by **0.999050″**. Restricting to draws numerically supported by both branches still does not provide consistent evidence:

| Synthetic truth | Common sample /16 | RMS free → NNLS (″) | P90 free → NNLS (″) |
|---|---:|---:|---:|
| Plane · 300 µJy | 1/16 | 16.780 → 16.769 | 16.780 → 16.769 |
| Plane · 600 µJy | 7/16 | 2.406 → 2.196 | 3.796 → 3.254 |
| Quadratic · 300 µJy | 0/16 | Undefined | Undefined |
| Quadratic · 600 µJy | 8/16 | 2.081 → 2.124 | 2.775 → 2.830 |

P90 uses linear-interpolated percentiles; with n=1 it is one observation, not a reliable tail estimate. Do not pool the four cases or choose a model from the best-looking subset. Negative target fluxes are retained: negative-frame counts for free/NNLS are **9/11, 2/4, 13/15, 0/0**, across 64 frames per branch per case. The counts of neighbor coefficients bound to zero under NNLS are **43, 48, 27, 22**; a frame can have several coefficients, so these are not draw counts or confirmed-source counts.

### Post hoc example: numerical support can still be badly wrong

Draw ID **8** (zero-based) in plane/300 µJy is the only draw passing the numerical screen in both branches. Free vector error is **16.780201″** and NNLS is **16.768697″**. Both epochs converge under IRLS, do not hit a boundary, have one near-best mode, and have no better point under the audit. The second frame in the after epoch has target flux around −203.3 µJy in both branches.

This is a post hoc diagnostic, not a known cause. Do not change the gate, drop the draw, force positive target flux, or change truth to rescue the result. Rank/convergence/single-mode checks do not confirm source presence or correct identification. Null controls, real sources, and absolute-error criteria are needed before evaluating a new gate.

## Audit and reproduction

The closed raw file has **87,581,267 bytes**, SHA-256 `428e070cd75b078875420653745e4be2dacce7da95342033ae8f6ab923ce520a`, and is Git-ignored at `data/raw/benchmark/neighbor-intervention.json`. Do not rerun a completed study to replace results. Publisher/tests were locked at `055053f` before reading completed raw data; the scientific source at `32573ad` is unchanged.

The publisher checks all 288 keys/checksums, source/design/input/runtime/Git commits, shared pixels/errors/design across branches, realization hashes and seeds, units, masks/order, native renderer, and KKT at saved points. It includes **704** linear-frame audits; maximum scaled KKT violation is **1.288×10⁻¹³**. Independent BVLS replayed costs at **2,583** successful final starts; maximum χ² difference is **1.592×10⁻¹²**. Nine failed final starts remain failures. This validates computations, not scientific acceptance.

| Public artifact | Bytes | SHA-256 |
|---|---:|---|
| [32 real fits and audit](../web/data/neighbor-intervention/development.json) | 19,232,175 | `0d1c2781f30572165261309bfbb0447da1876bc3f77a13533c4b71e5e1f02a85` |
| [64 draws, two branches, and audit](../web/data/neighbor-intervention/controls.json) | 5,179,378 | `59e6ddc47196d328723c112252a725f8d2397f8637546dc321def4a47e1317bf` |
| [Web overview](../web/data/neighbor-intervention/overview.json) | 53,184 | `558f03c0da2b9c108a2cb2f97e85c7c901ba01157a4bf662a7f41daedfdd41d6` |

The web app loads the overview only when opening the deep-dive section; large files require a user-initiated download. [Figure manifest](../web/data/neighbor-intervention/figures.json) records source, every plotted coordinate, units, font, package, and SVG hash. Plots retain unsupported pairs and do not draw ellipses or clip tails from axes.

```powershell
.venv/Scripts/python.exe -B -m scripts.publish_neighbor_intervention --raw-sha256 428e070cd75b078875420653745e4be2dacce7da95342033ae8f6ab923ce520a
.venv/Scripts/python.exe -B -m scripts.plot_neighbor_intervention
.venv/Scripts/python.exe -B -m unittest tests.test_neighbor_publication tests.test_neighbor_figures -v
```

Plotting uses optional `requirements-figures.txt`; Matplotlib is not included in web runtime. Product/figure tests do not need Matplotlib. Position/renderer replay requires the correctly hashed raw cache, original Windows runtime, and locked thread request.

Software was released through PRs #8 and #9 at `f2e2aa4`: [387 CI tests](evidence/0.10/ci-pr9-f88b340.json), 13 optional raw-cache/photutils skips, six real Mongo fixture tests, and four passing Node suites. [54 public responses](evidence/0.10/production-f2e2aa4.json) verify 40 artifacts, API commits, and QA cleanup; [browser evidence](evidence/0.10/neighbor-production-browser.json) shows sample switching and retaining case 0/16. The runbook retains two earlier failed builds; a minimal API contract separates the static report from the function. This evidence does not change the scientific conclusion above.

## Remaining limitations

Controls use original empirical VARIANCE as a Gaussian scale; it may already include shot noise from original sources. Source Poisson noise is an ideal ramp conditioned on gain/nominal timing and does not prove the detector noise budget avoids double-counting. The fitter receives an oracle source variance from truth. The Gaussian shape differs from the fitter's ePSF but is not an independently measured SPHEREx PSF; stress cases do not directly measure WISE error or blind-search ability. Background/noise correlations, ePSF uncertainty, missing catalog sources, neighbor positions, within-season motion, spectra/chromaticity, parallax, and shared registration covariance are not modeled.

There is no covariance/coverage or detection probability. Position Jacobian/rank has not been independently replayed; the Poisson/Gaussian realizations were not regenerated in the audit, which checks source mean/variance/provenance and recorded hashes only. [IRSA permits the newer ePSF on older QR2 images](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/); that does not validate bias from the current interpolation/renderer on WISE.

Next, on development data, keep reference stars out of PSF/alignment construction to measure residuals by position/color/brightness; add null/no-source controls and audit the neighbor catalog before proposing a new gate. Acceptance must use absolute error, failures/refusals, and false accepts with full denominators; a converged solution is not proof of a correctly measured source. Then add per-exposure time modeling and shared alignment covariance. Lock evaluator, power, support domain, gate, and overlap before the 12 calibration / 12 validation / 6 final holdout fields.
