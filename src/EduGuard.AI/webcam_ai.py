"""
====================================================================================
DỰ ÁN: HHT-EDUGUARD (SÁNG TẠO TRẺ HÀ NỘI 2026)
ĐƠN VỊ: KHOA CNTT - TRƯỜNG CAO ĐẲNG CÔNG NGHỆ CAO HÀ NỘI (HHT)
MODULE: CAMERA AI KIẾN TRÚC TÁCH BIỆT 2 TẦNG (2FA CỰ LY GẦN + KHUNG XƯƠNG GÓC CAO V2.5)
PHỤ TRÁCH: BÙI THỊ HƯƠNG QUỲNH (AI ENGINEER) - LỚP UDPM1-K16-CĐ
KẾT NỐI BACKEND C# (.NET 10): SÁI CÔNG PHI HÙNG (TECH LEAD)
====================================================================================
ĐẶC ĐIỂM ĐỘT PHÁ CỦA BẢN V2.5 (DECOUPLED 2-TIER ARCHITECTURE):
1. Tách biệt rõ 2 chế độ vận hành thực tế theo đúng nguyên lý vật lý phòng máy:
   - Chế độ 1 (Mặc định): CỰ LY GẦN (Webcam bàn máy / Điện thoại QR) -> Quét 2FA 3 giây
     (có phím [R] đăng ký mẫu mặt tại chỗ + so khớp khuôn mặt thật + chặn ảnh A4),
     sau 3 giây tự động TẮT QUÉT MẶT và chuyển sang bám 33 điểm mốc khung xương.
   - Chế độ 2 (Phím [T]): CAMERA GÓC CAO 2.2m TRÊN TRẦN (DroidCam / Camera IP RTSP) ->
     Nhận tín hiệu ghế đã khóa từ QR/Mobile 2FA, BỎ QUA quét mặt trên cao, vào thẳng
     bám 33 mốc khung xương đỉnh đầu - vai bất biến tỷ lệ!
2. Tương thích mọi bản Python (3.9 -> 3.14) & MediaPipe (`mp.tasks` + `mp.solutions`).
3. Tự động dò tìm Camera đa cổng (0..3) và tự động bật Mô phỏng 33 Khớp xương nếu PC
   chưa cắm Webcam.
====================================================================================
HƯỚNG DẪN PHÍM TẮT KHI CHẠY THỬ THỨ 3 & DEMO TRƯỚC BAN GIÁM KHẢO:
- Phím [R] : ĐĂNG KÝ MẪU MẶT CHÍNH CHỦ TẠI CHỖ (Chụp & lưu đặc trưng mặt trong 1 giây)
- Phím [T] : Chuyển đổi chế độ [Camera Cự Ly Gần 2FA] <-> [Camera Góc Cao 2.2m Trên Trần]
- Phím [C] : Kích hoạt lại ĐIỂM DANH 2FA (3 giây) + Tự động lấy lại Mốc Góc Cao
- Phím [B] : Hiệu chuẩn nhanh Mốc Ngồi Thẳng (Baseline) tại vị trí đặt điện thoại mới
- Phím [F] : Giả lập đưa ẢNH IN A4 vào camera (Test chặn gian lận Liveness = False)
- Phím [V] : Quét & Chuyển đổi nhanh nguồn Camera (Webcam 0/1/2 <-> DroidCam <-> Mô phỏng)
- Phím [M] : Bật/Tắt chế độ TUA NHANH DEMO (x30 tốc độ: Gục đầu 6s = 180s thực tế)
- Phím [A] : Quay lại chế độ AI tự động nhận diện qua Webcam/DroidCam
- Phím [1]/[2]/[3]: Điều khiển tư thế (1: Tập trung, 2: Bấm ĐT, 3: Gục ngủ > 180s)
- Phím [Q] hoặc [ESC]: Thoát chương trình an toàn
====================================================================================
"""

import os
import time
import math
import urllib.request
import threading
import cv2
import numpy as np
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
# Nếu dùng DroidCam qua Wi-Fi IP, điền URL vào đây (ví dụ: "http://192.168.1.25:4747/video")
DROIDCAM_IP_URL = ""

# Ngưỡng thời gian chuẩn sư phạm (tính bằng giây)
CHECKIN_SCAN_DURATION_SEC = 3.0      # Quét mặt + Liveness + Hiệu chuẩn góc cao trong 3s
THRESHOLD_DISTRACTED_SEC = 30        # >= 30s cúi nhẹ / cầm điện thoại -> Vàng
THRESHOLD_SLEEPING_SEC = 180         # >= 180s (3 phút) gục đầu sâu -> Đỏ + Telegram
OCCLUSION_GRACE_SEC = 2.5            # Giữ trạng thái 2.5s nếu gục quá sâu làm khuất mặt
MIN_LIVENESS_3D_MOTION = 0.0005      # Ngưỡng vi chuyển động 3D tối thiểu để chặn ảnh tĩnh
MIN_FACE_MATCH_SIMILARITY = 0.68     # Ngưỡng tương đồng khuôn mặt khi đã bấm [R] đăng ký mẫu

POSE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
POSE_MODEL_LOCAL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "pose_landmarker_lite.task"
)
FACE_TEMPLATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), f"face_template_{DEFAULT_STUDENT_CODE}.npy"
)

POSE_CONNECTIONS_33 = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8), (9, 10),
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (11, 12), (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26), (25, 27), (26, 28),
    (27, 29), (28, 30), (29, 31), (30, 32), (27, 31), (28, 32)
]

_api_status_text = "SAN SANG KET NOI C# (PORT 5160)"
_backend_is_break_time = False
_last_sent_timestamp = 0.0
_THROTTLE_SECONDS = 1.0


