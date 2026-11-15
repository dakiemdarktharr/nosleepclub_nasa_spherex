# Shared-Flux Fitting Core

`scripts/linked_flux_profile.py` solves the linear problem at a **fixed position**:

`data_i = A * coefficient_i * template_i + nuisance_i @ b_i`.

Each image has its own background/neighbors; A is shared. Units are checked explicitly: the units of A multiplied by the template units must match the image units. A may be in Jy and the template in sr⁻¹ for an image in Jy/sr, but values and units must be converted consistently before calling the function. The kernel does not convert numeric values labeled MJy/sr into Jy/sr.

Supply coefficients with their provenance; do not infer them from separately fitted per-frame fluxes or injected truth. The provenance string is an input contract and does not prove the coefficients themselves have been verified. There is no adapter that joins SED/response/gain/solid angle to real pixels yet, so **this has not replaced the WISE model**.

Each frame accepts diagonal errors or a positive-definite covariance. Whitening and column-normalized SVD check the rank of the nuisance and full designs; degenerate overlapping sources are rejected rather than hidden by a pseudoinverse. The result includes conditional amplitude and variance, nuisance terms, raw/whitened residuals, χ², rank, degrees of freedom, and condition number. Negative amplitudes are retained; they are not clipped and mislabeled as a positive-source measurement with Gaussian error. No physical constraint, amplitude prior, or detection gate is implemented.

Eight tests compare against a separately constructed full WLS solution and cover nondiagonal covariance, reordering/rescaling, score orthogonality, units, and near-degenerate designs:

```powershell
.venv/Scripts/python.exe -B -m unittest tests.test_linked_flux_profile -v
```

Covariance between frames is assumed independent; template, coefficient, mask, and position are fixed. There is no IRLS, SED/PSF/calibration uncertainty, shared registration, or centroid/motion fit. A numerically correct kernel does not establish higher S/N, lower bias, or scientific covariance on the sky.
