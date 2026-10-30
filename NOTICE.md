# Sources and rights

This repository combines original project code, third-party dependencies and
scientific products. Public GitHub visibility alone is not a blanket license for
every file. The proposed code license is under owner review in
[CODE_LICENSE_PROPOSAL.md](docs/CODE_LICENSE_PROPOSAL.md); no new source-code
license has been applied by that draft.

| Material | Source and current record | Reuse boundary |
|---|---|---|
| Original project code | Git history and scientific source hashes | Owner code-license decision pending; do not infer an open-source grant from visibility |
| Be Vietnam Pro fonts | `web/assets/fonts/provenance.json`, local `OFL.txt` | SIL Open Font License, retained with the font files |
| Canva illustrations | `web/assets/provenance.json`, media IDs and URLs | Artistic illustrations only. Account/content-specific rights are not established by the provenance JSON; no MIT or public-domain grant is asserted |
| SPHEREx cutouts and calibration products | NASA / Caltech / IPAC IRSA; source URLs, versions and hashes in each manifest | Preserve mission/archive credit and processing qualifications; project code licensing does not replace upstream terms |
| Gaia DR3 | ESA Gaia / DPAC via IRSA; query and release in manifests | Preserve release, source IDs, query and provenance; catalog predictions are not new measurements |
| CatWISE 2020 | NASA / IPAC IRSA; catalog and correction-table URLs in protocols | Retain catalog version and correction qualifications |
| SPIFF reference inventory | Jonathan Gagné et al., DOI `10.5281/zenodo.19051216`, QR2-2026-04-24 | Publisher metadata: CC-BY-4.0. Credit authors/version/DOI, identify modifications; downloaded archives stay in ignored raw cache |
| JWST/NIRSpec external references | NASA / ESA / CSA / STScI MAST, program 1230; exact G395M/PRISM products, associations, calibration contexts, URLs and hashes in `web/data/external/wise0855-sed-reference.json` and `wise0855-prism-reference.json` | Raw spectra stay in ignored cache. Retrieved pipeline products are distinct from Luhman et al. author extractions and their Spitzer normalization; no blanket code-license grant is asserted for external data |
| SPHEREx laboratory spectral response | Howard Hui / SPHEREx calibration delivery R7, July 2026; archive and selected CSV hashes in `web/data/spectral-response/` | Preserve delivery, source and response qualifications. Raw tar is not redistributed in Git; signed laboratory measurements are not a certified nonnegative photon model |
| Python and service dependencies | `requirements.txt`, `web/requirements.txt`, pinned CI actions and container digest | Separate upstream licenses apply; packages are not relicensed by this project |

Scientific figures, masks, hashes and uncertainty labels must remain attached to
derived results. The web's Canva images are never presented as FITS observations.
The project is an independent Space Apps entry; it does not imply NASA, ESA,
SpaceX, Canva or dataset-author endorsement. No NASA or SpaceX logo is licensed
through this file.

Primary references: [GitHub licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository),
[NASA media guidance](https://www.nasa.gov/nasa-brand-center/images-and-media/),
[Canva content agreement](https://www.canva.com/policies/content-license-agreement/),
[SPIFF dataset](https://zenodo.org/records/19051216).

This is a source/rights inventory, not proof of a license entitlement for every
external asset. Confirm account-specific Canva rights before claiming unrestricted
redistribution of the illustration files.
