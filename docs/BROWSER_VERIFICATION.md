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

## Bổ sung sau triển khai và nghiên cứu mới

- Production `c88fe57`, deployment `dpl_CWVm5qSJb2d7npBPv1ngV7vw3HGG`: [24 response checks](evidence/0.10/production-c88fe57.json) đạt, gồm commit API, cutout thật, review transaction/isolation/expiry và cleanup QA. Đây bổ sung bằng chứng API còn thiếu ở phần trên; không phải phép tải đồng thời hay chờ TTL 180 ngày thực sự trôi qua.
- Trình duyệt production xác nhận mặc định phổ chặt, nhãn chưa hiệu chuẩn, overlays đo/dự báo chưa bật và lưu trữ MongoDB. Tab từ nút cuối dialog về nút đóng; Shift+Tab quay lại nút cuối; Escape đóng và trả focus về `workspace-help`. [Ảnh focus production](evidence/0.10/dialog-keyboard-production.png). Menu mobile Escape trả `aria-expanded=false`, focus về nút menu; document không tràn ngang ở viewport yêu cầu 390 × 844 (content area đo được 375 pixel).
- Bảng sandwich mới đã thử **local**, chưa dùng ảnh chụp này để xác nhận deployment: mở bằng Enter, mặc định 68%/toàn bộ; đổi 50/95% và accepted cập nhật đúng tử/mẫu. Ví dụ w090p10 SNR2 ở 95% accepted cho GN/H/sandwich là 95/124, 108/124, 101/124. Không có lỗi JavaScript trong các thao tác này. [Desktop](evidence/0.10/sandwich-desktop.png), [mobile](evidence/0.10/sandwich-mobile.png); bảng giữ cuộn ngang riêng, control không tràn trang.
- Trang chỉ tải overview sandwich khoảng 177 KB khi mở; bản audit 8,2 MB là liên kết tải chủ động. Cả hai chứa hash để đối chiếu; biểu đồ/bảng không thêm một phép đo WISE mới.

Screen-reader thực, keyboard toàn trang, reflow 200–400%, mobile/touch thực, mất cookie nhiều tab, load/restore và khoa học độc lập vẫn chưa được nghiệm thu đầy đủ.

Bảng sandwich sau đó đã kiểm trên **production c65d79b**: deep link tự mở, cả sáu hàng mặc định khớp JSON; đổi 95%/accepted giữ đúng 95/124, 108/124 và 101/124 ở w090p10 SNR2, không có JS error trong thao tác. [Ảnh production](evidence/0.10/sandwich-production.png). [Receipt 30 response checks](evidence/0.10/production-c65d79b.json) xác minh hash các artifact mới; lượt fail 502 trước đó được giữ riêng trong evidence. Kiểm chứng này không thay phép đo khoa học hay các audit còn thiếu.

Local sau sửa mask API 1.1 (31/10/2026 giờ Việt Nam): truy vấn 350°/+35° trả 77 quan sát; ảnh đầu thật hiển thị 1.335 pixel khả dụng, 34 bị loại, 0 thiếu trên grid 37×37, cùng mức xám −0,0399–0,3072 MJy/sr. Không có JS error trong đường này. Test JS thực thi thêm ca từ chối ghép hai mask policy khác nhau, rồi tìm lại vùng để reset policy; toàn bộ suite explorer đạt trong V8. Chưa dùng thử local này để xác nhận policy mới đã deploy.

Sau merge PR #5, [receipt public fc17f96](evidence/0.10/production-fc17f96.json) đã xác minh byte các asset, API 1.1, policy và 1.335/34/0 pixel qua HTTP. Browser-control session trở nên không khả dụng khi kiểm lại giao diện public; không có ảnh chụp hoặc xác minh tương tác mới của production này. Ảnh production c65d79b phía trên vẫn chỉ chứng nhận đúng phiên bản được ghi. Công cụ fetch protected preview bị auto-review chặn vì tạo/tái sử dụng authenticated share link 23 giờ; không dùng link đó hoặc thay access protection để vượt qua.
