# Phát hành chẩn đoán profile — 31/10/2026

[Mở sản phẩm](https://nosleepclub-nasa-spherex.vercel.app/#profile-landscape)
→ chọn sao A/B và “Ảnh bị gate chặn”, rồi so với “Ảnh liền trước”. Bốn ô
đồ thị tách ePSF gốc/hiệu chỉnh và hai vector trọng số đã lưu. Bảng số mở
bằng Enter; archive tải riêng chứa đủ hai journal. README/NOTICE đã cập nhật;
mã nguồn riêng dùng MIT, quyền dữ liệu/font/Canva giữ riêng.

Milestone này đã được triển khai và kiểm tra. Toàn bộ goal production vẫn
chưa hoàn tất; không có phép đo khoa học hoặc mô hình sai số mới được chấp nhận.

## Commit, CI và triển khai

- [PR #13](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/pull/13)
  đã merge sau hai check bắt buộc. Head được kiểm tra:
  `57ba06c9a01812625f869d09307ca39c27285d72`; main production:
  `da79c6b9b3cb06dfea0126bd88b153d7ce73e89b`. Hai cây Git giống hệt nhau.
- [CI run 41164187761](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/actions/runs/41164187761):
  564 ca Python, 551 đạt và 13 optional raw-cache/photutils skip. Cả sáu ca
  Mongo replica set thật đều đạt; bảy suite Node 24 đạt. [Biên nhận CI](evidence/0.10/ci-pr13-57ba06c.json).
- Local chạy 564 ca: 558 đạt, sáu ca Mongo dành cho CI. Các assertion metadata
  hình bổ sung được kiểm lại bằng ba ca product và sau đó toàn bộ cây được CI
  kiểm tra. [Biên nhận local](evidence/0.10/profile-landscape-local-tests.json).
- Vercel production `dpl_7549bc8xMUnG2yV2ukQBQYUirgAp`, vùng cấu hình `sin1`,
  READY và alias public đúng commit. [Biên nhận deployment](evidence/0.10/deployment-da79c6b.json).
  Preview chỉ được xem metadata, không fetch hoặc tạo share link.

[88 phản hồi production](evidence/0.10/production-da79c6b.json) xác nhận 74
artifact theo byte Git, commit của cả ba API, FITS/mask contract và vòng QA
khách mới. Có 85 HTTP 200, hai HTTP 400 và một HTTP 403 theo các ca từ chối
được định trước; không có 5xx hoặc retry trong lượt này. Tất cả cờ kiểm tra
ID ổn định, expiry, tách owner, Origin, stale analysis, xóa theo ID và cleanup
đều đạt. Worktree sạch khi verifier bắt đầu. Credential Mongo không được tải
về local hay CI; QA chỉ dùng API production bằng session mới.

Hai lỗi 502 của lần phát hành trước vẫn ở receipt cũ. Telemetry mới chỉ bổ
sung enum cho giai đoạn/loại lỗi, không retry hoặc cache. Các fault path đã
được thử offline; lượt production này không phát sinh lỗi upstream để xác
nhận sự kiện lỗi thực trên cloud. Chưa kết luận nguyên nhân hoặc độ tin cậy
từ một lần smoke thành công.

## Bằng chứng khoa học và giao diện

Protocol `704e3ef` khóa trước 112 nhánh. Có 96 nhánh profile và 16 nhánh thiếu
đầu vào; đủ 14 sao được giữ. Kiểm toán WLS độc lập kiểm 2.760 nút được chọn,
stencil ba bước tại 192 điểm fit và 480 objective đã lưu. Các file source,
design, journal và hình đều có hash. [Kết quả đầy đủ](PROFILE_LANDSCAPE_RESULTS.md).

Hessian dương và các vùng liên thông trên lưới không chứng nhận nghiệm vật lý,
không phải coverage và không xóa gate cũ. Cả 252 ô assessment và 30 trường
triển vọng vẫn chưa mở. Chưa tăng độ chính xác thiên văn đã được chứng minh.

Browser public đã hiển thị đúng `96/112`, `16`, phần dành riêng chưa mở và
PNG 1.404 px tải thành công. [Bằng chứng public](evidence/0.10/profile-production-browser-da79c6b.json)
và [ảnh chụp](evidence/0.10/profile-production-da79c6b.png) bổ sung cho HTTP.
Local kiểm đổi sao/ảnh, Enter, Tab và reflow 390 px; bảng có vùng cuộn ngang,
không tràn toàn trang. Đây chưa phải kiểm toán screen reader/accessibility đầy đủ.

File dependency vẽ có sẵn được giữ nguyên byte. Một chỉnh sửa tạm thời đã
được hoàn tác trước CI phát hành; metadata inspection được sửa tương ứng,
giữ [biên nhận](evidence/0.10/profile-figure-environment-correction.json) và
lịch sử Git. Không render lại hình hay thay journal/gate khoa học.

## Mốc kế tiếp

Khóa đối chứng native về tín hiệu, nguồn chồng, template và pha pixel bằng
nguồn giả độc lập. Trước khi chạy phải có ngân sách bias/thu hồi tín hiệu,
định danh nguồn, điều kiện từ chối, seed và đủ mẫu số theo từng điều kiện.
Tiêu chí nghiệm thu là tái tạo được mọi lượt, kiểm toán chân trị/đơn vị/mask,
báo cáo cả lỗi và đạt ngân sách đã khóa; chưa dùng tập dành riêng để chọn mô hình.

Recovery production, tải đại diện/SLO, full uncertainty coverage, kiểm định
bầu trời độc lập và các hạng mục còn mở vẫn nằm trong
[bảng 20 tiêu chí](PRODUCTION_READINESS.md). Các receipt phát hành được lưu ở
commit tài liệu sau khi kiểm tra; API public vẫn là `da79c6b`, không tự đổi
theo HEAD của nhánh lưu bằng chứng.
