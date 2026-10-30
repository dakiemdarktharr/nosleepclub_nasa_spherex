# Chọn field triển vọng — chỉ hình học

[selection.json](../web/data/independent-fields/selection.json) là danh sách field triển vọng, **chưa phải** giao thức phân tích/hiệu chuẩn đã khóa, tập validation đã đo hay bằng chứng accuracy. Không truy vấn metadata mới, đọc pixel FITS, đo nguồn hoặc dùng outcome, spectrum, fit để chọn field. Các field và sản phẩm đã mở trước đây đều giữ vai trò development.

## Quy tắc và bằng chứng đầu vào

Lưới cơ sở RA `[12,48,84,120,156,192,228,264,300,336]` độ × Dec `[-45,0,+45]` độ. Trước khi đo, thử một **độ dịch RA toàn cục** nguyên từ 0 đến 35 độ, theo thứ tự tăng; RA được wrap modulo 360. Chọn offset đầu tiên mà mọi tâm mới cách mọi tâm đã cache ít nhất 6° và mỗi cặp tâm mới cách nhau **lớn hơn** 6°. Khoảng cách là cung tròn lớn trên mặt cầu; 1e-12 độ được coi là sai số làm tròn bằng đúng ngưỡng. Không thay riêng lẻ field hay dựa vào kết quả đo. Nếu không có offset hợp lệ, lệnh thất bại và không ghi selection.

Nguồn loại trừ là mọi JSON có `manifest` trong tên dưới `data/raw` chứa `field.ra/dec`, cặp `center_ra_deg/center_dec_deg` gốc, hoặc `records[].cutout_center_ra/dec`. Mỗi manifest có hướng được ghi path, SHA-256, tọa độ và JSON pointer gốc; manifest job không có tọa độ được bỏ qua. Hướng thiếu một thành phần hoặc không hợp lệ khiến lệnh thất bại. Không mở FITS hay catalog. Việc kiểm chứng này phụ thuộc tính đầy đủ của manifest local; không suy rằng mọi dữ liệu từng nhìn trong nguồn khác đã được liệt kê.

Trong snapshot local, 16 manifest có tâm đã biết. Offset **0–9°** không đạt; chi tiết conflict gần nhất và số conflict của từng offset nằm trong JSON. Offset 0–2 vi phạm gần trường `v150p45`; offset 3–9 vi phạm gần trường Barnard. Offset hợp lệ đầu tiên là **+10°**: tâm cũ gần nhất cách **6,531843°**; cặp hai field mới gần nhất cách **25,242833°**. Đây là geometry-only, không bảo đảm exposure/pixel độc lập.

## Phân vai tiền định

Sau khi chọn offset, field ID có dạng `r{RA:03d}{p|m}{|Dec|:02d}` theo tọa độ độ nguyên. Trong từng vòng Dec, tính SHA-256 của chuỗi `nosleepclub-independent-fields-20261030-v1|field_id`, sắp xếp tăng theo digest: bốn đầu calibration, bốn tiếp validation, hai cuối final holdout. Cộng lại **12/12/6**; thứ tự và digest từng field lưu trong JSON.

| Dec | Calibration | Validation | Final holdout |
|---:|---|---|---|
| −45° | r238m45, r166m45, r130m45, r022m45 | r202m45, r094m45, r274m45, r346m45 | r310m45, r058m45 |
| 0° | r238p00, r274p00, r346p00, r310p00 | r058p00, r094p00, r130p00, r022p00 | r166p00, r202p00 |
| +45° | r130p45, r058p45, r274p45, r094p45 | r022p45, r202p45, r166p45, r346p45 | r238p45, r310p45 |

Danh sách là lưới hình học có phân tầng, không phải mẫu xác suất đại diện cho toàn bộ bầu trời. `final_holdout` là vai trò dự kiến; việc công bố tọa độ ở đây không cho phép mở kết quả sớm hoặc dùng chúng để điều chỉnh model.

## Tái lập và bước tiếp theo

```powershell
.venv/Scripts/python.exe -m scripts.select_independent_fields --select
.venv/Scripts/python.exe -m unittest tests.test_independent_field_selection -v
# Chỉ sau khi commit source và selection, kiểm tra guard trước một workflow metadata tương lai:
.venv/Scripts/python.exe -m scripts.select_independent_fields --verify-committed
```

`--select` không ghi đè selection khác; nếu bản hiện tại giống byte, lệnh giữ nguyên. `--verify-committed` kiểm tra SHA source và selection so với Git HEAD, sau đó đọc lại manifest local để phát hiện nguồn mới/đổi và tính lại quy tắc chọn. Module không có chức năng query; workflow metadata tương lai phải gọi guard này trước khi query và không được coi guard như phê duyệt phân tích.

Trước khi đo bất kỳ field mới, cần lập và commit **giao thức phân tích riêng**: evaluator, budget sai số tuyệt đối, gates và mẫu số, sample size/power, PSF/SED/gain truth, source noise và support routing. Khi metadata được phép lấy, đối chiếu chính xác observation ID, footprint/pixel, thời gian và nguồn giữa các split; 6° quanh center không chứng minh các exposure hoặc sai số hệ thống độc lập. Tách calibration khỏi validation và giữ nguyên final holdout cho một lần đánh giá sau khi các lựa chọn đã cố định. Nếu xuất hiện overlap, thiếu hỗ trợ hoặc không đủ power, dừng và ghi rõ; không nới tiêu chí sau khi xem kết quả.
