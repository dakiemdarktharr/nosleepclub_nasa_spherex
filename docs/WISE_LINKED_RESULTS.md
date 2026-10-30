# WISE 0855: ràng buộc phổ chưa giải quyết được vị trí

Đủ **28/28** lượt fit hoàn tất theo protocol khóa tại
`cfb9d6a17ee37ca2c5c061a2cd44209d1093f4b7`. Đây là development trên **20
exposure QR2 đã mở**: broad dùng 10 ảnh mỗi epoch, strict dùng hai ảnh mỗi
epoch và là tập con của broad. Không có trường kiểm định mới được mở. Kết quả
chưa chứng minh giảm bias, độ chính xác, coverage hay phát hiện thiên văn.

[Demo tương tác](https://nosleepclub-nasa-spherex.vercel.app/#linked-flux)
cho đổi bộ ảnh, xem biểu đồ, đủ bảy vector và lý do chặn từng epoch.
[Protocol](WISE_LINKED_PROTOCOL.md), [overview](../web/data/linked-flux/overview.json)
và [28 attempt đầy đủ](../web/data/linked-flux/development.json) giữ nguồn,
đơn vị, runtime, mask/pixel, ePSF zone, spectral coefficient, mọi start/mode,
trọng số và covariance có điều kiện. Không thay estimator hay manifest WISE
đang hiển thị trong workspace.

## Kết quả tất cả nhánh

Đơn vị giây cung. Δ là khoảng cách Euclid giữa vector của nhánh đó và vector
control **trong cùng bộ ảnh**; nó không phải sai số so truth. “Screen” là
kiểm tra số học cho cả hai epoch, chưa phải nghiệm thu khoa học.

| Nhánh | Broad đông / bắc | Broad Δ | Broad screen | Strict đông / bắc | Strict Δ | Strict screen |
|---|---:|---:|---|---:|---:|---|
| 1 · Độ sáng riêng từng frame | −3,067 / +0,087 | 0 | 2/2 | −2,535 / +0,501 | 0 | 1/2 |
| 2 · Phổ R7 68, α=0 · candidate định trước | −3,029 / −0,023 | 0,116 | 2/2 | −3,122 / +2,704 | 2,280 | 1/2 |
| 3 · Phổ + độ nghiêng tự do | −3,322 / +0,226 | 0,290 | 2/2 | −2,535 / +0,501 | ≈0 | 1/2 |
| 4 · Reference α=−4 | −3,029 / −0,023 | 0,116 | 2/2 | −3,122 / +2,705 | 2,281 | 1/2 |
| 5 · Reference α=+4 | −3,030 / −0,023 | 0,116 | 2/2 | −3,121 / +2,703 | 2,279 | 1/2 |
| 6 · Center QR2, shape R7 68 | −2,859 / −0,082 | 0,268 | 2/2 | −3,133 / +2,692 | 2,272 | 1/2 |
| 7 · Response R7 17 kênh | −3,028 / −0,026 | 0,120 | 2/2 | −3,122 / +2,703 | 2,279 | 1/2 |

Khoảng cách lớn nhất giữa **mọi cặp** vector là **0,555861″ broad** (nhánh 3
và 6), **2,280631″ strict** (nhánh 3 và 4). Giá trị broad lớn nhất so riêng
control là 0,290400″; không dùng con số này thay cho toàn bộ spread. Tính
spread giữ cả nhánh không qua screening. Hai bộ ảnh chia sẻ dữ liệu, không
phải hai kiểm định độc lập.

Nhánh 3 có hai tham số flux và hai wavelength khác nhau trong strict, nên
span tuyến tính tương đương hai flux độc lập. Vector trùng control là kiểm
tra đại số, không phải thêm một bằng chứng thiên văn.

## Hai nghiệm trong epoch sau của strict

Cả bảy nhánh strict hội tụ IRLS nhưng bị chặn bởi
`multiple_near_best_modes` ở epoch `after`. Đây không phải timeout hoặc
failure chuẩn bị. Tại control, hai nghiệm tốt nhất có χ² weighted
272,823844 và 272,861320, chênh **0,037476**. Với candidate chính, chênh là
**0,568008**. Ngưỡng Δχ² của mode audit là heuristic, chưa có phân phối xác
suất hoặc mức phủ được chứng minh cho robust fit này.

[Replay hậu kiểm](WISE_LINKED_MODE_DIAGNOSTICS.md) tính lại profile tuyến tính
tại các vị trí và trọng số đã lưu; không refit, chọn lại model hoặc mở dữ
liệu. Chi phí, flux/error và residual tại điểm đã lưu khớp đúng trên runtime
hiện tại. Trong control, hai exposure đóng góp Δχ² **+0,554247** và
**−0,516770**, gần triệt tiêu nhau. Trong nhánh shared, amplitude chung do cả
hai ảnh quyết định; không diễn từng phần χ² như hai phép đo độc lập.

Mask core được chọn đầy đủ tại các mode đã kiểm tra. Mỗi ảnh có ba template
catalog trong nuisance. Một template gần các mode; phần information nguồn
còn lại sau phép chiếu giảm mạnh hơn ở mode gần template. Đây là chẩn đoán
hình học của mô hình. Chưa chứng minh template đó gây đa mode, chưa xác định
là một nguồn thiên văn tách biệt và chưa biết nghiệm nào đúng hơn.

## Những gì đã kiểm tra và còn thiếu

- R7 channel map có `DETCOORD=sky`, còn map center/bandwidth có
  `DETCOORD=DEVICE`: binder áp dụng orientation riêng từng HDU, tránh lật
  kép. [Audit quy ước photometry](PHOTOMETRIC_CONVENTION_AUDIT.md) ghi rõ
  thông tin xác minh được và phần chưa xác minh.
- Renderer chuẩn hóa toàn lattice native hữu hạn trước mask, giữ dấu các
  cánh âm của ePSF, dùng WCS nguồn chính xác và Ω pixel có đơn vị. Kiểm tra
  hội tụ Ω không phải error bound vật lý; chưa ghép đúng SAPM UUID từ
  processing history. Chuẩn hóa không tự làm ePSF thành truth độc lập.
- PRISM pipeline MAST năm 2023 được dùng riêng, không ghép G395M, scale
  Spitzer hoặc deconvolve LSF. Reference α=0, ±4 là các giả định tường minh,
  chưa xác minh là chuẩn calibration SPHEREx. Row center QR2 vẫn dùng shape
  response R7, không phải so hai pipeline QR2/QR3 đầy đủ.
- Tỷ số phổ giữ tại pixel gần anchor, chưa tích phân response qua footprint
  ePSF hay đạo hàm theo vị trí đang fit. Chưa propagate uncertainty phổ,
  variability, LSF, shape response, PSF tails, ePSF QR3 trên ảnh QR2.
- Một vị trí mỗi epoch chưa mô tả chuyển động/parallax trong mùa. Offset
  Gaia và vị trí/hình nguồn nền giữ cố định; covariance thiếu các hệ thống
  này và cross-frame/cross-epoch chung. Không cộng RSS các SNR frame shared
  vì chúng dùng cùng một tham số amplitude.
- GN/profile-H chỉ mô tả quanh một nghiệm theo trọng số cuối. Không nới
  covariance tùy ý để phủ mode khác, không dùng nó như ellipse hiệu chuẩn.
  Jacobian vị trí không được lưu nên publication auditor không thể tính
  lại GN từ report một cách độc lập; có kiểm PD và phép biến đổi covariance.
- Publisher tính lại χ² theo pixel, flux basis/covariance, IRLS/mode flags,
  vectors, spread và profile-H inverse. Đây là kiểm toán số học, chưa kiểm
  chứng PSF/noise/astrometric truth hoặc độ chính xác của estimator.

## Tái lập và provenance

Raw checkpoint 4.788.083 byte, SHA-256
`a5bffe162ae8ccd88a6fc5311d1e8ddc279c56092b072a782652da5a7f1cfd0a`.
Design SHA-256
`c5914ab5b3ef1e8fb0b0a41c0d35d0bab741cc562ea820b632ca902e4944b072`.
Public report chứa nguyên records/checksum và phần kiểm toán bổ sung;
overview giữ SHA/byte size của report. Raw FITS và checkpoint lớn ở
`data/raw/`, không đưa vào Git. [Manifest biểu đồ](../web/data/linked-flux/figures.json)
ghi source, package/font hash và tọa độ đã vẽ.

```powershell
.venv/Scripts/python.exe -B -m unittest tests.test_linked_publication -v
.venv/Scripts/python.exe -B -m scripts.publish_linked_study
# Tuỳ chọn, chỉ cho hình khoa học offline; không đổi requirements science đã khóa:
.venv/Scripts/python.exe -B -m pip install -r requirements-figures.txt
.venv/Scripts/python.exe -B -m scripts.plot_linked_study
node tests/linked-evidence.test.cjs
.venv/Scripts/python.exe -B -m scripts.serve_app --port 8767
# Mở http://127.0.0.1:8767/#linked-flux
```

Runner nguyên thủy từ chối ghi đè study đã hoàn tất. Muốn thử can thiệp mới
cần module/design/output khác; không sửa protocol sau khi xem các mode này.

## Mốc kế tiếp và điều kiện nghiệm thu

Khóa phép thử nguồn chồng/ePSF trên **dữ liệu development đã mở**. So cùng
pixel/căn chỉnh và giữ mọi mode giữa: nuisance hiện tại; neighbor có ràng
buộc vật lý cùng uncertainty vị trí/hình; ePSF kiểm tra trên sao tham chiếu
giữ ngoài xây PSF. Thêm đối chứng độc lập về pha, SED, PSF/noise, không chọn
model vì gần vector tài liệu hơn. Đánh giá cả RMS/bias, failure/abstention và
ngân sách uncertainty; covariance nhỏ hơn hoặc χ² thấp hơn tự nó không đạt.

Sau đó nối time model theo exposure và uncertainty căn chỉnh chung. Chỉ mở
**12 calibration / 12 validation / 6 holdout cuối** khi evaluator, overlap
exposure/pixel, power, gate tuyệt đối và quy tắc ngoài miền đã khóa. Phép thử
này chưa đáp ứng những điều kiện đó; goal production vẫn đang thực hiện.
