# Khóa thử nghiệm nguồn chồng, nền và ePSF trên dữ liệu đã mở

Đây là bước development sau study `cfb9d6a`; **không mở trường mới** hoặc
thay phép đo WISE mặc định. Study trước có hai nghiệm cạnh tranh ở epoch sau
strict. Replay chỉ mô tả quan hệ với span nuisance, chưa chỉ ra nguyên nhân.
Thử nghiệm mới thay từng yếu tố trên cùng pixel để đo sự nhạy và đánh giá
constraint bằng đối chứng có truth tổng hợp. Không chọn model theo độ gần
vector tài liệu hoặc ellipse nhỏ hơn.

## Câu hỏi và factorial định trước

Tái sử dụng 20 cutout QR2 trường rộng, offset Gaia, SOURCE-only mask, error,
anchor sky-grid (31,5;31,5), catalog/ID và thứ tự neighbor đã mở. Broad có 10
ảnh/epoch, strict có hai và là tập con của broad. Mỗi frame có target flux
**signed, tự do**, nền và flux neighbor riêng; không dùng PRISM hay reference
color để buộc target trong thử nghiệm này.

Ba yếu tố, đủ 2×2×2 = tám nhánh, cho hai epoch và hai bộ ảnh: **32 attempt**.

1. Nền plane `[1,x,y]` hoặc quadratic `[1,x,y,x²,xy,y²]`, với x/y native đã
   chia bán kính 6 pixel như sample cũ. “Plane” gồm gradient, không phải chỉ
   hằng số. Dữ liệu giữ IMAGE−ZODI−scalar; hằng số fit hấp thụ scalar, chưa
   kiểm tra bias do mô hình ZODI bị trừ.
2. ePSF spatial nearest hoặc bilinear từ bốn bảng thô, chuẩn hóa riêng từng
   bảng rồi trộn. Shape target giữ tại anchor, neighbor tại vị trí catalog;
   không đạo hàm shape theo vị trí fit. Ngoài grid center thì clamp cạnh và
   ghi flag; không giả lập một calibration mới.
3. Flux neighbor ký hiệu theo ID và đơn vị Jy, cho phép có dấu hoặc ràng
   buộc không âm bằng NNLS. **Chỉ constraint trên các cột vật lý**, không trên
   các cột SVD đã trộn nguồn và nền; target/nền vẫn signed. So sánh chính là
   `plane_nearest_free` với `plane_nearest_nonnegative`.

Neighbor mới được dựng lại bằng native renderer có đơn vị, WCS nguồn chính
xác và normalization toàn lattice trước mask. Vì vậy nhánh free mới là
bridge control, không phải replay byte-identical phép fit cũ. Chỉ contrast
nonnegative/free trong cùng shape/nền tách được tác động của constraint.

Mọi nguồn dùng ePSF SKY 5×, 33×33 có dấu từ calibration đã hash. Active WCS A
được kiểm qua metadata QR2 D6, không thêm flip D6. Ω nguồn là geometric WCS
area; chưa có exact SAPM binding. Không áp correction từ moment centroid của
bảng ePSF. [IRSA hướng dẫn dùng ePSF mới cho QR2 cũ](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/);
khuyến nghị đó không kiểm chứng residual/bias của WISE hoặc phép nội suy mới
ở đây.

## Solver, active constraints và lý do từ chối

Profile từng frame bằng SVD chuẩn hóa cột cho phần tự do, rồi NNLS cho phần
neighbor không âm sau projection. Kiểm rank/condition toàn design (cut
relative singular value 1e−10), KKT scaled 1e−8; không bỏ cột yếu, dùng pinv
hay clip một nghiệm âm đã fit xong. Lưu đủ hệ số theo ID, residual gốc/error,
weights, active mask và optimality diagnostics.

Chín start Cartesian offset −1,5/0/+1,5 pixel trong bounds anchor±2,5.
Chọn nghiệm solver thành công có chi phí thấp nhất; giữ failure từng start.
Huber 2,5 dựa trên residual/error gốc, tối đa 20 cập nhật. Sau ít nhất hai
lượt, đòi next max weight change≤0,001 và position max change≤1e−4 pixel.
Sau đó audit lại chín start trên weights cuối cố định, giữ điểm đã chọn.
Cluster các nghiệm cách >0,15 pixel, ghi các mode có Δχ²≤5,991 và bất kỳ
nghiệm tốt hơn point >1e−4. Các ngưỡng là heuristic, chưa có likelihood
coverage cho robust constrained fit. Multi-mode, better point, boundary,
rank, nonconvergence và final-start failure là numerical refusals.

Không trả covariance, ellipse, SNR hoặc detection probability. Các active
constraints làm suy luận ở biên khác với least squares tự do; không sử dụng
inverse curvature để tuyên bố đã hiệu chuẩn. Một vị trí mỗi epoch vẫn bỏ
chuyển động/parallax trong mùa và uncertainty căn chỉnh chung. Những việc
này còn cần giải quyết trước khoa học ngoài mẫu.

## Đối chứng PSF độc lập và source Poisson có điều kiện

