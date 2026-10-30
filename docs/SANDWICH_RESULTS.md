# Kết quả phát triển covariance sandwich theo exposure

**Sandwich chưa đạt cơ sở promotion.** Trong ba case SNR 2/frame, ellipse 68% centroid-only chứa truth lần lượt 73/128, 71/128 và 65/128 draw; profile Hessian đạt 76/128, 73/128 và 63/128. Sandwich có diện tích trung vị lớn hơn Gauss–Newton ở cả sáu case, nhưng không cải thiện nhất quán coverage so với profile Hessian. Đây là phép thử có điều kiện trên ba trường đã mở, không phải hiệu chuẩn độc lập hay xác nhận thiên văn.

Candidate dùng đúng point estimator padded 0.10; mỗi draw chỉ fit vị trí một lần rồi tính cả ba covariance tại điểm đó. Truth vẫn dùng nearest ePSF frozen, do đó có mismatch đã biết; noise Gaussian native dùng seed mới cho từng field/case, không có source shot noise. Trọng số Huber IRLS cuối được giữ cố định khi tính score và Hessian; không tính đạo hàm qua IRLS, uncertainty reference chung hoặc tương quan giữa exposure. CR1p `N/(N−2)` chỉ là hiệu chỉnh empirical với hai tham số centroid đã profile, không bảo đảm đúng khi số exposure ít hoặc nuisance lớn. GN và profile-H vẫn có inflation `max(1, reduced χ²)` của candidate, còn sandwich không có inflation này. Xem [giao thức](SANDWICH_PROTOCOL.md).

## Coverage centroid-only trên từng field/case

Mỗi bộ ba là số ellipse chứa truth tại mức danh nghĩa **50 / 68 / 95%**. Có 128/128 point numeric và 128/128 covariance supported cho cả ba phương pháp ở mỗi case; vì vậy tập all attempts, numeric và common-supported trùng nhau ở bảng này. Mỗi hàng có 128 realization nhiễu, **không phải 128 field trời độc lập**. Các ngưỡng χ² dùng để mô tả ellipse, không bảo đảm coverage danh nghĩa.

| Field | SNR/frame | GN: 50/68/95 | Profile H: 50/68/95 | Sandwich: 50/68/95 | Wilson 95% cho sandwich 68% |
|---|---:|---:|---:|---:|---:|
| w350p35 | 2 | 38 / 54 / 97 | 52 / 76 / 110 | 56 / 73 / 105 | 48,4–65,3% |
| w350p35 | 4 | 60 / 88 / 120 | 60 / 94 / 123 | 66 / 85 / 118 | 57,9–74,0% |
| w090p10 | 2 | 41 / 64 / 98 | 54 / 73 / 111 | 52 / 71 / 104 | 46,8–63,8% |
| w090p10 | 4 | 50 / 81 / 114 | 58 / 84 / 116 | 57 / 86 / 115 | 58,7–74,7% |
| w210m20 | 2 | 43 / 49 / 90 | 48 / 63 / 108 | 45 / 65 / 104 | 42,2–59,3% |
| w210m20 | 4 | 57 / 78 / 113 | 59 / 88 / 119 | 60 / 87 / 117 | 59,5–75,4% |

Wilson là uncertainty Monte Carlo cho các draw trong từng case; không tính dependence giữa field, không điều chỉnh việc xem nhiều nhóm, và không cho phép suy rộng quần thể. Những CI này không phải uncertainty thiên văn tổng.

Các mẫu accepted và common-accepted cũng trùng nhau vì cả ba covariance đều supported. Bảng sau báo **cùng ba mức** trên đúng mẫu accepted; trường hợp quality bị từ chối vẫn được giữ trong mẫu all attempts ở trên.

| Field | SNR/frame | Accepted / attempts | GN: 50/68/95 | Profile H: 50/68/95 | Sandwich: 50/68/95 |
|---|---:|---:|---:|---:|---:|
| w350p35 | 2 | 127 / 128 | 38 / 54 / 97 | 52 / 76 / 110 | 56 / 73 / 105 |
| w350p35 | 4 | 128 / 128 | 60 / 88 / 120 | 60 / 94 / 123 | 66 / 85 / 118 |
| w090p10 | 2 | 124 / 128 | 40 / 63 / 95 | 53 / 72 / 108 | 51 / 70 / 101 |
| w090p10 | 4 | 128 / 128 | 50 / 81 / 114 | 58 / 84 / 116 | 57 / 86 / 115 |
| w210m20 | 2 | 127 / 128 | 43 / 49 / 90 | 48 / 63 / 108 | 45 / 65 / 104 |
| w210m20 | 4 | 128 / 128 | 57 / 78 / 113 | 59 / 88 / 119 | 60 / 87 / 117 |

Bản JSON cũng ghi 50/68/95% và CI cho cả ba phương pháp với **centroid + registration**, theo từng selection. Registration offsets được giữ cố định khi sinh noise; kết quả cộng covariance registration chỉ là phép so sánh pipeline, không phải kiểm định coverage tổng. So với centroid-only, ở tập numeric chỉ có ba thay đổi số đếm: w350p35 SNR 2 profile-H mức 50% từ 52 lên 53; w350p35 SNR 4 sandwich mức 68/95% từ 85/118 lên 86/119; w210m20 SNR 4 GN mức 50% từ 57 lên 58.

## Diện tích và sai số điểm

Diện tích trung vị ellipse 68% centroid-only, đơn vị arcsec², và RMS sai số vector trên 128 point numeric:

