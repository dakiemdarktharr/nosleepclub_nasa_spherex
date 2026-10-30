# Nền ảnh, ePSF và hiệu chuẩn sai số — 0.8.0

Bản này kiểm tra riêng hai câu hỏi: vector đo có ít lệch hơn không, và ellipse sai số có bao phủ được sai lệch thật không. Nới ellipse không làm vị trí đo chính xác hơn. Số đo WISE 0855 vẫn dùng bản 0.3.0; chưa xác nhận chuyển động và chưa có vision model được huấn luyện.

## Chia tập và khóa thí nghiệm

| Vai trò | Trường | Dùng để làm gì? |
|---|---|---|
| Phát triển | Barnard, RW Aur | Trường đã mở ở các phiên trước; kiểm tra candidate và ca lỗi |
| Hiệu chuẩn | q030m10, q180p20, q300m30 | Trường đã mở ở 0.7; học error floor và scale từ nguồn giả |
| Kiểm định | v060m30, v150p45, v330p10 | Tọa độ mới (60°, −30°), (150°, +45°), (330°, +10°); chỉ fit sau khi khóa hệ số |

Đã tải **122 cutout QR2** ở ba trường kiểm định; chọn **58 exposure** thành 29 cặp có phổ tương thích. Tâm trường được khai báo theo hình học trước khi xem phép đo. Chọn cặp theo spectral WCS tại tâm, trong dải 4,55–4,94 µm, chênh lệch tối đa 0,5 bề rộng băng; tối đa 10 cặp mỗi trường. Không có exposure ID chung giữa ba vai trò. Thư viện hiệu chuẩn D6 chung vẫn tạo phụ thuộc hệ thống.

Trong từng trường, sao Gaia được chọn bằng catalog/hình ảnh trước fit, tối đa 32 sao trải theo góc phần tư. Sắp ID theo SHA-256, mỗi sao thứ ba giữ ngoài căn chỉnh. Sao giữ ngoài không được dùng để học covariance. Các offset căn chỉnh 0.7 đã xuất được dùng lại cho trường đã mở; trường mới chạy cùng recipe IR + median/MAD. Cả hai mô hình nhận **cùng offset, covariance căn chỉnh và pixel nguồn tiêm**.

Checkpoint thiết kế **`4e7a50c`**, SHA-256 `design.json` **`1e5805754bd5afba8ed50cf7b7ddff4f1c18345fc34999de5c4d1f17e8889f7d`**, được commit trước lượt hiệu chuẩn. Một checkpoint thứ hai khóa cả calibrator trước khi mở trường kiểm định. Các manifest FITS, catalog, spectral WCS, ePSF, URL truy vấn và hash mã nguồn nằm trong [design.json](../web/data/covariance/design.json). Kết quả không được ghi đè bởi runner.

## Thay đổi mô hình vị trí

[IRSA khuyến nghị dùng ePSF mới cho cả QR2](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/). Dự án đã dùng thư viện này từ trước; 0.8 thêm một phép thử độ rộng quanh ePSF đã ghim phiên bản. Đây không phải một ePSF mới do NASA cung cấp.

- Baseline: IR deblend + nền phẳng bậc một + hai vòng Huber của 0.7.
- Candidate: thêm `x²`, `xy`, `y²` vào nuisance nền riêng từng exposure. Biên độ nguồn và hàng xóm vẫn fit tự do bằng phép chiếu SVD có trọng số.
- ePSF mục tiêu là hỗn hợp giữa ePSF gốc và phiên bản Gaussian blur σ=0,25 pixel gốc. Một hệ số η∈[0,1] dùng chung cho các exposure trong mỗi epoch. Không dịch tâm ePSF theo truth; hình dạng/vị trí hàng xóm vẫn cố định.
- Fit đồng thời `(x,y,η)`. Covariance vị trí lấy khối 2×2 của nghịch đảo Hessian đầy đủ để marginalize η; tại biên η, đây vẫn là xấp xỉ.
- Giữ các ngưỡng chất lượng 0.7 trên noise và residual gốc. Gate bất đồng của candidate so với **IR robust 0.7**; baseline 0.7 giữ phép so với fit một nguồn. Vì tham chiếu bất đồng khác nhau, số qua gate không chỉ phản ánh thay đổi point estimator. RMS ghép cặp trước gate giúp đánh giá riêng vị trí.
- Thêm `0,25·ddᵀ`, với `d` là chênh vector dịch chuyển 0.8−0.7, vào covariance candidate. Đây là hạng nhạy mô hình PSD theo quy ước, không phải covariance xác suất đã được suy ra từ hai fit độc lập.

