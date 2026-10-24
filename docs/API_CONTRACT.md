# BẢN ĐẶC TẢ HỢP ĐỒNG GIAO TIẾP DỮ LIỆU JSON (API CONTRACT)
## HỆ THỐNG HHT-EDUGUARD

> **Quy ước kỹ thuật chung:**
> - Toàn bộ khóa JSON (JSON Keys) sử dụng chuẩn **`camelCase`**.
> - Backend C# .NET 10 lắng nghe tại cổng: `http://localhost:5160` (hoặc IP mạng LAN khi kết nối 2 máy).
> - Đã mở khóa bảo mật CORS cho toàn bộ domain (`AllowAnyOrigin`, `AllowAnyMethod`, `AllowAnyHeader`).

---

## 1. LUỒNG CAMERA AI -> BACKEND C# (QUỲNH -> HÙNG)

### Endpoint 1: Bắn tín hiệu tư thế định kỳ
* **URL:** `POST /api/alerts/pose` (hoặc alias `POST /api/alerts/sleep`)
* **Request JSON:**
```json
{
  "seatCode": "A2-01",
  "poseType": "sleeping",
  "durationSeconds": 185
}
```
* **Response JSON (Thành công & Kích hoạt Telegram):**
```json
{
  "success": true,
  "triggeredAlert": true,
  "seatCode": "A2-01",
  "studentName": "Bùi Thị Hương Quỳnh",
  "currentStatus": "sleeping",
  "cooldownRemainingSeconds": 300,
  "message": "Phát hiện gục đầu vượt 180s. Đã gửi tin nhắn khích lệ riêng qua Telegram!"
}
```
* **Response JSON (Bị Cooldown 5 phút chặn lại để chống spam):**
```json
{
  "success": true,
  "triggeredAlert": false,
  "seatCode": "A2-01",
  "studentName": "Bùi Thị Hương Quỳnh",
  "currentStatus": "sleeping",
  "cooldownRemainingSeconds": 240,
  "message": "Đang khóa Cooldown (240s)."
}
```

---

## 2. LUỒNG ĐIỂM DANH 2FA & CHỐNG ẢNH IN A4 (APP / CAMERA -> HÙNG)

### Endpoint 2: Xác thực điểm danh đầu giờ
* **URL:** `POST /api/attendance/check-in`
* **Request JSON:**
```json
{
  "studentCode": "SV003",
  "seatCode": "A2-01",
  "telegramChatId": 100003,
  "isLivenessVerified": true
}
```
* **Response JSON (Thành công):**
```json
{
  "success": true,
  "message": "Điểm danh 2FA thành công!",
  "data": {
    "studentCode": "SV003",
    "fullName": "Bùi Thị Hương Quỳnh",
    "seatCode": "A2-01",
    "status": "focused",
    "checkedInAt": "2026-10-24T13:30:00Z"
  }
}
```
* **Response JSON (Bị từ chối do gian lận ảnh A4):**
```json
{
  "success": false,
  "message": "Từ chối: Phát hiện ảnh A4 (Liveness Failed)!",
  "data": null
}
```

---

## 3. LUỒNG WEB DASHBOARD BỤC GIẢNG <-> BACKEND C# (LIÊN <-> HÙNG)

### Endpoint 3: Lấy trạng thái thời gian thực của lớp học (Liên gọi mỗi 2-3 giây)
* **URL:** `GET /api/dashboard/classroom-state`
* **Response JSON:**
```json
{
  "classEngagementIndex": 80.0,
  "totalCheckedIn": 5,
  "focusedCount": 4,
  "distractedCount": 0,
  "sleepingCount": 1,
  "isBreakTime": false,
  "generatedAt": "2026-10-24T13:45:00Z",
  "seats": [
    {
      "seatCode": "A1-01",
      "studentCode": "SV001",
      "fullName": "Sái Công Phi Hùng",
      "className": "UDPM2.K16.CĐ",
      "status": "focused",
      "continuousDurationSeconds": 0,
      "totalAlerts": 0,
      "colorCode": "#198754"
    },
    {
      "seatCode": "A2-01",
      "studentCode": "SV003",
      "fullName": "Bùi Thị Hương Quỳnh",
      "className": "UDPM1-K16-CĐ",
      "status": "sleeping",
      "continuousDurationSeconds": 190,
      "totalAlerts": 1,
      "colorCode": "#dc3545"
    }
  ]
}
```
* **Ý nghĩa mã màu (`colorCode`) để Liên tô màu ghế:**
  * `#198754` (Xanh lá): Tập trung học tập (`focused`).
  * `#ffc107` (Vàng): Lơ đễnh, nghịch điện thoại hoặc cúi ngắn (`distracted`).
  * `#dc3545` (Đỏ): Ngủ gật sâu liên tục trên 180s (`sleeping`).
  * `#0dcaf0` (Xanh dương): Đang trong giờ giải lao (`relaxing`).

### Endpoint 4: Bật/Tắt chế độ Giờ giải lao (Break Time)
* **URL:** `POST /api/classroom/break-time`
* **Request JSON:**
```json
{
  "isBreak": true
}
```
* **Response JSON:**
```json
{
  "success": true,
  "isBreakTime": true,
  "message": "Đã bật chế độ Giờ giải lao."
}
```

### Endpoint 5: Dữ liệu phân tích nhịp độ ca học & Cảnh báo 30 phút cuối giờ
* **URL:** `GET /api/dashboard/analytics`
* **Response JSON (Dùng vẽ Line Chart theo các block 15 phút):**
```json
{
  "timelineBlocks": [
    { "blockTime": "0-15p", "ceiPercentage": 96.0 },
    { "blockTime": "15-30p", "ceiPercentage": 92.5 },
    { "blockTime": "30-45p", "ceiPercentage": 88.0 },
    { "blockTime": "45-60p", "ceiPercentage": 85.0 },
    { "blockTime": "60-75p", "ceiPercentage": 78.0 },
    { "blockTime": "75-90p", "ceiPercentage": 72.0 },
    { "blockTime": "90-105p", "ceiPercentage": 54.0 },
    { "blockTime": "105-120p", "ceiPercentage": 48.0 }
  ],
  "isFinal30Minutes": true,
  "pedagogicalAlert": {
    "isDropDetected": true,
    "dropRatePercentage": 42.0,
    "recommendation": "Cảnh báo: Tập trung giảm còn 48% ở 30 phút cuối. Khuyến nghị chuyển sang thảo luận nhóm hoặc mini-game."
  }
}
```