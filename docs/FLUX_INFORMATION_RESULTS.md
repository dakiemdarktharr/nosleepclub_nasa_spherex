# Kết quả chẩn đoán thông tin flux tại truth

Trên ba trường đã mở, phép thử matched Gaussian tại vị trí truth cho thấy `JᵀJ` lớn hơn thông tin Fisher profile `F`, gần dự đoán `G` của mô hình số học đã khóa. Hessian trung bình nhìn chung gần `F`, nhưng chưa đủ chính xác để kết luận mọi epoch đều nằm trong dải chẩn đoán ±20%. Đây là kết quả tại **vị trí truth với trọng số cố định**, không phải phép fit vị trí, coverage, RMS, xác nhận thiên văn hay cơ sở promotion.

Giao thức và nguồn đã khóa tại commit `215dbfab9fb02ed8a1faec43639fd224ea52450d`; thiết kế SHA-256 `59d43f97fb2784760fd851f78a5f12fa13ac1b98904aee47f0778640ae1828c1`. Mỗi case gồm 64 draw Gaussian; hai epoch và hai điều kiện truth dùng chỉ số draw ghép cặp. Các draw là các realization nhiễu, **không phải field trời độc lập**. Không có IRLS, inflation theo reduced χ², optimizer, source shot noise hay dao động registration. Điều kiện primary có truth padded khớp template; secondary giữ truth nearest cũ và cùng nhiễu. Các expectation `F`, `G`, `V` chỉ áp dụng trực tiếp cho primary dưới các giả định trong [giao thức](FLUX_INFORMATION_PROTOCOL.md).

## Kết quả từng epoch

Tỷ số `M/F` trong bảng là `tr(F⁻¹M)/2`, vô thứ nguyên. Cột quan sát có dạng **matched / old-nearest**; các giá trị lý thuyết `G/F` và `V/F` được tính cho matched. CI 95% của Hessian là bootstrap 2.000 mẫu theo draw, tại bước 0,002 sky pixel, cho matched. Mỗi nhóm có 64/64 kết quả, 0 failure và 64/64 Hessian ổn định theo kiểm tra bước 0,002/0,004 ở **cả hai** điều kiện. Các CI là thăm dò, chưa điều chỉnh cho nhiều epoch/case.

| Field | SNR/frame | Epoch | `JᵀJ/F` matched / old | `G/F` matched | `H/F` matched / old; CI matched | Cov(score)/F matched / old / `V/F` | Mean χ²/dof matched / old |
|---|---:|---|---:|---:|---|---:|---:|
| w350p35 | 2 | before | 1,476 / 1,476 | 1,501 | 0,911 / 0,910; [0,816; 1,010] | 1,273 / 1,273 / 1,250 | 0,9999 / 0,9999 |
| w350p35 | 2 | after | 1,540 / 1,540 | 1,501 | 1,025 / 1,024; [0,916; 1,133] | 1,217 / 1,217 / 1,250 | 1,0140 / 1,0140 |
| w350p35 | 4 | before | 1,115 / 1,115 | 1,125 | 0,967 / 0,966; [0,922; 1,015] | 1,124 / 1,124 / 1,063 | 0,9999 / 0,9999 |
| w350p35 | 4 | after | 1,140 / 1,140 | 1,125 | 1,008 / 1,008; [0,955; 1,059] | 1,054 / 1,054 / 1,063 | 1,0140 / 1,0140 |
| w090p10 | 2 | before | 1,529 / 1,529 | 1,509 | 0,982 / 0,981; [0,888; 1,078] | 1,356 / 1,356 / 1,254 | 1,0012 / 1,0012 |
| w090p10 | 2 | after | 1,497 / 1,496 | 1,508 | 1,003 / 1,003; [0,893; 1,112] | 1,096 / 1,096 / 1,254 | 0,9989 / 0,9989 |
| w090p10 | 4 | before | 1,140 / 1,140 | 1,127 | 0,994 / 0,994; [0,951; 1,037] | 1,092 / 1,092 / 1,064 | 1,0012 / 1,0012 |
| w090p10 | 4 | after | 1,127 / 1,127 | 1,126 | 1,021 / 1,020; [0,967; 1,074] | 0,924 / 0,923 / 1,063 | 0,9990 / 0,9990 |
| w210m20 | 2 | before | 1,559 / 1,560 | 1,501 | 1,140 / 1,140; [1,023; 1,260] | 1,452 / 1,452 / 1,251 | 0,9945 / 0,9945 |
| w210m20 | 2 | after | 1,493 / 1,493 | 1,501 | 0,939 / 0,939; [0,853; 1,027] | 1,475 / 1,475 / 1,251 | 1,0011 / 1,0011 |
| w210m20 | 4 | before | 1,157 / 1,157 | 1,125 | 1,070 / 1,070; [1,016; 1,124] | 1,206 / 1,206 / 1,063 | 0,9945 / 0,9945 |
| w210m20 | 4 | after | 1,123 / 1,123 | 1,125 | 0,970 / 0,970; [0,913; 1,031] | 0,973 / 0,973 / 1,063 | 1,0011 / 1,0011 |

