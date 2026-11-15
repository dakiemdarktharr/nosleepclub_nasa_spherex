# Exposure-Time Model and GLS Astrometry

This is a standalone computational module for SPHEREx data: it reads IMAGE times, builds a design matrix, and fits GLS with rank checks. It is not connected to the point estimator, creates no new source measurement, and makes no claim of detection or measurable parallax on real data.

## Time and reference frame

`parse_image_header` requires `EXTNAME=IMAGE`, a valid `TIMESYS`, and three finite numeric values for `MJD-BEG`, `MJD-AVG`, and `MJD-END`. These MJD keywords are interpreted as **absolute MJD values in days**, without adding `MJDREF`. To reject an offset mistakenly treated as absolute days, the module accepts only MJD 40000–100000. This is the SPHEREx tool's domain limit, not a general MJD definition. If present, `MJDREF` must be finite; scalar and split forms must agree. Nonzero `TIMEZERO`/`TIMEOFFS`, barycentric or unrecognized `TREFPOS`, duplicate important keywords, invalid order, midpoint offset greater than 1 second, or `DATE-*` mismatch with MJD greater than 5 ms are rejected. Present `DATE-*` values are checked, but the module does not infer a timescale if `TIMESYS` is missing. Supported scales are UTC, TAI, TT, TDB, TCG, and TCB; there is no default to UTC for missing metadata, and UT1/LOCAL are not accepted.

