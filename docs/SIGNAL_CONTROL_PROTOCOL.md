# Đối chứng tín hiệu, nguồn chồng, template và pha native

Phiên bản `0.10.0-signal-controls.1`. Khóa mã, test, seed, danh sách lượt và
ngưỡng dưới đây trong Git trước khi tạo scene/nhiễu hoặc fit thí nghiệm.
Đây là phát triển có chủ đích trên dữ liệu đã mở, chưa phải validation bầu trời.

## Câu hỏi và miền dữ liệu

Đo bias vị trí/thông lượng và mức giữ tín hiệu của hai fitter đã có khi thay
template truth, pha dưới pixel và thông tin về nguồn chồng. Không học lại PSF,
đổi bộ giải, sửa gate cũ hay chọn mô hình từ kết quả này.

Chỉ dùng hình học hai sao training `5756942110218608640` và
`5756958431094222592` tại exposure cũ `2025W46_2A_0214_3`. Cả hai được chọn sau
gate cũ bị chặn; đây là hai stamp trong **một** exposure/trường đã chọn từ ảnh.
Không coi chúng là các trường độc lập. Pipeline xác minh parent protocol
`704e3ef`, journal/nguồn kế thừa và coefficient seal trước khi chuẩn bị input.
Ba artifact public của parent (overview, audit, archive đủ journal/checkpoint)
được ràng buộc hash và đối chiếu digest trước khi tạo design hoặc chạy.

Giữ nguyên các pixel đã chọn, mask, VARIANCE gốc, WCS và registration cũ.
Thay IMAGE bằng **scene tổng hợp**; không cộng vào ảnh nhiễu thật, không lấy
residual thật làm chân trị. Catalog neighbor gốc được thay bằng đúng nguồn
chồng kiểm soát; không âm thầm giữ sao thật trong mean tổng hợp.

Tâm mục tiêu native bằng floor(tâm Gaia đã đăng ký) cộng một trong bốn pha:
`(.25,.25), (.25,.75), (.75,.25), (.75,.75)`. Anchor tìm kiếm của fitter vẫn là
Gaia cũ cho mọi scene có nguồn, không biết vị trí được chèn. Riêng null dùng
anchor common chuyển từ native phase tương ứng; null không có source truth.
Nguồn chồng cách mục tiêu `(+1.5,0)`
native pixel, thông lượng bằng mục tiêu. Dùng WCS thuận/nghịch cùng offset
để chuyển tọa độ, kiểm roundtrip `1e-7` pixel. Bias/khoảng cách luôn đo bằng
**native pixel**, không nhân thang 6,15″ của lưới chung để giả làm native.

## Factorial đã khóa: 640 fit

| Phần | Phép nhân | Fit |
| --- | --- | ---: |
| Không nhiễu | 2 geometry × 2 truth × 4 pha × 3 cảnh × 2 flux × 2 fitter | 192 |
| Có nhiễu | 2 geometry × Gaussian truth × 2 pha × 3 cảnh × 1 flux × 16 draw × 2 fitter | 384 |
| Null | 2 geometry × 2 pha anchor × 8 draw × 2 fitter | 64 |

Truth gồm (1) ePSF nearest **gốc**, khớp mô hình để kiểm phần mềm — đây là
inverse crime, có thể có cánh âm; (2) Gaussian elip dương tích phân pixel,
σ=(.55,.70) native pixel, xoay 25°. Gaussian là họ toán học khác fitter,
không phải PSF SPHEREx đo độc lập. Hai nhánh fitter là nearest gốc và nearest
cộng đúng vector shape đã seal, áp dụng cho target và neighbor đang có.

Ba cảnh: `isolated` chỉ target; `modeled` có companion được fit tại tọa độ đúng;
`omitted` có cùng target+companion/ảnh/nhiễu như modeled nhưng bỏ cột companion
khỏi fitter. Cảnh omitted là stress sai mô hình, không phải mẫu để yêu cầu
fidelity khi mô hình cố ý thiếu nguồn. Nó không được chọn/bỏ sau khi xem kết quả.

Noiseless dùng 600 và 1.200 µJy; noisy chỉ Gaussian, 1.200 µJy, pha 0 và 3.
Null không có target hoặc companion; pha chỉ chỉ định anchor tương ứng, không
có tọa độ truth của một nguồn. Mọi fitter giữ target/neighbor flux có dấu, nền
plane, chín starts, ±2,5 common pixel và tối đa 20 vòng IRLS như code đã khóa.

## Chuẩn hóa, nền và nhiễu

Gaussian có mật độ chuẩn hóa trên toàn mặt phẳng, tích phân bằng Gauss–Legendre
12 và 24 điểm mỗi trục/pixel. Dùng kết quả 24, từ chối nếu L1 chênh quá
`1e-12+1e-10*selected_mass`. Không chuẩn hóa lại trên mask; lưu phần flux nằm
trong và ngoài tập pixel. Chuyển Jy sang MJy/sr bằng Ω riêng từng pixel.

Matched truth và fitter giữ nguyên quy ước Ω tại tâm nguồn của renderer cũ.
Lưu Ω tâm target/companion và khoảng min/max Ω(pixel)/Ω(tâm). Vì vậy, so hai
họ truth gồm cả khác biệt shape **và** quy ước solid-angle; không quy mọi sai
lệch cho PSF. Không sửa renderer cũ để tạo sự khớp giả. Nền mean cố định bằng
ba cột plane cũ nhân hệ số `[.04,.015,-.01]` MJy/sr.

