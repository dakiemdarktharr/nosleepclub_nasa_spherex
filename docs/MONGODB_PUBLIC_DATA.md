# Dữ liệu công khai trong MongoDB

## Phạm vi và dung lượng

Chuyển đúng **213 Git blob** dưới `web/data/`: 212.215.160 byte gốc,
127.478.741 byte sau nén transport. Có 426 phần, tối đa 512 KiB/phần.
Một ảnh chẩn đoán cục bộ bị ignore không thuộc danh mục phát hành. Không nhập
`data/raw/`, FITS tải thô, ghi chú riêng, cookie hay các trường dành riêng.
Các FITS/NPZ nhỏ vốn đã công khai trong `web/data/` vẫn được giữ nguyên hash.

Cluster M0 `nosleepclub-spherex`, project `NoSleepClub_NASA_SPHEREx`, database
`nosleepclub_nasa_spherex` được dùng tiếp. Trước import, `dbStats` ghi 34 byte
logical data, 126.976 byte storage và 249.856 byte index. Chunk giữ dạng base64
để phép chuyển qua connector/HTTP không đổi byte; khoảng 170 MB logical trước
overhead vẫn nằm trong hạn mức 512 MB. Chưa có bằng chứng cần thêm cluster.

MongoDB áp dụng giới hạn storage, connection, throughput và transfer cho M0;
thêm cluster không tự tăng băng thông Vercel. Tài liệu hiện hành:
[Atlas Free limits](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/),
[cluster capacity](https://www.mongodb.com/docs/atlas/manage-clusters/).
Không tạo project/cluster trả phí hoặc nhân cluster khi chưa đo nhu cầu.

## Đường đọc

`web/api/_data_manifest.json` ghim hash/size/MIME/encoding/chunk của từng Git blob.
`public_asset_chunks` chỉ chứa các chunk có `_id = SHA-256(payload)`. API không
nhận tên collection hoặc truy vấn Mongo từ client và không đọc review riêng.

URL chưa có phiên bản chuyển hướng đến `v=stored_sha256`, không cache redirect.
URL có phiên bản mới được cache browser/CDN; phiên bản cũ khác manifest bị từ
chối thay vì trả nhầm byte. Metadata chưa có phiên bản và mọi lỗi đều no-store.
JSON/SVG có thể truyền gzip rồi trình duyệt giải nén, hash gốc vẫn nguyên.
Từng phần được xác minh length và SHA ở server trước khi trả.

Vercel giới hạn một phản hồi function ở 4,5 MB. Response trực tiếp tối đa 4 MiB;
ba archive lớn chuyển đến trang tải theo phần. Trình duyệt kiểm từng chunk và
toàn tệp trước khi mở nút Lưu. Không gắn thuộc tính download vào link mở trang
tải. Đây là thay đổi vận chuyển, không tái chạy hoặc cải thiện phép đo khoa học.
[Function limits](https://vercel.com/docs/functions/limitations),
[CDN caching](https://vercel.com/docs/caching/cache-control-headers).

## Hai pha triển khai

1. Thêm reader/importer và cải thiện UX; giữ nguyên `/data/` trên CDN. Không
   kích hoạt `buildCommand`/`outputDirectory` hoặc rewrite trước reconciliation.
2. Nhập đủ, kiểm hash qua reader, thu hồi capability. Sau đó mới dùng
   `python build_public.py`, static output `public/` và rewrite `/data/` sang
   reader. Static output chỉ gồm UI/font/ảnh thiết kế; repo vẫn giữ dataset để
   tái lập và rollback. Source checkout/build vẫn tải repo, không gọi đó là
   giảm toàn bộ source storage hoặc băng thông function.

Cutover `7efcf6b` build thành công (static shell Linux: 615.668 byte), nhưng
wildcard rewrite trả 400 cho canonical `/data/manifest.json`. Smoke bắt lỗi
trước khi tạo review QA; đã rollback về deployment static ngay trước đó,
`2f1442a`, và xác minh manifest HTTP 200. Không xác định chính xác tập query
nội bộ từ rewrite. Bản sửa dùng **213 redirect cụ thể** từ danh mục đã ghim
sang `/api/data?path=...&v=...`, không truyền wildcard qua lớp rewrite.
Generator/check và canonical verifier kiểm đủ từng ánh xạ. Query validation
của reader không được nới lỏng; chưa coi lần cutover đầu là đã giao thành công.

## Nhập và khôi phục

`build_data_manifest --write` chỉ đọc Git blob đã commit, nén deterministic,
lưu phần tải trong ignored `data/raw/asset-migration/`. Source/hash gốc không
bị sửa. Connector Atlas đã trả 413 cho lô khoảng 1,4 MB; không tính là đã nhập.
Vì vậy dữ liệu lớn đi qua importer bị khóa bằng capability ngẫu nhiên riêng.
Mongo URI hiện có chỉ ở production Vercel, không tải ra máy/CI/preview.

`migrate_public_data --prepare` tạo capability cục bộ 32 byte ngẫu nhiên và
permit chỉ có hash, manifest ID, issued/expiry (tối đa 45 phút). Operator dùng
Atlas connector đặt đúng permit vào `public_asset_import_permits`. Import chỉ
chạy production, nhận payload ≤512 KiB có đúng SHA/size trong manifest, dùng
insert-only. Không ghi đè chunk đang có. Dùng `--upload` gửi đến domain production
cố định qua TLS; mỗi lần chạy có receipt riêng, kể cả khi lỗi. Có thể chạy lại
toàn bộ idempotently; không xóa receipt lỗi hoặc tính request lỗi là thành công.

Sau khi hoàn tất, xóa đúng permit của migration bằng connector, kiểm POST bị
từ chối, xóa capability cục bộ do migration tạo. Request đã qua kiểm tra permit
có thể hoàn tất trước khi thu hồi; không thể dùng nó để viết byte ngoài manifest.
Không có permit hợp lệ thì endpoint không nhận import. Không tự GC chunk;
trước khi xóa version cũ phải đối chiếu mọi deployment cần rollback.

Đường truyền local đã mất 41,312 giây cho một phần 512 KiB. Chủ repo đã cho
phép khóa public-asset tạm `SPHEREX_PUBLIC_DATA_IMPORT` trong GitHub Actions;
workflow chỉ chạy thủ công trên main và kiểm cả người khởi chạy/người bấm
rerun đều là owner. Secret chỉ vào bước import, không vào artifact; Mongo URI
không vào GitHub. Artifact chỉ giữ receipt import/reconciliation. Xóa Secret
cùng permit sau khi hoàn tất; mode canonical chỉ đối soát, không dùng secret.

Lượt import `41208174465` nhập đủ 426 phần; lượt đối soát đầu dừng ở NPZ vì
CDN gzip thêm cho client đã quảng cáo gzip. Tệp vẫn được browser giải mã đúng;
verifier cũ đã nhầm byte lưu với byte nén HTTP. Lượt đó được giữ nguyên. Verifier
mới thương lượng identity cho sản phẩm identity và chunk, gzip cho sản phẩm
gzip, đồng thời kiểm media type, encoding và byte thực nhận; không bỏ kiểm hash.

Nếu import/reader chưa đạt, giữ static release. Nếu cutover có lỗi, rollback
về release pha 1: dữ liệu vẫn có trong Git/CDN và review cũ vẫn dùng database
ban đầu. Khi logical size vượt 70% hạn mức hoặc tải đo được gây nghẽn, đánh giá
retention/versioning và storage cho binary trước khi khóa phân vùng nhiều cluster;
không coi nhiều M0 là sharding hay high availability đã kiểm chứng.

## UX được thử lại

WISE và IRSA đi theo Dữ liệu → So ảnh → Kiểm tra → Ghi nhận. Danh sách IRSA
được mở ngay sau metadata, kể cả khi ảnh đầu lỗi; bỏ qua quan sát không có URL,
có nút Tải lại ảnh. Chỉ khi đủ hai ảnh đã tải mới cho qua Kiểm tra. Danh sách
đánh dấu A/B, hiển thị ngày UTC; giữ khoảng ngày trong URL.

Nháp được giữ trong sessionStorage cùng tab (tối đa 50, hết hạn 24 giờ), gắn
analysis/selection hoặc query/A/B; không tự gửi lên máy chủ. Reload phải chọn
lại đúng cặp IRSA mới khôi phục nháp. Đóng tab có thể mất nháp: xuất JSON để
giữ. Xuất WISE chứa nhận xét đã lưu và nháp chưa lưu ở hai trường riêng, không
âm thầm bỏ phần đang gõ. Lưu cục bộ không hứa tự đồng bộ.

Các kiểm thử mô phỏng và browser của agent không thay thế thử với người mới
thật. Kết quả vận hành/public và giới hạn còn lại được bổ sung trong receipt
phát hành sau cutover; không coi tài liệu thiết kế là bằng chứng đã di chuyển.
