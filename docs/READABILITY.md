# Font tiếng Việt và độ dễ đọc — giao diện 0.5.4

## Font và bố cục

Be Vietnam Pro, năm độ đậm 400/500/600/700/800, bộ ký tự Vietnamese và Latin. Mười tệp WOFF2 tổng cộng 170.316 byte; giữ nguyên font từ Google Fonts, kèm SIL OFL và [provenance.json](../web/assets/fonts/provenance.json). CSS dùng font này cho nội dung, điều khiển, SVG và nhãn canvas, với Arial làm fallback. Chỉ tải asset cùng origin, tương thích CSP hiện có và demo offline.

Khoảng cách dòng của tiêu đề/nội dung tăng để dấu tiếng Việt không bị cắt. Hero chuyển sang hai hàng trong luồng bố cục, thay cho dải facts định vị tuyệt đối, nên nội dung xuống dòng không chồng nhau. Màu chữ phụ sáng hơn; badge có nền đặc; bảng có header và hàng xen kẽ rõ. Các nhãn dữ liệu/điều khiển chính có cỡ tối thiểu 12 px ở mobile.

Nhãn “Trước/Sau” trên canvas có nền đặc `#070d16`, viền màu và cỡ chữ theo kích thước hiển thị, thay vì luôn vẽ 17 pixel trong ảnh 1024 pixel rồi thu nhỏ. Nhãn tự được giới hạn trong mép khung; nhãn residual chỉ hiện cho vùng được chọn để giảm rối. Canvas vẽ lại khi font tải xong hoặc viewport đổi kích thước. Bản đồ giữ tên đầy đủ trong dropdown và chỉ nhấn nhãn sao đang chọn/hover/focus.

Panel nhận xét cuộn cùng trang trên màn hình thấp; chỉ sticky ở desktop đủ cao để chứa panel. Số đo, dữ liệu và quy tắc phân tích khoa học không thay đổi.

## Các cặp màu đã kiểm tra

Dùng relative luminance sRGB theo [W3C Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). Số dưới đây đo các cặp màu nền đặc; phần hero còn được kiểm tra trực quan vì nền ảnh thay đổi.

| Thành phần | Chữ / nền | Tương phản |
|---|---|---:|
| Nội dung | `#f6f7f8` / `#101419` | 17,23:1 |
| Chữ phụ | `#c3ccd7` / `#101419` | 11,39:1 |
| Trạng thái | `#ffd3a4` / `#2b2117` | 11,34:1 |
| Nhãn đo trên ảnh | `#d6fff6` / `#070d16` | 18,08:1 |
| Chữ biểu đồ | `#d1dce8` / `#101419` | 13,30:1 |
| Placeholder | `#b8c4d2` / `#12171e` | 10,17:1 |

## Kiểm tra giao diện

- Xác minh font 400/800 tải được với chuỗi có ă/â/đ/ê/ô/ơ/ư và dấu thanh.
- Kiểm tra hero, bảng, nhãn ảnh, menu và bộ chọn dữ liệu trên desktop 1.265 px và mobile 390 px; font 400/800 với chuỗi tiếng Việt đều tải thành công.
- Kiểm tra không tràn ngang trang, nội dung hero không đè lên facts; bảng rộng cuộn trong khung.
- Suite offline: 46/46 kiểm thử đạt. Smoke test production kiểm tra thêm hash của cả 10 tệp font cùng origin và thao tác MongoDB bằng review QA riêng.

Minh chứng: [desktop](wise0855-mission.jpg), [mobile](wise0855-vietnamese-mobile.jpg), [nhãn trên ảnh thật](wise0855-readable-overlay.jpg). Các phép đo màu trên không phải chứng nhận WCAG cho toàn bộ ứng dụng.

Ảnh giao diện và nhãn mới được cập nhật trong README. Milestone tiếp theo: kiểm thử luồng đọc chỉ số với người mới, đặc biệt ý nghĩa sai số và trạng thái chưa xác nhận, trước khi tăng mật độ thông tin.