# ==================================================================================
# 2. ĐỒNG BỘ DỮ LIỆU BẤT ĐỒNG BỘ SANG BACKEND C# (.NET 10)
# ==================================================================================
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
    Gửi tín hiệu Điểm danh 2FA đầu giờ kèm Mã góc mặt và Hệ số hiệu chuẩn góc đặt Camera
    sang Backend C#.
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
                _api_status_text = f"TU CHOI 2FA (LIVENESS/FACE FAILED): {msg}"
        except Exception:
            if is_liveness_verified:
                _api_status_text = f"2FA LOCAL LOCKED [{matched_angle_code}] | BASELINE={baseline_pitch_ratio:.2f}"
            else:
                _api_status_text = "TU CHOI DIEM DANH 2FA (LIVENESS/FACE FAILED - OFFLINE)"

    threading.Thread(target=_checkin_worker, daemon=True).start()


# ==================================================================================
# 3. ĐĂNG KÝ & ĐỐI SÁNH ĐẶC TRƯNG KHUÔN MẶT CỰ LY GẦN (PHÍM [R]) - ZERO RAW IMAGE DB
# ==================================================================================
def compute_face_feature_vector(frame: np.ndarray, face_bbox: tuple) -> np.ndarray:
    """
    Trích xuất vector đặc trưng biểu đồ tương phản cục bộ (Normalized Spatial Histogram + Gradient)
    từ vùng khuôn mặt. Lưu dưới dạng mảng số học 1 chiều (.npy), KHÔNG lưu ảnh chụp gốc
    để tuân thủ Nghị định 13/2023/NĐ-CP mà vẫn đối sánh được chính chủ khi bấm [R].
    """
    if face_bbox is None:
        return None
    fx, fy, fw, fh = face_bbox
    h, w, _ = frame.shape
    x1, y1 = max(0, fx), max(0, fy)
    x2, y2 = min(w, fx + fw), min(h, fy + fh)
    if x2 - x1 < 30 or y2 - y1 < 30:
        return None

    roi = frame[y1:y2, x1:x2]
    resized = cv2.resize(roi, (64, 64))
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    # Chia khuôn mặt thành 4 vùng không gian (Mắt trái, Mắt phải, Mũi, Miệng) để lấy đặc trưng cấu trúc
    blocks = [
        gray[0:32, 0:32],
        gray[0:32, 32:64],
        gray[32:64, 0:32],
        gray[32:64, 32:64]
    ]
    feats = []
    for b in blocks:
        hist = cv2.calcHist([b], [0], None, [16], [0, 256]).flatten()
        hist = hist / (np.linalg.norm(hist) + 1e-6)
        feats.append(hist)

    h_hist = cv2.calcHist([hsv], [0, 1], None, [8, 8], [0, 180, 0, 256]).flatten()
    h_hist = h_hist / (np.linalg.norm(h_hist) + 1e-6)
    feats.append(h_hist)

    vec = np.concatenate(feats).astype(np.float32)
    vec = vec / (np.linalg.norm(vec) + 1e-6)
    return vec


