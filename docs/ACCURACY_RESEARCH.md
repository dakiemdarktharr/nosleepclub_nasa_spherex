# Reducing WISE 0855 Error — Research and Experiment 0.4.0

Sources checked on 30 October 2026. Conclusion: a multi-source fit on native pixels and an A/B experiment were added, but **a stable improvement sufficient to replace Gaia version 0.3.0 has not been demonstrated**. Do not lower the reported error by dropping systematic terms or choosing a configuration closer to the external prediction.

## New evidence

Gaia lists a source at G≈16.31, about 8.67″ from the target anchor at MJD 61000. This is a propagated optical position; it does not establish the source's brightness or photocenter at 4.7 µm. The new model adds Gaia ePSFs within 11 sky-grid pixels of each fit region. Neighbor positions are fixed, with a separate free amplitude for each exposure and a shared plane background. SVD eliminates the linear parameters; only the target centroid is optimized nonlinearly, without using a predicted vector as a prior. Independent synthetic tests check centroid recovery with overlapping sources and duplicate columns in the nuisance matrix.

The A/B models use the same original stamps, quality flags, noise maps, ePSF, and multi-start solver. Noise bootstrap: 128 draws per epoch/model/configuration. For the real source with a broad spectrum, the single-source model gives vector (east, north) = (−3.268, +0.431)″; the multi-source model gives (−3.035, +0.107)″, with length 3.037″. **Projected noise σ increases from 0.495″ to 0.701″.** These values exclude frame, ePSF, and neighbor-position errors, so they are not directly comparable with the previous Gaia version's total σ of 0.52″.

Twelve new positions were recorded in `web/data/joint/protocol.json` before the run, in addition to the previous version's eight regions. Each region has two brightnesses and two injected vectors: `[0, 0]` and `[0.6, 0.05]` pixels. This gives 48 trials per method/configuration and 192 recoveries total. No parameters were selected using these regions' results. Because the results have now been viewed, these regions must be treated as development data in future work.

| Spectrum | Brightness | Single-source RMS | Multi-source RMS | Valid single / multi |
|---|---:|---:|---:|---:|
| Broad | 0.5× | 1.699″ | 1.572″ | 22/24 · 24/24 |
| Broad | 1× | 1.016″ | 1.336″ | 24/24 · 24/24 |
| Narrow | 0.5× | 2.128″ | 2.572″ | 24/24 · 23/24 |
| Narrow | 1× | 1.353″ | 1.137″ | 24/24 · 22/24 |

RMS in the table includes only successful fits that did not hit a boundary; do not ignore the valid-count column. Injections on the same region share background and noise, and both spectral configurations share exposures. No source shot noise was added; injection and fitting use the same ePSF family. This is a conditional diagnostic, not completeness, false-positive rate, or independent validation of systematic error.

Paired comparisons **restricted to trials valid in both methods** partly address denominator differences: broad 0.5× has RMS 1.699″ → 1.630″ (22 pairs), a 4.06% improvement; broad 1× is 31.49% worse. A post hoc bootstrap of 2,000 draws resampled by **spatial region**, not treating each injection as independent, gives approximate 95% intervals for percent improvement of [0.89, 7.64] and [−48.96, 6.38]. Narrow 0.5× is 26.65% worse; narrow 1× is 2.99% better on 22 pairs, but has two additional failures/boundary hits. With only 11–12 regions, conditional samples, and multiple comparisons, these intervals are not statistical guarantees or a confirmatory detection test.

Products: [broad.json](../web/data/joint/broad.json), [strict.json](../web/data/joint/strict.json), [summary.json](../web/data/joint/summary.json). Data, FITS, and hashes from version 0.3.0 remain unchanged. Each new result carries hashes for source code, catalog, and its parent Gaia analysis.

## Background research and decisions

1. **Model multi-source scenes before ranking with AI.** [IRSA Spectrophotometry documentation](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html) describes fitting companions jointly to reduce blending. The official tool holds positions fixed and fits flux only; centroid optimization in the demo is a separate implementation not validated by IRSA. A prototype has been implemented; it is not enabled by default because the A/B results do not meet the criteria.

