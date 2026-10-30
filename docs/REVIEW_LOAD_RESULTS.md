# Baseline tải nhỏ cho API nhận xét

Protocol và mã khóa tại `d7fd8f93595301e4f8a3f7b5700af5bc046ce2dc` trước lần chạy
duy nhất từ **21:21:16 đến 21:23:18 UTC ngày 2026-10-30**. Đích public vẫn là
API commit `80324933bfab21a73a0a2e3f05c447b99f2a81d2`; không xuất credential,
thay MongoDB, mở quyền hay chạy vào dữ liệu nhận xét có sẵn.

[Receipt đầy đủ](evidence/0.10/review-load-8032493.json) giữ cả 60 request và
kiểm toán lại percentile, concurrency, khoảng cách giữa các đợt cùng source
hash tại commit khóa. Raw SHA-256:
`e9245bd39cf2af3b036dcc2b70f0c0cba792094211fd36456d0716428fe4c0c7`.

| Phép đo | Kết quả | Gate khóa trước |
|---|---:|---:|
| API HTTP 200, đúng contract và commit | 60/60 | 60/60 |
| GET, gồm phiên mới | p95 1,937 s, n=36 | ≤3 s |
| POST | p95 0,203 s, n=12 | ≤5 s |
| DELETE | p95 0,141 s, n=12 | ≤5 s |
| POST và DELETE gộp | p95 0,188 s, n=24 | ≤5 s |
| Phiên QA đã xác minh rỗng sau cùng | 12/12 | 12/12 |
| Request cleanup bổ sung / lỗi bất ngờ | 0 / 0 | Không cần retry |

**Đạt baseline đã định.** 12 phiên khách độc lập chạy theo bốn nhóm ba phiên,
năm đợt GET–POST–GET–DELETE–GET mỗi nhóm. Tối đa ba request cùng lúc,
đợt sau bắt đầu ít nhất sáu giây sau khi đợt trước hoàn tất. Chỉ tạo 12 nhận
xét QA có nội dung ngẫu nhiên, không quá ba nhận xét cùng tồn tại; xóa đúng
ID do thử nghiệm tạo. Receipt không chứa cookie, note, review ID hay scope
gốc. Script không retry để làm đẹp latency.

Đây là quan sát khoảng hai phút, ở mức tải trung bình dưới 0,5 request/s,
từ một client. Chưa đo concurrency lớn, quota saturation, dữ liệu gần đầy,
khách ở nhiều khu vực, failover hay SLO theo thời gian. Các lỗi IRSA 502/504
ở release trước vẫn được giữ; baseline này chỉ đo API review, không IRSA
hay frame. Backup, phục hồi production, deletion reconciliation và rollback
vẫn là tiêu chí mở. Không suy throughput tối đa hoặc uptime từ 60 request.

Bước vận hành tiếp theo: khóa workload đại diện và cửa sổ quan sát dài hơn,
đo riêng endpoint/mức tải và tỷ lệ lỗi trước khi đặt SLO; đồng thời chuẩn bị
drill phục hồi trong database sandbox với nơi lưu mã hóa, key custody,
retention và RPO/RTO được xác định. Không dùng baseline này để bỏ các gate đó.

Xem [protocol](REVIEW_LOAD_PROTOCOL.md),
[20 tiêu chí](PRODUCTION_READINESS.md) và [runbook](OPERATIONS.md).
