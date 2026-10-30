# Đối chứng phổ JWST và đáp ứng SPHEREx R7

Đây là chẩn đoán trên dữ liệu development đã có, nhằm kiểm tra liệu thay phổ
bằng một điểm đơn sắc có làm thay đổi thông lượng dự đoán. Chưa fit vị trí,
bơm nguồn, mở 30 trường mới hoặc thay số đo WISE. Khóa code, quy tắc và hash
đầu vào trước khi tính convolution; không chọn kiểu đáp ứng theo kết quả đẹp.

Nguồn phổ là [MAST G395M x1d đã kiểm tra](WISE0855_EXTERNAL_SED.md), không phải
bảng author Fig 4. Dùng đúng DQ=0, flux/error hữu hạn và error>0; giữ flux âm.
Nguồn đáp ứng là [gói lab chính thức](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/spherex_spectral_calibrations.html),
archive 436.705.280 byte, SHA-256
`45ff6c57ca68da00a595a4e8a5c2f875cc98b094fde143d9ce109e69df252f09`.
Không giải nén archive ra filesystem; kiểm tra hash toàn bộ và hash riêng
35 CSV D6 được đọc. Raw FITS/tar giữ trong `data/raw/` bị Git bỏ qua.

## Phép tính đã định

Tính đủ 17 kênh danh nghĩa D6, cả `Cent` và `Allpix`, tại ba độ dịch trục đáp
ứng −0,0064 / 0 / +0,0064 µm: 102 lượt. Cent/Allpix là hai cách tổng hợp cùng
phép đo lab, không phải hai bộ kiểm định độc lập. Độ dịch chỉ là sensitivity;
không khẳng định đó là phép biến đổi QR2→R7 hoặc sửa wavelength của cutout.

Quy ước chẩn đoán là trung bình photon-weighted của Fν:
`∫ Fν(λ) R(λ) dλ/λ / ∫ R(λ) dλ/λ`, trả Jy. Giữ response âm nhỏ được đo,
không gắn nhãn chúng là throughput vật lý không âm. Nội suy tuyến tính giữa
các mẫu hợp lệ liền kề; không đi qua DQ lỗi hoặc khoảng cách quá 0,01 µm,
không ngoại suy. Tích phân trên hợp các knots phổ, đáp ứng và zero crossing.

Thiếu bất kỳ absolute response-weight khác 0 thì full-band mean
phải là null. Vẫn báo mean của phần có hỗ trợ dưới tên riêng, phần absolute
weight bị thiếu, phần âm và hash vector trọng số; không dùng partial mean như
ước lượng toàn dải. Tỷ số so giá trị đơn sắc và độ nhạy khi dịch chỉ tính cho
full-support mean, mẫu số đơn sắc/baseline dương. Giữ mọi lượt thiếu hỗ trợ
trong mẫu số 102. Không có ngưỡng promotion hoặc chọn mô hình trong audit này.

Không suy sai số tổng bằng cách xem các dòng phổ độc lập: thiếu covariance
phổ đầy đủ, calibration chung, khác biệt epoch và variability. Chưa xác minh
quy ước photometric reference của pipeline SPHEREx; quy ước photon này là một
linear functional minh bạch, chưa được chuyển thành MJy/sr của ảnh SPHEREx.

## Khóa, chạy và giới hạn

```powershell
.venv/Scripts/python.exe -B -m unittest tests.test_spectral_bandpass tests.test_lab_spectral_response tests.test_wise0855_x1d -v
.venv/Scripts/python.exe -B -m scripts.audit_spectral_reference --design
# Commit nguồn, test, protocol và design trước lệnh sau:
.venv/Scripts/python.exe -B -m scripts.audit_spectral_reference --run
```

Design và output từ chối ghi đè. Runner kiểm nguồn/design khớp Git HEAD,
hash/size cả hai raw inputs và schema từng CSV. Chưa ghép detector-coordinate
của response R7 với WCS A của từng exposure; D4–D6 cần chú ý chiều x theo tài
liệu. Không lấy nominal channel mean làm response chính xác của một pixel.

[Tài liệu delivery](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHERExSpectralFiles_202607.pdf)
ghi đây là sản phẩm R7; phổ response ở vị trí trung tâm và trung bình cả kênh
có độ rộng khác nhau, D5/D6 có hiệu chỉnh band center so bản trước. Ghép các
giả định này vào QR2, xử lý negative response, solid angle, gain và uncertainty
phải là protocol mới trước mô phỏng vật lý hoặc fit biên độ chung. Audit này
chỉ kiểm tra sự khác biệt spectral predictions, không đo astrometric bias.
