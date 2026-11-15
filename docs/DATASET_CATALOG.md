# Dataset Catalog for Planet X and SPHEREx

Checked on **14 November 2026**. [Open the 3D sky map](sky-atlas.html) or [download the JSON catalog](data/sky-datasets.json). The catalog contains **38 datasets, releases, or services** relevant to time-series imaging, motion cross-matching, variability, and spectra, plus a sample footprint layer retrieved directly from IRSA. Links point to data archives, query tools, or documentation published by the responsible organization or authors. This survey prioritizes IRSA, ESA, MAST, ESO, CADC, and survey teams. Local reference data have separate receipts. This step retrieves only small IRSA metadata responses.

## Challenge requirements

The challenge asks for a public website that accepts **RA and Dec** and plays **SPHEREx images of the same sky region over time**. The five targets are Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae, and R Draconis. The challenge lists WISE 0855 at **08h55m10.831s, −07°14′42.53″**, or **133.79512917°, −7.24514722°**. This is the challenge's reference coordinate. The repository also contains a predicted query center near the image epoch. [Challenge notes](CHALLENGE.md) · [Repository query-field centers](../web/data/challenge-targets.json) · [Official Details page](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details)

The Resources tab was opened directly on 14 November 2026 and showed eight entries. Four NASA resources are IRSA, the SPHEREx notebook, WiseView, and Gaia DR3. Four Canadian partner resources are the NEOSSat overview, CADC, a NEOSSat tutorial, and the NEOSSat dataset. Public Space Apps Navigator guidance recommends querying IRSA by coordinates, checking times and bands, aligning WCS, and playing images in time order. [Official Resources](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=resources) · [Official challenge cross-check](CHALLENGE_LIVE_REVIEW.md) · [NASA Space Apps discussion](https://github.com/nasa/spaceapps/discussions/1847)

## Direct SPHEREx data

| Dataset | Coverage | Access and use |
|---|---|---|
| **DR1 Spectral Images**, DOI `10.26131/IRSA678` | Broad sky coverage in Survey 1 and 2. Query separately for coverage by epoch, detector, and wavelength. | FITS spectral images for each observation. Query `spherex_dr1` through SIA2. [IRSA DR1](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html) |
| **QR3 Spectral Images** | Broad Survey 3 and 4 coverage, released over time. | Query `spherex_qr3`. IRSA documents using DR1 and QR3 together. Some QR3 files are reprocessed; compare IDs and processing dates. [Data releases](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases/) |
| **Deep Survey** | Two regions near the north and south ecliptic poles. The southern region is offset from the pole to reduce foreground contamination. | Query `spherex_dr1_deep` and `spherex_qr3_deep`. Check official IRSA MOCs and each image's `s_region`. [Survey design](https://spherex.caltech.edu/page/survey) · [IRSA MOC](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/searching.html) |
| **DR1 All-Sky Cube**, DOI `10.26131/IRSA679` | All sky, 102 nominal spectral channels. | Query `spherex_dr1_cube`. The cube is assembled from DR1 images for spectral lookup and background maps. Axis 3 is wavelength. [IRSA DR1](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html) |
| **QR2 Spectral Images** | Historical images still needed to reproduce repository measurements. | After DR1/QR3, IRSA discontinued QR2 SIA2 queries and retains direct downloads until **February 2027**. Record URI, version, and hash for each file needed for reproduction. [Data releases](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases/) · [Directory conventions](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/) |
| **Mosaic / Spectrophotometry** | User-requested regions when input images are available. | Create a coadded cube or spectrum from multiple images. IRSA spectrophotometry holds source position fixed when fitting flux. [Mosaics and spectral tools](https://irsa.ipac.caltech.edu/applications/spherex/) · [Spectrophotometry](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html) |
| **SPIFF QR2-2026-04-24** | M/L/T/Y dwarf targets in the spectral library. | Community spectral library and templates useful for developing extraction checks. Because the spectra use SPHEREx data, sources or exposures may overlap with a test set. [Zenodo](https://zenodo.org/records/19051216) · [Project receipt](EXTERNAL_REFERENCE_DATA.md) |

DR1 was released on **12 November 2026**. For time-series images, query `POS`, collection, and, if needed, `TIME` or `BAND` through SIA2; read each row's `s_region`; retrieve FITS cutouts; then align them on a common sky grid. Read WCS-WAVE at the target position to determine actual wavelength and apply FLAGS, VARIANCE, and PSF according to the measurement. Matching detector or band names alone does not establish equivalent spectral response at two pixels. [Release version](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/overview.html) · [Collections and FITS cutouts](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/) · [HDU descriptions](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/visualization.html)

### Direct queries at the five test fields

The following queries retrieve only SIA2 metadata in a **0.05° radius**, capped at **one row**, at repository field centers. `OVERFLOW` means results exist but were capped. A nonempty cell confirms at least one row intersected the cone at query time. To determine whether images form a suitable pair, check epoch count, timestamps, point footprint, wavelength, and valid pixels. `OK` with zero rows applies only to the specific collection, cone, and snapshot. SHA-256 values are calculated from VOTable response bytes. [SIA2 parameter definitions](https://irsa.ipac.caltech.edu/ibe/sia.html)

| Field center | DR1 | QR3 |
|---|---|---|
| Barnard's Star | [OVERFLOW · 1 row](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=CIRCLE+269.44626689+4.76822222+0.05&MAXREC=1) | [OVERFLOW · 1 row](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr3&POS=CIRCLE+269.44626689+4.76822222+0.05&MAXREC=1) |
| ε Indi B | [OVERFLOW · 1 row](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=CIRCLE+331.04583333+-56.78333333+0.05&MAXREC=1) | [OVERFLOW · 1 row](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr3&POS=CIRCLE+331.04583333+-56.78333333+0.05&MAXREC=1) |
| WISE 0855 | [OVERFLOW · 1 row](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=CIRCLE+133.76012139+-7.24212794+0.05&MAXREC=1) | [OK · 0 rows](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr3&POS=CIRCLE+133.76012139+-7.24212794+0.05&MAXREC=1) |
| RW Aurigae | [OVERFLOW · 1 row](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=CIRCLE+76.95652603+30.40143817+0.05&MAXREC=1) | [OVERFLOW · 1 row](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr3&POS=CIRCLE+76.95652603+30.40143817+0.05&MAXREC=1) |
| R Draconis | [OVERFLOW · 1 row](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=CIRCLE+248.16761083+66.75497942+0.05&MAXREC=1) | [OVERFLOW · 1 row](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr3&POS=CIRCLE+248.16761083+66.75497942+0.05&MAXREC=1) |

<details>
<summary>Query-response SHA-256</summary>

```text
barnard DR1 5bd4194e5324263c810ac976e99847c36664df37b17fd6b7dad33397346dc512
barnard QR3 a33d909b448f3340479c043b8f5e775c9d301c82f0df4cf9bfa8f5d80fa52ba5
epsilon DR1 58dd9e95ddb3bee05c72e629e21e3ed0ff49e553560aebfbafb14384fe3e87d1
epsilon QR3 c2816ca7f1d2daafbfdc7d2dfcb7112ed0cb8dfc1c10ca80cc3360434d8b7a41
wise0855 DR1 941460cdf510574fb3dfecba60b460f023269360514bd834728ed66cbc36638f
wise0855 QR3 fa538a0a6daf723452a8645c90efb86c1d6ddc68903b280bed9fb13ca1cdd3bd
rwaur DR1 acab7dfce19b5dca20cc06663f7cd00d56ba5bf99828a69d683d353afdf7836d
rwaur QR3 65201ce3b796198dec50cc5a468287220caf39a7159464daa9dd42073ed3909e
rdra DR1 b19a4d7a9d3e98d05ad84f0982b40791a8a53eafda41768d30fa345cc0e1aed7
rdra QR3 cdef3bac6db225de2c7c987192fa7f6efc817042e98d51b158405f7f6ec8f782
```

</details>

The **SPHEREx DR1 / QR3 · Sample Footprints** layer draws nine polygons from nine returned rows in the table. Vertices come from original `s_region` values (STC-S `POLYGON ICRS`, degrees). The JSON retains each `s_region` string, image ID, detector, MJD, detector band limits in meters, FITS URL, query, metadata SHA-256, and retrieval time. The geometry represents the image footprint in metadata. A cone query may return an image that intersects only the cone boundary. [Catalog and metadata](data/sky-datasets.json)

## Comparison datasets and reference layers

| Need | Sources and scope |
|---|---|
| **Earlier infrared epochs than SPHEREx** | **WISE/NEOWISE Single Exposure** provides images and per-exposure source tables. **unWISE time-resolved** provides W1/W2 images coadded by scan and epoch catalogs. These products share WISE/NEOWISE images. **VarWISE** selects variable sources and links back to individual exposure measurements. [WISE/NEOWISE](https://irsa.ipac.caltech.edu/Missions/wise.html) · [unWISE](https://irsa.ipac.caltech.edu/data/WISE/unWISE/overview.html) · [VarWISE](https://irsa.ipac.caltech.edu/data/WISE/VarWISE/overview.html) |
| **Reference stars and nearby sources** | **Gaia DR3** provides positions, proper motions, parallaxes, and quality parameters. **CatWISE2020** supports red-source lookup in W1/W2. **AllWISE**, **unWISE full-depth**, and **2MASS Atlas/PSC** provide all-sky reference images/catalogs. **2MASS 6X** is deeper in selected fields. [Gaia DR3](https://gea.esac.esa.int/archive/documentation/GDR3/index.html) · [CatWISE2020](https://irsa.ipac.caltech.edu/data/WISE/CatWISE/gator_docs/catwise_colDescriptions.html) · [AllWISE](https://irsa.ipac.caltech.edu/Missions/wise.html) · [unWISE](https://catalog.unwise.me/) · [2MASS](https://irsa.ipac.caltech.edu/data/2MASS/docs/releases/allsky/) · [2MASS 6X](https://irsa.ipac.caltech.edu/data/2MASS/docs/releases/allsky/doc/seca3_1.html) |
| **Optical epoch images and historical backgrounds** | **Pan-STARRS1 DR2** mainly covers declinations north of −30° and has stacks and individual warp images. **SkyMapper DR4** has all six bands down to about Dec +16°, with partial coverage to +28° in some fields. **DSS** combines all-sky photographic plates from multiple years and bands. **DESI Legacy Imaging Surveys** contains separated deep fields. [PS1 DR2](https://catalogs.mast.stsci.edu/panstarrs/) · [SkyMapper DR4](https://skymapper.anu.edu.au/data-release/dr4/) · [DSS](https://archive.stsci.edu/dss/) · [DESI Legacy Imaging](https://datalab.noirlab.edu/data/legacy-surveys) |
| **RW Aur or R Dra light curves** | **ZTF**, **PTF/iPTF**, **ASAS-SN**, **ATLAS**, **AAVSO**, and **TESS** provide time series with their own depth, saturation, and timing limits. Query each target before integration. Variability in one band needs band-specific evidence. [ZTF](https://irsa.ipac.caltech.edu/Missions/ztf.html) · [PTF](https://irsa.ipac.caltech.edu/Missions/ptf.html) · [ASAS-SN](https://www.astronomy.ohio-state.edu/asassn/public/) · [ATLAS](https://fallingstar-data.com/forcedphot/) · [AAVSO](https://aavso.org/search-and-download-data/) · [TESS](https://archive.stsci.edu/missions-and-data/tess) |
| **Deep images, spectra, and crowded fields** | **Spitzer Heritage/SEIP**, **JWST/NIRSpec WISE 0855**, and **HST** by program. **GLIMPSE I/II** follows the Milky Way plane, **VISTA VVV/VIRAC2** covers the bulge and southern disk, and **VISTA VHS** covers much of the southern sky. **Euclid DR1-Foundation** was released on 12 November 2026 and covers wide/deep survey fields; check actual tile footprints. [Spitzer](https://irsa.ipac.caltech.edu/Missions/spitzer.html) · [JWST WISE 0855 in this repository](WISE0855_PRISM.md) · [HST](https://archive.stsci.edu/missions-and-data/hst) · [GLIMPSE](https://irsa.ipac.caltech.edu/data/SPITZER/GLIMPSE/overview.html) · [VIRAC2](https://www.eso.org/rm/api/v1/public/releaseDescriptions/227) · [VISTA](https://www.eso.org/sci/observing/PublicSurveys/sciencePublicSurveys.html) · [Euclid](https://irsa.ipac.caltech.edu/Missions/euclid.html) |
| **Long-wavelength dust background** | **AKARI IRC/FIS** and **IRAS/IRIS** are near-all-sky surveys with different resolution and wavelengths from SPHEREx. They can show broad-area emission backgrounds. [AKARI](https://irsa.ipac.caltech.edu/data/AKARI/overview.html) · [IRIS](https://irsa.ipac.caltech.edu/data/IRIS/overview.html) |
| **Solar-system object candidates** | **NEOSSat** provides images and observing fields by program. **MPC** stores reported astrometry. **JPL Horizons/SB Identification** predicts based on orbit, observer location, and time. [NEOSSat/CADC](https://cadcftp.cadc.hia.nrc-cnrc.gc.ca/en/neossat/) · [MPC Data Services](https://data.minorplanetcenter.net/) · [Horizons](https://ssd-api.jpl.nasa.gov/doc/horizons.html) · [SB Identification](https://ssd-api.jpl.nasa.gov/doc/sb_ident.html) |

## Reading the celestial sphere and reproducing results

- All map locations are **directions on the celestial sphere**. Display size is angular size; distance from Earth is not encoded. All-sky coverage may represent survey design or merged products and can contain missing regions by band or epoch.
- Pan-STARRS, SkyMapper, GLIMPSE, and VVV/VIRAC2 boxes show published limits in degrees. The SPHEREx Deep Survey point near a pole approximates the J2000 ecliptic-pole direction. Use IRSA MOCs to inspect deep-field shapes. The JWST point shows the WISE 0855 target direction from the challenge.
- For releases with disjoint footprints such as Euclid and TESS, the catalog links to a map browser or tile/sector archive. MOCs and `s_region` provide geometry for adding these to the sphere. [Aladin MOC guide](https://aladin.cds.unistra.fr/java/FAQ.htx)
- Images used in analysis should retain accession/URL, release and calibration, time/time scale, WCS, units, mask, uncertainty, and SHA-256 of the image file itself. Query hashes above refer only to metadata. The repository stores raw FITS in `data/raw/` and demo products with provenance in `web/data/`. [Current manifest](../web/data/manifest.json) · [Current metadata contract](OBSERVATION_API_CONTRACT.md)

**Proposed next step.** Add DR1/QR3 to the image-search flow and play at least three compatible real frames over time for one target. Check each frame's coverage, wavelength, WCS alignment, and metadata. Then check the other four targets and show clearly when only two frames support A/B comparison or suitable images are unavailable. [Acceptance criteria](OVERHAUL_DISCOVERY.md#proposed-next-milestone)
