# Tách thử nền/ePSF và hiệu chuẩn theo S/N, nền — 0.9.0

Bản này chọn point model trước khi học covariance. Một ellipse phủ nhiều sai lệch hơn không làm centroid chính xác hơn. Các thí nghiệm trước được giữ nguyên; WISE 0855 vẫn dùng phép đo 0.3.0 và chưa được xác nhận chuyển động.

## Chia tập và khóa cấu hình

| Vai trò | Trường | Dữ liệu được dùng |
|---|---|---|
| Phát triển | v060m30, v150p45, v330p10, Barnard, RW Aur | Đều đã mở ở các phiên trước; so bốn point model và chọn ngưỡng đặc trưng nền |
| Calibration | q030m10, q180p20, q300m30 | Không dùng chọn point model; học covariance cho mô hình đã chọn |
| Validation ngoài | w090p10, w210m20, w350p35 | Tọa độ mới (90°, +10°), (210°, −20°), (350°, +35°); fit sau seal cuối |

Các trường được chọn theo tọa độ trước khi biết lỗi phục hồi. Không có exposure ID chung giữa ba vai trò. Trong từng trường, sao Gaia heldout không tham gia căn chỉnh. Catalog và chia sao giữ nguyên từ bước chọn bằng ảnh/catalog, không chọn lại theo sai lệch truth.

Checkpoint thiết kế **`63e2b6b`**; SHA-256 `design.json`: **`403dcadf4e75dd32219960d44eed3524e8600267f9a15d4a126ffd92c4cfcea7`**. Sau lượt phát triển sẽ có checkpoint khóa model/ngưỡng nền trước calibration và checkpoint thứ ba khóa calibrator trước validation. [design.json](../web/data/ablation/design.json) lưu URL, query, hash FITS, catalog, spectral WCS, ePSF, code và chia tập.

## Bốn point model trên cùng dữ liệu

| Tổ hợp | Nền mỗi exposure | Hình mục tiêu | Tham số phi tuyến mỗi epoch |
|---|---|---|---|
| `plane_fixed` | Mặt phẳng nghiêng bậc một | ePSF cố định | x, y |
| `quadratic_fixed` | Thêm x², xy, y² | ePSF cố định | x, y |
| `plane_flexible` | Mặt phẳng nghiêng bậc một | Hỗn hợp gốc/làm rộng | x, y, η |
| `quadratic_flexible` | Thêm x², xy, y² | Hỗn hợp gốc/làm rộng | x, y, η |

Hình làm rộng dùng Gaussian σ=0,25 pixel gốc; η∈[0,1] dùng chung cho các exposure trong epoch. Thư viện ePSF D6 vẫn là bản đã ghim. Mỗi exposure có biên độ mục tiêu, biên độ hàng xóm và nuisance nền riêng; flux không bị buộc theo W2 hoặc chuyển động dự báo ngoài. Hình dạng/vị trí hàng xóm giữ cố định.

Cả bốn nhận cùng pixel, nguồn tiêm, masks, error map, offset và covariance căn chỉnh. Dùng chung baseline **một nguồn** cho gate bất đồng vị trí; không đổi đối tượng so sánh giữa các mô hình như ở 0.8. Solver bắt đầu cùng anchor và bốn điểm lân cận. Hai vòng Huber giảm trọng số outlier; gate kiểm tra residual/noise gốc. Thiếu hạng thông tin của mô hình làm phép đo không qua gate.

Mỗi mô hình bắt lỗi riêng, nên một candidate lỗi không làm mất baseline hợp lệ. Raw covariance gồm Hessian đã marginalize nuisance, offset căn chỉnh và covariance Gaia của vector dự báo. Với η, dùng nghịch đảo Hessian đủ ba tham số; khi η chạm biên vẫn là xấp xỉ. Không cộng hạng khác biệt giữa hai model vào riêng một tổ hợp trong ablation này.

[IRSA](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html) mô tả xử lý nền cục bộ có che nguồn và fit các hàng xóm. Tool chính thức fit flux ở vị trí cố định; runner của dự án tự fit centroid, không phải phép đo do tool IRSA trả về.

