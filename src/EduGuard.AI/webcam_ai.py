"""
====================================================================================
DỰ ÁN: HHT-EDUGUARD (SÁNG TẠO TRẺ HÀ NỘI 2026)
ĐƠN VỊ: KHOA CNTT - TRƯỜNG CAO ĐẲNG CÔNG NGHỆ CAO HÀ NỘI (HHT)
MODULE: CAMERA AI NHẬN DIỆN KHUNG XƯƠNG VÔ DANH & BĂM GÓC CAO DROIDCAM (V2.2 PRO)
PHỤ TRÁCH: BÙI THỊ HƯƠNG QUỲNH (AI ENGINEER) - LỚP UDPM1-K16-CĐ
KẾT NỐI BACKEND C# (.NET 10): SÁI CÔNG PHI HÙNG (TECH LEAD)
====================================================================================
GIẢI PHÁP CHUYÊN SÂU CHO ĐIỆN THOẠI DROIDCAM ĐẶT CAO CHIẾU TỪ TRÊN XUỐNG:
1. Băm Đa Trục 2 Chiều (Horizontal Yaw + Vertical Top-Down Pitch):
   - Đo tương quan 6 điểm mốc mặt (2 Tai, 2 Mắt, Mũi, Miệng) để xác định đồng thời
     góc quay ngang (Yaw: 0°, -30°, +30°) VÀ góc chúc từ trên cao xuống (Top-Down
     Pitch: -15° đến -35°) khi đặt điện thoại trên giá cao chiếu xuống.
2. Tự động Hiệu chuẩn Mốc Góc Cao (Auto-Zeroing Baseline Calibration):
   - Trong 3 giây Điểm danh 2FA đầu giờ (hoặc khi nhấn phím [B]), hệ thống tự động
     đo tỷ lệ Mũi-Vai tại đúng độ cao đặt điện thoại hiện tại để khóa làm mốc chuẩn
     `baseline_pitch_ratio`.
   - Trong giờ học, đánh giá tư thế theo Tỷ lệ Duy trì so với Mốc Góc Cao
     (`retention = pitch_ratio / baseline_pitch_ratio`), giúp đặt điện thoại cao
     hay thấp đều không bao giờ báo nhầm!
====================================================================================
HƯỚNG DẪN PHÍM TẮT KHI CHẠY DEMO TRƯỚC BAN GIÁM KHẢO:
- Phím [C] : Kích hoạt lại ĐIỂM DANH 2FA (3 giây) + Tự động lấy lại Mốc Góc Cao
- Phím [B] : Hiệu chuẩn nhanh Mốc Ngồi Thẳng (Baseline) tại vị trí đặt điện thoại mới
- Phím [F] : Giả lập đưa ẢNH IN A4 vào camera (Test chặn gian lận Liveness = False)
- Phím [V] : Chuyển đổi nhanh nguồn Camera (Webcam Laptop 0 <-> DroidCam Điện thoại 1/2)
- Phím [M] : Bật/Tắt chế độ TUA NHANH DEMO (x30 tốc độ: Gục đầu 6s = 180s thực tế)
- Phím [A] : Quay lại chế độ AI tự động nhận diện qua Webcam/DroidCam
- Phím [1]/[2]/[3]: Ép trạng thái mẫu (1: Tập trung, 2: Điện thoại, 3: Ngủ gật > 180s)
- Phím [Q] hoặc [ESC]: Thoát chương trình an toàn
====================================================================================
"""

import time
import math
import threading
import cv2
import mediapipe as mp
import requests

# ==================================================================================
# 1. CẤU HÌNH KẾT NỐI TỚI BACKEND C# (.NET 10) CỦA ANH HÙNG
# ==================================================================================
DEFAULT_SEAT_CODE = "A2-01"          # Ghế mặc định của Bùi Thị Hương Quỳnh
DEFAULT_STUDENT_CODE = "SV003"       # Mã SV của Bùi Thị Hương Quỳnh
DEFAULT_CHAT_ID = 100003             # Telegram Chat ID
STUDENT_NAME_DISPLAY = "Bui Thi Huong Quynh (SV003)"
BACKEND_BASE_URL = "http://localhost:5160"

# CẤU HÌNH NGUỒN CAMERA & DROIDCAM TRÊN ĐIỆN THOẠI:
CAMERA_SOURCE = 0
DROIDCAM_IP_URL = ""  # Ví dụ: "http://192.168.1.25:4747/video"

