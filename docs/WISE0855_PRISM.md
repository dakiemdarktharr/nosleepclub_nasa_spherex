# Phổ JWST/NIRSpec PRISM riêng cho WISE 0855

Đã lấy [sản phẩm MAST x1d công khai cấp 3](https://mast.stsci.edu/jwst/api/v0.1/Download/file?uri=mast%3AJWST%2Fproduct%2Fjw01230-o007_t001-s000000001_nirspec_clear-prism-s200a1-subs200a1_x1d.fits)
của WISE 0855, program 1230, ngày 17-04-2023, CLEAR/PRISM, khe S200A1.
Metadata MAST ghi `PUBLIC`, obsid `349842176`, 198.720 byte; SHA-256 của FITS
là `17164197d803117d02c0e1e89ce64d5521ba86b523d3ba0cc03679974df53e3f`.
FITS ghi CAL_VER `3.0.0`, CRDS `jwst_1584.pmap`, thời điểm tạo
12-10-2026 10:03:40.226. MAST có thể tái xử lý sản phẩm; hash xác định bản
được audit. Metadata, bảng cột/đơn vị, URL, hash và association được ghi
trong [wise0855-prism-reference.json](../web/data/external/wise0855-prism-reference.json),
còn bản gốc và metadata đầy đủ ở `data/raw/external/wise0855/` đã được bỏ qua Git.

Association `spec3_00001` liệt kê **ba science exposure NRS1** cùng hai mục
target acquisition. FITS ghi `EXPCOUNT=7`; con số header này không được diễn
giải là số science member trong association. Đây là phổ pipeline MAST kết hợp
theo association, không phải bảng PRISM Hình 3 được trích xuất riêng trong
[Luhman và cộng sự 2024](https://doi.org/10.3847/1538-3881/ad0b72). Không
giả định phổ MAST đã nhận cùng bước scale Spitzer của nhóm tác giả.

File chứa 434 hàng, bước sóng `WAVELENGTH` tính bằng µm, `FLUX` và
`FLUX_ERROR` bằng Jy, cùng bitmask `DQ`. Định nghĩa kiểm tra mô tả ở đây là
DQ bằng 0, flux và error hữu hạn, error dương: **410/434 hàng đạt**. Có 24
hàng DQ khác 0 với flux NaN và error 0; chúng vẫn được giữ nguyên trong parser.
Trong các hàng đạt có 29 flux âm, cũng được giữ nguyên. Phạm vi wavelength
của hàng đạt là 0,5981883407–5,3010544777 µm.

Vùng 4,266020–5,110683 µm, là toàn bộ miền bước sóng của lưới response R7
và ba shift trong preflight trước đó, có **100/100 mẫu nằm trong miền đạt**.
Tính cả hai mẫu ngoài để kẹp hai biên có **102/102 mẫu đạt**, phạm vi kẹp
4,2642903328–5,1135554314 µm, khoảng cách giữa hai mẫu lớn nhất
0,0093011856 µm, nhỏ hơn ngưỡng 0,01 µm đã chọn. Riêng đoạn
5,0930738449–5,110683 µm có hai mẫu bên trong và bốn mẫu kẹp, tất cả đạt;
khoảng cách kẹp lớn nhất 0,0076842308 µm. Những con số này chỉ mô tả support
theo mask và sampling; chưa tính bandpass hoặc thay đổi bất kỳ kết quả trước.

Theo [tài liệu NIRSpec](https://jwst-docs.stsci.edu/jwst-near-infrared-spectrograph/nirspec-instrumentation/nirspec-dispersers-and-filters)
và bài báo Luhman, độ phân giải PRISM thay đổi theo bước sóng, khoảng
R≈300 gần đầu dài; G395M khoảng R≈1000. Phổ PRISM đã chịu line-spread function
và các bước xử lý của NIRSpec. Việc có mẫu kẹp không bảo đảm giữ được cấu trúc
phổ chi tiết cho response khác, kể cả response có R≈130; độ rộng, hình dạng
LSF và cách so sánh hoặc tích phân phải được xác định trong protocol riêng.
Sai số theo hàng không cung cấp covariance phổ đầy đủ, sai số chuẩn tuyệt đối
hay biến thiên thời gian giữa các quan sát.

Chưa ghép hoặc scale PRISM với G395M, chưa dựng SED kết hợp, bơm nhiễu, đo
nguồn hay fit. Nếu sau này cần nghiên cứu dùng PRISM, hãy khóa trước phương
pháp LSF/response, xử lý covariance và chấp nhận sai khác calibration; lấy
mẫu tại đủ bước sóng không tự xác nhận một phép đo thiên văn.

Kiểm tra file đã lưu bằng
`.venv\Scripts\python.exe scripts/parse_wise0855_prism.py` và chạy
`.venv\Scripts\python.exe -m unittest tests.test_wise0855_prism -v`.
Nếu file chưa được cache, `--fetch` chỉ lấy hai file MAST và metadata đã ghi,
kiểm tra hash/size và không ghi đè bytes khác; một bản MAST đã tái xử lý sẽ
bị từ chối thay vì âm thầm thay thế phiên bản đã xác định.
