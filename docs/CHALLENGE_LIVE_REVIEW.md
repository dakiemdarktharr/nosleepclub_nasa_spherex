# Planet X and SPHEREx | Official Challenge Review

The **Details** and **Resources** tabs on the NASA Space Apps portal were opened on **14 November 2026**. The challenge is rated **Advanced** and tagged Astrophysics, Planets & Moons, and Software. NASA Space Apps 2026 takes place on 14–15 November. The event portal lists the submission deadline as 23:59 local time on 15 November. [Details](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details) · [Resources](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=resources) · [Event schedule](https://www.spaceappschallenge.org/2026/)

## Challenge focus

The public web tool accepts RA and Dec for a sky region and plays **a time sequence of SPHEREx images of that same region** to help viewers notice moving points of light and other changes. The challenge gives Pluto’s discovery through image comparison as an example and notes the contribution of volunteer observers. SPHEREx surveys the entire sky about every six months across 102 near-infrared bands. Coverage and available wavelengths at each time depend on the field and data release. [Details](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details) · [IRSA](https://irsa.ipac.caltech.edu/Missions/spherex.html)

| Required test target | How to check it in the product |
| --- | --- |
| Barnard’s Star | Open the field, inspect available times and bands, and try comparing a pair of images. |
| Epsilon Indi B | Play the verified three-frame DR1 D6 sequence. Inspect the UTC timestamp and FITS file for each frame. |
| WISE 0855 | Enter the challenge coordinates: RA `08h55m10.831s`, Dec `−7d14m42.53s`. The app’s example target center is separately propagated to the observation epoch. |
| RW Aurigae | Check image availability and whether variable-star observations can be compared at compatible times and wavelengths. |
| R Draconis | Check images at each time and the status shown when no image in a matching band is available. |

For each case, record the query, release, detector, frame count, and loading status. Two-image comparison supports close inspection of a pair of epochs; the sequence player addresses the time-viewing requirement. The three-frame Epsilon Indi B sequence was run locally. **29 April, 1 May, and 7 May 2025 UTC** are the observation dates in the checked set, which uses a shared grid and display scale. The flows still need to be verified against the production commit. [Dataset catalog](DATASET_CATALOG.md) · [DR1 sequence receipt](data/spherex-dr1-timeline-smoke.json) · [Checklist on main](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/blob/main/Debai.md)

## Optional suggestions and challenge sources

The challenge suggests making new releases easy to add, exploring the 102 bands, combining data by each of the six detectors to improve signal, generating spectra, adding or subtracting images, choosing a field of view, overlaying Gaia or WISE, sharing coordinates in URLs, showing metadata such as contamination flags, and considering Astropy or Aladin. Wavelength selection in image comparison should distinguish a detector band from the wavelength at the sky position being viewed. Since each filter varies linearly across a pixel array, the wavelength may differ from pixel to pixel. Before inferring motion or variability, check WCS, wavelength, masks, and data quality. [Details](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details) · [Space Apps Connect technical discussion](https://github.com/nasa/spaceapps/discussions/1847)

| Group in the Resources tab | Links reviewed directly |
| --- | --- |
| NASA Data & Resources | [NASA/IPAC IRSA SPHEREx](https://irsa.ipac.caltech.edu/Missions/spherex.html) · [SPHEREx notebooks](https://caltech-ipac.github.io/irsa-tutorials/spherex/) · [WiseView](https://byw.tools/wiseview) · [Gaia DR3](https://archive.stsci.edu/missions-and-data/gaia) |
| Space Agency Partner Resources, CSA | [NEOSSat overview](https://www.asc-csa.gc.ca/eng/satellites/neossat/) · [CADC](https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/) · [NEOSSat tutorial](https://github.com/asc-csa/NEOSSAT_Tutorial) · [NEOSSat dataset](https://data.asc-csa.gc.ca/dataset/neossat) |

At the time of review, the Resources tab listed the eight items above. **Spectral Images DR1/QR3**, with FITS files from IRSA, is the primary data source for image sequences. The DR1 All-Sky Cube has a wavelength axis. [Resources](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=resources) · [SPHEREx releases](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases/) · [DR1](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html)

## Lighting in the orbit scene

SPHEREx’s fixed solar panels point toward the Sun for most of its orbit along Earth’s day–night line. During the survey, the mouth of the photon-shield assembly stays at least 91° from the Sun, and the telescope looks away from Earth. A soft illustrative light may come from the panel side. Rotation on hover is for inspecting the model. [JPL Press Kit: Spacecraft](https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/spacecraft/)

## Deployment and data storage

- GitHub protects `main` and requires pull requests to be up to date with the base branch, with Python and JavaScript checks. Vercel tracks `main`. At the time of review, the production domain returned HTTP 200 and the API reported commit `66247e3`. After merging, verify the new production commit, then try coordinate search, sequence playback, and image comparison. [Current Vercel deployment](https://nosleepclub-nasa-spherex.vercel.app/) · [Vercel Git](https://vercel.com/docs/git)
- The public image catalog currently contains **213 assets and 426 chunks**, with **127,478,741 bytes** of compressed payload before possible growth from base64, BSON, indexes, and review data. Atlas lists **0.5 GB** for one Free cluster and limits each project to one Free cluster. Vercel currently has one sensitive MongoDB URI in production. Further distribution requires an authorized secondary destination, manifest-based chunk routing, per-destination checksum checks, and continuity for existing paths. [Manifest](../web/api/_data_manifest.json) · [Storage procedure](DEPLOYMENT.md) · [Atlas Free cluster limits](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/)
