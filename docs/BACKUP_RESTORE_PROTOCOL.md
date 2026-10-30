# Protocol thử sao lưu/khôi phục review tổng hợp có mã hóa

Đây là **nguyên thủy thử nghiệm chỉ dành cho MongoDB loopback tổng hợp**, không phải giải pháp backup production và không kết nối Atlas. Không có CLI, route web, cấu hình credential hay chức năng cleanup tổng quát. `scripts/review_backup.py` chỉ chấp nhận đúng dạng `mongodb://127.0.0.1:<port>/?directConnection=true`, không auth, không database hoặc tham số khác; sau kết nối yêu cầu primary của replica set `codex-review-test`. Source phải tên `review_backup_src_<uuid4-hex>`, target phải tên `review_backup_dst_<uuid4-hex>`. Kết nối qua tunnel hoặc trỏ fixture vào hệ thống thật không thuộc phạm vi được phép.

## Nội dung và giới hạn

`seal_snapshot(documents, indexes, key)` tạo một token Fernet chứa BSON version 1, thời điểm tạo UTC, các document review và đúng hai index: unique `(owner, key)` và TTL `expires_at=0`; index `_id` do MongoDB tạo. `snapshot_fixture(uri, source_name, key)` đọc collection `reviews` tổng hợp qua snapshot transaction rồi mã hóa; source chỉ được chứa collection đó, index phải đúng hợp đồng. Index được kiểm tra trước snapshot transaction, vì vậy fixture phải độc quyền, không thay index đồng thời. Không sao lưu `limits`, `api_limits` hay `review_guard`; đây không phải snapshot đầy đủ của một database ứng dụng.

`restore_fixture(uri, target_name, ciphertext, key)` xác thực Fernet, giải mã và kiểm tra toàn bộ BSON/schema/version, ID trùng, cặp owner/key trùng, index trùng/sai và giới hạn **trước khi kết nối hay tạo target**. Target phải chưa tồn tại; không ghi đè. Các bản có `expires_at` trước hoặc bằng thời điểm restore bị bỏ qua, bản còn hạn giữ nguyên expiry, `_id`, owner và key; review ID được tính từ owner/key vẫn ổn định. Các bản hết hạn trong lúc restore không được gia hạn, API đọc phải tiếp tục lọc expiry và TTL dọn sau. Tạo index trước rồi insert trong transaction; nếu lỗi sau khi tạo collection, target tổng hợp có thể còn rỗng và cần điều tra, không tự xóa để thử lại.

Các giới hạn cố định: tối đa 500 document, 32.768 byte mỗi document, 2.000.000 byte BSON plaintext, 3.000.000 byte ciphertext; cấu trúc lồng không quá 30 mức. Chỉ chấp nhận `_id` BSON ObjectId, owner hex 64 ký tự, khóa analysis/scene/selection hợp lệ và expiry UTC chính xác mili giây. Cho phép các kiểu BSON dùng trong fixture như Binary, Int64, Decimal128, Timestamp, datetime UTC, danh sách và document; kiểu không hỗ trợ bị từ chối thay vì biến đổi âm thầm. Kiểm tra kích thước bảo thủ có thể từ chối một document nhỏ hơn trần BSON thực tế.

Dùng thư viện [Fernet của pyca/cryptography](https://cryptography.io/en/latest/fernet/) để mã hóa và xác thực; caller cung cấp key bằng bytes. Không ghi key, URI, note hay digest plaintext vào log/receipt; primitive không tự ghi file và chỉ trả token bytes. Receipt restore chỉ có version và số lượng tổng hợp, không có nội dung review. Fernet không che thời gian tạo token và độ dài token; ai có key có thể giải mã **và tạo** token mới. Không có key recovery hoặc rotation trong primitive này. Không đưa key hay token vào log, tham số process, CI artifact hoặc repository.

## Test fixture

Cài dependency offline `requirements.txt`, `web/requirements.txt` và `requirements-ops.txt` trong môi trường test; `requirements-ops.txt` không thuộc web runtime. Unit tests chạy:

```text
python -m unittest tests.test_review_backup tests.test_review_backup_mongo -v
```

Hai test Mongo sẽ tự skip nếu không có `REVIEW_TEST_MONGODB_URI`. Với một **replica set disposable loopback riêng** tên `codex-review-test`, do test runner tạo, đặt biến test thành `mongodb://127.0.0.1:27027/?directConnection=true` rồi chạy cùng lệnh. Tests tự tạo UUID source/target tổng hợp, chỉ dọn các database UUID đã được test tạo; không dùng `MONGODB_URI`. Chúng kiểm tra BSON/UTC/index và owner/key sau restore, target đã tồn tại, wrong-key/tamper không tạo target và bỏ qua bản hết hạn. Nếu restore lỗi giữa chừng, test không chủ động xóa target chưa được xác nhận tạo thành công; container disposable phải được hủy bởi runner.

Các test fake chỉ kiểm tra luồng chứ không chứng minh transaction hay độ bền MongoDB thật. CI chạy fixture MongoDB là bằng chứng cho thử nghiệm tổng hợp trên fixture đó, không phải Atlas M0, production backup, RPO, RTO hay bài diễn tập khôi phục người dùng thật. Không có kết quả synthetic live nào được ghi trong tài liệu này nếu chưa thực sự chạy.

## Điều kiện trước khi thiết kế backup production

Primitive này bị giới hạn ở fixture; chưa có đường backup production. Thiết kế thật cần xác định danh tính/quyền MongoDB, đích mã hóa, nơi giữ/rotate/khôi phục key, retention/xóa bản sao, lịch và giám sát, restore tách biệt, kiểm chứng đủ dữ liệu và gate chuyển bản restore sang production. Quyền sửa và triển khai web đã có; nếu thiết kế cần xuất review riêng sang đích mới, mở rộng nơi nhận credential hoặc phát sinh chi phí, phải có chấp thuận cụ thể cho phạm vi mới đó. Credential hiện vẫn chỉ dùng ở production Vercel. Kiểm tra lại availability và giá của backup M0 trước khi chọn dịch vụ.

Một snapshot cũ không biết review đã bị người dùng xóa sau lúc chụp: restore nó có thể làm xuất hiện lại dữ liệu đã xóa dù expiry vẫn còn trong tương lai. Cần deletion journal/tombstone hoặc quy trình đối soát xóa đã được kiểm chứng trước khi cân nhắc dữ liệu thật; lọc expiry không giải quyết điều này. Primitive này không thực hiện đối soát, không xác nhận restore, RPO/RTO hoặc production readiness.
