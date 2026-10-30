# Nguồn chồng, nền và ePSF: kết quả chưa cho phép chọn mô hình

**288/288 epoch-fit hoàn tất; đối chứng không chứng minh cải thiện nhất quán.**
Ràng buộc flux hàng xóm không âm giảm RMS ở ba trong bốn ca synthetic nhưng
làm ca nguồn mờ trên nền cong xấu hơn. Một draw qua toàn bộ sàng lọc số vẫn
lệch **16,8″** so truth. Không đổi phép đo WISE, cấp covariance hiệu chuẩn,
chọn model production hoặc mở 30 trường dành riêng.

[Mở bảng và biểu đồ](https://nosleepclub-nasa-spherex.vercel.app/#neighbor-intervention)
· [Protocol](NEIGHBOR_INTERVENTION_PROTOCOL.md)
· [Design](../web/data/neighbor-intervention/design.json)
· [Tóm tắt 53 KB](../web/data/neighbor-intervention/overview.json).

## Cấu hình và phạm vi đã khóa

Study khóa tại `32573ad53d6cafa47ef2cc79b0971b22bd3203bd`, trước mọi phép fit
hoặc draw mới của study. Design SHA-256:
`119f7d628c716f7e372778bf9983ecbfc5c256c02b9b32aebc7972de819f57d6`.
Toàn bộ ảnh, Gaia offset và catalog là dữ liệu WISE đã mở trong development.

- **32 fit thật:** hai bộ broad/strict × tám tổ hợp nền plane/bậc hai,
  ePSF nearest/bilinear và flux hàng xóm có dấu/không âm × hai epoch.
  Broad có 10 ảnh mỗi epoch; strict có hai và nằm trong broad.
- Target flux và nền luôn có dấu; chỉ cột vật lý theo ID của hàng xóm bị
  NNLS constraint. Vị trí hàng xóm/căn chỉnh giữ cố định. Nội suy ePSF là
  nội suy không gian, chưa phải học hình PSF từ sao thật.
- **256 fit control:** bốn ca nền plane/bậc hai × target 300/600 µJy,
  mỗi ca 16 draw, hai nhánh plane/nearest và hai epoch. Gaussian truth được
  tích phân theo pixel, khác family ePSF fitter; cùng realization giữa nhánh.
  Tất cả chỉ dùng một geometry strict đã mở, không phải 64 trường độc lập.

Renderer hàng xóm được dựng lại có đơn vị và native WCS; nhánh free mới là
bridge control, không replay byte-identical mô hình cũ. So NNLS/free trong
cùng nền/ePSF mới cô lập được constraint. Thử nghiệm này không dùng phổ để
buộc target flux; độ trải của nó không thể dùng để tuyên bố tốt hơn study
linked-flux có bảy giả định phổ khác.

## Ảnh thật: thay giả định vẫn làm vector đổi

Các giá trị dưới đây là thành phần vector giữa hai epoch, đơn vị giây cung.
Đây là độ nhạy mô hình trên dữ liệu đã mở, chưa là sai lệch so vị trí đúng.

| Nền / ePSF / hàng xóm | Broad Đông / Bắc (″) | Strict Đông / Bắc (″) | Strict, cả hai epoch qua số học |
|---|---:|---:|---|
| Plane / nearest / có dấu | −3,066 / +0,088 | −2,534 / +0,500 | Không: đa nghiệm ở sau |
| Plane / nearest / không âm | −3,028 / +0,017 | −2,207 / +0,176 | Có |
| Plane / bilinear / có dấu | −3,218 / +0,220 | −2,545 / +0,491 | Không: đa nghiệm ở sau |
| Plane / bilinear / không âm | −3,134 / +0,087 | −2,276 / +0,174 | Có |
| Bậc hai / nearest / có dấu | −3,197 / +0,174 | −3,051 / +0,936 | Không: đa nghiệm ở sau |
| Bậc hai / nearest / không âm | −3,150 / +0,076 | −2,667 / +0,587 | Có |
| Bậc hai / bilinear / có dấu | −3,350 / +0,310 | −3,083 / +0,933 | Không: đa nghiệm ở sau |
| Bậc hai / bilinear / không âm | −3,261 / +0,155 | −2,746 / +0,598 | Có |

Broad có **8/8** cặp qua kiểm tra số; strict **4/8**. Bốn nhánh strict free
cùng có nhiều near-best mode ở after. Constraint thay vị trí và cấu trúc
mode; chưa chứng minh mode còn lại là nguồn đúng. Contrast chính
plane/nearest NNLS−free đổi vector **0,080076″** broad, **0,460337″** strict.
Khoảng cách lớn nhất giữa mọi vector hoàn tất là **0,434865″** broad và
**1,158115″** strict. Giữ cả vector bị từ chối khi tính độ trải.

## Control độc lập: cải thiện không nhất quán, sai lệch lớn

Mọi ca có 16/16 cặp fit được ở cả hai nhánh. Không bỏ outlier hoặc nghiệm
bị sàng lọc khỏi bảng này. RMS/P90 là lỗi vector so displacement Gaussian
truth; thứ tự hai số luôn **free → NNLS**.

| Truth tổng hợp | Cặp fit được mỗi nhánh | RMS (″) | P90 (″) | Cặp cùng qua sàng lọc số /16 |
|---|---:|---:|---:|---:|
| Plane · 300 µJy | 16/16 | 14,535 → 14,263 | 21,357 → 20,766 | 1/16 |
| Plane · 600 µJy | 16/16 | 3,661 → 3,358 | 5,082 → 4,641 | 7/16 |
| Bậc hai · 300 µJy | 16/16 | 12,742 → 13,741 | 19,927 → 19,932 | 0/16 |
| Bậc hai · 600 µJy | 16/16 | 2,511 → 2,189 | 3,712 → 3,098 | 8/16 |

Ca bậc hai/300 µJy có RMS NNLS tăng **0,999050″**. Lọc chỉ những draw được
cả hai nhánh hỗ trợ cũng không tạo bằng chứng nhất quán:

| Truth tổng hợp | Mẫu chung /16 | RMS free → NNLS (″) | P90 free → NNLS (″) |
|---|---:|---:|---:|
| Plane · 300 µJy | 1/16 | 16,780 → 16,769 | 16,780 → 16,769 |
| Plane · 600 µJy | 7/16 | 2,406 → 2,196 | 3,796 → 3,254 |
| Bậc hai · 300 µJy | 0/16 | Không xác định | Không xác định |
| Bậc hai · 600 µJy | 8/16 | 2,081 → 2,124 | 2,775 → 2,830 |

P90 dùng percentile nội suy tuyến tính; với n=1 nó là chính một quan sát,
không phải ước lượng tail đáng tin cậy. Không pool bốn ca hoặc dùng bộ lọc
đẹp hơn để chọn model. Flux target âm vẫn giữ: số frame âm free/NNLS lần
lượt **9/11, 2/4, 13/15, 0/0**, trên 64 frame mỗi nhánh mỗi ca. Số hệ số
neighbor bị bound về 0 ở NNLS là **43, 48, 27, 22**; một frame có thể có
nhiều hệ số, nên đây không phải số draw hoặc số nguồn được xác nhận.

### Ví dụ hậu kiểm: numerical support vẫn có thể sai nghiêm trọng

Draw ID **8** (đánh số từ 0) của plane/300 µJy là draw duy nhất cùng qua
sàng lọc số. Lỗi vector free **16,780201″**, NNLS **16,768697″**. Cả hai
epoch hội tụ IRLS, không chạm boundary, một near-best mode và không có mode
tốt hơn point theo audit. Frame thứ hai ở after có target flux âm khoảng
−203,3 µJy ở cả hai nhánh.

Đây là chẩn đoán hậu kiểm, chưa xác định nguyên nhân. Không sửa gate, bỏ
draw, ép target dương hoặc đổi truth để cứu kết quả. Rank/hội tụ/đơn mode
không kiểm chứng sự hiện diện hay nhận diện đúng nguồn. Cần phép thử null,
nguồn thật và tiêu chí sai lệch tuyệt đối trước khi đánh giá một gate mới.

## Kiểm toán và tái lập

Raw đã đóng có **87.581.267 byte**, SHA-256
`428e070cd75b078875420653745e4be2dacce7da95342033ae8f6ab923ce520a`,
ở `data/raw/benchmark/neighbor-intervention.json` được ignore. Không chạy
lại study hoàn tất để thay kết quả. Publisher và test khóa tại `055053f`
trước khi đọc raw hoàn tất; source khoa học của `32573ad` không thay đổi.

Publisher kiểm đủ 288 key/checksum, source/design/input/runtime/Git commit,
cùng pixel/error/design giữa hai nhánh, realization hash và seed, đơn vị,
mask/order, native renderer và KKT tại điểm đã lưu. Có **704** kiểm toán
linear-frame; max scaled KKT violation **1,288×10⁻¹³**. BVLS độc lập replay
chi phí tại **2.583** successful final starts, max chênh χ²
**1,592×10⁻¹²**. Chín final-start failure được giữ, không đổi thành success.
Đây là kiểm tính toán, chưa là nghiệm thu khoa học.

| Artifact public | Byte | SHA-256 |
|---|---:|---|
| [32 fit thật và audit](../web/data/neighbor-intervention/development.json) | 19.232.175 | `0d1c2781f30572165261309bfbb0447da1876bc3f77a13533c4b71e5e1f02a85` |
| [64 draw, hai nhánh và audit](../web/data/neighbor-intervention/controls.json) | 5.179.378 | `59e6ddc47196d328723c112252a725f8d2397f8637546dc321def4a47e1317bf` |
| [Overview dùng trên web](../web/data/neighbor-intervention/overview.json) | 53.184 | `558f03c0da2b9c108a2cb2f97e85c7c901ba01157a4bf662a7f41daedfdd41d6` |

Web chỉ tự tải overview khi mở mục chuyên sâu; file lớn là tải chủ động.
[Figure manifest](../web/data/neighbor-intervention/figures.json) lưu nguồn,
tọa độ mọi điểm, đơn vị, font, package và hash SVG. Biểu đồ giữ cả các cặp
không được hỗ trợ, không vẽ ellipse hoặc cắt các tail khỏi trục.

```powershell
.venv/Scripts/python.exe -B -m scripts.publish_neighbor_intervention --raw-sha256 428e070cd75b078875420653745e4be2dacce7da95342033ae8f6ab923ce520a
.venv/Scripts/python.exe -B -m scripts.plot_neighbor_intervention
.venv/Scripts/python.exe -B -m unittest tests.test_neighbor_publication tests.test_neighbor_figures -v
```

Plot dùng `requirements-figures.txt` tùy chọn; không đưa Matplotlib vào web
runtime. Test sản phẩm/figure không cần Matplotlib. Replay vị trí/renderer
cần raw cache đúng hash, runtime Windows gốc và thread request đã khóa.

Phần mềm đã phát hành qua PR #8 và #9 tại `f2e2aa4`:
[387 test CI](evidence/0.10/ci-pr9-f88b340.json), 13 optional raw-cache/
photutils skip, sáu test Mongo fixture thật và bốn suite Node đạt.
[54 response public](evidence/0.10/production-f2e2aa4.json) xác minh 40
artifact, commit API và cleanup QA; [browser](evidence/0.10/neighbor-production-browser.json)
đổi được mẫu và giữ ca 0/16. Hai build lỗi trước đó được giữ trong runbook;
API contract tối giản tách static report khỏi function. Các bằng chứng này
không thay kết luận khoa học chưa đạt ở trên.

## Những giới hạn vẫn cần xử lý

Control dùng empirical VARIANCE gốc làm thang Gaussian; nó có thể đã chứa
shot noise của nguồn gốc. Source Poisson mới là ideal ramp với gain/nominal
timing có điều kiện, không chứng minh ngân sách detector không bị đếm trùng.
Fitter nhận phương sai nguồn oracle từ truth. Gaussian khác ePSF fitter,
nhưng chưa phải PSF SPHEREx đo độc lập; các stress-case không đo trực tiếp
sai số WISE hoặc khả năng tìm kiếm mù. Chưa mô hình tương quan nền/noise,
uncertainty ePSF, thiếu nguồn catalog, vị trí neighbor, chuyển động trong
mùa, phổ/chromaticity, parallax hoặc shared registration covariance.

Chưa có covariance/coverage hay detection probability. Jacobian/rank vị
trí chưa replay độc lập; Poisson/Gaussian realization không được redraw
trong audit, chỉ kiểm source mean/variance/provenance và hash đã ghi.
[IRSA cho phép ePSF mới trên ảnh QR2 cũ](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/);
điều đó không kiểm chứng bias của nội suy/renderer hiện tại trên WISE.

Mốc kế tiếp: trên dữ liệu development, giữ sao tham chiếu ngoài việc xây
PSF/căn chỉnh để đo residual theo vị trí/màu/độ sáng; thêm null/no-source
control và kiểm catalog hàng xóm trước một gate mới. Tiêu chí đạt gồm sai
lệch tuyệt đối, failure/refusal và false-accept giữ đủ mẫu số; một nghiệm
hội tụ không được xem là nguồn đã đo đúng. Sau đó nối time model từng
exposure và covariance căn chỉnh chung. Khóa evaluator, power, miền hỗ
trợ, gate và overlap trước 12 calibration / 12 validation / 6 final holdout.