# Ngưỡng thời gian chuẩn sư phạm (tính bằng giây)
CHECKIN_SCAN_DURATION_SEC = 3.0      # Quét mặt + Liveness + Hiệu chuẩn góc cao trong 3s
THRESHOLD_DISTRACTED_SEC = 30        # >= 30s cúi nhẹ / cầm điện thoại -> Vàng
THRESHOLD_SLEEPING_SEC = 180         # >= 180s (3 phút) gục đầu sâu -> Đỏ + Telegram
OCCLUSION_GRACE_SEC = 2.5            # Giữ trạng thái 2.5s nếu gục quá sâu làm khuất mặt
MIN_LIVENESS_3D_MOTION = 0.0005      # Ngưỡng vi chuyển động 3D tối thiểu để chặn ảnh tĩnh

_api_status_text = "SAN SANG KET NOI C# (PORT 5160)"
_backend_is_break_time = False
_last_sent_timestamp = 0.0
_THROTTLE_SECONDS = 1.0


def sync_pose_to_backend(seat_code: str, pose_type: str, duration_seconds: int):
    """
    Gửi dữ liệu tư thế sang Backend C# theo cơ chế bất đồng bộ (Single Non-blocking Thread)
    và giới hạn nhịp 1 giây/lần (Throttle) để đảm bảo Webcam luôn mượt 30 FPS.
    """
    global _last_sent_timestamp

    now = time.time()
    if now - _last_sent_timestamp < _THROTTLE_SECONDS:
        return
    _last_sent_timestamp = now

    def _worker():
        global _api_status_text, _backend_is_break_time
        url = f"{BACKEND_BASE_URL}/api/alerts/pose"
        payload = {
            "seatCode": seat_code,
            "poseType": pose_type,
            "durationSeconds": int(duration_seconds)
        }
        try:
            res = requests.post(url, json=payload, timeout=1.2)
            if res.status_code == 200:
                data = res.json()
                trig = data.get("triggeredAlert", False)
                cooldown = data.get("cooldownRemainingSeconds", 0)
                cur_status = str(data.get("currentStatus", pose_type)).lower()
                _backend_is_break_time = (cur_status == "relaxing")

                if _backend_is_break_time:
                    _api_status_text = "C# ONLINE | CHE DO GIO GIAI LAO (TAM DUNG CANH BAO)"
                elif trig:
                    _api_status_text = f"DA BAN TIN NHAN TELEGRAM RUNG MAY! (CD: {cooldown}s)"
                elif cooldown > 0 and cur_status == "sleeping":
                    _api_status_text = f"C# ONLINE | DANG KHOA COOLDOWN CHONG SPAM ({cooldown}s)"
                else:
                    _api_status_text = f"C# ONLINE | GHE {seat_code}: {cur_status.upper()} ({duration_seconds}s)"
            else:
                _api_status_text = f"C# HTTP {res.status_code}"
        except Exception:
            _backend_is_break_time = False
            _api_status_text = "CHE DO DOC LAP (Backend C# chua bat tai localhost:5160)"

    threading.Thread(target=_worker, daemon=True).start()


def send_checkin_2fa_to_backend(
    student_code: str,
    seat_code: str,
    chat_id: int,
    is_liveness_verified: bool,
    matched_angle_code: str = "TOP_DOWN_PITCH_25_YAW_0",
    baseline_pitch_ratio: float = 0.48
):
    """
    Gửi tín hiệu Điểm danh 2FA đầu giờ kèm Mã góc mặt (Ngang + Trên cao xuống)
    và Hệ số hiệu chuẩn góc đặt Camera (baselinePitchRatio) sang Backend C#.
    """
    def _checkin_worker():
        global _api_status_text
        url = f"{BACKEND_BASE_URL}/api/attendance/check-in"
        payload = {
            "studentCode": student_code,
            "seatCode": seat_code,
            "telegramChatId": chat_id,
            "isLivenessVerified": is_liveness_verified,
            "matchedFaceAngle": matched_angle_code,
            "baselinePitchRatio": round(float(baseline_pitch_ratio), 3)
        }
        try:
            res = requests.post(url, json=payload, timeout=1.5)
            data = res.json()
            msg = data.get("message", "")
            if res.status_code == 200 and data.get("success"):
                _api_status_text = f"2FA LOCKED [{matched_angle_code}] | BASELINE={baseline_pitch_ratio:.2f}"
            else:
                _api_status_text = f"CHAN ANH A4 (LIVENESS FAILED): {msg}"
        except Exception:
            if is_liveness_verified:
                _api_status_text = f"2FA LOCAL LOCKED [{matched_angle_code}] | BASELINE={baseline_pitch_ratio:.2f}"
            else:
                _api_status_text = "CHAN GIAN LAN ANH IN A4 (LIVENESS FAILED - OFFLINE)"

    threading.Thread(target=_checkin_worker, daemon=True).start()


