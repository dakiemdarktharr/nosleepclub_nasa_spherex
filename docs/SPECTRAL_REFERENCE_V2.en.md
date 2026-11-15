# Spectral Control: Fix the Zero Crossing and Retain Every Trial

*English translation of the hash-locked original, [SPECTRAL_REFERENCE_V2.md](SPECTRAL_REFERENCE_V2.md). The original remains the canonical source used by the scientific evidence manifests; this translation is provided for readability.*

V1, locked at b3eb94c, stopped before results were published. The fourth run, Cent channel 2 at an offset of −0.0064 µm, had a very small positive lobe that made the solution-position ratio round to 1. Calculating the remaining lobe length as h × (1 − fraction) then produced 0 and was rejected by the guard. The [failure receipt](evidence/0.10/spectral-reference-b3eb94c-aborted.json) retains reproducible inputs; V1 code and design remain unchanged.

V2 uses a new kernel, spectral_bandpass_v2.py, to avoid subtracting away a small lobe while retaining both sign and absolute weight. It does not clip response or flux, remove support limits, or relax tests. The new runner records numerical_failure, partial_only, and full_support separately across all 102 trials; a numerical error does not become zero flux or disappear from the denominator.

While fixing the issue, a specialist ran a numerical preflight on the same 102 development conditions: no exceptions remained, and all 102 had only partial support. This result was viewed **before** the V2 design commit. V2 was locked for release reproducibility; do not describe it as an unseen experiment, independent validation, or out-of-sample evidence. The 30 candidate fields remain unopened.

All physical choices, channels, offsets, and interpretation limits from [protocol V1](SPECTRAL_REFERENCE_PROTOCOL.en.md) remain unchanged. In particular, photon weighting has not been verified as the SPHEREx calibration convention; nominal response R7 has not been joined to each QR2 pixel. This is not a truth spectrum, astrometric validation, improved accuracy result, or evidence for fitting WISE with the old covariance.

    .venv/Scripts/python.exe -B -m unittest tests.test_spectral_bandpass_v2 tests.test_lab_spectral_response tests.test_wise0855_x1d -v
    .venv/Scripts/python.exe -B -m scripts.audit_spectral_reference_v2 --design
    # Commit code, tests, protocol, and v2-design.json before running:
    .venv/Scripts/python.exe -B -m scripts.audit_spectral_reference_v2 --run

The V2 design hashes V1/V2 sources, the protocol, both raw inputs, and spectral metadata. The new output is web/data/spectral-response/v2-development-audit.json; do not overwrite an existing design or result. Report complete full-band support, partial-spectrum-only support, and numerical failures, and include ratios only when denominators are valid.