Với dung sai chẩn đoán `[0,8; 1,2]` đã định, CI của `w210m20` SNR 2 before giao biên trên, nên nhóm này **chưa kết luận**; các CI matched còn lại hoàn toàn trong dải đó. Điều này không phải kiểm định tương đương chính thức. Các giá trị mean `H/F` tại bước 0,004 khác bước 0,002 không quá 0,000029 trên 24 nhóm condition–epoch. Cov(score) là covariance mẫu có trừ mean; JSON ghi ma trận đầy đủ và CI bootstrap hậu kỳ theo draw cho tỷ số của nó, không điều chỉnh nhiều phép so sánh.

Mean score và CI bootstrap 95% của matched, theo thứ tự trục sky-grid x/y, ở đơn vị sky-pixel⁻¹:

| Field / SNR | Epoch | Mean score x; CI | Mean score y; CI |
|---|---|---|---|
| w350p35 / 2 | before | 1,459; [−0,654; 3,569] | −1,792; [−4,140; 0,461] |
| w350p35 / 2 | after | −1,201; [−3,257; 0,751] | 0,598; [−1,521; 2,763] |
| w350p35 / 4 | before | 2,696; [−1,232; 6,693] | −2,918; [−7,193; 1,110] |
| w350p35 / 4 | after | −0,268; [−3,382; 2,836] | 0,338; [−3,932; 4,929] |
| w090p10 / 2 | before | 0,129; [−2,258; 2,491] | −0,345; [−2,583; 1,938] |
| w090p10 / 2 | after | −0,997; [−2,986; 0,948] | −0,691; [−2,549; 1,136] |
| w090p10 / 4 | before | −0,376; [−4,638; 3,828] | −0,178; [−4,335; 3,975] |
| w090p10 / 4 | after | 1,063; [−3,067; 4,897] | −0,110; [−3,094; 2,874] |
| w210m20 / 2 | before | 0,950; [−1,231; 3,179] | −0,021; [−2,384; 2,409] |
| w210m20 / 2 | after | 0,001; [−2,300; 2,260] | 0,068; [−2,508; 2,708] |
| w210m20 / 4 | before | 1,957; [−1,786; 5,913] | −0,544; [−4,935; 3,869] |
| w210m20 / 4 | after | −2,746; [−6,267; 0,858] | 2,168; [−1,975; 6,173] |

Tất cả các khoảng trên chứa 0, nhưng điều đó không chứng minh mean score bằng 0. Chênh lệch trung bình ghép cặp old-nearest trừ matched có trị tuyệt đối tối đa 0,000109 cho `JᵀJ/F` và 0,000696 cho `H/F` ở 12 nhóm; các so sánh và CI đó là phân tích hậu kỳ, không xác nhận PSF vật lý. Bậc tự do được tính theo từng exposure: số pixel hợp lệ trừ rank nuisance trừ một amplitude, không trừ centroid vì centroid không được fit.

