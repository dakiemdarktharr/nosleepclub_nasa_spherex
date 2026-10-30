# WISE 0855: đối chứng flux riêng và flux có ràng buộc phổ

Đây là phép thử development trên **20 cutout QR2 trường rộng đã mở**,
không phải validation mới hoặc thay số đo công bố. Cấu hình broad dùng 10
exposure mỗi epoch; strict dùng hai mỗi epoch, là tập con của broad. Không
tính hai cấu hình là 24 exposure độc lập. Khóa code/input trước lần chạy
point model mới; dữ liệu WISE và vị trí đo cũ đã được xem từ các nghiên cứu
trước, vì vậy không gọi đây là phép thử ngoài mẫu.

## Giả thuyết và đối chứng

Fit quanh anchor sky-grid (31,5;31,5), bounds ±2,5 pixel; mỗi epoch có vị trí
và flux tự do riêng. Không buộc vị trí theo vector chuyển động hoặc flux
theo trị tuyệt đối của JWST. Nhánh control `independent` có flux Jy riêng
mỗi frame. Candidate định trước `shared_r7_68_a0` có một biên độ Jy mỗi
epoch nhân với tỷ số phổ PRISM. So sánh này nhằm tách tác động giảm số
nuisance flux; không chọn candidate theo khoảng cách tới vector trong tài
liệu hoặc theo covariance nhỏ hơn.

Cả hai dùng cùng pixel/mask, renderer, neighbor/background span và offset
Gaia đã đóng băng. Renderer dùng WCS nguồn chính xác, ePSF QR3 zero-pad 16,
chuẩn hóa toàn lattice native theo pha trước mask, và Ω nguồn tính từ
celestial WCS (2/4 subdivisions, refinement diagnostic ≤1e−4). Đây là xấp xỉ
geometric center-Ω, không phải bằng chứng exact SAPM hoặc chuẩn màu. Nuisance
cũ gồm mặt phẳng và hàng xóm giữ vị trí/hình dạng; chỉ span tuyến tính được
tái sử dụng. IMAGE−ZODI−scalar giữ nguyên; hằng số fit hấp thụ scalar. Cờ
SOURCE được phép trong target mask; đơn vị và thứ tự pixel kiểm tường minh.

Control mới cũng thay WCS/normalization và có thể thay mask so với estimator
cũ. Vì vậy không gọi nó là replay byte-identical của phép đo 0.3/0.10 trước.

## Bảy nhánh đã định, đủ cả broad và strict

1. `independent`: flux riêng từng frame, không dùng tỷ số phổ.
2. `shared_r7_68_a0`: candidate chính, Cent 68 kênh, center R7, α=0.
3. `tilt_r7_68_a0`: thêm một nuisance độ nghiêng phổ chung mỗi epoch, pivot
   4,75 µm, scale 0,20 µm. Với hai frame và hai wavelength khác nhau, flux
   basis này có thể tương đương hoàn toàn nhánh independent; đó là sanity
   check đại số, không phải xác nhận thứ ba.
4. `shared_r7_68_am4`: cùng candidate nhưng α=−4.
5. `shared_r7_68_ap4`: cùng candidate nhưng α=+4.
6. `shared_qr2_68_a0`: lấy center từ CWAVE QR2 thay center R7.
7. `shared_r7_17_a0`: Cent 17 kênh thay 68.

PRISM là spectrum pipeline MAST riêng, không ghép G395M, scale Spitzer hay
deconvolve LSF. Response Cent được tịnh tiến từ center CSV đến center của
pixel gần anchor; không co giãn width hoặc tích phân response qua footprint
PSF. Channel map R7 dùng SKY trực tiếp, BC/BW dùng DEVICE nên D6 lật x riêng
hai map này. Mọi pixel map có header/provenance theo HDU, không lật toàn gói.

Quy ước giả định là photon-weighted Fν với reference
`Fν(λ)/Fν(λlocal)=(λ/λlocal)^α`; **chưa xác minh đây là quy ước calibration
SPHEREx**. Thiếu bất kỳ absolute response support nào thì từ chối chuẩn bị
nhánh; không ngoại suy hay bỏ frame để làm fit tốt. Tỷ số coefficient chia
giá trị cố định 0,0005 Jy cho cả hai epoch, chỉ đổi tham số hóa A, không đặt A
theo JWST. Chuẩn bị theo từng epoch; lỗi ở epoch này không chặn fit epoch kia.
Tỷ số cố định tại anchor; chưa đạo hàm response theo vị trí nguồn đang fit.

