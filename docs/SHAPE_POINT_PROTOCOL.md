# Sealed ePSF point-fit assessment

Freeze the point-fitting code, rules, tests, input inventory and already sealed
shape vector before any corrected position is fitted. All outcomes are from
the opened WISE reference cohort; none is independent new-sky validation.

## Separation and order

The coefficient vector comes only from the 14 old training IDs and first six
chronological exposures in each season, under calibration protocol `972c8b8`.
Its full three-vector, units, covariance qualification, record digest and
shape checks are sealed in `shape-correction/coefficient-seal.json` before this
protocol. No refitting, dimension selection or coefficient adjustment occurs.

1. Fit only the **168** calibration cells first. Reuse baseline preparation
   failures. Refit every old completed point, including old numerical refusals,
   with the same signed Jy amplitudes, planar background, masks, observed errors,
   nine starts, Huber iteration limit and final mode audit. Correct target and
   all retained neighbors with the single sealed vector.
2. Compare actual changes against the old fixed-tangent shape response for every
   one of the 145 information cells. All must remain numerically supported.
   The 90th percentile of the vector linearization error must be ≤**0.02 common
   pixels**, and the maximum ≤**0.05 common pixels**. A failure defers all
   reserved outcomes. These are numerical adequacy budgets, not precision claims.
3. Write the full calibration gate, including failures and journal digest, and
   commit it. Only a passing gate with exact Git bytes permits the assessment.
4. Fit the **252** remaining cells once. The primary assessment is exactly the
   **7 old heldout IDs × 8 reserved exposures = 56 cells**. Remaining cells are
   secondary descriptive diagnostics. All missing, failed and numerically refused
   cells remain in their planned source/exposure denominator.

The source and exposure holdouts were chosen earlier for the shape development,
but their old outcomes were already viewed and the original cohort was selected
from images. This staged assessment cannot establish independent generalization.

## Fixed primary summary and necessary budgets

For each primary source, compute its mean radial Gaia residual in common-completed
baseline/corrected pairs; average those source means equally. Require at least
five sources with at least two common completed frames in each season. Retain
every source in the source table, including sources with no pair. The corrected
model must not add a numerical refusal where the old point had numerical support.

Necessary developmental acceptance requires all of:

- Equal-source mean radial improvement ≥**0.05 arcsec**.
- Pooled primary P90 radial residual increase ≤**0.05 arcsec**.
- Corrected paired primary RMS ≤**0.5 arcsec** and P90 ≤**1 arcsec**.
- The source/season support and no-new-refusal requirements above.

These declared effect/absolute budgets are project choices to avoid promoting
tiny self-comparison changes, not SPHEREx specifications. All paired rows,
baseline/corrected distributions, subset counts and per-source outcomes are
reported even if a gate fails. No source is removed as an outlier, no alternate
shape family is selected, and no gate is relaxed after results. No uncertainty
interval assumes the 56 source/exposure cells are independent. A passing set is
necessary, never sufficient, for scientific promotion: real-source identity,
signal preservation, independent PSF/SED/noise controls, calibrated total
covariance and prospective field tests remain separate requirements.

The existing source-presence threshold was calibrated with different templates;
it is not reused or promoted for a corrected PSF. This protocol generates no
noise realization, WISE target trajectory or prospective field outcome.

```powershell
.venv/Scripts/python.exe -m scripts.run_shape_point_study --design
# Commit this design and all bound source/test/product bytes first.
.venv/Scripts/python.exe -m scripts.run_shape_point_study --run --stage calibration --protocol-commit <point-protocol-commit>
.venv/Scripts/python.exe -m scripts.run_shape_point_study --calibration-gate --protocol-commit <point-protocol-commit>
# Commit the passing calibration-gate.json before the following command.
.venv/Scripts/python.exe -m scripts.run_shape_point_study --run --stage assessment --protocol-commit <point-protocol-commit> --gate-commit <gate-commit>
.venv/Scripts/python.exe -m scripts.run_shape_point_study --summary --protocol-commit <point-protocol-commit> --gate-commit <gate-commit>
```

If the calibration gate fails, `--summary` reports all 252 assessment cells as
deferred and never opens their point journal; `--gate-commit` is unnecessary.
The primary metric implementation and its tests are included in this protocol's
source inventory before any corrected point is fitted.
