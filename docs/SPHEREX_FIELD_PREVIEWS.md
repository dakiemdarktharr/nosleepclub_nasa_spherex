# Xem toàn khung SPHEREx / SPHEREx detector field previews

Năm điểm vào trong màn hình bầu trời có ảnh xem trước của **toàn khung detector SPHEREx đã chụp**. Mỗi ảnh dùng khung đầu D6 của bộ kiểm tra QR2 đã ghim. Khung lớn giúp định hướng trước khi mở chuỗi cutout quanh tọa độ. Điểm đánh dấu lấy từ tọa độ hướng dẫn của repo qua WCS của ảnh gốc. Dấu này chỉ tâm người dùng muốn xem. Độ sáng từng điểm ảnh trên bản xem trước đã được kéo giãn theo từng khung. [Các khung đã ghim](../web/data/explorer-check/coverage.json) · [Metadata và hash](../web/assets/mission/full-fields/provenance.json)

The five sky entry points have a preview of each **complete measured SPHEREx detector frame**. Each uses the first D6 exposure in the pinned QR2 checks. The wide field shows the surroundings before the user opens a sequence of coordinate-centered cutouts. The marker uses the repository's guide coordinate and the original image WCS. It identifies the intended viewing location. Display intensity uses an independent stretch for each frame. [Pinned frames](../web/data/explorer-check/coverage.json) · [Metadata and hashes](../web/assets/mission/full-fields/provenance.json)

| Điểm xem / Viewing point | Observation ID | UTC | Ảnh / Image |
| --- | --- | --- | --- |
| WISE 0855 | 2025W19_1B_0116_1 | 2025-05-05 16:48:02 | [WebP](../web/assets/mission/full-fields/wise0855.webp) |
| Barnard’s Star | 2025W33_2C_0321_1 | 2025-08-15 20:45:11 | [WebP](../web/assets/mission/full-fields/barnard.webp) |
| Epsilon Indi B | 2025W18_1B_0081_2 | 2025-04-29 01:33:19 | [WebP](../web/assets/mission/full-fields/epsilon.webp) |
| RW Aurigae | 2025W37_2A_0051_1 | 2025-09-11 16:15:33 | [WebP](../web/assets/mission/full-fields/rwaur.webp) |
| R Draconis | 2025W20_2D_0243_1 | 2025-05-16 22:56:23 | [WebP](../web/assets/mission/full-fields/rdra.webp) |

Mỗi khung **2040 × 2040** được gom trung vị 4 × 4 xuống **510 × 510**. Giữ pixel IMAGE hữu hạn nếu không có cờ hoặc chỉ có SOURCE bit 21. Ô cần ít nhất 4 pixel hợp lệ. Ô thiếu dữ liệu có màu xanh sẫm. Giữ nguyên trục detector, lật thứ tự hàng để hiển thị, dùng phân vị 1 và 99 cùng phép kéo giãn asinh. Nền sáng thay đổi theo vị trí trong ảnh detector và các artefact còn thấy được. Đây là tài liệu định hướng trước khi xem các cutout với đơn vị và mức tương phản phù hợp cho chuỗi.

Each **2040 × 2040** frame is median-binned 4 × 4 to **510 × 510**. The display accepts finite IMAGE pixels without flags or with SOURCE bit 21 alone. A binned pixel needs at least 4 valid values. Dark blue denotes unavailable bins. The detector axes are preserved with row order flipped for display, using 1st and 99th percentiles and an asinh stretch. Background and artifacts can vary across detector coordinates. Use the previews for orientation and choose compatible cutouts for a time sequence.

Đầu vào giữ từ byte 0 đến 33.330.239 của từng FITS gốc IRSA, đủ PRIMARY, IMAGE và FLAGS. SHA-256 trong manifest áp dụng cho dải byte đầu vào và cho từng WebP tương ứng. Dữ liệu ảnh gốc thuộc NASA/IPAC IRSA, SPHEREx QR2. [Tài liệu về bản phát hành](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases/)

Input bytes 0 through 33,330,239 from each IRSA FITS contain the complete PRIMARY, IMAGE and FLAGS HDUs. The manifest records hashes of those input bytes and each corresponding WebP. The original observations are from the NASA/IPAC IRSA SPHEREx QR2 release. [Release notes](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases/)
