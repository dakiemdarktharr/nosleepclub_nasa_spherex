# Research để tăng độ tin cậy và hiệu quả của Sky Lab

Ngày đọc: 30/10/2026. CoChat được dùng để tìm paper và lấy nội dung; các kết quả không liên quan được bỏ qua. CoChat chỉ trả abstract của ARES, nên đã đọc thêm bản arXiv công khai. SMDET-1 có full text qua CoChat. Zotero không xuất hiện trong công cụ hoặc kết quả tìm plugin của phiên này; chưa tạo/sửa thư viện Zotero. Có thể nhập [references.bib](references.bib) vào Zotero.

## Những hướng có căn cứ

**Frame Gaia và kiểm tra biến dạng.** [Libralato, Bedin & Burgasser, ARES](https://app.cochat.ai/from/chatgpt/fetch/papers/10.1051/0004-6361/202557737), đọc thêm [full text arXiv](https://arxiv.org/pdf/2512.08533), dùng ePSF trên ảnh native, Gaia đã lan truyền và kiểm tra geometric distortion; ngân sách sai số có cả phần nguồn mục tiêu và transformation. Đây là căn cứ để kiểm tra local translation/affine và covariance calibration riêng. Không chuyển độ chính xác HST trong paper sang SPHEREx. Pipeline hiện đã làm bước Gaia/CV; điều kiện màu, PSF và noise khác HST vẫn phải đo riêng.

**Blending cần được xử lý trước khi nâng độ tin cậy.** [Mã nguồn pipeline chính thức SPHEREx](https://github.com/Caltech-IPAC/spherex-pipelines) có sử dụng Tractor và fork `tractor-spherex`. Điều này gợi ý ưu tiên forward model nhiều nguồn trên pixel gốc, thay vì chỉ trừ template hoặc tăng ngưỡng score. Đây là đề xuất phát triển của nhóm từ nguồn tham khảo và kết quả injection, chưa phải một module Tractor đã được tích hợp vào demo. Cần kiểm tra license, cấu trúc input/PSF và phạm vi dependency trước khi chọn phần mềm.

**Vision model cho chuỗi ảnh có ví dụ thực tế.** [Meisner et al. 2026, SMDET-1](https://app.cochat.ai/from/chatgpt/fetch/papers/10.3847/1538-3881/ae8e73) mô tả phát hiện nguồn chuyển động bằng recurrent CNN trên unWISE time series, huấn luyện bằng nguồn giả và kiểm tra trực quan các ứng viên xếp hạng cao. Paper còn cho thấy vai trò của nhiễu trộn và xác minh qua dữ liệu có độ phân giải tốt hơn. Hướng này phù hợp mục tiêu “highlight rồi chuyển người duyệt”. Tuy nhiên unWISE W1/W2 nhiều epoch khác SPHEREx có PSF và phổ thay đổi; chưa thể coi một model huấn luyện trên WISE là model đã được kiểm chứng cho SPHEREx.

## Áp dụng vào sản phẩm hiện tại

1. **Đã thực hiện:** mở trường 0,32°, quality gate Gaia, lan truyền covariance, tách sao training/heldout, kiểm tra đổi tập sao và bỏ từng sao; cache centroid để không lặp lại khoảng 1.700 fit sao khi chỉ sửa phần báo cáo/kiểm chứng.
2. **Ưu tiên kế tiếp:** fit chung mục tiêu + nguồn nền và kiểm tra đáp ứng phổ đầy đủ. Injection hiện cho thấy bias nền lớn hơn một số sai số có điều kiện; thêm CNN ngay chưa giải quyết được nguyên nhân đó.
3. **Benchmark trước model:** dùng mask, variance, PSF, wavelength/bandwidth cùng chuỗi ảnh. Tiêm nhiều tốc độ/hướng/độ sáng trên các vùng trời tách biệt; chia train/validation/test theo vùng và nguồn gốc ảnh, không chia ngẫu nhiên các biến thể trên cùng nền. Giữ nguồn đứng yên, nền thật và trường crowded như negative controls; báo cả precision/recovery theo độ sáng và độ dịch chuyển.
4. **Luồng review:** model tạo score/segmentation để ưu tiên vùng xem; bằng chứng vẫn có ảnh gốc, mask, epoch, phổ, centroid/covariance và provenance. So vision model với baseline xử lý ảnh; người duyệt quyết định. Chưa có model được huấn luyện hoặc chạy inference trong bản này.
5. **Hiệu quả web:** tiếp tục tiền xử lý khoa học trên Python, cache theo hash và chỉ phục vụ sản phẩm nhỏ cho trình duyệt. Chọn cách chạy model trên trình duyệt hay backend sau khi có benchmark về accuracy/latency/memory; không đánh đổi sai số khoa học để demo chạy nhanh.

Schema và calibration đọc trực tiếp từ nguồn: [Gaia DR3 tại AIP/DPAC](https://gaia.aip.de/metadata/gaiadr3/gaia_source/), [IRSA data products/ePSF](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/), [cutout API](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/). Các quality cut trong code là cấu hình đã khai báo của phép thử, không phải cam kết rằng mọi nguồn qua cut đều không có blending hoặc binary.

Giả thuyết cần kiểm tra tiếp: SED cực đỏ, gradient bước sóng theo pixel và hướng detector có thể ảnh hưởng photocentre khác với tập sao Gaia. Đây chưa phải nguyên nhân đã xác minh của chênh vector; nên kiểm tra residual theo màu, bước sóng và orientation trong mô hình nhiều nguồn.
