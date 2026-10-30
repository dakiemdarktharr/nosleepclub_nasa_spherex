# Hợp đồng API ảnh quan sát SPHEREx, phiên bản 1.1

`GET /api/frame` lấy một cutout từ Spectral Image MEF QR2 hoặc QR3 của IRSA và dựng PNG để **trực quan hóa**, không fit nguồn, photometry hay xác nhận phát hiện/chuyển động. Chỉ chấp nhận URL sản phẩm level2 HTTPS theo cấu trúc thư mục và tên tệp SPHEREx chính thức trên `irsa.ipac.caltech.edu`, không cho query/fragment hay redirect; URL thường lấy từ `/api/observations`. Request mẫu (URL phải được mã hóa):

```
/api/frame?url=<encodeURIComponent(access_url)>&ra=350&dec=35&fov_deg=0.05&zodi=raw&low=0&high=2
```

| Tham số | Ý nghĩa |
| --- | --- |
| `url` | Bắt buộc, URL level2 đầy đủ từ IRSA thuộc `qr2` hoặc `qr3`. Không nhận URL tùy ý. |
| `ra`, `dec` | Bắt buộc, số thập phân hữu hạn ICRS theo độ; RA [0,360), Dec [-90,90]. Frontend phải chuyển sexagesimal trước. |
| `fov_deg` | Chiều rộng tối thiểu của grid vuông theo độ, >0 và ≤0,12; mặc định 0,05. |
| `zodi` | `raw` mặc định giữ IMAGE; `subtract` trừ mô hình ZODI theo pixel nếu có. Không trừ nền cục bộ. |
| `low`, `high` | Tùy chọn, phải có cả hai, hữu hạn, `low < high`, nằm trong ±10⁹ MJy/sr. Truyền cùng khoảng cho các frame để so cường độ trên cùng thang hiển thị. Bỏ cả hai dùng percentile 1–99 riêng từng frame, không thể so độ sáng trực tiếp. |

PNG là RGB, lưới TAN ICRS chung tâm, bắc lên trên, đông sang trái, 6,15 arcsec/pixel; dùng WCS gốc gồm SIP của FITS và lấy mẫu nearest-neighbor. Số pixel mỗi chiều là số lẻ nhỏ nhất đủ phủ FOV, tối thiểu 3 và tối đa 192; `X-Frame-Grid-FOV-Deg` cho độ rộng thực tế lớn hơn hoặc bằng yêu cầu. Độ phân giải này là lưới hiển thị, không tạo thông tin độ phân giải cao hơn hay hiệu chỉnh sai lệch astrometry giữa các exposure. Kích thước cutout IRSA được mở rộng để bao góc grid khi ảnh bị xoay; vùng ngoài ảnh vẫn có thể thiếu. Lấy mẫu này không bảo toàn flux, không thích hợp làm đầu vào photometry, và không kèm uncertainty.

Pixel khả dụng cho hiển thị là grayscale tuyến tính sau cắt theo low/high. **Tím RGB (255,0,255)** là ngoài ảnh hoặc giá trị không hữu hạn, **cam RGB (255,140,0)** là pixel có FLAGS bị loại. Phiên bản 1.1 chỉ cho phép SOURCE bit 21; mọi bit khác, gồm **FULLSAMPLE bit 12** và bit lạ, đều mask. Header FLAGS phải xác nhận `MP_SOURCE=21`, `MP_FULLSAMPLE=12`, nếu thiếu/sai thì từ chối. SOURCE có thể là nguồn thật, còn FULLSAMPLE là vùng 8×32 lưu full-history mà supplement loại khỏi khoa học, không phải chứng nhận ramp hợp lệ. Xem [audit và nguồn chính thức](SCIENCE_MASK_AUDIT.md). Policy hiển thị không thay thế kiểm định photometry hay variance/gain; nguồn lân cận vẫn có thể gây nhiễm. Khi không có pixel khả dụng, PNG vẫn phản ánh vùng thiếu/mask thật và `X-Frame-Valid-Pixels: 0`; lỗi tải/đọc không tạo ảnh thay thế.

Phản hồi 200 `image/png` có các header:

