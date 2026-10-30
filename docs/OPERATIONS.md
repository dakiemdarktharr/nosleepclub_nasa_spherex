# Vận hành và kiểm tra trước phát hành

Phạm vi hiện tại là công cụ quan sát thăm dò, không phải xác nhận phát hiện thiên văn. [Ledger](PRODUCTION_READINESS.md) là nguồn theo dõi 20 mục; **CI xanh không xác nhận độ chính xác khoa học, bảo mật production, khả năng chịu tải hay khôi phục dữ liệu**. Kết quả 0.9 đã công bố có gate tổng và covariance không đạt; `point_passed=true` là so baseline với chính nó. Đừng quảng bá hoặc tự nâng kết quả này thành nghiệm khoa học.

## Trước mỗi lần phát hành

1. Ghi commit, trạng thái sạch/bẩn, môi trường, deployment ID và hash manifest/protocol; so commit triển khai với bản đã kiểm tra. `python scripts/check_readiness.py` xuất JSON với trạng thái Git, kiểm tra cấu hình/dependency/hash, ledger và evidence 0.9. Script không chạy test. Mặc định exit 0 chỉ khi các kiểm tra repository của nó đạt; `--require-science` hiện luôn trả nonzero vì chưa có cơ chế xác minh khoa học độc lập. Đây là fail-closed, không phải cách xác nhận khoa học khi tài liệu đổi trạng thái.
2. Chạy `.venv/Scripts/python.exe -m unittest discover -s tests -v` trên Windows, hoặc `python -m unittest discover -s tests -v` trong môi trường đã cài `requirements.txt` và `web/requirements.txt`. Kết quả `skip` phải được xem riêng; raw FITS không được đóng gói vào repo và test dùng raw có thể bỏ qua ở CI. Workflow `.github/workflows/checks.yml` chạy toàn bộ Python tests, compile và whitespace source, syntax JavaScript và các ca ReviewStore bằng Node 24 LTS. Workflow dùng quyền GitHub `contents: read`, không deploy hay đưa secrets vào job; artifact `python-readiness-<commit>` chỉ chứa `readiness.json` và `unittest.log`, giữ 7 ngày. Workflow phải được chạy trên GitHub và cài làm required check qua cấu hình repo trước khi có thể coi nó là gate; file workflow một mình không bật branch protection.
3. Xem [hợp đồng review](REVIEW_API_CONTRACT.md), [observations](OBSERVATION_API_CONTRACT.md), [frame](FRAME_API_CONTRACT.md), đặc biệt timeout IRSA, quota, khác biệt release và giới hạn khoa học. Kiểm tra CSP, chức năng có maxDuration tương ứng 15/30/120 giây và package size phù hợp môi trường thực; CI không chứng minh các giới hạn đó được nhà cung cấp chấp nhận.

## Staging và production smoke