## Solver, mode và uncertainty

Năm khởi tạo: anchor và (±0,7;0)/(0;±0,7); chọn nghiệm solver thành công có
χ² nhỏ nhất. Profile tuyến tính bằng SVD có chuẩn hóa cột, không pinv che
rank. Huber threshold 2,5 dùng residual/error **gốc**, cập nhật whitening và
projection nuisance, tối đa 20 lượt. Sau ít nhất hai lượt, đòi đổi vị trí
≤1e−4 pixel và đổi max weight tiếp theo ≤1e−3. Không hội tụ giữ điểm/mẫu số
nhưng không vượt screening số học.

Chạy lại đủ năm start trên trọng số cuối cố định, không cập nhật IRLS và
không âm thầm thay point. Lưu các mode cách nhau >0,15 pixel, mode có χ² tốt
hơn point >1e−4 và các mode trong Δχ²≤5,991 của best. Ngưỡng này là heuristic
phát hiện cạnh tranh nghiệm, không có bảo đảm likelihood coverage.

Lưu GN và observed profile-H ở bước 0,002/0,004 pixel; H chỉ supported khi
PD/rank và đổi tương đối ≤5%. Không nhân reduced χ². Covariance là
**centroid-only có điều kiện** theo trọng số cuối và noise diagonal, không
có registration chung, uncertainty ePSF/SED/response/neighbor, biến thiên
nguồn hay calibration. Screening solver không phải scientific validation.
Khi cộng covariance hai epoch, giả định cross-epoch centroid covariance bằng
0 có điều kiện; đây không phải tổng ngân sách hoặc kiểm tra độc lập hai epoch.
Không clip amplitude âm hoặc diễn SNR fixed-position thành xác suất phát hiện.

## Mẫu số và giới hạn

Hai cấu hình × bảy nhánh × hai epoch = **28 attempt**. Checkpoint sau từng
epoch, giữ failure và mọi start/mode cùng native x/y, error, ePSF zone, mask
selection, provenance và Ω tại nghiệm. Lỗi chuẩn bị theo configuration/epoch
được lưu cho các attempt tương ứng, không thả frame. Lỗi hash/protocol/runtime
hoặc hợp đồng dữ liệu toàn bộ thì dừng toàn run. Báo toàn bộ vector và độ đổi so control
khi cả hai epoch có điểm; độ đổi là model sensitivity, không phải bias hay
accuracy. Không có truth độc lập để báo RMS/coverage từ một đối tượng.

Vẫn dùng một vị trí mỗi mùa, bỏ chuyển động/parallax trong khoảng vài ngày;
offset Gaia giữ cố định, không propagate covariance. Giả định phổ nguồn
2023 có thể sai cho 2025–2026; α sensitivity không bao trọn calibration,
variability hoặc LSF. Không có promotion/default switch dù candidate trông
tốt hơn. Bước tiếp theo cần controls thật/PSF khác, noise phù hợp, time model
và calibration riêng trước khi mở 30 trường mới.

```powershell
.venv/Scripts/python.exe -B -m unittest tests.test_linked_epoch_model tests.test_wise_linked_inputs -v
.venv/Scripts/python.exe -B -m scripts.run_wise_linked_study --design
# Commit toàn bộ source/test/protocol/design, rồi mới chạy:
.venv/Scripts/python.exe -B -m scripts.run_wise_linked_study --run --configurations broad --variants independent
.venv/Scripts/python.exe -B -m scripts.run_wise_linked_study --run
```

`--design` chỉ hash inputs, không tính coefficient/fit. `--run` kiểm design,
source/metadata khớp Git HEAD và raw hashes; không ghi đè study hoàn tất.
Runner giữ khóa OS trong suốt lệnh; process chết giải phóng khóa, file khóa
còn lại không tự là bằng chứng có job sống. Checkpoint ghi atomically, mỗi
attempt có checksum; resume kiểm cả runtime/package pin và checksum, không
trộn môi trường. Chỉ một runner ghi tại một thời điểm. Resume bỏ qua các attempt đã ghi kể cả failure, không rerun ca khó hoặc
đổi protocol sau xem point để làm đẹp kết quả. Raw output bị Git bỏ qua.
