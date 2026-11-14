# Danh mục dữ liệu cho Planet X and SPHEREx

Đối chiếu ngày **14/11/2026**. [Mở bản đồ trời 3D](sky-atlas.html) hoặc [lấy danh mục JSON](data/sky-datasets.json). Danh mục có **38 bộ dữ liệu, bản phát hành hoặc dịch vụ** liên quan đến ảnh theo thời gian, đối chiếu chuyển động, biến quang và phổ, cùng một lớp footprint mẫu lấy trực tiếp từ IRSA. Các liên kết trỏ tới kho dữ liệu, công cụ truy vấn hoặc tài liệu do đơn vị quản lý hay tác giả công bố. Phiên khảo sát ưu tiên IRSA, ESA, MAST, ESO, CADC và các nhóm khảo sát. Dữ liệu tham khảo địa phương đã có receipt riêng. Bước này tải metadata IRSA dung lượng nhỏ.

## Theo đề bài

Đề bài yêu cầu một web công khai nhận **RA và Dec** và phát **ảnh SPHEREx của cùng vùng trời theo thời gian**. Năm mục tiêu là Barnard’s Star, ε Indi B, WISE 0855, RW Aurigae và R Draconis. Tọa độ WISE 0855 ghi trong đề là **08h55m10.831s, −07°14′42.53″** hay **133,79512917°, −7,24514722°**. Giá trị này là tọa độ tham chiếu trong đề. Repo còn có tâm truy vấn dự báo gần epoch ảnh. [Ghi chú đề bài](CHALLENGE.md) · [Tâm trường truy vấn của repo](../web/data/challenge-targets.json) · [Trang Details](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details)