[Tool spectrophotometry chính thức của IRSA](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html) có nền ảnh và mô hình nguồn lân cận nhưng chỉ fit flux ở vị trí cố định. Runner này tự fit centroid; không phải số đo do tool IRSA trả về.

## Hiệu chuẩn covariance

Tập calibration có 8 vị trí nền cố định mỗi trường × S/N mỗi frame {2,4} × vector {đứng yên, [0,6; 0,05] pixel} × hình nguồn {ePSF gốc, blur đẳng hướng σ=0,15 pixel}: **192 lượt**. Cả hai estimator nhận cùng ảnh tiêm. Không thêm shot noise của nguồn; noise/mask gốc giữ nguyên. Các lượt không đủ pixel, không hội tụ hoặc không qua gate đều giữ trong kết quả.

Chỉ các nguồn giả **candidate qua gate** ở tập calibration được dùng học hai tham số:

1. Trọng số tổng bằng nhau cho mỗi trường, mỗi vùng nền có mẫu đạt trong trường và mỗi tình huống trong vùng đó. Đặt `F = PSD₊(Σw·(eeᵀ−Craw)) + (0,05″)²I`, trong đó `e` là sai lệch vector [Đông, Bắc], `Craw` gồm nhiễu fit, căn chỉnh, hạng nhạy mô hình. `PSD₊` bỏ các trị riêng âm. Vì dùng moment không trừ trung bình, F chứa cả ảnh hưởng bias.
2. Tính `q=eᵀ(Craw+F)⁻¹e`. `s²=max(1, weighted_quantile68(q)/2,2788685664)`. Khóa `Ccal=s²(Craw+F)` cho mọi trường kiểm định. Không trừ bias khỏi centroid, không thu nhỏ ellipse.

