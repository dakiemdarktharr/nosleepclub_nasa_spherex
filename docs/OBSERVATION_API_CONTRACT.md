# SPHEREx Observation Metadata API Contract, Version 1.0

`GET /api/observations` searches DR1 or QR3 Spectral Image MEF metadata through the fixed SIA2 endpoint `https://irsa.ipac.caltech.edu/SIA`. Results describe images that overlap the query region. FITS data, quality at the target position, and comparison suitability must be checked separately. IRSA may take about a day to expose new data through SIA. [SPHEREx data access documentation](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/) · [SIA2 documentation](https://irsa.ipac.caltech.edu/ibe/sia.html).

Example query: `/api/observations?ra=350&dec=35&radius=0.01&release=dr1&detector=4&maxrec=100`.

| Parameter | Value |
| --- | --- |
| `ra`, `dec` | Required, finite ICRS decimal degrees; RA [0, 360), Dec [-90, 90]. Sexagesimal is not accepted; the frontend converts it first. |
| `radius` | Cone radius in degrees, > 0 and ≤ 0.16; default 0.05. This is the POS query radius, not the image size or detector FOV. |
| `release` | `dr1` or `qr3`, default `dr1`. Each request queries one release. `qr2` returns HTTP 400 with `release_retired` because IRSA has retired QR2 search. |
| `deep` | `0` by default (wide) or `1` (deep); collections are not combined automatically. |
| `detector` | Optional integer 1–6; filtered locally using `energy_bandpassname`, after IRSA applies MAXREC. |
| `time_min_mjd`, `time_max_mjd` | Both MJD bounds (days) are required together, in 0–100000, with lower ≤ upper. SIA TIME selects overlapping intervals. |
| `band_min_um`, `band_max_um` | Both wavelength bounds in micrometers are required together, in 0.01–1000, with lower ≤ upper. Converted to meters for SIA BAND; overlapping intervals are selected. |
| `maxrec` | Integer 1–500, default 300; sent to IRSA as `MAXREC`. |

Unknown parameters, duplicate keys, infinite/NaN numbers, and arbitrary URLs are rejected. Every 200 response includes `contract_version`, `status`, normalized `query`, `observations`, `returned_count`, `upstream_count`, `truncated`, and `provenance`. `status` is `ok` when rows are returned, `no_data` when no rows remain after filtering and the upstream response did not report overflow, or `truncated` when SIA reports `QUERY_STATUS=OVERFLOW`. Do not interpret `no_data` to mean that a source does not exist or that the entire archive has no data. Detector filtering happens after MAXREC, so a truncated response can return zero rows without proving that the detector is absent. SIA order is not chronological order or ranking.

Each row includes `obs_id`, `detector` (possibly null if IRSA does not provide a recognizable detector name), `bandpass`, `t_min_mjd`/`t_max_mjd`, `em_min_m`/`em_max_m`, `wavelength_center_um`, `wavelength_width_um`, `footprint` (the original STC-S `s_region` string), `access_url`, and `release`. Missing values are returned as `null`. MJD values are retained as returned by IRSA; the API does not assume a time scale or convert them to UTC. The wavelength center/width are the midpoint and width of `em_min`–`em_max` for the full image/detector band, **not** the wavelength or bandwidth at the target pixel; use spectral WCS in the FITS for that measurement. An image URL is returned only if it is HTTPS, on the valid IRSA host, and a level2 path in the selected release; invalid URLs become null. FITS hashes are not inferred from metadata hashes.

`provenance` includes the endpoint, `query_url` with parameters sent to IRSA, `response_sha256` for the original VOTable bytes, `retrieved_at` in UTC, `source_format`, and `collection`. `query.detector` records the local filter. A new request may return different results as IRSA updates the archive. The hash identifies the metadata bytes from that retrieval.

Only UTF-8 XML VOTable `TABLEDATA` with `RESOURCE type=results`, valid `QUERY_STATUS`, and required columns/units is supported. DTD/entity, BINARY, and BINARY2 are not processed. Upstream input is limited to 2,000,000 bytes, 500 rows, and the request’s `MAXREC`. Redirects are rejected; connections use only the fixed SIA host/path. The socket timeout is 6 seconds, with an 8-second deadline checked between reads; a pending read can last up to the socket timeout. If upstream is an error, invalid, too large, or has the wrong collection or units, the API returns 502 with an `upstream_*` code; timeout returns 504. Invalid input returns 400, a commonly unsupported method returns 405, and an internal error returns 500. Stack traces are not returned. Logs include request ID, status, error class, and latency, but not query, IP, cookie, or credentials.

The API uses the project’s shared quota and edge protections. Production requires a Vercel runtime with HTTPS access to IRSA. Run `python -m scripts.serve_app` to check the API and interface through loopback. Tests use a mocked upstream and, when raw files are available, a historical QR2 VOTable. [API quotas](API_ABUSE_CONTROLS.md) · [DR1/QR3 checks at five targets](SKY_EXPLORER.md).
