# Sao tham chiếu thật và kiểm tra hiện diện nguồn

Hai phép thử đã hoàn tất, nhưng **chưa đủ để thay mô hình đo WISE 0855 hoặc cấp sai số chuyển động đã hiệu chuẩn**. Nội suy ePSF không cải thiện đồng đều các thước đo trên sao thật. Quy tắc nhận nguồn đạt điều kiện đã khóa ở mức 600 µJy trong mô phỏng có điều kiện; ở 300 µJy, tỷ lệ thu hồi còn rất thấp.

[Mở báo cáo trên web](https://nosleepclub-nasa-spherex.vercel.app/#reference-presence). Tab **Sao thật** so vị trí với Gaia; tab **Có nguồn hay chỉ nhiễu?** hiển thị cả ca không có mục tiêu và ca có nguồn mô phỏng. Các bản gzip đầy đủ chỉ tải khi bấm vào liên kết.

## Cấu hình được khóa trước phép thử

| Bước | Commit | Phạm vi |
|---|---|---|
| Khóa sao tham chiếu | `71f63ca4bab85e9ee51c539cd46ae5bfd50c8bc2` | 21 sao × 20 exposure × 2 ePSF; 840 lượt |
| Khóa quy tắc nhận nguồn | `627fe211bd144d0d0e9f9b5b2042316418c54788` | Hai tập random riêng, toàn bộ 7.992 lượt và tiêu chí đã định |
| Niêm phong ngưỡng | `6fc5b7c7506333c0f320405718f08ca7d9cfa693` | Đủ 1.998 null calibration, trước khi sinh validation |
| Mã xuất và audit | `1cac567` | BVLS tại nghiệm lưu; QR và tính lại điểm số từ dữ liệu đã lưu |

Các commit khóa được tạo cục bộ trước bước tương ứng, sau đó đưa lên lịch sử GitHub cùng bản phát hành. Không gọi đây là một đăng ký nghiên cứu bên ngoài. Cả hai thí nghiệm dùng ảnh WISE đã mở; **không query, tải pixel hoặc đo 30 trường dành cho calibration/validation/holdout mới**. Các sản phẩm 0.3–0.9, linked-flux và neighbor-intervention trước đó được giữ nguyên.

Protocol chi tiết: [sao thật](REFERENCE_STAR_PROTOCOL.md), [nhận nguồn](SOURCE_PRESENCE_PROTOCOL.md). Design lưu hash của source, test, protocol, các sản phẩm đã mở và raw input. Runtime dùng đúng các gói đã pin; mỗi worker CLI yêu cầu một thread số học. Đây là cấu hình yêu cầu, không phải phép đo số thread backend.

## 1. Vị trí trên sao thật

Giữ đủ 21 sao từng được chọn từ ảnh và 20 exposure D6 QR2. Mỗi sao được đo độc lập trên từng exposure với ePSF gần nhất và ePSF nội suy. Cùng pixel, VARIANCE gốc, danh sách hàng xóm và mặt phẳng nền được dùng ở cả hai nhánh. Flux mục tiêu/hàng xóm được fit có dấu, không dùng ràng buộc phổ của WISE.

Vị trí Gaia được chuyển tới IMAGE MJD-AVG UTC. Với 14 sao từng tham gia căn chỉnh, sao đang được đánh giá bị loại khỏi nghiệm translation của chính nó; bảy sao mang nhãn heldout cũ dùng các sao training cũ. Nhãn cũ được giữ cho provenance, **không làm chúng thành validation chưa mở**. Sai số catalog năm tham số được giữ với tương quan giữa 20 thời điểm trong từng ma trận 40×40 riêng; đó chưa phải covariance centroid/căn chỉnh tổng.

| Mẫu số | Kết quả |
|---|---:|
| Lượt định trước / có bản ghi terminal | 840 / 840 |
| Fit hoàn tất / fit thất bại | 718 / 0 |
| Lỗi chuẩn bị vẫn giữ | 122 |
| Cặp sao × ảnh hoàn tất cả hai nhánh | 359 / 420 |
| Cặp qua sàng lọc số ở cả hai nhánh | 357 / 420 |
| Sao có ít nhất một cặp hoàn tất | 19 / 21 |

122 lượt lỗi gồm **116 thiếu lề ảnh** và **6 thiếu pixel hợp lệ quanh tâm dự kiến**. Chúng tương ứng 61 cặp bị từ chối, không được thay nguồn hoặc chạy lại với điều kiện dễ hơn. Hai sao không có kết quả vẫn có hàng `0/20` và giá trị không xác định trong bảng web/JSON. Một sao chỉ có hai cặp hợp lệ; không suy ra độ ổn định thời gian từ trường hợp đó.

| Trên cùng 359 cặp hoàn tất | ePSF gần nhất | ePSF nội suy |
|---|---:|---:|
| RMS radial so Gaia (″) | 0,934327 | 0,924057 |
| Trung vị radial (″) | 0,380255 | 0,345538 |
| P90 radial (″) | 0,876152 | 0,942167 |
| Trung bình Đông / Bắc (″) | −0,017431 / 0,073362 | −0,022827 / 0,082513 |

Nội suy giảm nhẹ RMS và trung vị nhưng **tăng P90**, nên chưa chọn nó làm ePSF mới. Đổi giữa hai ePSF gây dịch vị trí trung vị **0,066879″**, lớn nhất **0,431565″**. Đây là độ nhạy mô hình trên mẫu đang xem, không phải sai số độc lập của WISE 0855.

Nếu chỉ xem cùng 357 cặp qua sàng lọc số, RMS là **0,603717″ / 0,588622″**, P90 là **0,859338″ / 0,897138″**. Hai cặp bị loại về số học không bị xóa khỏi mẫu 359; giao diện mặc định giữ mọi cặp hoàn tất. Sàng lọc số vẫn chưa chứng nhận đúng nguồn, như failure 16,8″ của [pilot trước](NEIGHBOR_INTERVENTION_RESULTS.md).

Audit dựng lại sample và template tại điểm đã lưu, model/residual, KKT của hệ tuyến tính, đường đi IRLS và chi phí các final start thành công bằng BVLS độc lập. Lỗi chuẩn bị được replay; lỗi optimizer, nếu có, chỉ giữ input/provenance, không thử lại. Jacobian/rank vị trí chưa được kiểm lại bằng một phương pháp độc lập. Đủ bản ghi, mô hình có thể tái dựng, và độ chính xác thiên văn là ba điều khác nhau.

[Kiểm tra khoa học bổ sung](evidence/0.10/reference-presence-science-audit.json) xác nhận **6.459 final start thành công** đã được replay, giữ **3 final start thất bại**. Chênh chi phí lớn nhất là `4,55e-13`, vi phạm KKT theo thang cột lớn nhất `8,47e-15`. Đây là sai khác số học, không phải sai số vị trí.

Giới hạn còn lại: một trường đã mở, chọn sao từ ảnh trước đây, số ảnh mỗi sao khác nhau và sai số dùng chung giữa các sao/exposure. Không coi 718 fit là 718 quan sát độc lập. Upstream WCS/ePSF có thể dùng Gaia; thành viên tập huấn luyện upstream chưa biết. Chuyển vị trí dùng Earth parallax/proper motion bậc một, chưa có đầy đủ observer/perspective/radial-velocity. Residual gồm các thành phần đó, căn chỉnh và mô hình ảnh; chưa quy toàn bộ cho ePSF.

## 2. Hiệu chuẩn ngưỡng và validation nhận nguồn

Phép thử dùng một bố cục strict đã mở, hai ảnh trước và hai ảnh sau. Mỗi nhánh ePSF xét lưới 441 vị trí cố định. Điểm số có dấu được tính sau khi chiếu ra khỏi nuisance nền/hàng xóm; toàn bộ phép tìm cực đại, hai mùa và hai ePSF được đưa chung vào bước học ngưỡng. Đây là kiểm hiện diện mục tiêu, chưa phải đo centroid hoặc liên kết chuyển động.

Calibration có 999 null mỗi loại nền, tổng **1.998/1.998**, không có lỗi. Ngưỡng là cực đại trên cả hai ca: **17,70381304535502**. Ngưỡng không phải S/N, mức sigma hay xác suất phát hiện. File seal có `validation_generated: false` để ghi nhận trạng thái **tại lúc niêm phong**, trước validation; trường này không được sửa sau khi nghiên cứu hoàn tất.

Validation riêng có **5.994/5.994** lượt, không có lỗi. Mỗi ca dưới đây có mẫu số 999, dùng luồng PCG64 khác calibration và các study trước:

| Cảnh validation | Được chấp nhận /999 | Tỷ lệ quan sát | Cận một phía 97,5% | Tiêu chí khóa trước |
|---|---:|---:|---:|---|
| Plane, không có mục tiêu | 0 | 0% | Báo nhầm ≤0,3686% | Đạt ≤1% |
| Bậc hai, không có mục tiêu | 0 | 0% | Báo nhầm ≤0,3686% | Đạt ≤1% |
| Plane, 300 µJy | 46 | 4,6046% | Thu hồi ≥3,3906% | Chỉ báo cáo |
| Plane, 600 µJy | 928 | 92,8929% | Thu hồi ≥91,1196% | Đạt ≥80% |
| Bậc hai, 300 µJy | 55 | 5,5055% | Thu hồi ≥4,1741% | Chỉ báo cáo |
| Bậc hai, 600 µJy | 870 | 87,0871% | Thu hồi ≥84,8479% | Đạt ≥80% |

Không có báo nhầm quan sát được không có nghĩa tỷ lệ báo nhầm thật bằng không. Cận binomial được tính theo từng ca. Hai cận null 97,5% cho phát biểu đồng thời ít nhất 95% trong hai ca null đã định; **không gộp cả bốn gate thành một tuyên bố tin cậy chung 95%**. Lỗi được tính là false accept ở ca null và là miss ở ca positive khi xét gate, nên không thể cải thiện chỉ bằng cách bỏ lượt lỗi.

Đây là một bước tiến của quy tắc mô phỏng có điều kiện ở 600 µJy. Nguồn 300 µJy bị bỏ sót phần lớn, và chưa có kiểm chứng false-alarm trên bầu trời thật. **Chưa áp dụng ngưỡng này để xác nhận hoặc lọc phát hiện trong workspace WISE.**

Truth Gaussian tích phân theo pixel khác family fitter; noise dùng Gaussian với thang VARIANCE quan sát và source/neighbor-Poisson ramp lý tưởng theo gain có binding điều kiện. Scorer dùng **VARIANCE quan sát gốc**, không dùng error oracle từ generator. VARIANCE đó có thể đã chứa photon noise của nguồn thật; chưa phải phân rã noise detector được kiểm chứng. Không có nguồn mục tiêu trong null, nhưng hàng xóm vẫn có mặt.

Audit độc lập dựng lại template/native geometry, dùng QR kiểm phép chiếu SVD và tính lại đủ **7.992/7.992** điểm số, vị trí thắng lưới và quyết định từ vector dữ liệu đã lưu. Hash của data, source/gain/background và seed được kiểm. Audit này **không sinh lại noise từ RNG**, không đo độ phủ covariance và không biến 7.992 lượt noise thành 7.992 trường trời độc lập.

Điểm validation gần ngưỡng nhất cách **0,0091881** đơn vị điểm số; không có quyết định nào chỉ cách ngưỡng ở mức sai khác làm tròn của replay QR.

## Dữ liệu và cách kiểm tra

- Sao thật: [overview](../web/data/reference-stars/overview.json), [design](../web/data/reference-stars/design.json), [840 bản ghi/audit và covariance catalog](../web/data/reference-stars/records.json.gz), **14.164.757 byte gzip**.
- Nhận nguồn: [overview](../web/data/source-presence/overview.json), [design](../web/data/source-presence/design.json), [seal ngưỡng](../web/data/source-presence/threshold.json), [toàn bộ 7.992 lượt và geometry](../web/data/source-presence/records.json.gz), **71.148.124 byte gzip**.
- SHA-256 bản nén và bản giải nén nằm trong mỗi overview. Raw FITS và journal từng lượt nằm trong `data/raw/` đã ignore. Browser chỉ tải hai overview khi mở mục mới; không tự giải nén hoặc tải các audit lớn.

Với raw cache đã tải đúng provenance, chạy kiểm tra/xuất lại từ dữ liệu đã lưu:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.publish_reference_stars --protocol-commit 71f63ca4bab85e9ee51c539cd46ae5bfd50c8bc2
.\.venv\Scripts\python.exe -B -m scripts.publish_presence_study --protocol-commit 627fe211bd144d0d0e9f9b5b2042316418c54788 --threshold-commit 6fc5b7c7506333c0f320405718f08ca7d9cfa693
```

Các lệnh không tối ưu lại vị trí, sinh noise mới hoặc mở trường mới. Runtime/tham số phải khớp journal. [Kiểm thử sản phẩm](../tests/test_reference_presence_products.py) kiểm hash/giải nén theo luồng, source đã khóa và mẫu số mà không cần raw FITS.

## Mốc tiếp theo và điều kiện nghiệm thu

Mốc kế tiếp là **học hiệu chỉnh ePSF có ràng buộc trên tập sao development riêng, rồi kiểm tra trên sao giữ ngoài bước học, kèm covariance căn chỉnh dùng chung**. Khóa basis/độ phức tạp, chia tập theo source/exposure phù hợp và giữ các điều kiện mask trước khi fit. Không chọn mô hình chỉ từ RMS tổng đang đẹp hơn.

Điều kiện để đi tiếp: báo đủ mẫu số/abstention; cải thiện sai lệch tuyệt đối lẫn đuôi phân bố trên tập kiểm tra riêng; không làm mất nguồn hoặc suy giảm flux trong signal-preservation control; mô tả được tương quan thời gian/căn chỉnh và kiểm độ phủ covariance. Các sao/trường đã xem vẫn là development. Chỉ sau khi evaluator, power, ngân sách sai số, miền hỗ trợ và overlap được khóa mới mở **12 trường calibration, 12 validation và 6 holdout** đã dành trước.

[Bảng 20 tiêu chí](PRODUCTION_READINESS.md) tiếp tục mở. Recovery/rollback production, tải đại diện, SLO và giấy phép mã nguồn cũng còn phải hoàn tất; một gate mô phỏng đạt không đóng các hạng mục này.
