# WISE 0855: QR3, CatWISE và ePSF — kiểm chứng 0.5.0

Ngày truy vấn: 2026-10-30. Kết quả: **có tiến bộ ở cấu hình phổ rộng, chưa đạt gate thay phương pháp mặc định**. Giữ các sản phẩm Gaia 0.3.0 và phép đo 3,29″ ± 0,52″ có điều kiện; không biến thí nghiệm mới thành xác nhận chuyển động.

## QR3/QR2: so độ phủ, chưa có cặp ảnh cùng exposure

[IRSA Data Access](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/) cung cấp QR2 và QR3 qua SIA2, TAP và cutout. Truy vấn SIA `COLLECTION=spherex_qr3` với vòng 0,05° quanh RA 133,76037473328523°, Dec −7,242149767967145° trả về **0 hàng**. TAP trên `spherex.artifact`/`spherex.plane`, footprint chứa đúng tọa độ và URI thuộc QR3, cũng trả về **0 hàng**. Không có ảnh D6 QR3 hoặc cặp cùng observation ID để đo chênh QR2/QR3 tại điểm này trong snapshot truy vấn.

Đây là giới hạn độ phủ tại tọa độ và thời điểm truy vấn, không có nghĩa QR3 chưa được phát hành hoặc không tồn tại trên toàn bầu trời. Không suy ra QR3 tốt/xấu hơn từ kết quả rỗng. Không tạo ảnh QR3 giả. Thử nghiệm dưới đây tiếp tục dùng đúng **20 exposure QR2** của bản trước, chia phổ rộng 10 ảnh/epoch và phổ chặt 2 ảnh/epoch. Hai cấu hình chia sẻ dữ liệu, không phải hai phát hiện độc lập.

URL, ADQL, số hàng và SHA-256 của cả hai câu trả lời được lưu trong [protocol.json](../web/data/release/protocol.json). FITS thô/câu trả lời đầy đủ ở cache bỏ qua Git; script có thể tải lại để kiểm tra.

## Catalog hồng ngoại có hiệu chỉnh vị trí

Truy vấn CatWISE2020 trong bán kính 0,30°, W2<17 và S/N≥5: **5.078 nguồn**. Áp dụng điều kiện đã khóa: W2≤16, S/N≥10, reduced χ² W2≤2, artifact `00`, chuyển động ≤0,3″/năm. Nguồn không ghép Gaia cần sai số vị trí dự báo năm 2026≤1″, với floor chẩn đoán 0,1″. Kết quả **1.783 nguồn**, trong đó **508** có đối chiếu Gaia đạt chất lượng trong 2″ tại epoch catalog; 1.275 nguồn còn lại dùng CatWISE.

