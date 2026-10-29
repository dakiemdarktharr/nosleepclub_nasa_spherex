# Planet X and SPHEREx — ghi chú đề bài

Nguồn: [Details chính thức](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details), đọc ngày 30/10/2026. Độ khó: **Advanced**.

## Yêu cầu chính

Xây dựng web công khai: nhập tọa độ **Right Ascension (RA)** và **declination (Dec)**, rồi xem chuỗi ảnh SPHEREx của cùng vùng trời theo thời gian như video để nhận ra chuyển động.

## Mục tiêu kiểm thử được đề chỉ định

| Đối tượng | Ghi chú |
| --- | --- |
| Barnard’s Star | Sao |
| Epsilon Indi B | Cặp sao lùn nâu |
| WISE 0855 | RA `08h55m10.831s`, Dec `-7d14m42.53s` |
| RW Aurigae | Sao biến quang |
| R Draconis | Sao biến quang |

## Gợi ý tùy chọn từ đề

- Dễ cập nhật dữ liệu mới; khai thác 102 dải hồng ngoại.
- Cộng hoặc trừ ảnh, chọn trường nhìn, tạo phổ.
- Overlay Gaia/WISE, tọa độ trong URL, metadata và cờ nhiễm.
- Tham khảo Astropy và Aladin/CDS.

## Tài nguyên

Tab [Resources chính thức](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=resources) ghi sẽ có tài nguyên ngày **13/11/2026**. Chưa xác nhận endpoint, định dạng, quyền truy cập hoặc bộ ảnh khả dụng.

Trang cũng nhắc không bắt đầu làm sản phẩm trước khi hackathon diễn ra. Repo hiện chứa tài liệu chuẩn bị.

## Cách nhóm sẽ đánh giá prototype — đề xuất

Các tiêu chí dưới đây do nhóm đề xuất, chưa phải tính năng đã xây dựng:

- Người mới có thể mở một mục tiêu mẫu và hiểu cách so sánh ảnh mà không cần biết FITS.
- Cùng một vùng trời được căn chỉnh giữa các thời điểm; chuyển động trên màn hình phải phân biệt được với sai lệch căn chỉnh.
- Mỗi frame hiển thị thời điểm quan sát, đơn vị, dải phổ và nguồn dữ liệu.
- Giao diện giải thích khi thiếu ảnh, không có vùng phủ hoặc truy vấn không hợp lệ.
- Các dấu hiệu chuyển động/biến quang được trình bày là ứng viên cần kiểm chứng, không tự khẳng định phát hiện thiên thể mới.