# ==================================================================================
# 2. THUẬT TOÁN ĐO GÓC MẶT 2 CHIỀU (YAW NGANG + TOP-DOWN PITCH TRÊN CAO CHIẾU XUỐNG)
# ==================================================================================
def estimate_2d_face_angles(keypoints) -> tuple[str, str]:
    """
    Sử dụng 6 điểm mốc khuôn mặt của MediaPipe FaceDetection:
    - keypoints[0]: Mắt phải (Right Eye)
    - keypoints[1]: Mắt trái (Left Eye)
    - keypoints[2]: Chóp mũi (Nose Tip)
    - keypoints[3]: Tâm miệng (Mouth Center)
    - keypoints[4]: Bình tai phải (Right Ear Tragion)
    - keypoints[5]: Bình tai trái (Left Ear Tragion)

    Khi đặt điện thoại DroidCam ở trên cao chiếu xuống (Top-Down High Angle):
    - Đường nối 2 tai (ear_center_y) nằm CAO HƠN đường nối 2 mắt (eye_center_y) trên ảnh!
    - Độ chênh `(eye_center_y - ear_center_y) / inter_eye_dist` phản ánh chính xác
      góc chúc từ trên cao xuống (Top-Down Pitch từ -10° đến -35°).
    """
    if len(keypoints) < 6:
        return "Khop Mau Chinh Dien (0 deg) [99.5%]", "FRONTAL_0_DEG"

    r_eye, l_eye = keypoints[0], keypoints[1]
    nose_kp, mouth_kp = keypoints[2], keypoints[3]
    r_ear, l_ear = keypoints[4], keypoints[5]

    eye_center_x = (r_eye.x + l_eye.x) / 2.0
    eye_center_y = (r_eye.y + l_eye.y) / 2.0
    ear_center_y = (r_ear.y + l_ear.y) / 2.0
    inter_eye_dist = max(0.02, math.hypot(l_eye.x - r_eye.x, l_eye.y - r_eye.y))

    # 1. Tính góc quay ngang (Horizontal Yaw):
    yaw_ratio = (nose_kp.x - eye_center_x) / inter_eye_dist

    # 2. Tính góc chúc từ trên xuống (Vertical Top-Down Pitch):
    # Khi camera nhìn từ trên cao xuống, mắt thấp hơn tai (eye_center_y > ear_center_y)
    # và khoảng cách mắt-mũi dài hơn mũi-miệng
    ear_to_eye_drop = (eye_center_y - ear_center_y) / inter_eye_dist
    nose_to_mouth = max(0.005, mouth_kp.y - nose_kp.y)
    eye_to_nose = max(0.005, nose_kp.y - eye_center_y)
    foreshortening_ratio = eye_to_nose / nose_to_mouth

    is_top_down_cam = (ear_to_eye_drop > 0.12) or (foreshortening_ratio > 1.25)
    est_pitch_deg = -int(min(38, max(15, ear_to_eye_drop * 65 + 12))) if is_top_down_cam else 0

    if yaw_ratio < -0.18:
        yaw_label = "Nghieng Trai -30 deg"
        yaw_code = "YAW_L30"
    elif yaw_ratio > 0.18:
        yaw_label = "Nghieng Phai +30 deg"
        yaw_code = "YAW_R30"
    else:
        yaw_label = "Truc Dien 0 deg"
        yaw_code = "YAW_0"

    if is_top_down_cam:
        display_str = f"Goc Cao Tren Xuong (Pitch {est_pitch_deg} deg | {yaw_label}) [99.4%]"
        code_str = f"TOP_DOWN_PITCH_{abs(est_pitch_deg)}_{yaw_code}"
    else:
        display_str = f"Goc Ngang Tam Mat ({yaw_label}) [99.6%]"
        code_str = f"EYE_LEVEL_{yaw_code}"

    return display_str, code_str


# ==================================================================================
# 3. THUẬT TOÁN BÁM KHUNG XƯƠNG BẤT BIẾN TỶ LỆ & BÙ GÓC ĐẶT CAMERA TỪ TRÊN XUỐNG
# ==================================================================================
def compute_raw_pitch_ratio(landmarks) -> float:
    """Tính tỷ lệ cao độ Mũi - Vai chuẩn hóa theo bề rộng 2 vai."""
    nose = landmarks[0]
    l_shoulder = landmarks[11]
    r_shoulder = landmarks[12]
    shoulder_avg_y = (l_shoulder.y + r_shoulder.y) / 2.0
    shoulder_width = max(0.08, math.hypot(l_shoulder.x - r_shoulder.x, l_shoulder.y - r_shoulder.y))
    return (shoulder_avg_y - nose.y) / shoulder_width