| Field | SNR/frame | GN | Profile H | Sandwich | RMS point (″) |
|---|---:|---:|---:|---:|---:|
| w350p35 | 2 | 6,071 | 8,470 | 8,231 | 1,959 |
| w350p35 | 4 | 2,010 | 2,217 | 2,221 | 0,771 |
| w090p10 | 2 | 5,978 | 8,866 | 9,961 | 1,971 |
| w090p10 | 4 | 2,094 | 2,369 | 2,406 | 0,874 |
| w210m20 | 2 | 5,823 | 8,081 | 8,605 | 1,994 |
| w210m20 | 4 | 2,104 | 2,378 | 2,454 | 0,865 |

Các covariance dùng **cùng point**, nên không có cải thiện accuracy vị trí nào do sandwich. JSON ghi bias east/north, P90 lỗi, diện tích, bán trục lớn median/P90, Wilson CI và support theo mọi selection. Diện tích không mô tả đầy đủ hình dạng: ví dụ w350p35 SNR 2, sandwich có median bán trục lớn 2,257″, so với 1,821″ của profile H dù diện tích sandwich nhỏ hơn một chút.

Có 24 epoch-fit đa mode theo phép thử năm start cuối với trọng số cố định (13 w350p35 SNR 2, 3 w090p10 SNR 2, 8 w210m20 SNR 2); hai start không thành công ở w350p35 SNR 2. Một epoch w090p10 SNR 2 draw 35 có start tìm Δχ² = −0,20516 so với point ở trọng số cuối; draw này bị quality reject. Đây không khẳng định full-IRLS tại mode khác tốt hơn. Không có point boundary hoặc fit exception trong 768 draw. Sai khác tương đối scalar score so với `Jᵀr` lớn nhất khoảng 5,24e−5.

## Sáu phép thử trên ảnh nền gốc

Đây là một lần tiêm trên nền gốc cho mỗi case, **không** thuộc các draw Gaussian; bảng cho sai số vector và q centroid-only ở cùng point candidate. Giá trị baseline là point model frozen cũ; không so sánh coverage từ sáu số này.

| Field | SNR/frame | Lỗi baseline → candidate (″) | q GN / H / sandwich |
|---|---:|---:|---:|
| w350p35 | 2 | 2,5895 → 2,6121 | 8,132 / 5,430 / 3,519 |
| w350p35 | 4 | 1,1922 → 1,1897 | 5,482 / 5,242 / 9,009 |
| w090p10 | 2 | 1,3384 → 1,4012 | 2,039 / 1,451 / 1,095 |
| w090p10 | 4 | 0,5436 → 0,5499 | 1,068 / 0,849 / 0,518 |
| w210m20 | 2 | 1,7322 → 1,7642 | 3,821 / 1,512 / 1,430 |
| w210m20 | 4 | 0,4438 → 0,4493 | 0,635 / 0,324 / 0,254 |

Cả sáu candidate ảnh gốc accepted; hai vị trí epoch, vector sai số và GN covariance cộng registration khớp cache f138. Với 768 draw dùng seed mới không có point-cache cũ để đối chiếu từng draw; tính bất biến point giữa ba covariance đến từ cách thực thi đã khóa, không phải replay từng draw với một fitter khác.

## Kiểm toán và tái lập

[development-summary.json](../web/data/sandwich/development-summary.json) chứa đủ 768 attempt, mọi trạng thái quality, vị trí, covariance/q, scores từng exposure, Hessian, meat, mode/start và metadata. Array per-frame và score được mô tả trong `record_schema`; dữ liệu không làm tròn. Tệp 8,2 MB so với raw 25,3 MB vì giữ toàn bộ bằng chứng, không chỉ các thống kê. Source, thiết kế, URL và hash nguồn được giữ kèm sản phẩm.

[overview.json](../web/data/sandwich/overview.json) là bản gọn cho giao diện: gồm sáu summary đã kiểm toán, provenance theo field, các phép thử nền gốc riêng và các mode có objective thấp hơn. Nó không chứa mảng 768 draw; hash và kích thước báo cáo đầy đủ được ghi trong `provenance` để đối chiếu.

Builder kiểm hash commit `3995f2e6d0279fda8bedff2b47af1d53129dcfef`, nguồn và thiết kế; kiểm seed; tính lại meat từ score, Hessian, covariance CR1p, sai số vector, q, covariance centroid/registration, mode-count, mọi selection/coverage/Wilson/diện tích và đối chiếu summary raw. Nó đối chiếu riêng sáu ảnh gốc với cache trước. Tổng amplitude không nằm trong epoch record công khai của fitter frozen, nên numeric-valid được giữ từ kết quả gốc thay vì tuyên bố tái kiểm toàn bộ gate từ các giá trị tóm tắt. Các unit tests đối chiếu raw khi cache còn và tái tính độc lập các đại lượng chính.

```powershell
.venv/Scripts/python.exe -m scripts.build_sandwich_report
.venv/Scripts/python.exe -m unittest tests.test_sandwich_product tests.test_exposure_sandwich -v
```

- Raw report SHA-256: `9a6fa4ef30837ef4fee4b906b742d98b14747c7efb8ec93bebfe813fe82fd578`.
- Thiết kế SHA-256: `fe4ea22755062716f7aeea6d6240e0dffdb35fc7c70159e86424f8667081a386`.

Bước tiếp theo nên dùng kết quả này để thiết kế trước một kiểm định về robust weights, mode và registration, với realization mới và tiêu chí sai số/coverage/diện tích rõ ràng; sau đó mới thử trên field độc lập chưa mở. Không biến kết quả development thành phát hiện WISE 0855 hay chứng nhận khoa học.
