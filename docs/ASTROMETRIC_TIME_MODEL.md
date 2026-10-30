# Mô hình thời gian và GLS astrometry theo exposure

Đây là module tính toán độc lập cho dữ liệu SPHEREx: đọc thời điểm IMAGE, dựng ma trận thiết kế và fit GLS có kiểm tra rank. Module chưa được nối với point estimator, không tạo phép đo nguồn mới, không khẳng định detection hoặc tách được parallax trên dữ liệu thực.

## Thời điểm và hệ quy chiếu

`parse_image_header` yêu cầu header `EXTNAME=IMAGE`, `TIMESYS` hợp lệ và ba giá trị số hữu hạn `MJD-BEG`, `MJD-AVG`, `MJD-END`. Các từ khóa MJD này được hiểu là **MJD tuyệt đối, đơn vị ngày**, không cộng `MJDREF`. Để từ chối offset bị nhầm thành ngày tuyệt đối, module chỉ nhận MJD 40000–100000: đây là giới hạn phạm vi của công cụ SPHEREx, không phải định nghĩa tổng quát của MJD. `MJDREF` khi có phải hữu hạn; các dạng scalar/split phải khớp. `TIMEZERO`/`TIMEOFFS` khác 0, `TREFPOS` barycentric hoặc không nhận diện, duplicate keyword quan trọng, thứ tự sai, midpoint lệch tâm quá 1 giây hoặc `DATE-*` mâu thuẫn MJD quá 5 ms đều bị từ chối. DATE-* có thì kiểm tra, không tự suy scale khi thiếu TIMESYS. Các scale được hỗ trợ là UTC, TAI, TT, TDB, TCG, TCB; không mặc định UTC cho metadata thiếu hoặc nhận UT1/LOCAL.

