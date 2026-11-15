# Proposed Roadmap

This is NoSleepClub’s preparation backlog. Unchecked items have not been completed. The product should be delivered against the official hackathon schedule.

## Current technical slice

- [x] Download real WISE 0855 cutouts, inspect wavelengths, and select three pairs.
- [x] Align images, apply PSF cross-convolution, and export difference images with provenance.
- [x] Build a before/after web demo with highlights, evidence, and local notes.
- [x] Combine images within each epoch by spectrum and measure centroids independently with conditional uncertainties.
- [x] Propagate interpolation covariance into S/N; retain comparison stars, bootstrap checks, and injections on real backgrounds.
- [x] Expand the reference-star field, compare with Gaia, and test swapping the alignment-star set.
- [x] Leave out 14 stars in turn, test affine alignment and 32 injections per configuration, and retain image-background limitations.
- [x] Test multi-source infrared/ePSF fits on 30 preregistered regions; the gate for replacing the default was not met.
- [x] Download 129 cutouts in three new fields and check Gaia and synthetic sources under a preregistered protocol; retain fields with too few alignment stars.
- [x] Add a quality gate, infrared deblending/Huber fitting, and a preregistered check on 115 cutouts in three other fields; the replacement gate was not met.
- [x] Separate calibration and validation, lock the error floor before testing 122 cutouts across three new fields; position/covariance gates were not met.
- [x] Run a 2×2 ablation on five opened fields; retain the simple baseline and lock covariance by S/N/background before 135 cutouts across three new fields; the overall gate was not met.
- [ ] Diagnose bias and blending in field `w350`; add observational features and more varied field-level calibration before a new external set.
- [ ] Check the full spectral response, inject sources at multiple positions, and add a third epoch.
- [ ] Verify WISE 0855 motion using these data.

See the [external benchmark](EXTERNAL_BENCHMARK.md), [Gaia results](WISE0855_GAIA.md), and [research notes](GAIA_RESEARCH.md).

## Preparation

- [x] Read the official challenge details and review its resources.
- [x] Create the public GitHub repository and initial documentation.
- [ ] Review the official resource list again when it is published on 13 November 2026.
- [ ] Agree on team roles, demo scope, and the software license.

## At implementation start

### 1. Verify the data first

- [ ] Record source, version, reuse terms, query method, and download limits.
- [ ] Retrieve observations of a test target from different times.
- [ ] Check coordinate system, epoch, units, WCS, and quality flags.
- [ ] Create a reproducible manifest so every team member uses the same data.

### 2. Complete the first small end-to-end workflow

- [ ] Choose technologies after determining how data will be accessed and processed.
- [ ] Accept and validate RA/Dec, choose a sky region, and set a time range.
- [ ] Create cutouts of the same region and align them on a shared coordinate grid.
- [ ] Display an image sequence with play/pause, frame stepping, and observation times.
- [ ] Handle loading, errors, and empty results.

### 3. Validate and package the demo

- [ ] Try all five targets in `CHALLENGE.md`; record data limitations as well.
- [ ] Check the interface on small screens and with keyboard controls.
- [ ] Document reproduction steps, configuration, run commands, and appropriate checks.
- [ ] Prepare the demo, narration, and credits for data and assets.

### Optional work after the main flow

- [ ] Add field-of-view selection and shareable coordinate URLs.
- [ ] Compare, add, or subtract images with an explanation of normalization.
- [ ] Choose spectral bands/detector groups and display quality metadata.
- [ ] Add catalog overlays or spectrum generation if data and time allow.
