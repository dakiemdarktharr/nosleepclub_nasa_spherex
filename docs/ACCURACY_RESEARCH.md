# Giảm sai số WISE 0855 — nghiên cứu và thử nghiệm 0.4.0

Ngày kiểm tra nguồn: 2026-10-30. Kết luận: đã bổ sung fit nhiều nguồn trên pixel gốc và phép thử A/B, nhưng **chưa chứng minh cải thiện ổn định để thay bản Gaia 0.3.0**. Không hạ sai số công bố bằng cách bỏ hạng hệ thống hoặc chọn cấu hình gần dự báo ngoài hơn.

## Bằng chứng mới

Gaia có một nguồn G≈16,31 cách neo mục tiêu khoảng 8,67″ ở MJD 61000. Đây là vị trí quang học đã lan truyền, chưa chứng minh độ sáng hay tâm quang học của nguồn tại 4,7 µm. Mô hình mới thêm các ePSF Gaia nằm trong 11 pixel lưới trời quanh mỗi vùng fit. Vị trí lân cận cố định, biên độ tự do riêng từng exposure, cùng mặt phẳng nền. SVD khử các tham số tuyến tính; chỉ centroid mục tiêu được tối ưu phi tuyến, không dùng vector dự báo làm prior. Các phép thử tổng hợp độc lập kiểm tra phục hồi centroid khi có nguồn chồng và khi ma trận nuisance có cột trùng.

Hai mô hình A/B dùng cùng stamp gốc, cờ chất lượng, noise map, ePSF và solver đa khởi tạo. Bootstrap noise 128 lượt/epoch/mô hình/cấu hình. Nguồn thật với phổ rộng: một nguồn cho vector (Đông, Bắc) = (−3,268; +0,431)″; nhiều nguồn cho (−3,035; +0,107)″, độ dài 3,037″. **σ noise chiếu theo vector tăng từ 0,495″ lên 0,701″.** Những số này chưa gồm sai số frame, ePSF hoặc vị trí hàng xóm, nên không so trực tiếp với σ tổng 0,52″ của bản Gaia.

12 vị trí mới được ghi trong `web/data/joint/protocol.json` trước khi chạy, ngoài tám vùng của bản trước. Mỗi vùng có hai độ sáng và hai vector tiêm: [0;0] và [0,6;0,05] pixel. Tổng cộng 48 lượt/phương pháp/cấu hình, 192 phép phục hồi. Không chọn tham số bằng kết quả các vùng này. Bây giờ đã xem kết quả, phải xem các vùng này là dữ liệu phát triển cho lần tiếp theo.

| Phổ | Độ sáng | RMS một nguồn | RMS nhiều nguồn | Hợp lệ một / nhiều |
|---|---:|---:|---:|---:|
| Rộng | 0,5× | 1,699″ | 1,572″ | 22/24 · 24/24 |
| Rộng | 1× | 1,016″ | 1,336″ | 24/24 · 24/24 |
| Chặt | 0,5× | 2,128″ | 2,572″ | 24/24 · 23/24 |
| Chặt | 1× | 1,353″ | 1,137″ | 24/24 · 22/24 |

RMS ở bảng chỉ tính fit thành công, không chạm biên; không được bỏ qua cột số hợp lệ. Các lần tiêm trên cùng vùng chia sẻ nền và noise; hai cấu hình phổ cũng chia sẻ exposure. Không thêm shot noise nguồn; dùng cùng họ ePSF để tiêm và fit. Đây là chẩn đoán có điều kiện, chưa phải completeness, false-positive rate hay kiểm chứng độc lập sai số hệ thống.

So sánh ghép cặp **chỉ các lượt cùng hợp lệ** khắc phục một phần khác biệt mẫu số: rộng 0,5× có RMS 1,699″ → 1,630″ (22 cặp), cải thiện 4,06%; rộng 1× xấu hơn 31,49%. Bootstrap hậu kiểm 2.000 lượt theo **vùng không gian**, không coi từng injection là độc lập: khoảng 95% của phần trăm cải thiện lần lượt [0,89;7,64] và [−48,96;6,38]. Chặt 0,5× xấu hơn 26,65%; chặt 1× tốt hơn 2,99% trên 22 cặp, nhưng có thêm hai lỗi/biên. Chỉ 11–12 vùng, mẫu có điều kiện và nhiều phép so sánh: các khoảng này không phải đảm bảo thống kê hay phép kiểm định xác nhận phát hiện.

Sản phẩm: [broad.json](../web/data/joint/broad.json), [strict.json](../web/data/joint/strict.json), [summary.json](../web/data/joint/summary.json). Giữ nguyên dữ liệu, FITS và hash của bản 0.3.0. Mỗi kết quả mới có hash mã nguồn, catalog và phân tích Gaia cha.

## Nghiên cứu nguồn gốc và quyết định

1. **Khớp cảnh nhiều nguồn trước khi xếp hạng bằng AI.** [Tài liệu Spectrophotometry của IRSA](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html) mô tả việc fit đồng thời bạn đồng hành để giảm ảnh hưởng blending. Công cụ chính thức này giữ vị trí cố định và chỉ fit flux; phần tối ưu centroid trong demo là triển khai riêng, chưa được IRSA xác nhận. Đã triển khai thử nghiệm; chưa bật mặc định vì bảng A/B chưa đạt.