## Kiểm toán và dữ liệu công khai

[development-summary.json](../web/data/flux-information/development-summary.json) giữ **đầy đủ và không làm tròn** 384 draw × hai điều kiện × hai epoch: `JᵀJ`, hai Hessian, score, score quadratic, χ²/dof, amplitudes profile, cờ ổn định, failure và metadata. Các summary/CI được tính lại từ draw và so với raw; thêm bootstrap hậu kỳ cho covariance score và chênh matched/old. Metadata gồm hash code, giao thức, dữ liệu nguồn, URL, calibration, catalog và exposure đã chọn.

Raw report chỉ lưu các ma trận `F`, `F_known`, `G`, `V` tổng cùng amplitude, thông tin mục tiêu, pixel và rank theo exposure; nó **không** lưu ma trận đạo hàm từng exposure. Builder tái dựng hậu kỳ những ma trận `DᵀPD` và `DᵀD` từ native inputs đã cache bằng chính code frozen, kiểm hash manifest/FITS/calibration/catalog và cộng lại để kiểm cả bốn ma trận tổng. Các đóng góp đó được công khai tại `post_run_geometry_audit`; đây là tái dựng xác định bằng cùng triển khai, không phải phép đo mới hay kiểm chứng độc lập công thức đạo hàm. Raw report được giữ nguyên.

```powershell
.venv/Scripts/python.exe -m scripts.build_flux_information_report
.venv/Scripts/python.exe -m unittest tests.test_flux_information_products tests.test_flux_information_probe -v
```

- Raw report SHA-256: `e21a60352a8f04291e13a370126322b178edb78c8c49f8508248e57c79aa5100`.
- Thiết kế SHA-256: `59d43f97fb2784760fd851f78a5f12fa13ac1b98904aee47f0778640ae1828c1`.

Kiểm toán tái tính q, mean ma trận, CI theo draw, χ²/dof và tổng từ từng exposure. Sai khác lớn nhất khi tái phát mean cũ là `7,05e-17` đơn vị ảnh native; nhiễu selected-pixel là `5,56e-17`. Những kiểm tra này không đo sai số vật lý hoặc kiểm định coverage của centroid.

## Hai hướng tiếp theo cần thiết kế riêng

- **Exposure-cluster sandwich:** thử `H⁻¹ V H⁻¹` tại vị trí fit, với score theo exposure, refit Huber/nuisance và hiệu chỉnh finite-sample được định trước. Chỉ khoảng 10 exposure/epoch, score sau fit bị ràng buộc và các reference chung có thể tương quan; meat ngây thơ có thể bias, và cộng covariance reference phải giữ cross-covariance. So sánh với H profile hiện có trên các realization nhiễu **mới, seed được khóa trước**, sau đó xác nhận trên field độc lập; báo failure, bias, coverage 50/68/95 và diện tích trên cùng denominator.
- **Parametric bootstrap full-refit:** từ mô hình fit được bằng dữ liệu quan sát, sinh nhiễu mới và fit lại cả centroid, flux, nuisance, các điểm khởi tạo và hai vòng IRLS; nếu muốn uncertainty tổng thì mô hình hóa lại registration/reference chung. Chi phí tính lớn; sai đặc tả PSF/SED, residual sky, mode và bootstrap plug-in vẫn có thể gây undercoverage. Cần khóa seeds, số inner/outer, ngưỡng và thời gian trước, kiểm tra trên realization mới và các field chưa mở, báo đầy đủ thất bại và diện tích.

Quan hệ lý thuyết `V = F + Σ (1/I_i)D_iᵀP_iD_i` gợi ý sandwich là một giả thuyết để thử. Phép thử ở đây không chứng minh `H⁻¹VH⁻¹` đạt coverage danh định, triệt mọi sai số, hay giải thích toàn bộ pipeline.
