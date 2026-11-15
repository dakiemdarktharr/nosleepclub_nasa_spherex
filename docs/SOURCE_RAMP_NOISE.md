# Source Poisson Injection for an Idealized Ramp

The [source_ramp_noise.py](../scripts/source_ramp_noise.py) module generates the **signal and shot noise from an added source** for an idealized up-the-ramp model. It does not regenerate sky, read noise, or dark noise in the original image, modify input image/variance, or validate the actual SPHEREx detector model.

## Formula source and independent derivation

In the public [Caltech/IPAC SPHEREx source pipeline](https://github.com/Caltech-IPAC/spherex-pipelines/blob/aa0ba446ee12971024fe13dc1c47387615bbe85e/py_src/spx_tasks/create_variance_map.py), snapshot commit `aa0ba446ee12971024fe13dc1c47387615bbe85e`, Git blob SHA-1 `c682a3c8574b16e0f092dd89266a0dbaeaad9b47`, the nominal branch uses:

```text
n = SURLIM - (SURDLY - 1)
t_intg = n * TSAMP
P(n) = (6/5) * (n² + 1)/(n² - 1)
Var(source rate) = P(n) * s / (n * TSAMP)
```

This checks the formula in the inspected snapshot; it does not claim every data version or pixel uses that nominal processing. The [Explanatory Supplement](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf) describes the variance map and separately handled overflow/transient cases.

Independent derivation under an idealized model: take `n` nondestructive charge samples at `t_k=k*dt`, `k=0,…,n−1`. Charge increments between samples are independent `X_j ~ Poisson(s*dt)`, `j=1,…,n−1`; the initial sample is an intercept and is removed when fitting an OLS slope with intercept. The coefficient of each increment in the slope is:

```text
w_j = 6*j*(n-j) / [dt*n*(n²-1)]
slope − s = Σ_j w_j * (X_j − s*dt)
Var(slope) = s*dt*Σ_j w_j² = P(n)*s/(n*dt)
```

Because `Σ w_j*dt=1`, subtracting the mean does not add or remove expected signal. Directly calculating accumulated-charge covariance `Cov(Q_i,Q_j)=s*dt*min(i,j)` gives the same result: `P(2)=2`, `P(3)=1.5`, `P(75)=1.2004267425320057`. The simulation uses **integer Poisson draws** for each increment, not a Gaussian approximation.

## API and timing

`inject_source_ramp(expected_source, gain, header, valid_mask, rng, *, gain_provenance, source_provenance=None, batch_pixels=4096)` accepts:

- `expected_source`: a 2D Astropy `Quantity`, convertible to `MJy/sr`, finite and nonnegative on valid pixels.
- `gain`: a scalar or same-shape Astropy `Quantity`, convertible to `(MJy/sr)/(electron/s)`, finite and positive on valid pixels. This is an **absolute physical gain**, not electronic gain in e⁻/ADU. The caller must verify that the gain map matches detector, epoch, version, detector/sky orientation, and image processing. The module does not verify this compatibility.
- `header`: requires integer `SURLIM` and `SURDLY`, plus finite positive `TSAMP` and `XPOSURE` in seconds. Duplicate keys (including case-only duplicates) and missing keys are rejected. `2 ≤ n ≤ 10000` is an implementation limit. Header must satisfy `XPOSURE ≈ (n−1)*TSAMP`, with tolerance equal to the larger of 1e-4 seconds and 1e-8 times the span. Otherwise the module rejects the input instead of choosing a different time.
- `valid_mask`: same-shape boolean array. Only `True` pixels are simulated/validated. `False` pixels return NaN in all three added layers; the caller must preserve their original image/variance/flags. The mask must exclude pixels that do not match the nominal model first.
- `rng`: an explicitly created `numpy.random.Generator`. `gain_provenance` must have a nonempty `source` string; the caller may supply calibration URL, hash, and version. `source_provenance` records synthetic source information.

In this model `XPOSURE` is the **time span between the first and last sample**, `(n−1)*TSAMP`; `n*TSAMP` is the `t_intg` convention in the pipeline variance formula. Do not substitute one value for the other. Example nominal header `SURLIM=77`, `SURDLY=3`, `TSAMP=1.5349 s`: `n=75`, span `113.5826 s`, while `t_intg=115.1175 s`.

If `S` is expected intensity in MJy/sr and `g` is matching gain in `(MJy/sr)/(e⁻/s)`, source rate is `s=S/g`; intensity noise is `g*(slope−s)`, `added_image=S+noise`, and `added_variance=P(n)*g*S/(n*dt)` in `(MJy/sr)²`. Output has three layers: `added_image`, `source_noise`, and `added_variance`, plus a copied mask and provenance. Provenance records SHA-256 hashes for normalized numeric source/gain/mask arrays, header values/units, caller-provided calibration source, RNG bit-generator/state before and after, batch size, formula, and source pipeline. The caller is responsible for supplying the exact calibration version/URL/hash; an array hash does not prove that calibration is physically correct.

The module does not allocate an `n × image` array: Poisson scratch values are processed in batches of at most `batch_pixels`; additional memory scales as `O(image pixels + batch_pixels + n)`. With the same inputs, seed, bit generator, and batch size, output can be reproduced; changing batch size may change RNG consumption order. The batch limit is 1–1,000,000 pixels.

```python
import numpy as np
import astropy.units as u
from scripts import source_ramp_noise as srn

source = np.full((3, 3), 0.2) * (u.MJy / u.sr)
gain = 0.05 * ((u.MJy / u.sr) / (u.electron / u.s))
header = {'SURLIM': 77, 'SURDLY': 3, 'TSAMP': 1.5349, 'XPOSURE': 113.5826}
valid = np.ones((3, 3), dtype=bool)
addition = srn.inject_source_ramp(source, gain, header, valid, np.random.default_rng(123),
                                  gain_provenance={'source': 'synthetic example'},
                                  source_provenance={'source': 'synthetic model'})
# The caller adds added_image and added_variance to the original image/variance at valid pixels.
```

## Limits and checks

Photon arrivals are assumed independent across pixels and sampling intervals; slope fitting is unweighted OLS with a linear gain and no resampling covariance. Partial-ramp, overflow, transient, nonlinearity, saturation, persistence, crosstalk, PSF/gain uncertainty, and other processing are not modeled; the valid mask and metadata must exclude these cases. This primitive and its unit tests cannot establish completeness, coverage, calibration, or an astronomical detection.

```powershell
.venv/Scripts/python.exe -m unittest tests.test_source_ramp_noise -v
```

Tests include independent OLS ramp covariance for n=2/3/75, discrete Poisson support, empirical mean/variance/cross-covariance with a fixed seed and six-standard-error tolerance, units and scaling, mask/zero behavior, reproducibility, and rejection of invalid inputs/headers. Use the primitive only in a study with source, gain, and protocol locked before running; this is not a Monte Carlo study on real images.