`astropy.time.Time` giữ scale gốc và chuyển rõ sang TDB cho thời gian thiết kế. Năm là 365,25 ngày TDB. Đây là chuyển thang thời gian, **không phải** hiệu chỉnh light-travel time của photon về barycenter. Tài liệu [Astropy Time](https://docs.astropy.org/en/stable/api/astropy.time.Time.html) mô tả scale và định dạng; [SPHEREx Explanatory Supplement](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf) mô tả các keyword MJD và vị trí tàu.

Vị trí Trái Đất dùng `get_body_barycentric('earth', time.tdb, ephemeris='builtin')` với kết quả ICRS barycentric theo AU, không phụ thuộc cấu hình ephemeris toàn cục và không tải kernel. [Astropy](https://docs.astropy.org/en/latest/api/astropy.coordinates.get_body_barycentric.html) mô tả convention này. `X_SC/Y_SC/Z_SC` không được cộng vào vector Trái Đất: header chỉ khai gốc GEOCENTER, chưa xác minh orientation trục. Hàm riêng `spacecraft_parallax_bound` chỉ dùng norm XYZ và giả định giá trị theo km trong hệ Cartesian geocentric trực giao. Nó tính cận góc bậc nhất `||r_sc||/AU × parallax_assumed`, không phải hiệu chỉnh vector, uncertainty ngẫu nhiên hay tham số fit; thiếu gốc/tọa độ thì trả unavailable.

## Ma trận, GLS và dự báo

Tại hướng ICRS cố định `(α,δ)` do caller cung cấp, chọn vector đơn vị Đông `e=(-sin α, cos α, 0)` và Bắc `n=(-sin δ cos α, -sin δ sin α, cos δ)`. Ma trận cho mỗi exposure hai hàng Đông/Bắc:

```text
east(t)  = east0  + mu_east  * Δt − parallax * (r_earth/AU · e)
north(t) = north0 + mu_north * Δt − parallax * (r_earth/AU · n)
```

Vị trí và parallax có đơn vị arcsec; proper motion là arcsec/năm TDB; Δt tính so với `reference` do caller chọn. Đông là `ΔRA cos(dec)`, Bắc là `Δdec`; RA wrap được xử lý tuần hoàn, cực có hướng trục quy ước theo RA cung cấp. Đây là xấp xỉ tangent-plane bậc nhất quanh hướng cố định, không phải tọa độ tuyệt đối mới, không có prior chuyển động/độ sáng, và chưa mô hình perspective acceleration, aberration, chromaticity hay astrometric reference systematics.

`design_matrix(..., model='pm_only')` dựng **4** tham số `[east0, north0, mu_east, mu_north]`. `model='pm_parallax'` dựng **5** tham số trên cộng `parallax`. Hai lựa chọn hoàn toàn tường minh; không tự sửa mô hình hay giữ parallax cố định để tránh singularity. `fit_gls` nhận vector `[east_0,north_0,east_1,north_1,...]` và covariance **đầy đủ 2N×2N** theo arcsec², bao gồm block giữa các exposure. Nó kiểm tra covariance đối xứng dương xác định, whiten bằng Cholesky, scale từng cột và kiểm SVD. Không dùng pseudoinverse: bậc tự do ≤0, rank thiếu hoặc condition number sau scale >1000 mặc định gây `UnidentifiableDesign`, kèm chẩn đoán. Ngưỡng 1000 là guard số học có thể cấu hình, không phải bảo đảm precision khoa học; rank đầy đủ cũng không chứng minh tín hiệu thị sai có thể đo được. Covariance tham số là conditional GLS với covariance đầu vào, không tự nhân reduced χ² hay bổ sung hệ thống thiếu.

`predict` trả mean và covariance của fitted mean. Với covariance observation mới và block covariance train/new, nó trả thêm covariance của `y_new − fitted_mean`, tính cả cross-terms. Nếu không cung cấp cross-block thì giả định bằng 0; joint covariance được kiểm dương bán xác định. Đây là dự báo tuyến tính vô điều kiện, không cộng hiệu chỉnh kriging hay xử lý cross-covariance không được cung cấp.

Kiểm tra đối xứng và PSD chuẩn hóa theo độ lệch chuẩn của từng phần tử, với dung sai theo machine epsilon và kích thước ma trận; không dùng một ngưỡng tuyệt đối cố định theo arcsec². Ma trận covariance đầu vào chỉ được đối xứng hóa nếu chênh lệch nằm trong dung sai làm tròn, sau đó vẫn phải qua Cholesky. Joint covariance được kiểm PSD trong thang correlation, kể cả trường hợp singular PSD hợp lệ; cross-block không được cắt hoặc thay thế. Covariance residual được kiểm lại PSD theo thang của các hạng dùng để tính nó: giá trị âm vượt sai số làm tròn gây lỗi; nếu eigenvalue âm chỉ ở mức làm tròn, một hiệu chỉnh đường chéo nhỏ được ghi rõ tại `prediction_residual_psd_roundoff_adjustment_arcsec2`, cùng ngưỡng tại `prediction_residual_psd_tolerance_arcsec2`. Đây là xử lý số học, không phải thành phần uncertainty vật lý.

Ví dụ sử dụng (chỉ minh họa API; `headers`, `y`, `cov` phải đến từ dữ liệu đã được kiểm tra):

```python
from scripts import astrometric_time_model as atm

times = [atm.parse_image_header(h).midpoint for h in headers]
reference = times[len(times) // 2]
A, metadata = atm.design_matrix(times, reference, ra_deg, dec_deg, 'pm_parallax')
fit = atm.fit_gls(A, y, cov)  # raises UnidentifiableDesign when unsupported
B, _ = atm.design_matrix(new_times, reference, ra_deg, dec_deg, 'pm_parallax')
prediction = atm.predict(fit, B, new_cov, train_new_cross_cov)
```

## Audit development đã chạy trên cache WISE

```powershell
.venv/Scripts/python.exe -m unittest tests.test_astrometric_time_model -v
.venv/Scripts/python.exe -m scripts.audit_exposure_times
```

[development-audit.json](../web/data/time-model/development-audit.json) lưu hash manifest, code, từng FITS, URL, thời gian và trạng thái từng exposure. Audit chỉ đọc 31 ảnh đã tải trong manifest coadd WISE, không khẳng định chúng đều là cặp primary strict/broad, không đọc centroid hay fit nguồn. Toàn bộ 31 IMAGE header hợp lệ: 16 exposure tháng 11/2025 và 15 tháng 4/2026. `MJD-AVG` sau `MJD-OBS` khoảng 57,55873–57,55882 giây trong cache này; MJD-OBS là đầu exposure ở các header đó.

Khoảng trải midpoint trong hai mùa là 4,616 và 5,297 ngày. Với giả định minh họa từ [Luhman 2014](https://arxiv.org/pdf/1404.6501), `μ_east=−8,06″/năm`, `μ_north=+0,70″/năm`, `π=0,454″`, độ dịch lớn nhất dự tính giữa hai exposure cùng mùa do Earth-only là 0,108″ và 0,126″. Cộng cận bảo thủ của hai vị trí tàu làm các cận có điều kiện lần lượt 0,107793″ và 0,126300″; mỗi exposure có cận bỏ vị trí tàu khoảng 2,134–2,136 × 10⁻⁵″. Các giá trị giả định là ví dụ, không phải centroid đo được, fit target, hay cận tổng quát cho acceleration và sai số thiết bị.

Với identity weights và reference TDB gần median:

| Sampling | PM-only rank / condition | PM+parallax rank / condition | Diễn giải số học |
|---|---:|---:|---|
| 2025-11 riêng | 4 / 2,67 | 5 / 17.683 | PM+parallax bị từ chối do condition >1000 |
| 2026-04 riêng | 4 / 167,19 | 5 / 8.429 | PM+parallax bị từ chối do condition >1000 |
| 31 exposure gộp | 4 / 2,31 | 5 / 113,55 | Qua guard số học dưới identity weights; chưa chứng minh precision |
| Hai mùa co về đúng hai thời điểm | 4 / 2,31 | 4 / không xác định | PM+parallax thiếu rank, bị từ chối |

Variation trong từng mùa tạo thêm rank đại số trong thiết kế gộp, nhưng điều đó không chứng minh parallax có thể được đo chính xác: covariance thực, reference chung, blending, model PSF và độ nhạy đều chưa đưa vào audit. Bước tiếp theo là dùng covariance đầy đủ được kiểm định và mô phỏng có epoch withheld trên các trường đã mở; chỉ cân nhắc suy luận thật sau khi thiết kế, độ phủ và precision được xác minh độc lập. Không thay đổi sản phẩm 0.3–0.9 hoặc số đo WISE đã công bố.
