# ePSF Boundary Diagnostic: Development Data 0.10

This diagnostic asks whether ePSF interpolation makes the objective discontinuous at the kernel edge. It is an exploratory analysis on an opened field, not an astronomical confirmation, independent coverage assessment, or proposal to replace scientific calibration.

## Design and reproduction

```powershell
.venv/Scripts/python.exe -m unittest tests.test_epsf_boundary -v
.venv/Scripts/python.exe -m scripts.diagnose_epsf_boundary
```

The report is written to `data/raw/benchmark/epsf-boundary-development.json`, a Git-ignored path. To run a subset, use, for example, `--fields w350p35 --snrs 2`. The program records SHA-256 hashes of diagnostic code, frozen sources, design, and the original Gaussian report; each field has the path and hash of its source result. Scientific source URLs, hashes, and versions remain in the design and referenced source manifests; no scientific product is created or replaced.

The three fields `w350p35`, `w090p10`, and `w210m20`, patch 1, use two frozen cases: stationary at SNR 2/frame and moving by `[0.6, 0.05]` sky pixels at SNR 4/frame. For each case, reproduce **draw 0** from the seed-`20261030` 64-draw Gaussian experiment: the matched signal uses the nearest ePSF, with independent Gaussian noise using the original native-pixel variance, no original sky, and no source shot noise. Refit each epoch as before; compare vector errors with the prior record, with a maximum allowed difference of 1e-5 arcsec. All six cases in this run match at the recorded numerical precision.

At the original fitted position, hold valid pixels, WCS and Jacobian, final IRLS weights, data, variance, and nuisance projection (background and neighbors) fixed. The objective is half the weighted squared residual after profiling source amplitude; the residual is compared with the frozen function. The control changes only the target-source template: pad the normalized oversampled ePSF array with eight zero pixels on every edge, then apply the spline filter again. The fitted position and nuisance projection are not recomputed. Padding changes both interpolation within the existing region and support outside it; this is not a refit or a new validated physical model.

The Hessian uses sky-pixel steps `0.00025, 0.0005, 0.001, 0.002, 0.004, 0.008, 0.016`, using an independent scalar central-difference formula and comparing it with `profile_uncertainty.hessian`. A known second-order control checks diagonal and mixed terms. A synthetic kernel with a nonzero edge directly checks the discontinuity and continuity after padding. The program searches for boundary crossings in four directions `[1,0]`, `[0,1]`, `[1,1]`, and `[1,-1]` within ±0.016 sky pixels, and stores up to the three nearest distinct crossings per direction. The report records native-pixel coordinates, observation ID, edge, zone, template, and objective values on both sides at ±1e-8 sky pixels. Multiple pixels may cross at once, so the objective jump is for the whole epoch and cannot be attributed to one pixel. Crossing counts across directions are not independent events.

## Observations from this run

- Residual-reconstruction error and differences between Hessian formulas were both zero in the stored comparisons. The second-order and synthetic-boundary controls passed.
- Every sample inspected has a nonzero ePSF edge value. The largest absolute edge values after frozen-model normalization range from 0.00135 to 0.00599; these are template values, not measured source fluxes.
- 11/12 epochs had at least one boundary crossing within the search range in one of the four directions; the remaining epoch had none in that range. For each epoch with a crossing, the largest recorded objective jump among examples ranges from 0.00364 to 0.0424 half-chi-square units. The padded control changes by at most 1.89e-7 between the same two positions; this includes smooth variation and numerical error and is not a precise estimate of the jump limit.
- By the existing profile relative-Frobenius criterion, 5/12 epochs had an original Hessian changing by more than 5% between 0.002 and 0.004 sky-pixel steps. At the same positions and weights, the padded-control change was at most 0.023% across 12 epochs. A nearby boundary crossing need not fall on every point used by every stencil, so an epoch may have a crossing while its Hessian remains stable at these two step sizes.
- Example: `w350p35`, SNR 2, earlier epoch: original Hxy is -13.549 and +7.251 at the two steps; padded-control Hxy is -10.837 and -10.842. Along `[1,-1]`, a boundary crossing at +0.002899 sky pixels gives an objective jump of +0.004524, while the padded control changes by about 9.1e-9 at the same two positions. In the later epoch, original Hxy is -532.461 at step 0.002 and -7.227 at 0.00025; nearby crossings to the fitted position are recorded in the report.

## Interpretation and limitations

Direct measurements and controls strongly support the conclusion that the frozen interpolation boundary produces finite jumps in the objective for the samples inspected and can make finite-difference Hessians step-dependent. They do not establish how much of the 64-draw undercoverage this mechanism causes; the estimator, nonlinearity, mode selection, variance, and other assumptions may also contribute. Zero padding is a numerical intervention, not validation of a physical PSF; it provides no new coverage result, does not generalize to unopened fields, and does not establish an astronomical source or motion.

Next, design and lock the code and criteria before testing a candidate with a smooth boundary and a clear physical basis. Then run paired comparisons with controls for positional error, optimizer stability, and coverage, followed by validation on independent unopened fields. Consider promotion only if pre-published thresholds are met, source provenance and masks are retained, and error limits are stated.
