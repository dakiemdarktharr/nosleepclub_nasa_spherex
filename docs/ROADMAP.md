# Lộ trình đề xuất

Đây là backlog chuẩn bị của NoSleepClub. Các mục chưa đánh dấu đều chưa được thực hiện; triển khai sản phẩm theo thời gian chính thức của hackathon.

## Lát cắt kỹ thuật hiện tại

- [x] Tải cutout WISE 0855 thật, kiểm tra bước sóng và chọn 3 cặp.
- [x] Căn chỉnh, PSF cross-convolution, export ảnh sai khác và provenance.
- [x] Demo web trước/sau, highlight, evidence và nhận xét cục bộ.
- [x] Cộng ảnh trong epoch theo phổ và đo centroid độc lập kèm sai số có điều kiện.
- [x] Truyền covariance nội suy cho S/N; đối chứng sao giữ lại, bootstrap và injection nền thật.
- [x] Mở rộng trường sao tham chiếu, đối chiếu Gaia và kiểm tra đổi tập sao căn chỉnh.
- [x] Bỏ lần lượt 14 sao, thử affine và 32 injection mỗi cấu hình; giữ cả giới hạn nền ảnh.
- [x] Thử fit nhiều nguồn IR/ePSF trên 30 vùng khóa trước; chưa đạt gate thay mặc định.
- [x] Tải 129 cutout ở ba trường mới và kiểm tra Gaia/nguồn giả theo protocol khóa trước; giữ cả trường không đủ sao căn chỉnh.
- [ ] Giảm outlier/bias nguồn mờ và kiểm chứng covariance trên các trường chưa mở.
- [ ] Kiểm tra đáp ứng phổ đầy đủ, injection nhiều vị trí và thêm epoch thứ ba.
- [ ] Xác minh chuyển động của WISE 0855 bằng dữ liệu này.

Xem [benchmark ngoài trường](EXTERNAL_BENCHMARK.md), [kết quả Gaia](WISE0855_GAIA.md), cùng [research và tài liệu](GAIA_RESEARCH.md).

## Chuẩn bị

- [x] Đọc Details và kiểm tra Resources của đề chính thức.
- [x] Tạo repo GitHub public và tài liệu khởi đầu.
- [ ] Kiểm tra lại Resources khi công bố ngày 13/11/2026.
- [ ] Thống nhất vai trò thành viên, phạm vi demo và giấy phép mã nguồn.

## Khi bắt đầu triển khai

### 1. Xác minh dữ liệu trước

- [ ] Ghi nguồn, phiên bản, quyền sử dụng, cách truy vấn và giới hạn tải.
- [ ] Lấy được các quan sát có thời điểm khác nhau của một mục tiêu kiểm thử.
- [ ] Kiểm tra hệ tọa độ, epoch, đơn vị, WCS và các cờ chất lượng.
- [ ] Lập manifest có thể tái tạo để mọi thành viên dùng cùng dữ liệu.

### 2. Hoàn thiện luồng nhỏ đầu tiên

- [ ] Chốt công nghệ sau khi xác định cách lấy và xử lý dữ liệu.
- [ ] Nhập và kiểm tra RA/Dec, chọn vùng trời và khoảng thời gian.
- [ ] Tạo cutout cùng vùng phủ, căn chỉnh lên cùng lưới tọa độ.
- [ ] Hiển thị chuỗi ảnh với play/pause, bước frame và thời điểm quan sát.
- [ ] Xử lý trạng thái tải, lỗi và không có dữ liệu.

### 3. Kiểm chứng và đóng gói demo

- [ ] Thử đủ 5 mục tiêu trong `CHALLENGE.md`; ghi nhận cả giới hạn dữ liệu.
- [ ] Kiểm tra hiển thị trên màn hình nhỏ và thao tác bàn phím.
- [ ] Ghi quy trình tái tạo, cấu hình, lệnh chạy và kiểm thử phù hợp.
- [ ] Chuẩn bị demo, thuyết minh và ghi nguồn dữ liệu/tài sản.

### Sau luồng chính, tùy thời gian

- [ ] Chọn trường nhìn và tạo URL chia sẻ tọa độ.
- [ ] So sánh, cộng/trừ ảnh với giải thích phương pháp chuẩn hóa.
- [ ] Chọn dải phổ/nhóm detector và hiển thị metadata chất lượng.
- [ ] Overlay catalog hoặc tạo phổ khi dữ liệu và thời gian cho phép.
