# Vercel + MongoDB

Vercel project: `nosleepclub-nasa-spherex`, root `web/`, production public, preview vẫn có SSO. Static HTML/CSS/JS, một Python 3.12 Function `/api/reviews`, Singapore `sin1`. Không cài Node hoặc các dependency khoa học lên runtime web. Hướng dẫn [Python /api chính thức](https://vercel.com/docs/functions/runtimes/python/api-directory).

MongoDB Atlas project riêng `NoSleepClub_NASA_SPHEREx`, cluster M0 `nosleepclub-spherex`, AWS Singapore. Database `nosleepclub_nasa_spherex`; DB user chỉ có `readWrite` database này và giới hạn cluster này. `MONGODB_URI` là biến **sensitive chỉ production** trong Vercel; không có ở frontend, repo hoặc preview. Không log URI, cookie hay nội dung nhận xét.

User đã chấp thuận rõ việc lưu credential vào project này và allowlist `0.0.0.0/0` để Vercel dùng IP egress động. Kết nối vẫn bắt buộc TLS và xác thực; allowlist này cho mọi IP thử kết nối nếu biết endpoint. Không bật gói Static IP trả phí. Khi cần thu hẹp mạng cho production có dữ liệu nhạy cảm, lựa chọn egress/proxy riêng phải được thiết kế và phê duyệt chi phí trước.

API cấp session cookie `__Host-`, Secure, HttpOnly, SameSite=Strict; database chỉ giữ hash token. Không có danh sách review công khai hay quyền chọn owner từ payload. POST/DELETE kiểm tra Origin/Host HTTPS; kiểm tra scene/selection và hash phân tích theo manifest phía server, tự lấy hash dữ liệu đầu vào. Giới hạn body 8 KiB, note 2.000 ký tự, tối đa 100 review/session; giới hạn 90 request/phút theo hash IP, TTL rate bucket 2 phút. Guest session chưa thay thế đăng nhập/Bot protection cho quy mô lớn.

Review hết hạn sau 180 ngày theo TTL index; người dùng có thể xóa và xuất JSON. Cookie bị mất hoặc đổi thiết bị sẽ không lấy lại cùng phiên. Nếu server lỗi, lưu giữ bản local và hiện “Chưa đồng bộ”; không tự chuyển dữ liệu local cũ lên cloud. Trình server localhost vẫn hoạt động hoàn toàn offline và giữ local review.

Schema, index và rate limit được tạo khi API kết nối lần đầu. Kết quả QA production cần kiểm tra thực tế: anonymous GET, POST lưu, GET đọc lại cùng session, session khác không đọc được, cross-origin bị chặn, DELETE dữ liệu QA và GET xác nhận rỗng. Không dùng nhận xét thật của người dùng để thử.

Biến môi trường mẫu ở `web/.env.example`, tuyệt đối không thay bằng URI thật trong Git. Backend dependency pin trong `web/requirements.txt`, độc lập `requirements.txt` cho phân tích offline. Build từ commit GitHub đã kiểm tra; sau deployment kiểm tra runtime/readiness và API, không chỉ build status.
