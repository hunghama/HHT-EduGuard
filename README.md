# HHT EduGuard - Hệ Thống Đo Lường Nhịp Độ Giờ Học & Hỗ Trợ Can Thiệp Học Vụ Kín Đáo Ứng Dụng AI

> **Dự án Nghiên cứu Khoa học & Sáng tạo Trẻ Hà Nội 2026**
> **Đơn vị:** Khoa Công nghệ Thông tin - Trường Cao đẳng Công nghệ cao Hà Nội (HHT)
> **Giảng viên hướng dẫn:** Thầy Hiển

## Danh Sách Nhóm Tác Giả Thực Hiện

| STT | Họ và Tên | Mã SV | Lớp | Vai trò |
| :-: | :--- | :-: | :-: | :--- |
| 1 | **Lê Văn An (*)** | SV005 | UDPM1-K16-CĐ | **Trưởng nhóm:** Điều phối & Thuyết trình |
| 2 | **Sái Công Phi Hùng** | SV001 | UDPM2.K16.CĐ | **Tech Lead:** Backend C# .NET 10 & API |
| 3 | **Bùi Thị Hương Quỳnh** | SV003 | UDPM1-K16-CĐ | **AI Engineer:** MediaPipe Pose & Liveness |
| 4 | **Lưu Thị Kim Liên** | SV002 | UDPM1-K16-CĐ | **Frontend Dev:** Web Dashboard & Biểu đồ CEI |
| 5 | **Nguyễn Quang Huy** | SV004 | UDPM1-K16-CĐ | **Researcher:** Khảo sát & Đánh giá sư phạm |

## Kiến Trúc Hệ Thống (Clean Architecture)

* src/EduGuard.Backend/: Backend C# .NET 10 (EduGuard.Core, Infrastructure, WebAPI).
* src/EduGuard.AI/: Module Python (OpenCV + MediaPipe Pose) nhận diện khung xương vô danh.
* src/EduGuard.Dashboard/: Giao diện Web bục giảng và biểu đồ chỉ số tập trung CEI.
* docs/API_CONTRACT.md: Đặc tả hợp đồng giao tiếp dữ liệu JSON đồng bộ chuẩn camelCase.

## Hướng Dẫn Khởi Chạy Nhanh

1. **Khởi chạy Backend C# (.NET 10):**
   Mở src/EduGuard.Backend/EduGuard.WebAPI và chạy dotnet run (http://localhost:5160).
2. **Kiểm thử kết nối từ Python AI:**
   Mở src/EduGuard.AI và chạy python api_connector.py.
