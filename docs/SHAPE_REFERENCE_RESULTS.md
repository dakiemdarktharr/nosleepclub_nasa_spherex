# Hiệu chỉnh ePSF và covariance sao tham chiếu — 31/10/2026

**Ứng viên ePSF chưa được áp dụng vào phép đo.** Bước học qua các kiểm tra
thông tin và hình dạng, nhưng phép thử vị trí trên calibration tìm thêm nghiệm
cạnh tranh ở hai sao. Gate đã chặn đánh giá 252 ô còn lại. Nghiên cứu covariance
riêng tái lập được bằng đại số độc lập, nhưng chưa hiệu chuẩn tổng sai số.

[Mở demo](https://nosleepclub-nasa-spherex.vercel.app/#shape-validation) ·
[20 tiêu chí](PRODUCTION_READINESS.md) · [MIT](../LICENSE) · [NOTICE](../NOTICE.md).

## Ba bước được khóa trước khi chạy

| Bước | Commit protocol | Kết quả |
|---|---|---|
| Học ba hệ số ePSF từ calibration | `972c8b8723326bc60e99ebd8611e1beb6efd34b3` | 145 ô có thông tin /168 kế hoạch; 22 ô không có ảnh phù hợp, một ô baseline bị từ chối số học |
| Covariance baseline và khung tham chiếu | `b42515e3a4ac95df5e786d47f5ff18ad706b937b` | 357 ô có đáp ứng /420; 61 ô thiếu hỗ trợ và hai ô bị từ chối vẫn được giữ |
| Fit vị trí với hệ số ePSF đã seal | `31d07ab777628aecc90af3b244e882e2e6d95b93` | Calibration: 146 fit /168 ô, 22 lỗi chuẩn bị cũ. Gate không đạt; 252 ô assessment chưa được mở |

Tất cả sao và ảnh đều thuộc trường WISE đã mở. 14 nhãn training và bảy nhãn
heldout đã có từ trước; các kết quả baseline của chúng cũng đã được xem.
Trong mỗi mùa, sáu exposure đầu theo IMAGE MJD-AVG dùng học, bốn exposure cuối
dành cho đánh giá sau. Cách chia này tách dữ liệu cho phép thử mới, nhưng không
biến cohort đã chọn từ ảnh thành kiểm định bầu trời độc lập. 30 tâm trường
12/12/6 triển vọng vẫn chưa được query hoặc đo.

## Bước học: giảm một sao chi phối, chưa chứng minh giảm bias

Preflight không dùng residual score cho thấy một sao sáng đóng góp tới
50,70% thông tin theo một hướng hiệu chỉnh. Trước khi học hệ số, estimator
được đổi sang cân bằng theo thông tin trung bình mỗi exposure của từng sao.
Đây là lựa chọn sau khi xem thông tin của tập development, được công bố trong
[protocol](SHAPE_CALIBRATION_PROTOCOL.md). Ngưỡng chi phối 35% được giữ nguyên.

Sau cân bằng, đóng góp lớn nhất là **12,87%**, condition của thông tin ba chiều
là **1,052**. 13/14 sao cung cấp thông tin. Cả 145 mẫu khả dụng qua kiểm tra
moment, biến đổi peak và cánh âm. Hệ số được seal trong Git trước fit vị trí:

| Hệ số | Giá trị | Sai số chuẩn có điều kiện | Đơn vị |
|---|---:|---:|---|
| Độ rộng | −0,00830790 | 0,00568703 | pixel² native |
| Bất đối xứng x | +0,000695585 | 0,000828389 | pixel³ native |
| Bất đối xứng y | +0,000807192 | 0,000807902 | pixel³ native |

Họ mô hình giữ tổng và hai moment bậc nhất trên lattice native đầy đủ trước
khi mask; target và mọi hàng xóm giữ lại dùng cùng họ hiệu chỉnh. Điều đó cố
định một quy ước số học, không xác định tâm quang học thật hoặc chuẩn flux của
thiết bị. Covariance dùng đáp ứng trên 20.327 pixel gốc khác nhau, cộng đóng
góp của stamp chồng trước khi lan truyền noise.

Sai số trên có điều kiện theo vị trí baseline, trọng số Huber, cân bằng nguồn,
mask, tọa độ catalog và calibration. Cân bằng phụ thuộc biên độ khớp có nhiễu;
biến thiên của chính trọng số chưa được lan truyền. Không coi hệ số hoặc tỷ lệ
giá trị/sai số này là kiểm định quang học hay bằng chứng bias đã giảm.

## Gate vị trí: hai ca mất hỗ trợ

Không học lại hệ số. Fitter giữ pixel, error quan sát, nền phẳng nghiêng, flux
Jy có dấu, vị trí hàng xóm, chín điểm khởi đầu và giới hạn Huber của baseline.
Trong 145 ô trước đây có hỗ trợ số học, **143** còn hỗ trợ. Trên 143 ô này,
chênh lệch giữa thay đổi vị trí thực và dự báo tuyến tính có P90 **0,004593
pixel common** và cực đại **0,025339 pixel common**, dưới ngân sách 0,02/0,05.
Hai ô còn lại làm gate thất bại, không bị xóa khỏi mẫu số.

| Gaia source ID | Exposure | Số nghiệm gần tốt nhất cũ → mới | Hai nghiệm mới cách nhau |
|---|---|---:|---:|
| 5756942110218608640 | 2025W46_2A_0214_3 | 1 → 2 | 1,889921″ |
| 5756958431094222592 | 2025W46_2A_0214_3 | 1 → 2 | 3,378414″ |

Đây là các nghiệm được tìm trong audit chín điểm khởi đầu với trọng số cuối
cố định; ngưỡng Δχ² 5,991 là heuristic. Chưa chứng minh đã tìm hết nghiệm,
hoặc các nghiệm khác không tồn tại trong baseline. Cả hai fit Huber hội tụ;
nguyên nhân chặn lần này là nghiệm vị trí cạnh tranh, không phải hết iteration.

**252 ô assessment, gồm 56 ô primary = bảy sao × tám exposure, chưa được
đánh giá bằng mô hình hiệu chỉnh.** Các gate primary trong JSON chưa đạt do
chưa có kết quả; đó không phải kết luận chúng đã được đo và thất bại. Mọi
định danh, lỗi và danh sách ô hoãn vẫn có trong audit. Ngưỡng nhận nguồn cũ
không được chuyển sang PSF mới; phép đo WISE 0855 giữ nguyên.

Kiểm toán độc lập kiểm đủ 168 định danh/checksum, 146 mô hình trên native
pixel, IRLS và các nhóm nghiệm. **1.314/1.314** hàm mục tiêu cuối được replay
bằng BVLS tại vị trí đã lưu: chênh χ² lớn nhất **2,274×10⁻¹³**, chênh model
lớn nhất **1,776×10⁻¹⁵ MJy/sr**. Không tối ưu lại vị trí trong audit. Jacobian
và rank vị trí chưa được audit độc lập; đây không phải kiểm chứng PSF vật lý.

## Covariance baseline: giữ tương quan, chưa đạt hiệu chuẩn

Nghiên cứu riêng này dùng ePSF nearest cũ, **không** dùng hệ số vừa học. Đáp
ứng vị trí được tính tại điểm fit baseline đã lưu. Một biến noise cho mỗi
exposure/native pixel giữ tương quan giữa stamp chồng; Gaia giữ covariance
năm tham số dùng chung theo thời gian của mỗi sao. Ma trận có **49.294** pixel
gốc khác nhau. Nghiệm tịnh tiến của 20 exposure chỉ dùng sao training, với
11–13 sao khả dụng mỗi exposure. Covariance residual heldout giữ cả số hạng
chéo giữa sao và nghiệm khung tham chiếu.

| Chẩn đoán có điều kiện | Số ô dùng được | Chi² | Bậc tự do | Chi²/bậc tự do |
|---|---:|---:|---:|---:|
| Training | 238 | 833,8641 | 436 | 1,9125 |
| Heldout | 119 | 407,4310 | 238 | 1,7119 |

Sao heldout `5756959015209770112` không có ô khả dụng vẫn nằm trong bảng
`0/20`; sao training `5756962382464133248` cũng được giữ. Không bỏ outlier,
thêm floor hoặc tự nhân covariance để làm chi² vừa một. Thống kê danh nghĩa
cho thấy phần dư chưa khớp mô hình sai số này; chưa xác định được phần chênh
do bias, noise, nguồn chồng hoặc các thành phần còn thiếu.

Kiểm toán QR độc lập trên **357/357** điểm native tái dựng đúng data, error,
nền và thiết kế hàng xóm. Sai khác tuyệt đối lớn nhất của đáp ứng vị trí là
**5,575×10⁻¹⁵**, của covariance pixel là **2,082×10⁻¹⁷ pixel²**. Ma trận Gaia,
nghiệm GLS và residual heldout cũng được tái tính độc lập. Thành công đại số
không chứng minh covariance đã đủ: mask, trọng số, ePSF, đăng ký cũ và tọa độ
hàng xóm vẫn được giữ cố định, chưa lan truyền phụ thuộc noise của chúng;
catalog khác sao được giả định độc lập. Cohort đã mở và upstream WCS/ePSF có
thể dùng chung dữ liệu. Chưa có kiểm định độ phủ tổng thể.

## Sản phẩm có thể kiểm tra

| Sản phẩm | Bản nhẹ | Toàn bộ audit |
|---|---|---|
| Học hệ số | [Overview](../web/data/shape-correction/overview.json), [seal](../web/data/shape-correction/coefficient-seal.json) | [2,48 MB gzip](../web/data/shape-correction/calibration-records.json.gz) |
| Fit calibration và gate | [Overview](../web/data/shape-point-check/overview.json), [gate](../web/data/shape-point-check/calibration-gate.json), [audit độc lập](../web/data/shape-point-check/independent-audit.json) | [3,06 MB gzip](../web/data/shape-point-check/records.json.gz) |
| Covariance baseline | [Overview](../web/data/reference-covariance/overview.json), [audit độc lập](../web/data/reference-covariance/independent-audit.json) | [2,72 MB gzip](../web/data/reference-covariance/records.json.gz) |

Các overview ghi SHA-256 nén/giải nén, số byte, commit protocol, digest journal,
source audit và đơn vị. Web chỉ tải ba overview khi mở mục; archive là tải riêng.
FITS gốc vẫn ở cache bị Git bỏ qua; URL/hash/mask/phiên bản nằm trong từng record.
Sản phẩm 0.3–0.9 và hai nghiên cứu 840/7.992 lượt trước đó giữ nguyên.

Tài liệu [IRSA](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/)
và [tutorial chính thức](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/)
khuyến nghị ePSF mới cho ảnh QR2. Vì vậy, hai ca này không tự chứng minh việc
ghép QR2/ePSF mới là sai. [Photutils](https://docs.astropy.org/projects/photutils/en/stable/user_guide/epsf_building.html)
mô tả vai trò sampling, tâm và chuẩn hóa; không xác nhận họ hiệu chỉnh này.

## Bước tiếp theo và tiêu chí

Hồi quy local chạy **528 ca Python: 522 đạt, sáu ca Mongo fixture bỏ qua** vì
không đưa credential production về máy. Sáu suite Node 24 đạt. [Biên nhận
source/log](evidence/0.10/shape-reference-local-tests.json) và [kiểm tra
desktop/mobile/bàn phím](evidence/0.10/shape-local-browser.json) ghi phạm vi
thực tế; chưa phải audit screen-reader/WCAG đầy đủ. CI Mongo và bản public
cần biên nhận phát hành riêng.

Ưu tiên giải thích hai nghiệm cạnh tranh trong cùng exposure: khóa một phép
chẩn đoán profile vị trí trên hai sao lỗi, các sao training cùng ảnh và ảnh
liền kề; lưu ảnh gốc/model/residual/mask và vai trò hàng xóm. Phân biệt mode
có sẵn nhưng solver bỏ sót với thay đổi landscape khi chỉnh PSF. Giữ mọi ca
và không đổi ngưỡng để làm gate xanh.

Milestone đạt khi có kiểm tra tái lập được cơ chế gây cạnh tranh và một
estimator/miền từ chối được khai báo trước, thử cả giữ tín hiệu lẫn nguồn chồng.
Sau đó mới lan truyền đăng ký/tọa độ hàng xóm đầy đủ và kiểm định độ phủ theo
đặc trưng quan sát S/N, nền, crowding trên các split riêng. Chỉ mở 30 trường
triển vọng sau khi khóa evaluator, ngân sách sai số tuyệt đối, power, overlap
và quy tắc chấp nhận. Backup/restore production, tải đại diện, SLO và audit
accessibility đầy đủ tiếp tục nằm trong ledger; milestone này không đóng chúng.