Chỉ dùng geometry của strict, bốn frame đã mở. Hai flux target 300/600 µJy ×
hai background truth plane/quadratic × **16 noise draws/case**, cho 64 scene
độc lập theo RNG trên cùng geometry. Hai nhánh chính và hai epoch tạo
**256 attempt control**, tổng study **288 attempt**. Draw trên cùng geometry
không phải các trường trời độc lập.

Truth target trước (31,73;31,31), displacement sau (+0,55;+0,08) sky pixel.
Target Gaussian có σ native (0,55;0,70), neighbor (0,70;0,60); flux neighbor
theo thứ tự cố định là 150/(1+i) µJy. Tích phân Gaussian theo ô pixel bằng
CDF, không dùng ePSF hoặc chuẩn hóa theo cửa sổ. Pixel Ω riêng cho mỗi pixel
và flux thiếu ngoài cửa sổ được lưu. Đây là một family PSF synthetic khác
fitter, không phải measured instrument PSF hoặc spectrum WISE.

Background deterministic có hệ số plane MJy/sr (0,04;0,015;−0,01). Case
quadratic thêm (0,025;0,020;−0,015) cho x²/xy/y². Noise nền Gaussian độc lập
dùng VARIANCE gốc làm thang error; **không cộng lại noise trên ảnh đã nhiễu**
và không gọi đây là injection trên sky thật. VARIANCE đó vẫn có điều kiện
theo processing gốc và có thể đã gồm photon noise của các nguồn thật cùng
các thành phần xử lý. Vì vậy không chứng minh thang Gaussian đó chỉ gồm
sky/read noise, hay tổng phương sai sau cộng synthetic-source Poisson không
trùng một thành phần source nào về diễn giải vật lý. Đây là empirical noise
scale/oracle stress control; chưa tách sạch ngân sách noise detector/covariance.

Toàn bộ positive scene (target + neighbors) có ideal source Poisson ramp từ
module đã kiểm OLS, gain thực cùng UUID/hash, active pixel mapping và timing
header nominal. Gain/history/unit được kiểm; pixel gain xấu làm failure cả
epoch, không bị loại để cứu mẫu. Orientation dựa trên public R6, chưa chứng
minh đúng private patch; Poisson/background/noise vẫn là giả định control.
Fitter dùng **oracle** `sqrt(original variance + known expected-source
variance)`, không giả là observed-data uncertainty estimator.

RNG là PCG64/SeedSequence `[20261031,case_index,draw,epoch_index,frame_index]`;
hai nhánh nhận đúng cùng data/error. Resume phải khớp realization hash với
nhánh đã lưu. Lưu expected/noise/variance/gain/Ω, RNG states, input hashes và
mọi attempt, kể cả preparation/fit failure.

Đầu ra định trước: counts trên tất cả lượt; vector sai lệch/RMS của mọi cặp
completed, cặp completed chung và cặp numerical-supported chung; số flux
target âm, bound neighbor, mode và failure. Bốn case giữ riêng, không pool
để giấu case khó. Đây là pilot 16 draws/case, không đủ miền/trường để chọn
model production hoặc hiệu chuẩn coverage; không báo coverage khi không có
covariance. Không promotion dù một contrast trông tốt hơn.

## Khóa và tái lập

Design hash rules/source/tests/old opened products/raw inputs, cả gain/lookup
mới được dùng cho control. Inventory kế thừa cả archive phổ từ study trước
để audit lineage; các archive đó không tạo flux constraint trong study mới.
Commit toàn bộ trước bất kỳ phép fit thật hoặc draw control. Checkpoint có
checksum từng record, khóa OS, atomic write, runtime/package pins; resume
không chạy lại terminal failure hoặc ghi đè study hoàn tất. Không sửa source
đã khóa để cứu ca sau khi xem dữ liệu.

CLI mới yêu cầu các biến OpenBLAS/OMP/MKL/BLIS/vecLib thread bằng 1 trước
import NumPy/Astropy, chỉ trong process CLI; không đổi môi trường của caller
khi import như library. Giá trị yêu cầu được lưu trong runtime; đây chưa phải
phép kiểm độc lập số thread mà mọi backend thật sử dụng.

```powershell
.venv/Scripts/python.exe -B -m unittest tests.test_constrained_linear_profile tests.test_neighbor_epoch_model tests.test_neighbor_intervention_inputs tests.test_independent_scene_control tests.test_neighbor_intervention_study -v
.venv/Scripts/python.exe -B -m scripts.run_neighbor_intervention --design
# Commit source/tests/protocol/design trước:
.venv/Scripts/python.exe -B -m scripts.run_neighbor_intervention --run --sections real
.venv/Scripts/python.exe -B -m scripts.run_neighbor_intervention --run --sections controls
```

Đây chưa phải protocol cho 12 calibration / 12 validation / 6 final holdout.
Sau kết quả cần xác định vùng suy biến/abstention, kiểm PSF sao thật và time
model, rồi khóa evaluator, power, absolute gate và overlap trước mở 30 trường.
