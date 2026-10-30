# Quality gate và nguồn chồng — 0.7.0

**Chưa đạt tiêu chí thay phương pháp mặc định.** Mô hình mới giảm paired RMS nguồn giả ở hai trường, gần như không đổi ở trường thứ ba; sai lệch sao thật và kết quả sau gate chưa cải thiện đồng đều. 59 kiểm thử phần mềm/provenance đạt không đồng nghĩa phép đo thiên văn đã được xác nhận.

Phép thử này thêm kiểm tra chất lượng, mô hình nguồn hồng ngoại lân cận và giảm ảnh hưởng pixel outlier. Các trường Barnard, RW Aur và R Dra của bản 0.6.0 được dùng để phát triển. Ba tâm trường mới — RA/Dec (30°, −10°), (180°, +20°), (300°, −30°) — được khai báo theo hình học trước khi xem kết quả, rồi khóa cấu hình trước lượt đánh giá.

Số đo WISE 0855 đang phục vụ web được giữ nguyên. Kiểm tra ở đây dùng phổ rộng và fit quanh vị trí đã biết; chưa đo precision/recall của tìm kiếm mù.

Checkpoint trước đánh giá: **`330449c`**. Protocol SHA-256: **`9ad4bbef5c980ef55c71735587479620a2b42289b9f27408256f4f69d72e8104`**. Ba trường mới có **115 cutout QR2**, trong đó 58 exposure được ghép phổ cho lượt thử này; không dùng lại exposure của ba trường phát triển.

## Mô hình và gate

[IRSA hướng dẫn](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html) kiểm tra nguồn lân cận, cờ pixel, residual và nền ảnh khi đánh giá phép fit SPHEREx. Tool chính thức có thể fit biên độ nhiều nguồn ở các vị trí cố định; thí nghiệm này tự fit thêm centroid mục tiêu, nên không được gọi là phép đo của tool IRSA.

Mô hình mới giữ ePSF D6 đã ghim phiên bản, dùng catalog CatWISE có hiệu chỉnh tile và ưu tiên vị trí Gaia đạt chất lượng. Mỗi exposure có biên độ mục tiêu, biên độ hàng xóm và mặt phẳng nền riêng. Không buộc độ sáng SPHEREx theo W2 và không buộc vector dịch chuyển theo dự báo ngoài.

Các nguồn IR trong 8 pixel lưới trời được đưa vào mô hình, tối đa 24 nguồn sáng nhất theo W2. Nguồn catalog tương ứng mục tiêu thật được loại khỏi nuisance model; không xóa các hàng xóm còn lại. SVD xử lý các cột nuisance gần phụ thuộc. Sau fit ban đầu, hai vòng Huber IRLS giảm trọng số pixel có residual lớn; các metric gate vẫn đo trên residual và noise gốc, không chỉ trên residual đã giảm trọng số.

| Gate | Điều kiện nhận |
|---|---|
| Nghiệm | Solver hội tụ, không nằm trong 5% sát biên ±2,5 pixel, biên độ tổng dương ở từng epoch |
| Tín hiệu | S/N tổng theo mô hình mỗi epoch ≥5; sao căn chỉnh đơn frame còn cần S/N≥7 |
| Mức khớp chung | χ²r≤3 |
| Lõi nguồn | RMS residual/noise≤2,5; ≥75% pixel lõi hợp lệ; tỷ lệ residual lớn hơn 5 lần noise≤10%; cần đạt ở ≥80% frame |
| Nguồn chồng | Phần thông tin biên độ mục tiêu còn lại sau chiếu nuisance≥5% ở ≥80% frame; không phải Fisher 2D của centroid |
| Hai mô hình bất đồng | Khoảng cách hai centroid không vượt `max(0,20 pixel, 3√λmax(Σcũ+Σmới))` |
| Căn chỉnh | Ít nhất 4 sao sau gate khoảng cách chuẩn hóa bằng median/MAD; không dùng sao heldout |

Các ngưỡng là lựa chọn phát triển đã khóa, chưa phải chuẩn chứng nhận của NASA/IRSA. Hai fit dùng chung pixel nên gate bất đồng không phải kiểm định xác suất “3σ”. Khoảng cách median/MAD cũng không được diễn giải thành xác suất Gaussian, dù tên tham số trong code dùng chữ `mahalanobis`.

## Thiết kế kiểm chứng

Baseline là fitter một nguồn của bản 0.6.0. Cùng một bộ gate được áp dụng cho baseline và mô hình mới; luôn báo cả số fit hội tụ, số qua gate và số bị loại.

