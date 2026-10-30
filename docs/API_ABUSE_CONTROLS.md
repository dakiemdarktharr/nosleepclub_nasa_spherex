# Giới hạn truy vấn API công khai

`/api/observations` và `/api/frame` kiểm tra giới hạn **sau xác thực tham số và trước truy vấn IRSA**. Quota đề xuất cho demo ban đầu, không phải SLO hay bằng chứng chống DDoS:

| Endpoint | Mỗi IP/phút | Toàn bộ IP/phút |
| --- | ---: | ---: |
| observations | 12 | 60 |
| frame | 8 | 24 |

Mỗi process còn có bộ lọc burst tối đa 8 request cho cùng IP và endpoint trong một cửa sổ giây, trước khi ghi MongoDB; trạng thái được khóa thread và giới hạn 4.096 khóa, khóa cũ bị loại khi đầy. Cửa sổ phút/giây cố định nên có thể có burst quanh ranh giới. Bộ nhớ chỉ thuộc từng process, không chia sẻ giữa instance/cold start; **không phải quota phân tán**. Khi bộ lọc chặn, API trả 429, `Retry-After` theo giây, `Cache-Control: no-store` và `X-Request-ID`. Không có dữ liệu IP thô, URL, tọa độ hay note trong log của guard/API.

Khi có `MONGODB_URI`, các instance dùng collection `api_limits` trong database sẵn có. Mỗi counter được tăng nguyên tử bằng `find_one_and_update`; key là SHA-256 của namespace môi trường, endpoint, phút và scope/IP đã hash. TTL index trên `expires_at` xóa bucket sau khoảng 1–2 phút; expiry TTL là dọn dẹp bất đồng bộ, quota dựa trên khóa phút mới chứ không đợi TTL. Hash IP là pseudonymization, **không phải ẩn danh mạnh**: không có salt bí mật, địa chỉ IP có thể bị dò ngược bằng từ điển; chỉ dùng dữ liệu giới hạn này để giảm lạm dụng, không xem là danh tính người dùng. Không ghi IP gốc vào collection.

Counter toàn cục được tăng trước counter IP; mỗi counter nguyên tử nhưng hai phép tăng không phải transaction. Do đó request bị từ chối theo IP hay lỗi giữa hai bước vẫn có thể tiêu thụ quota global; đây là lựa chọn bảo thủ. Sau khi global đầy, request mới không tạo thêm document IP cho phút đó. TTL và giới hạn toàn cục chặn tăng số document trong bucket, nhưng không loại bỏ tải ghi vào counter global. Các endpoint và môi trường dùng bucket riêng; không gộp quota review vào đây.

Ở `VERCEL_ENV=production`, chỉ chấp nhận một địa chỉ IP hợp lệ trong `X-Forwarded-For`; thiếu hoặc chứa chuỗi IP không hợp lệ trả 503 `rate_identity_unavailable`. [Vercel mô tả header này là IP client và bị nền tảng ghi đè để chống spoofing](https://vercel.com/docs/headers/request-headers). Điều này dựa trên request thực sự đi qua Vercel; một proxy phía trước có thể khiến IP proxy được tính chung, còn Trusted Proxy Enterprise thay đổi giả định. Cần xác minh đường đi và header trên deployment trước phát hành, không coi header tự nó là bằng chứng mã hóa. Nếu thiếu URI, không kết nối/ghi được Mongo, hay không tạo được TTL index, production fail-closed 503 `rate_storage_unavailable`, không gọi IRSA và không rò thông tin kết nối.

Preview/local không tin forwarded header, dùng `client_address`; nếu không cấu hình Mongo thì dùng bộ đếm bộ nhớ khóa thread có tối đa 8.192 khóa, quá mức trả 503. Fallback này chỉ bảo vệ mỗi process và không thực thi global quota xuyên instance. Nếu preview có URI, vẫn dùng Mongo nhưng namespace tách khỏi production; client_address ở sau proxy có thể đại diện proxy thay vì client. Không xem thử nghiệm preview như bằng chứng rate limit production.

Response `frame` thành công có thể được browser/CDN cache 300 giây; request được cache có thể không đi đến guard. Các giới hạn này bảo vệ lượt xử lý tại origin và truy vấn upstream, không giới hạn mọi cache hit. Chúng không chống botnet/DDoS, bùng nổ instance hay quota bị chiếm bằng nhiều IP; cần kiểm soát tại biên và theo dõi quota/latency trước khi công khai rộng. Quota IP có thể khiến người dùng sau NAT chia sẻ mức giới hạn, và quota global có thể bị chiếm hết. Chưa có load test, test MongoDB thật, xác minh triển khai Vercel hay dịch vụ cảnh báo.

Tests dùng collection giả khóa thread và HTTP handler với upstream giả; chúng kiểm tra giới hạn đồng thời, isolation hai endpoint, fail-closed, TTL, lọc burst, response 429 và không lưu IP thô. Không có dịch vụ mới, không đổi credentials hay cấu hình cloud.


Hardening sau review: ngữ cảnh triển khai thiếu/không nhận diện được trả 503 deployment_context_unavailable. Local fallback cần SPHEREX_LOCAL_API=1 do launcher loopback bật rõ; cờ local không vượt qua VERCEL_ENV=production. Các system env phải được expose đúng ở Vercel; không coi thiếu env là local. Kiểm thử bao gồm cả trường hợp thiếu VERCEL_ENV/VERCEL và cờ local đặt nhầm trong production.

API review có quota riêng: 90 request/IP/phút và 60 POST hợp lệ/phút toàn cục, thêm giới hạn 100 bản còn hiệu lực mỗi owner và 20.000 document vật lý toàn hệ thống. Transaction ghi chung `review_guard` trước khi kiểm tra và upsert để chống write skew giữa các POST; GET/DELETE không cần transaction, và TTL dọn document hết hạn bất đồng bộ. Giới hạn là đề xuất cho demo, không chứng minh khả năng chống DDoS hoặc bảo đảm đủ dung lượng byte. Đếm toàn collection và điểm ghi chung có thể chậm hoặc tăng xung đột; khi lỗi/hết retry, POST fail-closed. Phiên bản cũ hoặc writer ngoài API không qua guard có thể phá invariant. Chi tiết lỗi và `save_outcome_unknown` ở [hợp đồng review](REVIEW_API_CONTRACT.md).

MongoDB mô tả [Free cluster là replica set ba node chạy MongoDB 8.0](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/) và [transaction hỗ trợ replica set](https://www.mongodb.com/docs/manual/core/transactions-production-consideration/); điều này không thay thế kiểm tra cluster/quyền thực tế. Test trong `tests/test_review_transactions.py` chỉ chạy khi cấu hình replica set loopback disposable; chưa có kết quả MongoDB thực hay benchmark Atlas ở checkpoint này. FakeDB không chứng minh isolation hoặc giới hạn dưới cạnh tranh thật.
