# ePSF shape and shared-reference development

This is development on the already opened WISE field, not a preregistration,
new validation, accuracy result or scientific promotion. The prior 840-reference
and 7,992-presence products remain immutable.

The next numerical candidate has three globally shared directions: an isotropic
second finite difference and two odd third differences. They are scaled by
native pixel²/pixel³, not a common dimensionless coefficient. A phase-specific
three-moment projection preserves the baseline's full finite native-lattice
flux and first moments before applying any image mask. Target and every retained
neighbor get the same correction family. Peak/negative-wing guards reject
unsupported shapes without clipping or stamp renormalization.

This fixes a numerical gauge; it does not establish the physical source center
or instrument flux convention. The [Photutils ePSF guide](https://docs.astropy.org/projects/photutils/en/stable/user_guide/epsf_building.html)
discusses phase sampling, centering and normalization conventions; [Anderson &
King](https://arxiv.org/abs/astro-ph/0006325) motivate empirical ePSF inference
from stars and dithered exposures. Their HST precision is not transferred to
SPHEREx. The proposed global width/skew family is our developmental model,
not a method validated by those references for this dataset.

The covariance implementation keeps one noise variable for each physical
exposure/native pixel, including overlapping reference stamps. If a shared
shape estimate has pixel influence G and measured positions have influence A
and shape response R, the nominal position covariance is formed from
`(A + R G) V (A + R G)^T`, with both cross terms. Shared five-parameter Gaia
errors are retained across exposure times. A strict joint-GLS translation
primitive accepts the resulting full covariance, calibration-source IDs only,
and every planned exposure. These are conditional fixed-weight/tangent
matrices; nonlinear curvature, changing robust weights/masks and unknown
calibration systematics are not magically included or coverage-calibrated.

## Information-only preflight

Before fitting any shape coefficients, the old 14 training references and the
first six chronological exposures in each of the two seasons were used to
inspect numerical information. Both the stars and their old fits had already
been viewed. The remaining seven old heldout labels and last four exposures
per season are reserved for the next conditional assessment, not called new
sky validation.

[The unweighted receipt](../web/data/shape-correction/feasibility-unweighted.json)
retains all **168** planned source/exposure cells: **145** supply information,
**22** have old preparation failures and **one** has an old numerical refusal.
Thirteen sources supply information. The three-column information condition
is **1.169**, but the largest generalized source contribution is **0.50696**,
above the proposed **0.35** dominance guard. Nominal errors relative to the
declared coefficient scales are **0.0662 / 0.1269 / 0.1176**, under the stated
known-noise linearization. These are feasibility descriptors, not measured
accuracy or empirically calibrated uncertainty.

No shape estimate, new position optimization, random draw, corrected heldout
result or prospective field was evaluated in this preflight. The receipt
identifies its uncommitted source bytes; this source snapshot is committed
before subsequent estimator changes so those bytes remain recoverable.

The next design step is to evaluate a calibration-information-only source
balance: normalize each source's mean information per available exposure,
without seeing the residual shape score or changing the dominance/precision
guards. Its weighted composite score and unique-pixel noise propagation must
be tested and locked before learning coefficients. All source/cell failures
remain in the denominator. A failed three-vector has no reduced-rank or zero
fallback masquerading as a validated correction.