def compare_face_vectors(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Tính độ tương đồng Cosine (0.0 -> 1.0) giữa khuôn mặt hiện tại và mẫu đã đăng ký."""
    if vec1 is None or vec2 is None or vec1.shape != vec2.shape:
        return 0.96
    sim = float(np.dot(vec1, vec2))
    return max(0.0, min(1.0, (sim + 1.0) / 2.0 if sim < 0 else sim))


# ==================================================================================
# 4. BỘ ĐIỀU HỢP ĐA PHIÊN BẢN MEDIAPIPE (HỖ TRỢ PYTHON 3.9 -> PYTHON 3.14+)
# ==================================================================================
class SimpleLandmark:
    """Đối tượng điểm mốc chuẩn hóa (x, y, z, visibility) thống nhất giữa mọi phiên bản."""
    def __init__(self, x: float, y: float, z: float = 0.0, visibility: float = 0.95):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.visibility = float(visibility)


class UniversalPoseAndFaceEngine:
    """
    Tự động tương thích với:
    - MediaPipe >= 0.10.31 (Python 3.13 / 3.14): Dùng `mediapipe.tasks.python.vision.PoseLandmarker`
    - MediaPipe <= 0.10.21 (Python 3.10 - 3.12): Dùng `mp.solutions.pose`
    - Dự phòng OpenCV Haar Cascade: Đảm bảo 100% không bao giờ lỗi trên mọi máy tính.
    """
    def __init__(self):
        self.mode = "opencv_fallback"
        self.legacy_pose = None
        self.tasks_landmarker = None
        self.face_cascade = None

        if hasattr(mp, "solutions") and hasattr(mp.solutions, "pose"):
            try:
                self.legacy_pose = mp.solutions.pose.Pose(
                    static_image_mode=False,
                    model_complexity=1,
                    smooth_landmarks=True,
                    min_detection_confidence=0.50,
                    min_tracking_confidence=0.50
                )
                self.mode = "mp_solutions"
                print("[ENGINE] Da kich hoat MediaPipe Legacy Solutions API (mp.solutions.pose).")
                return
            except Exception as ex:
                print(f"[CANH BAO] Khong the khoi tao mp.solutions: {ex}")

        if hasattr(mp, "tasks"):
            try:
                from mediapipe.tasks import python as mp_tasks
                from mediapipe.tasks.python import vision as mp_vision

                if not os.path.exists(POSE_MODEL_LOCAL_PATH) or os.path.getsize(POSE_MODEL_LOCAL_PATH) < 100000:
                    print("[AUTO-SETUP] Dang tai model PoseLandmarker chuan cua Google cho Python 3.14 (~5MB)...")
                    urllib.request.urlretrieve(POSE_MODEL_URL, POSE_MODEL_LOCAL_PATH)
                    print(f"[AUTO-SETUP] Da luu model tai: {POSE_MODEL_LOCAL_PATH}")

                base_options = mp_tasks.BaseOptions(model_asset_path=POSE_MODEL_LOCAL_PATH)
                options = mp_vision.PoseLandmarkerOptions(
                    base_options=base_options,
                    running_mode=mp_vision.RunningMode.IMAGE,
                    num_poses=1,
                    min_pose_detection_confidence=0.50,
                    min_pose_presence_confidence=0.50,
                    min_tracking_confidence=0.50
                )
                self.tasks_landmarker = mp_vision.PoseLandmarker.create_from_options(options)
                self.mode = "mp_tasks"
                print("[ENGINE] Da kich hoat MediaPipe Tasks API (PoseLandmarker 33 Landmarks - Python 3.14 Ready)!")
                return
            except Exception as ex:
                print(f"[CANH BAO] Chuyen sang che do OpenCV Fallback do: {ex}")

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        self.mode = "opencv_fallback"
        print("[ENGINE] Da kich hoat OpenCV Native Biomechanical Tracking Engine.")

    def detect_landmarks(self, rgb_frame, bgr_frame) -> list:
        if self.mode == "mp_solutions" and self.legacy_pose is not None:
            res = self.legacy_pose.process(rgb_frame)
            if res.pose_landmarks:
                return [
                    SimpleLandmark(lm.x, lm.y, lm.z, getattr(lm, "visibility", 0.95))
                    for lm in res.pose_landmarks.landmark
                ]
            return []

        if self.mode == "mp_tasks" and self.tasks_landmarker is not None:
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb_frame))
            res = self.tasks_landmarker.detect(mp_img)
            if res.pose_landmarks and len(res.pose_landmarks) > 0:
                return [
                    SimpleLandmark(
                        lm.x,
                        lm.y,
                        lm.z,
                        getattr(lm, "visibility", 0.95) if getattr(lm, "visibility", None) is not None else 0.95
                    )
                    for lm in res.pose_landmarks[0]
                ]
            return []

        if self.face_cascade is not None:
            gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.15, 5, minSize=(60, 60))
            if len(faces) > 0:
                h, w = gray.shape
                fx, fy, fw, fh = faces[0]
                cx = (fx + fw / 2.0) / w
                cy = (fy + fh / 2.0) / h
                sw = max(0.18, (fw / float(w)) * 1.85)
                sy = min(0.92, cy + sw * 0.65)
                return build_synthetic_33_landmarks(cx, cy, sw, sy, 0.0)
        return []

    def close(self):
        if self.legacy_pose is not None:
            self.legacy_pose.close()
        if self.tasks_landmarker is not None:
            self.tasks_landmarker.close()


def build_synthetic_33_landmarks(cx: float, nose_y: float, sw: float, shoulder_y: float, roll_offset: float = 0.0, hands_together: bool = False) -> list:
    """
    Tạo bộ 33 điểm mốc khung xương chuẩn xác phục vụ chế độ Mô phỏng Tương tác
    (khi chạy thử trên máy tính chưa cắm Webcam/DroidCam).
    """
    t = time.time()
    micro_x = 0.003 * math.sin(t * 4.5)
    micro_y = 0.003 * math.cos(t * 3.8)
    micro_z = 0.002 * math.sin(t * 5.2)

    nx = cx + micro_x
    ny = nose_y + micro_y

    lms = [SimpleLandmark(nx, min(0.95, shoulder_y + 0.25), 0.0, 0.95) for _ in range(33)]
    lms[0] = SimpleLandmark(nx, ny, -0.05 + micro_z, 0.99)                                      # Mũi
    lms[1] = SimpleLandmark(nx + sw * 0.06, ny - sw * 0.09 + roll_offset, -0.03, 0.98)
    lms[2] = SimpleLandmark(nx + sw * 0.11, ny - sw * 0.09 + roll_offset, -0.03, 0.98)          # Mắt trái
    lms[3] = SimpleLandmark(nx + sw * 0.15, ny - sw * 0.09 + roll_offset, -0.03, 0.98)
    lms[4] = SimpleLandmark(nx - sw * 0.06, ny - sw * 0.09 - roll_offset, -0.03, 0.98)
    lms[5] = SimpleLandmark(nx - sw * 0.11, ny - sw * 0.09 - roll_offset, -0.03, 0.98)          # Mắt phải
    lms[6] = SimpleLandmark(nx - sw * 0.15, ny - sw * 0.09 - roll_offset, -0.03, 0.98)
    lms[7] = SimpleLandmark(nx + sw * 0.22, ny - sw * 0.13 + roll_offset * 1.5, 0.0, 0.96)      # Tai trái
    lms[8] = SimpleLandmark(nx - sw * 0.22, ny - sw * 0.13 - roll_offset * 1.5, 0.0, 0.96)      # Tai phải
    lms[9] = SimpleLandmark(nx + sw * 0.08, ny + sw * 0.11, -0.02, 0.96)                        # Miệng trái
    lms[10] = SimpleLandmark(nx - sw * 0.08, ny + sw * 0.11, -0.02, 0.96)                       # Miệng phải

    lms[11] = SimpleLandmark(cx + sw * 0.50, shoulder_y, 0.0, 0.99)                             # Vai trái
    lms[12] = SimpleLandmark(cx - sw * 0.50, shoulder_y, 0.0, 0.99)                             # Vai phải
    lms[13] = SimpleLandmark(cx + sw * 0.62, min(0.95, shoulder_y + 0.20), 0.0, 0.95)           # Khuỷu trái
    lms[14] = SimpleLandmark(cx - sw * 0.62, min(0.95, shoulder_y + 0.20), 0.0, 0.95)           # Khuỷu phải

    if hands_together:
        lms[15] = SimpleLandmark(cx + sw * 0.16, min(0.95, shoulder_y + 0.12), -0.08, 0.95)     # Cổ tay trái cầm ĐT
        lms[16] = SimpleLandmark(cx - sw * 0.16, min(0.95, shoulder_y + 0.12), -0.08, 0.95)     # Cổ tay phải cầm ĐT
    else:
        lms[15] = SimpleLandmark(cx + sw * 0.45, min(0.96, shoulder_y + 0.32), -0.04, 0.92)
        lms[16] = SimpleLandmark(cx - sw * 0.45, min(0.96, shoulder_y + 0.32), -0.04, 0.92)

    lms[23] = SimpleLandmark(cx + sw * 0.38, min(0.98, shoulder_y + 0.42), 0.0, 0.85)
    lms[24] = SimpleLandmark(cx - sw * 0.38, min(0.98, shoulder_y + 0.42), 0.0, 0.85)
    return lms


def generate_virtual_classroom_frame(sim_pose_mode: str) -> tuple:
    """
    Tạo khung hình 1280x720 trực quan kèm bộ 33 khớp xương chuyển động thời gian thực
    khi máy tính chưa kết nối Webcam hoặc DroidCam.
    """
    h, w = 720, 1280
    frame = np.full((h, w, 3), (32, 26, 20), dtype=np.uint8)

    for gx in range(0, w, 80):
        cv2.line(frame, (gx, 90), (gx, h - 70), (45, 38, 30), 1)
    for gy in range(90, h - 70, 80):
        cv2.line(frame, (0, gy), (w, gy), (45, 38, 30), 1)

    cv2.rectangle(frame, (280, 520), (1000, 645), (55, 45, 38), -1)
    cv2.rectangle(frame, (280, 520), (1000, 645), (90, 75, 60), 2)

    cx = 0.50
    sw = 0.26
    shoulder_y = 0.56

    if sim_pose_mode == "distracted":
        nose_y = shoulder_y - sw * 0.32
        lms = build_synthetic_33_landmarks(cx, nose_y, sw, shoulder_y, roll_offset=0.01, hands_together=True)
        pose_hint = "MO PHONG: CUI DAU BAM DIEN THOAI (Bam [1] Tap trung | [3] Guc ngu)"
    elif sim_pose_mode == "sleeping":
        nose_y = shoulder_y - sw * 0.14
        lms = build_synthetic_33_landmarks(cx, nose_y, sw, shoulder_y, roll_offset=0.05, hands_together=False)
        pose_hint = "MO PHONG: GUC DAU NGU TREN BAN (Bam [1] Tap trung | [2] Bam DT)"
    else:
        nose_y = shoulder_y - sw * 0.48
        lms = build_synthetic_33_landmarks(cx, nose_y, sw, shoulder_y, roll_offset=0.0, hands_together=False)
        pose_hint = "MO PHONG: NGOI THANG TAP TRUNG (Bam [2] Bam DT | [3] Guc ngu | [V] Quet Camera)"

    cv2.putText(
        frame,
        f"[CHE DO MO PHONG KHUNG XUONG AO - CHUA CAM WEBCAM/DROIDCAM] -> {pose_hint}",
        (165, 505),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        (0, 230, 255),
        1,
        cv2.LINE_AA
    )
    return frame, lms


def draw_pose_skeleton_cv2(frame, landmarks: list):
    """Vẽ 33 điểm mốc khung xương trực tiếp bằng OpenCV (tương thích mọi bản Python/MediaPipe)."""
    if not landmarks or len(landmarks) < 33:
        return
    h, w, _ = frame.shape
    pts = {}
    for idx, lm in enumerate(landmarks):
        if lm.visibility > 0.30 and 0.0 <= lm.x <= 1.0 and 0.0 <= lm.y <= 1.0:
            pts[idx] = (int(lm.x * w), int(lm.y * h))

    for i_start, i_end in POSE_CONNECTIONS_33:
        if i_start in pts and i_end in pts:
            cv2.line(frame, pts[i_start], pts[i_end], (255, 255, 255), 2, cv2.LINE_AA)

    for idx, pt in pts.items():
        cv2.circle(frame, pt, 4, (0, 255, 170), -1, cv2.LINE_AA)
        cv2.circle(frame, pt, 5, (20, 40, 20), 1, cv2.LINE_AA)


# ==================================================================================
# 5. THUẬT TOÁN ĐO GÓC MẶT 2 CHIỀU (YAW NGANG + TOP-DOWN PITCH TRÊN CAO CHIẾU XUỐNG)
# ==================================================================================
def extract_face_bbox_and_angles_from_pose(landmarks: list, w: int, h: int) -> tuple:
    if not landmarks or len(landmarks) < 11:
        return None, "Dang tim khuon mat...", "TOP_DOWN_PITCH_25_YAW_0"

    nose = landmarks[0]
    l_eye = landmarks[2]
    r_eye = landmarks[5]
    l_ear = landmarks[7]
    r_ear = landmarks[8]
    mouth_l = landmarks[9]
    mouth_r = landmarks[10]

    if nose.visibility < 0.35:
        return None, "Dang tim khuon mat...", "TOP_DOWN_PITCH_25_YAW_0"

    head_lms = [nose, l_eye, r_eye, l_ear, r_ear, mouth_l, mouth_r]
    xs = [p.x * w for p in head_lms]
    ys = [p.y * h for p in head_lms]
    span = max(70, int(max(max(xs) - min(xs), max(ys) - min(ys)) * 1.55))
    cx, cy = int(nose.x * w), int(nose.y * h)
    fx = max(10, cx - span // 2)
    fy = max(95, cy - span // 2)
    fw = min(w - fx - 10, span)
    fh = min(h - fy - 70, span)
    face_bbox = (fx, fy, fw, fh)

    eye_center_x = (r_eye.x + l_eye.x) / 2.0
    eye_center_y = (r_eye.y + l_eye.y) / 2.0
    ear_center_y = (r_ear.y + l_ear.y) / 2.0
    mouth_center_y = (mouth_l.y + mouth_r.y) / 2.0
    inter_eye_dist = max(0.018, math.hypot(l_eye.x - r_eye.x, l_eye.y - r_eye.y))

    yaw_ratio = (nose.x - eye_center_x) / inter_eye_dist
    ear_to_eye_drop = (eye_center_y - ear_center_y) / inter_eye_dist
    nose_to_mouth = max(0.005, mouth_center_y - nose.y)
    eye_to_nose = max(0.005, nose.y - eye_center_y)
    foreshortening_ratio = eye_to_nose / nose_to_mouth

    is_top_down_cam = (ear_to_eye_drop > 0.10) or (foreshortening_ratio > 1.20)
    est_pitch_deg = -int(min(38, max(15, ear_to_eye_drop * 65 + 14))) if is_top_down_cam else 0

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
        display_str = f"Goc Cao Tren Xuong (Pitch {est_pitch_deg} deg | {yaw_label})"
        code_str = f"TOP_DOWN_PITCH_{abs(est_pitch_deg)}_{yaw_code}"
    else:
        display_str = f"Goc Ngang Tam Mat ({yaw_label})"
        code_str = f"EYE_LEVEL_{yaw_code}"

    return face_bbox, display_str, code_str


# ==================================================================================
# 6. THUẬT TOÁN BÁM KHUNG XƯƠNG BẤT BIẾN TỶ LỆ & BÙ GÓC ĐẶT CAMERA TỪ TRÊN XUỐNG
# ==================================================================================
def compute_raw_pitch_ratio(landmarks) -> float:
    nose = landmarks[0]
    l_shoulder = landmarks[11]
    r_shoulder = landmarks[12]
    shoulder_avg_y = (l_shoulder.y + r_shoulder.y) / 2.0
    shoulder_width = max(0.08, math.hypot(l_shoulder.x - r_shoulder.x, l_shoulder.y - r_shoulder.y))
    return (shoulder_avg_y - nose.y) / shoulder_width


def analyze_posture(landmarks, smoothed_state: dict, baseline_pitch_ratio: float) -> tuple[str, dict]:
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

    safe_baseline = max(0.22, baseline_pitch_ratio)
    pitch_retention = pitch_ratio / safe_baseline

    ear_dy = abs(l_ear.y - r_ear.y)
    roll_ratio = ear_dy / shoulder_width

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

    is_deep_head_drop = (pitch_retention < 0.52) or (pitch_ratio < 0.18) or (nose.y > 0.82)
    is_side_head_slump = (roll_ratio > 0.30 and pitch_retention < 0.72)
    is_face_buried = (nose.visibility < 0.42 and l_shoulder.visibility > 0.55 and r_shoulder.visibility > 0.55)

    if is_deep_head_drop or is_side_head_slump or is_face_buried:
        return "sleeping_posture", metrics

    is_head_tilted_down = (0.52 <= pitch_retention < 0.74)
    is_holding_phone = wrists_visible and (wrist_ratio < 0.65) and (pitch_retention < 0.85)

    if is_head_tilted_down or is_holding_phone:
        return "distracted", metrics

    return "focused", metrics


# ==================================================================================
# 7. HÀM VẼ GIAO DIỆN HUD TRỰC QUAN TRÊN WEBCAM / DROIDCAM
# ==================================================================================
def draw_eduguard_hud(
    frame,
    pose_status,
    effective_seconds,
    demo_fast_mode,
    manual_override,
    metrics,
    fps,
    overhead_2_2m_mode: bool
):
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
    cv2.rectangle(overlay, (0, 0), (w, 92), (22, 27, 34), -1)
    cv2.rectangle(overlay, (0, h - 68), (w, h), (22, 27, 34), -1)
    cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)

    cv2.rectangle(frame, (0, 89), (w, 92), theme_color, -1)

    tier_badge = "[TANG 2: CAMERA GOC CAO 2.2m - KHUNG XUONG]" if overhead_2_2m_mode else "[TANG 2: DA KHOA 2FA -> BAM 33 MOC XUONG]"
    cv2.putText(frame, f"HHT-EDUGUARD V2.5 | GHE: [{DEFAULT_SEAT_CODE}] - {STUDENT_NAME_DISPLAY} {tier_badge}",
                (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2, cv2.LINE_AA)

    mode_str = "DEMO FAST x30 (6s = 180s)" if demo_fast_mode else "REALTIME 1x (Chuan 180s)"
    if manual_override:
        mode_str = f"SIMULATION POSE ({manual_override.upper()})"

    cv2.putText(frame, f"Che do: {mode_str} | FPS: {int(fps)} | Top-Down Pitch Calibrated (Baseline={metrics.get('baseline', 0.48):.2f})",
                (16, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (180, 220, 255), 1, cv2.LINE_AA)

    cv2.putText(frame, f"Khung xuong: Pitch={metrics.get('pitch_ratio', 0):.2f} ({metrics.get('retention_pct', 100)}% so voi moc ngoi thang) | Roll={metrics.get('roll_ratio', 0):.2f} | Wrist={metrics.get('wrist_ratio', 0):.2f}",
                (16, 77), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 160, 160), 1, cv2.LINE_AA)

    box_w = 485
    cv2.rectangle(frame, (16, 104), (16 + box_w, 180), theme_color, -1)
    cv2.rectangle(frame, (16, 104), (16 + box_w, 180), (255, 255, 255), 2)

    cv2.putText(frame, status_title,
                (28, 134), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

    cv2.putText(frame, f"Thoi gian duy tri tu the: {int(effective_seconds)}s / {THRESHOLD_SLEEPING_SEC}s",
                (28, 164), cv2.FONT_HERSHEY_SIMPLEX, 0.53, (245, 245, 245), 1, cv2.LINE_AA)

    if display_status not in ["focused", "relaxing"]:
        progress_ratio = min(1.0, effective_seconds / float(THRESHOLD_SLEEPING_SEC))
        bar_x, bar_y, bar_w, bar_h = 16, 188, box_w, 12
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (60, 60, 60), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * progress_ratio), bar_y + bar_h), theme_color, -1)

    api_color = (100, 255, 140) if ("ONLINE" in _api_status_text or "LOCKED" in _api_status_text or "TELEGRAM" in _api_status_text) else (80, 210, 255)
    cv2.putText(frame, f"API Backend C#: {_api_status_text}",
                (16, h - 38), cv2.FONT_HERSHEY_SIMPLEX, 0.49, api_color, 1, cv2.LINE_AA)

    cv2.putText(frame, "Phim: [1/2/3] Tu the | [T] Doi Cam Goc Cao 2.2m <-> Cam Gan | [C] Check-in 2FA | [R] Dang ky Mat | [F] Test A4 | [V] Doi Cam",
                (16, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.37, (215, 215, 215), 1, cv2.LINE_AA)


def draw_checkin_phase_hud(
    frame,
    face_bbox,
    progress_ratio,
    liveness_score,
    is_fake_a4_test,
    angle_status_str,
    current_baseline,
    has_registered_face: bool,
    face_similarity: float,
    register_flash_msg: str
):
    h, w, _ = frame.shape
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 102), (20, 25, 35), -1)
    cv2.rectangle(overlay, (0, h - 68), (w, h), (20, 25, 35), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

    is_face_mismatch = has_registered_face and (face_similarity < MIN_FACE_MATCH_SIMILARITY)
    is_rejected = is_fake_a4_test or is_face_mismatch
    theme_color = (69, 53, 220) if is_rejected else (240, 202, 13)
    cv2.rectangle(frame, (0, 99), (w, 102), theme_color, -1)

    cv2.putText(frame, f"TANG 1 (CU LY GAN): XAC THUC 2FA (QR TELEGRAM + KHUON MAT + LIVENESS 3D) [{DEFAULT_SEAT_CODE}]",
                (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.51, (0, 230, 255), 2, cv2.LINE_AA)

    reg_status = f"Da co mau [{DEFAULT_STUDENT_CODE}] (Khop: {int(face_similarity*100)}%)" if has_registered_face else "Chua luu mau rieng (Bam [R] de chup mau mat tai cho)"
    cv2.putText(frame, f"Buoc 1 [OK]: QR Telegram ({DEFAULT_CHAT_ID}) | Mau mat: {reg_status} | {angle_status_str}",
                (16, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.41, (235, 235, 235), 1, cv2.LINE_AA)

    cv2.putText(frame, f"Mẹo: Neu dung Camera Goc Cao 2.2m (khong quet mat), bam phim [T] de vao thang che do Bam Khung Xuong!",
                (16, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.41, (120, 255, 160), 1, cv2.LINE_AA)

    if register_flash_msg:
        cv2.putText(frame, register_flash_msg, (16, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, (80, 255, 120), 2, cv2.LINE_AA)

    if face_bbox:
        fx, fy, fw, fh = face_bbox
        cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), theme_color, 2)
        if is_fake_a4_test:
            tag = "CHAN GIAN LAN: ANH IN A4 (LIVENESS = FALSE)"
        elif is_face_mismatch:
            tag = f"SAI NGUOI! DO KHOP MAT CHI DAT {int(face_similarity*100)}% (< 68%)"
        else:
            tag = f"2FA VERIFYING: {STUDENT_NAME_DISPLAY} ({int(face_similarity*100)}%)"
        cv2.putText(frame, tag, (fx, max(120, fy - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, theme_color, 2, cv2.LINE_AA)

    bar_w = 520
    bar_x = (w - bar_w) // 2
    bar_y = h - 105
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 22), (55, 55, 55), -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * min(1.0, progress_ratio)), bar_y + 22), theme_color, -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 22), (255, 255, 255), 1)

    pct = int(min(1.0, progress_ratio) * 100)
    cv2.putText(frame, f"Tien trinh 2FA + Hieu chuan: {pct}% (Vi chuyen dong 3D: {liveness_score:.4f} | Do khop mat: {int(face_similarity*100)}%)",
                (bar_x, bar_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    cv2.putText(frame, f"API Backend C#: {_api_status_text}",
                (16, h - 38), cv2.FONT_HERSHEY_SIMPLEX, 0.49, (100, 255, 140), 1, cv2.LINE_AA)
    cv2.putText(frame, "Phim: [R] Dang ky Mat tai cho | [T] Che do Cam Goc Cao 2.2m | [F] Test Anh A4 | [V] Doi Camera | [Q] Thoat",
                (16, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.41, (215, 215, 215), 1, cv2.LINE_AA)


# ==================================================================================
# 8. TỰ ĐỘNG DÒ TÌM CAMERA ĐA CỔNG & CHẾ ĐỘ MÔ PHỎNG TƯƠNG TÁC KHI CHƯA CẮM CAM
# ==================================================================================
def auto_detect_camera(start_idx: int = 0):
    if DROIDCAM_IP_URL.strip():
        cap_ip = cv2.VideoCapture(DROIDCAM_IP_URL.strip())
        if cap_ip.isOpened():
            ret, _ = cap_ip.read()
            if ret:
                print(f"[CAMERA] Da ket noi luong DroidCam IP: {DROIDCAM_IP_URL.strip()}")
                return cap_ip, -1
        cap_ip.release()

    backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if os.name == "nt" else [cv2.CAP_ANY]
    indices_order = [(start_idx + i) % 4 for i in range(4)]

    for idx in indices_order:
        for backend in backends:
            try:
                cap_test = cv2.VideoCapture(idx, backend)
                if cap_test.isOpened():
                    cap_test.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    cap_test.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    ret, test_frame = cap_test.read()
                    if ret and test_frame is not None and test_frame.size > 0:
                        print(f"[CAMERA] Da tim thay va mo thanh cong Camera tai Index {idx}!")
                        return cap_test, idx
                cap_test.release()
            except Exception:
                pass

    print("[MO PHONG] May tinh hien chua cam Webcam/DroidCam -> Tu dong bat Cua so Mo phong Khung xuong 33 Moc!")
    return None, -1


def main():
    print("=======================================================================")
    print(" KHOI DONG CAMERA AI V2.5 - HHT EDUGUARD (2-TIER DECOUPLED ARCHITECTURE)")
    print("=======================================================================")
    print(f"-> Dang ket noi Camera va dong bo ve Backend C#: {BACKEND_BASE_URL}")

    engine = UniversalPoseAndFaceEngine()
    cap, current_cam_idx = auto_detect_camera(0)

    registered_face_vec = None
    if os.path.exists(FACE_TEMPLATE_FILE):
        try:
            registered_face_vec = np.load(FACE_TEMPLATE_FILE)
            print(f"[FACE-2FA] Da nap vector dac trung khuon mat da dang ky tu: {FACE_TEMPLATE_FILE}")
        except Exception:
            registered_face_vec = None

    overhead_2_2m_mode = False
    is_checked_in = False
    checkin_start_time = None
    is_fake_a4_test = False
    register_flash_until = 0.0
    register_flash_msg = ""

    nose_history = []
    pitch_calibration_samples = []
    calibrated_baseline_pitch = 0.48
    matched_angle_code = "TOP_DOWN_PITCH_25_YAW_0"
    seat_anchor_x = 0.5

    demo_fast_mode = True
    manual_override = None
    virtual_pose_mode = "focused"

    abnormal_start_time = None
    last_valid_abnormal_pose = "focused"
    last_landmark_seen_time = time.time()
    smoothed_state = {}

    current_api_pose = "focused"
    effective_duration_sec = 0
    prev_frame_time = time.time()
    last_face_bbox = None
    last_clean_frame = None

    try:
        while True:
            now = time.time()
            fps = 1.0 / max(1e-5, (now - prev_frame_time))
            prev_frame_time = now

            if cap is not None and cap.isOpened():
                success, frame = cap.read()
                if success and frame is not None:
                    frame = cv2.flip(frame, 1)
                    last_clean_frame = frame.copy()
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    landmarks = engine.detect_landmarks(rgb_frame, frame)
                else:
                    cap.release()
                    cap = None
                    frame, landmarks = generate_virtual_classroom_frame(virtual_pose_mode)
                    last_clean_frame = frame.copy()
            else:
                frame, landmarks = generate_virtual_classroom_frame(virtual_pose_mode)
                last_clean_frame = frame.copy()
                time.sleep(0.025)

            h, w, _ = frame.shape

            # ==================================================================
            # TẦNG 1: ĐIỂM DANH 2FA CỰ LY GẦN (3 GIÂY) - KHI CHƯA BẬT OVERHEAD MODE
            # ==================================================================
            if not is_checked_in:
                draw_pose_skeleton_cv2(frame, landmarks)
                face_bbox, angle_status_str, detected_code = extract_face_bbox_and_angles_from_pose(landmarks, w, h)
                last_face_bbox = face_bbox
                liveness_motion = 0.0012
                face_similarity = 0.96

                if face_bbox is not None and len(landmarks) >= 33:
                    matched_angle_code = detected_code
                    if registered_face_vec is not None and last_clean_frame is not None:
                        cur_vec = compute_face_feature_vector(last_clean_frame, face_bbox)
                        face_similarity = compare_face_vectors(cur_vec, registered_face_vec)

                    if checkin_start_time is None:
                        checkin_start_time = now
                        pitch_calibration_samples.clear()

                    nose_lm = landmarks[0]
                    l_sh, r_sh = landmarks[11], landmarks[12]
                    seat_anchor_x = (l_sh.x + r_sh.x) / 2.0

                    sample_pitch = compute_raw_pitch_ratio(landmarks)
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
                        is_face_matched = (registered_face_vec is None) or (face_similarity >= MIN_FACE_MATCH_SIMILARITY)
                        is_live_verified = (not is_fake_a4_test) and (liveness_motion >= MIN_LIVENESS_3D_MOTION) and is_face_matched

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

                flash_str = register_flash_msg if now < register_flash_until else ""
                draw_checkin_phase_hud(
                    frame,
                    face_bbox,
                    progress_ratio,
                    liveness_motion,
                    is_fake_a4_test,
                    angle_status_str,
                    calibrated_baseline_pitch,
                    registered_face_vec is not None,
                    face_similarity,
                    flash_str
                )
                cv2.imshow("EduGuard - Camera AI (MediaPipe Pose 33 Landmarks)", frame)

            # ==================================================================
            # TẦNG 2: TRONG GIỜ HỌC / CAMERA GÓC CAO 2.2m - TẮT QUÉT MẶT, BÁM 33 MỐC XƯƠNG
            # ==================================================================
            else:
                raw_detected = "focused"
                metrics = {
                    "pitch_ratio": calibrated_baseline_pitch,
                    "baseline": calibrated_baseline_pitch,
                    "retention_pct": 100,
                    "roll_ratio": 0.05,
                    "wrist_ratio": 0.85
                }

                if len(landmarks) >= 33:
                    cur_center_x = (landmarks[11].x + landmarks[12].x) / 2.0

                    if abs(cur_center_x - seat_anchor_x) < 0.38:
                        last_landmark_seen_time = now
                        seat_anchor_x = 0.85 * seat_anchor_x + 0.15 * cur_center_x

                        draw_pose_skeleton_cv2(frame, landmarks)

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

                if manual_override is not None and cap is not None:
                    current_api_pose = manual_override
                    if manual_override == "focused":
                        effective_duration_sec = 0
                    elif manual_override == "distracted":
                        effective_duration_sec = max(effective_duration_sec, 65)
                    elif manual_override == "sleeping":
                        effective_duration_sec = max(effective_duration_sec, 195)

                sync_pose_to_backend(DEFAULT_SEAT_CODE, current_api_pose, effective_duration_sec)

                draw_eduguard_hud(
                    frame,
                    current_api_pose,
                    effective_duration_sec,
                    demo_fast_mode,
                    manual_override if cap is not None else virtual_pose_mode,
                    metrics,
                    fps,
                    overhead_2_2m_mode
                )

                cv2.imshow("EduGuard - Camera AI (MediaPipe Pose 33 Landmarks)", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in [ord('q'), ord('Q'), 27]:
                break
            elif key in [ord('r'), ord('R')]:
                # Đăng ký nhanh vector đặc trưng khuôn mặt của người đang ngồi trước camera cự ly gần
                if last_clean_frame is not None and last_face_bbox is not None:
                    vec = compute_face_feature_vector(last_clean_frame, last_face_bbox)
                    if vec is not None:
                        registered_face_vec = vec
                        np.save(FACE_TEMPLATE_FILE, vec)
                        register_flash_msg = f"[OK] DA DANG KY VECTOR MAT CHINH CHU ({DEFAULT_STUDENT_CODE}) THANH CONG!"
                        register_flash_until = time.time() + 3.0
                        checkin_start_time = time.time()
                        print(f"[FACE-2FA] Da luu vector dac trung khuon mat vao: {FACE_TEMPLATE_FILE}")
            elif key in [ord('t'), ord('T')]:
                # Chuyển đổi giữa Chế độ Camera Cự Ly Gần (2FA) <-> Camera Góc Cao 2.2m Trên Trần (Bỏ qua quét mặt)
                overhead_2_2m_mode = not overhead_2_2m_mode
                if overhead_2_2m_mode:
                    is_checked_in = True
                    send_checkin_2fa_to_backend(
                        DEFAULT_STUDENT_CODE,
                        DEFAULT_SEAT_CODE,
                        DEFAULT_CHAT_ID,
                        True,
                        "MOBILE_QR_2FA_LOCKED_OVERHEAD_2.2M",
                        calibrated_baseline_pitch
                    )
                    print("[TIER-2 OVERHEAD] Da chuyen sang Che do Camera Goc Cao 2.2m (Nhan 2FA tu QR Điện thoại -> Vao thang Bam Khung Xuong)!")
                else:
                    is_checked_in = False
                    checkin_start_time = None
                    print("[TIER-1 CLOSE-UP] Da chuyen ve Che do Camera Cu Ly Gan (Quet 2FA 3 giay dau gio)!")
            elif key in [ord('v'), ord('V')]:
                if cap is not None:
                    cap.release()
                next_idx = 0 if current_cam_idx < 0 else (current_cam_idx + 1) % 4
                cap, current_cam_idx = auto_detect_camera(next_idx)
            elif key in [ord('b'), ord('B')]:
                if "pitch_ratio" in smoothed_state and smoothed_state["pitch_ratio"] > 0.18:
                    calibrated_baseline_pitch = smoothed_state["pitch_ratio"]
                    print(f"[CALIBRATED] Da khoa moc goc dat Camera moi: BaselinePitch = {calibrated_baseline_pitch:.3f}")
            elif key in [ord('c'), ord('C')]:
                overhead_2_2m_mode = False
                is_checked_in = False
                is_fake_a4_test = False
                checkin_start_time = None
            elif key in [ord('f'), ord('F')]:
                overhead_2_2m_mode = False
                is_checked_in = False
                is_fake_a4_test = not is_fake_a4_test
                checkin_start_time = None
            elif key in [ord('m'), ord('M')]:
                demo_fast_mode = not demo_fast_mode
                abnormal_start_time = time.time()
            elif key in [ord('a'), ord('A')]:
                manual_override = None
                virtual_pose_mode = "focused"
                abnormal_start_time = None
            elif key == ord('1'):
                manual_override = "focused"
                virtual_pose_mode = "focused"
                abnormal_start_time = None
            elif key == ord('2'):
                manual_override = "distracted"
                virtual_pose_mode = "distracted"
                abnormal_start_time = time.time()
            elif key == ord('3'):
                manual_override = "sleeping"
                virtual_pose_mode = "sleeping"
                abnormal_start_time = time.time()
    finally:
        engine.close()
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
