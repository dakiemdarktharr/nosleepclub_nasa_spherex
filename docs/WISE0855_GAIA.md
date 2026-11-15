# WISE 0855: Expanded Star Field and Gaia DR3 Check

Run date: 2026-10-30. [Running demo](http://127.0.0.1:8766/), [machine-readable results and provenance](../web/data/gaia/results.json), [star map](../web/data/gaia/map.json), [research and bibliography](GAIA_RESEARCH.md).

## Results and interpretation

The astrometric frame changes little when reference stars are changed. The modeled error budget falls for the broad-spectrum configuration, but tests on real image backgrounds still show substantial errors. **WISE 0855's astronomical motion and systematic accuracy remain unconfirmed.**

| Quantity | Strict spectrum, primary | Broad spectrum, sensitivity check |
|---|---:|---:|
| Exposures per epoch | 2 | 10 |
| Measured East / North | −2.86″ / +1.07″ | −3.26″ / +0.43″ |
| Vector length ± conditional error | 3.06″ ± 0.99″ | 3.29″ ± 0.52″ |
| Vector change from pre-Gaia version | 0.21″ | 0.40″ |
| RMS of 7 stars held out from fitting, after Gaia-motion subtraction | 0.27″ | 0.17″ |
| Star-set swap: vector change | 0.16″ | 0.04″ |
| Leave-one-star-out: maximum change, 14/14 runs completed | 0.09″ | 0.17″ |
| Affine test: vector change | 0.04″ | 0.10″ |
| Difference from external predicted vector | 1.70″ | 1.21″ |

The broad configuration was not selected as primary because its error is smaller. Both configurations and spectral rules are carried over from the previous step and share exposures, so they are not independent checks. Current broad-spectrum aperture S/N before/after is 7.68 / 7.42, versus best single-image 4.90 / 4.91; strict is 3.18 / 4.50, versus 2.99 / 4.60. These are conditional S/N values at the fitted position with the corresponding masks/coverage, not confidence in a blind detection or total flux.

## Data and star selection

Keep the same 20 exposures from the earlier broad configuration; add no epochs and change no calibration release. Download 0.32° cutouts instead of 0.12°, at the same center; raw records include URL, observation ID, SHA-256, and native WCS. Use the official D6 ePSF at 5× oversampling and CWAVE/CBAND pinned in the previous step. [IRSA recommends this ePSF for QR2 as well](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/).

Query `gaia_dr3_source` through `https://irsa.ipac.caltech.edu/TAP/sync`: 0.25° cone, G<18.5, returning 675 sources. Full ADQL, VOTable hash, and covariance fields are saved in the report. Export `source_id` as a string in JSON to preserve 64-bit integer precision in JavaScript.

Before refitting the target, select stars using the fixed `RULES`:

- Five- or six-parameter astrometric solution, RUWE≤1.4, ≥9 visibility periods; no duplicated/non-single-star flags, `ipd_frac_multi_peak`≤2.
- |proper motion|≤300 mas/year and |parallax|≤20 mas to keep first-order propagation appropriate. This is a study choice, not a universal Gaia standard.
- Match SPHEREx peaks with propagated Gaia positions within 1 pixel; exclude Gaia neighbors with G<18.5 within 18″ or SPHEREx peaks within 3.5 pixels. Exclude the 8-pixel-radius target region and stars near edges.
- Fit each star/exposure with native ePSF: S/N≥7, reduced chi-square≤3, converged and no boundary hit. Require valid fits in ≥70% of 20 exposures and ≥3 exposures in each epoch.

There were 85 initially isolated matches; 21 sources passed native checks. The report retains the match audit, valid-frame counts, and rejection reasons for every source and selected-source frame. Select sources across quadrants, then split by fixed source-ID hash: **14 alignment stars, 7 heldout from fitting**. Each broad exposure actually uses 12–14 stars; swaps retain at least 6. Do not use the WISE 0855 vector or agreement with the prediction to choose stars.

Gaia DR3 has reference epoch 2016.0 in TCB. Propagate proper motion including cos Dec and parallax using Earth's barycentric position; retain the 5×5 covariance and correlations. Original field information is in the [Gaia/DPAC schema at AIP](https://gaia.aip.de/metadata/gaiadr3/gaia_source/). Perspective acceleration, Gaia global systematics, and spacecraft position instead of Earth are not modeled; for this limited low-motion/parallax star set, these terms are below current SPHEREx error levels.

## Frame fit, checks, and error budget

Fit a translation per exposure by GLS from native centroid minus propagated Gaia position, using centroid and Gaia covariance plus a 0.01-pixel floor for reference stars. Inflate covariance when chi-square>1. Fit WISE 0855 separately in each epoch on original pixels with per-exposure amplitude and background plane; do not constrain the vector to the external prediction.

Star-set swaps, leave-one-training-star-out checks, and a six-parameter affine fit all completed. When changing calibration, keep the target-stamp pixel set and ePSF fixed; apply affine transformation to both the center and local Jacobian. This avoids mixing sensitivity with added/removed edge pixels from recutting the stamp.

Displacement covariance budget:

1. **Centroid noise:** Jacobian covariance, inflated by chi-square, checked against 128 Gaussian-noise simulations per epoch.
2. **Calibration:** propagate covariance through per-exposure Gauss–Newton influence on the fixed pixel set. The total influence for a shared translation must equal −I; tests check this coordinate invariance. Bootstrap 256 times with paired star resampling across epochs; draw one shared Gaia five-parameter sample per star for all exposures, preserving temporal correlation. Use a positive covariance envelope with the formal estimate rather than reducing errors when bootstrap is smaller.
3. **Heldout stars:** second moment of residual displacement after Gaia-motion subtraction, retaining mean bias and scatter. This is conservative and may count some noise twice; only seven stars are available, and they are brighter/more isolated than the target.

All calibration bootstraps produced 256 draws with no failures. Each position's error has separate calibration and field-residual terms; errors between epochs are correlated, so do not simply add two position ellipses to get the vector error. The 68% vector ellipse uses Δχ²=2.30; vector-length error is first-order propagation along its direction.

Gaia also contributes to the input WCS of SPHEREx. “Held out from fitting” means excluded from this demo's **local fit**, not independent from the mission's calibration catalog or observations. Gaia optical and infrared photocenters may differ due to color or unresolved neighbors.

## Injection: the model error does not describe every image background

Keep eight off-target positions fixed and inject stationary or moving sources with displacement `(0.60, 0.05)` pixel. Two brightness levels are 0.5× and 1× the per-exposure WISE 0855 amplitude profile. Do not change exported science images, add shot noise, or change alignment stars. Use the same ePSF family for injection and fitting; ePSF calibration error is not separately tested.

| Configuration | Brightness | Source case | Inside 68% ellipse / 8 attempts | Vector-error RMS |
|---|---:|---|---:|---:|
| Strict | 0.5× | Stationary | 7/8 | 2.68″ |
| Strict | 0.5× | Moving | 6/8 | 1.76″ |
| Strict | 1× | Stationary | 7/8 | 1.33″ |
| Strict | 1× | Moving | 7/8 | 0.83″ |
| Broad | 0.5× | Stationary | 5/8 | 3.05″ |
| Broad | 0.5× | Moving | 2/8 | 2.26″ |
| Broad | 1× | Stationary | 6/8 | 2.72″ |
| Broad | 1× | Moving | 6/8 | 1.75″ |

All fits converged without boundary hits; large errors remain included. Some fits land on photocenters blended with background; high chi-square inflates the error but does not remove bias. In particular, 2/8 in the faint/moving group indicates that the error model needs more testing. Eight positions, brightness/source cases, and two configurations share backgrounds; these rates are correlated and are not 64 independent samples, completeness, or a calibrated false-positive rate. Do not use pooled RMS to reassign the target's error.

The broad-spectrum vector differs from the Luhman 2014 + external parallax prediction by about 1.21″. The report does not refit proper motion/parallax or add uncertainty from the old prediction to this comparison. The residual difference and injection bias justify keeping **`candidate_motion_unconfirmed`** despite frame stability under star changes. Do not interpret Mahalanobis distance as Gaussian sigma or discovery probability.

## Demo and reproduction

The web UI adds two Gaia configurations, a wide-field map with selectable alignment/heldout stars, Gaia quality for each star, a CV table, error budget, and all injection groups. The pre-Gaia version remains available for comparison. FITS/JSON downloads have WCS, units, and provenance. Native centroids are fit before display-image cross-convolution. Source code and calibration hashes are in the report; large raw files remain ignored.

After the baseline/coadd steps, use the README commands:

```sh
.venv\Scripts\python scripts/prepare_gaia_data.py
.venv\Scripts\python scripts/gaia_motion.py --publish
.venv\Scripts\python -m unittest discover -s tests -v
```

Without `--publish`, the script writes only to the processing cache; `--references-only` stops after star selection/measurement. The centroid cache fingerprint covers processing functions, rules, input manifest, and dependencies; measurement edits invalidate it. The 31 offline tests cover Gaia propagation, correlations, GLS/affine and influence signs, covariance budget, split audit, provenance/FITS versions, and old baseline checks. Software tests passing do not confirm an astronomical source.

## Next step and completion criteria

**Next milestone: fit multiple sources on original pixels for WISE 0855 and nearby background**, retaining the Gaia frame just checked. Add infrared sources, jointly fit nuisance/background by exposure, and evaluate color/spectral-response dependence; do not use Gaia source IDs as a complete infrared source list.

Completion requires comparing single-source/joint-source fits on identical data; splitting injection development and heldout sets by position/sky region; and reporting bias, failures/boundary hits, and ellipse coverage across brightness levels. Check whether nominal 68% matches sampling coverage on heldout data and compare bias with published error. Upgrade the science status only when systematic terms have a defined budget and more epochs can distinguish proper motion/parallax. Then build a candidate-ranking vision model on a benchmark without sky-region leakage.

Gaia acknowledgment: data from ESA's Gaia mission, processed by DPAC. Funding is provided by national institutions participating in the Gaia Multilateral Agreement; see the [citation guidance](https://gaia.aip.de/metadata/gaiadr3/gaia_source/).