Đây là **error envelope thực nghiệm**. Cùng tập calibration được dùng học F và s, chỉ có ba trường và nhiều nguồn giả dùng chung nền. Không diễn giải nó là posterior, xác suất phát hiện hay conformal coverage được bảo đảm. [Oliveira và cộng sự, JMLR 2024](https://www.jmlr.org/papers/v25/23-1553.html) phân tích vai trò của giả định exchangeability; thí nghiệm này không kiểm chứng các điều kiện để áp dụng bảo đảm lý thuyết cho dữ liệu phụ thuộc.

## Kiểm định đã định trước

Tập validation có 4 vị trí nền mỗi trường × hai S/N × hai vector × hai hình nguồn: **96 lượt**. Hình nguồn thứ hai là blur elip `(σy,σx)=(0,06;0,22)` pixel, khác họ blur đẳng hướng dùng calibration. Đây là stress test hình dạng giả định, chưa phải phép đo ePSF vật lý độc lập.

Tiêu chí khóa trước gồm:

- Mỗi trường/SNR/hình nguồn: ít nhất 4 cặp fit số chung; RMS và P90 không tăng; không giảm số fit hợp lệ hoặc số qua gate. Sao Gaia thật cần ít nhất 3 cặp chung, RMS không tăng và không giảm số fit/qua gate.
- Nguồn giả mới qua gate: tỷ lệ phủ ellipse danh nghĩa 68% trong [55%,85%], khoảng bootstrap bao gồm 68%, ít nhất 24 fit và 6 vùng nền có mẫu đạt, đủ cả ba trường.
- Median diện tích ellipse hiệu chuẩn / thô ≤16. Diện tích mỗi ellipse tỷ lệ `√det(C)`; đây không phải tỷ lệ bán kính.
- Chỉ xét dùng tiếp nếu cả gate vị trí và gate covariance đạt. Không tự thay kết quả WISE 0855.

Bootstrap phân cấp lấy lại trường rồi vùng nền, 2.000 lượt với seed cố định. Nó tôn trọng một phần phụ thuộc trong vùng, nhưng ba trường quá ít để có khoảng tin cậy mạnh hoặc đo distribution shift toàn bầu trời. Mốc 55–85% và trần diện tích là tiêu chí phát triển của dự án, không phải chuẩn NASA.

## Kết quả và giới hạn

**Chưa đạt tiêu chí thay mặc định.** RMS nguồn giả trên 88 cặp chung giảm 2,079→1,961″, nhưng P90 tăng 2,222→2,372″ và hai trong ba trường tăng RMS. Nhóm cùng qua gate (59 cặp) có RMS 1,261→1,281″. Không thể kết luận mô hình mới giảm bias đồng đều.

Checkpoint trước kiểm định: **`d7d92dc`**. Protocol SHA-256: **`a9f7a8d67b6119e016dac8ba503fbad51ab3f3b29802e8e3993fef4f8e5f1303`**. Mã và tham số không đổi sau khi mở tập mới.

| Trường RA/Dec | RMS nguồn giả cũ → mới, trước gate | Candidate qua gate / thử | Phủ 68% thô → hiệu chuẩn, trên mẫu qua gate | Diện tích trung vị | Bias mới Đông; Bắc |
|---|---:|---:|---:|---:|---:|
| 60° / -30° | 0,945 → 0,993″ (32 cặp) | 32/32 | 24/32 → 32/32 | ×3,58 | -0,409; -0,027″ |
| 150° / +45° | 1,368 → 1,418″ (24 cặp) | 21/32 | 9/21 → 18/21 | ×3,65 | -0,918; -0,692″ |
| 330° / +10° | 3,096 → 2,843″ (32 cặp) | 14/32 | 0/14 → 10/14 | ×3,62 | -0,122; 0,944″ |

Tổng nguồn giả candidate: **88/96** fit hợp lệ, **67/96** qua gate, trải trên 9 vùng nền của ba trường. Phủ ellipse 68% tăng **33/67 (49,3%)→60/67 (89,6%)**; phủ 95% tăng **55/67→65/67**. Diện tích ellipse trung vị tăng **3,65 lần**. Tỷ lệ phủ 89,6% vượt trần 85% đã khóa; khoảng bootstrap **71,4–100%** cũng không chứa 68%. Gate covariance **không đạt**. Nó cải thiện thiếu phủ ở v330 nhưng quá bảo thủ ở v060; một floor chung chưa ổn định theo trường.

Ma trận F đã học theo [Đông, Bắc], đơn vị arcsec²:

```text
[[ 1.892692, -0.597693],
 [-0.597693,  0.886835]]
s² = 1
```

Tập calibration có **146/192** mẫu qua gate trên **19** vùng nền. Phủ 68% trên tập này tăng **57/146→118/146**, diện tích trung vị ×3,26. Floor đã làm mức phủ có trọng số vượt mục tiêu nên scale bị chặn ở 1, không thu nhỏ trở lại. Đây là kết quả dùng để fit, không phải đánh giá độc lập.

| Sao Gaia giữ ngoài | Fit chung / thử | RMS cũ → mới | Candidate qua gate / thử | Diện tích trung vị |
|---|---:|---:|---:|---:|
| v060m30 | 10/11 | 0,943 → 0,909″ | 10/11 | ×8,58 |
| v150p45 | 5/11 | 0,862 → 0,658″ | 4/11 | ×62,74 |
| v330p10 | 10/11 | 0,304 → 0,312″ | 9/11 | ×31,20 |

Cả ba gate vị trí theo trường đều không đạt khi xét đủ các nhóm nguồn giả và sao Gaia. v060/v150 cải thiện RMS sao Gaia, v330 tăng nhẹ. Floor hiệu chuẩn trên nguồn giả S/N thấp làm ellipse Gaia sáng phình rất mạnh ở một số trường; không dùng nó như covariance đã kiểm chứng cho sao sáng.

Trường phát triển Barnard có RMS Gaia 0,256→0,264″; RW Aur 1,099→1,884″. Dữ liệu phát triển đã báo trước nguy cơ thêm tham số làm centroid kém ổn định. Đây là bằng chứng cần ablation trước khi chọn point model, không phải lý do chỉnh lại bộ validation vừa mở.

**Kiểm tra sổ lượt thử:** paired runner bắt exception chung cho hai mô hình. Audit sau lượt chạy đã fit lại baseline 0.7 độc lập cho toàn bộ **16** ca exception (8 nguồn giả, 8 Gaia) để kiểm tra có vô tình che mất baseline hợp lệ không. Cả 16 vẫn không fit được: thiếu pixel hợp lệ hoặc mục tiêu không định danh được. Không phục hồi baseline nào, không sửa dữ liệu gốc, không đổi tham số fit hoặc coverage. Audit là QA trên tập đã mở, không tính thành kiểm định mới. [failure-audit.json](../web/data/covariance/failure-audit.json) có hash đầu vào và kết quả từng ca.

**73/73 kiểm thử offline đạt**: phục hồi centroid với nền cong/hình nguồn rộng, covariance PSD không thu nhỏ, cách ly calibration/validation, tái tạo calibrator từ đúng tập, đếm mọi lượt thử, đối chiếu metric/covariance/diện tích và source/input hash. Đây là kiểm chứng phần mềm/provenance; kết luận khoa học vẫn chưa đạt gate.

Các giới hạn còn lại: fit quanh vị trí biết trước; phổ rộng tại tâm không đồng nghĩa đáp ứng phổ bằng nhau cho mọi nguồn; chưa propagate vị trí/hình dạng hàng xóm, covariance không gian của nền, sai số thư viện ePSF và tương quan offset/exposure đầy đủ. Các sao Gaia sáng nằm ngoài hai mức S/N nguồn giả dùng hiệu chuẩn; áp dụng cùng error floor lên chúng là stress test ngoại suy. Cần kiểm tra hiệu chuẩn có điều kiện theo S/N và nền trước khi dùng cho một nguồn cụ thể.

## Tái tạo

Dùng Python science environment và các raw cache đã ghim hash theo [hướng dẫn 0.7](QUALITY_VALIDATION.md). Raw FITS nằm trong `data/raw/` bị ignore. Không xóa protocol/kết quả đã mở để chạy lại như một lượt kiểm định mới. Với một thư mục output và vùng kiểm định mới được khai báo trước, quy trình là:

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_covariance_data
.\.venv\Scripts\python.exe -m scripts.covariance_study --design
.\.venv\Scripts\python.exe -m scripts.covariance_study --develop
# Commit thiết kế và mã trước bước sau.
.\.venv\Scripts\python.exe -m scripts.covariance_study --calibrate
.\.venv\Scripts\python.exe -m scripts.covariance_study --seal
# Commit calibrator và seal trước khi chạy kiểm định.
.\.venv\Scripts\python.exe -m scripts.covariance_study --validate
.\.venv\Scripts\python.exe -m scripts.build_covariance_overview
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Runner kiểm tra source/input hash và yêu cầu seal đã tồn tại trong HEAD trước khi fit validation. [calibrator.json](../web/data/covariance/calibrator.json), [validation-protocol.json](../web/data/covariance/validation-protocol.json) và [overview.json](../web/data/covariance/overview.json) nối hash đến sản phẩm nguồn.


## Bước tiếp theo và điều kiện nhận

Dùng các trường **đã mở** làm tập phát triển cho ablation 2×2: nền phẳng/bậc hai × ePSF cố định/linh hoạt. Giữ cùng pixel, căn chỉnh, hàng xóm và ngưỡng gate; tách nguồn/exposure trong validation nội bộ để tránh chọn mô hình theo chính noise đã fit. Đo RMS, P90, bias và độ ổn định theo S/N, mật độ nguồn, vị trí detector và η chạm biên.

Chỉ chọn candidate nếu không tăng RMS/P90 ở các nhóm đã định, không mất thêm fit và không chỉ cải thiện trung bình nhờ một trường. Sau đó thử floor/covariance có điều kiện theo S/N và nền trên tập calibration riêng, có shrinkage/pooling để nhóm ít mẫu không tự học floor tùy ý. Khóa model, rule phân nhóm và hệ số **trước** một tập ngoài mới. Điều kiện nhận vẫn cần cả vị trí, mức phủ hai phía và trần diện tích ellipse; chưa áp dụng lên WISE 0855 chỉ vì pooled RMS giảm.
