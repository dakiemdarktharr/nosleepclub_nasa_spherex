# Hợp đồng API metadata quan sát SPHEREx, phiên bản 1.0

`GET /api/observations` tìm metadata Spectral Image MEF của DR1 hoặc QR3 qua endpoint SIA2 cố định `https://irsa.ipac.caltech.edu/SIA`. Kết quả mô tả những ảnh giao vùng truy vấn. Dữ liệu FITS, chất lượng tại vị trí nguồn và khả năng so sánh cần kiểm tra riêng. IRSA có thể đưa dữ liệu mới vào SIA sau khoảng một ngày. [Tài liệu truy cập SPHEREx](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/) · [Tài liệu SIA2](https://irsa.ipac.caltech.edu/ibe/sia.html).

Truy vấn mẫu `/api/observations?ra=350&dec=35&radius=0.01&release=dr1&detector=4&maxrec=100`.

| Tham số | Giá trị |
| --- | --- |
| `ra`, `dec` | Bắt buộc, số thập phân hữu hạn theo độ ICRS; RA [0, 360), Dec [-90, 90]. Không nhận sexagesimal; frontend chuyển đổi trước. |
| `radius` | Bán kính cone theo độ, > 0 và ≤ 0,20; mặc định 0,05. Đây là bán kính truy vấn POS, không phải kích thước ảnh/FOV của detector. |
| `release` | `dr1` hoặc `qr3`, mặc định `dr1`. Mỗi request truy vấn một bản dữ liệu. Yêu cầu `qr2` trả HTTP 400 với `release_retired` vì IRSA đã ngừng tìm kiếm QR2. |
| `deep` | `0` mặc định (wide) hoặc `1` (deep); không tự gộp hai collection. |
| `detector` | Tùy chọn, số nguyên 1–6; lọc local bằng `energy_bandpassname`, sau khi IRSA áp dụng MAXREC. |
| `time_min_mjd`, `time_max_mjd` | Hai cận MJD (ngày), bắt buộc cùng xuất hiện, 0–100000 và dưới ≤ trên. SIA TIME chọn khoảng có giao nhau. |
| `band_min_um`, `band_max_um` | Hai cận bước sóng tính bằng micromet, bắt buộc cùng xuất hiện, 0,01–1000 và dưới ≤ trên. Chuyển sang mét cho SIA BAND; chọn khoảng có giao nhau. |
| `maxrec` | Số nguyên 1–500, mặc định 300; gửi `MAXREC` đến IRSA. |

Không nhận tham số lạ, trùng khóa, số vô hạn/NaN hay arbitrary URL. Mỗi response 200 có `contract_version`, `status`, `query` chuẩn hóa, `observations`, `returned_count`, `upstream_count`, `truncated` và `provenance`. `status` là `ok` khi có hàng, `no_data` khi không có hàng sau lọc và response upstream không báo overflow, hoặc `truncated` khi SIA báo `QUERY_STATUS=OVERFLOW`. Không diễn giải `no_data` là không tồn tại nguồn hay không có dữ liệu trong toàn archive; lọc detector diễn ra sau MAXREC nên một response bị cắt có thể trả 0 hàng và không chứng minh detector đó vắng mặt. Thứ tự SIA không được coi là thứ tự thời gian hay xếp hạng.

Mỗi hàng gồm `obs_id`, `detector` (có thể null nếu IRSA không cung cấp tên detector nhận diện được), `bandpass`, `t_min_mjd`/`t_max_mjd`, `em_min_m`/`em_max_m`, `wavelength_center_um`, `wavelength_width_um`, `footprint` (chuỗi STC-S `s_region` gốc), `access_url`, `release`. Dữ liệu thiếu được trả `null`. MJD giữ giá trị từ IRSA, không tự giả định timescale hay chuyển sang UTC. Hai đại lượng bước sóng center/width là trung điểm và độ rộng `em_min`–`em_max` của toàn ảnh/dải detector, **không phải** bước sóng hoặc độ rộng phổ tại pixel mục tiêu; cần WCS phổ trong FITS cho phép đo đó. URL ảnh chỉ được trả khi là HTTPS đúng host IRSA và đường dẫn level2 thuộc release được chọn; URL không hợp lệ trở thành null. Không suy ra hash FITS từ hash metadata.

`provenance` chứa endpoint, `query_url` với các tham số thực gửi IRSA, `response_sha256` của byte VOTable nguyên gốc, `retrieved_at` UTC, `source_format` và `collection`. `query.detector` ghi lại bộ lọc local. Request mới có thể cho kết quả khác khi IRSA cập nhật kho. Hash định danh bytes metadata của lần lấy đó.

Explorer tách kích thước ảnh hiển thị khỏi truy vấn metadata: POS dùng cone 0,001° quanh tọa độ nhập, còn FOV chỉ áp dụng khi dựng cutout. Điều này tìm các ảnh phủ điểm cần xem mà không quét cả vùng hiển thị rộng. `detector` vẫn được lọc local sau `MAXREC`, vì vậy response `truncated` có thể thiếu ảnh của detector đã chọn.

Chỉ hỗ trợ VOTable XML UTF-8 `TABLEDATA`, có `RESOURCE type=results`, `QUERY_STATUS` hợp lệ và các cột/đơn vị cần thiết. Không xử lý DTD/entity, BINARY hoặc BINARY2. Đầu vào upstream giới hạn 2.000.000 byte, 500 hàng và `MAXREC` của request. Redirect bị từ chối, chỉ kết nối host/đường dẫn SIA cố định. Timeout socket 6 giây và kiểm tra deadline 8 giây giữa các lần đọc; một lần đọc đang chờ có thể kéo dài thêm đến timeout socket. Nếu upstream trả lỗi, không hợp lệ, quá lớn, sai collection hoặc sai đơn vị, API trả 502 với mã `upstream_*`; timeout trả 504. `Retry-After` số hợp lệ từ upstream được chuyển tiếp có giới hạn để giao diện chờ trước lần thử lại duy nhất. Lỗi input trả 400, phương thức không hỗ trợ thông dụng trả 405, lỗi nội bộ trả 500. Không trả stack trace. Log có request ID, status, nhóm lỗi và latency, không ghi query, IP, cookie hay thông tin xác thực.

API chạy cùng quota và bộ bảo vệ biên của dự án. Production cần runtime Vercel kết nối HTTPS đến IRSA. Chạy `python -m scripts.serve_app` để kiểm tra API và giao diện qua loopback. Test dùng upstream giả cùng VOTable QR2 lịch sử khi có file raw. [Quota API](API_ABUSE_CONTROLS.md) · [Kiểm tra DR1/QR3 tại năm mục tiêu](SKY_EXPLORER.md).
