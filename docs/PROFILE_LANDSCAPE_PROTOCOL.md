# Chẩn đoán profile tại trọng số cố định

Phiên bản `0.10.0-profile-landscape.1`, khóa trước mọi phép lấy mẫu mới.
Đây là phép chẩn đoán hậu nghiệm của gate ePSF đã thất bại, không phải tập
validation độc lập hay một cơ hội thay đổi gate cũ. Kết quả cũ và hệ số ePSF
đã niêm phong giữ nguyên; không fit vị trí mới, không cập nhật Huber, không
điều chỉnh covariance hay ngưỡng phát hiện.

## Câu hỏi và mẫu

Hai ô `2025W46_2A_0214_3` của sao Gaia `5756942110218608640` và
`5756958431094222592` chuyển từ một sang hai nhóm nghiệm gần tốt nhất khi
thêm hiệu chỉnh ePSF. Nhóm được tạo từ chín lần khởi tạo, khoảng cách 0,15
pixel chung và khoảng chi phí 5,991. Quy tắc đó không chứng minh có hai cực
tiểu vật lý. Bộ giải có thể dừng bởi thay đổi chi phí hoặc bước vị trí nhỏ;
trạng thái success không đảm bảo gradient nhỏ hay cực tiểu toàn cục.

Giữ đủ 14 ID training gốc, kể cả sao không có fit. Chỉ dùng hai exposure
đã nằm trong calibration: `2025W46_2A_0214_2` và `_3`. Bốn nhánh trên mỗi ô:
ePSF gốc/gốc đã hiệu chỉnh × trọng số Huber cuối của fit gốc/fit đã hiệu
chỉnh. Tổng 112 nhánh dự kiến. Mọi lỗi chuẩn bị và lỗi profile đều được ghi;
thiếu fit của một phía làm cả phép so sánh ghép không khả dụng, không biến
thành kết quả âm hay bị xóa khỏi mẫu. Hai sao bị gate chặn được công bố là
mẫu được chọn sau khi xem kết quả; các sao khác là mô tả đối chứng cùng trường.

Giữ nguyên pixel native, VARIANCE, mask, pixel area, Gaia/registration, láng
giềng, nền phẳng nghiêng và biên ±2,5 pixel chung. Các hệ số thông lượng Jy
có dấu và hệ số nền được giải tuyến tính tại từng vị trí cố định. Hai vector
trọng số chỉ được đọc lại và hoán đổi, không ước lượng lại. Hiệu chỉnh ePSF
áp dụng cho cả mục tiêu và láng giềng. Tại nhánh ePSF/trọng số cùng họ, kiểm
tra lại chi phí của điểm đã lưu và tất cả final start thành công với
`rtol=atol=1e-10` trước khi chẩn đoán. Sai khác làm nhánh lỗi, không tự sửa.

## Đại lượng được khóa

- Lưới toàn miền 51 × 51 trên anchor ±2,5 pixel chung, bước 0,1 pixel.
- Với hai sao focus, lưới 21 × 21, bán kính 0,2 pixel, bước 0,02 quanh mọi
  near-best candidate khác tọa độ chính xác của hai họ fit đã lưu. Phần nằm
  ngoài miền được ghi thiếu, không cắt vị trí hay đổi tâm lưới.
- Probe tại điểm fit và mọi final start thành công của cả hai họ. Chỉ gộp
  tọa độ giống hệt, giữ đủ nguồn gốc. Đạo hàm sai phân trung tâm với ba bước
  cố định 0,004 / 0,002 / 0,001 pixel chung; stencil vượt biên không khả dụng.
- Chi phí là `F=rᵀr`, với residual chuẩn hóa theo sai số gốc và nhân căn bậc
  hai trọng số. Đây là hai lần `cost` theo quy ước SciPy.
- Giữ riêng gradient từ residual `2Jᵀr`, gradient sai phân trực tiếp của F,
  Hessian sai phân trực tiếp của F và Gauss–Newton `2JᵀJ`, eigenvalue, chuẩn
  cột J và hạng J đã chuẩn cột với tỷ lệ singular value `1e-10`. Không nghịch
  đảo Hessian thành covariance, không đặt ngưỡng đạt stationarity sau khi xem.
- Đếm thành phần liên thông 4 và 8 láng giềng tại các mức F trừ minimum
  **trên chính lưới** bằng 0,1 / 1 / 2,3 / 5,991. Ghi số nút, chạm biên và
  chạm nút thiếu. Các mức này không mang ý nghĩa coverage/confidence.
- Không RNG, không truy vấn mạng, không pixel mới, không phép tối ưu vị trí.
  Hai shard theo thứ tự source ID, mỗi tiến trình yêu cầu BLAS/OMP một luồng;
  đây là yêu cầu môi trường, không phải đo số luồng thực tế. Cache template
  giới hạn 8.192 vị trí cho mỗi ô/ePSF, chỉ dùng để chia sẻ render giữa hai
  nhánh trọng số, không thay đổi mô hình hay cache dữ liệu người dùng.

## Niêm phong và diễn giải

Design chứa hash mã mới, test, tài liệu này, các nguồn khoa học kế thừa,
hệ số đã niêm phong, gate cũ và digest journal gốc/corrected. Phải commit
design trước khi chạy bằng SHA đầy đủ. Journal bất biến có đủ 112 khóa;
resume không ghi đè kết quả. Assessment directory phải vắng trước và sau.
252 ô corrected assessment và 30 trường độc lập tiếp tục chưa mở.

Kiểm thử analytic gồm quadratic có gradient/Hessian biết trước, double-well
có rào chi phí biết trước, residual phẳng không định danh, nút lỗi và stencil
vượt biên. Kiểm thử runner xác nhận đủ mẫu, hoán đổi đúng trọng số, replay
chi phí, không gọi optimizer, không mở assessment và resume bất biến.

Lưới hữu hạn có thể bỏ sót thung lũng hẹp hoặc đường nối cong; đạo hàm hữu hạn
phụ thuộc bước và nội suy. Nhiều thành phần mẫu không chứng minh nhiều cực
tiểu, một thành phần cũng không loại trừ chúng. Huber cố định có điều kiện
theo ảnh, không phải likelihood đã hiệu chuẩn; nuisance, đăng ký, catalog,
PSF và nhiễu tương quan vẫn có các giới hạn đã công bố. Dù chẩn đoán chỉ ra
solver dừng sớm, gate cũ không được sửa thành đạt. Mọi thay đổi bộ giải hay
screening tiếp theo cần phiên bản, kiểm thử và protocol mới trước khi dùng
trên tập chưa mở.

Nguồn phương pháp: [SciPy least_squares 1.17](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.optimize.least_squares.html)
giải thích tiêu chí dừng và success; môi trường dự án giữ SciPy 1.17.1.
[O’Leary và Rust, NIST](https://www.nist.gov/publications/variable-projection-nonlinear-least-squares-problems)
trình bày variable projection cho bài toán có cả tham số tuyến tính và phi
tuyến. Việc giữ nguyên các nuisance tuyến tính ở đây là một chẩn đoán của
bài toán đang dùng, không phải xác nhận mô hình quang học đúng.
