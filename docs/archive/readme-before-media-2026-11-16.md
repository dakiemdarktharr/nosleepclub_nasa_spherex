> Historical README preserved from commit `b0934f6` (16 November 2026). Status statements describe their recorded checkpoints, not current certification. Start with the [current README](../../README.md) or [documentation index](../README.md).

# Touch The Sky

**NoSleepClub · NASA Space Apps Challenge 2026 · [Planet X and SPHEREx](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details)**

Touch The Sky is an educational website for middle-school learners and anyone curious about space. It helps visitors understand NASA’s SPHEREx mission through a playable learning story, short lessons, a mission guide, and an interactive way to explore real SPHEREx images. The goal is to make infrared astronomy approachable, build confidence in reading scientific images, and encourage learners to ask what the data can—and cannot—show.

**[Open Touch The Sky](https://nosleepclub-nasa-spherex.vercel.app/?lang=en)** · [Challenge: Planet X and SPHEREx](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details)

## What visitors can do

### Learn through the game

In **Touch The Sky**, players join Gagoo aboard a spacecraft and meet Alien X. They study a lesson on the ship’s tablet, answer six questions, and earn story fuel that powers a short flight sequence. The lesson introduces infrared light, filters, false-color images, spectra, and how astronomers use observations across multiple infrared bands to study material such as water ice in star-forming regions.

Fuel, aliens, wormholes, and flight progress are fictional game mechanics. They are not SPHEREx telemetry or scientific results. Learning progress is saved in the current browser, not in an account.

### Explore three short lessons

The lesson journal is designed for learners around grades 6–9 and for self-guided exploration. Its three activities take about 19 minutes in total:

1. **Why does SPHEREx photograph the same patch of sky again?** Learn how filters separate infrared wavelengths and why the same region can look different across bands.
2. **Can you find the same group of dots again?** Navigate a saved sequence of three real SPHEREx observations of the Epsilon Indi B field, recorded on 29 April, 1 May, and 7 May 2025 UTC.
3. **Did the bright dot really disappear?** Read missing-data and quality masks, compare image alignment, and consider what evidence is needed before claiming a source changed.

Each lesson includes an activity and connects to a six-question quiz with explanations. The material has not yet been evaluated in a formal classroom study.

### Read the SPHEREx mission guide

The **About SPHEREx** section explains the mission’s three science goals: studying the early universe through galaxy distributions, measuring the accumulated light from galaxies across cosmic history, and mapping ices in dense star-forming clouds. It also introduces the observatory, its infrared instrument, detectors, filters, data products, and the path from measurements to research.

SPHEREx measures near-infrared light from **0.75 to 5.0 micrometers**. Its six detectors and variable filters provide **102 nominal spectral channels** across the sky. The guide distinguishes explanatory diagrams and assigned colors from direct observations, and links to NASA and the SPHEREx archive for further reading.

### Explore real SPHEREx images

From **Explore the Sky**, visitors can select an example target or search by right ascension and declination. Search options include the **DR1** or **QR3** release, detector band, field of view, and an optional date range. The app queries the NASA/IPAC Infrared Science Archive (IRSA), lists available observations, and retrieves FITS cutouts for viewing.

The image viewer can:

- Compare two observations side by side on a shared view, or blink between them.
- Inspect compatible observations as a time sequence, with observation dates and metadata for each frame.
- Show the selected detector band and the wavelength at the target position when the FITS metadata supports it.
- Identify masked or missing pixels and provide links to source FITS files and provenance records.
- Export the query and viewed-frame metadata for later reference.

For comparisons, the app reads the FITS WCS/SIP coordinate solution and resamples images to a common tangent-plane grid. It applies consistent display and mask rules to the compared frames. Time playback is limited to compatible observations; it is a viewing aid, not a motion or variability measurement. The sequence eligibility rule checks detector, mask policy, usable center pixels, and wavelength overlap at the field center. Scientific claims require separate analysis of calibration, alignment, masks, uncertainty, and the underlying measurements.

## How the project teaches image literacy

Touch The Sky connects mission science with the choices a learner makes while viewing data. A learner can change the infrared band, revisit an observed field, read observation dates, compare image masks, and ask whether a visual difference might come from wavelength, image coverage, quality flags, or time. The site encourages learners to inspect sources and limitations before interpreting a change as an astronomical result.

The site presents educational material and interactive data views. It does not certify astronomical detections or establish that a source moved, brightened, or faded. The saved Epsilon Indi B sequence is suitable for learning to navigate repeated observations; it does not resolve the pair or confirm motion or variability.

## Technology

- **Frontend:** HTML, CSS, and modular JavaScript. Interactive spacecraft and sky scenes use WebGL, with Three.js bundled in `web/assets/three-0.187.0/`.
- **Mission and learning content:** Structured lesson data, bilingual interface copy, interactive diagrams, quizzes, and browser-local progress storage.
- **Archive access and image handling:** NASA/IPAC IRSA SIA queries and FITS cutouts; Python services use Astropy, NumPy, and Pillow for FITS/WCS handling and image preparation.
- **Local preview:** A Python launcher serves the web app and its local API routes. The static demo server can also serve the saved educational products without the live API.
- **Deployment:** Vercel serves the site and Python API routes. Selected review features use an isolated MongoDB database.

The original research and validation work remains documented under [`docs/`](../../docs/). Those reports include methods, data provenance, uncertainty qualifications, and open limitations. They should be read in context; their presence does not mean every exploratory analysis is a validated astronomical result.

## Run the local preview

From the repository root, install the Python requirements and start the application:

```powershell
python -m pip install -r requirements.txt -r web/requirements.txt
python -m scripts.serve_app --port 8767
```

Open <http://127.0.0.1:8767/>. The local launcher binds to loopback and does not load production secrets. Searching IRSA for new observations requires an internet connection; the saved Epsilon Indi B sequence is available when the archive is slow or unreachable.

To serve the saved educational demo without the local API:

```powershell
python scripts/serve_demo.py
```

## NASA data and references

The project uses NASA mission and science resources and SPHEREx archive data. Principal sources include:

- [NASA/IPAC IRSA SPHEREx archive documentation](https://caltech-ipac.github.io/spherex-archive-documentation/)
- [IRSA SPHEREx data access](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/)
- [IRSA SPHEREx data products](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/)
- [NASA/JPL SPHEREx mission science](https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/science/)
- [NASA SPHEREx mission overview](https://science.nasa.gov/missions/spherex/)

Individual dataset and asset records are linked from the app and recorded in the relevant manifests. For usage terms and third-party credits, see [`NOTICE.md`](../../NOTICE.md).

## Data, rights, and project status

Original project code and accompanying original documentation are released under the [MIT License](../../LICENSE). External datasets, fonts, illustrations, and dependencies retain their own terms; see [`NOTICE.md`](../../NOTICE.md) before reuse.

SPHEREx observations can be masked, incomplete, or unavailable for a selected field and date. IRSA requests may be slow or temporarily fail. Image colors and contrast are visualization choices, not visible-light colors or measurements of temperature. The app preserves source links and metadata where available so that viewers can inspect how an image was obtained.

This is an independent NASA Space Apps Challenge project and is not an official NASA product or endorsement.

## Current product workflow

[Open the Explore the Sky section](https://nosleepclub-nasa-spherex.vercel.app/#explore) · [Workflow and limitations](../../docs/WORKFLOW_UI.md).

The main task flow is **Choose data → Compare images → Check evidence → Record observations**. Each screen has one primary action and a clear way back. The interface keeps labels, units, and decision-relevant warnings visible, with deeper explanations available on demand. A separate verification library lists research reports without interrupting the image workflow.

WISE demo data and live IRSA searches keep separate context. Residual views do not show WISE motion vectors or S/N. IRSA comparison retains image A and loads image B; notes are restored for the matching query/image pair and exported as JSON, not sent to the WISE review API. Help, browser Back/Forward, and skip links retain the active data source. These interface changes do not alter science products or the WISE measurement.

For learners, the project connects mission science with choices made while viewing data: changing an infrared band, revisiting a field, reading observation dates, comparing masks, and considering whether a visible difference is caused by wavelength, image coverage, quality flags, or time. It encourages inspection of sources and limitations before treating a visual change as an astronomical result.

## Current scientific-validation status — version 0.10

The web explorer, saved-image sequences, review workflow, and evidence views are available. The science work remains exploratory. It has not produced a validated motion measurement for WISE 0855, a calibrated all-sky detection model, or a production-ready uncertainty estimate. The [20-item production-readiness checklist](../../docs/PRODUCTION_READINESS.md) tracks remaining work.

### Real-star and source-presence studies

**840 real-star attempts and 7,992 simulated source-presence attempts** were checked with calibration and validation separated. For 21 previously opened Gaia stars × 20 images × two ePSFs, **718 fits completed and 122 preparation failures** remain in the denominator. Across the same 359 completed pairs, interpolated ePSF lowers RMS from **0.934″ to 0.924″** but raises P90 from **0.876″ to 0.942″**. It was not selected as a new default; two stars without results remain visible as `0/20`.

The source-acceptance threshold **17.7038** was locked in Git after 1,998 null calibration cases and before a separate 5,994-attempt validation. It is a score, not sigma or detection probability.

| Validation on one previously opened geometry | Accepted /999 | One-sided 97.5% bound | Result |
|---|---:|---:|---|
| Plane · no target | 0 | False alarm ≤0.369% | Meets the simulation criterion |
| Quadratic · no target | 0 | False alarm ≤0.369% | Meets the simulation criterion |
| Plane · 600 µJy | 928 | Recovery ≥91.12% | Meets ≥80% |
| Quadratic · 600 µJy | 870 | Recovery ≥84.85% | Meets ≥80% |
| Plane · 300 µJy | 46 | Recovery ≥3.39% | Report only; most are missed |
| Quadratic · 300 µJy | 55 | Recovery ≥4.17% | Report only; most are missed |

**False alarms on the real sky and calibrated motion uncertainty remain unverified.** Simulations use one opened layout, Gaussian sources from a family different from the fitter, and conditional noise; the scorer uses observed VARIANCE, not oracle error. Independent QR audit recalculates all 7,992 scores from saved inputs but does not regenerate noise to validate the detector model.

[Results and limitations](../../docs/REFERENCE_PRESENCE_RESULTS.md) · [Reference-star protocol](../../docs/REFERENCE_STAR_PROTOCOL.md) · [Source-presence protocol](../../docs/SOURCE_PRESENCE_PROTOCOL.md) · [Real-star overview](../../web/data/reference-stars/overview.json) · [Simulation overview](../../web/data/source-presence/overview.json). Full audits with hashes are separate downloads (**14.2 MB / 71.1 MB gzip**); the web app loads only the two overviews when opening the section.

The earlier [neighbor-blend control](../../docs/NEIGHBOR_INTERVENTION_RESULTS.md) retains all 288 attempts, including a numerically supported draw with **16.8″** error. Do not drop that failure or select NNLS based only on favorable cases. Linked-flux and earlier science products remain unchanged.

**Science/production acceptance has not been met.** The [linked-flux study](../../docs/WISE_LINKED_RESULTS.md) retains all 28 fits and competing solutions; [continuous ePSF](../../docs/CONTINUOUS_EPSF_RESULTS.md) stabilizes the Hessian but does not lower RMS in all six cases; [sandwich covariance](../../docs/SANDWICH_RESULTS.md) still undercovers faint sources. Do not overwrite products 0.3–0.9 or describe them as unopened validation.

The [time model](../../docs/ASTROMETRIC_TIME_MODEL.md) checks 31 headers and GLS rank but is not connected to the source fit. [Independent spectra](../../docs/SPECTRAL_REFERENCE_RESULTS.md), [mask audit](../../docs/SCIENCE_MASK_AUDIT.md), [gain audit](../../docs/NATIVE_GAIN_BINDING.md), and [photometric-convention audit](../../docs/PHOTOMETRIC_CONVENTION_AUDIT.md) record units, UUIDs/hashes, and unverified assumptions. IRSA permits the newer ePSF on older QR2 data; residual/bias from the current renderer still needs separate measurement.

### Signal, blends, and pixel-phase controls

Design `9894074` was locked and pushed before **640 fit attempts**: 192 noiseless, 384 with Gaussian noise, and 64 null. Two star geometries and one already opened exposure were used; this is not a new sky field. The experiment compares original/corrected ePSF, two synthetic source families, four pixel phases, and specified/omitted blends. All 640 attempts completed and were independently audited; both journals are available in a **10.05 MB gzip** archive on request.

- **The noiseless measurement-fidelity gate failed: 70/128.** Of the passing cases, 64 came from the original matched-template control and only **6/64** from the independent Gaussian. All 128 passed numerical screening: a stable fit is not necessarily an accurate measurement.
- **Signal-preservation guard passed 64/64 pairs**, but it limits only relative degradation to ≤0.02 pixel and flux-ratio error to ≤0.02; it does not establish accuracy or improvement. **8/16 noisy groups** met the sample threshold ≥15/16. Paired noise conditions are not independent sky fields.
- An omitted companion can pull a fit toward the blended source despite passing numerical screens. The demo retains bias, flux, classifications as near simulated target/companion/other, and null controls. Null has no detection threshold and must not be called a false-alarm rate.

**The 252 reserved cells and 30 prospective fields remain unopened; the WISE 0855 measurement is unchanged.** Next, lock tests for pixel-area variation, template mismatch, and signal absorption by a blend. Consider opening new data only after a candidate passes absolute gates, signal-preservation controls, calibration, and independent PSF/error checks. Production goals for science, recovery/load/SLO, and accessibility remain open.

### Profile diagnostics and ePSF correction

Design `704e3ef` locked **14 stars × 2 opened images × 2 ePSFs × 2 weight sets** before sampling. **96/112 branches** have diagnostics; all **16 branches with missing inputs** from two stars remain in the denominator. The web view switches stars/images, shows four profile maps, and provides both profile/audit journals in a **3.89 MB gzip** archive without automatic download.

Independent WLS audit checked **2,760 grid nodes**, stencils at **192 fit points** across three finite-difference steps, and **480** saved objective functions. The two blocked cases retain alternative candidates with positive curvature at tested steps; this does not establish physical solutions or lower bias. **The old gate still fails; 252 reserved cells and 30 new fields remain unopened.**

The API adds upstream-error logging with enums and does not record URLs, exception messages, or credentials. The cause of two earlier 502 errors is unknown; there is no automatic retry. See [schema and limitations](../../docs/UPSTREAM_DIAGNOSTICS.md). A native signal/blend control follows the profile diagnostic; recovery, representative load, and SLO checks are also required. **The overall production goal is incomplete.**

The ePSF correction was learned from **145/168** calibration cells, retaining 22 without support and one numerical rejection. Source balancing lowered the maximum contribution from **50.70% to 12.87%**; coefficients were sealed before position fitting. Position fitting completed **146/168** cells, but **two stars have competing solutions 1.89″ and 3.38″ apart**. The gate blocked the model: **252 reserved cells remain unassessed**, including 56 primary cells. The correction has not been applied, and the old source-acceptance threshold was not transferred to the new PSF.

Baseline covariance retains **49,294 pixels** and shared Gaia errors: **357/420** cells have a response; 61 unsupported and two rejected cells remain visible. Heldout χ²/degrees of freedom is **407.431/238 ≈ 1.71**; error is not fully calibrated. Independent audit checked **357/357** native responses with QR and **1,314/1,314** final objectives for 146 new fits with BVLS at saved positions. This verifies arithmetic, not astronomical accuracy. Old registration, blended-source coordinates, weights, and some model uncertainties remain fixed; **30 prospective fields are unopened**.

The web separates learning → calibration gate → reserved assessment, and clearly reports deferred cases. Three overviews load only when opened; full audits (**2.48 / 3.06 / 2.72 MB gzip**) require separate download. Signal preservation and propagation of remaining error dependencies still need testing.

### Covariance-by-group model — version 0.9.0

Four combinations were compared on **five opened fields**, with identical pixels/alignment/gates. The selected model remains **plane background + fixed ePSF**: a quadratic background lowered pooled RMS from 3.110″ to 1.967″ but passed only 8/25 groups, not enough stability to replace baseline. All five leave-one-field-out checks retained the simpler choice.

Background selection/thresholds were locked at `1f1dae2`; covariance was learned from **192** separate calibration cases, splitting floor and scale learning and pooling small groups. Seal `8c7ad54` preceded **135 QR2 cutouts** in three new fields. S/N/background use observed features; truth was not used to choose groups. No calibrated covariance is returned outside the supported domain.

| 96 synthetic-source validation cases | Shared calibration | S/N/background conditional |
|---|---:|---:|
| Passed quality gate, common support | 69/96 | 69/96 |
| 68% ellipse coverage over 69 cases | 54/69 (78.3%) | 57/69 (82.6%) |
| Median ellipse area / raw | ×5.15 | ×2.23 |

**Overall gate failed.** Three of four bins are over-covered; by field, coverage is 100%, 83.9%, and 12.5%. The final field has only one background region with 8 correlated cases and errors remain 1.19–2.95″. The demo marks regions for human review on original images and separates synthetic sources from real astronomical objects. Gaia stars with 18/23 accepted cases lie outside the covariance domain and are labeled as extrapolation refusals.

**All 95/95 offline tests passed.** See [method, selection, results, and limitations](../../docs/ABLATION_VALIDATION.md). The WISE 0855 measurement is unchanged and motion remains unconfirmed. Next, diagnose bias/blending on opened data and add field-conditional calibration before locking an unseen set.

### Image background/ePSF covariance validation — version 0.8.0

The experiment tested quadratic background and flexible ePSF width, splitting by field/exposure into **development / calibration / validation**. Design was locked at `4e7a50c`; error floor was learned from **192** synthetic sources in three opened fields, then the calibrator was sealed at `d7d92dc` before fitting **122 QR2 cutouts** from three new fields. Validation includes 96 synthetic sources and 33 Gaia stars held out from alignment.

| RA/Dec field | Old → new synthetic RMS, paired | Passed gate /32 | Raw → calibrated 68% coverage |
|---|---:|---:|---:|
| 60° / −30° | 0.945 → 0.993″ | 32 | 24/32 → 32/32 |
| 150° / +45° | 1.368 → 1.418″ | 21 | 9/21 → 18/21 |
| 330° / +10° | 3.096 → 2.843″ | 14 | 0/14 → 10/14 |

**The default-replacement criteria were not met.** Pooled RMS fell from 2.079″ to 1.961″, but P90 rose and RMS rose in two fields. For 67/96 accepted cases, nominal 68% ellipse coverage rose from **49.3% to 89.6%**, with median area ×**3.65**; the new coverage is too high relative to the locked criterion. Calibration does not change centroids, confirm motion, or apply to WISE 0855.

The demo separates RMS/bias from coverage and ellipse expansion, switches between synthetic sources and Gaia stars, and records protocol/hash/limitations. **All 73/73 offline tests passed**; production MongoDB was checked separately by review QA.

See [methods, audit, results, and next steps](../../docs/COVARIANCE_VALIDATION.md). Next: ablate background/ePSF on opened data, choose the point model, and calibrate by S/N/background before a new external set.

### Quality gate and crowded-source study — version 0.7.0

The model adds CatWISE/Gaia neighbors, two Huber iterations for pixel outliers, and gates for residuals, source core, blend degeneracy, and centroid disagreement. Alignment rejects outliers with median/MAD and still requires at least four stars.

Code/catalog/split/rules were locked at **`330449c`** before evaluation on three new fields: **115 QR2 cutouts**, 58 spectrally matched exposures, 33 heldout stars, and 96 synthetic-source cases across two ePSF families.

| RA/Dec field | Old → new paired synthetic RMS before gate | Old → new passed /32 |
|---|---:|---:|
| 30° / −10° | 1.826 → 1.471″ | 24 → 20 |
| 180° / +20° | 1.989 → 1.991″ | 28 → 28 |
| 300° / −30° | 5.279 → 3.725″ | 8 → 8 |

**The default-replacement criteria were not met.** Synthetic-source point-estimate RMS fell in two fields, but real-star errors worsened in two; on the final field, jointly accepted RMS rose from 4.397″ to 5.282″. Only 8/56 accepted synthetic sources lie in nominal 68% ellipses, so the error budget is not calibrated.

In opened development fields, a 6.309″ Gaia outlier fell to 0.283″ but remained rejected; an RW Aur case with low residual but worse positional error was stopped by the model-disagreement gate. Demo shows rejection reasons and pre/post-gate counts. For the old WISE 0855 pair, UI checks only basic exported solver/bounds/χ²/S/N and states the full new gate was not run; the science measurement remains unchanged.

See [method, per-field/brightness results, limits, and reproduction](../../docs/QUALITY_VALIDATION.md). 59/59 offline tests passed; these validate software/data, not an astronomical detection.

### Earlier field benchmark — version 0.6.0

Downloaded **129 QR2 cutouts** across Barnard's Star, RW Aur, and R Draconis and checked **6,736 Gaia DR3 rows**. Code/dataset/split were locked at commit `8aa2536` before measurement. The WISE 0855 result was not changed.

| Broad-spectrum field | Heldout stars measured / attempted | Vector RMS vs Gaia | Synthetic fits valid / attempted | Valid synthetic RMS |
|---|---:|---:|---:|---:|
| Barnard | 11/11 | 1.921″ | 15/16 | 2.103″ |
| RW Aur | 11/11 | 0.182″ | 13/16 | 6.009″ |
| R Dra | Not measured | Only 3 alignment stars; ≥4 required | — | — |

Barnard has a Gaia outlier of **6.309″**. Barnard's target is **2.628″** from the prediction despite very high χ²r while the solver converged. Faint sources on the RW Aur background recover much worse than bright Gaia stars. Barnard strict/broad use the same image pairs and are not independent checks.

**There is no overall accuracy rate or blind-search precision/recall.** This is local fitting at known positions, with only 32 synthetic cases using the same ePSF family as the fitter, and the ellipse budget omits systematic terms. See [dataset, method, brightness-stratified results, and reproduction](../../docs/EXTERNAL_BENCHMARK.md).

## WISE 0855 demo and astrometry history

The [current WISE 0855 report](../../docs/WISE0855_GAIA.md) retains the same 20 broad-configuration exposures, expands cutouts from 0.12° to 0.32°, and cross-matches 675 Gaia DR3 sources. It selects 21 quality stars: 14 for alignment and 7 held out from fitting, propagating Gaia position/proper motion/parallax and covariance to observation dates.

For broad spectrum, the measured vector is **3.29″ ± 0.52″** over 163.5 days. Changing the star set changes it by **0.04″**; leave-one-star-out maximum change is **0.17″**; affine check changes it by **0.10″**. These are conditional model errors. The map is interactive and includes an error-budget table, injections at eight positions/two brightnesses, both pre-Gaia configurations, and three original single-image pairs. It supports wipe, side-by-side, difference, blink, zoom, highlights, and evidence table. Production review is stored in MongoDB per browser session, with local fallback, JSON export, and deletion by section.

**Motion signal, not confirmed.** Strict spectrum is primary: **3.06″ ± 0.99″**; broad spectrum is a sensitivity check and shares some images. Stationary synthetic sources of similar brightness on eight other real backgrounds have broad-configuration RMS error **2.72″**. Moving sources at half brightness fall inside the 68% ellipse in only **2/8** cases. The broad vector differs by **1.21″** from the external prediction. Gaia clarifies frame stability but does not resolve blending, ePSF, or spectral-response errors. No vision model has been trained.

The original single-image baseline, before coaddition, is documented in [WISE0855_DEMO.md](../../docs/WISE0855_DEMO.md). Epoch coadd/astrometry and the Gaia extension are documented in [WISE0855_COADD.md](../../docs/WISE0855_COADD.md) and [WISE0855_GAIA.md](../../docs/WISE0855_GAIA.md).

## Open the saved demo offline

The app uses small products checked into the repository; Python is needed to serve it, but no Node install or data download is required.

```sh
git clone https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex.git
cd nosleepclub_nasa_spherex
python scripts/serve_demo.py
```

Open **http://127.0.0.1:8766**. Change the port with `--port 8767`. The server serves only `web/` and binds to localhost. Files under `web/` can also be served by static hosting that supports JSON/PNG/FITS.

## Reproduce the science pipeline

Python 3.11 or later; a virtual environment is recommended. Versions in `requirements.txt` are those used on the development machine.

```sh
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
# Add API and operational-test dependencies for the full suite:
.venv\Scripts\python -m pip install -r web/requirements.txt -r requirements-ops.txt
# Only to regenerate science figures with Matplotlib:
.venv\Scripts\python -m pip install -r requirements-figures.txt
.venv\Scripts\python scripts/fetch_wise0855.py
.venv\Scripts\python scripts/fetch_wise0855.py --demo
.venv\Scripts\python scripts/build_demo.py
.venv\Scripts\python scripts/prepare_motion_data.py
.venv\Scripts\python scripts/motion_analysis.py
.venv\Scripts\python scripts/prepare_gaia_data.py
.venv\Scripts\python scripts/gaia_motion.py --publish
.venv\Scripts\python -m unittest discover -s tests -v
```

`--demo` downloads six selected cutouts and checks FITS; cache is in `data/raw/wise0855/target-centered/`. Run fetch without `--demo` to enumerate D6 observations in the initial query region; 43 observations have been checked. Downloads are cached and limited to three concurrent requests.

`prepare_motion_data.py` selects 31 cutouts in two epoch windows, downloads again around the target, and retrieves two version/hash-pinned official calibration files. Analysis uses 2 or 10 spectrally compatible pairs; it does not coadd all 31 images. `motion_analysis.py` runs 128 noise simulations per epoch/configuration, exports covariance/controls, and writes two web-product sets. Run `build_demo.py` before `motion_analysis.py` so the manifest contains both single-image and coadd products. Tests run offline; raw hashes are checked only when the cache is available.

`prepare_gaia_data.py` downloads wider cutouts for the same 20 exposures and queries Gaia DR3 via IRSA TAP, saving ADQL/URL/hash. `gaia_motion.py --publish` caches reference-star centroids, runs star-set swaps, 14 leave-one-out tests, affine fitting, 256 alignment bootstraps, and 32 injections per configuration, then adds Gaia products to the demo. Run steps in order to reproduce the complete manifest. 31 tests check committed products without downloading raw data.

Version 0.4.0 experiment: run `python -m scripts.joint_motion --configuration broad`, repeat with `strict`, then run `python -m scripts.summarize_joint`. It uses 192 synthetic-source recovery cases and 128 bootstraps per epoch/model. Multi-source fitting did not improve consistently; **it did not replace version 0.3.0 as default**. See RMS, fit failures, and paired comparisons in the accuracy report. The suite had 59 offline tests at the 0.7 checkpoint. CI and per-version reports record the latest outcomes; historical test counts are not current counts.

Version 0.6.0 benchmark: run `python -m scripts.prepare_benchmark_data --download`, then `python -m scripts.benchmark_accuracy`. Calibration from the earlier D6 workflow is required. Protocol is committed; scripts check hashes and refuse to replace locked inputs. Read the report before interpreting results or creating new validation data.

Version 0.7.0 quality study: run `python -m scripts.prepare_quality_data`, `python -m scripts.prepare_quality_data --new`, then `python -m scripts.quality_study` and `python -m scripts.build_quality_overview`. Use the committed protocol; do not run `--lock` over an opened set. Read the report to distinguish development, new evaluation, and covariance limitations.

## Documentation

- [Quality gate, crowded sources, and prespecified evaluation](../../docs/QUALITY_VALIDATION.md)
- [Three-field benchmark: data, accuracy, and failure cases](../../docs/EXTERNAL_BENCHMARK.md)
- [QR3, CatWISE, ePSF, and 30 prespecified fields](../../docs/QR3_CATWISE_VALIDATION.md)
- [Font, contrast, and layout readability](../../docs/READABILITY.md)
- [Interface design for new users](../../docs/UI_DESIGN.md)
- [Multi-source experiment 0.4.0](../../docs/ACCURACY_RESEARCH.md)
- [Gaia, vector stability, uncertainty, and next milestone](../../docs/WISE0855_GAIA.md)
- [Gaia research and importable Zotero bibliography](../../docs/GAIA_RESEARCH.md)
- [Pre-Gaia image coadds](../../docs/WISE0855_COADD.md)
- [Initial three-pair single-image baseline](../../docs/WISE0855_DEMO.md)
- [Vision-model analysis and review workflow](../../docs/DEEP_RESEARCH_VISION.md)
- [Challenge summary](../../docs/CHALLENGE.md)
- [Roadmap](../../docs/ROADMAP.md)
- [Contributing guide](../../CONTRIBUTING.md)

## Data and licensing

Source data: SPHEREx QR2 from NASA/IPAC IRSA, DOI [10.26131/IRSA652](https://doi.org/10.26131/IRSA652). PNG/FITS under `web/data/` are processed demo products, not official IRSA science products. Manifests retain cutout URL, SHA-256, observation ID, and pipeline version.

Do not commit tokens or large raw FITS datasets. Original project code and accompanying original documentation are licensed under [MIT](../../LICENSE), per the repository owner's choice on 2026-10-31. Data, fonts, Canva illustrations, and dependencies retain their own terms in [NOTICE](../../NOTICE.md).

Be Vietnam Pro is distributed under SIL Open Font License 1.1; its license and SHA-256 are in `web/assets/fonts/`. Run `python scripts/fetch_web_fonts.py` only if the font must be retrieved again from the official source. The repository clone already includes the font for local web use.

## Data hosting and web operations

The 213 public demo products (212.2 MB raw) are served from MongoDB through a [hash-verifying reader](../../docs/MONGODB_PUBLIC_DATA.md). New static output retains only UI, fonts, and design images; it does not bundle `web/data/`. One cluster currently uses about 170 MB logical data; a second cluster is not needed. The repository retains data for reproducibility.

The UI adds clear A/B selection, IRSA image-error recovery, same-tab drafts, and JSON export including WISE drafts; private notes are not made public automatically. Large audit files are downloaded in chunks and saved only after SHA-256 matches. The local server still uses files directly and needs no Mongo credential.

Older deployments remain available for rollback. Reducing new output does not remove source checkouts from Git or reduce all Vercel bandwidth costs; M0 has not passed long-duration load/failover tests. See [workflow and limits](../../docs/MONGODB_PUBLIC_DATA.md).

Cutover receipts, errors/rollback records, and public verification are retained in [MONGODB_PUBLIC_DATA_RELEASE.md](../../docs/MONGODB_PUBLIC_DATA_RELEASE.md).
