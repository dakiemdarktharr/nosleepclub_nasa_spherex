# SPHEREx Detector Field Previews

The five sky entry points show previews of the **complete measured SPHEREx detector frame**. Each uses the first D6 exposure from the pinned QR2 checks. The wide view provides context before opening a sequence of coordinate-centered cutouts. Markers use the repository’s guide coordinates transformed through the original image WCS; they indicate the intended viewing location. Preview intensity is stretched independently for each frame. [Pinned frames](../web/data/explorer-check/coverage.json) · [Metadata and hashes](../web/assets/mission/full-fields/provenance.json)

| Viewing point | Observation ID | UTC | Image |
| --- | --- | --- | --- |
| WISE 0855 | 2025W19_1B_0116_1 | 2025-05-05 16:48:02 | [WebP](../web/assets/mission/full-fields/wise0855.webp) |
| Barnard’s Star | 2025W33_2C_0321_1 | 2025-08-15 20:45:11 | [WebP](../web/assets/mission/full-fields/barnard.webp) |
| Epsilon Indi B | 2025W18_1B_0081_2 | 2025-04-29 01:33:19 | [WebP](../web/assets/mission/full-fields/epsilon.webp) |
| RW Aurigae | 2025W37_2A_0051_1 | 2025-09-11 16:15:33 | [WebP](../web/assets/mission/full-fields/rwaur.webp) |
| R Draconis | 2025W20_2D_0243_1 | 2025-05-16 22:56:23 | [WebP](../web/assets/mission/full-fields/rdra.webp) |

Each **2040 × 2040** frame is median-binned 4 × 4 to **510 × 510**. The display includes finite IMAGE pixels with no flags or with only SOURCE bit 21. Each binned pixel requires at least four valid values. Dark blue marks bins with missing data. The detector axes are retained, with row order flipped for display. The 1st and 99th percentiles define an asinh stretch. Background and artifacts vary across detector coordinates. These previews are for orientation; inspect compatible cutouts with suitable units and display ranges for time-series comparison.

The input retains bytes 0 through 33,330,239 from each original IRSA FITS file, including the complete PRIMARY, IMAGE, and FLAGS HDUs. The manifest records SHA-256 hashes for the input byte range and each corresponding WebP. The original image data are from NASA/IPAC IRSA SPHEREx QR2. [Release notes](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases/)
