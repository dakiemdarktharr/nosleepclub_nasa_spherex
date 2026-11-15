# JWST Spectrum and SPHEREx R7 Response Control

*English translation of the hash-locked original protocol, [SPECTRAL_REFERENCE_PROTOCOL.md](SPECTRAL_REFERENCE_PROTOCOL.md). The original remains the canonical source used by the scientific evidence manifests; this translation is provided for readability.*

This is a diagnostic on existing development data. It asks whether replacing a spectrum with a monochromatic point changes the predicted flux. It does not fit positions, inject sources, open 30 new fields, or replace the WISE measurement. Lock code, rules, and input hashes before calculating the convolution; do not select a response convention based on favorable results.

The spectrum is the [verified MAST G395M x1d](WISE0855_EXTERNAL_SED.md), not the authors' Figure 4 table. Use only DQ=0, finite flux/error, and error>0; retain negative flux. The response is from the [official lab package](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/spherex_spectral_calibrations.html), archive size 436,705,280 bytes, SHA-256 45ff6c57ca68da00a595a4e8a5c2f875cc98b094fde143d9ce109e69df252f09. Do not extract the archive to the filesystem; check its full hash and the individual hashes of the 35 D6 CSVs read. Raw FITS/tar files remain under Git-ignored data/raw/.

## Prespecified calculation

Calculate all 17 nominal D6 channels, both Cent and Allpix, at three response-axis shifts: −0.0064 / 0 / +0.0064 µm, for 102 attempts. Cent/Allpix are two aggregations of the same lab measurement, not independent validation sets. The shift is a sensitivity test; it does not assert a QR2→R7 transformation or correct the cutout wavelength.

The diagnostic convention is the photon-weighted mean of Fν:

    ∫ Fν(λ) R(λ) dλ/λ / ∫ R(λ) dλ/λ

The mean is returned in Jy. Retain small measured negative response values; do not label them as physically nonnegative throughput. Interpolate linearly between adjacent valid samples; do not cross bad DQ or gaps over 0.01 µm, and do not extrapolate. Integrate over the union of spectrum knots, response knots, and zero crossings.

If any absolute response weight other than zero is unsupported, the full-band mean must be null. Still report the supported-part mean under a separate name, the missing absolute-weight fraction, the negative part, and the hash of the weight vector. Do not use a partial mean as an estimate of the full band. Calculate the ratio to the monochromatic value and shift sensitivity only for a full-support mean with a positive monochromatic/baseline denominator. Keep unsupported attempts in the denominator of 102. This audit has no promotion threshold and does not select a model.

Do not infer total uncertainty by treating spectral rows as independent: full spectral covariance, shared calibration, epoch differences, and variability are missing. The SPHEREx pipeline's photometric reference convention is unverified; this photon convention is a transparent linear functional and has not been converted into MJy/sr for SPHEREx images.

## Lock, run, and limitations

    .venv/Scripts/python.exe -B -m unittest tests.test_spectral_bandpass tests.test_lab_spectral_response tests.test_wise0855_x1d -v
    .venv/Scripts/python.exe -B -m scripts.audit_spectral_reference --design
    # Commit source, tests, protocol, and design before running:
    .venv/Scripts/python.exe -B -m scripts.audit_spectral_reference --run

Design and output refuse overwrites. The runner checks that sources/design match Git HEAD, verifies hashes/sizes for both raw inputs, and validates each CSV schema. The detector-coordinate response for R7 has not been joined to WCS A for each exposure; D4–D6 x orientation requires attention to the documentation. Do not use nominal channel means as an exact response for an individual pixel.

The [delivery documentation](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHERExSpectralFiles_202607.pdf) identifies this as an R7 product; the response at the position center and the channel average have different widths, and D5/D6 band centers were corrected relative to the previous version. Combining these assumptions with QR2, handling negative response, solid angle, gain, and uncertainty requires a new protocol before physical simulation or a shared-amplitude fit. This audit tests only differences in spectral predictions; it does not measure astrometric bias.
