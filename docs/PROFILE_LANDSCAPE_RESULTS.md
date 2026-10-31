# Kết quả chẩn đoán profile tại trọng số cố định

Chẩn đoán giải thích thêm hai cảnh báo đa nghiệm của fit ePSF, nhưng **không
thay đổi gate hiệu chuẩn đã thất bại**. Trên lưới đã lấy mẫu, các vùng chi phí
thấp của hai trường hợp được chọn có liên thông tại những mức đã khai báo;
điều đó chưa chứng minh chỉ có một cực tiểu, cũng không chứng minh hai nghiệm
đã lưu là hai cực tiểu vật lý.

Nghiên cứu hậu nghiệm này giữ đủ **14 nguồn training**, hai exposure đã mở và
bốn tổ hợp ePSF/trọng số: **112 nhánh**, gồm 96 profile có kết quả số và 16
nhánh thiếu đầu vào từ hai nguồn × hai exposure × bốn tổ hợp. Hai nguồn thiếu
vẫn nằm trong mẫu số. Chưa mở 252 ô corrected assessment và 30 trường độc lập.

## Bối cảnh của hai trường hợp focus

Hai sao được chọn sau khi xem gate cũ, cùng tại exposure
`2025W46_2A_0214_3`. Cả hai chuyển từ một sang hai nhóm near-best theo phép
phân nhóm chín lần khởi tạo đã công bố. Với ePSF và trọng số đều đã hiệu chỉnh,
độ chênh `F = rᵀr` giữa nhóm thay thế và điểm fit đã lưu lần lượt là
**0,357866** và **2,293230**. Hai vị trí cách nhau **0,307305** và **0,549337
pixel chung**, tương ứng xấp xỉ **1,8899″** và **3,3784″** khi nhân thang lưới
danh nghĩa 6,15″/pixel. Đây là khoảng cách trên lưới chung, không phải xác nhận
có hai nguồn thiên văn.

Gate trước đó yêu cầu mọi ô có thông tin cũ còn được hỗ trợ số học. Hai ô này
thất bại do `multiple_near_best_modes`, nên assessment không được phép bắt đầu.
Trên 143 so sánh còn lại, sai khác tuyến tính có P90 **0,004593** và lớn nhất
**0,025339 pixel chung**, dưới các giới hạn tương ứng 0,02 và 0,05. Việc hai
giới hạn này đạt không xóa điều kiện hỗ trợ số học đã thất bại. Xem [gate đã
lưu](../web/data/shape-point-check/calibration-gate.json).

## Bốn tổ hợp ePSF và trọng số

Ký hiệu G/H là ePSF gốc/hiệu chỉnh; trọng số G/H là hai vector Huber cuối đã
lưu từ fit gốc/hiệu chỉnh. Bảng dùng cùng hai vị trí của fit hiệu chỉnh trong
mỗi hàng. `ΔF` là hiệu thay thế trừ điểm fit **trong chính hàng đó**; không dùng
các giá trị F ở những hàng có trọng số khác nhau như một kiểm định thống kê.

| Gaia DR3 source ID | ePSF | Trọng số | F điểm fit | F điểm thay thế | ΔF |
| --- | --- | --- | ---: | ---: | ---: |
| 5756942110218608640 | G | G | 127,316034 | 127,889512 | 0,573478 |
| 5756942110218608640 | G | H | 127,316034 | 127,889512 | 0,573478 |
| 5756942110218608640 | H | G | 127,647706 | 128,005572 | 0,357866 |
| 5756942110218608640 | H | H | 127,647706 | 128,005572 | 0,357866 |
| 5756958431094222592 | G | G | 145,850797 | 148,007466 | 2,156669 |
| 5756958431094222592 | G | H | 145,853635 | 148,010295 | 2,156660 |
| 5756958431094222592 | H | G | 145,890409 | 148,183648 | 2,293239 |
| 5756958431094222592 | H | H | 145,893245 | 148,186475 | 2,293230 |

Đối chiếu trực tiếp vector trọng số đã lưu, với “pixel đổi” nghĩa là hai số
floating-point khác nhau chính xác, không đặt ngưỡng sau khi xem:

