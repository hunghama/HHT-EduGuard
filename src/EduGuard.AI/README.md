# Module AI Camera (Phụ trách: Bùi Thị Hương Quỳnh)

## Hướng dẫn tích hợp nhanh cho Quỳnh:
1. Đặt file code webcam Python của em vào đúng thư mục `src/EduGuard.AI/` này.
2. Cài đặt thư viện:
   pip install -r requirements.txt

3. Trong file webcam của em, import hàm gửi API sang C# của anh Hùng:
   from api_connector import send_sleep_alert

   # Khi phát hiện gục đầu:
   send_sleep_alert(seat_code="A2-01", duration_seconds=185)
