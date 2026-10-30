# Audit gain vật lý theo pixel gốc

Đã nối UUID trong header của 31 cutout WISE với đúng tệp gain D6 QR2 qua IRSA. **30/31 ảnh có gain dương tại mọi pixel được target mask chọn**; ảnh còn lại có một pixel gain âm, không có flag, cách prior cũ khoảng 20,21 pixel và ngoài hộp prior ±5 pixel. Đó không phải vị trí fit lại; chưa xác định ảnh hưởng lên kết quả khoa học.

Đơn vị, UUID và hash đã kiểm tra. Orientation của gain là suy luận có điều kiện từ các snapshot R6 công khai: dùng WCS A để lấy `gain[y,x]`, không đảo thêm. Tệp gain không ghi DETCOORD và chưa tìm được source của các build ảnh chính xác. Binder từ chối gain không dương; chưa chạy bơm nhiễu photon hoặc đo lại nguồn. Bản ghi kỹ thuật dưới đây giữ đầy đủ giới hạn và nguồn để kiểm tra tiếp.

This audit binds one archived QR2 D6 absolute gain file to the 31 previously
cached WISE cutouts, conditional on the documented orientation inference below.
It does not inject source noise, refit positions, validate accuracy, or certify
a production calibration.

The IRSA TAP response `data/raw/benchmark/calibration-uuid-lookup.xml` maps
`0b762d1b-bec8-473f-9e6e-436fff6c631f` to the [D6 absolute gain FITS](https://irsa.ipac.caltech.edu/ibe/data/spherex/qr2/abs_gain_matrix/cal-agm-v7-2025-218/6/abs_gain_matrix_D6_spx_cal-agm-v7-2025-218.fits),
with product type calibration, product ID D6 and provenance version 6.1. Each
of the 31 IMAGE HISTORY headers names that exact UUID once. The complete TAP
query, cached-response SHA-256, URL, file SHA-256 and bytes, and calibration
headers are in the [audit JSON](../web/data/native-gain/development-audit.json).
The downloaded file is 16,652,160 bytes, SHA-256
`b297b1f286cd66b0ce109c5cb884ab08ca980376edf9f161cbf9cd754674bdb8`,
shape 2040 × 2040, software version `6.1.3.post97+g4430725`, and BUNIT
`MJy s / (electron sr)`, consistent with the [IRSA product description](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/).

The calibration file itself does **not** identify DETCOORD or contain a WCS.
The cutout IMAGE headers say `DETECTOR=6`, `DETCOORD=sky`, and alternate WCS A
is named `0-based active pixel coordinates`. The [public R6.4 pixel-removal
module](https://github.com/Caltech-IPAC/spherex-pipelines/blob/d31bc5a6666b4530c6e233c2484c586b4a598b24/py_src/spx_tasks/remove_reference_pixels.py)
sets the active-pixel WCS and reverses detector 4–6 images on X; its
[WCS helper](https://github.com/Caltech-IPAC/spherex-pipelines/blob/d31bc5a6666b4530c6e233c2484c586b4a598b24/py_src/spx_utils/alt_wcs.py)
defines this A system with zero-based active coordinates. The [R6.4 calibration
module](https://github.com/Caltech-IPAC/spherex-pipelines/blob/d31bc5a6666b4530c6e233c2484c586b4a598b24/py_src/spx_tasks/apply_dark_flat_field_and_photo_calib.py)
then multiplies the image directly by the gain array; the same direct operation
is present in [R6.5.5](https://github.com/Caltech-IPAC/spherex-pipelines/blob/aa0ba446ee12971024fe13dc1c47387615bbe85e/py_src/spx_tasks/apply_dark_flat_field_and_photo_calib.py).
The cutouts record the same module document version v1.5, but their exact
`6.4+psffix1` and `6.5.6` builds were not located in the public repository.
Thus using WCS A `(x, y)` as `gain[y, x]` with **no additional flip** is a
documented inference from public snapshots and recorded processing, not an
orientation asserted by the gain FITS metadata or verified exact-build code.
Independent official confirmation would close that gap.

The proposed binder is limited to this file, UUID, known hash and size, QR2 D6,
the two observed image versions, verified exact FITS header layout and an
identity-oriented linear WCS A. It requires native integer pixel coordinates,
an in-bounds active detector index, and finite positive gain for every pixel
requested. Unknown layouts, missing or conflicting metadata, wrong units,
noninteger positions, invalid indices or invalid gain fail explicitly. It does
not infer a flip or interpolate gain. The strict science target mask separately
requires finite image and positive finite variance and permits only zero or
SOURCE flags. The frozen pipeline and its masks are unchanged.

Of 31 cutouts, 30 have positive finite gain at every strict-target-mask pixel;
the other is partially unsupported. The exceptional pixel in
`2025W46_1A_0090_3` has native `(x,y)=(41,15)`, active `(932,1277)`, gain
−5.05665445, IMAGE −18.91776085 MJy/sr, VARIANCE 15.71095371 (MJy/sr)²,
and FLAGS 0. Adjacent gain values lie near 0.39–0.43. This co-located image
and variance anomaly is consistent with signed gain multiplication and a
squared variance scaling; it does not independently prove orientation. The
public v1.5 application passes the original flags through and contains no
visible positivity check on the gain array. The new binder rejects this pixel;
it never substitutes or silently discards its value. Descriptive gain quantiles
for the remaining positive pixels in that exposure are explicitly labeled as
a partial subset in the JSON.

For each exposure, the report gives gain quantiles and the corresponding
positive-gain coefficient `P(n) × gain / (n × TSAMP)` in gain per second, so
that multiplying by source surface brightness gives the ideal source-only
variance in squared brightness units. Here `n=SURLIM-(SURDLY-1)` and
`P(n)=6/5 × (n²+1)/(n²−1)`; the previously developed ideal-ramp timing checks
also verify XPOSURE against `(n−1) × TSAMP`. This is a coefficient, not a
measurement or a simulated draw. It does not include source PSF or SED truth,
partial ramps, read noise, nonlinearity, crosstalk or gain uncertainty. Before
any photon injection, lock an independent source/PSF/SED and noise protocol.

With the already cached input files, rebuild using
`.venv\Scripts\python.exe scripts/audit_native_gain.py` and test using
`.venv\Scripts\python.exe -m unittest tests.test_native_gain_binding -v`.
