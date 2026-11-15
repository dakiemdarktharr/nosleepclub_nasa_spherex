# Bias and Coverage Diagnostics on Opened Data — 0.10

This is development work following validation 0.9, not a new external test set. Sources and measurements from 0.3–0.9 remain unchanged. No new model or covariance has been applied to WISE 0855.

## Reproduction and interventions

The `diagnose_bias.py` code is locked at `a33dd64`. The three fields `w350p35`, `w090p10`, and `w210m20` were opened in 0.9. For each field, the study checks source region 1 at grid coordinate `[57.5, 5.5]` in two cases: S/N 2 per frame/stationary and S/N 4/moving by `[0.6, 0.05]` pixels. Both factors change together, so this is not an S/N-only ablation. Reproduced original vectors match within 1e-5 arcsec.

Compare four point models on the same previously injected source, search from nine starting points using final IRLS weights, omit each exposure in turn (20 times per case), and separate the injected signal from all original background/noise. The signal-only recovery control has error <0.00002 arcsec. This is an oracle intervention that knows the injected source; it cannot be used to remove background around an unknown astronomical source.

Then generate 64 independent Gaussian noise realizations per case from the original variance, using the ePSF matched to the fitter and retaining masks/layout and offsets. Cases use paired noise streams; do not treat the 384 cases as 384 independent sky regions. No source shot noise is added; this is an internal statistical check, not a physical detector simulation.

| Field | Case | Error on original background | Gaussian-noise RMS | Raw 68% ellipses containing truth on Gaussian noise | Largest vector change when omitting an exposure |
|---|---|---:|---:|---:|---:|
| w090p10 | S/N 2, stationary | 1.338″ | 1.943″ | 28/64 | 1.298″ |
| w090p10 | S/N 4, moving | 0.544″ | 0.782″ | 39/64 | 0.460″ |
| w210m20 | S/N 2, stationary | 1.732″ | 2.095″ | 22/64 | 2.981″ |
| w210m20 | S/N 4, moving | 0.444″ | 0.854″ | 36/64 | 0.531″ |
| w350p35 | S/N 2, stationary | 2.589″ | 2.291″ | 24/64 | 1.017″ |
| w350p35 | S/N 4, moving | 1.192″ | 0.803″ | 39/64 | 0.533″ |

The Gaussian-noise error exceeded the original-background result in 14/64 and 6/64 realizations for the two `w350p35` cases. This is a descriptive comparison, not a p-value for a background-caused effect. Reusing one fixed noise realization for multiple injected sources can produce vectors that are biased in the same direction. There is not enough evidence to attribute the `w350p35` errors specifically to blending or diffuse background.

No complex model consistently rescues both `w350p35` cases. For the fainter case, the flat-background/fixed-ePSF error is 2.589″; quadratic background is 2.640″; flexible ePSF is 2.836″; and both changes together give 2.829″. For the brighter case, the alternatives reduce the error modestly from 1.192″ to 1.134–1.165″. A field with greater exposure influence than `w350p35` can still recover better; a single jackknife threshold does not explain the undercoverage.

## Likelihood-curvature experiment

`profile_uncertainty.py`, `run_profile_diagnostics.py`, and numerical controls were locked at `ecd61de` before comparison on the same 64 realizations. Gauss–Newton uses JᵀJ; the full objective Hessian also includes the residual's second-derivative term. Linear and nonlinear numerical controls confirm that the two approaches can differ.

On the empirical images, the objective Hessian was often unstable at 0.002/0.004-pixel steps; only 20–28/64 cases per group passed step-sensitivity checks at both epochs. Do not apply a new ellipse by silently dropping the remaining cases.

Profile likelihood optimizes the initial position for a **motion vector**, while holding the vector fixed. This avoids incorrectly using a two-degree-of-freedom threshold for four fixed coordinates. Final robust weights are still held fixed; Wilks' theorem has not been established at low S/N.

| Field | S/N 2: GN → profile LR, contains truth | S/N 4: GN → profile LR, contains truth |
|---|---:|---:|
| w350p35 | 24/64 → 31/64 | 39/64 → 43/64 |
| w090p10 | 28/64 → 40/64 | 39/64 → 42/64 |
| w210m20 | 22/64 → 34/64 | 36/64 → 39/64 |

This changes how uncertainty is represented for the same centroids; it does not improve the positions. The faint cases remain undercovered. Next, check ePSF smoothness at the support boundary and likelihood identifiability, then calibrate/test on independent data. Do not select a new threshold against `w350p35` truth and claim generality.

## Provenance and reproduction

- `web/data/diagnostics/bias-overview.json` stores each vector, covariance, Gaussian cases, influence, profile modes, and the hash of the larger report.
- The larger report and raw FITS files are in `data/raw/benchmark/` and are not committed; they can be regenerated from the cache pinned in design 0.9.
- Run `python -m scripts.diagnose_bias --fields w350p35 --jackknife --noise-draws 16 --output data/raw/benchmark/bias-w350-development.json`; repeat for the two comparison fields into `bias-comparison-development.json`.
- Run `python -m scripts.diagnose_bias --fields w350p35 w090p10 w210m20 --noise-draws 64 --output data/raw/benchmark/bias-gaussian64-development.json`, then `python -m scripts.build_bias_overview`.
- `python -m scripts.run_profile_diagnostics` requires committed code and blocks overwriting a completed run. To reproduce in another environment, use a separate output/cache; do not modify a published checkpoint.

Limits: known-position fitting, matched ePSF, conditional Gaussian noise, fixed registration, shared exposures, and regions selected after seeing validation. This report contains no false-positive rate, blind-search completeness, or new astronomical detection.
