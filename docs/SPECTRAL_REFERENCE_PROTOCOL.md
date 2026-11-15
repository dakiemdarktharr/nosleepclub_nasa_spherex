# JWST Spectral Reference and SPHEREx R7 Response Control

This is a diagnostic on development data already available. It asks whether replacing a spectrum with a single monochromatic sample changes the predicted flux. It does not fit positions, inject sources, open 30 new fields, or change the WISE measurement. Code, rules, and input hashes were locked before convolution; no response model was selected based on which result looked best.

The spectrum is the [validated MAST G395M x1d product](WISE0855_EXTERNAL_SED.md), not the author's Figure 4 table. Use only rows with DQ=0, finite flux/error, and error > 0; retain negative flux. The response comes from the [official lab package](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/spherex_spectral_calibrations.html), a 436,705,280-byte archive with SHA-256 `45ff6c57ca68da00a595a4e8a5c2f875cc98b094fde143d9ce109e69df252f09`. The archive is not extracted to disk; verify the full archive hash and the hashes of the 35 D6 CSV files that are read. Raw FITS/tar files remain in Git-ignored `data/raw/`.

## Prespecified calculation

Evaluate all 17 nominal D6 channels, for both `Cent` and `Allpix`, at three response-axis shifts: −0.0064 / 0 / +0.0064 µm, for 102 evaluations. Cent and Allpix are two summaries of the same lab measurement, not independent validation sets. The shifts are sensitivity checks; they are not asserted to represent QR2-to-R7 conversion or a wavelength correction for a cutout.

The diagnostic convention is the photon-weighted mean of Fν:
`∫ Fν(λ) R(λ) dλ/λ / ∫ R(λ) dλ/λ`, returned in Jy. Retain measured small negative response values; do not label them as nonnegative physical throughput. Interpolate linearly between adjacent valid samples only. Do not cross bad-DQ regions or gaps larger than 0.01 µm, and do not extrapolate. Integrate over the union of the spectrum, response, and zero-crossing knots.

If any nonzero absolute response weight is unsupported, the full-band mean must be null. Still report the mean over the supported portion under its own name, the missing absolute weight, negative weight, and the weight-vector hash; never use a partial mean as a full-band estimate. Ratios against monochromatic values and shift sensitivity are calculated only for full-support means with positive monochromatic/baseline denominators. Keep all unsupported evaluations in the denominator of 102. This audit has no promotion threshold and does not select a model.

Do not infer total uncertainty by treating spectral rows as independent. Full spectral covariance, shared calibration, epoch differences, and variability are not available. The pipeline's photometric reference convention has not been verified; this photon-weighted convention is a transparent linear functional, not a conversion into SPHEREx image MJy/sr.

## Lock, run, and limitations

```powershell
.venv/Scripts/python.exe -B -m unittest tests.test_spectral_bandpass tests.test_lab_spectral_response tests.test_wise0855_x1d -v
.venv/Scripts/python.exe -B -m scripts.audit_spectral_reference --design
# Commit source, tests, protocol, and design before the next command:
.venv/Scripts/python.exe -B -m scripts.audit_spectral_reference --run
```

The design and output refuse overwrites. The runner checks that the source/design match Git HEAD, verifies both raw input hashes/sizes, and checks each CSV schema. The R7 response's detector coordinates have not been matched to WCS A for each exposure; the x-axis direction for D4–D6 requires care. A nominal channel mean is not an exact response for an individual pixel.

The [delivery documentation](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHERExSpectralFiles_202607.pdf) identifies these as R7 products. The response at a position and the channel average have different widths; D5/D6 band centers were corrected relative to the previous release. Before combining those assumptions with QR2, handling negative response, solid angle, gain, and uncertainty, a new protocol is required. This audit compares spectral predictions only; it does not measure astrometric bias.
