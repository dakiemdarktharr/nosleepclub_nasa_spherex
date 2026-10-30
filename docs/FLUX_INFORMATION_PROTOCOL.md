# Giao thức chẩn đoán thông tin flux tại vị trí truth

Đây là phép thử số học có điều kiện trên các field đã mở. Nó không fit centroid, không tính RMS vị trí hoặc độ bao phủ, không dùng để xác nhận thiên văn hay chọn mô hình production. Chỉ chạy sau khi code, test, tài liệu và thiết kế được commit; `--run` kiểm tra commit và hash trước khi đọc field. Không đổi mã/sản phẩm frozen.

## Câu hỏi và phép tính

Với một exposure, whiten bằng sai số pixel gốc và chiếu bỏ nuisance `Q` gồm nền phẳng cùng các ePSF hàng xóm cố định. Tại vị trí tiêm, gọi template đã chiếu là `p`, đạo hàm theo hai trục sky pixel là `D`, `I = pᵀp`, `P = 1 − ppᵀ/I`, amplitude truth là `a`. Tính và cộng theo exposure:

- Fisher khi profile amplitude: `F = Σ a² DᵀPD`.
- Fisher nếu biết amplitude: `F_known = Σ a² DᵀD`.
- Với Gaussian khớp mô hình, expectation của `JᵀJ` đầy đủ sau profile: `G = Σ (a² + 2/I) DᵀPD`.
- Covariance của score profile trong cùng điều kiện: `V_score = Σ (a² + 1/I) DᵀPD`. Score có kỳ vọng zero; phân bố không nhất thiết Gaussian ở SNR hữu hạn.

Ở mỗi draw, fit amplitude tuyến tính không ràng buộc tại truth (được âm), residual `r = âp − y`, `â = pᵀy/I`, Jacobian đầy đủ `J = âPD − p(Dᵀr)/I`. Tính `JᵀJ`, score `Jᵀr`, score quadratic `scoreᵀF⁻¹score`, `rᵀr`, cùng Hessian của một nửa tổng bình phương residual tại bước 0,002 và 0,004 sky pixel. Đạo hàm template dùng sai phân trung tâm 0,00025 sky pixel; Fisher phải dương xác định với eigenvalue nhỏ nhất / lớn nhất > 1e-10. Sai phân Hessian được coi ổn định nếu thay đổi Frobenius tương đối ≤5%; đây là thông tin chất lượng số, không phải gate khám phá thiên văn. Không dùng IRLS, không ước lượng hay nhân hệ số reduced chi-square. `Q` và trọng số luôn cố định tại error map gốc.

