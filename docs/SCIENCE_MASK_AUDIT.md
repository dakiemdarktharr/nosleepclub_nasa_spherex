# Audit mask SPHEREx trên dữ liệu đã mở

Policy cũ cho phép bit FULLSAMPLE; tài liệu SPHEREx yêu cầu loại vùng này khỏi khoa học. **Không có pixel FULLSAMPLE trong 31 cutout WISE đang dùng**, nên lỗi policy này không đi vào phép fit qua các cutout đó. Chưa kiểm tra ảnh hưởng ở các trường khác hay QR3.

Policy mới tách pixel để fit nguồn và pixel để thống kê nền: SOURCE vẫn dùng được khi fit nguồn, nhưng bị loại khi ước lượng nền riêng. Đây không có nghĩa phải bỏ pixel SOURCE khỏi một phép fit đồng thời nguồn+nền. Thay đổi nền chưa được thử lại với estimator; giữ nguyên sản phẩm khoa học đã khóa. Các số đếm, nguồn chính thức và cách tái lập dưới đây là audit phát triển, không phải phép đo WISE mới.

The prior WISE science mask and the prior frame renderer both allowed the
FULLSAMPLE flag, bit 12. The official [SPHEREx Explanatory Supplement v1.3,
Table 10](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf)
describes this rotating 8 × 32 full-history region as not usable for science.
The [IRSA source-discovery tutorial](https://caltech-ipac.github.io/irsa-tutorials/spherex-source-discovery-tool-demo/)
also includes it among excluded flags. The [official pipeline flags](https://github.com/Caltech-IPAC/spherex-pipelines/blob/aa0ba446ee12971024fe13dc1c47387615bbe85e/py_src/spx_data/spx_flags.py)
define FULLSAMPLE as `1 << 12` and SOURCE as `1 << 21`. The [IRSA QR2/QR3
help table](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html)
lists both flags for both releases; its “yes” columns describe availability,
not a claim that FULLSAMPLE is suitable for science.

The archived WISE coadd contains **zero FULLSAMPLE pixels** in 31 QR2 cutouts
(151,830 native pixels); zero are legacy-good. Every individual exposure has
zero, including the independently defined linear-prior target regions: a
2.5-native-pixel radius (611 pixels total) and a ±5-pixel box (3,100 pixels
total). Consequently this specific bit cannot have entered the WISE fit through
these 31 cutouts. This audit does not establish that the old policy is safe for
other fields, unexamined exposures, or QR3. The prior is the pre-existing
Luhman 2014 linear search position evaluated at IMAGE MJD-OBS. These regions
do not incorporate parallax or frame registration; they are not fitted source
positions. The zero count for the entire cutout is stronger than either region,
but does not address any data outside it. No source measurement was repeated.

The old science mask excludes its explicit BAD_BITS and additionally requires
finite image and finite positive variance. The old web display mask permits
only zero, SOURCE and FULLSAMPLE and requires finite image, not variance; its
actual output uses a nearest-neighbor resampled grid and an inside test. The
public report's native counts describe the equivalent per-pixel flag rule, not
a count of rendered output pixels. The prior renderer source is identified by
Git commit and SHA-256 independently of any later runtime changes.

The proposed `science_mask_policy.py` is a new, standalone, conservative
policy: target pixels may carry only SOURCE; background pixels must carry no
flags. Both also require finite image and finite positive variance. In these
cutouts the proposed target mask and old science mask each retain 147,238 pixels;
the background mask retains 102,142. In the 611-pixel prior circles, 605 meet
the old/target rule but none meet the background rule, because those valid
pixels carry SOURCE. This background-policy change is distinct from the
FULLSAMPLE correction and its downstream impact has not been measured. It is
not appropriate to silently substitute it into frozen products.

The policy accepts only explicitly labeled `spherex_qr2` or `spherex_qr3`
L2 inputs with mandatory MP_* cards matching the checked pipeline layout;
additional MP_* cards must match the verified names and bit positions, and
every set image bit must be declared by that frame. Unknown, missing, duplicate,
or mismatched definitions, negative/noninteger flags and undeclared bits fail
closed. The 31 audited headers are QR2, with two documented subsets of MP_*
definitions. QR3 is supported only conditional on the supplied header passing
the same checks; no QR3 frame has been audited here. The allowlist is deliberately
stricter than general-purpose IRSA photometry flags and does not itself prove
scientific suitability.

Reproduce from existing cached inputs with
`.venv\Scripts\python.exe scripts/audit_science_masks.py` and verify with
`.venv\Scripts\python.exe -m unittest tests.test_science_mask_policy -v`.
The [development audit](../web/data/mask-audit/development-audit.json) records
the manifest and raw FITS SHA-256, URLs, per-exposure header definitions, WCS
prior coordinates, each region's counts, and source hashes. Input hashes must
match before counting. This is a descriptive audit, not a new calibration,
validation, source detection, or revised WISE result.
