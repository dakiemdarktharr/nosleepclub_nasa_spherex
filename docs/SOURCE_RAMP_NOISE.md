# Injection Poisson nguồn cho ramp lý tưởng

Module [source_ramp_noise.py](../scripts/source_ramp_noise.py) sinh **phần tín hiệu và shot noise của nguồn được thêm vào** cho mô hình up-the-ramp lý tưởng. Nó không sinh lại sky, read noise hay dark noise của ảnh gốc, không sửa ảnh/variance đầu vào và không xác nhận mô hình detector SPHEREx thực.

## Nguồn công thức và phép suy độc lập

Trong [source pipeline SPHEREx công khai của Caltech/IPAC](https://github.com/Caltech-IPAC/spherex-pipelines/blob/aa0ba446ee12971024fe13dc1c47387615bbe85e/py_src/spx_tasks/create_variance_map.py), snapshot commit `aa0ba446ee12971024fe13dc1c47387615bbe85e`, blob Git SHA-1 `c682a3c8574b16e0f092dd89266a0dbaeaad9b47`, nhánh nominal dùng:

```text
n = SURLIM - (SURDLY - 1)
t_intg = n * TSAMP
P(n) = (6/5) * (n² + 1)/(n² - 1)
Var(source rate) = P(n) * s / (n * TSAMP)
```

Đây là đối chiếu công thức ở snapshot được đọc, không khẳng định mọi version dữ liệu hoặc mọi pixel dùng xử lý nominal đó. [Explanatory Supplement](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf) mô tả variance map và các trường hợp overflow/transient được xử lý riêng.

Suy từ mô hình lý tưởng: lấy `n` mẫu điện tích không phá hủy tại `t_k=k*dt`, `k=0,…,n−1`. Tăng điện tích giữa các mẫu là `X_j ~ Poisson(s*dt)` độc lập với `j=1,…,n−1`; mẫu ban đầu là intercept và triệt khi fit slope OLS có intercept. Hệ số của từng increment trong slope là

```text
w_j = 6*j*(n-j) / [dt*n*(n²-1)]
slope − s = Σ_j w_j * (X_j − s*dt)
Var(slope) = s*dt*Σ_j w_j² = P(n)*s/(n*dt)
```

Vì `Σ w_j*dt=1`, phép trừ mean không thêm hoặc bớt signal kỳ vọng. Tính trực tiếp covariance tích lũy `Cov(Q_i,Q_j)=s*dt*min(i,j)` cho cùng kết quả: `P(2)=2`, `P(3)=1,5`, `P(75)=1,2004267425320057`. Mô phỏng dùng **Poisson nguyên** cho từng increment, không thay bằng Gaussian.

## API và timing

`inject_source_ramp(expected_source, gain, header, valid_mask, rng, *, gain_provenance, source_provenance=None, batch_pixels=4096)` nhận:

- `expected_source`: ảnh 2D Astropy `Quantity`, chuyển được sang `MJy/sr`, hữu hạn và không âm trên pixel hợp lệ.
- `gain`: scalar hoặc ảnh cùng shape Astropy `Quantity`, đơn vị có thể chuyển sang `(MJy/sr)/(electron/s)`, hữu hạn và dương trên pixel hợp lệ. Đây là **absolute physical gain**, không phải electronic gain e⁻/ADU. Caller phải xác minh gain map phù hợp detector, epoch, version, detector/sky orientation và phép xử lý của ảnh. Module không tự kiểm chứng sự phù hợp đó.
- `header`: bắt buộc `SURLIM`, `SURDLY` là integer, `TSAMP`, `XPOSURE` là giây dương hữu hạn. Duplicate key (kể cả khác chữ hoa/thường) hoặc thiếu key bị từ chối. `2 ≤ n ≤ 10000` là giới hạn triển khai. Header phải thỏa `XPOSURE ≈ (n−1)*TSAMP`, dung sai lớn hơn của 1e-4 giây và 1e-8 lần span. Nếu không, module từ chối thay vì chọn thời gian khác.
- `valid_mask`: ảnh boolean cùng shape. Chỉ pixel `True` được mô phỏng/kiểm giá trị. Pixel `False` trả NaN trong cả ba layer bổ sung; caller phải giữ nguyên ảnh/variance/flags của chúng. Mask phải loại trước các pixel không phù hợp mô hình nominal.
- `rng`: `numpy.random.Generator` được tạo tường minh. `gain_provenance` phải có chuỗi `source` không rỗng; caller có thể cung cấp URL, hash và version calibration. `source_provenance` ghi thông tin nguồn tổng hợp.

`XPOSURE` là **khoảng giữa mẫu đầu/cuối** trong mô hình này, `(n−1)*TSAMP`; `n*TSAMP` là quy ước `t_intg` trong công thức variance pipeline. Không thay một giá trị cho giá trị kia. Ví dụ header nominal `SURLIM=77`, `SURDLY=3`, `TSAMP=1,5349 s`: `n=75`, span `113,5826 s`, còn `t_intg=115,1175 s`.

Nếu `S` là intensity kỳ vọng MJy/sr và `g` là gain khớp `(MJy/sr)/(e⁻/s)`, rate nguồn là `s=S/g`; noise intensity là `g*(slope−s)`, `added_image=S+noise`, và `added_variance=P(n)*g*S/(n*dt)` theo `(MJy/sr)²`. Output gồm ba layer `added_image`, `source_noise`, `added_variance`, mask bản sao và provenance. Provenance lưu SHA-256 mảng nguồn/gain/mask theo dạng số chuẩn hóa, giá trị header/đơn vị, nguồn calibration do caller khai, RNG bit-generator/state trước và sau, batch size, công thức và source pipeline. Caller chịu trách nhiệm cung cấp version/URL/hash calibration chính xác; hash mảng không chứng minh calibration đúng vật lý.

Không tạo mảng `n × image`: scratch Poisson xử lý từng batch tối đa `batch_pixels`; bộ nhớ bổ sung tỷ lệ `O(image pixels + batch_pixels + n)`. Cùng input, seed, bit-generator và batch size cho output có thể tái lập; thay batch size có thể đổi thứ tự dùng RNG. Giới hạn batch là 1–1.000.000 pixel.

```python
import numpy as np
import astropy.units as u
from scripts import source_ramp_noise as srn

source = np.full((3, 3), 0.2) * (u.MJy / u.sr)
gain = 0.05 * ((u.MJy / u.sr) / (u.electron / u.s))
header = {'SURLIM': 77, 'SURDLY': 3, 'TSAMP': 1.5349, 'XPOSURE': 113.5826}
valid = np.ones((3, 3), dtype=bool)
addition = srn.inject_source_ramp(source, gain, header, valid, np.random.default_rng(123),
                                  gain_provenance={'source': 'synthetic example'},
                                  source_provenance={'source': 'synthetic model'})
# Người gọi cộng added_image và added_variance vào các pixel valid của ảnh/variance gốc.
```

## Giới hạn và kiểm tra

Nguồn bức xạ Poisson được giả định độc lập giữa pixel và khoảng lấy mẫu; OLS unweighted và gain tuyến tính, không có covariance do tái lấy mẫu. Các pixel partial-ramp, overflow, transient, nonlinearity, saturation, persistence, crosstalk, không chắc chắn PSF/gain hay các xử lý khác không được mô hình hóa; valid mask và metadata phải loại những trường hợp này. Không thể suy completeness, coverage, calibration hay phát hiện thiên văn từ primitive hoặc unit tests.

```powershell
.venv/Scripts/python.exe -m unittest tests.test_source_ramp_noise -v
```

Kiểm thử bao gồm covariance ramp OLS độc lập cho n=2/3/75, hỗ trợ Poisson rời rạc, mean/variance và cross-covariance thực nghiệm trên seed cố định với dung sai sáu sai số chuẩn, đơn vị và scaling, mask/zero, tính tái lập, và từ chối input/header không hợp lệ. Chỉ dùng primitive trong một nghiên cứu đã khóa source, gain và giao thức trước khi chạy; đây chưa phải nghiên cứu Monte Carlo trên ảnh thật.
