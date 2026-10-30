# Kiểm tra khả năng truy cập 0.10

Ngày 2026-10-30, kiểm tra thủ công trong trình duyệt theo phương pháp `accessibility-compliance:wcag-audit-patterns`. Đây là kiểm tra có phạm vi, chưa phải chứng nhận WCAG 2.2 AA hay thử nghiệm với người dùng screen-reader.

## Đã đo và thực hiện

- Font của trường nhập là Be Vietnam Pro tự host; tiếng Việt được xem trực tiếp. Trên các phần tử đang hiển thị có nền đặc, phép tính luminance từ màu chữ và màu nền kế thừa không tìm thấy trường hợp dưới 4,5:1 cho chữ thường hoặc 3:1 cho chữ lớn. Bỏ qua control disabled và nền ảnh; phép kiểm chưa bao gồm mọi opacity, trạng thái tương tác hoặc pixel trong ảnh minh họa.
- Skip link **Đến ảnh quan sát** hoạt động bằng Enter. Tab tiếp theo vào nút `workspace-help` trong vùng so ảnh, bỏ qua điều hướng; focus ở dưới header cố định.
- Enter mở hướng dẫn; Escape đóng và trả focus về nút mở. Phát hiện vòng Tab native của trình duyệt này có lúc ra BODY; đã bổ sung vòng focus cho hai dialog. Ở bản local đã sửa, Tab từ nút cuối về `guide-close`, Shift+Tab từ nút đầu tới `guide-start`, focus vẫn trong dialog. Không chặn các tổ hợp Ctrl/Alt/Meta+Tab.
- Mở báo cáo ePSF bằng Enter, thấy cả sáu hàng có mẫu số và giá trị đúng. Kho thí nghiệm cũ mở theo deep link. Điều khiển thời gian nhận phím End để tới ảnh cuối.
- Menu mobile mở và đóng khi chọn liên kết; layout 390 × 844 không có input/select/button phần Khám phá tràn ngang. Nút đóng bằng Escape đã được bổ sung; kiểm tra production sau deploy còn cần ghi nhận.

Bổ sung production `c88fe57`: Tab/Shift+Tab vòng trong dialog và Escape trả về nút mở đều đã thử trên URL public; menu mobile Escape đóng và trả focus đúng. [Ảnh focus](evidence/0.10/dialog-keyboard-production.png). Bảng sandwich mới được thử riêng local: hai select có tên accessible tường minh; Enter mở details, các lựa chọn 50/68/95% và mẫu accepted hiển thị đúng. Chiều ngang document mobile không tăng theo bảng; vùng bảng cuộn ngang riêng. Phần này chưa thay thế screen-reader/reflow audit.

Ảnh kiểm tra vòng focus: [dialog-keyboard-local.jpg](evidence/0.10/dialog-keyboard-local.jpg). Kiểm tra web/dữ liệu thật và giới hạn môi trường ở [BROWSER_VERIFICATION.md](BROWSER_VERIFICATION.md).

## Còn cần kiểm tra

Screen-reader thực (ít nhất NVDA và một tổ hợp khác), toàn bộ keyboard journey và dialog bằng chứng có nội dung dài, zoom/reflow 200–400%, chế độ tương phản cao, reduced motion, mô tả phi thị giác của ảnh khoa học và marker, mobile thật/touch, cùng kiểm tra tương phản các trạng thái focus/hover và nền ảnh. Giữ giới hạn này trong ledger; không đổi kết quả khoa học dựa vào kiểm tra giao diện.
