# WISE 0855: bản demo dữ liệu thật

Ngày thực hiện: 30/10/2026. [Mở demo trên máy phát triển](http://127.0.0.1:8766/).

Đây là báo cáo baseline ảnh đơn. Bản mới đã cộng ảnh theo epoch và fit centroid độc lập: xem [kết quả cộng ảnh và astrometry](WISE0855_COADD.md). Những kết luận dưới đây áp dụng cho ba cặp ảnh đơn được giữ lại trong demo.

## Đã hoàn thành

- Truy vấn IRSA, tải 43 cutout D6 để kiểm tra spectral WCS tại vùng mục tiêu.
- Chọn ba cặp theo thời gian và bước sóng; tải thêm 6 cutout centered quanh vị trí ngoại suy của WISE 0855.
- Đọc IMAGE, FLAGS, VARIANCE, ZODI, PSF và WCS-WAVE; giữ liên hệ với detector gốc khi chọn PSF.
- Đưa về lưới TAN 64×64, 6.15 arcsec/pixel, bắc ở trên và đông bên trái.
- Fit dịch chuyển nhỏ bằng sao nền; cross-convolve bằng PSF đo của hai ảnh; hiệu chỉnh flux bằng tỷ lệ aperture sao nền và offset nền.
- Xuất trước/sau/sai khác, variance, mask hợp lệ và điểm residual thực nghiệm.
- Web so sánh bốn chế độ, zoom/highlight, xem provenance, lưu/xóa/xuất nhận xét cục bộ.

## Kết quả định lượng

| Cặp | Ngày trước → sau | Baseline | λ tại vị trí dự kiến, trước/sau | S/N PSF cố định trước/sau | RMS sao nền sau fit |
| --- | --- | --- | --- | --- | --- |
| 4.853 µm | 2025-05-05 → 2026-05-09 | 368.36 ngày | 4.853525 / 4.853311 µm | 2.97 / 4.69 | 0.237 px, 5 sao |
| 4.961 µm | 2025-05-05 → 2026-05-11 | 370.40 ngày | 4.961050 / 4.960913 µm | 1.06 / 2.65 | 0.265 px, 5 sao |
| 4.609 µm | 2025-11-10 → 2026-04-23 | 164.07 ngày | 4.606615 / 4.610911 µm | 4.46 / 5.28 | 0.210 px, 6 sao |

Các số đầy đủ được máy sinh trong [manifest](../web/data/manifest.json). Bề rộng phổ cặp đầu khoảng 37.9 nm; Δλ tra được khoảng 0.214 nm. **WCS-WAVE có độ chính xác trực quan hóa cỡ 1 nm**, nên không diễn giải các chữ số nhỏ hơn mức đó là độ chính xác đo được.

RMS là residual trên các sao đã dùng để fit translation, không phải tập sao kiểm tra độc lập. Hai ảnh vẫn có phiên bản xử lý khác nhau trong QR2 (`6.4+psffix1` và `6.5.6` ở cặp đầu); phép hiệu chỉnh toàn trường không loại hết mọi khác biệt calibration/màu phổ.

## Kết luận hiện tại

Phần mềm đã có thể tạo và highlight vùng ảnh sai khác từ dữ liệu thật. Các đối chứng số kiểm tra được registration và PSF cross-convolution. **Chưa xác minh độc lập chuyển động WISE 0855 từ những cặp này.**

Vị trí dự kiến lấy từ [Luhman 2014, Tables 1 và 2](https://arxiv.org/pdf/1404.6501): tọa độ Spitzer MJD 56677.3 và proper motion trong bài. Chỉ ngoại suy tuyến tính; chưa thêm parallax và chưa fit centroid của SPHEREx. S/N trong bảng là biên độ fit PSF tại vị trí đó chia sai số, có tăng sai số khi reduced chi-square > 1. Đây là kiểm tra có prior, không phải phát hiện mù.

Highlight tự động là các cực trị |score| ≥ 3.5 trong vùng qua mask, có support đủ và sai khác bước sóng cục bộ ≤ ½ bề rộng phổ. Score được chuẩn hóa theo phân bố residual nền, chưa có hiệu chuẩn false-alarm probability. Một residual vẫn có thể là artifact hoặc khác biệt màu của nguồn.

## Các giới hạn cần giữ khi demo

- Biến đổi theo bước sóng có thể trộn với biến đổi thời gian; WCS-WAVE chưa thay thế spectral calibration response cho khoa học chính xác.
- Bilinear interpolation và convolution tạo noise tương quan. Variance dùng squared weights, nhưng chưa giữ covariance đầy đủ giữa output pixels.
- Dùng PSF cục bộ quanh mục tiêu cho trường nhìn nhỏ; biến đổi PSF trong toàn vùng vẫn có thể gây residual.
- Các pixel bị mask được xử lý bằng support có chuẩn hóa; vùng không đủ support không được highlight.
- Chưa thực hiện blind centroid fit, mô hình parallax, đối sánh catalog hoặc injection–recovery trên nền SPHEREx thực.
- Đây là bộ ảnh cố định có thể kiểm tra, chưa phải công cụ truy vấn tọa độ bất kỳ.
- Nhận xét chỉ lưu trong localStorage của trình duyệt, có hash analysis/input để tránh gắn nhãn nhầm phiên bản; chưa có tài khoản hoặc đồng bộ nhóm.

## Kiểm tra đã thực hiện

9 tests trong `tests/test_science.py` đã qua: variance bilinear, missing-data mask, SOURCE bit, dấu registration, đối chứng nguồn đứng yên với PSF khác nhau, nguồn dịch chuyển giả lập tạo residual, hướng của prior, hash input và tính nhất quán WCS/sản phẩm thật.

Đã thử trực tiếp trên browser: trước/sau, song song, sai khác, đổi cặp, chọn residual, lưu nhận xét qua reload, xóa nhận xét thử, nút xuất JSON, evidence dialog. Kiểm tra responsive tại 390×844 không có tràn ngang; console không có log lỗi trong phiên kiểm tra. Nhận xét thử đã được xóa.

Các synthetic controls là kiểm tra phép toán; không phải benchmark recall/precision của pipeline trên thiên thể thật.

## Bước tiếp theo sau khi duyệt sản phẩm

**Ưu tiên: tăng S/N và đo chuyển động có sai số.**

1. Tạo manifest các ảnh trong từng epoch có response phổ tương thích; kiểm tra CWAVE/CBAND và cờ chất lượng. Không cộng các dải phổ tùy ý.
2. Cộng ảnh có trọng số và giữ variance/coverage cùng frame thành phần; đo xem S/N có cải thiện thật không.
3. Fit PSF/centroid độc lập ở hai epoch; kiểm tra với sao nền giữ lại và đưa parallax vào so sánh với astrometry tham khảo.
4. Chạy injection–recovery trên nền FITS thật với nguồn đứng yên, chuyển động và các mức flux khác nhau.

Điều kiện hoàn thành bước tiếp theo: có coadd thật theo epoch, bảng centroid và sai số, kiểm tra nền độc lập, kết luận rõ chuyển động có/không được phân giải với dữ liệu hiện có. Sau đó mới xây dataset và đo lợi ích của CNN thật/nhiễu.

## Nguồn và sản phẩm

- [IRSA: Data Access](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/)
- [IRSA: Cutouts và spectral WCS](https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts/)
- [IRSA: PSF trong cutout](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/)
- [IRSA: photometry và bitflags](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html)
- [SPHEREx QR2 DOI](https://doi.org/10.26131/IRSA652)
- [Ảnh sản phẩm](wise0855-demo-desktop.jpg)

Raw FITS và manifest tải nằm trong `data/raw/wise0855/` (ignored). Sản phẩm nhỏ có thể chia sẻ nằm trong `web/data/`. Download FITS đã xử lý ở web giữ WCS theo từng HDU, variance và thông tin processing; tên `EMP_SCORE` nhấn mạnh đây là score thực nghiệm.