- Sao thật: so vector hai epoch với Gaia. Baseline dùng căn chỉnh Gaussian cũ; mô hình mới dùng centroid IR của sao training và gate median/MAD. Sao heldout không tham gia căn chỉnh hoặc hiệu chuẩn lại ellipse.
- Nguồn giả: bốn vị trí cố định × S/N thiết kế 2/4 mỗi frame × đứng yên/dịch chuyển `[0,6; 0,05]` pixel × ePSF gốc/làm rộng = **32 tình huống mỗi trường**. Hai mô hình nhận đúng cùng dữ liệu pixel và cùng căn chỉnh baseline, để tách ảnh hưởng của cách fit centroid/nguồn chồng khỏi thay đổi frame.
- ePSF làm rộng dùng Gaussian σ=0,15 pixel gốc. Đây là phép perturbation giả định, không phải PSF vật lý đã hiệu chuẩn độc lập. Không thêm shot noise nguồn.
- RMS ghép cặp chỉ dùng các lượt cả hai mô hình cùng tính được. RMS sau gate cũng dùng giao của các lượt cùng qua gate. Báo thêm RMS/P90 của mọi fit hợp lệ để không giấu các lượt được cứu hoặc bị loại.

Tiêu chí toàn bộ phép thử: ở từng trường, từng S/N và từng họ ePSF tiêm, paired RMS phải giảm, P90 không tăng, không giảm số fit tính được hoặc số qua gate. Với sao thật cần ít nhất ba cặp chung, paired RMS không tăng và số fit/qua gate không giảm. Mọi trường phải đạt; không chọn trường tốt nhất làm kết luận chung. Khoảng bootstrap 95% được lấy theo vị trí không gian, không coi các lượt dùng chung nền là độc lập.

## Kết quả trên ba trường mới

| Trường RA/Dec | Gaia truy vấn | Nguồn IR qua sàng lọc | Cặp phổ |
|---|---:|---:|---:|
| 30° / −10° | 189 | 1.011 | 10 |
| 180° / +20° | 150 | 823 | 9 |
| 300° / −30° | 1.506 | 2.722 | 10 |

### Nguồn giả: đo bias trước khi loại theo chất lượng

96 tình huống trên 12 vị trí không gian, hai mô hình cùng nhận mỗi tình huống. Các dòng trong bảng gộp hai độ sáng, hai vector và hai họ ePSF. “Tính được” đòi hỏi solver/biên/flux hợp lệ; “qua gate” kiểm tra thêm chất lượng. Đơn vị RMS là arcsec.

| Trường | Cặp chung / thử | RMS cũ → mới trước gate | Cải thiện điểm ước lượng; bootstrap 95% | Qua gate cũ → mới |
|---|---:|---:|---:|---:|
| 30° / −10° | 24/32 | **1,826 → 1,471″** | +19,4%; [2,9%; 53,8%] | 24 → 20 /32 |
| 180° / +20° | 32/32 | **1,989 → 1,991″** | −0,08%; [−0,57%; 1,04%] | 28 → 28 /32 |
| 300° / −30° | 32/32 | **5,279 → 3,725″** | +29,4%; [−17,4%; 63,9%] | 8 → 8 /32 |

Mỗi mô hình tính được 88/96 vector. Các lượt không tính được vẫn có record. Không dùng tỷ lệ 88/96 như completeness của tìm kiếm thiên thể. Bootstrap chỉ có bốn block không gian mỗi trường và chia sẻ exposure; các khoảng này là chẩn đoán hậu kiểm, không chứng minh cải thiện toàn bầu trời.

### Sau gate vẫn còn bias

| Trường | Cặp cùng qua gate / thử | RMS cũ → mới trên đúng cặp đó |
|---|---:|---:|
| 30° / −10° | 20/32 | 1,593 → 1,513″ |
| 180° / +20° | 28/32 | 2,096 → 2,098″ |
| 300° / −30° | 8/32 | **4,397 → 5,282″** |

Ở trường 300°/−30°, toàn bộ tám lượt cùng qua gate đến từ một vị trí. Bootstrap sau gate vì vậy suy biến; khoảng hẹp trong JSON không phải bằng chứng chắc chắn. Ở trường này, RMS các fit được nhận còn tăng khoảng 20%. Đây là lý do cần giữ cả kết quả trước gate, số bị loại và dữ liệu từng vị trí.

Chỉ **8/56** lượt nguồn giả được mô hình mới nhận nằm trong ellipse danh nghĩa 68%; riêng hai trường sau là 0/28 và 0/8. Gate chất lượng chưa hiệu chuẩn được ngân sách sai số. Không dùng ellipse này như xác suất phát hiện hoặc gắn nhãn “đáng tin” cho kết quả chỉ vì qua gate.

### Sao Gaia giữ ngoài căn chỉnh

| Trường | Cặp tính được / thử | RMS cũ → mới | Qua gate cũ → mới |
|---|---:|---:|---:|
| 30° / −10° | 10/11 | 0,929 → 0,969″ | 9 → 9 /11 |
| 180° / +20° | 11/11 | 1,111 → 1,054″ | 10 → 11 /11 |
| 300° / −30° | 11/11 | 0,200 → 0,228″ | 7 → 8 /11 |