`astropy.time.Time` retains the original scale and explicitly converts to TDB for design time. A year is 365.25 TDB days. This is a timescale conversion, **not** a photon light-travel-time correction to the barycenter. [Astropy Time documentation](https://docs.astropy.org/en/stable/api/astropy.time.Time.html) describes scales and formats; the [SPHEREx Explanatory Supplement](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf) describes MJD keywords and spacecraft location.

Earth position uses `get_body_barycentric('earth', time.tdb, ephemeris='builtin')`, returning ICRS barycentric coordinates in AU without depending on global ephemeris configuration or downloading a kernel. [Astropy](https://docs.astropy.org/en/latest/api/astropy.coordinates.get_body_barycentric.html) documents this convention. Do not add `X_SC/Y_SC/Z_SC` to Earth's vector: the header states only a GEOCENTER origin, and axis orientation has not been verified. The separate `spacecraft_parallax_bound` function uses only the XYZ norm and assumes values are in km in an orthogonal geocentric Cartesian frame. It computes the first-order angular bound `||r_sc||/AU × parallax_assumed`; it is not a vector correction, random uncertainty, or fitted parameter. If origin/coordinates are missing, the result is unavailable.

## Design matrix, GLS, and predictions

At a fixed ICRS direction `(α,δ)` supplied by the caller, define east unit vector `e=(-sin α, cos α, 0)` and north unit vector `n=(-sin δ cos α, -sin δ sin α, cos δ)`. Each exposure contributes east/north rows:

```text
east(t)  = east0  + mu_east  * Δt − parallax * (r_earth/AU · e)
north(t) = north0 + mu_north * Δt − parallax * (r_earth/AU · n)
```

Position and parallax use arcseconds; proper motion uses arcseconds per TDB year; Δt is relative to a caller-selected reference. East is `ΔRA cos(dec)`, north is `Δdec`; RA wrap is handled periodically, and the pole's axis direction follows the supplied RA convention. This is a first-order tangent-plane approximation around a fixed direction, not a new absolute coordinate solution. It has no motion/brightness prior and does not model perspective acceleration, aberration, chromaticity, or astrometric-reference systematics.

`design_matrix(..., model='pm_only')` builds **4** parameters `[east0, north0, mu_east, mu_north]`. `model='pm_parallax'` adds parallax for **5** parameters. The choices are explicit; the module does not change models or hold parallax fixed to avoid singularity. `fit_gls` accepts vector `[east_0,north_0,east_1,north_1,...]` and a **full 2N×2N covariance** in arcsec², including between-exposure blocks. It checks positive-definite symmetry, whitens by Cholesky, scales columns, and checks SVD. It does not use a pseudoinverse: degrees of freedom ≤0, deficient rank, or scaled condition number >1000 by default raises `UnidentifiableDesign` with diagnostics. The threshold 1000 is a configurable numerical guard, not a scientific precision guarantee; full rank does not prove measurable parallax. Parameter covariance is conditional GLS using the input covariance; the module does not automatically multiply by reduced χ² or add missing systematics.

`predict` returns the fitted-mean estimate and covariance. Given covariance for new observations and a train/new block covariance, it also returns covariance of `y_new − fitted_mean`, including cross terms. If no cross block is supplied, it assumes zero; the joint covariance is checked for positive semidefiniteness. This is an unconditional linear prediction; it does not add kriging corrections or handle unspecified cross-covariance.

Symmetry and PSD checks are normalized by the standard deviations of matrix elements, with tolerance based on machine epsilon and matrix size; there is no fixed absolute threshold in arcsec². Input covariance is symmetrized only when differences are within rounding tolerance, then must still pass Cholesky. Joint covariance is checked for PSD in correlation scale, including valid singular PSD cases; the cross block is not clipped or replaced. Residual covariance is rechecked for PSD on the scale of its calculation terms: a negative value beyond rounding error raises an error; if negative eigenvalues are only at rounding scale, a small diagonal correction is recorded in `prediction_residual_psd_roundoff_adjustment_arcsec2`, along with the threshold in `prediction_residual_psd_tolerance_arcsec2`. This is numerical handling, not a physical uncertainty term.

Usage example (API illustration only; `headers`, `y`, and `cov` must come from validated data):

```python
from scripts import astrometric_time_model as atm

times = [atm.parse_image_header(h).midpoint for h in headers]
reference = times[len(times) // 2]
A, metadata = atm.design_matrix(times, reference, ra_deg, dec_deg, 'pm_parallax')
fit = atm.fit_gls(A, y, cov)  # raises UnidentifiableDesign when unsupported
B, _ = atm.design_matrix(new_times, reference, ra_deg, dec_deg, 'pm_parallax')
prediction = atm.predict(fit, B, new_cov, train_new_cross_cov)
```

## Completed development audit on the WISE cache

```powershell
.venv/Scripts/python.exe -m unittest tests.test_astrometric_time_model -v
.venv/Scripts/python.exe -m scripts.audit_exposure_times
```

[development-audit.json](../web/data/time-model/development-audit.json) stores manifest hashes, code, each FITS, URLs, times, and per-exposure status. The audit reads only the 31 images already downloaded in the WISE coadd manifest. It does not claim they are all primary strict/broad pairs, and does not read centroids or fit sources. All 31 IMAGE headers are valid: 16 exposures from November 2025 and 15 from April 2026. In this cache, `MJD-AVG` is about 57.55873–57.55882 seconds after `MJD-OBS`; those headers use MJD-OBS as exposure start.

Midpoint span within the two seasons is 4.616 and 5.297 days. Under the illustrative assumptions from [Luhman 2014](https://arxiv.org/pdf/1404.6501), `μ_east=−8.06″/year`, `μ_north=+0.70″/year`, and `π=0.454″`, the maximum predicted Earth-only shift between same-season exposures is 0.108″ and 0.126″. Adding a conservative bound for both spacecraft positions gives conditional bounds of 0.107793″ and 0.126300″, respectively; per-exposure bounds that omit spacecraft position are about 2.134–2.136 × 10⁻⁵″. These are assumed illustrative values, not measured centroids, target fits, or general bounds on acceleration/instrument error.

With identity weights and a reference TDB near the median:

| Sampling | PM-only rank / condition | PM+parallax rank / condition | Numerical interpretation |
|---|---:|---:|---|
| November 2025 only | 4 / 2.67 | 5 / 17,683 | PM+parallax rejected because condition >1000 |
| April 2026 only | 4 / 167.19 | 5 / 8,429 | PM+parallax rejected because condition >1000 |
| All 31 exposures | 4 / 2.31 | 5 / 113.55 | Passes the numerical guard under identity weights; precision is not established |
| Two seasons collapsed to exactly two times | 4 / 2.31 | 4 / undefined | PM+parallax is rank deficient and rejected |

Within-season variation adds algebraic rank to the combined design, but this does not prove parallax can be measured precisely: real covariance, a shared reference, blending, PSF model, and sensitivity were not included in the audit. Next, use validated full covariance and simulate with withheld epochs in already opened fields; consider real inference only after the design, coverage, and precision are independently verified. Do not change products 0.3–0.9 or published WISE measurements.