| Nguồn | Exposure | Số pixel | Pixel có trọng số đổi | Max `|wG − wH|` |
| --- | --- | ---: | ---: | ---: |
| 5756942110218608640 | `2025W46_2A_0214_2` | 144 | 1 | 3,15682×10⁻⁷ |
| 5756942110218608640 | `2025W46_2A_0214_3` | 141 | 0 | 0 |
| 5756958431094222592 | `2025W46_2A_0214_2` | 138 | 0 | 0 |
| 5756958431094222592 | `2025W46_2A_0214_3` | 130 | 1 | 1,06818×10⁻⁴ |

Ở focus `_3` thứ nhất, hai vector trọng số giống hệt nên hai hàng chỉ khác
nhãn trọng số thực chất dùng cùng vector. Ở focus `_3` thứ hai, một trọng số
thay đổi nhỏ. Phép hoán đổi cho thấy độ nhạy của các chi phí tại hai vị trí
đã lưu; nó không xác định riêng Huber, ePSF hay bộ giải là nguyên nhân của
cảnh báo đa nghiệm.

## Gradient và độ cong tại hai vị trí đã lưu

Bảng sau dùng **ePSF hiệu chỉnh + trọng số hiệu chỉnh** tại exposure `_3`.
“Điểm fit” là vị trí corrected đã lưu; “thay thế” là near-best còn lại, không
phải một fit mới. Gradient là sai phân trực tiếp của `F`, đơn vị
`F/pixel chung`; hai số λ là eigenvalue tăng dần của Hessian sai phân trực tiếp,
đơn vị `F/(pixel chung)²`. Mỗi hàng giữ bước sai phân `h` theo pixel chung.

| Nguồn | Vị trí | h | Gradient `(x, y)` | Eigenvalue Hessian `(λ₁, λ₂)` |
| --- | --- | ---: | --- | --- |
| 5756942110218608640 | Điểm fit | 0,004 | (−0,001245; −0,001800) | (47,919409; 227,177855) |
| 5756942110218608640 | Điểm fit | 0,002 | (0,000218; −0,002493) | (47,916124; 227,191921) |
| 5756942110218608640 | Điểm fit | 0,001 | (0,000583; −0,002666) | (47,915303; 227,195440) |
| 5756942110218608640 | Thay thế | 0,004 | (0,003087; −0,008810) | (16,790480; 189,379502) |
| 5756942110218608640 | Thay thế | 0,002 | (0,004536; −0,007487) | (16,785640; 189,386218) |
| 5756942110218608640 | Thay thế | 0,001 | (0,004898; −0,007156) | (16,784429; 189,387897) |
| 5756958431094222592 | Điểm fit | 0,004 | (0,003402; −0,006286) | (118,277264; 139,890628) |
| 5756958431094222592 | Điểm fit | 0,002 | (0,001796; −0,002395) | (118,271325; 139,885419) |
| 5756958431094222592 | Điểm fit | 0,001 | (0,001394; −0,001422) | (118,269839; 139,884116) |
| 5756958431094222592 | Thay thế | 0,004 | (−0,009180; 0,006297) | (23,386575; 105,422728) |
| 5756958431094222592 | Thay thế | 0,002 | (−0,006606; 0,003126) | (23,376405; 105,424600) |
| 5756958431094222592 | Thay thế | 0,001 | (−0,005963; 0,002333) | (23,373861; 105,425068) |

Các gradient và eigenvalue này là mô tả tại các bước sai phân đã khóa; không
có ngưỡng stationarity được định trước, do đó bảng không kết luận điểm nào
“đạt stationarity”. Hessian đầy đủ cũng không đồng nhất với Gauss–Newton. Chẳng
hạn tại `h=0,002`, eigenvalue Gauss–Newton ở điểm thay thế của hai nguồn lần
lượt là `(99,624876; 179,548504)` và `(62,319367; 162,116370)` theo cùng đơn
vị độ cong. Không nghịch đảo các ma trận này để tạo covariance.

Để đối chiếu cả bốn tổ hợp, bảng dưới giữ cùng hai vị trí corrected và bước
`h=0,002`. `‖∇F‖∞` có đơn vị `F/pixel chung`; các eigenvalue có đơn vị
`F/(pixel chung)²`. Các bảng đầy đủ cho cả ba bước và mọi probe nằm trong tệp
bản ghi nén.