2. **Deeper catalogs involve trade-offs.** [Huai et al., *Simulating Spectral Confusion in SPHEREx Photometry and Redshifts*](https://arxiv.org/abs/2510.01410) simulates both confusion from sources absent from the catalog and blending among known sources. Catalog depth affects both; adding every source is not automatically optimal. The paper focuses mainly on photometry/redshift and does not provide a centroid-error guarantee for WISE 0855. CoChat found the journal version, DOI [10.3847/1538-4357/ae472b](https://doi.org/10.3847/1538-4357/ae472b); its content was checked against the authors' arXiv version. An initial broad CoChat search returned irrelevant results; the paper was retained only after its exact title was verified.

3. **The ePSF must match the pixel and detector position.** [Anderson & King 2000](https://arxiv.org/abs/astro-ph/0006325) explains that the ePSF integrates pixel response and varies spatially. The HST accuracy levels in the paper do not transfer to SPHEREx. The [official ePSF notebook](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/) shows how to retrieve SPHEREx calibration. The demo currently selects the nearest zone; zone interpolation, exposure-dependent ePSF perturbations, and subpixel-dependence checks still need evaluation and are not claimed as completed.

4. **The noise map may depend on the data being fit.** The authors' [tractorjax-spherex documentation: Backgrounds & systematics](https://spherex-photometry.readthedocs.io/en/latest/backgrounds_systematics.html) notes that VARIANCE depends on observed count rate and may cause weight-noise bias for faint sources. This is a hypothesis to check against real product/read-noise behavior. Variance has not been replaced with a constant or a custom formula. A CWAVE-based background may be useful, but the He I 1.083 µm example is not direct evidence for detector D6 at 4.7 µm. Lock the background model on development regions and keep validation regions unopened.

5. **QR3 is available for calibration checks.** The [IRSA mission page](https://irsa.ipac.caltech.edu/Missions/spherex.html) and [official Data Products documentation](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/) confirm that QR3 release began in September 2026. This is a priority before attempting to optimize QR2 at extreme precision. It has not been confirmed that QR3 contains the required WISE 0855 exposures; no data have been replaced or versions combined. Query footprints, pin calibration/hash, and compare QR2/QR3 for the same exposure before adding an epoch.

6. **Separate precision from accuracy.** Stable Gaia frames do not eliminate bias from photocenter, blending, or the spectrum of a very red brown dwarf. The 0.52″ value is the previous version's conditional budget, while some injection errors are larger. A model that increases σ may correctly reflect information lost to blending; do not treat that increase as an error to force down.

## Next milestone and acceptance criteria

Prioritize a QR3 check for the same exposures; cross-reference suitable infrared catalogs such as CatWISE/AllWISE/Legacy Survey with clear epochs and proper motions; use catalogs to select infrared-supported nuisance sources. Then evaluate ePSF interpolation and background/variance models on already opened regions. Do not select a model based on proximity to the Luhman vector.

Lock the pipeline, source-exclusion criteria, and spectral choice before opening **at least 30 new regions** sufficiently far from old stamps. Report error/boundary failures, vector bias, RMSE, paired comparisons, and coverage by brightness/source density. Change the default only if RMSE decreases at both 0.5× and 1×, failures do not increase, and coverage does not worsen; region-level bootstrap must support the conclusion, not just point estimates. Check ePSF mismatch when injection and fit models differ, add source noise with supported units/calibration, and assess correlated instrument noise.

After the position measurement is stable, add a third epoch and fit motion + parallax with an appropriate baseline; two epochs alone do not solve these parameters. Use a vision model to rank scenes and hand them to a reviewer after physical gates, with train/test splits by sky region; do not use an LLM to replace covariance.

## Reproduction

```powershell
.\.venv\Scripts\python.exe -m scripts.joint_motion --configuration broad
.\.venv\Scripts\python.exe -m scripts.joint_motion --configuration strict
.\.venv\Scripts\python.exe -m scripts.summarize_joint
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The first two commands require the broad cutout cache and Gaia centroids from the preceding milestone. The summary/test commands read the committed small products.
