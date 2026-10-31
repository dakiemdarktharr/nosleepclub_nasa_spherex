# Sources and rights

This repository combines original project code, third-party dependencies and
scientific products. Original project code and its original accompanying
documentation are licensed under the [MIT License](LICENSE), as approved by
the repository owner on 2026-10-31. External data, fonts, illustrations and
dependencies retain their separate rights below. The decision and original
proposal are recorded in [CODE_LICENSE_PROPOSAL.md](docs/CODE_LICENSE_PROPOSAL.md).

| Material | Source and current record | Reuse boundary |
|---|---|---|
| Original project code and its original accompanying documentation | Git history, scientific source hashes and [LICENSE](LICENSE) | MIT; retain its copyright and permission notice. This grant does not relicense external material listed below |
| Be Vietnam Pro fonts | `web/assets/fonts/provenance.json`, local `OFL.txt` | SIL Open Font License, retained with the font files |
| DejaVu glyphs in scientific SVG/PNG figures | Matplotlib 3.11.2 bundled DejaVu Sans; font hashes in `web/data/linked-flux/figures.json` and `web/data/profile-landscape/figure-environment.json` | Upstream Bitstream/DejaVu/Arev notices retained in [DEJAVU-LICENSE.txt](docs/licenses/DEJAVU-LICENSE.txt); the code's MIT grant does not replace these font terms |
| Profile-landscape derived costs, diagnostics and figures | Frozen `704e3ef` protocol; complete profile and independent-audit journals in `web/data/profile-landscape/records.json.gz`, linked source/input hashes and four PNG hashes in its overview | Derived, conditional scientific products from the SPHEREx/Gaia materials below; retain source and model qualifications. The original-code MIT grant does not establish a new blanket license for upstream data |
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