Sao thật xấu hơn ở hai trường. Trường 300°/−30° qua bốn nhóm injection nhưng không qua điều kiện sao thật. Trường 30°/−10° mất bốn lượt qua gate và hai nhóm nguồn mờ không đạt. Trường 180°/+20° gần như không đổi ở injection và không qua nhóm nào. **Không trường nào qua toàn bộ tiêu chí; không thay fitter mặc định của WISE 0855.**

## Các ca phát triển đã mở

- Outlier Gaia trong trường Barnard giảm sai lệch **6,309 → 0,283″**, nhưng vẫn không qua gate vì mức khớp chung còn kém.
- Barnard’s Star giảm chênh dự báo **2,628 → 1,102″**, vẫn bị loại vì residual, lõi bị mask và mô hình không khớp tốt.
- Một sao RW Aur chuyển từ sai lệch khoảng **0,105″** sang **3,598″** dù χ²r gần 1. Gate bất đồng giữa hai mô hình chặn ca này. Residual nhỏ một mình không đủ để kết luận đúng vị trí.
- Ở R Dra, mô hình mới đo được cả tám sao heldout, sáu qua gate; baseline thiếu sao căn chỉnh nên không có so sánh ghép cặp hoặc injection công bằng. Không gọi việc cứu được fit là đã chứng minh chính xác hơn.

Các ví dụ này dùng để phát triển gate, không được tính như tập kiểm chứng mới. Những thay đổi cuối được chạy lại đầy đủ trên các trường phát triển; protocol phát triển và code hash khớp với phiên bản đã khóa. Không chỉnh solver, ngưỡng hay chọn mẫu sau khi mở ba trường đánh giá.

## Sản phẩm

- [Demo quality gate](https://nosleepclub-nasa-spherex.vercel.app/#quality-validation).
- [Protocol khóa trước](../web/data/quality/protocol.json), [kết quả đánh giá](../web/data/quality/evaluation-summary.json), [payload UI và hash](../web/data/quality/overview.json).
- [Kết quả phát triển](../web/data/quality/development-summary.json) giữ riêng với đánh giá mới.

## Giới hạn

Covariance IRLS và căn chỉnh vẫn có điều kiện, chưa mô tả đầy đủ sai số vị trí hàng xóm, màu, ePSF và tương quan giữa frame. Qua gate không có nghĩa đã tìm đúng nguồn hoặc đã xác nhận chuyển động. Phép thử làm rộng PSF chỉ kiểm tra một loại mismatch. Ba trường chưa đại diện toàn bầu trời; nguồn mờ, biến quang, mở rộng và chuyển động lớn vẫn cần đối chứng riêng.

Gate mới đầy đủ được chạy trong benchmark này. Với bộ ảnh WISE 0855 cũ trên giao diện so sánh, web chỉ kiểm tra solver/biên/χ²/S/N có trong sản phẩm đã xuất, và ghi rõ chưa chạy toàn bộ gate mới. Không gắn nhãn “đáng tin” cho phép đo cũ bằng các chẩn đoán chưa tính.

## Tái tạo

Cần cache ảnh/calibration của bản 0.6.0. FITS, XML catalog và logs mới nằm trong `data/raw/quality/` và `data/raw/benchmark/`, được bỏ qua Git. Protocol versioned giữ manifest, URL, query, hash, danh sách sao, chia mẫu và các rule.

```powershell
python -m scripts.prepare_quality_data
python -m scripts.prepare_quality_data --new
python -m scripts.quality_study --develop
# Chỉ lần đầu, trước lượt đánh giá mới:
python -m scripts.quality_study --lock
# Protocol có sẵn sẽ kiểm tra hash, không ghi đè:
python -m scripts.quality_study
python -m scripts.build_quality_overview
python -m unittest discover -s tests -v
```

Không thay code hoặc rule sau khi khóa rồi gọi kết quả đó là heldout chưa xem. Tập đánh giá đã mở sau lượt này trở thành dữ liệu phát triển cho phiên bản tiếp theo.

## Bước tiếp theo

Ưu tiên **ngân sách sai số và mô hình nền ảnh**. Dùng các trường đã mở để kiểm tra residual theo vị trí, mật độ nguồn, màu và vùng detector; phân biệt lỗi nền, ePSF, nguồn thiếu trong catalog và tương quan pixel. Gate hiện tại giúp nêu lý do từ chối, chưa thay thế được mô hình sai số đúng.

Tách tập hiệu chuẩn covariance khỏi tập đánh giá. Sau khi khóa thay đổi tiếp theo, dùng các trường chưa xem và PSF perturbation khác để kiểm tra bias, RMS/P90, số fit bị loại và coverage theo độ sáng. Chỉ nâng phương pháp mặc định khi cải thiện giữ được trên tập mới, không đổi mẫu số để làm đẹp và đối chứng sao thật không xấu đi. Chưa xác nhận chuyển động WISE 0855 từ lượt thử này.
