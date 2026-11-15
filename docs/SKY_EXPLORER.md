# SPHEREx Coordinate Search and Image Sequences

Enter RA in degrees or hours:minutes:seconds and Dec in degrees or degrees:minutes:seconds. Choose DR1 or QR3, a detector, field of view, and an optional date range, then search for images. DR1 is the default. Legacy QR2 links direct users to the reprocessed DR1 data. The query filters `BAND` by detector band to reduce the number of returned rows. SIA metadata describes the footprint of the full detector. [Data releases and QR2 status](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/).

Images are retrieved on demand from the IRSA cutout service. The app uses the FITS WCS/SIP solution to place each image on a north-up, east-left TAN grid at 6.15 arcseconds per pixel. Keep one reference image, then select another frame to blink between A and B. **Play sequence** becomes available after at least three images have been opened with a shared display scale and mask policy, distinct observation IDs and UTC MJDs, the same detector, valid center pixels, and WCS-WAVE overlap at the center of at least 75% of the widest band in the sequence. This threshold is a display rule. Stellar alignment, spectral response, variability, and motion require separate validation. FITS links point to the exact hashed cutout, including the extension needed to represent the image rotation. [WCS-WAVE limitations](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/).

**A/B comparison** uses the same grid, mask rule, and display scale. Choose an observation and detector band for each pane. Both panes share zoom and center when panned, moved with the arrow keys, or reset. The selector lists nominal bands. WCS-WAVE below each image shows the wavelength at the center position when it can be read from the FITS file. Changing the band in one pane keeps the other image and queries IRSA for the new band. Open **Observation timeline** to see observation times and play compatible frames. Wavelength can vary across the field. [IRSA visualization guide](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/visualization.html)

Orange marks pixels excluded by FLAGS; purple marks missing or out-of-image regions. Nearest-neighbor interpolation is for display. Photometry requires flux-preserving sampling and suitable uncertainty handling. The browser retries a cutout once after a temporary IRSA error or interrupted stream. If the image is still missing, the user sees an error and can choose another result. Request and cache limits keep service load bounded. IRSA may still be slow or unavailable.

`web/data/challenge-targets.json` records the source and epoch for example target centers. WISE 0855 and Barnard’s Star are propagated to 2026 so that fast-moving sources do not fall outside the field when using older catalog centers. Epsilon Indi B uses historical ESO field coordinates and a wider field of view; the pair is unresolved. These coordinates help locate fields and are not independent measurements.

On 30 October 2026, two real cutouts were retrieved at each example target center. Ten historical QR2 PNGs, with metadata, URLs, and hashes, are stored in `web/data/explorer-check/`. These pinned images remain available as examples when IRSA no longer returns QR2 search results. [Test-field catalog](DATASET_CATALOG.md).

## DR1 and QR3 check on 14 November 2026

The API read SIA VOTables from both releases at five field centers, using a 0.001° cone, a 4.415–4.996 µm band, and `MAXREC=100`, then filtered for detector D6.

| Field center | DR1 D6 | QR3 D6 |
| --- | ---: | ---: |
| WISE 0855 | 45 | 0 |
| Barnard’s Star | 41 | 17 |
| Epsilon Indi B | 49 (truncated) | 36 |
| RW Aurigae | 38 | 18 |
| R Draconis | 30 (truncated) | 21 |

IRSA returned two Barnard’s Star cutouts with FLAGS in the newer schema. The renderer produced PNGs at the requested 0.05° field of view, with 929 usable pixels from DR1 and 193 from QR3. QR3 lacked 763 pixels because the field only partially overlapped the cutout. SHA-256 for the DR1 cutout: `79c70ed83d50a7c9f1c0848547bf8e44add6270bb41384564bf82c411d2ab8d2`; for QR3: `5005ce035d4748c47b19dec3cef6362bffe51c06480af8fa1a929a6531e7d445`. The center pixel was masked or outside the image in both frames, so neither qualified for a WCS-WAVE sequence. [DR1 source](https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W33_2C/l2b-v27-2026-228/6/level2_2025W33_2C_0321_1D6_spx_l2b-v27-2026-228.fits?center=269.446266885%2C4.76822221648&size=0.08612855) · [QR3 source](https://irsa.ipac.caltech.edu/ibe/data/spherex/qr3/level2/2026W33_2A/l2b-v27-2026-241/6/level2_2026W33_2A_0594_3D6_spx_l2b-v27-2026-241.fits?center=269.446266885%2C4.76822221648&size=0.08612855).

Three DR1 D6 images of the **Epsilon Indi B field** passed the sequence display check at RA 331.04583333°, Dec −56.78333333°, and a 0.12° field of view. Their WCS-WAVE overlap at the center is **99.755%** of the widest band. The PNGs use a shared 71×71-pixel grid, mask policy, and contrast fixed from the first image. This field can be played as an image sequence. Resolving the pair or measuring its motion requires independent analysis.

| Start time (UTC) | Observation ID | Center wavelength (µm) | Usable pixels |
| --- | --- | ---: | ---: |
| 29 Apr 2025 01:35:28 | `2025W18_1B_0081_3` | 4.458349 | 4,885 |
| 1 May 2025 13:57:52 | `2025W18_2B_0011_3` | 4.458435 | 4,948 |
| 7 May 2025 05:14:15 | `2025W19_1B_0344_3` | 4.458371 | 4,609 |

In the sky view, select **Epsilon Indi B → Compare images** to load these three images in order. With the local server, you can also [open the Epsilon Indi B query for 29 April–7 May 2025](http://127.0.0.1:8767/?lang=en&sky_ra=331.04583333&sky_dec=-56.78333333&sky_fov=0.12&sky_det=6&sky_release=dr1&sky_from=2025-04-29&sky_to=2025-05-07&sky_sequence=epsilon-dr1&sky_autoload=1#explore). Select **Play sequence** after all three images are ready. Chromium loaded three cutouts from a live query that returned 25 rows, played them in order, and paused. The JSON retains original URLs, processing version, and SHA-256 values for SIA metadata, FITS, and PNG files. Other IRSA requests in the same session were slow, returned HTTP 503, or had interrupted downloads. [DR1 sequence receipt](data/spherex-dr1-timeline-smoke.json)

Select **Open saved sequence** on the same Epsilon Indi B card to play three PNGs whose hashes match the receipt without waiting for IRSA. This option also works with the static server, `python scripts/serve_demo.py`. The interface retains UTC times and a FITS link for each frame. [Metadata for the three saved images](../web/assets/mission/epsilon-sequence/provenance.json)

## Run locally

After installing `requirements.txt` and `web/requirements.txt`:

```powershell
python -m scripts.serve_app --port 8767
```

Open <http://127.0.0.1:8767/#explore>. The launcher binds to loopback, enables explicit local API budgets, and does not load production secrets. `python scripts/serve_app.py --check` checks imports without opening a socket. To serve exported products only, run `python scripts/serve_demo.py` on port 8766; this static server does not run the two new APIs. Local reviews stay in the browser, while cloud reviews are available only in production with configured credentials.

An exported explorer JSON bundle stores the query, IRSA metadata, provenance headers for viewed frames, display scale, and the user’s note. Explorer notes are exported to a file; they are not collaborative review records or scientific validation. Reviews of the fixed WISE analyses still use the client API with separate IDs and expiry.

See the [observations API](OBSERVATION_API_CONTRACT.md), [frame API](FRAME_API_CONTRACT.md), [quota controls](API_ABUSE_CONTROLS.md), and [verification and open limitations](PRODUCTION_READINESS.md).