Noisy/null cộng Gaussian độc lập theo VARIANCE quan sát gốc, không source
Poisson hoặc variance oracle. VARIANCE vốn phản ánh ảnh đã quan sát; đây chỉ
là mô hình conditional, không xác nhận noise detector, tương quan nền hay
thông lượng nguồn thực. Mỗi draw dùng PCG64/SeedSequence `[2026103102, draw]`
để tạo bank theo toàn shape exposure, thứ tự C. Cùng pixel vật lý và draw dùng
cùng Z ở hai stamp, mọi pha/cảnh/flux/fitter; null dùng tám bank đầu. Draws
độc lập có điều kiện, các nhánh/strata được ghép cặp và không độc lập nhau.

## Đại lượng và ngưỡng trước kết quả

Giữ mọi lượt chuẩn bị lỗi, fit lỗi, fit hoàn tất nhưng bị từ chối số học.
Mỗi stratum báo đủ planned/completed/supported, dx/dy có dấu, radial/RMS/P90/max,
Fhat/Ftrue và bias. Báo riêng all-completed và supported-completed; không dùng
mean có dấu để che bias triệt tiêu giữa các pha. MCSE của tỷ số flux chỉ mô tả
nhiễu Monte Carlo trên các draw hoàn tất, chưa xử lý missingness hoặc covariance
thiên văn. Cặp baseline/corrected báo đủ số cặp dự kiến và thiếu.

- **Noiseless sạch:** mọi **128 fit** isolated/modeled phải hoàn tất, được hỗ
  trợ số học, radial≤0,1 native pixel và Fhat/Ftrue∈[0,9;1,1]. Một ca sai vẫn
  làm guard chung trượt, không gộp với pha khác để xóa failure.
- **Noisy sạch:** mỗi trong **16 strata** geometry×pha×scene×fitter có 16 draw;
  ít nhất 15 phải đồng thời hoàn tất, được hỗ trợ, Fhat>0, radial≤0,5 native
  pixel và Fhat/Ftrue∈[0,5;1,5]. Đây là ngưỡng **mẫu quan sát**, chưa chứng nhận
  tỷ lệ quần thể. Lỗi/thiếu là không đạt trong mẫu số 16.
- **Giữ tín hiệu khi thêm correction:** đủ **64 cặp noiseless sạch** hoàn tất,
  không có numerical refusal mới, radial không tăng quá 0,02 native pixel và
  |Fhat/Ftrue−1| không tăng quá 0,02. Guard này không thay gate fidelity trên.
- Omitted báo đủ bias, nhầm sang companion và mức hỗ trợ/lỗi; không yêu cầu
  đạt fidelity của cảnh sạch hoặc chọn mô hình từ stress thuận lợi.
- Null chỉ báo flux có dấu và số fit đồng thời supported+flux dương với khoảng
  Clopper–Pearson. Không có radial truth, flux ratio, detection hoặc false-alarm
  rate đã hiệu chuẩn; không tái dùng ngưỡng nhận nguồn cũ cho PSF này.

Các budget là điều kiện phát triển cần thiết để phát hiện hỏng tín hiệu và
nhận nhầm nguồn, không phải yêu cầu NASA hoặc chứng nhận độ chính xác vật lý.
Khoảng binomial 95% hai phía tính riêng mỗi stratum cố định; không gộp strata
ghép cặp thành IID. Với N=16, ngay 16/16 có cận dưới≈0,794; 15/16≈0,698.
P(đạt≥15/16|p=.9)≈.515, nên pilot không đủ power chứng nhận 90% population
recovery. Null N=8 với zero outcome vẫn có cận trên≈.369. Công bố toàn bộ
strata và uncertainty, không chọn phần đạt rồi gọi là miền đã kiểm định.

## Isolation và công bố

Design ghi hash code/test/tài liệu, nguồn/raw đã ghim, gate cũ, seal và đúng
640 khóa. Commit/push trước chạy; hai shard theo geometry, yêu cầu BLAS/OMP một
luồng mỗi process (không phải phép đo số luồng thực). Journal giữ terminal
records bất biến và resume không thay kết quả. Assessment directory phải vắng
trước/sau. Mỗi fitter/nhánh companion được chuẩn bị lazy riêng; lỗi correction
hoặc companion không làm mất ca baseline/nguồn đơn không liên quan. Truth matched
chỉ phụ thuộc template gốc cần thiết, Gaussian không phụ thuộc model fitter.
Dù mọi guard mới đạt, **gate cũ vẫn trượt**; 252 ô dành riêng và
30 trường mới không được mở bởi study này. Chưa có model selection hoặc promotion.

Kiểm toán độc lập sẽ kiểm scene/seed/đơn vị, objective tại vị trí đã lưu và
gate/mẫu số trước công bố. UI phải ghi rõ ảnh tổng hợp, không gọi nguồn giả
là đo lại WISE 0855. Thí nghiệm tiếp theo cần protocol mới, nguồn dữ liệu độc
lập vật lý, đánh giá nền thật và covariance; không nới ngưỡng sau lần này.

Nguồn phương pháp: [Gaussian2D, Astropy](https://docs.astropy.org/en/stable/api/astropy.modeling.functional_models.Gaussian2D.html),
[quadrature, NumPy](https://numpy.org/doc/stable/reference/generated/numpy.polynomial.legendre.leggauss.html),
[exact binomial interval, SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html).
Code dùng phiên bản đã ghim trong requirements, không tự nâng package theo trang docs hiện hành.
