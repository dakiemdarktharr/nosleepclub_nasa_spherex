# Kết quả phát triển: ePSF mục tiêu có biên liên tục

**Kết quả: chưa đạt cơ sở thay phương pháp khoa học.** Trên ba trường đã mở, đệm ePSF mục tiêu làm Hessian profile ổn định hơn, nhưng RMS sai số vector không giảm trong cả sáu case Gaussian. Tại SNR 2/frame, số ellipse profile 68% chứa truth chỉ là 31/64, 36/64 và 34/64. Đây là tần suất trong phép thử có điều kiện, không phải ước lượng chính xác coverage của mọi nguồn ngoài trời.

Giao thức và mã mô hình được khóa tại commit `f138e1109183bb7db2122384ec1cfcd8f5958488`; thiết kế SHA-256 `ea41e9e83133329c04f9d648d193941053a84ca4805cdfd35c746634b6dfec5a`. Truth trong phép thử vẫn dùng ePSF nearest frozen và candidate chỉ đệm ePSF của mục tiêu; ePSF hàng xóm, mặt nạ, WCS, nhiễu và phép chiếu nuisance theo giao thức. Không có kiểm định PSF vật lý độc lập, không thêm source shot noise, không có trường độc lập mới và không có phép đo WISE 0855 mới. Xem [giao thức](CONTINUOUS_EPSF_PROTOCOL.md) để biết cách tạo dữ liệu, các giả định và giới hạn.

## Gaussian controls, từng field và case

Mỗi hàng là 64 draw Gaussian độc lập về nhiễu trên cùng geometry/exposure của một case, không phải 64 trường trời độc lập. Mọi fit của cả hai nhánh đều numeric-valid: mẫu số common numeric = 64. Bảng cho ellipse thô Gauss–Newton (GN) và observed profile Hessian (H), trước hiệu chuẩn nhóm; các số coverage là số chứa truth trên số có covariance. RMS tính trên cùng 64 cặp; ΔRMS = candidate trừ baseline.

| Field | SNR/frame | Common accepted | RMS base → candidate (″) | GN 68% base → candidate | GN 95% base → candidate | H 68% base → candidate | H 95% base → candidate |
|---|---:|---:|---:|---:|---:|---:|---:|
| w350p35 | 2 | 62/64 | 2,2905 → 2,3115 | 24/64 → 22/64 | 43/64 → 43/64 | 9/20 → 31/64 | 18/20 → 56/64 |
| w350p35 | 4 | 64/64 | 0,8029 → 0,8031 | 39/64 → 42/64 | 61/64 → 61/64 | 16/28 → 44/64 | 25/28 → 61/64 |
| w090p10 | 2 | 64/64 | 1,9428 → 1,9477 | 28/64 → 28/64 | 48/64 → 48/64 | 11/21 → 36/64 | 16/21 → 53/64 |
| w090p10 | 4 | 64/64 | 0,7822 → 0,7904 | 39/64 → 39/64 | 61/64 → 60/64 | 14/25 → 41/64 | 23/25 → 62/64 |
| w210m20 | 2 | 63/64 | 2,0948 → 2,1003 | 22/64 → 23/64 | 47/64 → 47/64 | 13/23 → 34/64 | 19/23 → 51/64 |
| w210m20 | 4 | 64/64 | 0,8541 → 0,8545 | 36/64 → 35/64 | 60/64 → 61/64 | 13/25 → 39/64 | 24/25 → 61/64 |

Baseline và candidate đều accepted lần lượt 62, 64, 64, 64, 63, 64/64 theo thứ tự hàng trên; trong dữ liệu này tập accepted hai nhánh trùng nhau. **H baseline có số mẫu nhỏ vì loại các Hessian không đạt điều kiện, nên không so sánh trực tiếp tỷ lệ H baseline với candidate như trên cùng population.** Các tập baseline numeric, baseline accepted, candidate numeric, candidate accepted, common numeric và common accepted có số mẫu, RMS, P90, coverage và ΔRMS ghép cặp được ghi riêng trong JSON.

