# Replay hậu kiểm các mode WISE 0855

Đây là diagnostic **post hoc** sau khi đã xem kết quả development; không phải
kiểm định định trước, validation độc lập hay bằng chứng phát hiện thiên thể.
Chỉ tính lại profile tuyến tính tại hai mode đã lưu của epoch `strict/after`,
với đúng pixel, offset, nuisance, spectral coefficient và trọng số IRLS cuối
của từng nhánh. Không tối ưu lại vị trí, không chạy Monte Carlo và không mở
trường mới. Mọi độ lệch dưới đây là mode thứ hai trừ mode có χ² thấp nhất
**trong cùng một nhánh**; hai nhánh có thứ tự vị trí mode khác nhau.

Checkpoint nguồn SHA-256
`a5bffe162ae8ccd88a6fc5311d1e8ddc279c56092b072a782652da5a7f1cfd0a`,
protocol commit `cfb9d6a`. [Bảng JSON](../web/data/linked-flux/mode-diagnostics.json)
giữ hash design, source và input, URL/hash hai exposure, tọa độ native, đủ
giá trị không làm tròn và kiểm tra replay. Script từ chối xuất kết quả nếu
không replay đúng chi phí hay flux theo tolerance tương đối 1e−7 và tuyệt đối
1e−8. Trên runtime hiện tại, chênh lệch được kiểm tra của cả χ², amplitude,
flux, error và weighted residual tại điểm đã lưu đều bằng **0**; χ² của cả
hai mode cũng khớp đúng đến giá trị lưu.

| Nhánh | Mode tốt nhất (sky pixel x,y) | Mode cạnh tranh (x,y) | Δχ² weighted tổng |
|---|---:|---:|---:|
| independent | (32,381675; 31,470075) | (32,532657; 31,883726) | +0,037476 |
| shared R7 68 α=0 | (32,481646; 31,844229) | (32,405766; 31,531498) | +0,568008 |

Đóng góp vào Δχ² weighted có dấu ngược nhau:

| Exposure | independent | shared R7 68 α=0 |
|---|---:|---:|
| 2026W17_1B_0507_3 | +0,554247 | −0,283609 |
| 2026W17_1B_0634_1 | −0,516770 | +0,851617 |

Trong nhánh independent, hai phần đóng góp gần triệt tiêu; trong shared,
0634_1 có phần đóng góp lớn hơn về trị tuyệt đối. Từng amplitude independent
được profile riêng, còn amplitude shared được profile bằng **cả hai exposure**;
do đó bảng shared không phải hai phép đo độc lập và không xác định exposure
nào gây ra sự đa mode. Đây là so sánh chi phí tại các vị trí đã lưu, không
đo hiệu ứng nhân quả khi bỏ exposure hay thay model.

Ở independent, tỷ lệ chuẩn bình phương của template nguồn còn lại sau phép
chiếu nuisance có trọng số giảm từ 0,3813 xuống 0,0826 cho 0507_3 và từ
0,5135 xuống 0,1636 cho 0634_1 khi chuyển sang mode cạnh tranh. Flux profile
tăng từ 399,6 lên 792,2 µJy và từ 722,7 lên 1368,2 µJy; tất cả còn dương.
Đây là dấu hiệu vị trí và flux nhạy với span nuisance, không chứng minh một
hàng xóm cụ thể hoặc ePSF là nguyên nhân. SNR trong JSON là SNR amplitude có
điều kiện tại vị trí cố định; hai SNR shared phản ánh cùng một tham số flux và
không phải hai bằng chứng phát hiện riêng.

Mỗi exposure giữ ba template catalog trong nuisance. Entry
`J085501.95-071428.2` có vị trí mô hình cách hai mode independent khoảng
0,735 và 0,322 sky-grid pixel; khoảng cách tại hai mode shared tương ứng 0,386
và 0,670 pixel. Quan hệ gần nhau của các cột thiết kế phù hợp với việc tỷ lệ
information sau chiếu thấp hơn tại mode gần entry này. Nó không xác định entry
là một thiên thể tách biệt, không chứng minh nguyên nhân đa mode và không
thay thế một phép thử ablation hay dữ liệu độc lập.

Với bán kính core 2,5 pixel native, cả bốn vị trí của mỗi nhánh có 100% pixel
core hình học được chọn, và không có pixel core mang FULLSAMPLE; SOURCE xuất
hiện trong toàn core. RMS residual/error gốc trong core khoảng 0,80–0,96 cho
0507_3 và 1,17–1,22 cho 0634_1. Mask core đầy đủ không loại trừ sai lệch
nền, neighbor hoặc ePSF; RMS là mô tả trên cùng dữ liệu đã chọn, không phải
kiểm định độc lập.

Hai zone ePSF QR3 là 312 và 291: `NSTAR` tương ứng 433 và 414,
`NEFF_MEAN` 5,097 và 5,083, `CWAVE` 4,5832 và 4,6112 µm. Tỷ phần giá trị âm
trên tổng trị tuyệt đối của **bảng thô** là 0,463% và 0,361%; centroid có dấu
của bảng tương ứng (−0,0720; −0,0174) và (−0,0913; −0,0163) native pixel.
Các centroid đó là thống kê của bảng có dấu, không phải correction hay sai
lệch vật lý được đo. Bảng native sau nội suy/chuẩn hóa có tổng có dấu bằng 1
trên toàn support hữu hạn; chuẩn thô trước chia tổng và phần được mask chọn
được lưu riêng theo mode. Chưa xác minh PSF wings, màu, SAPM hay chênh lệch
giữa QR3 ePSF và ảnh QR2.

Covariance profile-H và Gauss–Newton tại một mode là curvature cục bộ theo
trọng số cuối; chúng không tích phân xác suất qua các mode cạnh tranh, không
gồm các hệ thống chung và chưa có coverage được hiệu chuẩn. Không có căn cứ
từ diagnostic này để gọi các mode là hai nguồn thiên văn, kết luận vị trí nào
đúng hơn, thay measurement cũ hoặc nâng model lên production.
