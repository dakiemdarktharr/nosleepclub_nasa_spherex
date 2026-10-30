# Chẩn đoán bias và độ phủ trên dữ liệu đã mở — 0.10

Đây là phát triển sau validation 0.9, không phải tập kiểm định ngoài mới. Nguồn và số đo 0.3–0.9 giữ nguyên. Chưa có mô hình hay covariance mới được áp dụng lên WISE 0855.

## Tái hiện và can thiệp

Mã `diagnose_bias.py` khóa tại `a33dd64`. Ba trường w350p35, w090p10, w210m20 đã được mở ở 0.9. Mỗi trường kiểm tra vùng số 1, tọa độ lưới [57.5,5.5], hai ca: S/N mỗi frame 2/đứng yên và S/N 4/dịch [0.6,0.05] pixel. Hai yếu tố cùng thay đổi, nên không gọi đây là ablation riêng S/N. Tái hiện vector gốc khớp trong 1e-5 arcsec.

So bốn point model trên đúng nguồn tiêm cũ, tìm nghiệm từ chín điểm khởi đầu ở trọng số IRLS cuối, bỏ từng exposure (20 lần/ca), và tách tín hiệu tiêm khỏi toàn bộ nền/noise gốc. Đối chứng chỉ có tín hiệu phục hồi sai lệch <0.00002 arcsec. Đối chứng này là một can thiệp oracle có biết nguồn tiêm, không thể dùng để xóa nền quanh nguồn thiên văn chưa biết.

Sau đó tạo 64 noise realizations Gaussian độc lập mỗi ca từ variance gốc, ePSF ghép đúng với fitter, giữ nguyên masks/bố cục và offset. Các ca dùng stream noise ghép cặp; không coi 384 ca là 384 vùng trời độc lập. Không thêm shot noise nguồn; đây là kiểm tra thống kê nội tại, chưa phải mô phỏng detector vật lý.

| Trường | Ca | Sai lệch trên nền gốc | RMS noise Gaussian | Raw ellipse 68% trên noise Gaussian | Đổi vector lớn nhất khi bỏ exposure |
|---|---|---:|---:|---:|---:|
| w090p10 | S/N 2, đứng yên | 1.338″ | 1.943″ | 28/64 | 1.298″ |
| w090p10 | S/N 4, dịch chuyển | 0.544″ | 0.782″ | 39/64 | 0.460″ |
| w210m20 | S/N 2, đứng yên | 1.732″ | 2.095″ | 22/64 | 2.981″ |
| w210m20 | S/N 4, dịch chuyển | 0.444″ | 0.854″ | 36/64 | 0.531″ |
| w350p35 | S/N 2, đứng yên | 2.589″ | 2.291″ | 24/64 | 1.017″ |
| w350p35 | S/N 4, dịch chuyển | 1.192″ | 0.803″ | 39/64 | 0.533″ |

Tỷ lệ noise Gaussian có sai lệch lớn hơn ca w350 gốc là 14/64 và 6/64. Đây là so sánh mô tả, không phải p-value kiểm định nguyên nhân nền. Một realization noise cố định được dùng lại cho nhiều nguồn tiêm có thể tạo các vector lệch cùng hướng. Chưa có bằng chứng đủ để gán lỗi w350 riêng cho blending hay nền khuếch tán.

Không mô hình phức tạp nào cứu đồng đều cả hai ca w350. Ở ca mờ, sai lệch nền phẳng/ePSF cố định 2.589″; nền bậc hai 2.640″; ePSF linh hoạt 2.836″; cả hai 2.829″. Ở ca sáng hơn, các phương án giảm nhẹ 1.192″ xuống 1.134–1.165″. Vùng có ảnh hưởng exposure lớn hơn w350 vẫn có thể phục hồi tốt hơn; một ngưỡng jackknife đơn lẻ chưa giải thích được miscoverage.

## Thử độ cong likelihood

`profile_uncertainty.py`, `run_profile_diagnostics.py` và các numerical controls khóa tại `ecd61de` trước khi so trên cùng 64 realizations. Gauss–Newton dùng JᵀJ; Hessian đầy đủ của objective còn có hạng đạo hàm bậc hai của residual. Đối chứng số học tuyến tính và phi tuyến xác nhận hai cách có thể khác nhau.

Trên ảnh thực nghiệm, Hessian objective ở bước 0.002/0.004 pixel thường không ổn định; chỉ 20–28/64 ca mỗi nhóm có cả hai epoch qua kiểm tra độ nhạy bước. Không áp dụng một ellipse mới bằng cách bỏ im lặng các ca còn lại.

Profile likelihood cho **vector chuyển động** tối ưu lại vị trí đầu khi cố định delta, tránh sai lầm dùng threshold hai bậc tự do cho bốn tọa độ đã cố định. Vẫn giữ trọng số robust cuối; tính chất Wilks chưa được chứng minh ở S/N thấp.

| Trường | S/N 2: GN → profile LR, chứa truth | S/N 4: GN → profile LR, chứa truth |
|---|---:|---:|
| w350p35 | 24/64 → 31/64 | 39/64 → 43/64 |
| w090p10 | 28/64 → 40/64 | 39/64 → 42/64 |
| w210m20 | 22/64 → 34/64 | 36/64 → 39/64 |

Đây là thay cách biểu diễn bất định trên cùng centroid, chưa phải cải thiện vị trí. Ca mờ vẫn thiếu phủ. Bước tiếp theo là kiểm tra độ trơn của ePSF ở biên support và tính xác định của likelihood, rồi hiệu chuẩn/kiểm định trên dữ liệu độc lập. Không chọn ngưỡng mới theo truth w350 để tuyên bố tổng quát.

## Provenance và tái tạo

- `web/data/diagnostics/bias-overview.json` lưu từng vector, covariance, các ca Gaussian, influence, profile modes và hash của report lớn.
- Report lớn và raw FITS ở `data/raw/benchmark/`, không commit; có thể tái tạo từ cache đã ghim trong design 0.9.
- Chạy `python -m scripts.diagnose_bias --fields w350p35 --jackknife --noise-draws 16 --output data/raw/benchmark/bias-w350-development.json`; lặp hai trường so sánh vào `bias-comparison-development.json`.
- Chạy `python -m scripts.diagnose_bias --fields w350p35 w090p10 w210m20 --noise-draws 64 --output data/raw/benchmark/bias-gaussian64-development.json`, rồi `python -m scripts.build_bias_overview`.
- `python -m scripts.run_profile_diagnostics` yêu cầu mã đã commit và chặn ghi đè lượt hoàn tất. Để tái tạo ở môi trường khác, dùng output/cache riêng; không sửa checkpoint đã công bố.

Giới hạn: known-position fitting, matched ePSF, Gaussian conditional noise, fixed registration, shared exposures, vùng được chọn sau khi thấy validation. Không có false-positive rate, completeness tìm kiếm mù hay phát hiện thiên văn mới trong báo cáo này.
