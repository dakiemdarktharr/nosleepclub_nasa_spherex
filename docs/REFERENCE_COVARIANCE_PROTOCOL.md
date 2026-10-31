# Conditional reference-frame covariance protocol

Commit this protocol, its design and all source/input inventory before assembling
the full covariance or evaluating these diagnostics. This is a descriptive
development analysis of the already opened, image-selected WISE reference cohort;
it cannot establish coverage, a scientific improvement or an astronomical detection.
No prospective field, new point fit, random realization or learned shape is used.

## Cohort and fixed inputs

Retain all 21 old source IDs and 20 old exposures: **420 planned nearest-ePSF
source/exposure cells**, including every baseline preparation or fitting failure,
old numerical refusal and any new linearization failure. Reuse the complete
checksummed old journal and freeze its digest, identities, source split, exposure
list, raw/source hashes and runtime identity. Failed cells remain terminal and
visible by status and source. Four distinct old training references are required
in each planned exposure; failure refuses the full joint diagnostic, without
removing frames or changing the threshold.

For each numerically supported saved baseline fit, reproduce its original mask,
metadata, fixed nearest ePSF, signed target/neighbor amplitudes, plane background,
and final Huber weights. At the saved point calculate the full local
position/nuisance tangent influence on original native pixels. The helper receives
zero shape directions and no learned shape is estimated or propagated. The raw
common-grid offset is saved fitted registered point **plus** its legacy
registration offset **minus** its Gaia anchor. No position is reoptimized.

## Covariance and frame solve

Identify each original pixel by exposure ID and native integer x/y. Use its
original VARIANCE once, so overlapping stamps share image noise. Add the Gaia
component from each source's fixed five-parameter covariance and exposure-specific
propagation Jacobians. Gaia errors for different sources are assumed independent;
pixel and catalogue errors are assumed independent conditional on the fixed
legacy geometry. The matrix order is explicitly saved as source/exposure pairs,
with x then y for each row, in common-grid pixel².

Fit all exposure translations jointly using only the 14 old training IDs and
their complete covariance submatrix. Other sources are held out of the fit.
Use the full covariance for corrected heldout residuals, including calibration
and heldout cross-covariance, not an independence shortcut. Report the nominal
joint chi-square with 2 degrees of freedom per usable heldout observation,
two-dimensional marginal Mahalanobis squared per heldout row, and seven
source-level chi-squares using each source's complete residual submatrix. Missing
heldout sources remain listed with zero observations and zero degrees of freedom.
All summaries are descriptive; the cohort and earlier fits were already opened.

Require full-covariance PSD and calibration and heldout residual covariance SPD.
Do not add floors, remove outliers, use a pseudoinverse, rescale by chi-square,
or claim precision/coverage validation. A refusal is a terminal result, not a
fallback to independent observations or fewer planned cells.

## Uncertainty limits and provenance

The input pixel variance and fixed local tangent describe only part of the
estimator uncertainty. Baseline masks, final robust weights, PSF, legacy
registration offsets and neighbor coordinates are **conditioned on**, including
the omitted noise dependence of registration and neighbors. Detector/model
systematics, selection and unknown upstream WCS/ePSF training membership remain
unmodeled. This is not the full joint image-estimator covariance. Catalogue
cross-source dependence and pixel/catalogue dependence are not included. There is
no estimated-shape term or evidence of shape improvement.

Preserve original cutout URLs, raw hashes, units, masks and processing metadata in
the immutable per-cell journal. The result stores full pixel, Gaia, total and
heldout residual covariance matrices, row identities, raw/corrected offsets,
frame translations and descriptive statistics. It is stored under ignored
`data/raw/`; a checksum ties it to the immutable complete journal and design.

## Reproduction after review

```powershell
.venv/Scripts/python.exe -m scripts.run_reference_covariance_study --design
# Commit the design, protocol, sources and tests before the next command.
.venv/Scripts/python.exe -m scripts.run_reference_covariance_study --run --protocol-commit <40-character-commit>
```

No operation in this protocol promotes a model or authorizes work on new fields.