Tập phát triển có **160** nguồn giả (5 trường × 4 vị trí × 2 mức S/N mỗi frame × 2 vector × 2 hình nguồn) và **55** sao Gaia heldout. Các hình nguồn là ePSF gốc hoặc blur đẳng hướng σ=0,15 pixel. Tình huống dùng cùng background/exposure có tương quan; không tính bốn model là bốn mẫu độc lập.

## Quy tắc chọn mô hình

Một model phức tạp chỉ được thay `plane_fixed` nếu:

- Mỗi trường/SNR/hình nguồn có ít nhất 4 cặp chung cả trước và sau gate; paired RMS và P90 đều không tăng; không mất thêm fit hợp lệ hay fit qua gate.
- Từng trường sao Gaia có ít nhất 3 cặp chung, cũng không tăng RMS/P90 hoặc mất fit.
- Pooled paired RMS nguồn giả giảm ít nhất 5%. Không chọn theo trung bình nếu một nhóm xấu hơn.
- Nếu không có candidate đạt, giữ baseline đơn giản. Điều này là quyết định bảo thủ, không chứng nhận baseline đúng. Chạy thêm năm phép chọn bỏ một trường để xem quyết định nhạy với trường nào; đây là chẩn đoán nội bộ trên dữ liệu đã mở.

## Đặc trưng dùng hiệu chuẩn

**S/N quan sát** là giá trị nhỏ hơn trong hai S/N epoch của fit đã chọn. Không dùng nhãn S/N nguồn tiêm để chọn nhóm. Ngưỡng S/N=10 được khai báo trước.

**Độ gồ ghề nền** đo trên pixel gốc trước khi thêm nguồn giả: vành 4–9 pixel native, bỏ lõi mục tiêu và che hàng xóm catalog bán kính 2,5 pixel. Cần ít nhất 24 pixel mỗi frame. Fit mặt phẳng có trọng số, ba lượt clip 3σ; lấy `1,4826 × MAD` residual chia noise gốc. Mỗi epoch cần ít nhất 80% frame có đặc trưng; lấy median rồi giá trị lớn hơn của hai epoch. Đây là chỉ số không đơn vị, không phải giá trị nền MJy/sr.

Ngưỡng nền là median theo trường/vùng trên **đặc trưng tập phát triển**, không theo lỗi fit, nhãn chuyển động hoặc nguồn tiêm. Nó được lưu trong `selection.json` và commit trước calibration. Chia bốn ô S/N thấp/cao × nền êm/gồ ghề. Catalog thiếu nguồn hoặc sai vị trí vẫn có thể làm đặc trưng lệch; S/N đo được ở vùng chồng nguồn cũng có thể khác S/N thật của nguồn tiêm.

## Hiệu chuẩn và gộp nhóm ít mẫu

Calibration có **192** nguồn giả ở 8 vị trí mỗi trường. Vùng chỉ số **chẵn** học F, vùng **lẻ** học α và s. Các vị trí không trùng nhưng vẫn dùng chung exposure và thư viện hiệu chuẩn; không gọi chúng là các mẫu độc lập.

Với trọng số bằng nhau theo trường rồi vùng nền, F là phần PSD của moment sai lệch `eeᵀ−Craw`, không trừ bias trung bình. Nhóm chỉ fit riêng khi **mỗi partition** có ≥12 ca, ≥3 vùng nền và ≥2 trường. F của nhóm riêng trộn với F nhóm cha bằng trọng số `B/(B+8)`, B là số vùng nền học F. Nhóm thiếu dữ liệu gộp về cùng S/N, rồi toàn tập, thay vì tự fit một ma trận từ rất ít ca.

Trên partition lẻ, chọn α nhỏ nhất trong {0;0,1;…;1} để mức phủ có trọng số đạt 68%. Nếu α=1 vẫn thiếu phủ, học s² từ phân vị Mahalanobis. Luôn s²≥1:

```text
Ccal = s² · (Craw + (0,05″)² I + α F)
```

Không thu nhỏ Craw, không trừ bias khỏi vector. Khi raw ellipse đã quá bảo thủ, thuật toán không thể sửa quá phủ bằng cách thu nhỏ. So cách **chung** và **theo nhóm** trên cùng model, cùng calibration split và cùng tập validation được cả hai hỗ trợ.

