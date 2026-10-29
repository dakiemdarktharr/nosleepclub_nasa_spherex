# WISE 0855: cộng ảnh theo epoch và astrometry độc lập

Ngày thực hiện: 30/10/2026. [Mở demo](http://127.0.0.1:8766/). Các số đầy đủ, covariance, observation ID, URL và hash nằm trong [results.json](../web/data/motion/results.json), [manifest web](../web/data/manifest.json) và evidence JSON của từng cấu hình.

## Kết quả hiện tại

Đã đo được dấu hiệu dịch chuyển về phía tây của nguồn trong vùng WISE 0855. Hai vị trí được fit độc lập trên pixel gốc, không buộc theo vector chuyển động cũ. Chưa xác nhận chuyển động thiên thể từ phép đo này vì ngân sách sai số hệ thống còn chưa hoàn chỉnh.

| Cấu hình | Ảnh mỗi epoch | S/N ảnh đơn tốt nhất → cộng, trước | S/N ảnh đơn tốt nhất → cộng, sau | Đông / Bắc | Độ dịch chuyển ± sai số theo mô hình | RMS sao giữ lại |
| --- | ---: | ---: | ---: | --- | --- | --- |
| Phổ chặt, cấu hình chính | 2 | 2,55 → 2,60 | 4,66 → 4,57 | −3,08″ / +1,05″ | 3,25″ ± 1,05″ | 0,53″, 3 sao |
| Phổ rộng, kiểm tra độ nhạy | 10 | 5,11 → 7,87 | 4,64 → 7,58 | −3,24″ / +0,03″ | 3,25″ ± 0,80″ | 0,66″, 4 sao |

Cấu hình chặt không tăng S/N rõ; giữ nguyên kết quả này. Hai cấu hình dùng chung một số ảnh, không phải hai lần xác minh độc lập. Cấu hình rộng được mở đầu trong web để xem lợi ích cộng ảnh, nhưng được đánh dấu rõ là kiểm tra độ nhạy.

S/N là thống kê khẩu độ tại vị trí đã fit, chưa phải độ tin cậy của phát hiện mù. Độ phủ khẩu độ trước/sau là 94,7% / 100% ở cấu hình chặt và 84,2% / 100% ở cấu hình rộng. Các ảnh đơn được so tại cùng vị trí và có thêm mặt nạ hợp lệ của ảnh cộng. Đây không phải phép đo tổng thông lượng hoặc bằng chứng biến thiên độ sáng.

## Chọn dữ liệu và phổ

- Nguồn: SPHEREx QR2, D6, 31 cutout thật trong hai cửa sổ MJD [60989, 60994) và [61151, 61157), tương ứng tháng 11/2025 và tháng 4/2026. Mỗi cutout rộng 0,12°, centered quanh vùng mục tiêu.
- Giữ IMAGE, VARIANCE, FLAGS, ZODI, native WCS và WCS detector gốc. Mask chất lượng giống baseline, vẫn giữ bit SOURCE.
- Dùng bản đồ khoa học đầy đủ CWAVE/CBAND `cal-wcs-v4-2025-254`; WCS-WAVE của baseline chỉ dành cho trực quan hóa. Dùng ePSF `cal-epsf-v1-2026-191`, oversampling 5, đã tích chập đáp ứng pixel. Theo IRSA, ePSF mới được khuyến nghị cả cho ảnh QR2.
- Chọn bước sóng tại vùng mục tiêu trong 4,55–4,94 µm. Ghép một đối một giữa hai epoch theo |Δλ| / bề rộng phổ trung bình, bằng tối ưu assignment; không nhân bản exposure. Gate chặt ≤ 0,20; gate rộng ≤ 0,50. Cấu hình được cố định trước khi fit mục tiêu.
- Hai ảnh mỗi epoch ở cấu hình chặt là hai cặp gần 4,572/4,578 và 4,606/4,611 µm. Cấu hình rộng có 10 cặp trải đến khoảng 4,94 µm. Đây là cộng nhiều kênh phổ có trọng số, không phải 10 ảnh cùng bước sóng.
- Mỗi cặp dùng trọng số tỷ lệ nghịch tổng variance trung vị của hai exposure; chuẩn hóa rồi dùng **cùng trọng số phổ ở cả hai epoch**. Có chuẩn hóa cục bộ theo coverage; chỉ giữ pixel có ≥90% tổng trọng số đầu vào. Ghép tâm/bề rộng chưa đảm bảo toàn bộ đáp ứng phổ tương đương.

URL và SHA-256 của hai calibration được ghim trong `prepare_motion_data.py`; raw giữ ở `data/raw/` và không commit. Tệp hiệu chuẩn mới trong tương lai không tự thay đổi phép thử này.

## Cộng ảnh và đo vị trí

1. Trừ ZODI và nền trung vị đã sigma clip. Chiếu mỗi ảnh lên TAN 64×64, 6,15″/pixel bằng toán tử bilinear thưa, dùng bình phương trọng số để truyền variance. Thiếu support được giữ là thiếu dữ liệu.
2. Chọn sao sáng có mặt ở cả hai ảnh cộng, tránh mục tiêu và rìa. Chia xen kẽ thành tập căn chỉnh và tập giữ lại: 3/3 hoặc 4/4. Từng exposure fit ePSF cho sao căn chỉnh; cần ít nhất 2 sao có S/N ≥7 và fit không chạm biên. Chỉ hiệu chỉnh translation, không fit biến dạng cao bậc với ít sao.
3. Fit ePSF trên pixel gốc của mỗi epoch, centroid chung cho các exposure trong epoch; mỗi exposure có biên độ và mặt phẳng nền riêng. Không ép chung màu phổ hoặc thông lượng. Hai epoch dùng cùng vùng tìm kiếm 31,5 ±2,5 pixel, không dùng vector dự báo làm ràng buộc vị trí.
4. Fit nhiều điểm khởi đầu, kiểm tra hội tụ và biên. Tất cả centroid mục tiêu hội tụ và không chạm biên. Reduced chi-square khoảng 1,09–1,18. Vị trí là trung bình thời gian trong epoch; effective MJD dùng trọng số S/N² từ fit. Chưa fit chuyển động trong cửa sổ <6 ngày; ngoại suy cũ gợi ý smear <0,14″.
5. Covariance centroid từ Jacobian, tăng khi reduced chi-square >1. Kiểm tra thêm 128 mô phỏng noise Gaussian trên pixel gốc mỗi epoch/cấu hình, seed được lưu. Lấy phần tăng covariance dương từ bootstrap; không giảm sai số hình thức. Tỷ lệ fit chạm biên trong mô phỏng là 0.
6. Đo dịch chuyển của sao giữ lại bằng cùng phương pháp, độc lập với fit căn chỉnh. Thêm second moment của các residual giữ lại (gồm cả bias trung bình), cùng covariance căn chỉnh trung bình của hai epoch, vào covariance dịch chuyển mục tiêu. Hạng này có thể đếm một phần noise hai lần, được giữ theo hướng thận trọng.

| Cấu hình | Effective MJD trước / sau | RA, Dec trước (độ) | RA, Dec sau (độ) |
| --- | --- | --- | --- |
| Chặt | 60989,366953 / 61153,061990 | 133,759831; −7,242381 | 133,758970; −7,242088 |
| Rộng | 60990,692919 / 61154,178274 | 133,759818; −7,242080 | 133,758910; −7,242072 |

Đây là tọa độ theo WCS SPHEREx được căn chỉnh tương đối, chưa neo một frame astrometry ngoài. Covariance đầy đủ có trong JSON. Web hiển thị σ từng trục với hạng căn chỉnh và nửa hạng giữ lại mỗi epoch; tổng hai covariance này khớp covariance hiệu vị trí. Ellipse 68% dùng Δχ²=2,30 theo giả định Gaussian hai chiều. Sai số của độ dài vector là phép truyền bậc nhất theo hướng vector, không phải độ chính xác hệ thống tuyệt đối.

Để tính S/N khẩu độ bán kính 2,5 pixel và vành nền 4–6 pixel, trọng số khẩu độ/nền được truyền ngược qua toán tử chiếu về pixel gốc. Cách này giữ covariance do nội suy trong thống kê khẩu độ; vẫn giả định pixel gốc và các exposure độc lập. Mặt phẳng nền được khử cả với mặt nạ không đối xứng.

## Đối chiếu dự báo và đối chứng

Dự báo ngoài dùng [Luhman 2014, Tables 1–2](https://arxiv.org/pdf/1404.6501): μRA cos Dec = −8,06″/năm, μDec = +0,70″/năm, parallax 0,454″, cộng dịch chuyển barycentric Trái Đất từ ephemeris built-in Astropy. Ở cấu hình rộng, dự báo Đông/Bắc khoảng −4,47″ / +0,54″, so với đo −3,24″ / +0,03″. Đây là đối chiếu; chưa fit proper motion và parallax riêng bằng hai epoch. Dấu dự báo nét đứt trên ảnh vẫn là ngoại suy tuyến tính cũ không parallax, được ghi riêng để tránh lẫn với vector dự báo trong biểu đồ.

Mahalanobis 2 chiều của dịch chuyển so với zero là 3,18 (chặt), 4,34 (rộng). **Không chuyển thành Gaussian sigma, xác suất phát hiện hay xác nhận thiên thể**, vì sai số hệ thống và lựa chọn nguồn chưa được hiệu chuẩn đầy đủ.

Đã tiêm nguồn ePSF giả ở vị trí ngoài mục tiêu trên nền dữ liệu thật; dữ liệu hiển thị và sao căn chỉnh không bị thay đổi:

| Cấu hình | Nguồn đứng yên: vector đo (pixel) | Nguồn dịch chuyển thật (0,60; 0,05) pixel: vector đo | Sai lệch Mahalanobis đứng yên / dịch chuyển |
| --- | --- | --- | --- |
| Chặt | (0,008; −0,096) | (0,690; −0,025) | 0,87 / 1,10 |
| Rộng | (0,008; −0,145) | (0,656; −0,088) | 2,59 / 2,77 |

Nguồn đứng yên vẫn lệch 0,59″ / 0,89″. Đối chứng này chỉ có một vị trí và một mức biên độ, không thêm shot noise nguồn, dùng calibration cố định. Nó cho thấy ảnh hưởng nền/blending có thể đáng kể; không dùng kết quả một vị trí để chỉnh sai số mục tiêu cho đẹp. Chưa có benchmark completeness hoặc false-positive rate.

Đã thử đổi chéo tập sao căn chỉnh/giữ lại, nhưng thất bại vì `2025W46_1A_0090_3` không còn đủ 2 sao đạt S/N ≥7. Giữ nguyên ngưỡng và ghi lý do trong JSON/web. Đây là kiểm tra robustness **chưa đạt**, không phải một kiểm tra đã qua.

18 kiểm thử offline bao gồm hồi phục centroid nguồn đứng yên/dịch chuyển với phase pixel khác nhau, variance khẩu độ đối chiếu Monte Carlo, khử nền với pixel thiếu, dấu WCS, control PSF, hash/provenance, tập sao disjoint, covariance dương và mask highlight. Qua kiểm thử phần mềm không đồng nghĩa xác nhận chuyển động thiên văn.

## Demo và sản phẩm

Demo giữ hai cấu hình cộng ảnh và ba cặp ảnh đơn. Chấm/ellipse là phép đo; overlay dự kiến có thể bật riêng. Xem song song, kéo vạch, nhấp nháy hoặc sai khác; nhấn **Phóng vào vùng chọn** để xem dịch chuyển dưới pixel. Không có residual tự động vượt ngưỡng ở cấu hình rộng sau các gate hiện tại; centroid vùng nguồn biết trước vẫn được đo độc lập như trên. Không gắn highlight residual thành WISE 0855 khi chưa có bằng chứng danh tính.

PNG dùng cùng asinh stretch cho hai epoch, giới hạn từ median−2σ đến median+12σ của nền gộp; sao sáng có thể bị clip trên màn hình. Ảnh hiển thị được cross-convolution bằng ePSF tổng hợp cục bộ và hiệu chỉnh gain/nền. Việc này chỉ phục vụ xem và residual, **không dùng các ảnh đã làm mượt để fit centroid**. Variance output là đường chéo; covariance đầy đủ do convolution không được lưu. Điểm EMP_SCORE chỉ là điểm residual thực nghiệm.

FITS có WCS và đơn vị cho BEFORE/AFTER, VAR_BEFORE/VAR_AFTER, COADD_A/COADD_B, DIFFERENCE, EMP_SCORE và VALID. Raw, calibration và covariance centroid giữ provenance trong evidence JSON. Tái tạo bằng các lệnh trong [README](../README.md).

## Giới hạn và milestone tiếp theo

Sai số hiện là sai số có điều kiện với ePSF, noise map và tập sao đã chọn. Chưa xử lý đầy đủ sai số ePSF, pixel thiết bị tương quan, màu phổ khác nhau, blending, chuyển động riêng của sao nền hoặc sai số WCS ngoài. Bootstrap chỉ mô phỏng noise, không bao phủ các sai số này. Cả hai cấu hình có cùng ảnh thành phần nên không độc lập. Hai epoch không đủ tách proper motion/parallax.

**Milestone ngay sau khi duyệt bản này: mở rộng vùng sao tham chiếu và đối chiếu Gaia.** Mục tiêu là kiểm tra xem vector khoảng 3,25″ có ổn định khi thay đổi frame astrometry hay không. Điều kiện hoàn thành:

1. Có thêm sao tham chiếu đủ S/N, cross-match catalog và lan truyền vị trí sao đến epoch quan sát, lưu cả quy tắc loại nguồn.
2. Đổi chéo và bỏ lần lượt sao căn chỉnh chạy được trên mọi exposure, báo cả trường hợp không đạt; giữ một tập kiểm tra ngoài fit.
3. Injection nhiều vị trí/độ sáng đo bias và coverage của khoảng sai số. Chỉ nâng trạng thái tin cậy khi residual nền và thay đổi vector nằm trong ngân sách sai số đã định trước.

Tiếp đó kiểm tra toàn bộ đáp ứng phổ và thêm epoch thứ ba để thử mô hình chuyển động + parallax. Khi baseline đủ ổn định, dùng review thật và injection đã đánh giá để xây bộ nhãn, benchmark và vision model xếp hạng ứng viên cho người xử lý.

Tài liệu hiệu chuẩn chính thức: [IRSA data products](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/), [hướng dẫn ePSF](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/).
