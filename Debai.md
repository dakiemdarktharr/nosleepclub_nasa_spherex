# Checklist đề bài — Planet X and SPHEREx

> Checklist nghiệm thu theo challenge **Planet X and SPHEREx** của NASA Space Apps 2026. Các ô để trống là mục cần nhóm xác minh và tick khi có bằng chứng; không đồng nghĩa chức năng hiện chưa có.

**Nguồn chính thức**

- [Challenge Details](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details)
- [Challenge Resources](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=resources)

Đã đối chiếu nội dung trang chính thức ngày 14/11/2026. Challenge được xếp độ khó **Advanced**.

## 1. Mục tiêu bắt buộc

- [ ] **R1 — Công cụ công khai:** Xây dựng một web tool hướng tới công chúng.
- [ ] **R2 — Đúng dữ liệu:** Hiển thị ảnh bầu trời từ sứ mệnh NASA SPHEREx.
- [ ] **R3 — Tọa độ vùng trời:** Cho phép người dùng nhập tọa độ Right Ascension (RA) và declination (Dec) của một vùng trời.
- [ ] **R4 — Chuỗi theo thời gian:** Hiển thị một chuỗi ảnh của cùng vùng trời như một video ngắn.
- [ ] **R5 — Dễ nhận ra thay đổi:** Giúp người dùng nhanh chóng quan sát thay đổi theo thời gian và phát hiện các vật thể đang dịch chuyển.
- [ ] **R6 — Kiểm thử Barnard’s Star:** Thử công cụ trên Barnard’s Star.
- [ ] **R7 — Kiểm thử Epsilon Indi B:** Thử công cụ trên Epsilon Indi B, một cặp sao lùn nâu quay quanh một ngôi sao.
- [ ] **R8 — Kiểm thử WISE 0855:** Thử trên WISE 0855 tại RA 08h55m10.831s, Dec −7°14′42.53″; đây là sao lùn nâu chuyển động nhanh.
- [ ] **R9 — Kiểm thử RW Aurigae:** Thử công cụ trên sao biến quang RW Aurigae.
- [ ] **R10 — Kiểm thử R Draconis:** Thử công cụ trên sao biến quang R Draconis.

## 2. Bối cảnh khoa học của đề

Các ý dưới đây giải thích vì sao challenge quan tâm tới chuỗi ảnh; chúng không tự tạo thêm tính năng bắt buộc ngoài mục 1.

- SPHEREx lập bản đồ toàn bầu trời mỗi sáu tháng.
- Nhiệm vụ thu thập ảnh ở 102 dải cận hồng ngoại.
- Tập dữ liệu bao gồm hơn một tỷ vật thể; đề nhắc đến sao lùn nâu, sao chổi, tiểu hành tinh, sao, siêu tân tinh và thiên hà.
- Chuyển động biểu kiến giữa các thời điểm có thể giúp tìm vật thể mới và đo khoảng cách.

## 3. Các hướng mở rộng tùy chọn

Challenge ghi rõ các cân nhắc sau là **không bắt buộc**. Chỉ đánh dấu nếu nhóm chọn triển khai và có bằng chứng kiểm tra.

- [ ] **O1 — Cập nhật dữ liệu:** Thiết kế để dễ cập nhật các bản phát hành SPHEREx mới.
- [ ] **O2 — 102 dải hồng ngoại:** Tìm cách trình bày dữ liệu từ 102 dải để hỗ trợ khám phá.
- [ ] **O3 — Cộng theo detector:** Cân nhắc cộng dữ liệu của sáu mảng detector riêng rẽ để cải thiện signal-to-noise.
- [ ] **O4 — Phổ:** Có thể tạo phổ theo yêu cầu.
- [ ] **O5 — Cộng/trừ ảnh:** Cho phép cộng hoặc trừ các ảnh lấy ở những thời điểm khác nhau.
- [ ] **O6 — Trường nhìn:** Cho người dùng chọn field of view, nêu rõ đánh đổi giữa vùng quan sát rộng hơn và thời gian truyền dữ liệu lâu hơn.
- [ ] **O7 — Overlay catalog:** Cho phép chồng dữ liệu từ các sứ mệnh khác như Gaia hoặc WISE.
- [ ] **O8 — Chia sẻ tọa độ:** Cho phép đặt tọa độ trong URL để nhúng/chia sẻ truy vấn.
- [ ] **O9 — Metadata:** Hiển thị metadata hữu ích, ví dụ cờ nhiễm.
- [ ] **O10 — Công cụ thiên văn:** Đánh giá công cụ công khai như Astropy để xử lý dữ liệu và Aladin để hiển thị dữ liệu thiên văn.

## 4. Tài nguyên chính thức để tham khảo

Các liên kết dưới đây là tài nguyên tham khảo, không phải yêu cầu phải tích hợp tất cả vào sản phẩm.

- [ ] Xem tài nguyên SPHEREx của NASA/IPAC Infrared Science Archive (IRSA).
- [ ] Xem các tutorial notebook SPHEREx và cách truy cập dữ liệu bằng Python.
- [ ] Tham khảo WiseView như một sản phẩm tương tự để lấy cảm hứng.
- [ ] Dùng Gaia Data Release 3 nếu sản phẩm cần dữ liệu Gaia.
- [ ] Xem tài nguyên NEOSSat/CADC của Canadian Space Agency nếu phù hợp.

## 5. Quy ước nghiệm thu

- Mỗi ô chỉ được tick khi có bằng chứng cụ thể trong ứng dụng, dữ liệu, kiểm tra hoặc tài liệu.
- Với mục kiểm thử, ghi lại tọa độ/truy vấn, số quan sát, thời điểm ảnh đầu/cuối, và trạng thái nếu dữ liệu nguồn không có.
- Không diễn giải khác biệt ảnh thành phát hiện thiên thể đã xác nhận nếu chưa có kiểm chứng khoa học độc lập.
