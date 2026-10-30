# Dữ liệu tham chiếu mới cho phổ và kiểm định

Đã tải một gói nhỏ từ **SPIFF QR2-2026-04-24**, DOI [10.5281/zenodo.19051216](https://zenodo.org/records/19051216), tác giả Jonathan Gagné và cộng sự. Metadata API ghi license **CC-BY-4.0**; [bài báo](https://arxiv.org/abs/2604.22012) mô tả phương pháp trích phổ. Code SPIFF có license riêng; project này chưa cài hoặc chạy code đó.

## Đã lấy và kiểm tra

`scripts/fetch_spiff_reference.py` chỉ tải README, manifest checksum, bảng catalog và template phổ hybrid: tổng **872.724 byte**, không tải gói 6,7 GB hay ảnh/spectrum riêng của nguồn. Đối chiếu size và MD5 do Zenodo công bố, rồi ghi SHA-256 độc lập cho từng tệp. Raw nằm trong `data/raw/external/spiff/`, bị Git bỏ qua. [Receipt công khai](../web/data/external/spiff-reference.json) giữ URL, phiên bản, license, hash và inventory ZIP; không giải nén hoặc thực thi nội dung tải về.

README của phiên bản này ghi 6.003 phổ chất lượng cao và 47 subtype chuẩn trong thư viện. Đây là số do tác giả công bố, không phải số phép thử đã chạy trên web. Template từ M8 đến Y1 và các lớp trọng lực không bao phủ sao lùn rất lạnh như WISE 0855. Tên lớp hay subtype không tạo ra độ chính xác vị trí.

```powershell
.venv/Scripts/python.exe -m scripts.fetch_spiff_reference
```

Lần chạy lại từ chối checksum/version/license khác hoặc ghi đè cache khác. Publisher có thể thay metadata của record; khi hash metadata khác, giữ receipt cũ và xem xét một phiên bản mới thay vì âm thầm cập nhật.

## Cách dùng để cải thiện công cụ

1. Dùng template làm tập phát triển kiểm tra đáp ứng phổ: tích phân SED với response theo vị trí detector; giữ normalization, đơn vị và biến thiên trong band. CWAVE/CBAND đơn lẻ chỉ xấp xỉ hình dạng response, chưa đủ chứng minh hai ảnh đo cùng phổ.
2. Dùng catalog để xây dựng cohort nguồn đỏ có chuyển động đã biết từ phép đo ngoài. Khóa danh sách, epoch, chất lượng truth, chia theo field/exposure/source và tiêu chí trước khi đo ảnh của cohort mới.
3. So một pipeline độc lập, như SPIFF, để phát hiện bất đồng. Kết quả của pipeline khác vẫn có systematic và không tự trở thành truth; phải giữ phương pháp PSF/centroid/nền và dữ liệu đầu vào của từng pipeline.

Chưa có phép thử accuracy mới từ gói này. Template được suy ra từ SPHEREx có thể chia sẻ chính pixel hoặc nguồn với validation. Không dùng template của một nguồn làm prior rồi đánh giá lại chính nguồn/exposure đó như dữ liệu độc lập. Không đổi tên các field đã mở thành holdout.

## Hai điểm phương pháp cần giữ

[Tài liệu IRSA](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html) xác định phép forced photometry chính thức giữ vị trí nguồn cố định và chỉ fit flux; nó không chứng nhận độ chính xác của một phép tự do fit chuyển động. [Mô hình dữ liệu của tác giả tractorjax-spherex](https://tractorjax-spherex.readthedocs.io/en/latest/data_model.html) phân biệt PSF optical QR2 và ePSF QR3 đã chứa pixel response; tích phân pixel lần nữa có thể tạo bias. Đây là nguồn để thiết kế kiểm tra chéo, chưa phải bằng chứng pipeline hiện tại đã sửa toàn bộ bias.