| Nguồn | ePSF/trọng số | Vị trí | `‖∇F‖∞` | `(λ₁, λ₂)` Hessian |
| --- | --- | --- | ---: | --- |
| 5756942110218608640 | G/G | Điểm fit | 0,615427 | (64,819006; 228,889420) |
| 5756942110218608640 | G/G | Thay thế | 0,652579 | (14,928862; 184,525387) |
| 5756942110218608640 | G/H | Điểm fit | 0,615427 | (64,819006; 228,889420) |
| 5756942110218608640 | G/H | Thay thế | 0,652579 | (14,928862; 184,525387) |
| 5756942110218608640 | H/G | Điểm fit | 0,002493 | (47,916124; 227,191921) |
| 5756942110218608640 | H/G | Thay thế | 0,007487 | (16,785640; 189,386218) |
| 5756942110218608640 | H/H | Điểm fit | 0,002493 | (47,916124; 227,191921) |
| 5756942110218608640 | H/H | Thay thế | 0,007487 | (16,785640; 189,386218) |
| 5756958431094222592 | G/G | Điểm fit | 1,005548 | (131,762814; 139,481527) |
| 5756958431094222592 | G/G | Thay thế | 1,809880 | (28,012712; 122,967736) |
| 5756958431094222592 | G/H | Điểm fit | 1,005466 | (131,761912; 139,481131) |
| 5756958431094222592 | G/H | Thay thế | 1,809848 | (28,013368; 122,967760) |
| 5756958431094222592 | H/G | Điểm fit | 0,002499 | (118,272802; 139,885622) |
| 5756958431094222592 | H/G | Thay thế | 0,006649 | (23,375360; 105,424538) |
| 5756958431094222592 | H/H | Điểm fit | 0,002395 | (118,271325; 139,885419) |
| 5756958431094222592 | H/H | Thay thế | 0,006606 | (23,376405; 105,424600) |

Ở cả tám nhánh focus `_3`, lưới toàn miền 51×51 cho một thành phần liên thông
được lấy mẫu theo cả 4 và 8 láng giềng tại từng mức ΔF 0,1; 1; 2,3; 5,991,
tính từ minimum **trên lưới của chính nhánh đó**. Các mức không phải vùng tin
cậy. Một lưới hữu hạn có thể bỏ sót cấu trúc hẹp hoặc đường nối; số thành phần
không chứng minh số cực tiểu trong không gian liên tục.

## Kiểm toán và sản phẩm

Kiểm toán độc lập đã xác nhận đủ 112 checkpoint: **96 verified, 16
verified-unavailable**, không có mismatch hay study failure chưa kiểm chứng.
Các phép đối chiếu gồm **2.760 nút** được chọn theo chỉ số định trước, **192
probe tại vị trí fit đã lưu × 3 bước**, **480** lần replay hàm mục tiêu cùng
họ, **1.916** probe và nguồn gốc vị trí, cùng **40** lưới cục bộ focus. Mọi
ô thiếu được giữ rõ trạng thái. Sai khác tuyệt đối lớn nhất giữa WLS độc lập
và kết quả lưu là **1,364×10⁻¹²** cho chi phí lưới, **2,274×10⁻⁷** cho
Hessian chi phí, **1,844×10⁻⁹** cho Gauss–Newton và **1,137×10⁻¹³** cho chi phí
replay cùng họ. Đây là kiểm toán tính toán, không phải kiểm định accuracy.

Nguồn và dấu vết chính:

- [Protocol đã khóa](PROFILE_LANDSCAPE_PROTOCOL.md), commit
  `704e3efc806dddef7906b032ba917745f80442a1`; SHA-256 design
  `6896060318db83a09d9b917f2ced0d4b5f930116d2cbdef2b046c22440b4ef56`.
- [Tổng quan](../web/data/profile-landscape/overview.json) và [biên nhận kiểm
  toán](../web/data/profile-landscape/independent-audit.json); digest journal
  `fe1105b90c176412e22b837e13c6b7573ea1d9f3ace4e3dc7723648a4a2bb270`, checksum
  nội dung biên nhận `35156d08b0f8198e28eb6e01aff14e73a7749f7f9d07bf47eab3712818964ec3`.
- Mã kiểm toán [audit_profile_landscape.py](../scripts/audit_profile_landscape.py),
  SHA-256 `90eaa6f825a91526bfe3ed049349e40d4d813f1b778d6b4e80b42f85d037e24e`;
  mã xuất bản [publish_profile_landscape.py](../scripts/publish_profile_landscape.py),
  SHA-256 `d3fb8ef80ed49ccb7af6d0dd68fd10f5e9c1d60571748f00b811f9265c4a77ac`.
