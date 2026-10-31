# Source-balanced ePSF calibration-only protocol

This protocol must be committed with its source/input inventory before any
shape score, coefficient or corrected shape under this design is evaluated.
It opens no prospective fields and fits no corrected source positions. It
cannot certify accuracy, covariance coverage or an astronomical detection.

## Design and prior information

The 21-reference, 20-exposure WISE cohort and all earlier fits have already
been opened. Only the old 14 training IDs and first six chronological IMAGE
MJD-AVG exposures per season enter this calibration: **168 planned cells**.
The seven old heldout IDs and last four exposures per season are reserved
for a future, separately frozen conditional assessment. Neither set is new
sky validation. Baseline nearest results, preparation failures and numerical
refusals are reused, not rerun or removed from the denominator.

The unweighted information-only preflight was viewed before this protocol.
It reported 145 usable information cells, 22 unavailable cells and one old
numerical refusal. One bright source contributed 50.7% of a shape direction.
Source balancing was chosen after that information-only look, before any
residual score or shape estimate was inspected. This adaptation is explicit;
the design is a development experiment, not an untouched preregistration.

## Single estimator

Use the nearest official ePSF and exactly three shared native shape directions:
one isotropic second finite difference and two odd third differences. Full
finite native-lattice flux and first moments are preserved before masking.
Parameters have units pixel², pixel³ and pixel³ and absolute bounds
**0.04 / 0.003 / 0.003**. The same family applies to target and all retained
catalogued neighbors. Pixel masks, signed per-exposure Jy amplitudes, planar
background, catalog IDs, original errors and final Huber weights are unchanged.

At the old fitted point, project all shape columns off the complete local
position/amplitude/background/neighbor tangent. For each source, divide its
summed scaled information trace by its number of available exposures. Its
weight is the median of these positive source means divided by its own mean.
The same weight multiplies information, residual score and pixel response.
No residual or validation value chooses a weight. Partial sources keep their
actual exposure count. Do not tune a weight, bound or dimension after results.

Solve one composite linear update. For covariance, identify every pixel by
exposure ID and integer native x/y; sum responses for repeated physical pixels
before propagating their original VARIANCE. This retains stamp overlap rather
than assigning duplicated pixels independent noise. It is conditional on the
fitted point, robust weights, balance, masks, catalog coordinates and calibration.
Because the balance uses noisy fitted amplitudes, its variability is omitted.
No full-estimator coverage or physical systematic floor is claimed.

## Guards and terminal outcomes

All three directions must have full rank, scaled information condition ≤100,
at least eight calibration sources and at least four distinct sources per
season. Maximum generalized source information fraction is **0.35**, unchanged
from the unweighted diagnostic. Conditional errors divided by parameter bounds
must be ≤0.5 in every direction. The unbounded diagnostic vector is retained;
any bound violation rejects the whole correction, without clipping or fallback.

Only if these guards pass, render the corrected target at its old anchor and
saved point plus every retained neighbor in all available calibration cells.
Every rendering must meet the frozen kernel's 5% peak-change, 1% additional
negative-wing and discrete-moment guards. No new optimum or residual-based
shape-family search occurs. Any rendering refusal rejects the candidate.

All 168 cell outcomes are written once in checksummed, resumable journal records.
Failures remain terminal. The final result identifies the protocol commit,
raw/source inventory and complete journal digest. A failed candidate is reported;
it does not allow automatic expansion of bounds, removal of hard stars, smaller
shape families or a correction silently set to zero. A passing candidate remains
conditional and cannot replace the measurement/detection pipeline without a
new frozen point-fit, signal-preservation and heldout evaluation protocol.

## Reproduction

```powershell
.venv/Scripts/python.exe -m scripts.run_shape_calibration --design
# Commit design, sources and tests before evaluating the following command.
.venv/Scripts/python.exe -m scripts.run_shape_calibration --run --protocol-commit <40-character-commit>
```

This bounded family is a project hypothesis. The numerical moment gauge does
not prove the true optical centroid or flux convention. Upstream WCS/ePSF
training membership is unknown. All 30 prospective fields remain unopened.

The [IRSA product guide](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/)
and [official ePSF tutorial](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/)
recommend the newer effective-PSF calibration for QR2 images as well as QR3.
Thus a residual or refused correction does not itself establish an invalid
QR2/QR3 pairing. Reprocessing, flag, background, source-identity and optical
model effects must be distinguished with their own controls. The
[Photutils guide](https://docs.astropy.org/projects/photutils/en/stable/user_guide/epsf_building.html)
also motivates explicit sampling/normalization/centering choices; it does not
validate this project's three-direction family or transfer its accuracy.