Checkpoint 0.10 đã được merge qua [PR #1](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/pull/1) tại `63b1bd75cd7bbca52f1e33d332ece2855cf93756`, deployment `dpl_pHZ12WnQeRriKjmjezZPfA1rSPDF`. Smoke đầu tiên đạt 24 response checks: static hash theo Git blob, metadata/no-data/input, cutout thật và review MongoDB ổn định ID/expiry/isolation/ID-only deletion; nhận xét QA được kiểm tra xóa hết. Có một timeout IRSA 504 ở lần thử trước, truy vấn sau thành công; không diễn giải thành uptime/SLO. Verifier khi đó chưa commit nên đây là receipt vận hành ban đầu, chưa phải chuỗi tái lập đầy đủ.

`scripts/verify_production_milestone.py` bổ sung receipt bất biến cho cả pass/fail, không ghi cookie/nội dung note/ID review. Nó so byte từ commit Git, vì working copy Windows có thể dùng CRLF, và yêu cầu `X-App-Commit` của ba API trùng commit đang kiểm. Sau khi source verifier đã commit và đúng bản đó lên production, chạy `python -m scripts.verify_production_milestone --write-smoke`; lệnh tạo/đọc/xóa duy nhất một review QA trong phiên riêng. Mỗi upstream GET chỉ thử lại tối đa một lần với 502/504 và giữ mọi status. Không retry POST tự động. Receipt ở `data/raw/benchmark/production-smoke-*.json`; không ghi đè receipt đã có. Cần kiểm lại bản phát hành mới trước khi dùng nó làm bằng chứng nghiệm thu.

PR #2 đã lên production tại `fbdc9b85e732c65e04f5a3341674b04cd6508709`, deployment `dpl_6PLkero2XYy2X9ZYGrGKJMUcFmKe`. [Receipt từ verifier đã commit](evidence/0.10/production-fbdc9b8.json) đạt 24 response checks và xác minh `X-App-Commit` của cả ba API đúng commit đó; cleanup QA đã xác nhận. Working tree khi chạy còn chứa phát triển quota mới, nên chỉ các Git blob và API của commit nói trên được chứng nhận. Không dùng receipt này để nói bản quota chưa deploy đã được kiểm tra.

PR #3 phát hành quota atomic tại `c88fe57ed10f551c4e330abfb63da2a74481dd2d`, deployment `dpl_CWVm5qSJb2d7npBPv1ngV7vw3HGG`. Hai check bắt buộc đạt; Python CI chạy 182 test, bốn raw-cache skip, có cả bốn test concurrency trên replica set thật. [Receipt production](evidence/0.10/production-c88fe57.json) đạt 24 response checks, commit của ba API khớp, transaction QA hoạt động trên M0 và cleanup đã xác minh. Đây không phải test concurrency/load/failover trên M0; các phần này cùng restore/rollback vẫn cần bằng chứng riêng.

PR #4 phát hành `c65d79baf90d0b159dc139c159dcf4d3f3cc23bc`, deployment `dpl_EqFMcAJ6TgkqAYP6LwtJuApxrr5Z`, sau 208 test CI (năm raw-cache skip) và cả hai check bắt buộc đạt. [30 response checks](evidence/0.10/production-c65d79b.json) đã xác minh đủ artifact mới, ba API commit và cleanup QA. [Lượt trước](evidence/0.10/production-c65d79b-failed.json) có hai frame response 502 trong khoảng 1 giây rồi dừng trước ghi review; lần chẩn đoán sau trả 200. Log cũ chỉ có `upstream_or_fits`, nên không xác định được nguyên nhân cụ thể của hai 502. Giữ cả fail và pass; không tính đây là SLO hoặc bỏ hai lỗi khỏi lịch sử.

PR #6 phát hành báo cáo phổ tại `906af662afab4bbc5c60cf2b9199ec38b04c98a9`, deployment `dpl_Cv1CKpe7GgmxVEnCUe4ehipTJFyR`. [CI](evidence/0.10/ci-pr6-6d45a21.json) có 273 test, 11 raw-cache skip và hai check bắt buộc đạt. [37 response checks](evidence/0.10/production-906af66.json) giữ một observations 504 và GET retry 200, đồng thời xác minh current artifact/API hash và cleanup review. [Lỗi DNS client riêng](evidence/0.10/production-906af66-client-dns-failed.json) dừng trước HTTP: không được tính là response lỗi của Vercel. Lượt mạng được phép sau đó mới cung cấp bằng chứng public. Chưa xác lập baseline/SLO hoặc xác định nguyên nhân cold-query timeout.

Workflow Python bổ sung replica set MongoDB 8.0 disposable, image chính thức được [pin bằng digest](evidence/0.10/mongo-image.json), chỉ publish loopback `127.0.0.1:27027`. Các test transaction dùng database synthetic UUID riêng và xóa đúng database đó; không nhận URI hay secrets production. Replica set được khởi tạo và test ngay trong check Python bắt buộc hiện có. Kết quả concurrency thật phải đạt trước khi phát hành quota; môi trường một node này không chứng minh throughput, failover hay entitlement trên Atlas M0.

Lượt CI `41085237290` dừng trước test: image MongoDB báo lỗi kernel Linux ≥6.19, theo [SERVER-121912](https://jira.mongodb.org/browse/SERVER-121912). Workflow đã ghim `ubuntu-22.04`; [manifest runner chính thức](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2204-Readme.md) tại lúc sửa ghi image `20261026.341.1`, kernel `6.8.0-1070-azure`. Job in `uname -sr` và giữ log khởi động để xác minh môi trường thực mỗi lượt. Không vô hiệu hóa kiểm tra khởi động của MongoDB hoặc giảm cách ly container. Label Ubuntu vẫn được GitHub cập nhật, không phải snapshot VM bất biến.

Nhánh `main` đã bật cấu hình người dùng chấp thuận: hai check Python/JavaScript từ GitHub Actions app 15368 bắt buộc và nhánh phải cập nhật, mọi thay đổi qua PR với 0 reviewer bắt buộc, áp dụng cả admin, giải quyết hết conversation, chặn force-push và xóa nhánh. Quyền này không thay thế review khoa học. Actions được pin ở SHA của các bản chính thức v7.0.0; CI không nhận credential production.

- Dùng staging có database và guest session tách biệt. Kiểm tra trang, manifest/hash và điều hướng; test review tạo/đọc/xóa trong phiên thử dùng một lần, xác nhận phiên khác không đọc/xóa được, và không tái sử dụng ghi chú thật. Kiểm tra QR2/QR3, no-data/overflow, đơn vị, error state khi upstream lỗi, và từng ảnh thực: grid, nguồn/cutout SHA, mask, tương phản, release, MJD. Không suy luận nguồn được phát hiện từ ảnh hay metadata. Vì IRSA có thể timeout, lưu status/request ID và phân biệt upstream không sẵn sàng với kết quả `no_data`.
- Chỉ sau khi xác định đúng deployment production và được phép thực hiện smoke có ghi, chạy `python scripts/smoke_production.py`. Script đang hard-code URL production và **tạo rồi xóa một review thử**; nó không phải script staging. Xác minh cleanup thành công, đối chiếu hash với commit triển khai, và không ghi cookie, note hay URL database vào log/ticket. Không chạy các truy vấn ảnh diện rộng hoặc lưu lượng cao như một smoke test.
- Một smoke pass chỉ nói các đường được thử hoạt động lúc đó; không chứng minh restore, load, tính đúng khoa học hoặc mọi browser đều đạt. Ghi rõ các bước chưa chạy và lý do.

## Rollback và quan sát

Trước release ghi lại deployment trước đó và commit/hash đã xác minh. Khi rollback thực sự cần thiết, chuyển traffic về deployment đã biết hoạt động bằng cơ chế Vercel của dự án, sau đó kiểm tra URL/deployment ID, manifest hash và các smoke read-only trước khi ghi lại kết quả. Rollback code không khôi phục MongoDB; không tự restore database vào production khi điều tra. Nếu schema thay đổi, xem tương thích trước khi chuyển traffic. Chưa có bằng chứng ở đây rằng rollback đã được diễn tập.

Các API phát structured log với request ID, status, nhóm lỗi và latency; log không chủ ý chứa cookie, ghi chú, URI MongoDB, IP thô hay tọa độ. Dùng request ID để nối sự kiện trong giới hạn quyền truy cập, kiểm tra thực tế nền tảng không tự ghi query string/header nhạy cảm, và đặt thời hạn lưu theo chính sách đã được người vận hành duyệt. Cache công khai frame có thể trả request ID và retrieval timestamp của response được cache. Không thu thập nội dung review để theo dõi.

Helper `_telemetry.py` bổ sung allowlist trường log, severity theo status (2xx/3xx info ra stdout, 4xx warning và 5xx error ra stderr), mã lỗi frame và HTTP status từ IRSA khi có. Không log URL/body upstream. [Đối chiếu production fc17f96](evidence/0.10/telemetry-fc17f96.json) xác nhận request 200 có JSON `level:info`, còn 504 có JSON `level:error` trên stderr, **nhưng Vercel vẫn gắn platform level `info` cho dòng 504 này**. Bộ lọc lỗi phải parse `status/level` trong JSON ứng dụng; chỉ chọn platform error sẽ bỏ sót lỗi đã quan sát. Không suy tỷ lệ lỗi từ số dòng: deduplicate bằng application request ID vì mỗi request có thể có cả platform event và application event. Verifier giữ mã JSON lỗi hợp lệ trong receipt fail mà không sao chép body.

Theo dõi số request, tỷ lệ lỗi 4xx/5xx và timeout theo endpoint/category, latency p50/p95/p99, tỷ lệ cache hit nếu có dữ liệu, kích thước lưu trữ Mongo và mức sử dụng/timeouts của function. Phân biệt mất telemetry với hệ thống khỏe. Chưa có SLO hay ngân sách lỗi được đo: trước khi cấu hình alert, lấy baseline tải thực tế, chọn cửa sổ đo, mục tiêu availability/latency và ngân sách cùng chủ sở hữu, thử thông báo và ghi lại kênh nhận. Các giới hạn timeout hiện tại là giới hạn cấu hình, không phải số đo SLO. Chưa có bằng chứng load test; chỉ thử tải có phạm vi và tần suất được phép của IRSA, ngừng khi lỗi/tải tăng.

## Backup và diễn tập restore MongoDB

[Primitive backup/restore tổng hợp](BACKUP_RESTORE_PROTOCOL.md) dùng Fernet/BSON và giới hạn cứng ở loopback fixture, hai prefix UUID riêng. Không có CLI hoặc route production. Các unit test mã hóa không thay thế hai test replica set thật; CI phải cài `requirements-ops.txt` (tách khỏi bundle web). Đích production, custody key, retention, deletion journal và RPO/RTO chưa được kiểm chứng.

Đừng giả định M0 có backup miễn phí tự động. [Tài liệu MongoDB Free Cluster Backups](https://www.mongodb.com/docs/atlas/backup/cloud-backup/free-cluster-backup/) hiện mô tả tính năng snapshot M0 là private preview trả phí tùy chọn, cần payment method; các trang tổng quan có thể mô tả khác theo phiên bản/triển khai. Kiểm tra trực tiếp tier, khu vực, trạng thái backup, chi phí và khả năng áp dụng tại thời điểm vận hành; **không tự bật dịch vụ trả phí**. Nếu chưa có backup đã được kiểm chứng, ghi rõ nguy cơ mất review. Review guest có TTL 180 ngày, mang dữ liệu riêng tư; bản sao cũng phải được mã hóa, giới hạn truy cập và có thời hạn xóa phù hợp.

Để lên kế hoạch một drill không phá dữ liệu, người vận hành chuẩn bị quyền tối thiểu hiện có, nơi lưu mã hóa có kiểm soát và **database sandbox tách biệt** có thể restore; nếu quyền hoặc môi trường chưa có, dừng và ghi blocker, không mở rộng quyền tùy tiện. Dùng công cụ MongoDB Database Tools theo [mongodump](https://www.mongodb.com/docs/database-tools/mongodump/) và [mongorestore](https://www.mongodb.com/docs/database-tools/mongorestore/) với config chứa URI/secret được bảo vệ, không đặt URI hay mật khẩu trên command line, log hoặc CI artifact. Xuất riêng database review, ghi phiên bản tool, thời điểm và hash archive; chỉ restore vào sandbox bằng cấu hình đích riêng và kiểm tra namespace, index, TTL, số bản ghi còn hiệu lực cùng việc đọc/xóa review thử. Không copy bản restore lên production hoặc thay đổi collection hiện hữu như một phần drill. Xóa bản tạm theo chính sách sau khi được phép, xác minh quyền và ghi bằng chứng thời gian sao lưu/khôi phục để đo RPO/RTO thực tế. Không coi tài liệu này là bằng chứng rằng backup hay restore đã diễn ra.


## Release 8032493

PR #7 qua hai check bắt buộc tại e26cfa0; Vercel production
`dpl_AH4SZFa3yuCrq1N41ni4pYkzU4F2` READY, public alias giữ nguyên.
[Deployment metadata](evidence/0.10/deployment-8032493.json) tách khỏi
[bằng chứng 45 response](evidence/0.10/production-8032493.json). 31 static
asset khớp Git blob, cả ba API đúng commit và phiên QA được cleanup. Hai GET
metadata 200 mất 3,141/5,781 giây, frame 200 mất 2,657 giây; không có retry
upstream trong lượt này. Các 400/403 là input/Origin probe có chủ đích.
Lượt này không xóa hay thay thế lịch sử 502/504; chưa có SLO/load/recovery
production được chứng minh. Reviewer guest/credential scope giữ nguyên.

## Baseline review mức tải nhỏ

Protocol `d7fd8f9` đã khóa trước một lần đo trên production `8032493`:
[60/60 API request đạt](REVIEW_LOAD_RESULTS.md), 12/12 phiên khách QA được
xác minh rỗng sau cùng, không cần cleanup phụ hoặc retry. p95 GET 1,937 s,
POST 0,203 s, DELETE 0,141 s. Tối đa ba request cùng lúc; đợt sau cách lúc
hoàn tất đợt trước ít nhất sáu giây. [Receipt](evidence/0.10/review-load-8032493.json)
giữ đủ latency/status/request ID đã lọc và kiểm toán lại nguồn/cadence.
Baseline hai phút dưới 0,5 request/s này không thay thế SLO, saturation,
quan sát dài hạn, failover, backup/restore hoặc rollback. Không đo lại để
thay receipt bất lợi; các lỗi upstream từ trước vẫn thuộc lịch sử vận hành.

## Sự cố đóng gói sau PR #8

PR #8 merge ở `ffbd7c1` sau [382 test CI](evidence/0.10/ci-pr8-2151ac4.json),
13 optional raw-cache/photutils skip và bốn suite Node đạt. Hai deployment
[cached](evidence/0.10/deployment-ffbd7c1-failed.json) và
[không cache](evidence/0.10/deployment-ffbd7c1-nocache-failed.json) cùng lỗi
`ENOENT` khi đóng gói bytecode `vercel_runtime`. Log ghi bundle 226,29 MB vào
bước tối ưu dependency. Rebuild không cache xác nhận stale cache đơn thuần
chưa giải thích đầy đủ lỗi. Bản public trước đó vẫn phục vụ; CI xanh không
đồng nghĩa source mới đã phát hành.

API review chỉ cần ID selection, hash, detection qualification và analysis
hash, nên contract server mới giữ đúng các trường đó trong 3.084 byte, có
hash nguồn và kiểm tra stale. `data/**` và UI assets được loại khỏi ba function
bằng `excludeFiles`, vẫn giữ trên CDN. Source/product khoa học không đổi.
Test isolated chỉ có thư mục `api` xác minh đọc contract và từ chối review
sai/analysis cũ. Cần build Vercel và smoke đủ artifact/API/cleanup trên commit
mới trước khi coi đây là khắc phục đã kiểm chứng. [Vercel Python configuration](https://vercel.com/docs/functions/runtimes/python/api-directory)
mô tả phạm vi loại file khỏi function; điều này không tự chứng minh build.