Tab Resources đã được mở trực tiếp ngày 14/11/2026 và hiển thị tám mục. Bốn mục NASA gồm IRSA, notebook SPHEREx, WiseView và Gaia DR3. Bốn mục của đối tác Canada gồm giới thiệu NEOSSat, CADC, tutorial NEOSSat và bộ dữ liệu NEOSSat. Hướng dẫn công khai của Space Apps Navigator khuyên tra IRSA theo tọa độ, kiểm tra thời điểm và dải, căn chỉnh WCS rồi phát ảnh theo thứ tự thời gian. [Resources chính thức](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=resources) · [Đối chiếu đề chính thức](CHALLENGE_LIVE_REVIEW.md) · [Trao đổi trong NASA Space Apps](https://github.com/nasa/spaceapps/discussions/1847)

## SPHEREx dùng trực tiếp

| Bộ dữ liệu | Phủ vùng nào | Truy cập và sử dụng |
| --- | --- | --- |
| **DR1 Spectral Images**, DOI `10.26131/IRSA678` | Khảo sát rộng toàn trời trong Survey 1 và 2. Độ phủ theo epoch, detector và bước sóng cần truy riêng. | FITS ảnh phổ từng lần chụp. Tìm `spherex_dr1` qua SIA2. [IRSA DR1](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html) |
| **QR3 Spectral Images** | Khảo sát rộng Survey 3 và 4, phát hành theo tiến độ. | Tìm `spherex_qr3`. IRSA hướng dẫn dùng DR1 và QR3 chung. Một số QR3 đã có tệp reprocess, nên đối chiếu ID và ngày xử lý. [Các bản phát hành](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases/) |
| **Deep Survey** | Hai vùng gần cực hoàng đạo Bắc và Nam. Vùng Nam lệch cực để giảm nhiễm tiền cảnh. | Tìm `spherex_dr1_deep` và `spherex_qr3_deep`. Xem MOC chính thức trong IRSA và `s_region` từng ảnh. [Thiết kế khảo sát](https://spherex.caltech.edu/page/survey) · [MOC IRSA](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/searching.html) |
| **DR1 All-Sky Cube**, DOI `10.26131/IRSA679` | Toàn trời, 102 kênh phổ danh định. | Tìm `spherex_dr1_cube`. Cube ghép từ ảnh DR1 dùng cho tra phổ và bản đồ nền. Trục thứ ba là bước sóng. [IRSA DR1](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html) |
| **QR2 Spectral Images** | Ảnh lịch sử còn cần để tái lập các lần đo của repo. | Sau DR1/QR3, IRSA ngừng tra QR2 qua SIA2 và giữ tải trực tiếp đến **tháng 2/2027**. Ghi lại URI, phiên bản và hash của từng tệp cần tái lập. [Các bản phát hành](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases/) · [Quy ước thư mục](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/) |
| **Mosaic / Spectrophotometry** | Vùng do người dùng yêu cầu với các ảnh đầu vào có sẵn. | Tạo cube ghép hoặc phổ từ nhiều ảnh. Spectrophotometry IRSA giữ vị trí nguồn cố định khi fit flux. [Mosaic và công cụ phổ](https://irsa.ipac.caltech.edu/applications/spherex/) · [Spectrophotometry](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html) |
| **SPIFF QR2-2026-04-24** | Mục tiêu sao lùn M/L/T/Y của bộ phổ. | Thư viện phổ và template cộng đồng, hữu ích cho phát triển phép trích phổ. Phổ dùng dữ liệu SPHEREx nên có thể chia sẻ nguồn hoặc exposure với bộ thử. [Zenodo](https://zenodo.org/records/19051216) · [Receipt của dự án](EXTERNAL_REFERENCE_DATA.md) |

DR1 phát hành ngày **12/11/2026**. Với ảnh chuỗi thời gian, truy `POS`, collection và nếu cần `TIME` hoặc `BAND` qua SIA2, đọc `s_region` của từng hàng, lấy cutout FITS, rồi căn chỉnh trên lưới trời chung. Đọc WCS-WAVE tại vị trí mục tiêu để biết bước sóng thực, và dùng FLAGS, VARIANCE, PSF theo điều kiện phép đo. Cùng detector hoặc cùng tên dải chưa đủ để kết luận hai điểm ảnh có đáp ứng phổ tương đương. [Phiên bản bản phát hành](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/overview.html) · [Collection và FITS cutout](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/) · [Các HDU](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/visualization.html)

### Truy vấn trực tiếp ở năm trường thử

Các truy vấn dưới đây chỉ lấy metadata SIA2 trong vòng tròn **0,05°**, giới hạn **1 hàng**, tại tâm trường của repo. `OVERFLOW` báo có kết quả và bộ trả về bị giới hạn. Các ô có dữ liệu xác nhận có ít nhất một hàng giao cone ở thời điểm tra. Muốn xác định cặp ảnh phù hợp cần kiểm tra số epoch, dấu thời gian, footprint điểm, bước sóng và pixel hợp lệ. Riêng `OK` 0 hàng là kết quả của collection, cone và snapshot cụ thể. SHA-256 tính trên bytes phản hồi VOTable. [Định nghĩa tham số SIA2](https://irsa.ipac.caltech.edu/ibe/sia.html)

| Tâm trường | DR1 | QR3 |
| --- | --- | --- |
| Barnard’s Star | [OVERFLOW · 1 hàng](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=CIRCLE+269.44626689+4.76822222+0.05&MAXREC=1) | [OVERFLOW · 1 hàng](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr3&POS=CIRCLE+269.44626689+4.76822222+0.05&MAXREC=1) |
| ε Indi B | [OVERFLOW · 1 hàng](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=CIRCLE+331.04583333+-56.78333333+0.05&MAXREC=1) | [OVERFLOW · 1 hàng](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr3&POS=CIRCLE+331.04583333+-56.78333333+0.05&MAXREC=1) |
| WISE 0855 | [OVERFLOW · 1 hàng](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=CIRCLE+133.76012139+-7.24212794+0.05&MAXREC=1) | [OK · 0 hàng](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr3&POS=CIRCLE+133.76012139+-7.24212794+0.05&MAXREC=1) |
| RW Aurigae | [OVERFLOW · 1 hàng](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=CIRCLE+76.95652603+30.40143817+0.05&MAXREC=1) | [OVERFLOW · 1 hàng](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr3&POS=CIRCLE+76.95652603+30.40143817+0.05&MAXREC=1) |
| R Draconis | [OVERFLOW · 1 hàng](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=CIRCLE+248.16761083+66.75497942+0.05&MAXREC=1) | [OVERFLOW · 1 hàng](https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr3&POS=CIRCLE+248.16761083+66.75497942+0.05&MAXREC=1) |

<details>
<summary>SHA-256 phản hồi truy vấn</summary>

```text
barnard DR1 5bd4194e5324263c810ac976e99847c36664df37b17fd6b7dad33397346dc512
barnard QR3 a33d909b448f3340479c043b8f5e775c9d301c82f0df4cf9bfa8f5d80fa52ba5
epsilon DR1 58dd9e95ddb3bee05c72e629e21e3ed0ff49e553560aebfbafb14384fe3e87d1
epsilon QR3 c2816ca7f1d2daafbfdc7d2dfcb7112ed0cb8dfc1c10ca80cc3360434d8b7a41
wise0855 DR1 941460cdf510574fb3dfecba60b460f023269360514bd834728ed66cbc36638f
wise0855 QR3 fa538a0a6daf723452a8645c90efb86c1d6ddc68903b280bed9fb13ca1cdd3bd
rwaur DR1 acab7dfce19b5dca20cc06663f7cd00d56ba5bf99828a69d683d353afdf7836d
rwaur QR3 65201ce3b796198dec50cc5a468287220caf39a7159464daa9dd42073ed3909e
rdra DR1 b19a4d7a9d3e98d05ad84f0982b40791a8a53eafda41768d30fa345cc0e1aed7
rdra QR3 cdef3bac6db225de2c7c987192fa7f6efc817042e98d51b158405f7f6ec8f782
```

</details>

Lớp **SPHEREx DR1 / QR3 · Footprint mẫu** vẽ chín đa giác từ chín hàng có kết quả trong bảng. Các đỉnh lấy từ `s_region` nguyên gốc (STC-S `POLYGON ICRS`, đơn vị độ). Tệp JSON giữ chuỗi `s_region`, ID ảnh, detector, MJD, cận dải detector theo mét, URL FITS, truy vấn, SHA-256 metadata và thời điểm lấy. Hình học phản ánh phạm vi ảnh trong metadata. Một truy vấn cone có thể trả ảnh chỉ giao với biên của cone. [Danh mục và metadata](data/sky-datasets.json)

## Dữ liệu đối chiếu và lớp tham khảo

| Nhu cầu | Nguồn và phạm vi |
| --- | --- |
| **Thêm epoch hồng ngoại trước SPHEREx** | **WISE/NEOWISE Single Exposure** có ảnh và bảng nguồn từng lần chụp. **unWISE time-resolved** có các ảnh W1/W2 gộp theo lượt quét và catalog theo epoch. Các bộ này chia sẻ ảnh WISE/NEOWISE. **VarWISE** tuyển nguồn biến quang, liên kết về các phép đo từng exposure. [WISE/NEOWISE](https://irsa.ipac.caltech.edu/Missions/wise.html) · [unWISE](https://irsa.ipac.caltech.edu/data/WISE/unWISE/overview.html) · [VarWISE](https://irsa.ipac.caltech.edu/data/WISE/VarWISE/overview.html) |
| **Sao chuẩn và nguồn lân cận** | **Gaia DR3** cho vị trí, proper motion, thị sai và tham số chất lượng. **CatWISE2020** hỗ trợ nguồn đỏ trong W1/W2. **AllWISE**, **unWISE full-depth** và **2MASS Atlas/PSC** làm lớp ảnh và catalog tham khảo toàn trời. **2MASS 6X** sâu hơn trong một số trường. [Gaia DR3](https://gea.esac.esa.int/archive/documentation/GDR3/index.html) · [CatWISE2020](https://irsa.ipac.caltech.edu/data/WISE/CatWISE/gator_docs/catwise_colDescriptions.html) · [AllWISE](https://irsa.ipac.caltech.edu/Missions/wise.html) · [unWISE](https://catalog.unwise.me/) · [2MASS](https://irsa.ipac.caltech.edu/data/2MASS/docs/releases/allsky/) · [2MASS 6X](https://irsa.ipac.caltech.edu/data/2MASS/docs/releases/allsky/doc/seca3_1.html) |
| **Ảnh quang học theo epoch và ảnh nền lịch sử** | **Pan-STARRS1 DR2** chủ yếu từ Dec −30° lên Bắc, có stack và từng ảnh warp. **SkyMapper DR4** có đủ sáu dải tới khoảng Dec +16°, với một số trường phủ một phần đến +28°. **DSS** gom tấm kính toàn trời từ nhiều năm và nhiều dải. **DESI Legacy Imaging Surveys** có các trường sâu rời. [PS1 DR2](https://catalogs.mast.stsci.edu/panstarrs/) · [SkyMapper DR4](https://skymapper.anu.edu.au/data-release/dr4/) · [DSS](https://archive.stsci.edu/dss/) · [DESI Legacy Imaging](https://datalab.noirlab.edu/data/legacy-surveys) |
| **Light curve của RW Aur hoặc R Dra** | **ZTF**, **PTF/iPTF**, **ASAS-SN**, **ATLAS**, **AAVSO** và **TESS** cho các chuỗi thời gian, mỗi bộ có giới hạn độ sâu, bão hòa và thời gian riêng. Tra theo mục tiêu trước khi tích hợp. Mệnh đề biến quang ở band này cần bằng chứng riêng cho từng band. [ZTF](https://irsa.ipac.caltech.edu/Missions/ztf.html) · [PTF](https://irsa.ipac.caltech.edu/Missions/ptf.html) · [ASAS-SN](https://www.astronomy.ohio-state.edu/asassn/public/) · [ATLAS](https://fallingstar-data.com/forcedphot/) · [AAVSO](https://aavso.org/search-and-download-data/) · [TESS](https://archive.stsci.edu/missions-and-data/tess) |
| **Ảnh sâu, phổ và trường dày nguồn** | **Spitzer Heritage/SEIP**, **JWST/NIRSpec WISE 0855**, **HST** theo chương trình. **GLIMPSE I/II** bám dải Ngân Hà, **VISTA VVV/VIRAC2** quanh phình và đĩa Nam, **VISTA VHS** phần lớn trời Nam. **Euclid DR1-Foundation** công bố 12/11/2026, phủ các trường khảo sát rộng và sâu; xem footprint thực theo tile. [Spitzer](https://irsa.ipac.caltech.edu/Missions/spitzer.html) · [JWST WISE 0855 trong repo](WISE0855_PRISM.md) · [HST](https://archive.stsci.edu/missions-and-data/hst) · [GLIMPSE](https://irsa.ipac.caltech.edu/data/SPITZER/GLIMPSE/overview.html) · [VIRAC2](https://www.eso.org/rm/api/v1/public/releaseDescriptions/227) · [VISTA](https://www.eso.org/sci/observing/PublicSurveys/sciencePublicSurveys.html) · [Euclid](https://irsa.ipac.caltech.edu/Missions/euclid.html) |
| **Nền bụi ở bước sóng dài** | **AKARI IRC/FIS** và **IRAS/IRIS** khảo sát gần toàn trời, với độ phân giải và bước sóng khác SPHEREx. Phù hợp xem nền phát xạ trên vùng rộng. [AKARI](https://irsa.ipac.caltech.edu/data/AKARI/overview.html) · [IRIS](https://irsa.ipac.caltech.edu/data/IRIS/overview.html) |
| **Ứng viên vật thể Hệ Mặt Trời** | **NEOSSat** có ảnh và trường chụp theo chương trình. **MPC** lưu astrometry đã báo cáo. **JPL Horizons/SB Identification** cung cấp dự báo từ quỹ đạo theo vị trí người quan sát và thời điểm. [NEOSSat/CADC](https://cadcftp.cadc.hia.nrc-cnrc.gc.ca/en/neossat/) · [MPC Data Services](https://data.minorplanetcenter.net/) · [Horizons](https://ssd-api.jpl.nasa.gov/doc/horizons.html) · [SB Identification](https://ssd-api.jpl.nasa.gov/doc/sb_ident.html) |

## Cách đọc hình cầu và tái lập

- Mọi vị trí trên bản đồ là **hướng nhìn trên thiên cầu**. Kích thước hiển thị là kích thước góc; khoảng cách từ Trái Đất không được mã hóa. Phạm vi toàn trời biểu thị thiết kế khảo sát hoặc sản phẩm hợp nhất và có thể chứa vùng thiếu dữ liệu theo từng dải hay epoch.
- Những hộp của Pan-STARRS, SkyMapper, GLIMPSE và VVV/VIRAC2 biểu diễn các giới hạn công bố bằng độ. Chấm gần cực của SPHEREx Deep Survey diễn tả hướng cực hoàng đạo J2000 xấp xỉ. Dùng MOC của IRSA để biết hình dạng vùng sâu. Chấm JWST biểu diễn hướng mục tiêu WISE 0855 theo đề.
- Với các bản phát hành có footprint rời như Euclid và TESS, danh mục trỏ đến trình duyệt bản đồ hoặc kho theo tile/sector. MOC và `s_region` cung cấp cách truy lại hình học khi cần thêm vào quả cầu. [Hướng dẫn MOC của Aladin](https://aladin.cds.unistra.fr/java/FAQ.htx)
- Ảnh sử dụng trong phân tích cần lưu accession/URL, release và calibration, thời điểm và hệ thời gian, WCS, đơn vị, mask, uncertainty và SHA-256 của chính tệp ảnh. Hash truy vấn ở trên chỉ thuộc metadata. Repo lưu FITS thô trong `data/raw/` và các sản phẩm demo có provenance trong `web/data/`. [Manifest hiện tại](../web/data/manifest.json) · [Hợp đồng metadata hiện tại](OBSERVATION_API_CONTRACT.md)

**Bước tiếp theo đề xuất.** Đưa DR1/QR3 vào luồng tìm ảnh và phát ít nhất ba khung thật tương thích theo thời gian trên một mục tiêu. Kiểm vùng phủ, bước sóng, căn chỉnh WCS và metadata của mỗi khung. Sau đó kiểm bốn mục tiêu còn lại và hiển thị rõ khi chỉ đủ hai khung cho A/B hoặc chưa đủ ảnh phù hợp. [Tiêu chí nghiệm thu](OVERHAUL_DISCOVERY.md#milestone-tiếp-theo-đề-xuất)
