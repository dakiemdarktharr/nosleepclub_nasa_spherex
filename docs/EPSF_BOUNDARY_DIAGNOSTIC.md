# Chẩn đoán biên ePSF: dữ liệu phát triển 0.10

Chẩn đoán này khảo sát liệu phép nội suy ePSF có làm hàm mục tiêu gián đoạn tại mép kernel hay không. Đây là phân tích thăm dò trên trường đã mở, không phải xác nhận thiên văn, đánh giá độ bao phủ độc lập, hay đề xuất thay hiệu chuẩn khoa học.

## Thiết kế và tái lập

```powershell
.venv/Scripts/python.exe -m unittest tests.test_epsf_boundary -v
.venv/Scripts/python.exe -m scripts.diagnose_epsf_boundary
```

Báo cáo được ghi vào `data/raw/benchmark/epsf-boundary-development.json`, một đường dẫn bị Git bỏ qua. Để chạy tập con, dùng ví dụ `--fields w350p35 --snrs 2`. Chương trình ghi hash SHA-256 của mã chẩn đoán, các nguồn frozen, thiết kế, và báo cáo Gaussian gốc; từng trường có đường dẫn và hash của kết quả nguồn. Các URL, hash và phiên bản nguồn khoa học được giữ trong thiết kế và các manifest nguồn đã tham chiếu; không tạo hay thay sản phẩm khoa học.

Ba trường `w350p35`, `w090p10`, `w210m20`, patch 1, sử dụng hai case frozen: nguồn đứng yên SNR 2/frame và nguồn dịch `[0.6, 0.05]` sky pixel SNR 4/frame. Với mỗi case, tái tạo **draw 0** từ seed 20261030 của phép thử Gaussian 64 draw: tín hiệu ghép dùng ePSF nearest, nhiễu Gaussian độc lập theo phương sai native-pixel ban đầu, không có sky gốc và không có source shot noise. Tái fit mỗi epoch như trước; đối chiếu sai lệch vector với bản ghi trước, sai số tối đa cho phép 1e-5 arcsec. Toàn bộ sáu case trong lượt này khớp chính xác ở độ chính xác số được ghi.

Tại vị trí fit gốc, giữ nguyên các pixel hợp lệ, WCS và Jacobian, trọng số IRLS cuối, dữ liệu, phương sai và phép chiếu nuisance gồm nền và các hàng xóm. Hàm mục tiêu là một nửa tổng bình phương residual có trọng số sau khi profile biên độ nguồn; residual đối chiếu với hàm frozen. Đối chứng thay duy nhất template nguồn mục tiêu: đệm 8 pixel bằng không trên mỗi cạnh của mảng ePSF oversampled đã chuẩn hóa rồi spline-filter lại. Vị trí fit và phép chiếu nuisance không được tính lại. Phép đệm thay cả nội suy vùng trong lẫn hỗ trợ vùng ngoài; không phải tái fit hay mô hình vật lý mới đã được kiểm định.

Hessian sử dụng bước sky pixel `0.00025, 0.0005, 0.001, 0.002, 0.004, 0.008, 0.016`, theo công thức scalar sai phân trung tâm độc lập và được so với `profile_uncertainty.hessian`. Đối chứng bậc hai có Hessian biết trước kiểm tra cả đường chéo và thành phần hỗn hợp. Một kernel tổng hợp có cạnh khác không kiểm tra trực tiếp sự gián đoạn và tính liên tục khi đệm. Chương trình tìm giao điểm với biên theo bốn hướng `[1,0]`, `[0,1]`, `[1,1]`, `[1,-1]` trong khoảng ±0.016 sky pixel và lưu tối đa ba giao điểm gần nhất riêng biệt mỗi hướng. Báo cáo lưu tọa độ pixel native, observation ID, cạnh, zone, template và giá trị mục tiêu ở hai phía ±1e-8 sky pixel. Nhiều pixel có thể vượt cùng lúc, vì thế bước nhảy mục tiêu là của toàn epoch, không quy riêng cho một pixel. Đếm giao điểm giữa các hướng không phải số sự kiện độc lập.

## Quan sát của lượt chạy

- Sai số tái tạo residual và khác biệt công thức Hessian đều bằng 0 trong các phép so sánh đã lưu. Đối chứng bậc hai và đối chứng biên tổng hợp đều đạt.
- Mọi mẫu được khảo sát có giá trị cạnh ePSF khác không. Các giá trị tuyệt đối lớn nhất trên cạnh, sau chuẩn hóa của mô hình frozen, nằm khoảng 0.00135–0.00599; đây là giá trị template, không phải flux đo của vật thể.
- 11/12 epoch có ít nhất một giao biên trong khoảng khảo sát theo một trong bốn hướng; epoch còn lại không có giao điểm trong phạm vi đó. Ở mỗi epoch có giao điểm, bước nhảy mục tiêu lớn nhất trong các ví dụ đã lưu nằm khoảng 0.00364–0.0424 đơn vị nửa chi-bình-phương. Đối chứng đệm thay đổi tối đa 1.89e-7 giữa cùng hai vị trí sát biên; giá trị đó bao gồm biến thiên trơn và sai số số học, không phải ước tính chính xác giới hạn bước nhảy.
- Theo tiêu chí tương đối Frobenius của profile hiện có, 5/12 epoch có Hessian gốc thay đổi hơn 5% giữa bước 0.002 và 0.004 sky pixel. Ở cùng vị trí và trọng số, thay đổi của đối chứng đệm tối đa 0.023% trên 12 epoch. Giao biên gần đó không nhất thiết nằm trên các điểm được dùng bởi mọi stencil, nên có trường hợp có giao biên nhưng Hessian tại hai bước này vẫn ổn định.
- Ví dụ `w350p35`, SNR 2, epoch trước: Hxy gốc là -13.549 và +7.251 tương ứng hai bước trên; đối chứng đệm là -10.837 và -10.842. Theo hướng `[1,-1]`, giao biên tại +0.002899 sky pixel cho bước nhảy mục tiêu +0.004524, trong khi đối chứng đệm thay đổi khoảng 9.1e-9 tại cùng hai vị trí. Epoch sau có Hxy gốc -532.461 tại bước 0.002 và -7.227 tại 0.00025; các giao biên gần vị trí fit được ghi trong báo cáo.

## Suy luận và giới hạn

Các phép đo trực tiếp và đối chứng hỗ trợ mạnh kết luận rằng biên nội suy frozen gây ra những bước nhảy hữu hạn trong hàm mục tiêu của các mẫu khảo sát, và có thể làm Hessian sai phân phụ thuộc bước. Chúng không xác định bao nhiêu undercoverage của 64 draw do cơ chế này gây ra; estimator, độ phi tuyến, chọn mode, phương sai, và các giả định khác vẫn có thể đóng góp. Đệm bằng không là can thiệp số học, không xác nhận PSF vật lý, không có kết quả bao phủ mới, không suy rộng ra các trường chưa mở, và không chứng minh nguồn hay chuyển động thiên văn.

Bước tiếp theo là thiết kế, cố định mã và tiêu chí trước một mô hình ứng viên có biên trơn và có nguồn gốc vật lý rõ ràng; sau đó chạy so sánh ghép cặp cùng controls về sai lệch vị trí, độ ổn định tối ưu và độ bao phủ, rồi kiểm định trên trường độc lập chưa mở. Chỉ xem xét promotion nếu các ngưỡng công bố trước đạt, nguồn gốc và mặt nạ được giữ, và giới hạn sai số được nêu rõ.
