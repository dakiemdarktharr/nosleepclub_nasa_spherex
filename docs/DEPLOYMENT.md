# Vercel + MongoDB

Vercel project: `nosleepclub-nasa-spherex`, root `web/`, production public, preview vẫn có SSO. Static HTML/CSS/JS, các Python Functions `/api/reviews`, `/api/observations`, `/api/frame`, Singapore `sin1`. Không dùng Node ở runtime web. Bản 0.10 cài riêng Astropy/NumPy/Pillow để đọc FITS/WCS và dựng ảnh; các phép fit khoa học nặng vẫn chạy offline. Hướng dẫn [Python /api chính thức](https://vercel.com/docs/functions/runtimes/python/api-directory).

MongoDB Atlas project riêng `NoSleepClub_NASA_SPHEREx`, cluster M0 `nosleepclub-spherex`, AWS Singapore. Database `nosleepclub_nasa_spherex`; DB user chỉ có `readWrite` database này và giới hạn cluster này. `MONGODB_URI` là biến **sensitive chỉ production** trong Vercel; không có ở frontend, repo hoặc preview. Không log URI, cookie hay nội dung nhận xét.

User đã chấp thuận rõ việc lưu credential vào project này và allowlist `0.0.0.0/0` để Vercel dùng IP egress động. Kết nối vẫn bắt buộc TLS và xác thực; allowlist này cho mọi IP thử kết nối nếu biết endpoint. Không bật gói Static IP trả phí. Khi cần thu hẹp mạng cho production có dữ liệu nhạy cảm, lựa chọn egress/proxy riêng phải được thiết kế và phê duyệt chi phí trước.

API cấp session cookie `__Host-`, Secure, HttpOnly, SameSite=Strict; database chỉ giữ hash token. Không có danh sách review công khai hay quyền chọn owner từ payload. POST/DELETE kiểm tra Origin/Host HTTPS; kiểm tra scene/selection và hash phân tích theo manifest phía server, tự lấy hash dữ liệu đầu vào. Giới hạn body 8 KiB, note 2.000 ký tự, tối đa 100 review/session; giới hạn 90 request/phút theo hash IP, TTL rate bucket 2 phút. Guest session chưa thay thế đăng nhập/Bot protection cho quy mô lớn.

Review hết hạn sau 180 ngày theo TTL index; người dùng có thể xóa và xuất JSON. Cookie bị mất hoặc đổi thiết bị sẽ không lấy lại cùng phiên. Nếu server lỗi, lưu giữ bản local và hiện “Chưa đồng bộ”; không tự chuyển dữ liệu local cũ lên cloud. Trình server localhost vẫn hoạt động hoàn toàn offline và giữ local review.

Schema, index và rate limit được tạo khi API kết nối lần đầu. Kết quả QA production cần kiểm tra thực tế: anonymous GET, POST lưu, GET đọc lại cùng session, session khác không đọc được, cross-origin bị chặn, DELETE dữ liệu QA và GET xác nhận rỗng. Không dùng nhận xét thật của người dùng để thử.

Đã xác minh production từ commit `244f5377bd56149e859c39aa2a09b96688919bf7`, deployment `dpl_6iExhUFB4TxF7vandvCxZzSnA1dt`, runtime Python 3.12 ở `sin1`, trạng thái READY. URL public: https://nosleepclub-nasa-spherex.vercel.app. HTTP: site/GET/POST/DELETE đều 200; Origin lạ 403; hash cũ 400; đọc lại đúng nội dung; phiên khác không thấy review; xóa và xác nhận rỗng. Kiểm tra nút lưu/xóa trên giao diện public cũng qua, badge “MongoDB”, không có lỗi JavaScript. Không để lại review QA. Script chạy lại: `python -m scripts.smoke_production` (cần requests/truststore, chỉ tạo/xóa review riêng của bài test).

Ở checkpoint triển khai ban đầu, 38 kiểm thử offline qua. Xem README và báo cáo theo phiên bản để biết kiểm chứng mới nhất. Kiểm tra giao diện desktop và viewport 390 px: không tràn ngang trang; bảng rộng cuộn trong khung. Subtext được ẩn, nhãn/đơn vị/trạng thái chưa xác nhận được giữ lại. Giới hạn khoa học ở hộp bằng chứng và tài liệu accuracy.

Biến môi trường mẫu ở `web/.env.example`, tuyệt đối không thay bằng URI thật trong Git. Backend dependency pin trong `web/requirements.txt`, độc lập `requirements.txt` cho phân tích offline. Build từ commit GitHub đã kiểm tra; sau deployment kiểm tra runtime/readiness và API, không chỉ build status.


Bản 0.8 bổ sung các sản phẩm tĩnh `data/covariance/`, không đổi schema nhận xét hoặc secret. Smoke test đối chiếu hash design, calibrator, seal, overview và từng trường validation với repo, rồi thực hiện cùng chu trình MongoDB bằng review QA riêng. Bộ phân tích nền/ePSF/covariance vẫn chạy offline; Vercel không chạy fit khoa học khi người dùng mở trang.


Bản 0.9 thêm `data/ablation/` và bảng chọn mô hình/hiệu chuẩn có miền hỗ trợ; runtime web và schema MongoDB không đổi. Script smoke đối chiếu hash design, selection, calibrator, seal, summary và ba kết quả trường mới trước chu trình review QA. Wrapper offline `python -m scripts.run_ablation <phase>` chặn ghi đè các phase hoàn tất; không chạy các fit qua API web.


Bản 0.10 thêm hai API đọc dữ liệu IRSA và dựng ảnh thật. Frame có deadline/socket/byte caps, cache và quota; cấu hình maxDuration=120 cần được deployment thực chấp nhận (Hobby cần Fluid compute). Guard production cần system env VERCEL_ENV đúng và URI MongoDB hiện có; thiếu ngữ cảnh triển khai thì fail-closed, local chỉ bật rõ bởi serve_app. Xem SKY_EXPLORER.md và API_ABUSE_CONTROLS.md. Chưa coi cấu hình file là bằng chứng deployment hoặc SLO. Goal và các nghiệm thu còn mở ở PRODUCTION_READINESS.md.
