# BẢN ĐẶC TẢ HỢP ĐỒNG DỮ LIỆU JSON (API CONTRACT)

Quy ước chung: Toàn bộ JSON Keys sử dụng chuẩn **camelCase**.

### 1. Luồng Camera AI -> C# (Quỳnh -> Hùng)
- Endpoint: `POST /api/alerts/sleep`
- Payload:
{
  "seatCode": "A2-01",
  "durationSeconds": 185
}

- Response:
{
  "success": true,
  "triggeredAlert": true,
  "seatCode": "A2-01",
  "message": "Phát hiện ngủ gật vượt ngưỡng 180s. Đã kích hoạt Telegram!"
}

### 2. Luồng Dashboard -> C# (Liên <-> Hùng)
- Endpoint: `GET /api/dashboard/classroom-state`
- Response: Trả về danh sách ghế và chỉ số tập trung cả lớp CEI.