Hessian dùng bước 0,002 và 0,004 sky pixel. Trong 768 epoch-fit Gaussian, 304 Hessian baseline có thay đổi tương đối hơn 5%, candidate có 0. Candidate có profile hợp lệ ở cả hai epoch trong cả 384 draw. Kết quả này xác nhận tính ổn định số của phép thử đã chạy, không chứng minh ước lượng uncertainty được hiệu chuẩn hay PSF đệm chính xác vật lý.

Diện tích ellipse 68% là `π × 2,278868566 × sqrt(det(C))`, đơn vị arcsec². Median trên common numeric, GN baseline → candidate lần lượt là 5,773 → 6,063; 1,982 → 2,041; 6,056 → 6,108; 2,025 → 2,069; 5,814 → 5,902; 2,010 → 2,048. Với profile candidate là 8,554; 2,307; 8,321; 2,342; 8,687; 2,231. JSON cũng ghi diện tích baseline profile và mẫu số tương ứng; do chọn lọc khác nhau, không coi tỉ lệ diện tích giữa chúng là so sánh ghép cặp.

## Ảnh nền gốc: sáu phép thử riêng

Các giá trị dưới đây là sai số vector arcsec của **một nguồn tiêm trên ảnh nền gốc** cho từng case, không nằm trong 64 draw Gaussian và không phải sáu phát hiện mới:

| Field | SNR/frame | Baseline (″) | Candidate (″) |
|---|---:|---:|---:|
| w350p35 | 2 | 2,5895 | 2,6121 |
| w350p35 | 4 | 1,1922 | 1,1897 |
| w090p10 | 2 | 1,3384 | 1,4012 |
| w090p10 | 4 | 0,5436 | 0,5499 |
| w210m20 | 2 | 1,7322 | 1,7642 |
| w210m20 | 4 | 0,4438 | 0,4493 |

## Kiểm toán và tái lập

Bản công khai [development-summary.json](../web/data/continuous-epsf/development-summary.json) giữ toàn bộ 384 cặp, vị trí trước/sau, vector sai số, covariance, q, trạng thái chất lượng, profile covariance và cờ hỗ trợ từng epoch. Các giá trị lưu không làm tròn; bảng trên làm tròn để đọc. Metadata gồm hash tất cả nguồn khóa, URL/sha256 ảnh và calibration được chọn, các cặp exposure, dữ liệu Gaia và provenance của trường.

Builder kiểm tra baseline đủ 384/384 cặp trùng cache, sáu baseline ảnh nền gốc trùng, và sáu replay draw 0 có cùng status, sai lệch vector 0 arcsec. Nó kiểm tra lại vector từ vị trí và truth, q từ covariance, covariance GN/profile với phần đăng ký chung, ổn định Hessian, và tính lại các mẫu số/RMS/coverage. Các so sánh tệp/nguồn thực hiện bằng SHA-256 và đối chiếu commit khóa. Kiểm thử độc lập tính lại q, diện tích và các subset từ JSON, đối chiếu cache khi có mặt:

```powershell
.venv/Scripts/python.exe -m scripts.build_continuous_epsf_report
.venv/Scripts/python.exe -m unittest tests.test_continuous_epsf_products -v
```

- Raw report SHA-256: `1bc935bed7871a6b71e1163047828c75712bd072d023321c265126409420e270`.
- Cache baseline SHA-256: `98d284e521f6b188435e49c4af701da55fc25b55a17fc3b29639456bbc209d30`.
- Báo cáo profile baseline SHA-256: `97c3cd54857cc7297415485c7bbb5c0d4a0d981eef32a9e9cf4ecb4509ed81ff`.

Bước kế tiếp là chẩn đoán bias và nguồn bất định còn thiếu trên dữ liệu đã mở, đồng thời khóa trước ngân sách sai số và thiết kế split field/exposure/time cho kiểm định độc lập. Chỉ xem xét promotion sau khi cả sai số tuyệt đối, coverage, diện tích ellipse và các failure/abstention đạt ngưỡng đăng ký trước trên trường chưa mở. Không tự nâng kết quả này thành phát hiện thiên văn.