Miền hỗ trợ theo min–max S/N và nền của nhóm đã học tham số, với dung sai nhân **1,25** đã định trước. Đây là dung sai thực nghiệm, không bảo đảm ngoại suy. Ngoài miền hoặc thiếu đặc trưng thì không cấp covariance hiệu chuẩn; vẫn giữ lượt thử và raw fit trong sản phẩm. Demo báo cả số trong miền / qua quality gate, tránh làm tỷ lệ phủ đẹp hơn bằng cách giấu mẫu khó.

[Braun và cộng sự, ICML 2026](https://proceedings.mlr.press/v306/braun26c.html) phân biệt chẩn đoán coverage có điều kiện với coverage trung bình. Bản này dùng bảng nhóm đơn giản, không triển khai phương pháp ERT của bài báo và không có bảo đảm conformal/conditional coverage. Mẫu ít, selection/gating và distribution shift giữa trường vẫn là giới hạn chính.

## Kiểm định ngoài đã định trước

Ba trường mới có 96 nguồn giả và 33 sao Gaia giữ ngoài căn chỉnh. Hình nguồn thứ hai là blur elip `(σy,σx)=(0,06;0,22)` pixel, khác blur đẳng hướng dùng phát triển/calibration. Đây là hình nguồn stress test giả định, không phải ePSF đo vật lý độc lập. Không thêm shot noise của nguồn; noise map/mask gốc giữ nguyên.

Gate covariance yêu cầu: mức phủ 68% trong [55%,85%] ở pooled và cả bốn ô; mỗi ô có ít nhất 8 ca trong miền và 2 vùng nền; tổng ≥24 ca, ≥6 vùng nền, đủ ba trường; ≥80% ca qua quality gate nằm trong miền; diện tích ellipse trung vị ≤16 lần raw; khoảng bootstrap có chứa 68%. Bootstrap phân cấp theo trường rồi vùng, 2.000 lượt, vẫn yếu vì chỉ ba trường.

Gate vị trí so model đã chọn với `plane_fixed` trên cùng các ca, gồm RMS/P90 trước/sau gate và số fit. Chỉ xét dùng tiếp nếu đủ cả vị trí lẫn covariance; không tự thay WISE 0855.

## Kết quả

**Giữ `plane_fixed`: nền phẳng + ePSF cố định.** Không tổ hợp phức tạp nào đạt đủ điều kiện. Cả 5 lựa chọn bỏ một trường cũng giữ baseline. Đây là lựa chọn bảo thủ trên dữ liệu đã mở, không chứng nhận baseline đã ổn định ở mọi nguồn.

Checkpoint chọn model/ngưỡng nền **`1f1dae2`**; checkpoint seal trước trường ngoài **`8c7ad54`**. Protocol SHA-256 **`f6545377be850ce1c5d7e015326747be6f7e47790da01bc816b8b62c9938d83f`**. Ba trường ngoài có **135 cutout QR2**, chọn **60 exposure** thành 30 cặp phổ; code/threshold/calibrator không chỉnh sau khi mở chúng.

| Tổ hợp phát triển | Fit hợp lệ / thử | Paired RMS / P90 so baseline | Qua gate / thử | Nhóm đạt / thử |
|---|---:|---:|---:|---:|
| Nền phẳng / ePSF cố định | 152/160 | 3,110 / 2,751″ | 111/160 | 21/25 |
| Nền bậc hai / ePSF cố định | 152/160 | 1,967 / 2,660″ | 108/160 | 8/25 |
| Nền phẳng / ePSF linh hoạt | 152/160 | 3,086 / 2,843″ | 108/160 | 6/25 |
| Nền bậc hai / ePSF linh hoạt | 152/160 | 3,080 / 2,661″ | 109/160 | 6/25 |

Nền bậc hai/ePSF cố định giảm pooled RMS khoảng 36,7%, nhưng chỉ đạt 8/25 nhóm và mất thêm 3 fit qua gate. Vì vậy không chọn nó theo con số trung bình. Baseline có 21/25 nhóm đủ điều kiện so tự thân; bốn nhóm thiếu số ca cùng qua gate tối thiểu. Không hiểu “được chọn” thành chứng minh tính đúng ở cả 25 nhóm.

Ngưỡng nền đã khóa là **1,016051688**, S/N=10. Phần lớn chỉ số nền chỉ quanh mức noise; “thấp/cao” là tương đối theo tập phát triển, chưa phải nhãn có/không có nền khuếch tán vật lý.

Calibration có **140/192** ca usable qua gate: 82 ca/11 vùng nền chẵn học F, 58 ca/9 vùng lẻ học α/s. Hai ô nền thấp chỉ có 4 ca ở một vùng, một trường trong partition lẻ nên gộp theo S/N. Hai ô nền cao đủ dữ liệu học riêng. Hệ số s² của nhóm S/N thấp khoảng 2,61–2,75, nhóm S/N cao bằng 1 với α=0,6–0,7. Trên toàn calibration, cả chung/theo nhóm phủ 114/140; diện tích trung vị ×5,00→×4,30. Đây là tập dùng fit, không phải kiểm định độc lập.

**Kiểm định ngoài: chưa qua gate covariance.** Có **88/96** nguồn giả fit hợp lệ, **69/96** qua quality gate; cả 69 nằm trong miền hỗ trợ của hai cách hiệu chuẩn, trải trên **9** vùng nền. Raw ellipse 68% chứa **28/69 (40,6%)** vector đúng. Hiệu chuẩn chung đạt **54/69 (78,3%)**, theo nhóm đạt **57/69 (82,6%)**, nhưng không đồng đều theo trường/ô. Diện tích ellipse trung vị so raw giảm từ **×5,15 xuống ×2,23** khi đổi chung→theo nhóm. Hai mức phủ nằm trong khung pooled, nhưng ba trong bốn ô vượt trần 85%; không cho qua chỉ vì pooled đẹp hơn. Khoảng bootstrap theo trường/vùng **12,5–100%** rất rộng.

| Trường ngoài | Qua quality gate / thử | RMS / P90 · mẫu qua gate | Phủ 68% chung → nhóm | Diện tích trung vị chung → nhóm |
|---|---:|---:|---:|---:|
| w090p10 | 30/32 | 1,525 / 2,375″ | 29/30 → 30/30 | ×5,11 → ×2,24 |
| w210m20 | 31/32 | 1,489 / 2,298″ | 24/31 → 26/31 | ×5,17 → ×2,23 |
| w350p35 | 8/32 | 2,065 / 2,748″ | 1/8 → 1/8 | ×4,23 → ×3,81 |

| Ô đặc trưng quan sát | Trong miền / qua gate | Phủ 68% chung → nhóm | Diện tích trung vị chung → nhóm | Ca dùng hệ số gộp |
|---|---:|---:|---:|---:|
| snr_low_bg_smooth | 11/11 | 11/11 (100,0%) → 11/11 (100,0%) | ×3,43 → ×7,15 | 11 |
| snr_low_bg_structured | 22/22 | 11/22 (50,0%) → 19/22 (86,4%) | ×3,28 → ×6,57 | 0 |
| snr_high_bg_smooth | 12/12 | 12/12 (100,0%) → 12/12 (100,0%) | ×5,95 → ×2,15 | 12 |
| snr_high_bg_structured | 24/24 | 20/24 (83,3%) → 15/24 (62,5%) | ×5,67 → ×1,81 | 0 |

w350p35 chỉ còn một vùng nền có 8 ca qua gate. Chỉ 1/8 nằm trong ellipse 68% sau cả hai cách hiệu chuẩn, dù S/N và nền đều trong miền. Sai lệch 1,19–2,95″, bias trung bình [−1,098;−1,568]″. Tám ca cùng nền/exposure, không phải tám kiểm chứng độc lập. Điều này cho thấy kiểm tra miền S/N/nền chưa đủ bảo vệ trước mọi bias; chưa xác định nguyên nhân vật lý. Demo đánh dấu vùng nền này trên ảnh gốc, ghi rõ ảnh chưa có nguồn tiêm. Chọn ca khó là chẩn đoán sau kiểm định, không dùng chọn lại model/hệ số.

Sao Gaia thật: **27/33** fit số hợp lệ, **23/33** qua quality gate, RMS trên mẫu qua gate **0,412″**. Chỉ **5/23** trong miền covariance; **18** được báo ngoài miền, thay vì ngoại suy floor cho sao sáng. Phủ 5/5 của nhóm nhỏ trong miền không được gọi là “độ chính xác 100%”.

`point_passed=true` ở lượt ngoài vì mô hình giữ lại chính baseline, có đủ số ca và các phép so tự thân không đổi. Nó không chứng minh vị trí chính xác hơn; kết luận tổng vẫn false và WISE 0855 không được nâng mức tin cậy. Có thể xem các ca lỗi và lý do ở JSON từng trường.

**95/95 kiểm thử offline đạt**, gồm bốn tổ hợp, cách ly exception, routing không dùng truth, tách floor/quantile theo vùng, pooling, PSD không thu nhỏ, từ chối ngoài miền, tái tạo lựa chọn/calibrator, mọi mẫu số và hash chain. Đây là kiểm chứng phần mềm/provenance, không phải xác nhận thiên văn.

## Tái tạo và giới hạn

Raw FITS/cache nằm trong `data/raw/` bị ignore, các manifest/hash trong `design.json`. Với môi trường science đã cài và cache đúng hash:

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_ablation_data
.\.venv\Scripts\python.exe -m scripts.run_ablation design
# Commit thiết kế và mã.
.\.venv\Scripts\python.exe -m scripts.run_ablation develop
# Commit kết quả phát triển và selection.json.
.\.venv\Scripts\python.exe -m scripts.run_ablation calibrate
.\.venv\Scripts\python.exe -m scripts.run_ablation seal
# Commit calibrator và seal trước validation.
.\.venv\Scripts\python.exe -m scripts.run_ablation validate
.\.venv\Scripts\python.exe -m scripts.build_ablation_overview
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Wrapper `run_ablation` chặn ghi đè phase khi đã có selection, calibrator, seal hoặc summary hoàn tất tương ứng. Các field result được dùng lại khi tiếp tục một phase bị ngắt; source/rule hash phải khớp. Core `ablation_study` được giữ nguyên theo source hash; nên dùng wrapper để tránh vô tình viết lại summary/metadata bằng cách gọi core trực tiếp. Không gọi dữ liệu đã mở thành “mới”; lượt thử mới cần output/protocol và trường ngoài mới.

Web vẫn là HTML/CSS/JS tĩnh; chỉ API nhận xét dùng Python/MongoDB. Fit khoa học chạy offline. Giới hạn còn lại gồm vị trí biết trước, phổ rộng tại tâm, covariance noise/offset chưa đầy đủ tương quan, hàng xóm/ePSF cố định và số trường ít. Kiểm thử phần mềm đạt không tương đương xác nhận một chuyển động thiên văn.


## Bước tiếp theo và điều kiện nhận

Trước khi mở thêm trường, chẩn đoán vùng w350p35 và các ca outlier phát triển trên dữ liệu **đã mở**: kiểm tra nguồn chồng, residual, nhiều nghiệm centroid, mask, vị trí detector và độ nhạy khi bỏ exposure. Không sửa hệ số theo chính vector truth của một ca rồi gọi nó là cải thiện tổng quát.

Thử thêm đặc trưng quan sát về độ chồng nguồn, phần thông tin centroid/biên độ còn lại và độ nhạy giữa các lần bỏ exposure. So xem chúng dự báo được miscoverage ngoài S/N/nền hay không bằng validation nội bộ theo trường, với quy tắc gộp/từ chối khai báo trước. Bổ sung trường calibration đa dạng để hai nhóm nền thấp có ít nhất ba vùng và hai trường ở từng partition, thay vì chỉ một vùng học scale.

Chỉ khóa lượt ngoài mới sau khi có cải thiện tái hiện ở nhiều vùng/trường: RMS/P90 không xấu hơn, tỷ lệ phủ không thiếu/quá phủ theo cả trường lẫn nhóm, số ca trong miền không giảm để che mẫu khó và ellipse không phình vô ích. Các ngưỡng và tập mới phải khóa trước fit. Mục đích là xử lý bias có cấu trúc, không chỉ làm con số pooled gần 68%.
