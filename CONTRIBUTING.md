# Đóng góp cho NoSleepClub

1. Đọc [tóm tắt đề](docs/CHALLENGE.md) và [lộ trình](docs/ROADMAP.md).
2. Tạo issue có mục tiêu cụ thể và điều kiện hoàn thành.
3. Tạo branch từ `main`, ví dụ `feat/sky-viewer`, `fix/coordinate-input` hoặc `docs/data-access`.
4. Giữ mỗi pull request tập trung vào một thay đổi có thể review; mô tả kết quả và cách kiểm chứng.

## Dữ liệu và bảo mật

- Không commit token, thông tin đăng nhập hoặc tệp `.env` chứa bí mật. Nếu cần cấu hình, thêm `.env.example` chỉ có tên biến và giá trị an toàn.
- Không commit ảnh FITS, bộ tải về hoặc cache lớn. Ghi cách tái tạo dữ liệu và dùng Git LFS hoặc kho dữ liệu phù hợp nếu nhóm thống nhất sau này.
- Ghi nguồn và điều kiện sử dụng cho dữ liệu, thư viện, hình ảnh và nội dung bên thứ ba.
- Phân biệt rõ dữ liệu thật, dữ liệu mô phỏng và kết quả suy luận trong tài liệu lẫn giao diện.

## Kiểm chứng

Chạy `python -m unittest discover -s tests -v` trong môi trường đã cài `requirements.txt`. Khi thay pipeline, tái sinh `web/data/` bằng `scripts/build_demo.py`, giữ provenance và ghi rõ giới hạn khoa học trong tài liệu.

Mỗi lần bàn giao cần có bản xem được, kiểm chứng đã làm, giới hạn còn lại và bước tiếp theo cụ thể để người dùng duyệt rồi tiếp tục. Xem `AGENTS.md`.
