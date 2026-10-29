# Luồng khám phá cho người mới

Tham khảo trực tiếp NASA.gov và SpaceX.com ngày 2026-10-30: hero dùng ảnh lớn, chữ trắng có tương phản, điều hướng ngắn và hành động rõ. Không sao chép logo, ảnh, bài viết hay mã nguồn của hai trang.

Token: đen vũ trụ `#000000`, nền công cụ `#101419`, bề mặt `#191f27`, trắng `#f6f7f8`, xám đọc được `#c3ccd7`, cam đánh dấu `#ffb36a`. Từ giao diện 0.5.4 dùng Be Vietnam Pro tự host, gồm Vietnamese/Latin và năm độ đậm; Arial làm fallback. Dùng tabular numbers cho phép đo, không dùng monospace trang trí. Nhãn trên ảnh có nền riêng; thông tin hero nằm trong luồng bố cục để chữ xuống dòng không chồng dải facts.

```text
Điều hướng: Nhiệm vụ | Quan sát | Kiểm chứng | Ghi nhận
Hero minh họa Canva + Bắt đầu quan sát / Hướng dẫn
1 So ảnh → 2 Xem bằng chứng → 3 Lưu nhận xét
Quan sát: ảnh thật lớn | mục tiêu + nhận xét
  Đổi bộ ảnh, mode, zoom, chọn điểm luôn là thao tác thật
  Tọa độ, thuật ngữ và cấu hình cũ mở theo nhu cầu
Kiểm chứng: QR3 có dữ liệu? → 30 vùng mới → kết luận có đạt không?
Bước kế: mục tiêu và tiêu chí chấp nhận
```

So với một dashboard kỹ thuật, phần mặc định ưu tiên ảnh, chỉ dẫn thao tác đúng lúc và ý nghĩa kết quả. Không đặt chồng bảng covariance, source ID và danh sách phiên bản lên luồng nhập môn. Người có kinh nghiệm vẫn truy cập đủ Gaia, FITS, CSV/JSON, nguồn, hash và hạn chế. Không ẩn trạng thái “Chưa xác nhận”.

Asset hero và minh họa hai thời điểm do Canva tạo theo brief riêng; cả hai được ghi là minh họa, không đặt làm ảnh quan sát. FITS/overlay giữ nguyên sản phẩm khoa học. Mọi số liệu trong hero và báo cáo lấy từ dữ liệu thực, không từ ảnh Canva.

Tiêu chí UX: từ trang đầu đến ảnh chỉ một nút; đến nhận xét từ vùng quan sát bằng một hành động; menu mobile đóng/mở bằng bàn phím; hướng dẫn giải thích mục tiêu, ảnh bị vỡ hạt, ellipse và vì sao chưa xác nhận; không tràn trang ở 390 px; tôn trọng reduced motion; modal có nhãn/đóng và không làm mất lựa chọn dữ liệu; review MongoDB còn lưu/xóa hoạt động.

Canva assets: [Hero](https://www.canva.com/M/MAHZbvmhEbQ), [hướng dẫn hai thời điểm](https://www.canva.com/M/MAHZbsQBgXg). Bản WebP giữ trong `web/assets/`, metadata/hash trong `provenance.json`. Không hotlink URL thumbnail có hạn dùng. Mã frontend chính trong `mission.css`/`mission.js`; canvas và phép đo giữ `app.js`. Menu, chọn bộ ảnh, bốn mode, zoom, modal, bộ lọc phổ/ePSF và xem bản đồ kiểm thử đều thực hiện hành động thật.
