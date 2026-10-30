# Khám phá tọa độ và chuỗi ảnh SPHEREx

Nhập RA theo độ hoặc giờ:phút:giây; Dec theo độ hoặc độ:phút:giây. Chọn QR2/QR3, detector, trường nhìn và khoảng ngày tùy chọn, rồi tìm ảnh. Truy vấn chọn BAND theo dải detector để giảm cắt danh sách. Metadata bước sóng là phạm vi của toàn detector, không phải lambda tại nguồn.

Ảnh tải theo nhu cầu từ dịch vụ cutout IRSA, dùng WCS/SIP thật để đặt lên lưới TAN bắc trên/đông trái với 6.15″/pixel. Không fit chuyển động, không căn chỉnh theo sao và không ghép phổ tại pixel. Mỗi frame có thể khác PSF, màu, nền và calibration. Giữ một ảnh đối chiếu, chọn frame khác rồi phát hai ảnh đã tải; thang tương phản khóa theo ảnh hợp lệ đầu tiên và được kiểm tra ở từng response. Link FITS trỏ đúng cutout được hash, kể cả phần mở rộng để bao góc xoay.

Cam biểu thị pixel bị loại theo FLAGS; tím là vùng thiếu/ngoài ảnh. Nearest-neighbor dùng cho quan sát, không bảo toàn flux và không phải đầu vào photometry. Mọi lỗi upstream xuất hiện rõ, không thay bằng ảnh giả. IRSA có thể chậm hoặc ngắt stream; các giới hạn request và cache là biện pháp vận hành, không bảo đảm độ trễ.

`web/data/challenge-targets.json` ghi nguồn và epoch của các tâm mẫu. WISE 0855 và Barnard được dự báo tới năm 2026 để tránh việc tâm catalog cũ làm nguồn chuyển động nhanh ra khỏi khung. Epsilon Indi B dùng tọa độ trường ESO lịch sử và FOV rộng hơn; cặp chưa được phân giải. Những tọa độ này chỉ hướng dẫn tìm vùng, không phải phép đo độc lập.

Ngày 30/10/2026 đã truy vấn và tải hai cutout thật cho từng mục tiêu: WISE 43, Barnard 42, Epsilon Indi B 57, RW Aur 36, R Dra 89 quan sát D6 trong truy vấn point-like QR2; không response nào bị cắt. Mười PNG cùng metadata/URL/hash ở `web/data/explorer-check/`. Đây là smoke khám phá dữ liệu, không phải kiểm định chuyển động, biến quang hoặc tính đúng của định danh nguồn trong ảnh. `python -m scripts.check_observation_targets --images` chạy lại truy vấn tuần tự có giới hạn và ghi nguyên liệu lớn vào `data/raw/explorer-check/`.

## Chạy tại máy

Sau khi cài `requirements.txt` và `web/requirements.txt`:

```powershell
python -m scripts.serve_app --port 8767
```

Mở http://127.0.0.1:8767/#explore. Launcher chỉ bind loopback, bật rõ local API budgets; không nạp secret production. `python scripts/serve_app.py --check` kiểm tra imports mà không mở socket. Bản chỉ dùng sản phẩm đã xuất vẫn mở bằng `python scripts/serve_demo.py` ở port 8766; server tĩnh đó không chạy hai API mới. Review local nằm trong trình duyệt, còn cloud review chỉ ở production có credential đã được cấp.

Gói JSON xuất từ explorer lưu query, metadata IRSA, headers provenance của các frame đã xem, thang hiển thị và ý kiến cá nhân. Ghi chú explorer hiện xuất thành tệp, chưa thành hồ sơ review cộng tác hay xác nhận khoa học. Review các phân tích WISE cố định vẫn dùng API khách có ID và expiry riêng.

Xem [observations API](OBSERVATION_API_CONTRACT.md), [frame API](FRAME_API_CONTRACT.md), [quota](API_ABUSE_CONTROLS.md), [kiểm chứng và các giới hạn còn mở](PRODUCTION_READINESS.md).
