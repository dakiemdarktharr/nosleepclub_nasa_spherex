# Sao lưu nhận xét thủ công / Manual review backups

Công cụ `scripts/backup_reviews_local.py` đọc riêng collection `reviews` của database Atlas hiện có `nosleepclub_nasa_spherex`. Đây là thao tác thủ công, không bật dịch vụ trả phí hay lịch chạy. Không sao lưu các chunk ảnh công khai, API counters hoặc cookie người dùng.

The tool reads only the existing database's `reviews` collection. It does not schedule jobs, enable a paid backup service, or copy public image chunks, API counters, or session cookies.

## Chạy trên Windows / Run on Windows

Dùng môi trường Python có các dependency kiểm thử hiện tại (`pymongo`, `cryptography`). Chạy từ thư mục dự án:

```powershell
.venv/Scripts/python.exe -m scripts.backup_reviews_local snapshot
```

Nhập URI Atlas hiện có vào lời nhắc ẩn. Công cụ cũng nhận biến môi trường `SPHEREX_BACKUP_MONGODB_URI` từ một trình quản lý secret; không ghi URI vào lệnh, script, lịch sử terminal hoặc Git. Tài khoản MongoDB cần quyền đọc collection và session snapshot, không cần cấp thêm quyền ghi production cho việc sao lưu.

Enter the existing Atlas URI at the hidden prompt, or inject `SPHEREX_BACKUP_MONGODB_URI` through a secret manager. Never put credentials in command arguments or repository files. The snapshot uses a read-only transaction with snapshot read concern.

Tệp mã hóa nằm tại `%LOCALAPPDATA%/SPHEREx/backups/reviews-<UTC>-<random>.spherex.enc`. Khóa Fernet chỉ lưu dưới dạng `review-key.dpapi`, được Windows DPAPI bảo vệ cho người dùng hiện tại. Không có tệp BSON thuần. Đầu ra chỉ có tên tệp, thời điểm, số bản ghi và SHA-256 của bản mã. Không in URI, khóa, nội dung nhận xét hay owner ID.

Encrypted files and the current-user DPAPI-protected key stay outside the repository. Losing the Windows profile or DPAPI key can make these backups unrecoverable. This local mechanism is not an off-device disaster-recovery copy. Do not copy decrypted keys into the repository or CI artifacts. No automatic retention/deletion policy is enabled; keep encrypted copies under the owner's approved retention policy.

```powershell
.venv/Scripts/python.exe -m scripts.backup_reviews_local verify --file reviews-<UTC>-<random>.spherex.enc
```

`verify` giải mã trong bộ nhớ, xác thực toàn vẹn và schema BSON; nó **không chứng minh MongoDB đã restore thành công**. Giới hạn: 20.000 bản ghi, 128 MiB bản thuần; vượt giới hạn thì thất bại toàn bộ, không cắt ngắn im lặng. ObjectId, ID chuỗi hex, thời gian UTC, Binary và Int64 được giữ nguyên.

`verify` authenticates and validates the snapshot in memory. It does not prove a successful database restore. Limit violations fail the whole operation rather than silently dropping records.

## Diễn tập tách biệt / Isolated restore drill

Chuẩn bị MongoDB loopback dùng riêng cho kiểm thử, replica set `codex-review-test`, cổng mặc định 27027. Không dùng tunnel đến hệ thống thật. Công cụ chỉ chấp nhận `127.0.0.1` và replica set này; không có lệnh restore lên Atlas.

```powershell
.venv/Scripts/python.exe -m scripts.backup_reviews_local restore-drill --file reviews-<UTC>-<random>.spherex.enc --local-port 27027
```

The drill creates a fresh `review_backup_dst_<uuid4>` database, refuses an existing target, restores only unexpired documents, checks BSON equality, then restores and verifies the unique owner/key index and TTL index. It does not change the production database or resurrect expired reviews. A failed drill can leave an isolated target for investigation; the CLI does not delete databases automatically. The target name is reported after a successful drill.

Các bản ghi có hạn dùng chưa đến sẽ tiếp tục chịu TTL gốc. Việc restore nhận xét không khôi phục cookie bị mất của người dùng và không tự cấp quyền truy cập lại cho thiết bị mới.

## Trạng thái kiểm chứng / Verification status

Unit tests cover authenticated encryption, BSON types, ID forms, refusal of existing targets and bad sources, plus actual Windows DPAPI key protection. The MongoDB integration test runs only when `REVIEW_TEST_MONGODB_URI` points to the isolated loopback fixture. A skip is not a successful restore drill.

The synthetic restore into an isolated MongoDB replica set passed in [GitHub CI run 43582777817](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/actions/runs/43582777817), including BSON equality, indexes and expiry handling. Windows DPAPI was tested locally. No production snapshot has been taken: the production URI is unavailable locally. Production backup/restore timing, capacity and recovery objectives remain unmeasured. These tests are not evidence that production reviews have already been backed up.

References: [Windows current-user DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata), [PyMongo sessions and transactions](https://pymongo.readthedocs.io/en/stable/api/pymongo/client_session.html), [existing fixture-only protocol](BACKUP_RESTORE_PROTOCOL.md).
