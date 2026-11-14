# Chuyển dữ liệu công khai sang MongoDB — 31/10/2026

Production: [mở demo](https://nosleepclub-nasa-spherex.vercel.app/#home),
commit `20bf9ae79c9cc50898d71afbf6778f3f8af26078`, deployment
`dpl_6uuZugMniSWj2of6AE59DX5ZTfSM`. Source được merge qua
[PR #16](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/pull/16),
[17](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/pull/17),
[18](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/pull/18) và
[19](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/pull/19).

## Kết quả đã đo

| Phần | Kết quả |
| --- | --- |
| Dữ liệu công khai | 213 Git blob, 212.215.160 byte gốc |
| Mongo transport | 426 phần, 127.478.741 byte đã nén |
| Canonical public | 213/213 khớp byte/hash; 607 phản hồi: 213 × 307, 394 × 200; không retry |
| Vercel static output | 41 file, 615.668 byte; không có `data/` |
| Mongo database | Khoảng 170 MB logical, 339 MB allocated; một M0, không tạo cluster/tier mới |
| Software CI cuối | 623 ca Python: 610 đạt, 13 optional raw-cache/photutils skip; cả sáu ca Mongo fixture thật đạt; 11 chương trình Node đạt |
| Production smoke | 173 phản hồi đạt hợp đồng; 84 payload kiểm hash, ba audit lớn kiểm metadata/redirect ở smoke và kiểm đủ byte trong canonical reconciliation |

[Canonical receipt](evidence/0.10/mongo-canonical-20bf9ae.json),
[smoke](evidence/0.10/mongo-production-20bf9ae.json),
[CI](evidence/0.10/mongo-ci-chain.json),
[capacity](evidence/0.10/mongo-capacity-after-import.json),
[remote build](evidence/0.10/mongo-deployment-20bf9ae.json).

Smoke có 99 HTTP 200, 70 redirect 307, hai 400 và hai 403 có chủ đích;
không retry. Nhận xét QA được tạo/đọc/xóa, kiểm ổn định ID, expiry,
scope/Origin isolation, stale analysis và cleanup. Không dùng số lượng HTTP
200 làm bằng chứng độ chính xác thiên văn hay uptime.

## Hai luồng và tải audit

Đã thử WISE từ chọn dữ liệu → chọn R01 → xem giới hạn → lưu riêng Mongo →
xuất JSON → xóa nhận xét QA; lịch sử bắt đầu/kết thúc đều 0. Nháp được thử
qua reload trước khi lưu ở bản pha 1; logic draft không đổi trong cutover.
Vùng residual không hiện nhầm vector WISE.

IRSA dùng lại vùng đã mở RA 350°, Dec 35°, QR2/D6, 01–30/06/2025: 18 quan
sát; chọn `2025W26_2A_0314_1` / `_2`, xem giới hạn, ghi chú và xuất JSON ở
bản cuối. Nhấp nháy và query/date/pair draft qua reload được thử ở pha 1.
Bản cuối hiện cả ngày giờ
UTC và ảnh A/B; ghi chú IRSA không được gửi vào API nhận xét WISE. Nháp QA
đã xóa. Không truy vấn 30 trường dành riêng.

Audit đối chứng tín hiệu tải 20 phần trong browser, chỉ mở nút lưu khi hash
từng phần/toàn tệp khớp. Tệp thực tải xuống có 10.046.627 byte, SHA-256
`ef757d6c605f623ecfae35c0c4ebdc43b8ab3e1308adb741bc9be7d8d2d555a0`,
khớp sản phẩm Git đã khóa. Desktop và viewport 390 × 844 đã kiểm; document
375/375 px không tràn ngang, canvas không bị nút tiếp tục đè. Viewport đã reset.
[Browser evidence](evidence/0.10/mongo-browser-20bf9ae.json).

## Quyền nhập và các lần lỗi được giữ lại

Mongo URI vẫn chỉ ở production Vercel. Chủ repo đã duyệt capability tạm cho
GitHub Actions; permit gắn hash manifest, chỉ nhận byte công khai đã ghim,
insert-only và tối đa 45 phút. Permit được xóa lúc 14:21:17 UTC; khóa cũ trả
403, GitHub Secret và tệp khóa cục bộ đã xóa.
[Revocation](evidence/0.10/mongo-import-revocation.json).

- Connector từ chối lô lớn bằng 413 trước khi nhập. Đường truyền local timeout
  khi gửi; khối 512 KiB sau đó cần 41,312 giây. Chuyển upload sang runner theo
  chấp thuận, không chuyển Mongo credential vào CI.
- [Import](evidence/0.10/mongo-import-41208174465.json) hoàn tất 426 phần, nhưng
  [reconciliation đầu](evidence/0.10/mongo-initial-reconciliation-41208174465.json)
  dừng sau 32 sản phẩm vì CDN gzip thêm NPZ. Verifier sửa thương lượng HTTP,
  giữ kiểm MIME/encoding và byte/hash. [Pre-cutover](evidence/0.10/mongo-reader-before-cutover.json)
  đạt 213 sản phẩm với 396 attempt records, gồm hai read timeout và hai retry
  được giữ nguyên. [Source binding](evidence/0.10/mongo-reader-source-binding.json)
  khớp file verifier trong commit `1862358`; lúc chạy file còn ở working tree.
- Cutover `7efcf6b` có [smoke 400](evidence/0.10/mongo-production-7efcf6b-failed.json)
  và [canonical failure](evidence/0.10/mongo-canonical-7efcf6b-failed.json).
  Wildcard rewrite không tương thích parser; query nội bộ chính xác chưa được
  ghi lại. Đã rollback về static `2f1442a`, xác minh manifest HTTP 200, rồi
  dùng 213 redirect cụ thể theo hash. Query validation không được nới lỏng.

Các lỗi không bị thay thế bằng lượt thành công. Smoke cuối so Git blob và API
commit; cờ working-tree-dirty đến từ bản sao receipt lỗi chưa commit, không có
thay đổi source runtime. Archive tài liệu/evidence được commit sau bản production
để tránh tạo vòng deploy chỉ để lưu biên nhận.

## Giới hạn và mốc tiếp theo

Đã giảm **static output của bản mới**, không xóa dataset khỏi Git/source checkout
hoặc các deployment cũ được giữ để rollback. Các Python function vẫn có cảnh báo
bundle 261–297 MB trước tối ưu; chưa có số đo byte triển khai cuối từng function.
Không cộng static shell 616 KB thành dung lượng toàn project Vercel.

M0 chưa có chứng nhận tải lớn, failover, SLO dài hạn hoặc recovery production.
Kiểm thử browser của agent không thay nghiên cứu với người mới thật, screen reader
hoặc toàn bộ browser/device matrix. IRSA vẫn chỉ là so ảnh hiển thị; phép đo WISE
vẫn có sai số mô hình chưa hiệu chuẩn. Không thay threshold/PSF/covariance, không
mở 252 assessment cells hoặc 30 trường dành riêng, không tuyên bố phát hiện.

Mốc đề xuất tiếp theo: tách dependency của reader/review khỏi xử lý FITS để giảm
bundle Python. Nghiệm thu bằng số đo bundle trước/sau trên Vercel, reader/review
không mang Astropy/Pillow không cần thiết, và giữ toàn bộ byte/hash, private-review
lifecycle cùng hai luồng end-to-end đạt. Sau đó mới khóa một đợt thử tải để quyết
định scale, dựa trên latency/cache/memory thay vì nhân cluster theo cảm tính.
