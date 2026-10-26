# BAN DAC TA HOP DONG GIAO TIEP DU LIEU JSON (API CONTRACT)
## HE THONG HHT-EDUGUARD

- Toan bo khoa JSON (JSON Keys) su dung chuan camelCase.
- Backend C# .NET 10 lang nghe tai cong: http://localhost:5160 (hoac IP mang LAN).
- Da mo khoa bao mat CORS cho toan bo domain (AllowAnyOrigin, AllowAnyMethod, AllowAnyHeader).

## 1. LUONG CAMERA AI -> BACKEND C# (QUYNH -> HUNG)
### Endpoint 1: POST /api/alerts/pose (hoac alias POST /api/alerts/sleep)
- Request JSON: { "seatCode": "A2-01", "poseType": "sleeping", "durationSeconds": 185 }
- Response JSON: { "success": true, "triggeredAlert": true, "seatCode": "A2-01", "studentName": "Bui Thi Huong Quynh", "currentStatus": "sleeping", "cooldownRemainingSeconds": 300, "message": "Phat hien guc dau vuot 180s. Da gui tin nhan khich le rieng qua Telegram!" }

## 2. LUONG DIEM DANH 2FA DA TRUC (GOC CAO DROIDCAM TREN XUONG + HIEU CHUAN BASELINE)
### Endpoint 2: POST /api/attendance/check-in
- Request JSON: { "studentCode": "SV003", "seatCode": "A2-01", "telegramChatId": 100003, "isLivenessVerified": true, "matchedFaceAngle": "TOP_DOWN_PITCH_25_YAW_0", "baselinePitchRatio": 0.485 }

## 3. LUONG WEB DASHBOARD BUC GIANG <-> BACKEND C# (LIEN <-> HUNG)
### Endpoint 3: GET /api/dashboard/classroom-state
- Tra ve classEngagementIndex, totalCheckedIn, focusedCount, distractedCount, sleepingCount, isBreakTime va danh sach 5 ghe seats kem colorCode (#198754, #ffc107, #dc3545, #0dcaf0).

### Endpoint 4: POST /api/classroom/break-time
- Request JSON: { "isBreak": true }

### Endpoint 5: GET /api/dashboard/analytics (Chi cung cap so lieu thong ke dinh luong khach quan)
- Response JSON: Tra ve timelineBlocks (8 khung 15 phut) va metricsSummary (peakCeiPercentage: 96.0, final30MinAverageCei: 51.0, endingCeiPercentage: 48.0, dropAmplitudePercentage: 42.0, totalTelegramAlertsSent, statisticalNote).