# SPHEREx science showcase

Rà soát: **14/11/2026**. Phần nội dung song ngữ VI/EN sau lịch sử SPHEREx. Đây là phần giảng giải về nhiệm vụ, thiết kế và cách đọc dữ liệu; các SVG là sơ đồ do dự án dựng, không phải sản phẩm khoa học hay mô phỏng vật lý.

## Tích hợp

- CSS: `web/spherex-science.css`.
- JS: `web/spherex-science.js`, không dependency, không gọi mạng, không lưu dữ liệu người dùng.
- Điểm gắn: `window.SpherexScience.mount(container)`. Module cũng tự tìm `#spherex-science` khi DOM sẵn sàng. Gọi lại với cùng phần tử không tạo bản sao hoặc listener mới.
- `mount` thay nội dung fallback, chuyển class `about-mission` sang `spherex-science`, đặt heading và `aria-labelledby` của container.
- Ngôn ngữ ban đầu lấy từ `document.documentElement.lang`; nghe `document` event `spherex:language` với `{detail: {language: "vi" | "en"}}`. Khi đổi ngôn ngữ, giữ lựa chọn, slider, details đang mở và focus của control.
- Hàm trả về có `destroy()` để gỡ listener. Dự án hiện dùng một container cố định; không cần gọi khi đổi route.
- Mục lục dùng anchor `#about-story-title` và `#ss-1-*` cho instance thông thường. Router cần giữ người dùng ở trang About khi chọn anchor này.
- Dùng biến theme `--public-text`, `--public-muted`, `--public-panel`, `--public-border`, `--public-accent`. Không phụ thuộc font tải mạng. Các sơ đồ dùng nền tối cố định và màu chữ riêng để giữ tương phản ở cả hai theme.

## Nội dung và thao tác

1. **Ba câu hỏi lớn:** chọn vũ trụ sơ khai / lịch sử thiên hà / băng liên sao. Sơ đồ, phương pháp và giới hạn kết luận đổi theo lựa chọn.
2. **Quỹ đạo và Mặt Trời:** ba trạng thái quỹ đạo cực / hướng an toàn / vùng phủ theo mùa. Phân biệt hướng miệng bộ chắn photon với trục quang học và tấm pin.
3. **Thiết kế:** chọn quang học / chắn photon / tản nhiệt / điện & dữ liệu. Sơ đồ cắt lớp làm sáng hệ thống tương ứng; các chi tiết sâu mở bằng `details`.
4. **Sáu detector và 102 kênh:** chọn một trong sáu dải detector, kéo vị trí nguồn trên LVF. Năm vị trí minh họa nguyên lý, không giả lập exposure hoặc trả một bước sóng hiệu chuẩn. Không dựng đồ thị phổ giả.
5. **Kết quả đã công bố:** phân biệt mốc khảo sát, kết quả quan sát, bài báo và phát hành dữ liệu. Những ví dụ chọn lọc không được gọi là danh sách đầy đủ mọi phát hiện của nhiệm vụ.
6. **Từ photon tới bằng chứng:** đo → hiệu chuẩn → sản phẩm → kiểm chứng. Mở giải thích FITS, wavelength calibration, hạn chế cube DR1 và metadata để tái lập.

Các nội dung quan trọng đều có văn bản ngoài SVG; screen reader nhận mô tả sơ đồ, button có `aria-pressed`, range có label/output/`aria-valuetext`. Nội dung thay đổi có vùng thông báo lịch sự. Không tự động chuyển cảnh, không chạy animation liên tục. Tôn trọng `prefers-reduced-motion`.

## Nguồn và phạm vi khẳng định

