# Audit quy ước photometry SPHEREx: bằng chứng và giới hạn

Audit này chỉ đọc mã/tài liệu chính thức và header calibration; không fit ảnh,
không bơm nguồn và không thay pipeline đã khóa. Snapshot công khai được xem là
R6.4 commit `d31bc5a6666b4530c6e233c2484c586b4a598b24` và R6.5.5 commit
`aa0ba446ee12971024fe13dc1c47387615bbe85e`. Những snapshot này không chứng
minh nội dung của exact build nội bộ đã tạo từng sản phẩm QR2.

## Đơn vị và solid angle

[IRSA](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/)
mô tả IMAGE là độ sáng bề mặt MJy/sr, còn SAPM là solid angle theo arcsec²
cho từng pixel. Với một pixel đã có Ω đúng đơn vị và vị trí:

`flux_pixel[Jy] = IMAGE_pixel[MJy/sr] × 10^6 × Ω_pixel[sr]`.

Đây là đổi đơn vị cho flux density tích phân trên pixel, không tự suy ra tổng
flux nguồn riêng khỏi background, hàng xóm hay bandpass. Ví dụ thuần đơn vị,
nếu Ω = (6,15 arcsec)² thì Ω = 8,889963240650299×10⁻¹⁰ sr và
1 MJy/sr × Ω = 888,996324065 µJy. Đây là giá trị **minh họa**, không thay
SAPM thực tế. [Tutorial IRSA](https://caltech-ipac.github.io/irsa-tutorials/spherex-source-discovery-tool-demo/)
minh họa đổi từng pixel IMAGE bằng SAPM của từng detector.

Mã Tractor có một lựa chọn khác ở bước sau fit. Trong [R6.4](https://github.com/Caltech-IPAC/spherex-pipelines/blob/d31bc5a6666b4530c6e233c2484c586b4a598b24/py_src/spx_utils/photometry/tractor_utils.py#L363-L389)
và [R6.5.5](https://github.com/Caltech-IPAC/spherex-pipelines/blob/aa0ba446ee12971024fe13dc1c47387615bbe85e/py_src/spx_utils/photometry/tractor_utils.py#L363-L389),
`MJysr_to_uJy` nhân amplitude MJy/sr bằng SAPM **tại pixel gần vị trí nguồn**,
có chia `oversample²`; [forced photometry R6.4](https://github.com/Caltech-IPAC/spherex-pipelines/blob/d31bc5a6666b4530c6e233c2484c586b4a598b24/py_src/spx_tasks/perform_forced_photometry.py#L630-L638)
và [R6.5.5](https://github.com/Caltech-IPAC/spherex-pipelines/blob/aa0ba446ee12971024fe13dc1c47387615bbe85e/py_src/spx_tasks/perform_forced_photometry.py#L649-L657)
truyền oversample bằng 1. Code fit amplitude trong đơn vị ảnh với PSF native
chuẩn tổng 1; kết quả catalog là µJy. Đây là quy ước SAPM tại tâm của đoạn
code công khai, không phải chứng minh rằng pixelwise Ω trên footprint là hằng
số hoặc rằng một vị trí cắt bất kỳ được map đúng vào full detector.

Đọc bytes 0–65535 của [SAPM QR2 D6 ví dụ chính thức](https://irsa.ipac.caltech.edu/ibe/data/spherex/qr2/solid_angle_pixel_map/cal-sapm-v2-2025-164/6/solid_angle_pixel_map_D6_spx_cal-sapm-v2-2025-164.fits)
qua HTTP 206: IMAGE ghi `ARRAY=6`, `DETCOORD=sky`, `BUNIT=arcsec2`, kích
thước 2040×2040. SHA-256 **của byte-range**, không phải của cả FITS, là
`b153300308d25ec8ac1196a394f1fd5e7d316e812a3759db7e92a57b7785a705`.
[Mã tạo SAPM](https://github.com/Caltech-IPAC/spherex-pipelines/blob/d31bc5a6666b4530c6e233c2484c586b4a598b24/py_src/spx_tasks/update_field_distortion.py#L448-L454)
gán đơn vị arcsec² và orientation sky; code Tractor lấy `pix_map[y,x]`.
Điều này chỉ xác nhận sản phẩm ví dụ và snapshot, **chưa ràng buộc được phiên
bản SAPM đúng cho cả 31 ảnh WISE**. Với cutout phải xác minh header, detector,
provenance và ánh xạ WCS A sang tọa độ active integer trước; không đảo X thêm
chỉ vì detector D6. Không dùng quy tắc SAPM để suy orientation của HDU khác.
Kiểm tra HISTORY của các HDU trong 31 ảnh WISE hiện mở không tìm thấy UUID
SAPM: file ví dụ không thể được gán là calibration đúng cho chúng chỉ từ dữ
liệu này. Đặc biệt, R7 channel map có `DETCOORD=sky` còn HDU BC/BW có
`DETCOORD=DEVICE`; orientation phải được kiểm theo từng HDU và phiên bản.

## Gain và template PSF

[R6.4 apply calibration](https://github.com/Caltech-IPAC/spherex-pipelines/blob/d31bc5a6666b4530c6e233c2484c586b4a598b24/py_src/spx_tasks/apply_dark_flat_field_and_photo_calib.py#L157-L176)
trừ dark và nhân gain theo mảng, với gain có đơn vị
`(MJy/sr)/(electron/s)`; variance được đổi đơn vị bình phương. Vì IMAGE đã
được hiệu chuẩn, không nhân gain lần nữa khi chỉ đổi IMAGE sang Jy. Gain dùng
trong một mô hình source-shot-noise là vấn đề khác, cần đúng file/đơn vị và
protocol riêng.

[Tractor R6.4](https://github.com/Caltech-IPAC/spherex-pipelines/blob/d31bc5a6666b4530c6e233c2484c586b4a598b24/py_src/spx_utils/photometry/tractor_utils.py#L164-L222)
shift PSF oversampled, downsample bằng `INTER_AREA`, rồi chuẩn hóa tổng patch
native về 1; fit dùng `LinearPhotoCal(1)` và amplitude theo đơn vị ảnh. Đó là
code xử lý PSF của snapshot, không tự chứng minh rằng cùng thao tác là đúng
cho ePSF QR3. [Tutorial ePSF IRSA](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/)
viết rằng cần shift, downsample và normalize; ví dụ code cụ thể lại gọi
`ImagePSF.evaluate` tại tâm pixel native rồi chia tổng stamp. Không suy từ
phần prose rằng phải tích phân pixel một lần nữa trên một ePSF đã bao gồm
pixel response. Loại PSF, LSF, interpolation, phase và encircled energy phải
được xác định trước khi dùng.

Code local `motion_analysis.py` nhân ePSF thô với `oversampling²/sum` trước
spline và lấy mẫu tại tâm pixel; `continuous_epsf_model.py` giữ cùng chuẩn
thô rồi zero-pad. Hai thao tác này **không chứng minh** tổng ePSF native tại
mỗi phase bằng 1, cũng không chứng minh amplitude local là Jy. ePSF local là
sản phẩm QR3 D6, version header `7.0.0b6.post2+g6b3a1a7`, SHA-256
`52f85faeb93d67ed2020b68a628fc947c1f0b78cbf9282ca193ec6d588ac1a36`, dùng
với ảnh QR2; khác biệt giữa các release cần được đánh giá riêng.

Nếu một template native `p_i` **đã được chứng minh** là tỉ phần flux nguồn
với tổng 1 trên một miền support xác định trước, có thể viết hai công thức
điều kiện để thiết kế nghiên cứu:

* Theo quy ước nguồn điểm SAPM tại tâm của Tractor, `I_i[MJy/sr] = F[Jy] × p_i / (10^6 Ω_source[sr])`.
* Theo phép đổi solid angle từng pixel, `I_i[MJy/sr] = F[Jy] × p_i / (10^6 Ω_i[sr])`.

Hai công thức dùng giả định khác nhau; chưa so sánh hoặc chọn công thức cho
fit WISE. Không chuẩn hóa lại theo **chỉ các pixel còn sau mask**, vì như vậy
thay đổi ý nghĩa flux theo mask; phải khai báo support, phần PSF ngoài stamp
và sai số của nó. Nếu response thay đổi theo pixel trong footprint, một hệ số
màu vô hướng trên mỗi frame có thể không đủ. Với photon injection còn phải
đảm bảo kỳ vọng nguồn vật lý không âm, gain phù hợp và không cộng lại nhiễu
bầu trời/read noise.

Primitive mới `scripts/native_flux_template.py` triển khai duy nhất công thức
Tractor tại tâm ở trên: ePSF 33×33 được zero-pad 16 mẫu oversampled, spline
cubic, lấy mẫu trên toàn lattice native hữu hạn kể cả ngoài ảnh và chuẩn tổng
riêng cho từng phase trước khi áp mask. Nó yêu cầu Ω có đơn vị và provenance
do caller cung cấp; không đọc SAPM, WCS hay ảnh. Tổng suy biến bị từ chối,
bao gồm trường hợp toàn lattice chỉ còn roundoff. Pixel âm do wings hay spline
được giữ nguyên, không ép centroid và không cắt về zero. Chuẩn này chỉ định
nghĩa support mô hình hữu hạn; không khôi phục flux ngoài ePSF hay chứng minh
ePSF thực. Template có giá trị âm không phải kỳ vọng Poisson hợp lệ để inject;
điều đó cần mô hình nguồn vật lý riêng, không âm và được kiểm chứng.

## Phổ chuẩn và hiệu chỉnh màu

[Explanatory Supplement v1.3](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf)
mô tả hiệu chuẩn tuyệt đối QR2 dựa trên 11 sao CALSPEC, dự đoán phổ sao qua
bandpass từng vị trí và hiệu chỉnh màu zodiacal. [Code R6.4/R6.5.5](https://github.com/Caltech-IPAC/spherex-pipelines/blob/d31bc5a6666b4530c6e233c2484c586b4a598b24/py_src/spx_tasks/update_photometric_calibration.py#L117-L148)
tính trung bình rời rạc `sum(trans × spectrum)/sum(trans)` và tính tỉ lệ
bandpass của phổ zodiacal trên phổ sao, sau khi chuẩn hóa từng phổ tại mẫu
gần bước sóng quan sát. Phần `trans` đến từ `SPinst.Tabular_Bandpass`; ở đây
chưa xác minh được định nghĩa đo lường, lưới, đơn vị hay trọng số photon của
thư viện đó. Supplement trình bày hệ số zodiacal bằng tích phân phổ zodiacal
chuẩn hóa; code trình bày thêm mẫu số phổ sao. Không coi hai biểu thức là
đồng nhất nếu chưa xác minh các định nghĩa và bước còn lại.

Thêm một giới hạn quan trọng: [snapshot R6.4](https://github.com/Caltech-IPAC/spherex-pipelines/blob/d31bc5a6666b4530c6e233c2484c586b4a598b24/py_src/spx_tasks/estimate_abs_gain_matrix.py#L1507-L1516)
nhận `photo_calib` nhưng tại đoạn dựng gain dùng `ones / ArrayCalValues` và
chia `ff_est`. Điều này không đủ để tái dựng cách file gain QR2 thực tế được
tạo bởi build nội bộ trước đó, cũng không bác bỏ mô tả hiệu chuẩn phát hành
của supplement. Chưa có bằng chứng để chọn mặc định phổ chuẩn phẳng Fν hay
phẳng νFν, hoặc khẳng định quy ước `R(λ)/λ` của diagnostic local là calibration
SPHEREx. PRISM/G395M, R7 lab response và gain QR2 cũng chưa được ràng buộc
thành một forward model tuyệt đối.

Trước một phép fit flux liên kết, cần kiểm chứng riêng: SAPM đúng version và
orientation từng exposure; native ePSF và tổng theo subpixel trên support cố
định; spectral response/calibration convention và tỷ số màu cùng đơn vị của
nguồn; pixel-dependent response; covariance và các kiểm soát độc lập. Chỉ
phép đổi đơn vị là đã có cơ sở; coefficient nguồn tuyệt đối hiện chưa sẵn
sàng để công bố hoặc dùng làm scientific truth. Provenance mã và trạng thái
từng kết luận được liệt kê trong [photometric-convention.json](../web/data/external/photometric-convention.json).
