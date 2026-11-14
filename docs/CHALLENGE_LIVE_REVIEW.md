# Planet X and SPHEREx | Đối chiếu đề chính thức

Đã mở trực tiếp hai tab **Details** và **Resources** trên cổng NASA Space Apps ngày **14/11/2026**. Đề xếp độ khó **Advanced**, thuộc các chủ đề Astrophysics, Planets & Moons và Software. NASA Space Apps 2026 diễn ra 14–15/11. Cổng sự kiện ghi thời hạn nộp lúc 23:59 ngày 15/11 theo giờ địa phương. [Details](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details) · [Resources](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=resources) · [Lịch sự kiện](https://www.spaceappschallenge.org/2026/)

## Trọng tâm của đề

Web công khai nhận RA và Dec của một vùng trời, rồi phát **chuỗi ảnh SPHEREx của chính vùng đó theo thời gian** để người xem dễ nhận ra điểm sáng dịch chuyển hoặc các thay đổi khác. Đề lấy ví dụ phát hiện Pluto bằng đối chiếu ảnh và nhắc tới đóng góp của người quan sát tình nguyện. SPHEREx khảo sát toàn trời theo chu kỳ khoảng sáu tháng qua 102 dải cận hồng ngoại. Độ phủ và bước sóng có sẵn ở từng thời điểm phụ thuộc vị trí và bản phát hành. [Details](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details) · [IRSA](https://irsa.ipac.caltech.edu/Missions/spherex.html)

| Mục tiêu đề yêu cầu thử | Cách kiểm trong sản phẩm |
| --- | --- |
| Barnard’s Star | Mở vùng, xem thời điểm và dải phổ khả dụng, thử so cặp ảnh. |
| Epsilon Indi B | Phát ba khung DR1 D6 đã kiểm tra. Xem timestamp UTC và FITS từng khung. |
| WISE 0855 | Thử nhập đúng RA `08h55m10.831s`, Dec `−7d14m42.53s` theo đề. Tâm mẫu trong ứng dụng được ngoại suy riêng về epoch quan sát. |
| RW Aurigae | Kiểm ảnh và khả năng đối chiếu biến quang khi thời điểm và dải phù hợp. |
| R Draconis | Kiểm ảnh ở từng thời điểm và trạng thái khi thiếu ảnh cùng dải. |

Mỗi ca ghi truy vấn, release, detector, số khung và trạng thái tải. Cặp hai ảnh hỗ trợ xem kỹ từng epoch, còn trình phát chuỗi giúp đáp ứng yêu cầu xem theo thời gian. Ba khung Epsilon Indi B đã được chạy local. Các ngày **29/04, 01/05 và 07/05/2025 UTC** là ngày chụp trong bộ đã kiểm, với lưới và thang hiển thị chung. Cần kiểm chứng lại các luồng trên đúng commit production. [Danh mục dữ liệu](DATASET_CATALOG.md) · [Receipt DR1](data/spherex-dr1-timeline-smoke.json) · [Checklist lưu tại main](https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/blob/main/Debai.md)

## Các gợi ý tùy chọn và nguồn của đề

Đề gợi ý cập nhật release dễ dàng, khám phá 102 dải, cộng theo từng detector trong sáu detector để cải thiện tín hiệu, tạo phổ, cộng/trừ ảnh, chọn trường nhìn, overlay Gaia hoặc WISE, chia sẻ tọa độ qua URL, hiện metadata như cờ nhiễm, và xem xét Astropy hoặc Aladin. Phần lựa chọn bước sóng trong so sánh cần phân biệt dải detector với bước sóng tại điểm trời đang xem. Ở mỗi pixel, bộ lọc biến thiên tuyến tính có thể cho bước sóng khác. Khi suy luận chuyển động hoặc biến quang, kiểm WCS, bước sóng, mask và chất lượng dữ liệu trước. [Details](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details) · [Trao đổi kỹ thuật của Space Apps Connect](https://github.com/nasa/spaceapps/discussions/1847)

| Nhóm trong tab Resources | Các liên kết đã thấy trực tiếp |
| --- | --- |
| NASA Data & Resources | [NASA/IPAC IRSA SPHEREx](https://irsa.ipac.caltech.edu/Missions/spherex.html) · [Notebook SPHEREx](https://caltech-ipac.github.io/irsa-tutorials/spherex/) · [WiseView](https://byw.tools/wiseview) · [Gaia DR3](https://archive.stsci.edu/missions-and-data/gaia) |
| Space Agency Partner Resources, CSA | [Giới thiệu NEOSSat](https://www.asc-csa.gc.ca/eng/satellites/neossat/) · [CADC](https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/) · [Tutorial NEOSSat](https://github.com/asc-csa/NEOSSAT_Tutorial) · [Dataset NEOSSat](https://data.asc-csa.gc.ca/dataset/neossat) |

Trong lần kiểm tra, tab Resources liệt kê tám mục trên. Đường dữ liệu chính cho chuỗi là **Spectral Images DR1/QR3**, với FITS từ IRSA. DR1 All-Sky Cube có trục bước sóng. [Resources](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=resources) · [Các bản phát hành SPHEREx](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases/) · [DR1](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html)

## Ánh sáng trên cảnh quỹ đạo

Tấm pin cố định của SPHEREx gần như luôn hướng về Mặt Trời khi bay dọc đường ngày–đêm Trái Đất. Trong khảo sát, miệng cụm chắn photon cách hướng Mặt Trời ít nhất 91° và kính nhìn ra xa Trái Đất. Nguồn sáng minh họa dịu có thể chiếu từ phía tấm pin. Việc xoay khi hover phục vụ quan sát mô hình. [JPL Press Kit, Spacecraft](https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/spacecraft/)

## Phát hành và kho dữ liệu

- GitHub bảo vệ `main` và yêu cầu PR cập nhật theo base cùng hai check Python và JavaScript. Vercel theo dõi `main`. Tại lần kiểm tra, tên miền production hiện có trả HTTP 200 và API trả mã commit `66247e3`. Sau merge cần kiểm tra mã commit mới trên production, rồi thử luồng tìm tọa độ, phát chuỗi và so ảnh. [Vercel hiện hành](https://nosleepclub-nasa-spherex.vercel.app/) · [Vercel Git](https://vercel.com/docs/git)
- Danh mục ảnh công khai hiện được gom thành **213 asset, 426 chunk**, với **127.478.741 byte** payload đóng gói trước phần tăng kích thước có thể phát sinh do base64, BSON, index và dữ liệu nhận xét. Atlas công bố **0,5 GB** cho một Free cluster và giới hạn một Free cluster mỗi project. Vercel hiện chỉ có một URI MongoDB dạng sensitive ở production. Việc phân tán thêm cần đích phụ đã được cấp quyền, định tuyến chunk theo manifest, kiểm checksum từng đích và giữ liên tục đường dẫn cũ. [Manifest](../web/api/_data_manifest.json) · [Quy trình lưu trữ](DEPLOYMENT.md) · [Atlas Free cluster limits](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/)
