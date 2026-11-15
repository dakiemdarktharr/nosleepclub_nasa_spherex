# Giao thức phát triển ePSF liên tục 0.10

Mục tiêu là kiểm tra ảnh hưởng của biên template nguồn mục tiêu lên sai số vị trí và độ bao phủ có điều kiện trong các phép thử đã mở. Đây là nghiên cứu phát triển, không phải tập kiểm định độc lập, xác nhận thiên văn hoặc thay đổi WISE 0855.

## Ứng viên và giới hạn

Ứng viên kế thừa `plane_fixed` 0.9: pixel và mask native, WCS và offsets, phương sai, biên fit ±2.5 sky pixel, năm điểm khởi tạo, nền phẳng và flux tự do, hai vòng Huber IRLS, cùng đối chiếu chất lượng với fit nguồn đơn gốc. Chỉ template mục tiêu thay đổi: đọc đúng ePSF raw, ép float, chuẩn hóa `raw * oversampling² / sum(raw)` như cũ, đệm 16 ô oversampled số 0 mỗi cạnh, rồi spline-filter bậc ba. Trung tâm được tính từ kích thước mảng mới. Không monkeypatch và không sửa pipeline frozen. PSF hàng xóm trong phép chiếu nuisance vẫn là PSF cũ; chúng không liên tục tại biên và đây là giới hạn có chủ ý để cô lập biên của mục tiêu. Tái fit lại IRLS và flux theo ứng viên; pad 16 không chứng minh PSF có ý nghĩa vật lý.

Một fit được tính numeric khi solver thành công, không sát biên theo quy tắc 0.9, tổng amplitude dương, vị trí/covariance hữu hạn, rank thông tin là 2 và covariance dương xác định. Các gate chất lượng 0.9 và so sánh nguồn đơn vẫn áp dụng. Không thay đổi thông số frozen. Covariance Gauss–Newton và observed profile Hessian lấy tại cùng vị trí fit ứng viên, với trọng số IRLS cuối cố định. Profile dùng hai bước 0.002 và 0.004 sky pixel và ngưỡng ổn định 5% của `profile_uncertainty`; bỏ trống nếu hai epoch không hợp lệ hoặc Hessian không ổn định/dương xác định. Cộng covariance đăng ký cũ trước khi đổi sang east/north arcsec. Đây là độ bất định có điều kiện, chưa hiệu chuẩn, không bao gồm đầy đủ sai số vật lý.

## Mẫu và phép so sánh được khóa

Chỉ dùng ba trường đã mở `w350p35`, `w090p10`, `w210m20`; patch 1 và ePSF nearest frozen. Mỗi trường có hai case: đứng yên SNR 2/frame và chuyển động `[0.6, 0.05]` sky pixel SNR 4/frame. Mỗi case được đánh giá trên ảnh gốc đã chèn nguồn, và 64 draw Gaussian độc lập trong pixel với cùng phương sai và seed 20261030 như cache baseline `data/raw/benchmark/bias-gaussian64-development.json`; RNG được khởi tạo lại cho từng case và lấy theo thứ tự frame/epoch cũ. Ảnh Gaussian gồm tín hiệu trừ ảnh gốc cộng nhiễu mới, không có nền gốc và không thêm shot noise của nguồn. Tín hiệu truth dùng `source_image` frozen, không đổi sang PSF đệm; phép so sánh ghép cặp có mismatch có chủ ý giữa truth cũ và candidate. Không có điều khiển padded-truth phụ trong giao thức này.

Cache baseline đã chạy lưu toàn bộ 64 bản ghi mỗi case. Khi chạy, tái fit baseline draw 0 và từ chối nếu trạng thái hoặc vector khác cache quá 1e-5 arcsec. Từng trial trong báo cáo ghép đúng chỉ số draw với bản ghi baseline, bao gồm cả thất bại; ứng viên không thay kết quả baseline. Ghi riêng số numeric và accepted của từng nhánh và tập common numeric/common accepted. Với từng tập, báo RMS và P90 sai số vector, số ellipse chứa truth ở 68% và 95% kèm số covariance sẵn có. Không diễn giải tỷ lệ trên tập có profile như tỷ lệ của mọi trial khi profile không sẵn có. Các trường dùng chung exposure trong mỗi trường, còn Gaussian draw độc lập về nhiễu; sáu case không phải sáu trường độc lập mới.

Không chọn hay mở tập calibration/validation mới. Những kết quả này không đủ để promotion; muốn xét tiếp phải khóa mô hình và tiêu chí trước, đo bias và coverage trên trường độc lập mới, đánh giá PSF vật lý và nhiễu hệ thống, và công bố đầy đủ denominators cùng out-of-support.

## Khóa và chạy

```powershell
.venv/Scripts/python.exe -m unittest tests.test_continuous_epsf -v
.venv/Scripts/python.exe -m scripts.run_continuous_epsf_study --design
# Sau khi commit design và toàn bộ nguồn, tài liệu, test được hash:
.venv/Scripts/python.exe -m scripts.run_continuous_epsf_study --run
# Có thể chạy hoặc tiếp tục riêng một case:
.venv/Scripts/python.exe -m scripts.run_continuous_epsf_study --run --fields w350p35 --snrs 2
```

`--design` từ chối ghi đè và lưu hash SHA-256 của code, test, tài liệu, requirements, nguồn frozen, thiết kế và sản phẩm 0.9 đã mở, cùng cache baseline. `--run` từ chối khi design, sources hay sản phẩm đã theo dõi chưa commit ở HEAD, hash trên đĩa sai hoặc cache baseline thay đổi. Cache nhiễu gốc nằm trong `data/raw/` bị bỏ qua nên được ràng buộc bằng hash thay vì Git. Dữ liệu gốc, calibration và nguồn URL được xác minh theo manifest và hash của thiết kế frozen khi tải trường. Kết quả chỉ ghi trong `data/raw/benchmark/continuous-epsf-development.json`, checkpoint sau từng draw bằng thay thế file; resume tái tạo cùng RNG từ đầu và kiểm tra chuỗi draw liên tục. Kết quả đã hoàn tất không được ghi đè.

Trên máy hiện tại, một phép thử original-background của `w350p35` SNR 2 mất khoảng 7 giây tải và 0.66 giây fit hai epoch sau tải. Đây chỉ là phép thử hiệu năng đơn lẻ, không phải kết quả Monte Carlo. Ước lượng thấp khoảng 5 phút cho 390 phép fit cặp, cộng tải trường, I/O checkpoint và biến thiên hội tụ; nên dự trù 10–20 phút hoặc hơn. Xem tiến độ console và có thể tiếp tục theo case nếu bị ngắt.
