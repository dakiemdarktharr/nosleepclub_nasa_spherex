# Khám phá tọa độ và chuỗi ảnh SPHEREx

Nhập RA theo độ hoặc giờ:phút:giây, Dec theo độ hoặc độ:phút:giây. Chọn DR1 hoặc QR3, detector, kích thước ảnh hiển thị và khoảng ngày tùy chọn rồi tìm ảnh. DR1 là mặc định. Liên kết QR2 cũ báo người dùng tìm bản DR1 đã xử lý lại. Metadata SIA được tìm bằng cone 0,001° quanh tọa độ tâm và BAND theo dải detector; FOV chỉ điều khiển kích thước cutout sau khi đã tìm được ảnh phủ tâm. Metadata SIA mô tả phạm vi của toàn detector. [Các bản phát hành và trạng thái QR2](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/).

Ảnh tải theo nhu cầu từ dịch vụ cutout IRSA, dùng WCS/SIP thật để đặt lên lưới TAN bắc trên/đông trái với 6,15″/pixel. Giữ một ảnh đối chiếu rồi chọn khung khác để nhấp nháy A/B. `Phát chuỗi` hoạt động khi đã mở ít nhất ba ảnh có cùng thang hiển thị và policy mask, obs ID và MJD UTC riêng, cùng detector, pixel tâm khả dụng và giao dải WCS-WAVE tại tâm đạt ít nhất 75% độ rộng dải rộng nhất trong chuỗi. Ngưỡng này là quy tắc hiển thị. Căn chỉnh sao, đáp ứng phổ, biến quang và chuyển động cần kiểm chứng riêng. Link FITS trỏ đúng cutout được hash, kể cả phần mở rộng để bao góc xoay. [Giới hạn WCS-WAVE](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/).

**So sánh A/B** giữ cùng lưới, quy tắc mask và mức hiển thị. Chọn một lần quan sát và một dải detector trên mỗi ô. Cả hai ô dùng chung độ phóng đại và tâm khi kéo, bấm phím mũi tên hoặc đặt lại. Dải danh nghĩa nằm trong bộ chọn. WCS-WAVE dưới ảnh là bước sóng tại tâm, khi xác định được từ FITS. Đổi dải ở một ô giữ nguyên ảnh bên kia và tra IRSA cho dải mới. Mở **Chuỗi thời gian** để xem các lần chụp và bật phát cho các khung tương thích. Bước sóng có thể biến thiên qua trường. [Hướng dẫn trực quan IRSA](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/visualization.html)

Kiểm tra production ngày 15/11/2026 cho RW Aurigae: cone 0,001° trả 38 ảnh DR1 D6 trong 1,9 giây, không bị cắt; cone 0,20° trên cùng tọa độ hết thời gian chờ, kể cả khi giảm `MAXREC` từ 500 xuống 100. Vì vậy truy vấn ảnh phủ điểm được giữ nhỏ độc lập với FOV hiển thị.

Cam biểu thị pixel bị loại theo FLAGS, tím là vùng thiếu hoặc ngoài ảnh. Nearest-neighbor phục vụ hiển thị, còn photometry cần phép lấy mẫu bảo toàn flux và sai số phù hợp. Trình duyệt thử tải lại cutout một lần khi IRSA trả lỗi tạm thời hoặc ngắt stream. Nếu ảnh vẫn thiếu, người dùng thấy lỗi và có thể chọn lại từ danh sách. Các giới hạn request và cache giữ tải trong biên cho phép. IRSA vẫn có thể chậm hoặc không sẵn sàng.

`web/data/challenge-targets.json` ghi nguồn và epoch của các tâm mẫu. WISE 0855 và Barnard được dự báo tới năm 2026 để tránh việc tâm catalog cũ làm nguồn chuyển động nhanh ra khỏi khung. Epsilon Indi B dùng tọa độ trường ESO lịch sử và FOV rộng hơn; cặp chưa được phân giải. Những tọa độ này chỉ hướng dẫn tìm vùng, không phải phép đo độc lập.

Ngày 30/10/2026 đã lấy hai cutout thật tại mỗi tâm mục tiêu. Mười PNG QR2 lịch sử cùng metadata, URL và hash nằm ở `web/data/explorer-check/`. Khi IRSA ngừng tra QR2, bộ ảnh này vẫn là dữ liệu mẫu đã ghim. [Danh mục trường thử](DATASET_CATALOG.md).

## Kiểm tra DR1 và QR3 ngày 14/11/2026

API đã đọc VOTable SIA của cả hai bản dữ liệu tại năm tâm, dùng cone 0,001°, band 4,415–4,996 µm, MAXREC 100, sau đó lọc detector D6.

| Tâm trường | DR1 D6 | QR3 D6 |
| --- | ---: | ---: |
| WISE 0855 | 45 | 0 |
| Barnard’s Star | 41 | 17 |
| Epsilon Indi B | 49 (truncated) | 36 |
| RW Aurigae | 38 | 18 |
| R Draconis | 30 (truncated) | 21 |