- [112 bản ghi profile, 112 checkpoint kiểm toán và hai header nén](../web/data/profile-landscape/records.json.gz):
  **3.885.257 byte** (khoảng 3,885 MB thập phân), SHA-256
  `5e0c5798333a0533dd495d73131e2830ecf45b2a502b55c95ac87859877b91c4`.
- Bốn hình: nguồn `5756942110218608640` tại [exposure _2](../web/data/profile-landscape/profile-5756942110218608640-2025W46_2A_0214_2.png)
  và [exposure _3](../web/data/profile-landscape/profile-5756942110218608640-2025W46_2A_0214_3.png);
  nguồn `5756958431094222592` tại [exposure _2](../web/data/profile-landscape/profile-5756958431094222592-2025W46_2A_0214_2.png)
  và [exposure _3](../web/data/profile-landscape/profile-5756958431094222592-2025W46_2A_0214_3.png).
  Màu hình được chặn ở ΔF=6 chỉ để hiển thị; các chi phí gốc nằm trong tệp nén.
- [Môi trường hình](../web/data/profile-landscape/figure-environment.json)
  ghi phiên bản package, hash font DejaVu và hash bốn PNG qua kiểm tra sau khi
  render. [Dependency vẽ](../requirements-figures.txt) được tách khỏi runtime
  Vercel. Đây chưa phải chứng nhận tái tạo byte trên nền tảng sạch khác.

Các hình là chẩn đoán profile hậu nghiệm trên cohort đã chọn từ ảnh. Trọng số,
registration và tọa độ láng giềng được giữ cố định có điều kiện; chưa có chân
trị PSF vật lý độc lập, covariance tổng đã hiệu chuẩn hay xác nhận nguồn. Tám
nhánh cho mỗi nguồn thiếu đầu vào không trở thành kết quả âm. Mẫu focus được
chọn sau khi xem gate, và cả lưới lẫn sai phân đều hữu hạn.

## Mốc tiếp theo đề xuất

Trước khi dùng dữ liệu deferred, khóa một protocol **kiểm chứng signal,
blend, template và pha native** bằng các phép chèn tín hiệu độc lập trên hình
học native đã định. Mỗi phép chèn cần có chân trị vị trí/thông lượng, PSF và
láng giềng được định danh, nguồn nhiễu và mask được mô tả, cùng toàn bộ lần
thử và thất bại được giữ lại. Các trường hợp phải bao gồm pha dưới pixel, độ
sáng, tách blend và sai khác họ template được khai báo trước.

Tiêu chí hoàn tất là: tái hiện được các phép chèn từ seed và provenance đã
khóa; vượt các gate **giữ tín hiệu** và **đúng danh tính mô hình/nguồn** được
định trước trên toàn bộ mẫu số; báo cáo sai lệch vị trí và thông lượng cùng
thất bại theo từng điều kiện; và chứng minh pipeline từ chối trường hợp không
hỗ trợ thay vì xóa chúng. Ngưỡng số cần được xác lập trong protocol trước khi
chạy. Có thể so sánh hai hướng trong protocol mới: giữ nguyên ePSF với
screening đa nghiệm được kiểm định riêng, hoặc dùng template thay thế độc lập
và kiểm định signal preservation. Không nới gate cũ, chọn mô hình sau khi xem
kết quả, hoặc hứa sai lệch giảm trước khi đo.

Nhánh telemetry chỉ bổ sung log phân loại, không thêm retry: 41 kiểm thử offline
đã được báo cáo đạt; bằng chứng cũ chưa xác định nguyên nhân gốc của hai lỗi
502. Bộ kiểm thử local đầy đủ được báo cáo gồm **564 trường hợp: 558 đạt, 6
bỏ qua do MongoDB**. Kiểm tra trình duyệt local xác nhận đổi sao/ảnh, mở bảng
bằng Enter và cuộn ngang trong viewport 390 px, không tràn ngang toàn trang.
Biên nhận CI và production được ghi riêng trong PR phát hành; test count hay
trạng thái cloud READY không thay thế các gate khoa học và recovery/SLO.
