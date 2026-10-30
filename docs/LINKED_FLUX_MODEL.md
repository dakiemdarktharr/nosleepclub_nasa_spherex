# Lõi fit thông lượng chung

`scripts/linked_flux_profile.py` giải bài toán tuyến tính tại **vị trí cố định**:

`data_i = A * coefficient_i * template_i + nuisance_i @ b_i`.

Mỗi ảnh có nền/hàng xóm riêng; A dùng chung. Đơn vị được kiểm tra tường minh:
đơn vị A nhân đơn vị template phải đúng đơn vị ảnh. Có thể dùng A theo Jy và
template theo sr⁻¹ với ảnh theo Jy/sr, nhưng phải chuyển số và đơn vị nhất
quán trước khi gọi; kernel không tự đổi các số mang nhãn MJy/sr sang Jy/sr.

Các coefficient phải được cung cấp cùng provenance, không suy từ flux đã
fit riêng từng frame hoặc injected truth. Chuỗi provenance là hợp đồng đầu
vào, không chứng minh bản thân hệ số đã được xác minh. Chưa có adapter ghép
SED/response/gain/solid angle với pixel thật, nên **chưa thay mô hình WISE**.

Mỗi frame nhận error diagonal hoặc covariance dương xác định. Whitening và
SVD chuẩn hóa cột kiểm tra hạng của nuisance và toàn thiết kế; nguồn chồng
suy biến bị từ chối, không dùng pseudoinverse để che rank. Trả biên độ và
variance có điều kiện, nuisance, residual gốc/whitened, χ², rank, dof và
condition. Biên độ âm giữ nguyên; không clip rồi gọi Gaussian error là phép
đo nguồn dương. Chưa có ràng buộc vật lý, prior biên độ hay detection gate.

Tám test so với nghiệm WLS đầy đủ được dựng riêng, covariance nondiagonal,
đổi thứ tự/đổi thang, trực giao score, đơn vị và thiết kế gần suy biến:

```powershell
.venv/Scripts/python.exe -B -m unittest tests.test_linked_flux_profile -v
```

Các covariance giữa frame được giả định độc lập; template, coefficient,
mask và vị trí là cố định. Chưa có IRLS, uncertainty của SED/PSF/calibration,
registration chung hay fit centroid/motion. Một kernel số học đúng không
xác nhận tăng S/N, giảm bias hoặc covariance khoa học trên bầu trời.
