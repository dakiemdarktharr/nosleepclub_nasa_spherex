# WISE 0855: mở rộng trường sao và kiểm chứng với Gaia DR3

Ngày thực hiện: 30/10/2026. [Demo đang chạy](http://127.0.0.1:8766/), [kết quả máy đọc và provenance](../web/data/gaia/results.json), [bản đồ sao](../web/data/gaia/map.json), [research và bibliography](GAIA_RESEARCH.md).

## Kết quả và ý nghĩa

Frame astrometry ít thay đổi khi đổi sao tham chiếu. Ngân sách sai số theo mô hình giảm ở cấu hình phổ rộng, nhưng các thử nghiệm trên nền ảnh thật còn cho sai lệch đáng kể. **Chưa xác nhận chuyển động thiên thể hoặc độ chính xác hệ thống của WISE 0855.**

| Đại lượng | Phổ chặt, cấu hình chính | Phổ rộng, kiểm tra độ nhạy |
| --- | ---: | ---: |
| Exposure mỗi epoch | 2 | 10 |
| Đông / Bắc đo được | −2,86″ / +1,07″ | −3,26″ / +0,43″ |
| Độ dài vector ± sai số có điều kiện | 3,06″ ± 0,99″ | 3,29″ ± 0,52″ |
| Thay đổi vector so với bản trước Gaia | 0,21″ | 0,40″ |
| RMS 7 sao giữ ngoài fit, sau trừ Gaia motion | 0,27″ | 0,17″ |
| Đổi chéo tập sao: thay đổi vector | 0,16″ | 0,04″ |
| Bỏ từng sao: thay đổi lớn nhất, 14/14 lượt chạy được | 0,09″ | 0,17″ |
| Thử affine: thay đổi vector | 0,04″ | 0,10″ |
| Chênh vector dự báo ngoài | 1,70″ | 1,21″ |

Không chọn cấu hình rộng làm cấu hình chính vì sai số nhỏ hơn. Hai cấu hình và quy tắc phổ được giữ từ bước trước, có dùng chung exposure, nên không phải hai kiểm chứng độc lập. S/N khẩu độ phổ rộng trước/sau hiện là 7,68 / 7,42, so ảnh đơn tốt nhất 4,90 / 4,91; phổ chặt là 3,18 / 4,50 so 2,99 / 4,60. Đây là S/N có điều kiện tại vị trí fit, với mask và coverage tương ứng, chưa phải độ tin cậy phát hiện mù hoặc tổng thông lượng.

## Dữ liệu và chọn sao

Giữ đúng 20 exposure trong cấu hình rộng cũ, không thêm thời điểm hay đổi phiên bản calibration. Tải cutout rộng 0,32° thay 0,12°, cùng center; raw có URL, observation ID, SHA-256 và WCS native. Dùng ePSF chính thức D6 oversampling 5 và CWAVE/CBAND đã ghim ở bước trước. [IRSA khuyến nghị ePSF này cho cả QR2](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/).

Truy vấn `gaia_dr3_source` qua `https://irsa.ipac.caltech.edu/TAP/sync`: cone 0,25°, G<18,5, trả 675 nguồn. ADQL đầy đủ, hash VOTable và các trường covariance được lưu trong report. `source_id` giữ dạng chuỗi khi xuất JSON để tránh mất chính xác số nguyên 64 bit trong JavaScript.

Trước khi fit lại mục tiêu, chọn sao bằng các quy tắc cố định trong `RULES`:

- Có giải astrometry 5/6 tham số, RUWE≤1,4, ≥9 visibility periods; không có cờ duplicated/non-single-star, `ipd_frac_multi_peak`≤2.
- Giới hạn |proper motion|≤300 mas/năm, |parallax|≤20 mas để giữ xấp xỉ lan truyền bậc nhất phù hợp; đây là lựa chọn của phép thử, không phải tiêu chuẩn Gaia phổ quát.
- Ghép peak SPHEREx và Gaia đã lan truyền trong 1 pixel; không có hàng xóm Gaia G<18,5 trong 18″ hoặc peak SPHEREx trong 3,5 pixel. Loại vùng mục tiêu bán kính 8 pixel và sao sát rìa.
- Fit ePSF native từng sao/từng exposure: S/N≥7, reduced chi-square≤3, hội tụ và không chạm biên. Cần ≥70% trong 20 exposure hợp lệ và ≥3 exposure ở mỗi epoch.

Có 85 ghép cô lập ban đầu; 21 nguồn qua kiểm tra native. Report giữ audit ghép, số frame hợp lệ, lý do loại của từng nguồn và từng frame của nguồn được chọn. Chọn trải các góc phần tư rồi chia bằng hash source ID cố định: **14 sao căn chỉnh, 7 sao giữ ngoài fit**. Trên mỗi exposure thực tế dùng 12–14 sao ở cấu hình rộng; đổi chéo còn ít nhất 6 sao. Không dùng vector WISE 0855 hoặc độ giống dự báo để chọn sao.

Gaia DR3 có reference epoch 2016.0 theo TCB. Lan truyền proper motion có cos Dec và parallax dùng vị trí barycentric Trái Đất; giữ ma trận covariance 5×5 và các correlation. Thông tin trường gốc có trong [schema Gaia/DPAC tại AIP](https://gaia.aip.de/metadata/gaiadr3/gaia_source/). Chưa mô hình perspective acceleration, Gaia global systematics, hoặc vị trí vệ tinh thay cho Trái Đất; với tập sao chuyển động/parallax nhỏ đã giới hạn, các hạng này nhỏ hơn mức sai số SPHEREx hiện tại.

## Fit frame, kiểm tra và ngân sách sai số

Fit translation theo GLS cho từng exposure từ hiệu centroid native trừ vị trí Gaia đã lan truyền, có covariance centroid và Gaia, thêm floor 0,01 pixel cho sao tham chiếu. Tăng covariance khi chi-square>1. Fit WISE 0855 riêng từng epoch trên pixel gốc, giữ biên độ và mặt phẳng nền riêng từng exposure; không buộc vector theo dự báo ngoài.

Đổi chéo tập sao, bỏ lần lượt từng sao training và thử affine sáu tham số đều chạy được. Khi đổi calibration, giữ nguyên tập pixel và ePSF của stamp mục tiêu; affine được đưa vào cả tâm và Jacobian cục bộ. Nhờ vậy kiểm tra độ nhạy không trộn với việc thêm/bớt pixel rìa khi cắt lại stamp.

Ngân sách covariance của hiệu vị trí gồm:

1. Noise centroid: covariance Jacobian, tăng theo chi-square, đối chiếu 128 mô phỏng noise Gaussian/epoch.
2. Calibration: truyền covariance qua influence Gauss–Newton của từng exposure trên tập pixel cố định. Tổng influence của một translation chung phải bằng −I; kiểm thử kiểm tra tính bất biến tọa độ này. Bootstrap 256 lần với số lần chọn sao được ghép cặp giữa hai epoch; mỗi sao có một draw Gaia 5 tham số dùng chung qua mọi exposure, giữ correlation qua thời gian. Lấy positive covariance envelope với estimate formal thay vì giảm sai số khi bootstrap nhỏ hơn.
3. Sao giữ lại: second moment của residual hiệu vị trí sau trừ Gaia motion, giữ cả mean bias và scatter. Hạng này thận trọng, có thể đếm một phần noise hai lần; chỉ có bảy sao và chúng sáng/cô lập hơn nguồn mục tiêu.

Các bootstrap calibration đều đủ 256 draw, không có draw thất bại. Sai số từng vị trí có hạng calibration và residual field riêng; sai số giữa hai epoch có tương quan, nên không lấy đơn giản tổng hai ellipse vị trí để suy ra sai số vector. Ellipse vector 68% dùng Δχ²=2,30; sai số độ dài vector là phép truyền bậc nhất theo hướng vector.

Gaia cũng góp phần vào WCS đầu vào của SPHEREx. “Giữ ngoài fit” ở đây có nghĩa không tham gia **fit cục bộ của demo**, không phải một catalog hoặc bộ quan sát độc lập với hiệu chuẩn nhiệm vụ. Photocentre quang học Gaia và hồng ngoại có thể khác nhau do màu hoặc nguồn lân cận chưa tách.

## Injection: sai số mô hình chưa đủ mô tả mọi nền ảnh

Giữ cố định tám vị trí ngoài vùng mục tiêu, tiêm nguồn đứng yên hoặc dịch chuyển (0,60; 0,05) pixel. Hai độ sáng bằng 0,5× và 1× profile biên độ từng exposure đo của WISE 0855. Không thay ảnh khoa học xuất ra, không thêm shot noise, không thay sao căn chỉnh. Dùng cùng họ ePSF để tiêm và fit; chưa đánh giá riêng sai số calibration ePSF.

| Cấu hình | Độ sáng | Kiểu nguồn | Trong ellipse 68% / 8 lượt | RMS sai lệch vector |
| --- | ---: | --- | ---: | ---: |
| Chặt | 0,5× | Đứng yên | 7/8 | 2,68″ |
| Chặt | 0,5× | Dịch chuyển | 6/8 | 1,76″ |
| Chặt | 1× | Đứng yên | 7/8 | 1,33″ |
| Chặt | 1× | Dịch chuyển | 7/8 | 0,83″ |
| Rộng | 0,5× | Đứng yên | 5/8 | 3,05″ |
| Rộng | 0,5× | Dịch chuyển | 2/8 | 2,26″ |
| Rộng | 1× | Đứng yên | 6/8 | 2,72″ |
| Rộng | 1× | Dịch chuyển | 6/8 | 1,75″ |

Tất cả lượt fit hội tụ và không chạm biên; vẫn giữ cả các sai lệch lớn. Có trường hợp fit vào photocentre trộn với nền; chi-square lớn làm tăng sai số nhưng chưa loại được bias. Đặc biệt, 2/8 ở nhóm nguồn mờ/chuyển động là dấu hiệu mô hình sai số cần kiểm tra thêm. Tám vị trí, các độ sáng/kiểu nguồn và hai cấu hình dùng chung nền; các tỷ lệ này có tương quan, không phải 64 mẫu độc lập, completeness hoặc false-positive rate đã hiệu chuẩn. Không lấy một RMS chung để gán lại sai số cho mục tiêu.

Vector phổ rộng chênh dự báo Luhman 2014 + parallax ngoài khoảng 1,21″. Report không fit lại proper motion/parallax và chưa cộng uncertainty của dự báo cũ vào phép so sánh này. Chênh lệch còn lại và injection bias là lý do tiếp tục giữ trạng thái **candidate_motion_unconfirmed**, dù frame ổn định khi đổi sao. Chưa diễn giải Mahalanobis thành Gaussian sigma hay xác suất khám phá.

## Demo và tái tạo

Web thêm hai cấu hình Gaia, bản đồ trường rộng với sao căn chỉnh/giữ lại bấm chọn được, chất lượng Gaia của từng sao, bảng CV, ngân sách sai số và toàn bộ nhóm injection. Giữ bản trước Gaia để so sánh. Download FITS/JSON có WCS, đơn vị và provenance. Native centroid được fit trước khi cross-convolution ảnh hiển thị. Source code và calibration hash có trong report; raw lớn vẫn ở thư mục ignored.

Theo lệnh trong README, sau các bước baseline/coadd chạy:

```sh
.venv\Scripts\python scripts/prepare_gaia_data.py
.venv\Scripts\python scripts/gaia_motion.py --publish
.venv\Scripts\python -m unittest discover -s tests -v
```

Không có `--publish`, script chỉ ghi kết quả vào cache xử lý; `--references-only` dừng sau chọn/đo sao. Cache centroid có fingerprint theo các hàm xử lý, rules, input manifest và dependencies; sửa phép đo làm cache mất hiệu lực. 31 kiểm thử offline bao gồm lan truyền Gaia, correlation, GLS/affine và dấu influence, covariance budget, audit split, provenance/phiên bản FITS và các kiểm tra baseline cũ. Kiểm thử phần mềm qua không phải xác nhận thiên thể.

## Bước tiếp theo và điều kiện hoàn thành

**Milestone tiếp theo: mô hình nhiều nguồn trên pixel gốc cho WISE 0855 và nền lân cận**, giữ frame Gaia vừa kiểm tra. Dùng danh sách nguồn hồng ngoại bổ sung, fit chung nuisance/background theo exposure, đánh giá phụ thuộc màu và đáp ứng phổ; chưa dùng source ID Gaia như danh sách đầy đủ của các nguồn hồng ngoại.

Điều kiện hoàn thành: so single-source/joint-source trên cùng dữ liệu; tách tập injection dùng phát triển và tập giữ lại theo vị trí/vùng trời; báo bias, failure/boundary và coverage ellipse ở nhiều độ sáng. Kiểm tra nominal 68% có phù hợp khoảng tin cậy lấy mẫu trên tập giữ lại, cùng bias so với sai số công bố. Chỉ nâng trạng thái khoa học khi các hạng hệ thống có ngân sách rõ và thêm epoch đủ phân biệt proper motion/parallax. Sau đó mới xây vision model xếp hạng ứng viên trên benchmark không rò rỉ vùng trời.

Ghi nguồn Gaia: dữ liệu từ sứ mệnh Gaia của ESA, do DPAC xử lý. Kinh phí từ các tổ chức quốc gia tham gia Gaia Multilateral Agreement; xem [hướng dẫn ghi nguồn](https://gaia.aip.de/metadata/gaiadr3/gaia_source/).
