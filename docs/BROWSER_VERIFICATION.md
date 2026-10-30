# Kiểm tra web 0.10

Kiểm tra trực tiếp ngày 2026-10-30 trên trình duyệt trong ứng dụng, tại `http://127.0.0.1:8767/`. Môi trường local dùng API IRSA thật, còn review chỉ lưu ở trình duyệt. Đây chưa phải bằng chứng triển khai Vercel hoặc MongoDB production.

## Những đường đã chạy

- RA = 350°, Dec = +35°, FOV = 0.06°, D6, QR2: truy vấn trả 77 quan sát và tải PNG thật. Ảnh đầu MJD 60853.93441 có cutout SHA-256 `514ac17f7c8d2b7de1f723e4464dfc85a1caacf666f868e70fd844c9d80de8a6`; ảnh cuối MJD 61221.83881 có SHA-256 `2965965e13366ed397f1896f80025aa0facd42b0297141a6165a9407d5ffbb6c`. Ảnh cuối tải thành công 37 × 37 pixel; hai ảnh dùng khoảng xám −0.0399 đến 0.3072 MJy/sr. Hash là của cutout nguồn, không phải PNG.
- Ghim ảnh đầu, chọn ảnh cuối bằng bàn phím `End`, phát và dừng nhấp nháy: nhãn MJD, số ảnh, hash và slider chuyển theo ảnh đang hiện. Link FITS mang đúng cutout query. Đây chỉ là kiểm tra hiển thị, chưa căn chỉnh theo sao hay so phổ tại nguồn.
- RA 360° bị từ chối với thông báo phạm vi; không gửi truy vấn. Trường nhập tay được ghi nhãn `Tọa độ tự nhập` để tránh gắn nhầm tên mục tiêu mẫu.
- Lưu ghi chú QA local, thấy lịch sử tăng từ 0 lên 1; xóa, thấy lịch sử về 0 và thông báo đã xóa. Không dùng ghi chú thật.
- Mặc định WISE chọn bộ phổ gần nhau hơn; vị trí đo và vị trí dự báo chưa bật. Deep link `#covariance-validation` tự mở kho thí nghiệm cũ và giữ phần đó hiển thị.
- Menu mobile mở và đưa tới Khám phá. Ở viewport 390 × 844, không có input/select/button của phần Khám phá tràn ngang; chiều rộng document đo được 375 pixel. Font tiếng Việt và tương phản được xem trực tiếp. Chưa phải một audit screen-reader hoặc WCAG đầy đủ.
- Không có lỗi JavaScript được trình duyệt ghi nhận trong những đường này.

## Kiểm tra tự động liên quan

142 Python tests đạt trong môi trường local. `tests/explorer.test.cjs` và `tests/review-store.test.cjs` thực thi JS thật với DOM/HTTP test doubles; các ca lifecycle, mất phiên, GET/POST/DELETE chạy chồng, chọn ảnh nhanh, phản hồi cũ, đổi vùng, no-data và thang tương phản không khớp đều đạt trong V8. Những test này không thay thế kiểm tra trình duyệt hoặc cơ sở dữ liệu thật. GitHub CI còn phải được kiểm tra trên đúng commit triển khai.

Ảnh chụp tại [desktop](evidence/0.10/explorer-desktop.jpg) và [mobile](evidence/0.10/explorer-mobile.jpg). Dữ liệu IRSA có thể cập nhật; số quan sát và cutout trên đây là kết quả tại lần kiểm tra, không phải assertion cố định cho archive tương lai.

## Chưa nghiệm thu

Vercel bundle/timeout và nhận diện môi trường, MongoDB quota/TTL/owner isolation thật, review mất cookie nhiều tab, screen-reader, bàn phím toàn trang, phục hồi dữ liệu, tải đồng thời và phép đo khoa học độc lập. Không gọi trang đã đạt production chỉ dựa trên những bước ở trên.
