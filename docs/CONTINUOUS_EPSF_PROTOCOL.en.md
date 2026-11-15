# Continuous ePSF Development Protocol 0.10

*English translation of the hash-locked original, [CONTINUOUS_EPSF_PROTOCOL.md](CONTINUOUS_EPSF_PROTOCOL.md). The original remains the canonical source used by the scientific evidence manifests; this translation is provided for readability.*

This study tests how the target-source template boundary affects positional error and conditional coverage in previously opened trials. It is development research, not an independent validation set, an astronomical confirmation, or a change to WISE 0855.

## Candidate and limits

The candidate inherits `plane_fixed` 0.9: native pixels and mask, WCS and offsets, variance, a ±2.5 sky-pixel fit boundary, five initial positions, a flat background and free flux, two Huber IRLS iterations, and the original single-source-fit quality comparison. Only the target template changes: read the raw ePSF, cast to float, normalize as before using `raw * oversampling² / sum(raw)`, pad with 16 zero oversampled cells on each edge, then apply a cubic spline filter. Compute the center from the new array dimensions. Do not monkeypatch or modify the frozen pipeline. Neighbor PSFs in the nuisance projection remain the old PSF; they are not continuous at the boundary, intentionally isolating the target boundary. Refit IRLS and flux for the candidate. A 16-cell pad does not establish that the PSF is physically meaningful.

A fit is numerically valid when the solver succeeds, it is not near a boundary under the 0.9 rule, the total amplitude is positive, position/covariance are finite, information rank is 2, and covariance is positive definite. The 0.9 quality gates and single-source comparison still apply. No frozen parameters change. Gauss–Newton covariance and the observed profile Hessian are evaluated at the same candidate-fit position, using fixed final IRLS weights. The profile uses steps of 0.002 and 0.004 sky pixels and a 5% stability threshold for `profile_uncertainty`; it is omitted if either epoch is invalid or the Hessian is unstable/not positive definite. Add the existing registration covariance before transforming to east/north arcseconds. This is conditional, uncalibrated uncertainty and does not include all physical errors.

## Locked sample and comparison

Use only the three already opened fields `w350p35`, `w090p10`, and `w210m20`; patch 1 and the nearest ePSF remain frozen. Each field has two cases: stationary at SNR 2/frame and moving at `[0.6, 0.05]` sky pixels at SNR 4/frame. Each case is evaluated on the original-background image with an injected source and on 64 independent Gaussian pixel-noise draws with the same variance and seed `20261030` as the baseline cache `data/raw/benchmark/bias-gaussian64-development.json`. Reinitialize the RNG for each case and preserve the original frame/epoch order. A Gaussian image consists of the signal minus the original image plus new noise; it has no original background and no added source shot noise. Truth uses the frozen `source_image`, not the padded PSF; the paired comparison intentionally mismatches the old truth and the candidate. This protocol has no separate padded-truth control.

The completed baseline cache contains all 64 records for each case. At run time, refit baseline draw 0 and reject it if status or vector differs from the cache by more than 1e-5 arcsec. Pair each reported trial with the baseline record at the same draw index, including failures; candidate results do not replace baseline results. Record numeric and accepted counts separately for each branch and for the common-numeric/common-accepted subsets. For each subset, report vector-error RMS and P90, and the number of truth-containing 68% and 95% ellipses with the number of available covariances. Do not interpret coverage among trials with a profile as coverage for all trials when a profile is unavailable. Exposures are shared within each field, while Gaussian draws have independent noise; the six cases are not six new independent fields.

Do not select or open a new calibration/validation set. These results are insufficient for promotion. Further review requires a model and criteria locked in advance, bias and coverage measured on new independent fields, assessment of physical PSFs and systematic noise, and full reporting of denominators and out-of-support cases.

## Lock and run

```powershell
.venv/Scripts/python.exe -m unittest tests.test_continuous_epsf -v
.venv/Scripts/python.exe -m scripts.run_continuous_epsf_study --design
# After committing the design and all hashed source, documentation, and tests:
.venv/Scripts/python.exe -m scripts.run_continuous_epsf_study --run
# A single case can be run or resumed separately:
.venv/Scripts/python.exe -m scripts.run_continuous_epsf_study --run --fields w350p35 --snrs 2
```

`--design` refuses to overwrite and records SHA-256 hashes for code, tests, documentation, requirements, frozen sources, design, the opened 0.9 product, and baseline cache. `--run` refuses to proceed if the design, sources, or tracked product are not committed at HEAD, if on-disk hashes differ, or if the baseline cache changed. The original noise cache under ignored `data/raw/` is bound by hash rather than Git. Original data, calibration, and source URLs are verified against the manifest and frozen-design hashes when loading fields. Results are written only to `data/raw/benchmark/continuous-epsf-development.json`, with a file-replacement checkpoint after each draw. Resume recreates the same RNG sequence from the beginning and verifies draw continuity. Completed results cannot be overwritten.

On the current machine, one original-background `w350p35` SNR 2 trial took about 7 seconds to load and 0.66 seconds to fit two epochs after loading. This is a single performance trial, not a Monte Carlo result. A low estimate is about 5 minutes for 390 paired fits, plus field loading, checkpoint I/O, and convergence variability; allow 10–20 minutes or more. Monitor console progress and resume by case if interrupted.
