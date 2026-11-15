# Giao thức phát triển covariance sandwich theo exposure

Giao thức này so sánh ba covariance trên **cùng vị trí fit** của candidate 0.10 đã khóa. Không thay centroid, không chọn mô hình từ kết quả chưa xem và không có promotion khoa học từ việc tự so với baseline. Đây là phép thử phát triển trên ba trường đã mở, không phải validation thiên văn hay tái đo WISE 0855.

## Candidate, score và điều kiện hỗ trợ

Mỗi draw fit lại toàn bộ candidate padded: năm khởi tạo, hai vòng Huber IRLS, flux/nền/hàng xóm nuisance, mask/WCS, bounds và common single-source quality reference của 0.10. Chỉ sau fit, với trọng số IRLS cuối được giữ cố định, tại vị trí candidate lấy cho từng exposure `u_i = ∂[r_iᵀr_i/2]/∂x` bằng sai phân trung tâm bước 0,002 sky pixel. Residual đã profile amplitude nguồn và project plane cùng hàng xóm, nên score bao gồm ảnh hưởng của nuisance profile; không thay bằng `amplitude² × Fisher`. Song song tính `J_iᵀr_i` bằng sai phân residual, lưu chênh so với score scalar để kiểm tra số học.

Tính Hessian quan sát `H = Σ_i ∂²[r_iᵀr_i/2]/∂x∂xᵀ` tại các bước 0,002 và 0,004 sky pixel; thịt `B = Σ_i u_i u_iᵀ`, không trừ mean score. Ứng viên là `C_sand = (N/(N−2)) H⁻¹ B H⁻ᵀ` với `N` là số exposure native, tính riêng từng epoch. Tên đúng của thừa số là **CR1p**, với `p=2` đếm hai tham số centroid đã profile. [Tài liệu clubSandwich](https://jepusto.github.io/clubSandwich/reference/vcovCR.html) mô tả dạng `m/(m−p)`; ở đây đó là lựa chọn empirical định trước, không phải hiệu chỉnh chính xác cho số nuisance riêng từng frame, Huber hoặc reference tương quan. N=10 cho hệ số 1,25. Không điều chỉnh hay tune hệ số theo kết quả.

Trạng thái supported đòi tối thiểu 8 exposure ID phân biệt/epoch; solver thành công, vị trí không sát biên, rank point=2; Hessian 0,002 và 0,004 thay đổi tương đối Frobenius ≤5%; `H`, `B`, `C_sand` dương xác định với eigenvalue nhỏ nhất/lớn nhất >1e-10. Không dùng giả nghịch đảo để che rank thiếu. Nếu không đạt, lưu lý do và không tính ellipse sandwich. Tính toán này không lấy đạo hàm qua việc cập nhật IRLS weights, không bảo đảm hai vòng IRLS đã hội tụ, và không bao gồm tương quan do reference chung. Khoảng 10 exposure là ít cluster; giá trị p và hệ số CR1p không tạo bảo đảm hữu hạn mẫu. Tổng score, tổng norm score, sai số scalar so với residual-Jacobian, Hessian, meat, mỗi score và lý do unsupported đều được lưu. Không cộng hệ số χ² vào sandwich; GN và profile-H dùng nguyên quy tắc `max(1, reduced χ²)` của candidate frozen, nên khác biệt này phải nêu khi diễn giải.

Để nhìn mode mà không sửa vị trí, sau fit chạy riêng năm khởi tạo trên **mục tiêu với final weights cố định**, không cập nhật IRLS; lưu chi², nghiệm, số mode cách nhau >0,15 sky pixel, start failure và trường hợp nghiệm cố định có chi² thấp hơn điểm candidate hơn 1e-4. Những phép này là chẩn đoán cuối, không thay point estimator hoặc biến kết quả thành fit full-IRLS mới.

## Các case và mẫu số

Ba trường `w350p35`, `w090p10`, `w210m20`, patch 1, hai case: SNR/frame 2 đứng yên và SNR/frame 4 dịch `[0.6, 0.05]` sky pixel. Truth giữ `source_image` nearest frozen, còn model dùng target padded: đây là mismatch đã biết, không phải chứng nhận PSF vật lý. Nguồn tiêm giữ amplitude mỗi exposure do `injected_frames` tính; không thêm source shot noise.

Mỗi case có **128 draw Gaussian mới** theo variance native ban đầu và seed riêng cho field/case. Seed lấy 64 bit đầu big-endian của SHA-256 của chuỗi `sandwich-development.1|field|integer_snr|motion_components`, trong đó motion components dùng định dạng `.8g`, nối bằng dấu phẩy; thiết kế lưu seed dưới dạng chuỗi thập phân để không mất chính xác 64 bit. Các seed mới khác seed cũ 20261030; trong mỗi draw, GN, H và sandwich dùng cùng một point fit và cùng nhiễu. Cùng field/exposure vẫn chỉ là ba geometry trời đã mở, không phải 768 field độc lập. Ngoài ra có sáu kiểm tra ảnh nền gốc đã tiêm nguồn, giữ riêng khỏi 128 draw Gaussian của từng case.

Vector sai số là fitted displacement trừ truth, đổi sang east/north arcsec. Với mỗi phương pháp, báo riêng:

1. `centroid_only`: tổng covariance hai fit epoch, đúng với generator điều kiện giữ registration offsets cố định.
2. `plus_registration`: cộng covariance đăng ký frozen để tham chiếu pipeline cũ. Generator không sinh realization lỗi registration; không gọi coverage của nhánh này là nominal total coverage hay kiểm định sai số registration.

Cho từng field/case lưu toàn bộ attempt, point numeric/accepted, rank, boundary, mode, failure và support từng phương pháp. Báo riêng all attempts, numeric, accepted, common-supported, common-accepted; trong mỗi tập ghi cả denominator ellipse thực sự có covariance. Ghi bias vector, RMS/P90 lỗi của mọi fit numeric trong tập, ellipse 50/68/95% có threshold χ²₂ lần lượt 1,386294361, 2,278868566, 5,991464547, số chứa truth, denominator và CI Wilson 95% của tỉ lệ từng case; CI là độ bất định MC của draw trong case, không hàm ý độc lập giữa fields hoặc bảo đảm ellipse. Ghi median diện tích ellipse 68%, median và P90 bán trục lớn. Báo unsupported/reason theo phương pháp và số fit/mode thất bại; không bỏ trường hợp lỗi khỏi denominator attempt.

## Khóa và chạy sau review

```powershell
.venv/Scripts/python.exe -m unittest tests.test_exposure_sandwich -v
.venv/Scripts/python.exe -m scripts.run_sandwich_study --design
# Sau khi commit nguồn, test, tài liệu và design đã hash:
.venv/Scripts/python.exe -m scripts.run_sandwich_study --run
# Có thể tiếp tục từng case:
.venv/Scripts/python.exe -m scripts.run_sandwich_study --run --fields w350p35 --snrs 2
```

Design hash code, tests, tài liệu, requirements, nguồn frozen, thiết kế/sản phẩm đã mở và cache baseline; `--design` từ chối ghi đè. `--run` từ chối nếu thiết kế hoặc nguồn chưa commit ở HEAD, hash khác, hoặc kết quả đã hoàn tất. Output duy nhất là `data/raw/benchmark/sandwich-development.json` bị Git bỏ qua; checkpoint sau mỗi draw, resume tái sinh RNG từ đầu và kiểm tra chuỗi draw. Không chạy dữ liệu khi tạo design. Sáu case × 128 draw cần 768 fit cặp cùng sáu case nền gốc; phép mode cuối có thêm năm lần solve trên trọng số cố định cho mỗi epoch. Chưa benchmark thực nghiệm; cần theo dõi thời gian/memory và dùng resume, không hứa runtime.

Thử nghiệm này có thể cho thấy undercoverage hoặc ellipse quá rộng, và cả hai phải được báo. Chỉ nghiên cứu độc lập đã đăng ký trước với PSF/SED/noise/registration phù hợp và trường chưa mở mới có thể xem xét promotion.
