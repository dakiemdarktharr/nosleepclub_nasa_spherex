# Đối chứng phổ: sửa zero crossing và giữ mọi lượt thử

V1 khóa ở `b3eb94c` đã dừng trước khi xuất kết quả. Lượt thứ tư, Cent kênh 2,
dịch −0,0064 µm, có một thùy dương rất nhỏ làm tỉ số vị trí nghiệm đổi dấu
làm tròn thành 1. Tính chiều dài thùy còn lại bằng `h*(1-fraction)` đã thành
0 và bị guard từ chối. [Receipt lỗi](evidence/0.10/spectral-reference-b3eb94c-aborted.json)
giữ đầu vào tái hiện; code và design V1 được giữ nguyên.

V2 dùng kernel mới `spectral_bandpass_v2.py`, tránh phép trừ làm mất thùy nhỏ,
giữ cả dấu và trọng số tuyệt đối. Không clip response hoặc flux, không bỏ
giới hạn hỗ trợ và không nới test. Runner mới giữ riêng `numerical_failure`,
`partial_only` và `full_support` cho đủ 102 lượt; lỗi số học không trở thành
flux bằng 0 hoặc bị bỏ khỏi mẫu số.

Trong khi sửa lỗi, specialist đã chạy preflight số học trên cùng 102 điều
kiện development: không còn exception và cả 102 chỉ có hỗ trợ một phần. Kết
quả này đã được xem **trước** commit design V2. Khóa V2 vì tính tái lập của
bản phát hành; không gọi nó là thử nghiệm chưa xem trước, kiểm định độc lập
hoặc bằng chứng ngoài mẫu. Ba mươi trường triển vọng vẫn chưa được mở.

Mọi lựa chọn vật lý, kênh, độ dịch và giới hạn diễn giải của
[protocol V1](SPECTRAL_REFERENCE_PROTOCOL.md) giữ nguyên. Đặc biệt, photon
weighting chưa xác minh là quy ước calibration SPHEREx; nominal response R7
chưa ghép mỗi pixel QR2. Đây không phải phổ truth, astrometric validation,
độ chính xác đã tăng hay chứng cứ để fit WISE bằng covariance cũ.

```powershell
.venv/Scripts/python.exe -B -m unittest tests.test_spectral_bandpass_v2 tests.test_lab_spectral_response tests.test_wise0855_x1d -v
.venv/Scripts/python.exe -B -m scripts.audit_spectral_reference_v2 --design
# Commit code, test, protocol và v2-design.json rồi mới chạy:
.venv/Scripts/python.exe -B -m scripts.audit_spectral_reference_v2 --run
```

Design V2 hash cả nguồn V1/V2, protocol, hai raw inputs và metadata phổ.
Output mới là `web/data/spectral-response/v2-development-audit.json`;
không ghi đè file thiết kế hoặc kết quả đã tồn tại. Báo đủ số hỗ trợ toàn
dải, chỉ có phần phổ và lỗi số học, kèm mọi tỷ số chỉ khi mẫu số phù hợp.