[Định nghĩa CatWISE chính thức](https://irsa.ipac.caltech.edu/data/WISE/CatWISE/gator_docs/catwise_colDescriptions.html) nêu sai lệch hệ thống theo tile; [bảng hiệu chỉnh](https://irsa.ipac.caltech.edu/data/WISE/CatWISE/gator_docs/CatWISE2020_Table1_20201012.tbl) quy định **cộng** offset vào giá trị catalog. Đã lấy tile từ 8 ký tự đầu `source_id`, hiệu chỉnh vị trí và proper motion, dùng `ra_pm/dec_pm` tại MJD 57170, đơn vị proper motion arcsec/năm và hệ số cos(Dec) khi đổi góc RA. Đơn vị được kiểm tra từ TAP_SCHEMA và kiểm thử riêng.

Nguồn ghép Gaia dùng propagation proper motion/parallax/covariance của triển khai trước; nguồn CatWISE đơn lẻ dùng chuyển động tuyến tính, chưa có parallax. Ghép catalog ở đây vẫn là ghép gần nhất có quality gate, chưa là đối sánh xác suất. Tâm nguồn quang học/IR có thể khác nhau. Sai số vị trí catalog chưa được truyền vào covariance của phép thử centroid. Không dùng độ sáng W2 để ép flux SPHEREx; flux tự do riêng từng ảnh. Catalog IR cũng có thể thiếu nguồn mờ/thiên hà mở rộng.

## Ba mô hình và kiểm tra ePSF

1. `single_nearest`: mục tiêu + mặt phẳng nền, ePSF zone gần nhất, làm baseline.
2. `ir_nearest`: thêm nguồn IR trong 11 pixel lưới trời quanh vùng fit, ePSF gần nhất.
3. `ir_bilinear`: cùng catalog và mô hình, nội suy song tuyến tính bốn zone ePSF, chuẩn hóa từng zone trước khi trộn.

[Notebook ePSF của IRSA](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/) khuyến nghị ePSF mới và cho phép dùng calibration này cho ảnh QR2 cũ. Bản demo đã dùng tệp D6 `cal-epsf-v1-2026-191` từ milestone trước. **Không phải vừa thay PSF cũ bằng ePSF lần đầu.** Nội suy bốn zone là thử nghiệm riêng, không gọi là phương pháp đã được IRSA xác nhận. Kiểm thử số kiểm tra normalization, giá trị trộn và tính liên tục; chưa chứng minh đây là ePSF vật lý chính xác hơn tại mọi vị trí.

Cả ba mô hình dùng cùng pixel gốc, cờ lỗi, noise map, cửa sổ fit và solver đa khởi tạo. SVD khử biên độ nguồn nền và mặt phẳng tuyến tính; centroid mục tiêu tự do theo từng epoch, không ép theo vector Luhman. Frame translation giữ nguyên phép căn chỉnh Gaia 0.3.0; **chưa fit lại sao tham chiếu bằng ePSF nội suy**, nên chưa phải hiệu chuẩn astrometry nhất quán cho toàn bộ mô hình mới.

## Khóa trước khi thử 30 vùng mới

Checkpoint Git **`581de3342788563226368e567e86c413f29e0d0b`** được tạo trước các fit mục tiêu và injection. SHA-256 protocol: **`79803094b4aeee039e589f8b3ceb3af5fcfbcc61bd929c89cc2ed26fbf51fac1`**. Protocol khóa code của sáu module, dữ liệu, calibration, catalog, solver, gate và 30 vị trí. Không thay mã/rules sau khi khóa; kết quả kiểm tra lại hash trước khi chạy.

Chọn vị trí chỉ bằng hình học và mặt nạ hợp lệ: giữa các tâm mới≥20 pixel, cách các vị trí cũ/mục tiêu≥20 pixel, mỗi stamp có≥100 pixel gốc hợp lệ ở mọi exposure. Đây là **30 vùng nhỏ trong cùng một trường**, không phải 30 trường trời độc lập. Các phép thử cũ không được dùng lại như heldout mới.

30 vùng × hai độ sáng (0,5×/1×) × hai vector thật (đứng yên/[0,6;0,05] pixel) × hai họ ePSF tiêm (gần nhất/nội suy) × ba mô hình × hai cấu hình phổ = **1.440 phép phục hồi**, tương ứng 2.880 fit centroid epoch. Thêm bootstrap noise 128 lượt/epoch/mô hình/cấu hình cho mục tiêu thật. Hai họ ePSF tiêm kiểm tra một loại mismatch, vẫn chưa là PSF vật lý độc lập hay coverage mô phỏng đầy đủ. Chưa thêm shot noise nguồn; các lượt tiêm và cấu hình chia sẻ nền/exposure.

Gate khóa trước: cả hai độ sáng, cả hai ePSF tiêm, cả hai cấu hình phổ phải giảm paired RMSE và không tăng lỗi/biên. Không chọn mô hình bằng độ gần dự báo chuyển động ngoài. Tập 30 vùng đã mở sau thí nghiệm này và không còn là tập chưa xem cho lần tiếp theo.

Một lượt chạy broad song song strict bị lỗi cấp phát bộ nhớ sau vùng thứ bảy. Đã chạy lại **toàn bộ broad tuần tự, cùng code/protocol**, không bỏ vùng hoặc đổi điều kiện. Hai tệp kết quả cuối đều có đủ 720 record, không chọn kết quả từ lượt dở dang.

## Kết quả: tiến bộ cục bộ, chưa chứng minh cải thiện ổn định

Bảng này dùng nguồn tiêm ePSF gần nhất và mô hình mới `ir_bilinear`. Đơn vị RMS là arcsec. Cột ghép cặp chỉ gồm lượt cả hai phương pháp cùng hợp lệ; cột mọi fit mới giữ cả các fit được cứu khỏi lỗi/biên cũ.

| Phổ / độ sáng | RMS cũ → mới trên cặp chung | Cặp chung | Fit hợp lệ cũ → mới | RMS mọi fit mới | Trong ellipse noise 68% |
|---|---:|---:|---:|---:|---:|
| Rộng / 0,5× | 3,133 → 1,980 | 50/60 | 50/60 → 60/60 | 2,413 | 28/60 |
| Rộng / 1× | 0,622 → 0,607 | 52/60 | 52/60 → 60/60 | 0,616 | 41/60 |
| Chặt / 0,5× | 3,976 → 3,529 | 49/60 | 50/60 → 59/60 | 4,291 | 28/60 |
| Chặt / 1× | 1,184 → 1,202 | 52/60 | 52/60 → 60/60 | 2,126 | 38/60 |

Ở phổ rộng/0,5×, IR+nội suy giảm paired RMSE điểm ước lượng **36,8%**, nhưng bootstrap hậu kiểm 2.000 lượt **theo vùng không gian**, chỉ các cặp cùng hợp lệ, cho khoảng chẩn đoán 95% **[−31,4%; +64,2%]**. Phổ rộng/1× giảm 2,49%, khoảng **[−3,13%; +7,30%]**. Các khoảng vẫn chứa không cải thiện; không coi đó là phép kiểm định xác nhận.

Khi tiêm bằng ePSF nội suy, phổ rộng có paired RMSE 3,144→1,981″ ở 0,5× và 0,624→0,600″ ở 1×; phổ chặt/1× vẫn xấu hơn. Mô hình IR+ePSF gần nhất cũng không qua gate ở phổ chặt/1×. **Không mô hình nào qua toàn bộ gate.**

Coverage ở nguồn mờ chỉ khoảng 45–47% cho ellipse dự kiến 68%, là bằng chứng noise-only covariance chưa mô tả tốt toàn bộ sai lệch. Bootstrap theo vùng không khử tương quan giữa exposure hoặc bias chung của một trường. Không công bố completeness, false-positive rate, độ tin cậy Gaussian hoặc một sai số hệ thống tổng đã được hiệu chuẩn.

Mục tiêu thật với phổ rộng: IR+nội suy cho vector **Đông −3,187″, Bắc +0,224″**, độ dài **3,195″**, σ noise chiếu vector **0,742″**. Đây là kết quả thử nghiệm có điều kiện; không so trực tiếp σ noise này với σ tổng 0,52″ của bản Gaia. Nó không tự xác nhận chuyển động, không tách proper motion/thị sai và chưa giải quyết chênh với dự báo ngoài.

## Sản phẩm và tái tạo

- [Protocol đã khóa](../web/data/release/protocol.json), [broad](../web/data/release/broad.json), [strict](../web/data/release/strict.json).
- [Bootstrap ghép cặp và toàn bộ group](../web/data/release/summary.json); [payload UI nhỏ](../web/data/release/overview.json).
- UI có bộ lọc phổ/họ nguồn tiêm, số fit lỗi, RMS mọi fit mới, bản đồ 30 tâm kiểm thử và tải JSON. Giữ nguồn thật tách khỏi hình minh họa Canva.

```powershell
python -m scripts.prepare_release_data
# Chỉ khi tạo protocol lần đầu, trước mọi thử nghiệm:
python -m scripts.release_analysis --lock
# Với protocol đã có trong repo, script sẽ kiểm tra hash rồi dùng lại:
python -m scripts.release_analysis --configuration broad
python -m scripts.release_analysis --configuration strict
python -m scripts.summarize_release
python -m unittest discover -s tests -v
```

Chạy broad và strict tuần tự trên máy ít bộ nhớ. Cần cache Gaia/QR2 của các milestone trước. `--lock` từ chối ghi đè protocol có sẵn. Muốn phát triển mô hình mới phải tạo protocol mới, ghi rõ thay đổi và dùng tập kiểm chứng chưa mở; không sửa kết quả đã khóa để làm đẹp.

## Milestone tiếp theo

Ưu tiên **hiệu chuẩn covariance và mô hình cảnh nhất quán**: fit lại sao tham chiếu với cùng ePSF, kiểm tra residual theo vị trí/màu/mật độ nguồn; mô hình hóa bất định tọa độ hàng xóm và nền ảnh trước khi tăng độ tin cậy. Dùng các vùng đã mở để phát triển, không tiếp tục dùng chúng làm heldout mới.

Khóa cấu hình trước tập mới ở nhiều trường trời, thêm PSF perturbation không trùng họ fit và noise nguồn theo calibration/đơn vị đã xác minh. Báo cả bias, paired RMSE, fit lỗi và coverage theo độ sáng; yêu cầu cải thiện ổn định, không chỉ một điểm ước lượng tốt. Khi QR3 phủ đúng exposure, thực hiện đối chiếu cùng ảnh trước khi gộp phiên bản. Epoch thứ ba/dữ liệu độc lập là bước sau để phân biệt chuyển động riêng và thị sai.
