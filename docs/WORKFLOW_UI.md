# Giao diện theo quy trình

Giao diện xử lý một bộ dữ liệu tại một thời điểm, qua bốn màn hình.
[Mở ứng dụng](https://nosleepclub-nasa-spherex.vercel.app/#home).
Đây là thay đổi giao diện và quản lý ngữ cảnh; không chạy lại phép đo khoa học.

| Bước | Bộ mẫu WISE 0855 | Ảnh tìm tại IRSA |
|---|---|---|
| 1. Dữ liệu | Chọn bộ ảnh; xem ảnh SPHEREx thật thu nhỏ trước/sau | Nhập tọa độ, release, detector và trường nhìn; tìm metadata rồi tải cutout |
| 2. So ảnh | Kéo vạch, song song, ảnh sai khác hoặc nhấp nháy; chọn WISE/residual | Giữ ảnh A, chọn ảnh B; so nhấp nháy các ảnh đã tải cùng thang hiển thị |
| 3. Kiểm tra | Vector/SNR WISE chỉ hiện khi chọn WISE; residual có tọa độ và điểm riêng | Xem ID hai ảnh, mask, nguồn, quy ước hiển thị và giới hạn; chưa fit chuyển động |
| 4. Ghi nhận | Nhận xét riêng gắn đúng analysis hash, scene và vùng; cơ chế API MongoDB giữ nguyên | Xuất JSON kèm đúng truy vấn, cặp A/B và ghi chú; không POST nhận xét IRSA vào API WISE |

Thanh bước và nút chính dùng cùng thứ tự. Mỗi màn có nút quay lại; đổi màn không
đổi dữ liệu. Quay về chọn dữ liệu là một hành động rõ ràng. Chuyển sang kho kiểm
chứng giữ vị trí để trở lại quy trình.

## Bớt chữ, giữ thông tin quyết định

- Bỏ trang mở đầu minh họa lớn, các đoạn quảng bá và hướng dẫn lặp dưới tiêu đề.
  Ảnh chọn dữ liệu là thumbnail SPHEREx của chính scene; Canva nằm trong hướng
  dẫn và vẫn được ghi là minh họa.
- Chi tiết kỹ thuật, provenance, hash và giới hạn dài nằm trong mục mở khi cần.
  Đơn vị, nhãn ảnh thật/nguồn giả, cảnh báo sai số chưa hiệu chuẩn và lỗi chất
  lượng ảnh hưởng quyết định vẫn hiển thị cạnh bước liên quan.
- Kho kiểm chứng tách khỏi bốn màn. Chỉ một báo cáo được hiển thị, có đường quay
  về danh sách và quay về công việc. Báo cáo lịch sử không được trình bày như kết
  quả phân tích tọa độ IRSA đang chọn. Các journal lớn vẫn là tải theo yêu cầu.
- Dùng font Be Vietnam Pro cục bộ, nền đặc, nhãn trường và focus rõ; không đặt chữ
  xử lý dữ liệu lên ảnh trang trí.

## Ràng buộc ngữ cảnh

Nút đi tiếp chờ dữ liệu sẵn sàng. IRSA cần giữ A và tải B khác trước khi sang kiểm
tra/ghi nhận. Xem màn kiểm tra được nhớ theo chữ ký của bộ ảnh và vùng; thay đổi
scene, vùng, truy vấn hoặc cặp ảnh sẽ yêu cầu kiểm lại. Đây là thứ tự thao tác,
**không phải một gate xác nhận khoa học**.

Khi tải scene mới, dữ liệu cũ không được coi là scene mới đã sẵn sàng. Lỗi về trễ
của request cũ không ghi đè scene mới. Nhấp nháy dừng khi rời màn so ảnh và giữ
cặp đã chọn, kể cả đang hiển thị ảnh A tại thời điểm bấm tiếp.

Ghi chú IRSA được giữ trong bộ nhớ theo truy vấn và hai URL nguồn; đổi cặp không
gắn nhầm ghi chú cũ, quay lại cùng cặp khôi phục nháp. Các nháp này chưa được lưu
qua lần reload/đóng trang; nút **Xuất ghi nhận JSON** là đầu ra cần lưu. Nhận xét
WISE vẫn theo vòng đời riêng của ReviewStore/API, không chuyển sang vùng IRSA.

## Điều hướng và bàn phím

`#home` là màn dữ liệu; `#compare-step`, `#check-step`, `#review-step` giữ nguồn
đang chọn. Link cũ `#workspace` mở WISE, `#explore` mở truy vấn IRSA, và các link
báo cáo như `#signal-controls`/`#profile-landscape` vẫn có đích. Back/Forward
đổi màn, không khởi tạo lại bộ dữ liệu.

Skip link chỉ đưa focus vào nội dung hiện tại. Mỗi lần đổi màn, focus chuyển đến
tiêu đề; mở báo cáo bằng Enter không để focus trong danh sách đã ẩn. Hướng dẫn
quay lại nguồn đang dùng, không âm thầm chuyển IRSA sang WISE.

Các kiểm tra bàn phím và reflow chỉ xác minh những thao tác đã thử; chưa thay
thế đánh giá screen reader hoặc kiểm toán WCAG đầy đủ.

## Giới hạn khoa học giữ nguyên

Ảnh IRSA mới là cutout đặt trên WCS hiển thị, chưa căn chỉnh sao, ghép phổ tại
nguồn hay fit chuyển động. Phép đo WISE đang dùng sản phẩm có điều kiện đã công
bố. Residual chưa có danh tính thiên thể; số fit chạy được không chứng nhận phát
hiện. Không đổi ngưỡng, PSF, covariance hoặc sản phẩm khoa học đã khóa; 252 ô
assessment và 30 trường dành riêng vẫn chưa mở.

## Bước tiếp theo

Thử với ba người mới: mỗi người hoàn thành cả luồng WISE và IRSA, giữ đúng dữ
liệu/vùng khi quay lại và xuất/lưu đúng ghi nhận mà không cần nhắc đường đi.
Ghi lại điểm dừng và hiểu nhầm, đặc biệt giữa residual, vector WISE và báo cáo
nguồn giả. Sau vòng này, tiếp tục milestone khoa học tách bias diện tích pixel,
template và nguồn chồng đã nêu trong SIGNAL_CONTROL_RESULTS.md.

Preview cục bộ:

```powershell
.venv/Scripts/python.exe -m scripts.serve_app --port 8770
```

Mở `http://127.0.0.1:8770/#home`. Runtime web vẫn tách khỏi môi trường tính toán
khoa học; không thêm Node runtime hoặc framework build vào ứng dụng.
