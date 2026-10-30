# Đối chứng phổ: có dữ liệu thật, chưa đủ hệ số cho fit ảnh

Đã có hai phổ JWST/NIRSpec công khai của WISE 0855 cùng chương trình 1230:
[G395M](WISE0855_EXTERNAL_SED.md) và [PRISM](WISE0855_PRISM.md). Cả hai là
pipeline MAST, không phải bảng tác giả trích xuất riêng hoặc phép chuẩn
Spitzer của bài báo. Raw FITS, association và metadata giữ trong cache bị
Git bỏ qua; repo giữ source URL, hash và báo cáo, không sao chép raw vào web.

## Kết quả đã ghi

| Phép kiểm tra | Kết quả | Diễn giải |
|---|---|---|
| G395M x1d | 1.233/1.254 hàng usable, 335/335 trong 4,4–5,0 µm | Mask kỹ thuật; không phải chứng nhận flux chính xác |
| Response lab R7 | 17 kênh D6 × Cent/Allpix × 3 shift = 102 điều kiện | Kênh danh nghĩa, chưa ghép response của mỗi pixel QR2 |
| Kernel V2 trên G395M | 102 tính được; 102 partial; 0 full; 0 numerical failure | Không ngoại suy qua DQ hoặc ngoài miền file |
| Trọng số tuyệt đối thiếu | 0,0136776–0,1592443% | Tỷ lệ trọng số, không phải độ lệch hoặc sai số flux |
| PRISM bổ sung | 100/100 mẫu trong miền response, 102/102 tính cả bracket | Chưa convolution, ghép phổ, scale hoặc sửa LSF |

Phổ G395M có điểm usable cuối tại 5,0930738449 µm; các điểm tiếp theo có DQ.
Response lab gốc kéo đến 5,104283 µm, với shift lớn nhất đến 5,110683 µm.
Do đó 102 điều kiện thiếu trọng số vì DQ cuối phổ; 68 điều kiện còn vượt miền
file G395M. Các tail nhỏ không được tự coi flux bằng 0. Mean của phần có hỗ
trợ được lưu riêng; mọi full-band mean và tỷ số dùng full-band mean là null.
Không suy confidence interval từ các dòng flux có thể tương quan.

PRISM có các mẫu hợp lệ kẹp toàn bộ miền response ở giới hạn gap 0,01 µm.
Điều đó giải quyết khả năng lấy mẫu của dữ liệu bổ sung, chưa xác nhận
convolution có cùng độ phân giải hoặc chuẩn flux. Chưa dùng PRISM thay G395M
trong 102 kết quả trên và chưa tạo SED tổng hợp.

## Lỗi, khóa cấu hình và tái lập

V1 `b3eb94c` dừng ở điều kiện thứ tư do root fraction làm tròn thành 1,
làm mất chiều dài một thùy đáp ứng nhỏ. [Receipt thất bại](evidence/0.10/spectral-reference-b3eb94c-aborted.json)
và nguồn V1 còn nguyên. V2 giữ hai thùy bằng moment giải tích ổn định, không
clip dấu. Numerical preflight đã xem 102 điều kiện development trước khi
khóa V2; không gọi đây là validation chưa xem trước.

Lượt ghi chính thức dùng commit `f5a1e518a4d0f28268337f42af0bbabdfc605e78`,
[design V2](../web/data/spectral-response/v2-design.json) SHA-256
`fd7c0c6141d7a8b204190b04ca140017e9b0316585df07d21d913937c37718c9`.
[Báo cáo 102 điều kiện](../web/data/spectral-response/v2-development-audit.json),
150.164 byte, SHA-256
`21a07ae84771d4267c8afc992005a74eb82554c375e4c62cee21c3049187a97b`.
Mỗi curve có hash CSV, mỗi functional có hash vector trọng số; 35 CSV đã đọc
không được giải nén ra filesystem. Ba test sản phẩm tính lại mẫu số, kiểm
hash và replay toàn bộ khi có raw. Kernel V2 có 13 test, gồm regression thật
và đối chiếu tích phân độc lập; parser lab 3, G395M 3, PRISM 5 test.

## Trước khi ràng buộc flux trong fit WISE

1. Ghép response theo detector/pixel, wavelength và đúng release; kiểm quy
   ước flux cùng solid angle, gain. R7 không tự thay calibration QR2.
2. Định nghĩa xử lý LSF, negative response, normalization và covariance của
   PRISM/G395M; báo sai khác và giới hạn thay vì ghép theo mắt.
3. Khóa adapter và point model trên development, kiểm S/N, centroid bias,
   modes và uncertainty với source-noise/PSF độc lập trước calibration ngoài.

[Lõi shared flux](LINKED_FLUX_MODEL.md) đã có kiểm số học nhưng chưa nối
các giả định trên vào pixel thật. Ba mươi trường triển vọng vẫn chưa được
đo; không xem bất kỳ kết quả này là xác nhận chuyển động hoặc production.
