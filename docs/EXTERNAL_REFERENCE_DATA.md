# New Reference Data for Spectra and Validation

A small package was downloaded from **SPIFF QR2-2026-04-24**, DOI [10.5281/zenodo.19051216](https://zenodo.org/records/19051216), by Jonathan Gagné et al. The metadata API reports a **CC-BY-4.0** license; the [paper](https://arxiv.org/abs/2604.22012) describes the spectral-extraction method. SPIFF code has a separate license; this project has not installed or run it.

## Retrieved and checked

`scripts/fetch_spiff_reference.py` downloads only the README, checksum manifest, catalog table, and hybrid spectral template: **872,724 bytes total**. It does not download the 6.7 GB package or source-specific images/spectra. The downloader checks the sizes and MD5 values published by Zenodo, then records independent SHA-256 hashes for each file. Raw files are in `data/raw/external/spiff/`, which Git ignores. The [public receipt](../web/data/external/spiff-reference.json) records URLs, version, license, hashes, and ZIP inventory; downloaded content is neither extracted nor executed.

The README for this version reports 6,003 high-quality spectra and 47 standard subtypes in the library. These are author-reported counts, not a number of trials run on the website. Templates from M8 to Y1 and the gravity classes do not cover very cold dwarfs such as WISE 0855. A class or subtype label does not establish positional accuracy.

```powershell
.venv/Scripts/python.exe -m scripts.fetch_spiff_reference
```

Reruns reject a different checksum/version/license or overwriting a different cache. The publisher may change record metadata; if the metadata hash differs, retain the old receipt and review a new version instead of silently updating it.

## Using the data to improve the tool

1. Use the template as a development set to check spectral response: integrate the SED with detector-position response, retaining normalization, units, and within-band variation. A single CWAVE/CBAND value only approximates response shape; it is not enough to establish that two images measure the same spectrum.
2. Use the catalog to build a cohort of red sources with motion known from external measurements. Lock the list, epochs, truth quality, splits by field/exposure/source, and criteria before measuring images from a new cohort.
3. Use an independent pipeline such as SPIFF to identify disagreements. Another pipeline's results still have systematics and do not automatically become truth; retain each pipeline's PSF/centroid/background method and input data.

No new accuracy test has been run with this package. A template derived from SPHEREx may share pixels or sources with validation. Do not use a source's template as a prior and then evaluate that same source/exposure as independent data. Do not relabel fields already opened as holdouts.

## Two methodological points to preserve

[IRSA documentation](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html) states that official forced photometry holds source positions fixed and fits only flux; it does not certify the accuracy of a free motion fit. The [data model for the authors' tractorjax-spherex project](https://tractorjax-spherex.readthedocs.io/en/latest/data_model.html) distinguishes the QR2 optical PSF and the QR3 ePSF, which already includes pixel response; integrating pixel response again may create bias. These sources support cross-check design; they do not prove that all biases in the current pipeline have been corrected.