- `X-Frame-Contract`, `X-Frame-Source-URL`, `X-Frame-Cutout-URL`, `X-Frame-Cutout-SHA256`, `X-Frame-Retrieved-At` (UTC): phiên bản và provenance của byte FITS cutout thực nhận. Hash này không phải hash file MEF đầy đủ.
- `X-Frame-Release`, `X-Frame-Obs-ID`, `X-Frame-Detector`, `X-Frame-MJD-Obs` nếu có: định danh và thời điểm từ FITS. Server kiểm tra OBSID/DETECTOR khớp tên URL. MJD giữ giá trị header gốc, không tự giả định timescale.
- `X-Frame-Grid-RA-Deg`, `X-Frame-Grid-Dec-Deg`, `X-Frame-Grid-Scale-Arcsec`, `X-Frame-Grid-Size-Px`, `X-Frame-Grid-FOV-Deg`: grid chung và kích thước ảnh.
- `X-Frame-Unit: MJy/sr`, `X-Frame-Zodi`, `X-Frame-Contrast-Mode` (`fixed` hoặc `percentile_1_99`), `X-Frame-Contrast-Low`, `X-Frame-Contrast-High`, `X-Frame-Valid-Pixels`: xử lý và thang hiển thị. Nếu tất cả pixel thiếu, percentile dự phòng là [0,1]; nếu percentile trùng nhau, khoảng được mở ±0,5 MJy/sr.
- `X-Frame-Mask-Policy: source-only-allowlist-v2`, `X-Frame-Masked-Pixels`, `X-Frame-Missing-Pixels`: policy và số pixel bị loại/thiếu trên grid PNG. Tổng valid + masked + missing bằng size². Frontend giữ policy trong JSON, hiển thị số lượng và từ chối đối chiếu hai policy khác nhau trong cùng lượt tìm.

Không trả bước sóng tại pixel: `WCS-WAVE` chỉ đạt độ chính xác trực quan; phép đo cần CWAVE/CBAND và spectral calibration tương ứng. [IRSA Data Products](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/) mô tả các sản phẩm này. Các frame khác thời điểm có thể khác bandpass, calibration, PSF, nền và độ phủ; lưới chung không khử các khác biệt đó.

IRSA cutout sử dụng `center` và `size` theo [hướng dẫn dịch vụ](https://irsa.ipac.caltech.edu/ibe/cutouts.html). Giới hạn FITS 12.000.000 byte, ảnh native tối đa 512×512; socket timeout 20 giây và deadline 80 giây kiểm tra giữa các lượt đọc, một lần chờ đọc có thể kéo dài thêm 20 giây. Khuyến nghị Vercel `maxDuration=120` để có khoảng cho cold start và xử lý; theo [giới hạn Vercel](https://vercel.com/docs/functions/limitations), cấu hình này cần Fluid compute trên Hobby (không Fluid, Hobby tối đa 60 giây). Xác minh cấu hình thực tế trước triển khai; không tự đổi plan. Runtime cần `astropy==8.0.2`, `numpy==2.4.6`, `Pillow==13.0.0`. Static Python server địa phương không chạy API serverless này.

Phép thử ngày 30/10/2026 với một exposure QR2 D6 tại RA 350°, Dec 35° nhận cutout 5.094.720 byte trong 3,27 giây; HTTP handler tạo PNG thật trong 2,94 giây, SHA-256 cutout `5479f905947fe3703a092f812abaca4235ca5723aa07a5da6a8d78bb6dedff21`. Sau khi sửa, exposure kế tiếp qua handler trả PNG thật trong 3,12 giây, SHA-256 cutout `2ca7b4bf2ab7a4e7ae7309745b6b7adfcf8172363f533b524d0aa7a6503ba0d4`. Các lần gọi khác nhận lỗi HTTP hoặc luồng bị ngắt sau 47,06 giây; đây không phải bảo đảm độ trễ hay độ sẵn sàng trên Vercel. IRSA cho biết cutout SPHEREx giữ mọi extension; không tự bỏ PSF hay dùng partial FITS để tránh thay đổi provenance. Luồng bị cắt hoặc sai Content-Length trả lỗi, không tạo PNG. Cache public 300 giây có thể giảm tải khi URL giống hệt và tầng cache hỗ trợ, không bảo đảm cache hit.

Request sai trả JSON 400; phương thức không hỗ trợ thông dụng 405; lỗi upstream/FITS 502; timeout 504; lỗi nội bộ 500. Không trả stack trace. Rate guard production dùng MongoDB, 8/IP/phút và 24 toàn cục/phút, vượt trả 429 và Retry-After; thiếu môi trường/identity/storage hợp lệ trả 503 trước gọi IRSA. [Hợp đồng guard](API_ABUSE_CONTROLS.md) mô tả XFF và local test mode. Cache browser/CDN tối đa 300 giây; lỗi no-store, không có cache FITS trong database. Retrieval timestamp/hash thuộc response đã cache. Log dùng allowlist request ID/status/category/latency/severity; lỗi frame có mã lỗi và HTTP status upstream khi có, không có URL, tọa độ, body, cookie hoặc secret.