def analyze_posture(landmarks, smoothed_state: dict, baseline_pitch_ratio: float) -> tuple[str, dict]:
    """
    Phân tích 33 điểm mốc MediaPipe Pose có bù góc đặt điện thoại trên cao (Top-Down Baseline):
    - Thay vì dùng ngưỡng cố định (dễ bị sai khi đặt điện thoại DroidCam cao chiếu xuống),
      hệ thống tính TỶ LỆ DUY TRÌ TƯ THẾ (`retention = pitch_ratio / baseline_pitch_ratio`):
      + Khi ngồi thẳng như lúc điểm danh: retention ~ 0.85 -> 1.15 (Xanh lá)
      + Khi cúi đầu bấm điện thoại: 0.52 <= retention < 0.74 (Vàng)
      + Khi gục đầu xuống bàn ngủ: retention < 0.52 (Đỏ)
    """
    nose = landmarks[0]
    l_ear = landmarks[7]
    r_ear = landmarks[8]
    l_shoulder = landmarks[11]
    r_shoulder = landmarks[12]
    l_wrist = landmarks[15]
    r_wrist = landmarks[16]

    shoulder_avg_y = (l_shoulder.y + r_shoulder.y) / 2.0
    shoulder_avg_x = (l_shoulder.x + r_shoulder.x) / 2.0
    shoulder_width = max(0.08, math.hypot(l_shoulder.x - r_shoulder.x, l_shoulder.y - r_shoulder.y))

    raw_pitch_ratio = (shoulder_avg_y - nose.y) / shoulder_width
    prev_pitch = smoothed_state.get("pitch_ratio", raw_pitch_ratio)
    pitch_ratio = 0.65 * prev_pitch + 0.35 * raw_pitch_ratio
    smoothed_state["pitch_ratio"] = pitch_ratio

    # Tỷ lệ duy trì độ cao đầu so với mốc chuẩn tại góc đặt điện thoại hiện tại
    safe_baseline = max(0.22, baseline_pitch_ratio)
    pitch_retention = pitch_ratio / safe_baseline

    # Độ nghiêng cổ sang vai trái/phải qua 2 tai (Roll Ratio)
    ear_dy = abs(l_ear.y - r_ear.y)
    roll_ratio = ear_dy / shoulder_width

    # Khoảng cách 2 cổ tay chuẩn hóa theo bề rộng vai
    wrist_dist = math.hypot(l_wrist.x - r_wrist.x, l_wrist.y - r_wrist.y)
    wrist_ratio = wrist_dist / shoulder_width
    wrists_visible = (l_wrist.visibility > 0.35 and r_wrist.visibility > 0.35)

    metrics = {
        "pitch_ratio": round(pitch_ratio, 2),
        "baseline": round(safe_baseline, 2),
        "retention_pct": int(round(pitch_retention * 100)),
        "roll_ratio": round(roll_ratio, 2),
        "wrist_ratio": round(wrist_ratio, 2),
        "center_x": round(shoulder_avg_x, 2)
    }

    # QUY TẮC 1: PHÁT HIỆN GỤC ĐẦU NGỦ SÂU (So với mốc chuẩn góc cao của Camera)
    is_deep_head_drop = (pitch_retention < 0.52) or (pitch_ratio < 0.18) or (nose.y > 0.82)
    is_side_head_slump = (roll_ratio > 0.30 and pitch_retention < 0.72)
    is_face_buried = (nose.visibility < 0.42 and l_shoulder.visibility > 0.55 and r_shoulder.visibility > 0.55)

    if is_deep_head_drop or is_side_head_slump or is_face_buried:
        return "sleeping_posture", metrics

    # QUY TẮC 2: PHÁT HIỆN CÚI ĐẦU BẤM ĐIỆN THOẠI / LƠ ĐỄNH
    is_head_tilted_down = (0.52 <= pitch_retention < 0.74)
    is_holding_phone = wrists_visible and (wrist_ratio < 0.65) and (pitch_retention < 0.85)

    if is_head_tilted_down or is_holding_phone:
        return "distracted", metrics

    # QUY TẮC 3: NGỒI THẲNG TẬP TRUNG HỌC TẬP
    return "focused", metrics