| Chủ đề | Nguồn chính đã kiểm tra | Quy tắc diễn giải |
|---|---|---|
| Thiết kế nhiệm vụ, 102 kênh, dải 0,75–5 µm | [Bock et al., The SPHEREx Satellite Mission](https://arxiv.org/abs/2511.02985), [bản xuất bản tại Caltech](https://authors.library.caltech.edu/records/1hhqm-ehm09) | Khảo sát phổ toàn trời; không mô tả là 102 camera hoặc mọi pixel của một ảnh cùng bước sóng. |
| Vũ trụ sơ khai | [Caltech: Origin of the Universe](https://spherex.caltech.edu/page/the-origin-of-the-universe) | Phân bố thiên hà và dịch đỏ giúp kiểm tra mô hình lạm phát; không chụp trực tiếp Big Bang hay nói đã xác định cơ chế lạm phát. |
| Thiên hà và EBL | [Caltech: Origin and History of Galaxies](https://spherex.caltech.edu/page/the-origin-and-history-of-galaxies) | Nền ngoài Ngân Hà và biến thiên không gian; cực hoàng đạo khác cực địa lý. |
| Băng liên sao | [Caltech: Origin of Water](https://spherex.caltech.edu/page/the-origin-of-water-in-planetary-systems) | Phổ hấp thụ nhận diện các phân tử trong băng; không suy ra sự sống. |
| Quỹ đạo | [JPL: Mission overview](https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/) | Khoảng 650 km, 98 phút, một lượt khoảng sáu tháng, bốn lượt trong kế hoạch chính; đây không phải ephemeris trực tiếp. Press kit là tài liệu trước phóng, không lấy ngày phóng dự kiến làm ngày thực tế. |
| Hướng tương đối với Mặt Trời | [JPL: Spacecraft, Cooling Orbit and Orientation](https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/spacecraft/) | **91° áp dụng cho hướng miệng bộ chắn photon, không phải trục kính.** Kính bên trong hơi nghiêng về phía Mặt Trời để phủ toàn trời. Tấm pin gần như luôn hướng về Mặt Trời; kính quan sát ra xa Trái Đất. |
| Quang học, LVF | [Caltech: Instrument](https://spherex.caltech.edu/page/instrument), [Korngut et al., calibration/testing/performance](https://arxiv.org/abs/2603.29835) | Khẩu độ 20 cm, ba gương, hai nhánh qua dichroic, sáu detector với LVF cố định. Không mô phỏng đúng đường tia bằng hình zigzag. Trang Instrument có thông số thiết kế lịch sử; không lấy resolving power cũ để gán cho DR1. |
| Cấu trúc, nhiệt, điện, liên lạc | [JPL: Spacecraft](https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/spacecraft/), [Bock et al.](https://arxiv.org/abs/2511.02985) | Phân biệt ba photon shields và V-groove radiators. Làm lạnh thụ động trong hoạt động bình thường không có nghĩa vệ tinh không cần điện. Tấm pin khoảng 750 W theo thiết kế. Hệ thống có heater cho mục đích khử nhiễm ban đầu; nội dung không khẳng định “không bao giờ dùng heater”. |
| Bản đồ đầu tiên | [JPL, 18/12/2025](https://www.jpl.nasa.gov/news/nasas-spherex-observatory-completes-first-cosmic-map-like-no-other/) | Mốc khảo sát và trực quan hóa; không phải xác nhận tất cả mục tiêu khoa học. |
| 3I/ATLAS | [NASA, 04/02/2026](https://science.nasa.gov/blogs/3iatlas/2026/02/04/nasas-spherex-mission-tracks-brightening-of-interstellar-comet/), [Lisse et al.](https://arxiv.org/abs/2601.06759) | Quan sát tháng 12/2025, hoạt động sau cận nhật và bụi/khí trong coma. Gắn nhãn “kết quả quan sát”, không biến nó thành nghiên cứu sự sống. |
| Băng/PAH | [Hora et al., ApJ 1001, 165](https://authors.library.caltech.edu/records/ba2ay-z4658), [preprint](https://arxiv.org/abs/2603.12390) | Bản đồ Cygnus X và North America Nebula; công bố 15/04/2026. Phân biệt màu giả gán cho phân tử với màu mắt người nhìn thấy. |
| Sao lùn nâu | [NASA, 08/10/2026](https://www.nasa.gov/missions/spherex/nasas-spherex-telescope-sees-menagerie-of-brown-dwarfs/), [Rustamkulov et al.](https://arxiv.org/abs/2607.00543) | Mẫu 37 sao lùn nâu và đối chiếu mô hình khí quyển. 08/10 là ngày NASA giới thiệu nghiên cứu, không gán là ngày công bố bài báo. |
| Pipeline | [Akeson et al.](https://arxiv.org/abs/2511.15823), [Cukierman et al.](https://arxiv.org/abs/2603.25790) | Hiệu chuẩn, map making, foreground và sai số hệ thống là phần của nghiên cứu; blink ảnh chỉ hỗ trợ quan sát. |
| DR1 hiện hành | [IRSA DR1 overview](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html), [IRSA data products](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/), [Explanatory Supplement](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf) | DR1 tháng 11/2026, dùng ảnh xử lý lại cùng QR3. WCS-WAVE cho visualization; CWAVE/CBAND cho science. Cube kênh 51/52 trống, có stripes, đã trừ ZODI; spectral IMAGE chưa trừ ZODI. HiPS PNG không thay FITS phân tích. |

Không nêu catalog tương lai là đã phát hành. Không đưa các ảnh “first light” chưa hiệu chuẩn vào danh sách dữ liệu đủ dùng cho khoa học. Các kết quả nghiên cứu có link tới bài báo hoặc bản author repository, không chỉ bài truyền thông.

## Kiểm tra

Chạy Python Playwright từ `.venv/Scripts/python.exe`, Chromium, với harness cục bộ riêng dưới `data/raw/science-showcase-review/` (ignored).

- Desktop 1366 px, mobile 390 px và 320 px.
- Bấm toàn bộ 3 mục tiêu, 3 trạng thái quỹ đạo, 4 hệ thống, 6 detector; kiểm tra chỉ một nút của mỗi nhóm có `aria-pressed=true`.
- Slider dùng phím Home/ArrowRight, output và `aria-valuetext` khớp.
- VI → EN → VI giữ detector, range, details mở.
- Dark/light, không overflow ngang, không JavaScript error; mount lần hai không nhân bản.
- Kiểm tra bounding box chữ trong SVG, ảnh chụp để đối chiếu trực quan ở desktop/mobile.
- Bằng chứng: `data/raw/science-showcase-review/results.json`, `orbit-1366-light.png`, `orbit-390-dark.png`, các ảnh toàn trang và các lượt kiểm tra bổ sung cùng thư mục.

Kiểm thử module độc lập không thay thế smoke test router/trang About sau tích hợp. Root phụ trách kiểm thử cùng site, các anchor và các thay đổi khác trước phát hành.

## Ranh giới và việc tiếp theo

- Sơ đồ thuật toán giảng giải không khẳng định kích thước, góc chi tiết, vị trí linh kiện hay công suất tức thời đúng với spacecraft thật.
- Không đo learning outcome chỉ từ việc control hoạt động; cần quan sát người học hiểu sự khác nhau giữa shield/kính, thời gian/bước sóng và ảnh đẹp/số đo.
- Bước tiếp theo: thử một lượt đọc–thao tác–giải thích với từng nhóm tuổi, kiểm tra họ giải thích được vì sao hai ảnh khác nhau chưa chắc thiên thể biến đổi; thêm bài tập bằng dữ liệu thật ở nền tảng học khi nội dung được duyệt.
