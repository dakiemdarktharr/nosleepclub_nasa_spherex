# Định hình lại Sky Lab

## Đề bài và khoảng cách của bản hiện tại

**Planet X and SPHEREx** yêu cầu một web công khai để nhập RA/Dec và phát ảnh SPHEREx của cùng một vùng trời theo thời gian, giúp người xem nhận ra thay đổi. Năm mục tiêu dùng để kiểm thử là Barnard’s Star, Epsilon Indi B, WISE 0855, RW Aurigae và R Draconis. Đề gợi ý thêm cộng/trừ ảnh, đổi trường nhìn, phổ, lớp Gaia/WISE, cờ nhiễm và tọa độ trong URL. [Ghi chú đề bài](CHALLENGE.md) · [Details chính thức](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details) · [Bản đăng lại của HackAthlone](https://hackathlone.com/challenges/planet-x-and-spherex).

Ngày 14/11/2026, trang Details và Resources chính thức không mở được từ công cụ tra cứu. Bản đăng lại của sự kiện HackAthlone khớp mục tiêu đã lưu trong repo và liệt kê tám tài nguyên, gồm IRSA, notebook SPHEREx, WiseView, Gaia DR3, CADC và NEOSSat. Trạng thái của một bộ cutout dựng sẵn cho cả năm mục tiêu vẫn chưa được xác nhận. [Resources chính thức](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=resources) · [Tài nguyên HackAthlone](https://hackathlone.com/challenges/planet-x-and-spherex#resources) · [Trao đổi với Space Apps Navigator](https://github.com/nasa/spaceapps/discussions/1847).

| Yêu cầu | Bản hiện tại | Việc cần làm cho bản mới |
| --- | --- | --- |
| Tìm vùng bằng RA/Dec | Có hai định dạng tọa độ, năm mục tiêu mẫu và truy vấn IRSA theo bản dữ liệu, detector, trường nhìn, khoảng ngày. Tiêu đề trang và bộ mẫu chính tập trung vào WISE 0855. | Đưa mục tiêu mẫu và ô nhập tọa độ vào cùng lối vào. Chuyển truy vấn sống sang DR1/QR3 và kiểm lại. |
| Xem vùng thay đổi theo thời gian | Có danh sách lần chụp, bước tới/lùi và nhấp nháy giữa hai ảnh A/B đã tải. Có bằng chứng lịch sử về hai cutout QR2 cho mỗi mục tiêu. | Phát nhiều khung theo thời điểm chụp, có thanh thời gian, tạm dừng và đọc từng khung. Dùng A/B khi chỉ có hai ảnh phù hợp. |
| Hiểu điều đang thay đổi | Ảnh IRSA cùng lưới hiển thị WCS, có cờ pixel và thang tương phản chung. Chưa đăng ký lại theo sao hay kiểm bước sóng ngay tại nguồn. | Hiện thời điểm, detector, bản dữ liệu, dải phổ đã biết và cờ cạnh ảnh. Báo khi thiếu dữ liệu để so sánh ở cùng dải sóng. |
| Kiểm tra và lưu bằng chứng | Có kho kiểm chứng, JSON và đường dẫn FITS. Nhận xét WISE theo phiên khách riêng. Truy vấn IRSA xuất ghi chú theo cặp. | Cho chuyên gia mở metadata mà vẫn giữ vùng và khung đang xem. Chọn dạng chia sẻ theo nhu cầu thực tế. |

[Luồng hiện tại](WORKFLOW_UI.md) · [Explorer và lần kiểm tra năm mục tiêu](SKY_EXPLORER.md) · [Mã phát A/B](../web/explorer.js#L171) · [Trạng thái kiểm định](PRODUCTION_READINESS.md).

Tài liệu IRSA ngày 12/11/2026 xác nhận **DR1 và QR3 đã thay QR2**. DR1 xử lý lại ảnh Survey 1–2. QR3 bao gồm Survey 3–4 và được thiết kế để dùng cùng ảnh DR1. IRSA ghi QR2 đã rời dịch vụ tìm kiếm và còn tải trực tiếp đến tháng 02/2027. Giao diện/API hiện chỉ nhận `qr2` hoặc `qr3`, mặc định `qr2`. Nên kiểm riêng truy vấn DR1/QR3 mới và giữ nhãn QR2 trên các sản phẩm lịch sử. Cube DR1 toàn trời có 102 kênh danh nghĩa. Trình phát cần **Spectral Images** theo từng lần quan sát. [IRSA Data Releases](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-releases/) · [IRSA DR1 Overview](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html) · [API hiện tại](OBSERVATION_API_CONTRACT.md).

## Sáu câu quyết định hướng làm

Bạn có thể trả lời bằng mã câu và vài chữ. Cột cuối là phương án đề xuất để bạn sửa hoặc thay.

| # | Câu hỏi | Phương án đề xuất |
| --- | --- | --- |
| **1. Mục đích và hạn** | Bản đầu phục vụ **nộp hackathon**, **người dùng quan sát lâu dài**, hay **cả hai**? Mốc cứng là lúc nào, ai duyệt và cần giao URL, video hay bản thử nội bộ? | Với hạn hackathon, ưu tiên một quy trình công khai trọn vẹn cho giám khảo và chuẩn bị bộ ảnh thật tải sẵn cho phần demo. |
| **2. Người dùng và việc đầu tiên** | Ai cần dùng tốt trước, người tò mò chưa biết RA/Dec, học sinh/người hướng dẫn, người săn ứng viên nghiệp dư, hay nhà thiên văn? Trong lần đầu, họ phải hoàn thành việc gì để bạn coi là thành công? | Người mới mở một mẫu và phát được ảnh. Người có kinh nghiệm nhập thẳng RA/Dec, đổi bộ lọc và tải bằng chứng. |
| **3. Câu chuyện khoa học** | Bạn muốn dẫn bằng **chuyển động** của Barnard/WISE 0855, **biến quang** của RW Aur/R Dra, **sàng lọc ứng viên** cần người xem lại, hay câu chuyện khác? Mục tiêu nào sẽ lên màn hình đầu tiên? | Chọn mẫu chuyển động sau khi kiểm được chuỗi phù hợp. Dùng các mục tiêu còn lại để khám phá và ghi rõ trạng thái dữ liệu từng vùng. |
| **4. Điều hướng và bản đồ** | Vào web nên gặp **mục tiêu mẫu**, **ô tọa độ** hay **bản đồ 3D** trước? Hai nhóm dùng chung màn hình có phần nâng cao, hay cần hai chế độ riêng? Bạn muốn giữ thao tác nào từ bản đang có? | Một màn hình quan sát, có mục tiêu mẫu và lối nhập tọa độ trực tiếp. Phần nâng cao mở tại chỗ, bản đồ 3D mở qua tab Khám phá. |
| **5. Phạm vi dữ liệu và đo đạc** | Bản đầu cần **chuỗi ảnh SPHEREx**, **thêm Gaia/WISE để đối chiếu**, hay **so sánh nhiều khảo sát**? Trong số các công cụ chuyên gia như metadata và mask, đăng ký sao, phép trừ ảnh, đo vị trí, đường cong ánh sáng, phổ và tải hàng loạt, hai mục nào quan trọng nhất? | Phát ảnh DR1/QR3 theo thời gian, hiện WCS/mask/metadata và tải FITS. Đưa overlay hoặc phép đo vào theo thứ tự bạn chọn. |
| **6. Kết quả và thiết bị** | Người xem cần gửi gì sau khi quan sát? Có thể chọn **link mở lại vùng/khung**, **ảnh/video**, **JSON/CSV/FITS** hoặc **hồ sơ review chung**. Thiết bị, ngôn ngữ, mạng yếu hoặc offline nào là bắt buộc? | Link mở lại truy vấn và các khung đã chọn, kèm JSON/FITS khi cần tái lập. Web dùng được bằng bàn phím và điện thoại, chọn ngôn ngữ mặc định theo người nhận. |

## Câu hỏi chi tiết để chốt phạm vi

### Tìm và xem ảnh

7. Ngoài RA/Dec theo độ và dạng giờ–phút–giây, có cần tìm theo tên thiên thể, chọn trên quả cầu, mở từ link chia sẻ, hay dán danh sách tọa độ? Nếu tìm theo tên, cần hiện nguồn định danh và epoch như thế nào?
8. Trình phát cần tua tốc độ, bước từng khung, chiếu lặp, khóa tương phản, đồng bộ zoom/pan hay nhấp nháy A/B? Bạn muốn chọn các khung vào chuỗi hay để web đề xuất trước? Khi vùng không đủ khung hợp lệ, bạn muốn hiện số khung thật, đổi khoảng ngày hay gợi ý mục tiêu khác?
9. Bạn muốn chọn dữ liệu bằng tên dải dễ hiểu, detector D1–D6, bước sóng tại điểm đang xem, hay cả ba theo mức kinh nghiệm? Cần trường nhìn tối đa, khoảng ngày mặc định hoặc thao tác đánh dấu một vùng con để kiểm tra không?
10. Bản đồ 3D cần dẫn từ **chọn khảo sát → vùng phủ → chọn vị trí → mở ảnh**, hay chủ yếu dùng để học và thuyết trình? Bạn có cần một lớp ảnh nền, đường xích đạo/dải Ngân Hà, mặt cắt theo thời gian, hoặc footprint từng ảnh? [Bản đồ trời thử](sky-atlas.html) · [Danh mục nguồn](DATASET_CATALOG.md).

### Bằng chứng khoa học

11. Khi xếp ảnh, bản đầu cần hiển thị nhanh chung lưới WCS, hay cần đăng ký theo sao tham chiếu và kiểm residual trước khi so sánh? Bạn muốn hệ thống chọn ít ảnh tương thích phổ, hay cho chọn rộng với nhãn rõ mức tương thích?
12. Nếu thêm lớp ngoài SPHEREx, việc nào cần làm trước? Có thể dùng Gaia để đối chiếu vị trí và chuyển động, WISE/NEOWISE cho lịch sử hồng ngoại, ZTF cho biến quang quang học hoặc JWST để đối chiếu phổ của một nguồn. Bạn muốn xem cạnh nhau, xếp chồng hay đo chung? Ai quyết định điều kiện để so được phép đo qua các khảo sát?
13. Bạn muốn công cụ dừng ở quan sát và ghi chú, hay xếp hạng ứng viên để chuyên gia duyệt? Nếu có xếp hạng, cần phân biệt tín hiệu chuyển động, biến quang, vật thể di động, ảnh lỗi và ca chưa đủ bằng chứng ra sao? Ai xem lại ứng viên và bằng chứng nào đủ để gửi cho người khác?
14. Chuyên gia cần tái lập truy vấn, cách đặt ảnh lên cùng lưới hay cả phép đo? Bạn cần lưu kèm những gì trong số danh sách khung, thời điểm, dữ liệu gốc, mask, bước sóng, tham số, phiên bản xử lý và sai số? Có cần xuất bảng theo nhiều mục tiêu hoặc định dạng khớp notebook đang dùng?

### Phát hành và vận hành

15. Có cần tải phiên làm việc lên máy chủ, dùng trên nhiều thiết bị, chia sẻ riêng hoặc cộng tác chuyên gia? Nếu có, ai được xem, sửa, xóa và giữ trong bao lâu? Một link chỉ chứa cấu hình truy vấn có đáp ứng nhu cầu của bạn không?
16. Nên giữ URL và nhận xét của Sky Lab đang chạy hay dùng một preview riêng để thử? Bạn có trang tham chiếu về cách trình bày, tên/thương hiệu cần giữ, yêu cầu tiếng Anh trước khi nộp, hoặc giới hạn chi phí lưu trữ, băng thông và ước lượng số người dùng không?
17. Bạn có thể mời ai thử trước khi chốt? Bạn muốn đo thời gian từ trang đầu đến phát chuỗi, tỷ lệ tự tìm được ảnh, tỷ lệ mở lại đúng truy vấn từ link hay khả năng đọc được nguồn và giới hạn của từng khung?

## Milestone tiếp theo đề xuất

**Từ tọa độ đến trình phát SPHEREx**. Sau khi chốt các câu 1–6, chọn mẫu dẫn và dựng một luồng chung với bản xem trước riêng. Kiểm API DR1/QR3 trước để tránh làm giao diện dựa vào một nguồn đã đổi.

1. Nhập RA/Dec hoặc mở mục tiêu mẫu, phát thử **ít nhất ba khung quan sát thật tương thích của một vùng**, theo thứ tự thời điểm quan sát. Xác minh từng khung có đúng vùng phủ, chất lượng đủ để hiển thị, cùng lưới và thang hiển thị, và có thông tin phổ đủ cho cách so sánh đã chọn. Ghi timestamp, bản phát hành, detector, URL gốc, hash và mask trong bằng chứng. Mỗi lần quan sát được đếm một lần dù có nhiều bản xử lý.
2. Kiểm truy vấn mới cho cả năm mục tiêu. Trường hợp có hai khung phù hợp cho phép nhấp nháy A/B. Trường hợp còn một hoặc không có khung phù hợp báo đúng số lượng và lý do có thể xác định. Nếu IRSA lỗi, bản demo tải sẵn hiện rõ bản phát hành và thời điểm chụp.
3. Mời ba người mới mở mẫu và phát ảnh không cần chỉ chỗ, sau đó hỏi họ ảnh chụp ngày nào và một thay đổi nhìn thấy có thể do đâu. Mời một người có kinh nghiệm tái lập lần xem từ tọa độ và kiểm nguồn dữ liệu từng khung. Thử luồng bằng bàn phím và điện thoại, gồm quay lại và tạm dừng trình phát. Các con số thử người dùng là đề xuất để bạn điều chỉnh.
4. Hiện riêng ảnh quan sát, tọa độ ngoại suy, nguồn giả và kết quả mô hình. Hiển thị chi tiết điều kiện so sánh theo khung. Xác nhận khoa học cần phép đo, sai số và đối chứng thích hợp. [Giới hạn khoa học và vận hành đã ghi](PRODUCTION_READINESS.md).

**Trả lời nhanh**

```text
1. Mục đích / hạn:
2. Người dùng đầu tiên / việc phải làm được:
3. Câu chuyện / mục tiêu dẫn:
4. Mở đầu / cách dùng nâng cao:
5. Nguồn dữ liệu / hai tính năng chuyên gia:
6. Đầu ra / thiết bị / ngôn ngữ:
Điều bắt buộc khác:
```