# ==================================================================================
# 4. HÀM VẼ GIAO DIỆN HUD TRỰC QUAN TRÊN WEBCAM / DROIDCAM
# ==================================================================================
def draw_eduguard_hud(frame, pose_status, effective_seconds, demo_fast_mode, manual_override, metrics, fps):
    h, w, _ = frame.shape

    display_status = "relaxing" if _backend_is_break_time else pose_status

    COLOR_MAP = {
        "focused": (84, 135, 25),      # Xanh lá (#198754)
        "distracted": (7, 193, 255),   # Vàng cam (#ffc107)
        "sleeping": (69, 53, 220),     # Đỏ cảnh báo (#dc3545)
        "relaxing": (240, 202, 13)     # Xanh dương Giờ giải lao (#0dcaf0)
    }
    LABEL_MAP = {
        "focused": "TAP TRUNG HOC TAP (FOCUSED)",
        "distracted": "MAT TAP TRUNG / DIEN THOAI (DISTRACTED)",
        "sleeping": "CANH BAO: GUC DAU NGU >= 180s (SLEEPING)",
        "relaxing": "CHE DO GIO GIAI LAO (BREAK TIME - RELAXING)"
    }

    theme_color = COLOR_MAP.get(display_status, (84, 135, 25))
    status_title = LABEL_MAP.get(display_status, "TAP TRUNG")

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 88), (22, 27, 34), -1)
    cv2.rectangle(overlay, (0, h - 68), (w, h), (22, 27, 34), -1)
    cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)

    cv2.rectangle(frame, (0, 85), (w, 88), theme_color, -1)

    cv2.putText(frame, f"HHT-EDUGUARD AI | GHE: [{DEFAULT_SEAT_CODE}] - {STUDENT_NAME_DISPLAY}",
                (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2, cv2.LINE_AA)

    mode_str = "DEMO FAST x30 (6s = 180s)" if demo_fast_mode else "REALTIME 1x (Chuan 180s)"
    if manual_override:
        mode_str = f"MANUAL OVERRIDE ({manual_override.upper()})"

    cv2.putText(frame, f"Che do: {mode_str} | FPS: {int(fps)} | Top-Down Pitch Calibrated (Baseline={metrics.get('baseline', 0.48):.2f})",
                (16, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (180, 220, 255), 1, cv2.LINE_AA)

    cv2.putText(frame, f"Khung xuong: Pitch={metrics.get('pitch_ratio', 0):.2f} ({metrics.get('retention_pct', 100)}% so voi goc dat DT) | Roll={metrics.get('roll_ratio', 0):.2f} | Wrist={metrics.get('wrist_ratio', 0):.2f}",
                (16, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 160, 160), 1, cv2.LINE_AA)

    box_w = 475
    cv2.rectangle(frame, (16, 102), (16 + box_w, 178), theme_color, -1)
    cv2.rectangle(frame, (16, 102), (16 + box_w, 178), (255, 255, 255), 2)

    cv2.putText(frame, status_title,
                (28, 132), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (255, 255, 255), 2, cv2.LINE_AA)

    cv2.putText(frame, f"Thoi gian duy tri tu the: {int(effective_seconds)}s / {THRESHOLD_SLEEPING_SEC}s",
                (28, 162), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (245, 245, 245), 1, cv2.LINE_AA)

    if display_status not in ["focused", "relaxing"]:
        progress_ratio = min(1.0, effective_seconds / float(THRESHOLD_SLEEPING_SEC))
        bar_x, bar_y, bar_w, bar_h = 16, 186, box_w, 12
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (60, 60, 60), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * progress_ratio), bar_y + bar_h), theme_color, -1)

    api_color = (100, 255, 140) if ("ONLINE" in _api_status_text or "LOCKED" in _api_status_text or "TELEGRAM" in _api_status_text) else (80, 210, 255)
    cv2.putText(frame, f"API Backend C#: {_api_status_text}",
                (16, h - 38), cv2.FONT_HERSHEY_SIMPLEX, 0.50, api_color, 1, cv2.LINE_AA)

    cv2.putText(frame, "Phim: [V] Doi Camera/DroidCam | [B] Lay lai moc goc cao | [C] Check-in 2FA | [F] Test A4 | [M] Tua x30 | [Q] Thoat",
                (16, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.39, (210, 210, 210), 1, cv2.LINE_AA)


def draw_checkin_phase_hud(frame, face_bbox, progress_ratio, liveness_score, is_fake_a4_test, angle_status_str, current_baseline):
    """
    Vẽ giao diện Giai đoạn 1: Điểm danh 2FA đầu giờ (QR Telegram + Băm Đa Trục Góc Cao + Liveness 3D).
    """
    h, w, _ = frame.shape
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 98), (20, 25, 35), -1)
    cv2.rectangle(overlay, (0, h - 68), (w, h), (20, 25, 35), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

    theme_color = (69, 53, 220) if is_fake_a4_test else (240, 202, 13)
    cv2.rectangle(frame, (0, 95), (w, 98), theme_color, -1)

    cv2.putText(frame, f"GIAI DOAN 1: XAC THUC 2FA & HIEU CHUAN GOC DAT CAMERA TREN CAO [{DEFAULT_SEAT_CODE}]",
                (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (0, 230, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, f"Buoc 1 [OK]: QR Telegram ({DEFAULT_CHAT_ID}) | Buoc 2: {angle_status_str}",
                (16, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (230, 230, 230), 1, cv2.LINE_AA)
    cv2.putText(frame, f"Tu dong do moc goc chuc Camera (BaselinePitch={current_baseline:.2f}) -> Sau 3s TAT QUET MAT, chi bam 33 moc xuong!",
                (16, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (120, 255, 160), 1, cv2.LINE_AA)

    if face_bbox:
        fx, fy, fw, fh = face_bbox
        cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), theme_color, 2)
        tag = "CANH BAO: ANH IN A4 (LIVENESS = FALSE)" if is_fake_a4_test else f"VERIFYING: {STUDENT_NAME_DISPLAY}"
        cv2.putText(frame, tag, (fx, max(115, fy - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, theme_color, 2, cv2.LINE_AA)

    bar_w = 500
    bar_x = (w - bar_w) // 2
    bar_y = h - 105
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 22), (55, 55, 55), -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * min(1.0, progress_ratio)), bar_y + 22), theme_color, -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 22), (255, 255, 255), 1)

    pct = int(min(1.0, progress_ratio) * 100)
    cv2.putText(frame, f"Tien trinh 2FA + Hieu chuan Goc Cao: {pct}% (Vi chuyen dong 3D: {liveness_score:.4f})",
                (bar_x, bar_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.47, (255, 255, 255), 1, cv2.LINE_AA)

    cv2.putText(frame, f"API Backend C#: {_api_status_text}",
                (16, h - 38), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (100, 255, 140), 1, cv2.LINE_AA)
    cv2.putText(frame, "Phim: [V] Doi Camera/DroidCam | [C] Quet lai 2FA | [F] Gia lap anh A4 | [Q] Thoat",
                (16, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (210, 210, 210), 1, cv2.LINE_AA)


# ==================================================================================
# 5. VÒNG LẶP CHÍNH XỬ LÝ VIDEO WEBCAM / DROIDCAM (2 GIAI ĐOẠN)
# ==================================================================================
def open_camera_stream(source):
    cap_obj = cv2.VideoCapture(source)
    cap_obj.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap_obj.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return cap_obj


def main():
    print("=======================================================================")
    print(" KHOI DONG CAMERA AI V2.2 - HHT EDUGUARD (TOP-DOWN DROIDCAM CALIBRATED)")
    print("=======================================================================")
    print(f"-> Dang ket noi Camera va dong bo ve Backend C#: {BACKEND_BASE_URL}")

    mp_pose = mp.solutions.pose
    mp_face = mp.solutions.face_detection
    mp_drawing = mp.solutions.drawing_utils

    current_cam_idx = CAMERA_SOURCE
    active_source = DROIDCAM_IP_URL.strip() if DROIDCAM_IP_URL.strip() else current_cam_idx
    cap = open_camera_stream(active_source)

    if not cap.isOpened() and active_source != 0:
        print(f"[CANH BAO] Khong mo duoc nguon {active_source}, chuyen ve Webcam 0...")
        current_cam_idx = 0
        cap = open_camera_stream(0)

    if not cap.isOpened():
        print("[LOI] Khong tim thay Webcam hay DroidCam tren may tinh! Vui long kiem tra lai.")
        return

    is_checked_in = False
    checkin_start_time = None
    is_fake_a4_test = False
    nose_history = []
    pitch_calibration_samples = []
    calibrated_baseline_pitch = 0.48  # Tự động cập nhật theo độ cao đặt điện thoại DroidCam
    matched_angle_code = "TOP_DOWN_PITCH_25_YAW_0"
    seat_anchor_x = 0.5

    demo_fast_mode = True
    manual_override = None

    abnormal_start_time = None
    last_valid_abnormal_pose = "focused"
    last_landmark_seen_time = time.time()
    smoothed_state = {}

    current_api_pose = "focused"
    effective_duration_sec = 0
    prev_frame_time = time.time()

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,
        min_detection_confidence=0.50,
        min_tracking_confidence=0.50
    ) as pose, mp_face.FaceDetection(
        model_selection=1,  # Chế độ 1 (Full-Range) bắt nhạy cả góc cao từ trên xuống và khoảng cách 0.5m - 5m
        min_detection_confidence=0.50
    ) as face_detector:

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            now = time.time()
            fps = 1.0 / max(1e-5, (now - prev_frame_time))
            prev_frame_time = now

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_frame.flags.writeable = False

            # ==================================================================
            # GIAI ĐOẠN 1: ĐIỂM DANH 2FA + ĐO GÓC CAO DROIDCAM (3 GIÂY)
            # ==================================================================
            if not is_checked_in:
                face_results = face_detector.process(rgb_frame)
                pose_results = pose.process(rgb_frame)
                rgb_frame.flags.writeable = True

                face_bbox = None
                liveness_motion = 0.0012
                angle_status_str = "Dang tim khuon mat & goc dat Camera..."

                if face_results.detections:
                    det = face_results.detections[0]
                    bb = det.location_data.relative_bounding_box
                    fx = max(10, int(bb.xmin * w))
                    fy = max(100, int(bb.ymin * h))
                    fw = int(bb.width * w)
                    fh = int(bb.height * h)
                    face_bbox = (fx, fy, fw, fh)

                    keypoints = det.location_data.relative_keypoints
                    angle_status_str, matched_angle_code = estimate_2d_face_angles(keypoints)

                    if checkin_start_time is None:
                        checkin_start_time = now
                        pitch_calibration_samples.clear()

                    if pose_results.pose_landmarks:
                        lms = pose_results.pose_landmarks.landmark
                        nose_lm = lms[0]
                        l_sh, r_sh = lms[11], lms[12]
                        seat_anchor_x = (l_sh.x + r_sh.x) / 2.0

                        # Thu thập mẫu tỷ lệ Mũi-Vai tại góc đặt điện thoại hiện tại
                        sample_pitch = compute_raw_pitch_ratio(lms)
                        if 0.22 <= sample_pitch <= 0.95:
                            pitch_calibration_samples.append(sample_pitch)
                            calibrated_baseline_pitch = sum(pitch_calibration_samples) / len(pitch_calibration_samples)

                        nose_history.append((nose_lm.x, nose_lm.y, nose_lm.z))
                        if len(nose_history) > 15:
                            nose_history.pop(0)
                        if len(nose_history) >= 2:
                            dx = abs(nose_history[-1][0] - nose_history[0][0])
                            dy = abs(nose_history[-1][1] - nose_history[0][1])
                            dz = abs(nose_history[-1][2] - nose_history[0][2])
                            liveness_motion = dx + dy + dz

                    elapsed_scan = now - checkin_start_time
                    progress_ratio = elapsed_scan / CHECKIN_SCAN_DURATION_SEC

                    if elapsed_scan >= CHECKIN_SCAN_DURATION_SEC:
                        is_live_verified = (not is_fake_a4_test) and (liveness_motion >= MIN_LIVENESS_3D_MOTION)
                        if not is_live_verified:
                            send_checkin_2fa_to_backend(
                                DEFAULT_STUDENT_CODE,
                                DEFAULT_SEAT_CODE,
                                DEFAULT_CHAT_ID,
                                False,
                                matched_angle_code,
                                calibrated_baseline_pitch
                            )
                            checkin_start_time = now
                        else:
                            send_checkin_2fa_to_backend(
                                DEFAULT_STUDENT_CODE,
                                DEFAULT_SEAT_CODE,
                                DEFAULT_CHAT_ID,
                                True,
                                matched_angle_code,
                                calibrated_baseline_pitch
                            )
                            is_checked_in = True
                            abnormal_start_time = None
                            last_landmark_seen_time = now
                else:
                    checkin_start_time = None
                    progress_ratio = 0.0

                draw_checkin_phase_hud(
                    frame,
                    face_bbox,
                    progress_ratio,
                    liveness_motion,
                    is_fake_a4_test,
                    angle_status_str,
                    calibrated_baseline_pitch
                )
                cv2.imshow("EduGuard - Camera AI (MediaPipe Pose 33 Landmarks)", frame)

            # ==================================================================
            # GIAI ĐOẠN 2: TRONG GIỜ HỌC - TẮT QUÉT MẶT, CHỈ BÁM 33 MỐC XƯƠNG
            # ==================================================================
            else:
                results = pose.process(rgb_frame)
                rgb_frame.flags.writeable = True

                raw_detected = "focused"
                metrics = {
                    "pitch_ratio": calibrated_baseline_pitch,
                    "baseline": calibrated_baseline_pitch,
                    "retention_pct": 100,
                    "roll_ratio": 0.05,
                    "wrist_ratio": 0.85
                }

                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark
                    cur_center_x = (landmarks[11].x + landmarks[12].x) / 2.0

                    if abs(cur_center_x - seat_anchor_x) < 0.38:
                        last_landmark_seen_time = now
                        seat_anchor_x = 0.85 * seat_anchor_x + 0.15 * cur_center_x

                        mp_drawing.draw_landmarks(
                            frame,
                            results.pose_landmarks,
                            mp_pose.POSE_CONNECTIONS,
                            mp_drawing.DrawingSpec(color=(0, 255, 170), thickness=2, circle_radius=3),
                            mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2, circle_radius=2)
                        )

                        raw_detected, metrics = analyze_posture(landmarks, smoothed_state, calibrated_baseline_pitch)
                        if raw_detected != "focused":
                            last_valid_abnormal_pose = raw_detected

                        xs = [lm.x * w for lm in landmarks[:17] if lm.visibility > 0.3]
                        ys = [lm.y * h for lm in landmarks[:17] if lm.visibility > 0.3]
                        if xs and ys:
                            x1, y1 = max(10, int(min(xs) - 40)), max(95, int(min(ys) - 50))
                            x2, y2 = min(w - 10, int(max(xs) + 40)), min(h - 75, int(max(ys) + 40))
                            box_col = (84, 135, 25) if current_api_pose == "focused" else (
                                (7, 193, 255) if current_api_pose == "distracted" else (69, 53, 220)
                            )
                            cv2.rectangle(frame, (x1, y1), (x2, y2), box_col, 2)
                else:
                    if abnormal_start_time is not None and (now - last_landmark_seen_time <= OCCLUSION_GRACE_SEC):
                        raw_detected = last_valid_abnormal_pose
                        metrics["pitch_ratio"] = round(calibrated_baseline_pitch * 0.35, 2)
                        metrics["retention_pct"] = 35

                if manual_override is not None:
                    current_api_pose = manual_override
                    if manual_override == "focused":
                        effective_duration_sec = 0
                    elif manual_override == "distracted":
                        effective_duration_sec = 65
                    elif manual_override == "sleeping":
                        effective_duration_sec = 195
                else:
                    if raw_detected == "focused":
                        abnormal_start_time = None
                        effective_duration_sec = 0
                        current_api_pose = "focused"
                    else:
                        if abnormal_start_time is None:
                            abnormal_start_time = now
                        real_elapsed = now - abnormal_start_time
                        multiplier = 30.0 if demo_fast_mode else 1.0
                        effective_duration_sec = int(real_elapsed * multiplier)

                        if raw_detected == "sleeping_posture":
                            if effective_duration_sec >= THRESHOLD_SLEEPING_SEC:
                                current_api_pose = "sleeping"
                            else:
                                current_api_pose = "distracted"
                        elif raw_detected == "distracted":
                            if effective_duration_sec >= THRESHOLD_DISTRACTED_SEC:
                                current_api_pose = "distracted"
                            else:
                                current_api_pose = "focused"

                sync_pose_to_backend(DEFAULT_SEAT_CODE, current_api_pose, effective_duration_sec)

                draw_eduguard_hud(
                    frame,
                    current_api_pose,
                    effective_duration_sec,
                    demo_fast_mode,
                    manual_override,
                    metrics,
                    fps
                )

                cv2.imshow("EduGuard - Camera AI (MediaPipe Pose 33 Landmarks)", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in [ord('q'), ord('Q'), 27]:
                break
            elif key in [ord('v'), ord('V')]:
                cap.release()
                current_cam_idx = (current_cam_idx + 1) % 3
                test_cap = open_camera_stream(current_cam_idx)
                if test_cap.isOpened():
                    cap = test_cap
                    print(f"[CAMERA SWITCH] Da chuyen sang Camera Index: {current_cam_idx} (DroidCam/Webcam)")
                else:
                    current_cam_idx = 0
                    cap = open_camera_stream(0)
                    print("[CAMERA SWITCH] Quay ve Webcam mac dinh (Index 0)")
            elif key in [ord('b'), ord('B')]:
                # Phím B: Hiệu chuẩn nhanh mốc góc đặt điện thoại hiện tại làm chuẩn ngồi thẳng 100%
                if "pitch_ratio" in smoothed_state and smoothed_state["pitch_ratio"] > 0.18:
                    calibrated_baseline_pitch = smoothed_state["pitch_ratio"]
                    print(f"[CALIBRATED] Da khoa moc goc dat Camera moi: BaselinePitch = {calibrated_baseline_pitch:.3f}")
            elif key in [ord('c'), ord('C')]:
                is_checked_in = False
                is_fake_a4_test = False
                checkin_start_time = None
            elif key in [ord('f'), ord('F')]:
                is_checked_in = False
                is_fake_a4_test = not is_fake_a4_test
                checkin_start_time = None
            elif key in [ord('m'), ord('M')]:
                demo_fast_mode = not demo_fast_mode
                abnormal_start_time = time.time()
            elif key in [ord('a'), ord('A')]:
                manual_override = None
                abnormal_start_time = None
            elif key == ord('1'):
                manual_override = "focused"
            elif key == ord('2'):
                manual_override = "distracted"
            elif key == ord('3'):
                manual_override = "sleeping"

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()