# Tham chiếu phổ độc lập cho WISE 0855

Ứng viên là phổ JWST/NIRSpec G395M do **Luhman và cộng sự** công bố trong
[AJ 167, 5 (2024)](https://doi.org/10.3847/1538-3881/ad0b72), dữ liệu cho
Hình 4. [CDS ReadMe](https://cdsarc.cds.unistra.fr/viz-bin/ReadMe/J/AJ/167/5?format=html&tex=true)
liệt kê `fig4.dat` có 1.488 hàng: `Wave` theo µm, `Flux` và `e_Flux` theo Jy;
hai cột thông lượng có thể trống. Danh mục là `J/AJ/167/5`, bảng
`J/AJ/167/5/fig4`, DOI [10.26093/cds/vizier.51670005](https://doi.org/10.26093/cds/vizier.51670005).
Bài báo có giấy phép CC BY 4.0; cần xác minh riêng điều kiện sử dụng bảng
trước khi phân phối lại dữ liệu.

Bài báo cho biết JWST quan sát ngày 17-04-2023 UTC, chương trình GTO 1230,
khe S200A1 với G395M/F290LP, ba vị trí nod, tổng thời gian 3.931 giây.
Phổ có độ phân giải xấp xỉ 1.000 và dải hữu ích 2,87–5,09 µm cùng
5,37–5,54 µm, bao gồm vùng D6 4,4–5,0 µm. Đây là phổ trích xuất và kết hợp
bởi nhóm tác giả từ nhiều nod; không phải phổ của một exposure riêng lẻ.
Nhóm dùng pipeline ESA tùy biến, sao chuẩn quan sát khi commissioning và
điều chỉnh chuẩn flux theo quang trắc [4.5] nhiều epoch của Spitzer. Nguồn
phổ này độc lập với SPHEREx, song chuẩn thông lượng của nó không độc lập
với phép chuẩn Spitzer mà tác giả sử dụng. Tham chiếu ảnh gốc MAST được bài
báo nêu là [10.17909/1fsf-6j64](https://doi.org/10.17909/1fsf-6j64).

**Chưa có file phổ tác giả trong workspace.** CDS ReadMe và metadata đã được kiểm tra,
nhưng các lần thử tải trực tiếp `fig4.dat`, export VizieR và mirror Harvard
đều timeout từ môi trường. Do đó không có hash hay số liệu phổ giả định.
Đường lấy dữ liệu: mở [danh mục CDS](https://vizier.cds.unistra.fr/viz-bin/VizieR-2?-source=J/AJ/167/5),
chọn bảng `J/AJ/167/5/fig4`, export toàn bộ hàng; hoặc dùng liên kết FTP của
danh mục lấy `fig4.dat` theo ReadMe. Sau khi truy cập được, lưu nguyên bytes,
thời điểm lấy, URL, SHA-256, giấy phép và kiểm tra đủ 1.488 hàng, đơn vị,
giá trị trống, dải bước sóng và kết quả chuẩn hóa. Thời điểm cập nhật
[registry CDS](https://dc.g-vo.org/rr/q/lp/custom/CDS.VizieR/J/AJ/167/5)
là 06-11-2024, không chứng minh nội dung file là một snapshot bất biến.
Metadata máy đọc được ở [wise0855-sed-reference.json](../web/data/external/wise0855-sed-reference.json).

Đã lấy được một **phổ thay thế từ pipeline MAST**, không phải bảng Hình 4 của
tác giả: [sản phẩm x1d cấp 3](https://mast.stsci.edu/jwst/api/v0.1/Download/file?uri=mast%3AJWST%2Fproduct%2Fjw01230-o007_t001-s000000001_nirspec_f290lp-g395m-s200a1-subs200a1_x1d.fits),
được MAST liệt kê công khai trong program 1230, target WISE0855-0714,
F290LP/G395M, ngày 17-04-2023. File có 322.560 byte, SHA-256
`9474fbbcfe1304fa6763fd3a9ea3190f419785763f53a1827ac997aef84e19a6`,
CAL_VER `3.0.0`, CRDS `jwst_1584.pmap` và thời điểm tạo FITS 12-10-2026.
Các product MAST có thể được xử lý lại, nên phải khóa hash này trước khi dùng.
File association công khai đi kèm xác định ba exposure science NRS1; việc kết
hợp và trích xuất của pipeline khác quy trình tùy biến và scale theo Spitzer
của Luhman. Không khẳng định hai phổ bằng nhau hoặc flux là bất biến.
Chính sách [MAST Data Use](https://archive.stsci.edu/publishing/data-use)
cho phép sử dụng công khai sau thời gian độc quyền; trích dẫn và attribution
được mô tả tại nguồn này.

File FITS có 1.254 hàng trong EXTRACT1D; `WAVELENGTH` tính bằng µm, `FLUX`
và `FLUX_ERROR` bằng Jy, `DQ` là bitmask. Giới hạn kỹ thuật thận trọng ở đây
là DQ bằng 0, flux và sai số hữu hạn, sai số dương: 1.233/1.254 hàng đạt;
vùng 4,4–5,0 µm có 335/335 hàng đạt. Có 26 flux âm trong toàn bộ các hàng đạt;
chúng được giữ lại vì flux đo có nhiễu có thể âm. Quy tắc này không chứng minh
flux chính xác hoặc độc lập. [JWST pipeline](https://jwst-pipeline.readthedocs.io/en/1.17.x/jwst/extract_1d/description.html)
mô tả các cột và phép trích xuất; NRS1 ở khe A có thể bao phủ vùng G395M này
theo [tài liệu NIRSpec](https://jwst-docs.stsci.edu/jwst-near-infrared-spectrograph/nirspec-operations/nirspec-fs-operations/nirspec-fs-wavelength-ranges-and-gaps).
Không thay dữ liệu MAST bằng bảng tác giả chưa tải, và không áp hệ số Spitzer
từ bài báo sang file này. Metadata, association, hash và nguồn gốc query đã
được lưu trong JSON; nguyên FITS và responses nằm trong `data/raw/external/wise0855/`.
Kiểm tra lại bằng `.venv\Scripts\python.exe scripts/parse_wise0855_x1d.py` và
`.venv\Scripts\python.exe -m unittest tests.test_wise0855_x1d -v`.

Không xem `e_Flux` là toàn bộ bất định độc lập giữa các bước sóng: ReadMe
không cung cấp ma trận hiệp phương sai đầy đủ, còn sai số chuẩn tuyệt đối
có thành phần chung. Phổ không đồng thời với các ảnh SPHEREx. Bài báo nêu
phân tán giữa các epoch Spitzer khi đánh giá chuẩn flux; [Miles và cộng sự
2026](https://arxiv.org/abs/2609.20664) báo cáo biến thiên phụ thuộc bước
sóng của dải CO đến 10% peak-to-peak tại một số bước sóng trong chuỗi NIRSpec
11 giờ. Đây là kết quả preprint, không phải mức biến thiên áp dụng cho mọi
bước sóng hoặc mọi epoch.

Phổ cũng không phải đáp ứng phổ của SPHEREx. Trước một nghiên cứu bơm nhiễu
cần khóa cách tích phân phổ theo đáp ứng theo pixel và theo bước sóng, đơn vị
flux, PSF, phân bố thời gian/biến thiên và mô hình gain/nhiễu; không thay tích
phân dải bằng giá trị đơn sắc nếu chưa chứng minh là phù hợp. Những bước này
chưa được thực hiện, và tham chiếu này không xác nhận độ chính xác WISE.

Thông tin vị trí là vấn đề riêng: [Kirkpatrick và cộng sự 2021, Table 5](https://doi.org/10.3847/1538-4365/abd107)
ghi WISE 0855 tại epoch trung bình MJD 57633,39, với parallax
439,0 ± 2,4 mas, μRA −8123,7 ± 1,3 và μDec +673,2 ± 1,3 mas/năm.
Dòng này ghi 19 epoch Spitzer, không có epoch WISE, và 46 sao Gaia dùng đăng
ký. Các sai số riêng lẻ trong bảng không cung cấp toàn bộ covariance để lan
truyền sang 2025–2026; cần xác minh quy ước thành phần μRA, ephemeris và
covariance trước khi dùng làm tham chiếu vị trí định lượng. Phổ không tạo ra
astrometric truth, và prior WISE hiện tại không được sửa.
