# Kiểm tra trên dataset mới — 0.6.0

Ngày chạy: 30/10/2026. **Pipeline chưa ổn định đủ để công bố một tỷ lệ “chính xác” chung.** Đo sao Gaia khá tốt trong một trường, nhưng còn outlier, bias với nguồn mờ và trường không đủ sao căn chỉnh. Giữ nguyên số đo WISE 0855 và mọi sản phẩm khoa học trước đây.

## Dataset đã lấy và thực sự dùng

Truy vấn [SPHEREx SIA/cutout chính thức tại IRSA](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/), dùng tọa độ trường J2000 từ SIMBAD. Tọa độ này chỉ xác định vùng lấy ảnh; vị trí sao kiểm tra được lan truyền từ Gaia DR3 tới ngày quan sát, không dùng tọa độ J2000 làm truth năm 2026.

| Trường mới | Cutout D6 QR2 tải về | Gaia G<18,5 | Ảnh được chọn | Mùa quan sát trong cache |
|---|---:|---:|---:|---|
| [Barnard’s Star](https://simbad.cds.unistra.fr/simbad/sim-basic?Ident=Barnard%27s+star) | 42 | 3.952 | 20 | 15–27/08/2025; 19/03–05/05/2026 |
| [RW Aur](https://simbad.cds.unistra.fr/simbad/sim-id?Ident=RW+Aur) | 36 | 2.413 | 20 | 11–20/09/2025; 20/02–02/03/2026 |
| [R Draconis](https://simbad.cds.unistra.fr/simbad/sim-id?Ident=%40376084&Name=V%2A+R+Dra&submit=submit) | 51 | 371 | 16 | 16/05–12/06/2025; 26/12/2025–13/01/2026 |

Tổng **129 FITS/cutout thật**, 6.736 hàng Gaia, 56 exposure được chọn theo bước sóng; 40 exposure ở hai trường chạy được phép đo, 16 ở R Dra dừng tại gate căn chỉnh. Khoảng ngày trong bảng là toàn bộ cache; ngày của các ảnh thực sự chọn có trong từng kết quả JSON. Ba trường tách nhau hơn 10°, khác trường WISE 0855 và dùng các exposure khác nhau.

SIA còn trả về 19 ảnh D6 QR3 quanh Barnard và 19 quanh RW Aur; R Dra trả 0. **Chưa tải/chạy QR3**: đây là các epoch/exposure khác, không phải cặp cùng exposure để so hiệu chuẩn QR2/QR3. Dataset bổ sung có thể khai thác sau là [unTimely/time-resolved unWISE](https://arxiv.org/abs/2209.14327), W1/W2 và baseline dài hơn; chưa chạy trong báo cáo này, cần adapter riêng cho PSF, mask, noise và bandpass.

## Phương pháp đã khóa trước khi xem kết quả

Checkpoint **`8aa2536`**, protocol SHA-256 **`58d1860a985ef0475309d710621039d75078ce95cea1c2b4a0665363411250f3`**. [Protocol](../web/data/benchmark/protocol.json) chứa code hash, manifest đầu vào đầy đủ, URL/FITS hash, catalog/query/calibration hash, cặp ảnh, sao tham chiếu và vị trí tiêm nguồn. Không sửa solver, ngưỡng hoặc chia mẫu sau khi mở kết quả.

- Dùng fitter ePSF trên pixel gốc và phép căn chỉnh translation theo Gaia của bản đang phục vụ web. Adapter đổi tọa độ trường và nhãn epoch; không sửa các module khoa học đã khóa từ trước.
- Giữ detector D6, 4,55–4,94 µm, mismatch bước sóng ≤0,20 hoặc ≤0,50 bandwidth; tối đa 10 cặp mỗi cấu hình. Lấy hai mùa QR2 đầu tiên ngăn bằng khoảng trống >60 ngày, không chọn mùa theo kết quả fit.
- Chọn nguồn bằng catalog, hình học và ảnh thăm dò; tối đa 32, chia theo SHA-256 source ID **trước fit**: mỗi nguồn thứ ba giữ ngoài căn chỉnh. Áp dụng quality gate cũ cho sao huấn luyện căn chỉnh; không dùng heldout để hiệu chỉnh frame hay covariance.
- Barnard: 21 nguồn training được chọn, 9 đủ điều kiện; 11 heldout. RW Aur: 21 training, 14 đủ điều kiện; 11 heldout. R Dra: 15 training, chỉ 3 đủ điều kiện; 8 heldout chưa được đo vì frame cần ít nhất 4 sao.
- Mỗi cấu hình chạy được: bốn vị trí khóa trước × S/N thiết kế mỗi frame 2/4 × đứng yên/dịch chuyển `[0,6; 0,05]` pixel = 16 phép phục hồi. Tâm fit tự do trong ±2,5 pixel. Không lựa chọn vị trí bằng sai số sau fit.

`valid` ở đây nghĩa solver hội tụ, không chạm biên và biên độ tổng dương ở cả hai epoch. **Không có nghĩa mô hình mô tả tốt ảnh**; mọi χ² và outlier vẫn được giữ. Không thêm quality cut hậu kiểm để làm RMS nhỏ đi.

## Kết quả sao thật giữ ngoài căn chỉnh

Đây là sai lệch **vector dịch chuyển giữa hai epoch** so với Gaia, không phải sai số vị trí tuyệt đối. Các hàng dưới dùng bộ phổ rộng.

| Trường | Đo được / thử | RMS | Trung vị | P90 | Kết quả |
|---|---:|---:|---:|---:|---|
| Barnard | 11/11 | **1,921″** | 0,336″ | 0,447″ | Một outlier 6,309″ được giữ |
| RW Aur | 11/11 | **0,182″** | 0,105″ | 0,162″ | Sai lệch lớn nhất 0,512″ |
| R Dra | — | — | — | — | Chỉ 3 sao căn chỉnh đạt điều kiện, cần ≥4 |

Outlier Barnard có Gaia ID `4472836876874287744`, χ²r hai epoch 2,37/5,79. Trung vị/P90 khá nhỏ nhưng RMS lớn cho thấy tác động của đuôi lỗi; không loại nguồn này khỏi báo cáo. RW Aur trong bảng là **sao Gaia trong trường quanh RW Aur**, không phải đã xác minh biến quang của chính RW Aur.

Phổ chặt và rộng ở Barnard chọn **cùng 10 cặp**, cho kết quả trùng nhau hoàn toàn. RW Aur và R Dra không có đủ cặp qua ngưỡng phổ chặt; không nới gate. Không tính hai cấu hình Barnard là hai bộ kiểm chứng độc lập.

## Nguồn giả trên nền ảnh thật

| Trường, phổ rộng | Fit hợp lệ / thử | RMS các fit hợp lệ | P90 | Trong 1 pixel / thử | Trong ellipse 68% / thử |
|---|---:|---:|---:|---:|---:|
| Barnard | 15/16 | **2,103″** | 3,896″ | 15/16 | 7/16 |
| RW Aur | 13/16 | **6,009″** | 12,142″ | 11/16 | 8/16 |

Một pixel rộng 6,15″. “Trong 1 pixel” là ngưỡng phục hồi vị trí tương đối thô, không phải tỷ lệ phát hiện đúng. RMS chỉ tính fit hợp lệ; số fit lỗi và mọi mẫu số vẫn được giữ. Không lấy RMS sao sáng để đại diện độ chính xác nguồn mờ.

| Trường / S/N thiết kế mỗi frame | RMS đứng yên | RMS dịch chuyển | Fit hợp lệ / 8 |
|---|---:|---:|---:|
| Barnard / 2 | 1,594″ | 3,022″ | 7/8 |
| Barnard / 4 | 0,700″ | 2,249″ | 8/8 |
| RW Aur / 2 | 8,990″ | 10,448″ | 5/8 |
| RW Aur / 4 | 1,072″ | 1,010″ | 8/8 |

Có 48 lượt chạy nguồn giả qua ba cấu hình khả dụng, nhưng chỉ **32 tình huống duy nhất** vì Barnard phổ chặt/rộng trùng hoàn toàn. Tương tự, có 33 lượt fit heldout nhưng chỉ 22 sao duy nhất. Các stamp cùng trường và phép thử cùng stamp vẫn tương quan. Không suy ra khoảng tin cậy thống kê từ việc coi tất cả lượt là độc lập.

## Đối chứng chuyển động lớn: Barnard’s Star

Gaia DR3 `4472832130942575872`; lan truyền bằng Astropy có vận tốc xuyên tâm −110,11 km/s từ SIMBAD, có perspective acceleration và thị sai quan sát bậc nhất. Đây là dự báo ngoài, không ép fit ảnh theo vector đó.

- Vector đo (Đông; Bắc): **[+0,394; +3,138]″**.
- Vector dự báo tại effective MJD của hai fit: **[+0,575; +5,760]″**.
- Sai lệch vector **2,628″**; χ²r **334,30 / 202,57**.

Solver hội tụ nhưng mô hình không khớp tốt ảnh; formal covariance nhỏ không mô tả được bias này. Không gọi đây là kiểm chứng thành công chuyển động Barnard. Cần kiểm tra residual, cờ pixel, hình nguồn, phổ và biến đổi vị trí trong epoch; chưa xác định nguyên nhân là saturation hay yếu tố riêng nào.

## Giới hạn của phép đo này

Đây là benchmark **local fitting tại vị trí biết trước**, chưa đo precision, recall, completeness hay false-positive rate của tìm kiếm mù. Phần tô sáng/nhấp nháy trên web giúp người xem; chưa có vision model được huấn luyện. Không công bố “web chính xác X%”.

Covariance chẩn đoán dùng centroid hình thức + covariance translation trung bình với giả định frame độc lập; thêm covariance Gaia vi sai ở sao thật. **Không tái tạo toàn bộ ngân sách sai số 0.3.0**, không chạy bootstrap target/calibration 128/256 lượt cho mọi nguồn mới, không thêm heldout scatter vào ellipse rồi tự đánh giá coverage trên chính heldout. Thiếu tương quan frame, hệ thống không gian, sai số ePSF/phổ/nguồn nền; covariance dự báo Barnard còn xấp xỉ và bỏ qua bất định vận tốc xuyên tâm.

Nguồn giả dùng **cùng ePSF gần nhất** với fitter, chưa thêm shot noise hay PSF perturbation độc lập. S/N 2/4 là thiết kế theo noise map và mô hình tuyến tính, không phải S/N đo sau fit và không mô phỏng phổ WISE 0855. Các điều kiện này có thể làm test lạc quan; bias nền ảnh vẫn hiện rõ. Hai trường đo được là mẫu quá nhỏ để đại diện bầu trời; R Dra là một lỗi khả dụng quan trọng, không được bỏ qua.

## Xem và tái tạo

- [Web: benchmark mới](https://nosleepclub-nasa-spherex.vercel.app/#external-benchmark).
- [Summary JSON](../web/data/benchmark/summary.json), [Barnard](../web/data/benchmark/barnard.json), [RW Aur](../web/data/benchmark/rw-aur.json), [R Dra](../web/data/benchmark/r-dra.json).
- FITS và phản hồi catalog thô ở `data/raw/benchmark/`, được bỏ qua Git; input manifest/hash đã được giữ trong protocol versioned.

Cần calibration D6 đã tải bằng quy trình WISE 0855 trước đó. Sau đó:

```powershell
python -m scripts.prepare_benchmark_data --download
# --lock chỉ dành cho lần đầu, trước đánh giá; không ghi đè protocol có sẵn.
python -m scripts.benchmark_accuracy
python -m unittest discover -s tests -v
```

Script kiểm tra hash code, calibration, Gaia, manifest và FITS trước khi chạy. Nếu upstream thay đổi dữ liệu, cần khôi phục đúng cache/hash hoặc tạo phiên bản protocol mới; không ghi đè bản đã mở. Lần tải đầu gặp timeout CDS và HTTP 504 IRSA; tọa độ được kiểm tra từ trang SIMBAD, IRSA được thử lại và cả 129 FITS cuối cùng đều tải thành công.

## Bước tiếp theo

Ưu tiên **gate chất lượng mô hình và chống outlier**: hiển thị rõ solver hội tụ nhưng χ² cao, từ chối phép đo thiếu sao căn chỉnh, kiểm tra residual/nguồn chồng nhau trước khi đưa độ tin cậy. Dùng ba trường đã mở để phát triển; không tái sử dụng như heldout mới.

Sau đó khóa mô hình và dùng các trường chưa xem cùng PSF perturbation độc lập để kiểm chứng lại. Tiêu chí: đủ sao căn chỉnh ở từng exposure; báo đủ thất bại; giảm RMS/P90 ở nguồn mờ, kiểm tra coverage với hệ thống được mô phỏng; đối chứng chuyển động thật phải khớp dự báo trong ngân sách sai số hợp lý. Chưa nâng mức tin cậy của WISE 0855 từ benchmark hiện tại.
