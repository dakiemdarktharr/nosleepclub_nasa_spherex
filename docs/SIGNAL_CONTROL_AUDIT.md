# Kiểm toán độc lập synthetic signal controls

Auditor chỉ chạy sau khi cả 640 ô đã hoàn tất, trên protocol commit
`9894074fdacbba908b8816d3dbcac1df901731f1`. Mọi checkpoint là terminal,
hash-bound và không ghi đè. Không chạy optimizer, IRLS, fit vị trí mới,
truy vấn sky hay mở assessment. Các bank PCG64 được tái dựng đúng seed đã
khóa, không tạo các realization mới cho thí nghiệm.

Kiểm chứng journal, nguồn và design, upstream, summary, seed/pixel/mask,
pha và phép đổi tọa độ; so synthetic mean/data và các cặp dùng chung ảnh.
Truth Gaussian được tính độc lập bằng mật độ covariance khai triển với
Gauss–Legendre 64 điểm mỗi chiều trên mọi pixel đã chọn của tám geometry–pha,
so L1 với generator 24 điểm. Matched dùng chính ePSF gốc, là kiểm tra phần mềm
inverse crime và không xác nhận physical PSF. Nền, tọa độ và variance vẫn là
điều kiện cố định; original IMAGE không được cộng vào mean.

Tại từng vị trí đã lưu, giải tuyến tính tự do bằng `numpy.linalg.lstsq` với
các cột được chuẩn hóa và đúng final weights: so flux target/neighbor, nền,
model, residual và weighted cost. Với các start cuối thành công, chỉ kiểm
objective ở tọa độ đã lưu. Failure được giữ, phân biệt kiểm input với không
có objective; không gọi replay là chứng minh optimizer tìm được nghiệm tối ưu.
Giải độc lập dùng ngưỡng hạng tương đối `1e-10`, khớp guard đã khóa. Lỗi
chuẩn bị chỉ được ghi nhận là đã tái hiện khi cả loại lỗi, thông điệp và
stage `geometry_or_realization` hoặc `preparation` khớp chính xác record gốc;
checkpoint giữ lỗi và stage đã tái hiện, không khẳng định có objective. Lỗi
kiểm toán hay stage/thông điệp không khớp là finding và làm receipt failed.
Tính lại độc lập các mẫu số, stratum, cặp và guard, dùng khoảng nhị thức chính
xác hai phía từ `scipy.stats.binomtest` thay cho công thức beta của study.

Ngưỡng cố định trước audit: cost `atol=1e-8, rtol=1e-9`; hệ số flux Jy
`atol=1e-10, rtol=1e-8`; pixel/model `atol=1e-9, rtol=1e-9`; tọa độ native
`atol=1e-7, rtol=0`; Gaussian L1 không quá `1e-10 + 1e-10*selected_mass`.
Khoảng confidence so `atol=2e-12`; các metrics còn lại so `atol=1e-10,
rtol=1e-9`. Mismatch là finding, không nới ngưỡng theo kết quả.

Kiểm toán điều kiện này không chứng nhận PSF vật lý, bias thiên văn, coverage,
source detection hay khả năng mở assessment; các ô lỗi không được loại khỏi
mẫu số. Hash phát hiện thay đổi vô ý, không chống tác nhân có thể ghi lại tất
cả hash.