2. **Catalog sâu có đánh đổi.** [Huai et al., Simulating Spectral Confusion in SPHEREx Photometry and Redshifts](https://arxiv.org/abs/2510.01410) mô phỏng cả confusion từ nguồn không có trong catalog và blending giữa nguồn đã biết. Độ sâu catalog làm thay đổi cả hai; thêm mọi nguồn không tự động tối ưu. Bài nghiên cứu chủ yếu về photometry/redshift, không cung cấp cam kết sai số centroid cho WISE 0855. CoChat tìm được bản tạp chí DOI [10.3847/1538-4357/ae472b](https://doi.org/10.3847/1538-4357/ae472b); đã đối chiếu nội dung với bản tác giả arXiv. Truy vấn CoChat rộng ban đầu có kết quả lạc đề, chỉ giữ bài sau khi xác minh chính xác tiêu đề.

3. **ePSF cần đúng pixel và vị trí detector.** [Anderson & King 2000](https://arxiv.org/abs/astro-ph/0006325) giải thích ePSF tích hợp đáp ứng pixel và tính biến đổi không gian. Các mức chính xác HST trong bài không chuyển được sang SPHEREx. [Notebook ePSF chính thức](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/) cung cấp cách truy xuất calibration SPHEREx. Hiện demo chọn zone gần nhất; nội suy zone, perturbation ePSF theo exposure và kiểm tra phụ thuộc subpixel là các bước cần đánh giá, chưa tuyên bố đã làm.

4. **Noise map có thể phụ thuộc chính dữ liệu đang fit.** [Tài liệu tác giả tractorjax-spherex: Backgrounds & systematics](https://spherex-photometry.readthedocs.io/en/latest/backgrounds_systematics.html) lưu ý VARIANCE phụ thuộc observed count rate và có thể gây weight-noise bias cho nguồn mờ. Đây là giả thuyết cần kiểm tra với sản phẩm/read-noise thực tế. Chưa thay variance bằng hằng số hoặc công thức tự đặt. Nền theo CWAVE có thể hữu ích, nhưng ví dụ He I 1,083 µm không phải bằng chứng trực tiếp cho detector D6 ở 4,7 µm. Khóa mô hình nền bằng vùng phát triển, giữ vùng kiểm chứng chưa mở.

5. **Có QR3 để kiểm tra hiệu chuẩn.** [Mission page IRSA](https://irsa.ipac.caltech.edu/Missions/spherex.html) và [Data Products chính thức](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/) xác nhận QR3 bắt đầu phát hành tháng 9/2026. Đây là hướng ưu tiên trước khi cố tối ưu cực hạn QR2. Chưa xác nhận QR3 có đúng exposure WISE 0855 cần dùng, chưa tự thay dữ liệu hoặc gộp phiên bản. Cần truy vấn footprint, pin calibration/hash, so QR2/QR3 cùng exposure trước, rồi mới thêm epoch.

6. **Tách precision và accuracy.** Frame Gaia ổn định không loại bỏ bias do photocentre, blending hay phổ của một brown dwarf rất đỏ. Mức 0,52″ là ngân sách có điều kiện của bản trước, trong khi các phép tiêm có sai lệch lớn hơn. Thêm một mô hình làm σ tăng có thể phản ánh đúng mất thông tin do blending; không coi đó là lỗi cần ép giảm.

## Milestone tiếp theo và điều kiện đạt

Ưu tiên khảo sát QR3 cùng exposure; đối chiếu catalog hồng ngoại phù hợp như CatWISE/AllWISE/Legacy Survey với epoch và proper motion rõ ràng; dùng catalog để chọn nguồn nuisance có căn cứ IR. Sau đó đánh giá nội suy ePSF và mô hình nền/variance trên các vùng đã mở. Không chọn mô hình theo độ gần vector Luhman.

Khóa pipeline, điều kiện loại nguồn và lựa chọn phổ trước khi mở **tối thiểu 30 vùng mới**, cách các stamp cũ đủ xa. Báo lỗi/biên, vector bias, RMSE, paired comparison và coverage theo độ sáng/mật độ nguồn. Chỉ thay mặc định nếu RMSE giảm ở cả 0,5× và 1×, số lỗi không tăng và coverage không xấu hơn; bootstrap theo vùng phải hỗ trợ kết luận, không chỉ điểm ước lượng. Kiểm tra mismatch ePSF khi tiêm khác mô hình fit, thêm noise nguồn có căn cứ đơn vị/calibration và nhiễu tương quan thiết bị.

Sau khi nền đo ổn định, thêm epoch thứ ba, fit motion + parallax với baseline phù hợp; hai epoch không tự giải được các tham số này. Vision model dùng để xếp hạng cảnh và chuyển người duyệt sau các gate vật lý, đánh giá train/test theo vùng trời, không dùng LLM để thay covariance.

## Tái tạo

```powershell
.\.venv\Scripts\python.exe -m scripts.joint_motion --configuration broad
.\.venv\Scripts\python.exe -m scripts.joint_motion --configuration strict
.\.venv\Scripts\python.exe -m scripts.summarize_joint
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Hai lệnh đầu cần cache cutout rộng và centroid Gaia của milestone trước. Lệnh summary/test đọc các sản phẩm nhỏ đã commit.