Bậc tự do residual là `Σ(n_valid − rank(Q) − 1)`: trừ một flux tự do mỗi exposure, không trừ centroid vì chưa fit. Với matched Gaussian và model rank cố định, `rᵀr` có expectation bằng bậc tự do; score quadratic không mặc định theo χ²(2) ở SNR hữu hạn. `E[H_truth] = F` trong mô hình đúng/chiếu và trọng số cố định, trong khi `E[JᵀJ] = G`; không suy từ `G>F` rằng Hessian hay toàn pipeline phải under-cover. Công thức này là đại số của residual profile; [NIST về variable projection](https://www.nist.gov/publications/variable-projection-nonlinear-least-squares-problems) mô tả phương pháp khử tham số tuyến tính.

## Dữ liệu và tái phát

Ba field `w350p35`, `w090p10`, `w210m20`, patch 1, SNR/frame 2 đứng yên và SNR/frame 4 dịch `[0.6, 0.05]` sky pixel; 64 draw/case, seed 20261030, cùng thứ tự before/after, exposure và kích thước native array như cache Gaussian 0.10. Một vector nhiễu được dùng cho cả hai điều kiện trong mỗi draw:

1. **Primary matched-padded:** trên pixel native đã chọn, mean bằng đúng `a_i × p_padded(x_truth)` trước whiten/project. Amplitude từng exposure `a_i` được tái tạo theo `injected_frames`: `SNR × sqrt(pinv(DᵀD)[0,0])`, với `D` là thiết kế ePSF gốc + plane chia error ở vị trí truth. Không ước lượng `a_i` từ fit hoặc dùng flux chung.
2. **Secondary old-nearest:** giữ nguyên mean từ `source_image` nearest frozen và cùng nhiễu. Do truth cũ và template padded khác nhau, các expectation matched ở trên không được giả định đúng cho điều kiện này; mọi khác biệt chỉ là chẩn đoán mismatch.

Trước khi thử, so sánh mean từ ảnh đã tiêm trừ ảnh gốc với `source_image` dựng lại bằng `a_i`, và so sánh `error²` của từng mẫu với phương sai native. Trong từng draw kiểm tra nhiễu tại selected pixels trùng mẫu RNG đã sinh; lưu sai số lớn nhất, từ chối khi vượt dung sai. Các mẫu giữ WCS tuyến tính, mask, vị trí hàng xóm và Q của candidate. Tín hiệu ban đầu trừ ảnh gốc không chứa nền/nguồn trời gốc; noise pixel Gaussian tổng hợp độc lập, không source shot noise. Không có random offset đăng ký được sinh. Các nguồn ePSF lân cận vẫn từ mô hình frozen, không phải dữ liệu trời thật.

## Báo cáo và cách diễn giải đã định

Mỗi field/case và epoch được báo riêng: số attempt/success/failure và lý do, rank, amplitudes, SNR projected theo truth, `F`, `F_known`, `G`, `V_score`, Hessian mean cho từng bước, mean `JᵀJ`, χ² và dof, mean score, score covariance/quadratic. Điểm so sánh ma trận là `tr(F⁻¹M)/2`; với truth matched, `F` tương ứng 1 và `G` là dự đoán theo từng geometry. 2.000 bootstrap mẫu draw với seed 20261031 cho khoảng 95% của trace trung bình và score mean. Hai epoch dùng cùng chỉ số draw bootstrap; không gộp epoch hay sáu case thành các field độc lập. Mọi draw lỗi được giữ; nếu có lỗi, không xuất CI như thể mẫu thành công là ngẫu nhiên không chọn lọc.

Khóa cách đọc trước khi xem kết quả: trong primary, CI trace trung bình `JᵀJ` nằm trên 1 là bằng chứng thăm dò về inflation theo hướng Fisher; đối chiếu thêm khoảng này với trace dự đoán `G`, không suy cơ chế sai chỉ vì khoảng cắt dự đoán. Với Hessian, dải gần đúng `[0,8; 1,2]` là dung sai chẩn đoán định trước cho trace trung bình: CI hoàn toàn trong dải hỗ trợ phù hợp ở độ chính xác này, CI hoàn toàn ngoài dải cho thấy khác đáng kể theo tiêu chí này, CI giao biên là chưa kết luận. Đây không phải kiểm định tương đương chính thức hay ngưỡng production; 12 epoch/case là nhiều phép nhìn thăm dò, không tuyên bố ý nghĩa đồng thời hoặc suy rộng ba field. Kỳ vọng không bị bác bỏ không chứng minh hoàn toàn đúng mô hình. Cả hai bước Hessian, ma trận đầy đủ và denominator đều phải được báo.

## Vận hành

```powershell
.venv/Scripts/python.exe -m unittest tests.test_flux_information_probe -v
.venv/Scripts/python.exe -m scripts.run_flux_information_probe --design
# Sau khi review và commit toàn bộ mã, test, tài liệu và design:
.venv/Scripts/python.exe -m scripts.run_flux_information_probe --run
# Tiếp tục theo field/case sau khi commit:
.venv/Scripts/python.exe -m scripts.run_flux_information_probe --run --fields w350p35 --snrs 2
```

Thiết kế hash toàn bộ nguồn được dùng, test, giao thức, products opened và cả hai cache noise. `--design` từ chối ghi đè, đối chiếu 384 cặp baseline cache với báo cáo candidate. `--run` từ chối nếu thiết kế/nguồn chưa commit hoặc hash khác và từ chối overwrite kết quả hoàn tất. Kết quả chỉ ghi `data/raw/benchmark/flux-information-development.json` bị Git bỏ qua, checkpoint sau từng draw và hỗ trợ resume. Một smoke test duy nhất của `w350p35` SNR 2 chạy không ghi output; setup 7,52 giây và một draw hai điều kiện/two epochs 0,05 giây trên máy hiện tại, không phải kết quả 64-draw. Tính toán ước chừng một đến vài phút cộng I/O; runtime phụ thuộc máy.

Nghiên cứu về vị trí fitted, IRLS, mode selection, mismatch vật lý hay empirical coverage phải được thiết kế và khóa riêng sau phép thử này.