IRSA trả hai cutout Barnard’s Star có FLAGS theo schema mới. Renderer xuất PNG tại FOV yêu cầu 0,05° với 929 pixel khả dụng từ DR1 và 193 pixel khả dụng từ QR3. QR3 thiếu 763 pixel vì vùng chụp chỉ giao một phần. SHA-256 cutout DR1 là `79c70ed83d50a7c9f1c0848547bf8e44add6270bb41384564bf82c411d2ab8d2`, QR3 là `5005ce035d4748c47b19dec3cef6362bffe51c06480af8fa1a929a6531e7d445`. Pixel tâm bị mask hoặc nằm ngoài ảnh ở hai khung này nên chúng không đủ điều kiện cho chuỗi WCS-WAVE. [Nguồn DR1](https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W33_2C/l2b-v27-2026-228/6/level2_2025W33_2C_0321_1D6_spx_l2b-v27-2026-228.fits?center=269.446266885%2C4.76822221648&size=0.08612855) · [Nguồn QR3](https://irsa.ipac.caltech.edu/ibe/data/spherex/qr3/level2/2026W33_2A/l2b-v27-2026-241/6/level2_2026W33_2A_0594_3D6_spx_l2b-v27-2026-241.fits?center=269.446266885%2C4.76822221648&size=0.08612855).

Ba ảnh DR1 D6 của vùng **Epsilon Indi B** qua kiểm tra hiển thị chuỗi với tâm RA 331,04583333°, Dec −56,78333333°, trường nhìn 0,12°. Chúng có giao dải WCS-WAVE tại tâm bằng **99,755%** độ rộng dải lớn nhất. Các PNG dùng chung lưới 71×71 pixel, policy mask và tương phản cố định theo ảnh đầu. Đây là vùng ảnh có thể phát theo thời gian. Việc phân giải cặp sao hay đo chuyển động của chúng cần phép đo độc lập.

| Bắt đầu UTC | Observation ID | Bước sóng tại tâm (µm) | Pixel khả dụng |
| --- | --- | ---: | ---: |
| 29/04/2025 01:35:28 | `2025W18_1B_0081_3` | 4,458349 | 4.885 |
| 01/05/2025 13:57:52 | `2025W18_2B_0011_3` | 4,458435 | 4.948 |
| 07/05/2025 05:14:15 | `2025W19_1B_0344_3` | 4,458371 | 4.609 |

Trong Bầu trời, chọn **Epsilon Indi B → So sánh ảnh** để tải lần lượt ba ảnh trên. Khi dùng server local, cũng có thể [mở truy vấn Epsilon Indi B ngày 29/04–07/05/2025](http://127.0.0.1:8767/?lang=vi&sky_ra=331.04583333&sky_dec=-56.78333333&sky_fov=0.12&sky_det=6&sky_release=dr1&sky_from=2025-04-29&sky_to=2025-05-07&sky_sequence=epsilon-dr1&sky_autoload=1#explore). Nhấn **Phát chuỗi** sau khi ba ảnh sẵn sàng. Chromium đã đọc ba cutout từ truy vấn live trả 25 hàng, phát đúng thứ tự và tạm dừng. JSON giữ URL gốc, processing version và SHA-256 của metadata SIA, FITS và PNG. Một số lần gọi IRSA khác trong cùng phiên bị chậm, lỗi HTTP 503 hoặc ngắt khi tải. [Receipt chuỗi DR1](data/spherex-dr1-timeline-smoke.json)

Chọn **Mở chuỗi ảnh đã lưu** trên cùng thẻ Epsilon Indi B để phát ba PNG có hash trùng receipt mà không cần chờ IRSA. Tùy chọn này cũng chạy với server tĩnh `python scripts/serve_demo.py`. Giao diện giữ giờ UTC và liên kết FITS của từng khung. [Metadata của ba ảnh đã lưu](../web/assets/mission/epsilon-sequence/provenance.json)

## Chạy tại máy

Sau khi cài `requirements.txt` và `web/requirements.txt`:

```powershell
python -m scripts.serve_app --port 8767
```

Mở http://127.0.0.1:8767/#explore. Launcher chỉ bind loopback, bật rõ local API budgets; không nạp secret production. `python scripts/serve_app.py --check` kiểm tra imports mà không mở socket. Bản chỉ dùng sản phẩm đã xuất vẫn mở bằng `python scripts/serve_demo.py` ở port 8766; server tĩnh đó không chạy hai API mới. Review local nằm trong trình duyệt, còn cloud review chỉ ở production có credential đã được cấp.

Gói JSON xuất từ explorer lưu query, metadata IRSA, headers provenance của các frame đã xem, thang hiển thị và ý kiến cá nhân. Ghi chú explorer hiện xuất thành tệp, chưa thành hồ sơ review cộng tác hay xác nhận khoa học. Review các phân tích WISE cố định vẫn dùng API khách có ID và expiry riêng.

Xem [observations API](OBSERVATION_API_CONTRACT.md), [frame API](FRAME_API_CONTRACT.md), [quota](API_ABUSE_CONTROLS.md), [kiểm chứng và các giới hạn còn mở](PRODUCTION_READINESS.md).
