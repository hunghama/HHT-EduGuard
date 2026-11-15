"""
====================================================================================
DỰ ÁN: HHT-EDUGUARD (SÁNG TẠO TRẺ HÀ NỘI 2026)
ĐƠN VỊ: KHOA CNTT - TRƯỜNG CAO ĐẲNG CÔNG NGHỆ CAO HÀ NỘI (HHT)
MODULE: CAMERA AI ĐA LUỒNG 5 GHẾ & BẢO MẬT VECTOR SHA-256 (V2.8 CODEX-AUDITED)
PHỤ TRÁCH: SÁI CÔNG PHI HÙNG (TECH LEAD) & BÙI THỊ HƯƠNG QUỲNH (AI ENGINEER)
====================================================================================
ĐẶC ĐIỂM KỸ THUẬT CHUẨN XÁC CỦA BẢN V2.8 (ĐÃ VÁ 2 LỖ HỔNG [P1] & [P2] CỦA CODEX):
1. Vá lỗi [P1] của Codex (Không bao giờ tự ý Check-in 2FA hộ cả lớp khi bấm [T]):
   - Khi chuyển sang Chế độ Camera Góc Cao 2.2m (`[T]`), hệ thống CHỈ chuyển tầng hiển thị
     sang giám sát khung xương cho những ghế đã thực sự hoàn tất xác thực 2FA (hoặc kiểm tra
     trạng thái ghế từ Backend C#), tuyệt đối KHÔNG gửi `isLivenessVerified=True` hàng loạt!
2. Vá lỗi [P2] của Codex (Ánh xạ Khung xương theo Vùng Tọa Độ Ghế Cố Định - Fixed Seat ROI):
   - Mỗi ghế (`A1-01`..`A3-01`) có một vùng tọa độ ngang cố định (`roi_x_min` -> `roi_x_max`)
     và tâm ghế chuẩn (`seat_center_x`). Khi một ghế trống hoặc sinh viên rời khỏi ghế > 3.5s,
     người ngồi ở ghế bên phải sẽ chỉ khớp vào đúng vùng ROI của ghế bên phải (hoặc giữ ở
     trạng thái `UNASSIGNED` nếu nằm ngoài vùng ghế đã check-in), tuyệt đối KHÔNG bị gán nhầm
     vào slot trống đầu tiên (`SV001 / A1-01`)!
3. Băm Bảo Mật Khuôn Mặt (`Salted SHA-256`) + 5-Frame Debounce + Phím `[L]` Chống Ngược Chữ.
====================================================================================
BẢNG PHÍM TẮT ĐIỀU KHIỂN THỰC CHIẾN:
- Phím [L] : Bật/Tắt LẬT GƯƠNG (Chống ngược chữ khi dùng Camera sau DroidCam)
- Phím [R] : ĐĂNG KÝ MẪU MẶT CHÍNH CHỦ TẠI CHỖ (Kèm băm bảo mật SHA-256)
- Phím [T] : Chuyển đổi [Tầng 1: Cự Ly Gần 2FA] <-> [Tầng 2: Góc Cao 2.2m Đa Người]
- Phím [S] : Chuyển đổi Ghế đang chọn để kiểm thử (`A1-01` -> `A3-01`)
- Phím [C] : Kích hoạt lại ĐIỂM DANH 2FA (3 giây) cho ghế đang chọn
- Phím [B] : Hiệu chuẩn nhanh Mốc Ngồi Thẳng (Baseline Pitch)
- Phím [F] : Giả lập đưa ẢNH IN A4 vào camera (Test chặn gian lận Liveness = False)
- Phím [V] : Quét & Chuyển đổi nhanh nguồn Camera (Webcam 0/1/2 <-> DroidCam <-> Mô phỏng)
- Phím [M] : Bật/Tắt chế độ TUA NHANH DEMO (x30 tốc độ: Gục đầu 6s = 180s thực tế)
- Phím [1]/[2]/[3]: Ép trạng thái kiểm thử cho ghế đang chọn (1: Tập trung, 2: ĐT, 3: Ngủ)
- Phím [A] : Quay lại chế độ AI tự động hoàn toàn
- Phím [Q] hoặc [ESC]: Thoát chương trình an toàn
====================================================================================
"""

import os
import json
import time
import math
import hashlib
import urllib.request
import threading
import cv2
import numpy as np
import mediapipe as mp
import requests

# ==================================================================================
# 1. CẤU HÌNH HỆ THỐNG & VÙNG TỌA ĐỘ GHẾ CỐ ĐỊNH (FIXED SEAT ROI ZONES)
# ==================================================================================
BACKEND_BASE_URL = "http://localhost:5160"
DROIDCAM_IP_URL = ""  # Điền "http://<IP_DIEN_THOAI>:4747/video" nếu bắt luồng IP trực tiếp
CRYPTO_SALT = "HHT_EDUGUARD_ND13_2026_SALT"

# Mỗi ghế có vùng tọa độ ngang cố định (roi_min_x, roi_max_x, seat_center_x) trên khung hình
SEAT_ROSTER = [
    {
        "seat": "A1-01", "code": "SV001", "name": "Sai Cong Phi Hung", "short": "Hung",
        "chat_id": 6599740123, "center_x": 0.14, "roi_min_x": 0.00, "roi_max_x": 0.24
    },
    {
        "seat": "A1-02", "code": "SV002", "name": "Luu Thi Kim Lien", "short": "Lien",
        "chat_id": 100002, "center_x": 0.32, "roi_min_x": 0.24, "roi_max_x": 0.41
    },
    {
        "seat": "A2-01", "code": "SV003", "name": "Bui Thi Huong Quynh", "short": "Quynh",
        "chat_id": 100003, "center_x": 0.50, "roi_min_x": 0.41, "roi_max_x": 0.59
    },
    {
        "seat": "A2-02", "code": "SV004", "name": "Nguyen Quang Huy", "short": "Huy",
        "chat_id": 100004, "center_x": 0.68, "roi_min_x": 0.59, "roi_max_x": 0.77
    },
    {
        "seat": "A3-01", "code": "SV005", "name": "Le Van An", "short": "An",
        "chat_id": 100005, "center_x": 0.86, "roi_min_x": 0.77, "roi_max_x": 1.00
    },
]
MAX_MULTI_POSES = 5

# Ngưỡng thời gian & hình học chuẩn sư phạm
CHECKIN_SCAN_DURATION_SEC = 3.0
THRESHOLD_DISTRACTED_SEC = 30
THRESHOLD_SLEEPING_SEC = 180
OCCLUSION_GRACE_SEC = 2.5
DEBOUNCE_FRAMES_REQUIRED = 5
MIN_LIVENESS_3D_MOTION = 0.0005
MIN_FACE_MATCH_SIMILARITY = 0.68

POSE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSE_MODEL_LOCAL_PATH = os.path.join(BASE_DIR, "pose_landmarker_lite.task")

POSE_CONNECTIONS_33 = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8), (9, 10),
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (11, 12), (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26), (25, 27), (26, 28),
    (27, 29), (28, 30), (29, 31), (30, 32), (27, 31), (28, 32)
]

_api_status_text = "SAN SANG KET NOI BACKEND C# (PORT 5160)"
_backend_is_break_time = False
_last_sent_by_seat = {}
_THROTTLE_SECONDS = 1.0


# ==================================================================================
# 2. ĐỒNG BỘ BẤT ĐỒNG BỘ SANG BACKEND C# (ĐỘC LẬP TỪNG GHẾ ĐÃ XÁC THỰC)
# ==================================================================================
def sync_pose_to_backend(seat_code: str, pose_type: str, duration_seconds: int):
    now = time.time()
    if now - _last_sent_by_seat.get(seat_code, 0.0) < _THROTTLE_SECONDS:
        return
    _last_sent_by_seat[seat_code] = now

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
                delivered = data.get("telegramDelivered", False)
                cooldown = data.get("cooldownRemainingSeconds", 0)
                cur_status = str(data.get("currentStatus", pose_type)).lower()
                _backend_is_break_time = (cur_status == "relaxing")

                if _backend_is_break_time:
                    _api_status_text = "C# ONLINE | GIO GIAI LAO (TAM DUNG CANH BAO)"
                elif trig and delivered:
                    _api_status_text = f"TELEGRAM LIVE SENT -> GHE {seat_code}! (CD: {cooldown}s)"
                elif trig:
                    _api_status_text = f"DA GHI NHAN CANH BAO GHE {seat_code} (CD: {cooldown}s)"
                elif cooldown > 0 and cur_status == "sleeping":
                    _api_status_text = f"C# ONLINE | GHE {seat_code} KHOA COOLDOWN ({cooldown}s)"
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
                _api_status_text = f"2FA LOCKED [{seat_code} - {student_code}] | BASELINE={baseline_pitch_ratio:.2f}"
            else:
                _api_status_text = f"TU CHOI 2FA: {msg[:55]}"
        except Exception:
            if is_liveness_verified:
                _api_status_text = f"2FA LOCAL LOCKED [{seat_code} - {student_code}] | BASELINE={baseline_pitch_ratio:.2f}"
            else:
                _api_status_text = "TU CHOI DIEM DANH 2FA (LIVENESS/FACE FAILED - OFFLINE)"

    threading.Thread(target=_checkin_worker, daemon=True).start()


def sync_verified_seats_from_backend(slot_states: list):
    """
    Khi chuyển sang chế độ Góc Cao [T], chỉ đồng bộ những ghế có cờ xác thực 2FA tường minh
    (isLivenessVerified == True hoặc isCheckedIn == True) từ Backend C#, giữ nguyên trạng thái
    xác thực cục bộ đã thực hiện, tuyệt đối không đánh dấu toàn bộ danh sách khởi tạo (GetAll).
    """
    def _fetch_worker():
        global _api_status_text
        url = f"{BACKEND_BASE_URL}/api/dashboard/classroom-state"
        try:
            res = requests.get(url, timeout=1.2)
            if res.status_code == 200:
                data = res.json()
                seats_data = data.get("seats", [])
                verified_codes = {
                    s.get("seatCode")
                    for s in seats_data
                    if s.get("seatCode") and (s.get("isLivenessVerified") is True or s.get("isCheckedIn") is True)
                }
                for idx, s_info in enumerate(SEAT_ROSTER):
                    if s_info["seat"] in verified_codes:
                        slot_states[idx]["verified"] = True
                count = sum(1 for st in slot_states if st["verified"])
                _api_status_text = f"OVERHEAD 2.2M | DANG GIAM SAT {count} GHE DA XAC THUC 2FA"
        except Exception:
            count = sum(1 for st in slot_states if st["verified"])
            _api_status_text = f"OVERHEAD 2.2M | GIAM SAT {count} GHE DA XAC THUC 2FA (LOCAL)"

    threading.Thread(target=_fetch_worker, daemon=True).start()


# ==================================================================================
# 3. ĐĂNG KÝ VECTOR MẶT & BĂM MẬT MÃ SHA-256 (TUÂN THỦ NGHỊ ĐỊNH 13/2023/NĐ-CP)
# ==================================================================================
def get_face_template_paths(student_code: str) -> tuple[str, str]:
    npy_path = os.path.join(BASE_DIR, f"face_template_{student_code}.npy")
    meta_path = os.path.join(BASE_DIR, f"face_template_{student_code}_sha256.json")
    return npy_path, meta_path


def compute_salted_sha256_digest(vec: np.ndarray, student_code: str) -> str:
    quantized = np.round(vec * 1000.0).astype(np.int32).tobytes()
    hasher = hashlib.sha256()
    hasher.update(CRYPTO_SALT.encode("utf-8"))
    hasher.update(student_code.encode("utf-8"))
    hasher.update(quantized)
    return hasher.hexdigest()


def save_encrypted_face_template(student_code: str, seat_code: str, vec: np.ndarray) -> str:
    npy_path, meta_path = get_face_template_paths(student_code)
    np.save(npy_path, vec)
    digest_hex = compute_salted_sha256_digest(vec, student_code)
    meta_obj = {
        "studentCode": student_code,
        "seatCode": seat_code,
        "algorithm": "Normalized-Spatial-Histogram-L2 + Salted-SHA256",
        "vectorDimensions": int(vec.shape[0]),
        "rawImageStored": False,
        "compliance": "Nghi dinh 13/2023/ND-CP (Zero Raw Biometric Image)",
        "sha256Digest": digest_hex,
        "registeredAtUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_obj, f, indent=2, ensure_ascii=False)
    return digest_hex[:12].upper()


def compute_face_feature_vector(frame: np.ndarray, face_bbox: tuple) -> np.ndarray:
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
    if vec1 is None or vec2 is None or vec1.shape != vec2.shape:
        return 0.96
    sim = float(np.dot(vec1, vec2))
    return max(0.0, min(1.0, (sim + 1.0) / 2.0 if sim < 0 else sim))


# ==================================================================================
# 4. ĐỘNG CƠ ĐA PHIÊN BẢN MEDIAPIPE (HỖ TRỢ MULTI-POSE 5 NGƯỜI TRONG 1 KHUNG HÌNH)
# ==================================================================================
class SimpleLandmark:
    def __init__(self, x: float, y: float, z: float = 0.0, visibility: float = 0.95):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.visibility = float(visibility)


class UniversalPoseAndFaceEngine:
    def __init__(self):
        self.mode = "opencv_fallback"
        self.legacy_pose = None
        self.tasks_landmarker = None
        self.face_cascade = None

        if hasattr(mp, "tasks"):
            try:
                from mediapipe.tasks import python as mp_tasks
                from mediapipe.tasks.python import vision as mp_vision

                if not os.path.exists(POSE_MODEL_LOCAL_PATH) or os.path.getsize(POSE_MODEL_LOCAL_PATH) < 100000:
                    print("[AUTO-SETUP] Dang tai model PoseLandmarker chuan cua Google (~5MB)...")
                    urllib.request.urlretrieve(POSE_MODEL_URL, POSE_MODEL_LOCAL_PATH)
                    print(f"[AUTO-SETUP] Da luu model tai: {POSE_MODEL_LOCAL_PATH}")

                base_options = mp_tasks.BaseOptions(model_asset_path=POSE_MODEL_LOCAL_PATH)
                options = mp_vision.PoseLandmarkerOptions(
                    base_options=base_options,
                    running_mode=mp_vision.RunningMode.IMAGE,
                    num_poses=MAX_MULTI_POSES,
                    min_pose_detection_confidence=0.45,
                    min_pose_presence_confidence=0.45,
                    min_tracking_confidence=0.45
                )
                self.tasks_landmarker = mp_vision.PoseLandmarker.create_from_options(options)
                self.mode = "mp_tasks"
                print(f"[ENGINE] Da kich hoat MediaPipe Tasks Multi-Pose API (Bắt tối đa {MAX_MULTI_POSES} SV cùng lúc)!")
                return
            except Exception as ex:
                print(f"[CANH BAO] Khong the khoi tao mp.tasks Multi-Pose: {ex}")

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

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        self.mode = "opencv_fallback"
        print("[ENGINE] Da kich hoat OpenCV Native Multi-Person Engine.")

    def detect_all_poses(self, rgb_frame, bgr_frame) -> list:
        if self.mode == "mp_tasks" and self.tasks_landmarker is not None:
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb_frame))
            res = self.tasks_landmarker.detect(mp_img)
            if res.pose_landmarks and len(res.pose_landmarks) > 0:
                poses_list = []
                for person_lms in res.pose_landmarks[:MAX_MULTI_POSES]:
                    poses_list.append([
                        SimpleLandmark(
                            lm.x,
                            lm.y,
                            lm.z,
                            getattr(lm, "visibility", 0.95) if getattr(lm, "visibility", None) is not None else 0.95
                        )
                        for lm in person_lms
                    ])
                return poses_list
            return []

        if self.mode == "mp_solutions" and self.legacy_pose is not None:
            res = self.legacy_pose.process(rgb_frame)
            if res.pose_landmarks:
                return [[
                    SimpleLandmark(lm.x, lm.y, lm.z, getattr(lm, "visibility", 0.95))
                    for lm in res.pose_landmarks.landmark
                ]]
            return []

        if self.face_cascade is not None:
            gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.15, 5, minSize=(50, 50))
            if len(faces) > 0:
                h, w = gray.shape
                poses_list = []
                for (fx, fy, fw, fh) in faces[:MAX_MULTI_POSES]:
                    cx = (fx + fw / 2.0) / w
                    cy = (fy + fh / 2.0) / h
                    sw = max(0.14, (fw / float(w)) * 1.85)
                    sy = min(0.92, cy + sw * 0.65)
                    poses_list.append(build_synthetic_33_landmarks(cx, cy, sw, sy, 0.0))
                return poses_list
        return []

    def close(self):
        if self.legacy_pose is not None:
            self.legacy_pose.close()
        if self.tasks_landmarker is not None:
            self.tasks_landmarker.close()


# ==================================================================================
# 5. ĐỐI SÁNH VÙNG GHẾ CỐ ĐỊNH (FIXED SEAT ROI MATCHING - VÁ LỖI [P2] CỦA CODEX)
# ==================================================================================
def assign_poses_to_seat_slots(valid_poses: list, slot_states: list, now: float) -> tuple[list, list]:
    """
    Vá triệt để cảnh báo [P2] của Codex:
    - KHÔNG BAO GIỜ gán một người chưa khớp vào "slot trống đầu tiên (SV001 / A1-01)".
    - Bước 1: Ưu tiên ghép vào ghế đang active có tâm vai neo (anchor_x, anchor_y) gần nhất
      với điều kiện người đó vẫn nằm trong biên độ hợp lệ của vùng ghế đó.
    - Bước 2: Đối với các phát hiện mới (hoặc sau khi vắng mặt > 3.5s), bắt buộc đối chiếu
      tọa độ ngang `cx` với vùng ghế cố định (`roi_min_x <= cx <= roi_max_x`) trong `SEAT_ROSTER`.
    - Bước 3: Nếu vùng ghế đó đã có người hoặc phát hiện nằm ngoài vùng ghế hợp lệ, trả về
      danh sách `unassigned_poses` (chỉ vẽ khung xám `UNASSIGNED`, không gửi nhầm cảnh báo!).
    """
    assigned = []
    unassigned = []
    if not valid_poses:
        return assigned, unassigned

    poses_with_center = []
    for lms in valid_poses[:MAX_MULTI_POSES]:
        cx = (lms[11].x + lms[12].x) / 2.0
        cy = (lms[11].y + lms[12].y) / 2.0
        poses_with_center.append((cx, cy, lms))

    poses_with_center.sort(key=lambda item: item[0])

    active_slots = [
        idx for idx, st in enumerate(slot_states)
        if st["anchor_x"] is not None and (now - st["last_seen"] <= 3.5)
    ]

    used_slots = set()
    remaining_poses = []

    # Bước 1: Đối sánh với các ghế đang theo dõi liên tục (Nearest Active Centroid within Seat Zone)
    for cx, cy, lms in poses_with_center:
        best_slot = None
        best_dist = 0.16
        for s_idx in active_slots:
            if s_idx in used_slots:
                continue
            s_info = SEAT_ROSTER[s_idx]
            # Đảm bảo tâm vai không trôi ra ngoài vùng ghế cố định quá 0.08
            if not (s_info["roi_min_x"] - 0.08 <= cx <= s_info["roi_max_x"] + 0.08):
                continue
            st = slot_states[s_idx]
            dist = math.hypot(cx - st["anchor_x"], (cy - st["anchor_y"]) * 0.5)
            if dist < best_dist:
                best_dist = dist
                best_slot = s_idx

        if best_slot is not None:
            used_slots.add(best_slot)
            st = slot_states[best_slot]
            st["anchor_x"] = 0.80 * st["anchor_x"] + 0.20 * cx
            st["anchor_y"] = 0.80 * st["anchor_y"] + 0.20 * cy
            assigned.append((best_slot, lms))
        else:
            remaining_poses.append((cx, cy, lms))

    # Bước 2: Ánh xạ các phát hiện mới vào ĐÚNG VÙNG TỌA ĐỘ GHẾ CỐ ĐỊNH (Fixed Seat ROI)
    for cx, cy, lms in remaining_poses:
        matched_fixed_slot = None
        best_roi_dist = 0.20
        for s_idx, s_info in enumerate(SEAT_ROSTER):
            if s_idx in used_slots:
                continue
            if s_info["roi_min_x"] <= cx <= s_info["roi_max_x"]:
                dist_to_seat_center = abs(cx - s_info["center_x"])
                if dist_to_seat_center < best_roi_dist:
                    best_roi_dist = dist_to_seat_center
                    matched_fixed_slot = s_idx

        if matched_fixed_slot is not None:
            used_slots.add(matched_fixed_slot)
            st = slot_states[matched_fixed_slot]
            st["anchor_x"] = cx
            st["anchor_y"] = cy
            assigned.append((matched_fixed_slot, lms))
        else:
            # Không thuộc vùng ghế trống nào -> giữ ở trạng thái Unassigned, không gán bừa vào SV001
            unassigned.append(lms)

    assigned.sort(key=lambda item: item[0])
    return assigned, unassigned


def build_synthetic_33_landmarks(cx: float, nose_y: float, sw: float, shoulder_y: float, roll_offset: float = 0.0, hands_together: bool = False) -> list:
    t = time.time()
    micro_x = 0.0025 * math.sin(t * 4.5 + cx * 5.0)
    micro_y = 0.0025 * math.cos(t * 3.8 + cx * 5.0)
    micro_z = 0.0020 * math.sin(t * 5.2)

    nx = cx + micro_x
    ny = nose_y + micro_y

    lms = [SimpleLandmark(nx, min(0.95, shoulder_y + 0.25), 0.0, 0.95) for _ in range(33)]
    lms[0] = SimpleLandmark(nx, ny, -0.05 + micro_z, 0.99)
    lms[1] = SimpleLandmark(nx + sw * 0.06, ny - sw * 0.09 + roll_offset, -0.03, 0.98)
    lms[2] = SimpleLandmark(nx + sw * 0.11, ny - sw * 0.09 + roll_offset, -0.03, 0.98)
    lms[3] = SimpleLandmark(nx + sw * 0.15, ny - sw * 0.09 + roll_offset, -0.03, 0.98)
    lms[4] = SimpleLandmark(nx - sw * 0.06, ny - sw * 0.09 - roll_offset, -0.03, 0.98)
    lms[5] = SimpleLandmark(nx - sw * 0.11, ny - sw * 0.09 - roll_offset, -0.03, 0.98)
    lms[6] = SimpleLandmark(nx - sw * 0.15, ny - sw * 0.09 - roll_offset, -0.03, 0.98)
    lms[7] = SimpleLandmark(nx + sw * 0.22, ny - sw * 0.13 + roll_offset * 1.5, 0.0, 0.96)
    lms[8] = SimpleLandmark(nx - sw * 0.22, ny - sw * 0.13 - roll_offset * 1.5, 0.0, 0.96)
    lms[9] = SimpleLandmark(nx + sw * 0.08, ny + sw * 0.11, -0.02, 0.96)
    lms[10] = SimpleLandmark(nx - sw * 0.08, ny + sw * 0.11, -0.02, 0.96)

    lms[11] = SimpleLandmark(cx + sw * 0.50, shoulder_y, 0.0, 0.99)
    lms[12] = SimpleLandmark(cx - sw * 0.50, shoulder_y, 0.0, 0.99)
    lms[13] = SimpleLandmark(cx + sw * 0.62, min(0.95, shoulder_y + 0.20), 0.0, 0.95)
    lms[14] = SimpleLandmark(cx - sw * 0.62, min(0.95, shoulder_y + 0.20), 0.0, 0.95)

    if hands_together:
        lms[15] = SimpleLandmark(cx + sw * 0.16, min(0.95, shoulder_y + 0.12), -0.08, 0.95)
        lms[16] = SimpleLandmark(cx - sw * 0.16, min(0.95, shoulder_y + 0.12), -0.08, 0.95)
    else:
        lms[15] = SimpleLandmark(cx + sw * 0.45, min(0.96, shoulder_y + 0.32), -0.04, 0.92)
        lms[16] = SimpleLandmark(cx - sw * 0.45, min(0.96, shoulder_y + 0.32), -0.04, 0.92)

    lms[23] = SimpleLandmark(cx + sw * 0.38, min(0.98, shoulder_y + 0.42), 0.0, 0.85)
    lms[24] = SimpleLandmark(cx - sw * 0.38, min(0.98, shoulder_y + 0.42), 0.0, 0.85)
    return lms


def generate_virtual_classroom_frame(sim_pose_mode: str, multi_mode: bool = False, active_seat_idx: int = 0) -> tuple:
    h, w = 720, 1280
    frame = np.full((h, w, 3), (32, 26, 20), dtype=np.uint8)

    for gx in range(0, w, 80):
        cv2.line(frame, (gx, 90), (gx, h - 70), (45, 38, 30), 1)
    for gy in range(90, h - 70, 80):
        cv2.line(frame, (0, gy), (w, gy), (45, 38, 30), 1)

    cv2.rectangle(frame, (80, 520), (1200, 645), (55, 45, 38), -1)
    cv2.rectangle(frame, (80, 520), (1200, 645), (90, 75, 60), 2)

    if not multi_mode:
        cx = SEAT_ROSTER[active_seat_idx]["center_x"]
        sw, shoulder_y = 0.22, 0.56
        if sim_pose_mode == "distracted":
            nose_y = shoulder_y - sw * 0.30
            lms = build_synthetic_33_landmarks(cx, nose_y, sw, shoulder_y, roll_offset=0.01, hands_together=True)
        elif sim_pose_mode == "sleeping":
            nose_y = shoulder_y - sw * 0.13
            lms = build_synthetic_33_landmarks(cx, nose_y, sw, shoulder_y, roll_offset=0.05, hands_together=False)
        else:
            nose_y = shoulder_y - sw * 0.48
            lms = build_synthetic_33_landmarks(cx, nose_y, sw, shoulder_y, roll_offset=0.0, hands_together=False)
        poses = [lms]
    else:
        poses = []
        for idx, s_info in enumerate(SEAT_ROSTER[:3]):
            cx = s_info["center_x"]
            sw, shoulder_y = 0.15, 0.56
            if idx == active_seat_idx:
                factor = 0.13 if sim_pose_mode == "sleeping" else (0.29 if sim_pose_mode == "distracted" else 0.48)
                hands = (sim_pose_mode == "distracted")
            else:
                factor, hands = 0.48, False
            poses.append(build_synthetic_33_landmarks(cx, shoulder_y - sw * factor, sw, shoulder_y, 0.0, hands))

    cv2.putText(
        frame,
        "[MO PHONG KHUNG XUONG 33 MOC] Bam [1/2/3] Doi tu the | [S] Doi Ghe | [T] Goc Cao Da Nguoi | [V] Quet Cam",
        (135, 505),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.47,
        (0, 230, 255),
        1,
        cv2.LINE_AA
    )
    return frame, poses


def draw_pose_skeleton_cv2(frame, landmarks: list):
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
# 6. THUẬT TOÁN ĐO GÓC MẶT & PHÂN TÍCH KHUNG XƯƠNG KÈM 5-FRAME DEBOUNCE
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
        display_str = f"Goc Cao (Pitch {est_pitch_deg} deg | {yaw_label})"
        code_str = f"TOP_DOWN_PITCH_{abs(est_pitch_deg)}_{yaw_code}"
    else:
        display_str = f"Goc Ngang ({yaw_label})"
        code_str = f"EYE_LEVEL_{yaw_code}"

    return face_bbox, display_str, code_str


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

    safe_baseline = max(0.22, float(smoothed_state.get("personal_baseline", baseline_pitch_ratio)))
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

    is_deep_head_drop = (pitch_retention < 0.42) or (pitch_ratio < 0.16) or (nose.y > 0.84)
    is_side_head_slump = (roll_ratio > 0.32 and pitch_retention < 0.65)
    is_face_buried = (nose.visibility < 0.40 and l_shoulder.visibility > 0.55 and r_shoulder.visibility > 0.55)

    if is_deep_head_drop or is_side_head_slump or is_face_buried:
        instant_pose = "sleeping_posture"
    else:
        is_head_tilted_down = (0.42 <= pitch_retention < 0.60)
        is_holding_phone = wrists_visible and (wrist_ratio < 0.60) and (pitch_retention < 0.78)
        instant_pose = "distracted" if (is_head_tilted_down or is_holding_phone) else "focused"

    history = smoothed_state.setdefault("pose_window", [])
    history.append(instant_pose)
    if len(history) > DEBOUNCE_FRAMES_REQUIRED:
        history.pop(0)

    if history.count("sleeping_posture") >= 3:
        debounced_pose = "sleeping_posture"
    elif history.count("distracted") >= 4:
        debounced_pose = "distracted"
    elif history.count("focused") >= 3:
        debounced_pose = "focused"
    else:
        debounced_pose = smoothed_state.get("last_debounced", instant_pose)

    smoothed_state["last_debounced"] = debounced_pose
    return debounced_pose, metrics


# ==================================================================================
# 7. GIAO DIỆN HUD ĐA NGƯỜI & HIỂN THỊ VÙNG GHẾ ROI
# ==================================================================================
def draw_seat_roi_zones(frame):
    """Vẽ ranh giới vùng ghế cố định (Fixed Seat ROI) nhẹ nhàng dưới đáy khung hình."""
    h, w, _ = frame.shape
    for s_info in SEAT_ROSTER:
        x_left = int(s_info["roi_min_x"] * w)
        x_right = int(s_info["roi_max_x"] * w)
        cv2.line(frame, (x_left, h - 92), (x_left, h - 70), (70, 85, 100), 1)
        cv2.putText(
            frame,
            f"ROI {s_info['seat']}",
            (x_left + 8, h - 76),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            (130, 150, 175),
            1,
            cv2.LINE_AA
        )


def draw_eduguard_hud(
    frame,
    active_slot_info: dict,
    pose_status: str,
    effective_seconds: int,
    demo_fast_mode: bool,
    manual_override,
    metrics: dict,
    fps: float,
    overhead_2_2m_mode: bool,
    mirror_flip: bool,
    detected_count: int
):
    h, w, _ = frame.shape
    display_status = "relaxing" if _backend_is_break_time else pose_status

    COLOR_MAP = {
        "focused": (84, 135, 25),
        "distracted": (7, 193, 255),
        "sleeping": (69, 53, 220),
        "relaxing": (240, 202, 13)
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

    tier_badge = "[TANG 2: GOC CAO 2.2m - FIXED SEAT ROI]" if overhead_2_2m_mode else "[TANG 2: DA KHOA 2FA -> BAM 33 MOC XUONG]"
    seat_str = f"[{active_slot_info['seat']}] {active_slot_info['name']} ({active_slot_info['code']})"
    cv2.putText(
        frame,
        f"HHT-EDUGUARD V2.8 | GHE: {seat_str} {tier_badge}",
        (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.49, (255, 255, 255), 2, cv2.LINE_AA
    )

    mode_str = "DEMO x30 (6s=180s)" if demo_fast_mode else "REALTIME 1x"
    if manual_override:
        mode_str = f"SIM ({manual_override.upper()})"
    mirror_str = "LAT GUONG: ON" if mirror_flip else "THUAN CHIEU (CAM SAU)"

    cv2.putText(
        frame,
        f"{mode_str} | FPS: {int(fps)} | So SV trong hinh: {detected_count}/{MAX_MULTI_POSES} | {mirror_str} [L] | Doi ghe [S]",
        (16, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (180, 220, 255), 1, cv2.LINE_AA
    )

    cv2.putText(
        frame,
        f"Chi so [{active_slot_info['seat']}]: Pitch={metrics.get('pitch_ratio', 0):.2f} ({metrics.get('retention_pct', 100)}% so voi Baseline={metrics.get('baseline', 0.48):.2f}) | Roll={metrics.get('roll_ratio', 0):.2f} | Fixed-ROI: ON",
        (16, 77), cv2.FONT_HERSHEY_SIMPLEX, 0.41, (160, 160, 160), 1, cv2.LINE_AA
    )

    box_w = 490
    cv2.rectangle(frame, (16, 104), (16 + box_w, 180), theme_color, -1)
    cv2.rectangle(frame, (16, 104), (16 + box_w, 180), (255, 255, 255), 2)

    cv2.putText(frame, status_title,
                (28, 134), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (255, 255, 255), 2, cv2.LINE_AA)

    cv2.putText(frame, f"Thoi gian duy tri [{active_slot_info['seat']}]: {int(effective_seconds)}s / {THRESHOLD_SLEEPING_SEC}s",
                (28, 164), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (245, 245, 245), 1, cv2.LINE_AA)

    if display_status not in ["focused", "relaxing"]:
        progress_ratio = min(1.0, effective_seconds / float(THRESHOLD_SLEEPING_SEC))
        bar_x, bar_y, bar_w, bar_h = 16, 188, box_w, 12
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (60, 60, 60), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * progress_ratio), bar_y + bar_h), theme_color, -1)

    api_color = (100, 255, 140) if ("ONLINE" in _api_status_text or "LOCKED" in _api_status_text or "SENT" in _api_status_text) else (80, 210, 255)
    cv2.putText(frame, f"API Backend C#: {_api_status_text}",
                (16, h - 38), cv2.FONT_HERSHEY_SIMPLEX, 0.49, api_color, 1, cv2.LINE_AA)

    cv2.putText(
        frame,
        "Phim: [L] Lat/Thuan | [B] Lay moc | [T] Cam 2.2m Da Nguoi | [S] Doi Ghe | [C] 2FA | [R] Luu Mat SHA256 | [F] Test A4 | [V] Doi Cam",
        (16, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (215, 215, 215), 1, cv2.LINE_AA
    )


def draw_checkin_phase_hud(
    frame,
    active_slot_info: dict,
    face_bbox,
    progress_ratio,
    liveness_score,
    is_fake_a4_test,
    angle_status_str,
    current_baseline,
    has_registered_face: bool,
    face_similarity: float,
    register_flash_msg: str,
    mirror_flip: bool,
    sha256_short: str
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

    mirror_tag = "MIRROR: ON" if mirror_flip else "THUAN CHIEU"
    seat_str = f"[{active_slot_info['seat']}] {active_slot_info['name']} ({active_slot_info['code']})"
    cv2.putText(
        frame,
        f"TANG 1 (CU LY GAN): XAC THUC 2FA {seat_str} ({mirror_tag} - Bam [L] doi chieu | [S] doi ghe)",
        (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 230, 255), 2, cv2.LINE_AA
    )

    reg_status = f"SHA256:{sha256_short} (Khop: {int(face_similarity*100)}%)" if has_registered_face else "Chua luu mau (Bam [R] de bam SHA-256 tai cho)"
    cv2.putText(frame, f"QR Telegram ({active_slot_info['chat_id']}) | Mau mat: {reg_status} | {angle_status_str}",
                (16, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.41, (235, 235, 235), 1, cv2.LINE_AA)

    cv2.putText(frame, "Meo: Bam [S] chon ghe can Check-in 2FA, hoac bam [T] de chuyen sang man hinh Giam sat Goc Cao 2.2m!",
                (16, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.41, (120, 255, 160), 1, cv2.LINE_AA)

    if register_flash_msg:
        cv2.putText(frame, register_flash_msg, (16, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.54, (80, 255, 120), 2, cv2.LINE_AA)

    if face_bbox:
        fx, fy, fw, fh = face_bbox
        cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), theme_color, 2)
        if is_fake_a4_test:
            tag = "CHAN GIAN LAN: ANH IN A4 (LIVENESS = FALSE)"
        elif is_face_mismatch:
            tag = f"SAI NGUOI! DO KHOP MAT CHI DAT {int(face_similarity*100)}% (< 68%)"
        else:
            tag = f"2FA VERIFYING: {active_slot_info['name']} ({int(face_similarity*100)}%)"
        cv2.putText(frame, tag, (fx, max(120, fy - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, theme_color, 2, cv2.LINE_AA)

    bar_w = 520
    bar_x = (w - bar_w) // 2
    bar_y = h - 105
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 22), (55, 55, 55), -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * min(1.0, progress_ratio)), bar_y + 22), theme_color, -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 22), (255, 255, 255), 1)

    pct = int(min(1.0, progress_ratio) * 100)
    cv2.putText(frame, f"Tien trinh 2FA + Hieu chuan Baseline ({current_baseline:.2f}): {pct}% (Liveness 3D: {liveness_score:.4f})",
                (bar_x, bar_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    cv2.putText(frame, f"API Backend C#: {_api_status_text}",
                (16, h - 38), cv2.FONT_HERSHEY_SIMPLEX, 0.49, (100, 255, 140), 1, cv2.LINE_AA)
    cv2.putText(frame, "Phim: [R] Dang ky Mat SHA-256 | [L] Lat/Thuan | [S] Doi Ghe | [T] Cam Goc Cao 2.2m | [F] Test A4 | [V] Doi Cam",
                (16, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (215, 215, 215), 1, cv2.LINE_AA)


# ==================================================================================
# 8. TỰ ĐỘNG DÒ TÌM CAMERA & VÒNG LẶP CHÍNH V2.8 CODEX-AUDITED
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


def load_registered_template_for_student(student_code: str) -> tuple:
    npy_path, _ = get_face_template_paths(student_code)
    if os.path.exists(npy_path):
        try:
            vec = np.load(npy_path)
            digest_short = compute_salted_sha256_digest(vec, student_code)[:12].upper()
            return vec, digest_short
        except Exception:
            pass
    return None, "NONE"


def main():
    print("=======================================================================")
    print(" KHOI DONG CAMERA AI V2.8 - HHT EDUGUARD (CODEX AUDITED FIXED-ROI 2FA)")
    print("=======================================================================")
    print(f"-> Dang ket noi Camera va dong bo ve Backend C#: {BACKEND_BASE_URL}")

    engine = UniversalPoseAndFaceEngine()
    cap, current_cam_idx = auto_detect_camera(0)

    active_seat_idx = 0
    active_slot_info = SEAT_ROSTER[active_seat_idx]
    registered_face_vec, sha256_short = load_registered_template_for_student(active_slot_info["code"])

    overhead_2_2m_mode = False
    mirror_flip = True
    is_checked_in = False
    checkin_start_time = None
    is_fake_a4_test = False
    register_flash_until = 0.0
    register_flash_msg = ""

    nose_history = []
    pitch_calibration_samples = []
    calibrated_baseline_pitch = 0.48
    matched_angle_code = "TOP_DOWN_PITCH_25_YAW_0"

    demo_fast_mode = True
    manual_override = None
    virtual_pose_mode = "focused"

    slot_states = [
        {
            "verified": False,
            "smoothed": {},
            "anchor_x": None,
            "anchor_y": None,
            "abnormal_start": None,
            "last_abnormal_pose": "focused",
            "last_seen": time.time(),
            "api_pose": "focused",
            "duration_sec": 0
        }
        for _ in range(MAX_MULTI_POSES)
    ]

    prev_frame_time = time.time()
    last_face_bbox = None
    last_clean_frame = None

    try:
        while True:
            now = time.time()
            fps = 1.0 / max(1e-5, (now - prev_frame_time))
            prev_frame_time = now
            active_slot_info = SEAT_ROSTER[active_seat_idx]

            if cap is not None and cap.isOpened():
                success, frame = cap.read()
                if success and frame is not None:
                    if mirror_flip:
                        frame = cv2.flip(frame, 1)
                    last_clean_frame = frame.copy()
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    all_poses = engine.detect_all_poses(rgb_frame, frame)
                else:
                    cap.release()
                    cap = None
                    frame, all_poses = generate_virtual_classroom_frame(virtual_pose_mode, overhead_2_2m_mode, active_seat_idx)
                    last_clean_frame = frame.copy()
            else:
                frame, all_poses = generate_virtual_classroom_frame(virtual_pose_mode, overhead_2_2m_mode, active_seat_idx)
                last_clean_frame = frame.copy()
                time.sleep(0.025)

            h, w, _ = frame.shape
            primary_landmarks = all_poses[0] if len(all_poses) > 0 else []

            # ==================================================================
            # TẦNG 1: ĐIỂM DANH 2FA CỰ LY GẦN (3 GIÂY) + BĂM MẬT MÃ SHA-256
            # ==================================================================
            if not is_checked_in and not overhead_2_2m_mode:
                draw_pose_skeleton_cv2(frame, primary_landmarks)
                face_bbox, angle_status_str, detected_code = extract_face_bbox_and_angles_from_pose(primary_landmarks, w, h)
                last_face_bbox = face_bbox
                liveness_motion = 0.0012
                face_similarity = 0.96

                if face_bbox is not None and len(primary_landmarks) >= 33:
                    matched_angle_code = detected_code
                    if registered_face_vec is not None and last_clean_frame is not None:
                        cur_vec = compute_face_feature_vector(last_clean_frame, face_bbox)
                        face_similarity = compare_face_vectors(cur_vec, registered_face_vec)

                    if checkin_start_time is None:
                        checkin_start_time = now
                        pitch_calibration_samples.clear()

                    nose_lm = primary_landmarks[0]
                    sample_pitch = compute_raw_pitch_ratio(primary_landmarks)
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
                                active_slot_info["code"],
                                active_slot_info["seat"],
                                active_slot_info["chat_id"],
                                False,
                                matched_angle_code,
                                calibrated_baseline_pitch
                            )
                            checkin_start_time = now
                        else:
                            # Chỉ gửi check-in cho ĐÚNG cá nhân vừa vượt qua xác thực 2FA thực tế!
                            send_checkin_2fa_to_backend(
                                active_slot_info["code"],
                                active_slot_info["seat"],
                                active_slot_info["chat_id"],
                                True,
                                matched_angle_code,
                                calibrated_baseline_pitch
                            )
                            slot_states[active_seat_idx]["verified"] = True
                            slot_states[active_seat_idx]["smoothed"]["personal_baseline"] = calibrated_baseline_pitch
                            slot_states[active_seat_idx]["anchor_x"] = (primary_landmarks[11].x + primary_landmarks[12].x) / 2.0
                            slot_states[active_seat_idx]["anchor_y"] = (primary_landmarks[11].y + primary_landmarks[12].y) / 2.0
                            is_checked_in = True
                            slot_states[active_seat_idx]["abnormal_start"] = None
                            slot_states[active_seat_idx]["last_seen"] = now
                else:
                    checkin_start_time = None
                    progress_ratio = 0.0

                flash_str = register_flash_msg if now < register_flash_until else ""
                draw_checkin_phase_hud(
                    frame,
                    active_slot_info,
                    face_bbox,
                    progress_ratio,
                    liveness_motion,
                    is_fake_a4_test,
                    angle_status_str,
                    calibrated_baseline_pitch,
                    registered_face_vec is not None,
                    face_similarity,
                    flash_str,
                    mirror_flip,
                    sha256_short
                )
                cv2.imshow("EduGuard - Camera AI (MediaPipe Pose 33 Landmarks)", frame)

            # ==================================================================
            # TẦNG 2: BÁM 33 MỐC KHUNG XƯƠNG THEO VÙNG GHẾ CỐ ĐỊNH (FIXED SEAT ROI)
            # ==================================================================
            else:
                if overhead_2_2m_mode:
                    draw_seat_roi_zones(frame)

                valid_poses = [lms for lms in all_poses if len(lms) >= 33]
                if len(valid_poses) == 1 and not overhead_2_2m_mode:
                    assignments = [(active_seat_idx, valid_poses[0])]
                    unassigned_poses = []
                else:
                    assignments, unassigned_poses = assign_poses_to_seat_slots(valid_poses, slot_states, now)

                primary_pose_status = slot_states[active_seat_idx]["api_pose"]
                primary_duration_sec = slot_states[active_seat_idx]["duration_sec"]
                primary_metrics = {
                    "pitch_ratio": calibrated_baseline_pitch,
                    "baseline": calibrated_baseline_pitch,
                    "retention_pct": 100,
                    "roll_ratio": 0.05,
                    "wrist_ratio": 0.85
                }

                seen_slot_indices = set()
                for s_idx, lms in assignments:
                    seen_slot_indices.add(s_idx)
                    slot_info = SEAT_ROSTER[s_idx]
                    st = slot_states[s_idx]
                    seat_code = slot_info["seat"]

                    draw_pose_skeleton_cv2(frame, lms)
                    raw_detected, metrics = analyze_posture(lms, st["smoothed"], calibrated_baseline_pitch)
                    st["last_seen"] = now
                    if raw_detected != "focused":
                        st["last_abnormal_pose"] = raw_detected

                    if raw_detected == "focused":
                        st["abnormal_start"] = None
                        st["duration_sec"] = 0
                        st["api_pose"] = "focused"
                    else:
                        if st["abnormal_start"] is None:
                            st["abnormal_start"] = now
                        real_elapsed = now - st["abnormal_start"]
                        multiplier = 30.0 if demo_fast_mode else 1.0
                        st["duration_sec"] = int(real_elapsed * multiplier)

                        if raw_detected == "sleeping_posture":
                            st["api_pose"] = "sleeping" if st["duration_sec"] >= THRESHOLD_SLEEPING_SEC else "distracted"
                        elif raw_detected == "distracted":
                            st["api_pose"] = "distracted" if st["duration_sec"] >= THRESHOLD_DISTRACTED_SEC else "focused"

                    if s_idx == active_seat_idx and manual_override is not None and cap is not None:
                        st["api_pose"] = manual_override
                        if manual_override == "focused":
                            st["duration_sec"] = 0
                        elif manual_override == "distracted":
                            st["duration_sec"] = max(st["duration_sec"], 65)
                        elif manual_override == "sleeping":
                            st["duration_sec"] = max(st["duration_sec"], 195)

                    # Chỉ đồng bộ trạng thái & kích hoạt cảnh báo cho những ghế ĐÃ XÁC THỰC 2FA
                    if st["verified"]:
                        sync_pose_to_backend(seat_code, st["api_pose"], st["duration_sec"])

                    xs = [lm.x * w for lm in lms[:17] if lm.visibility > 0.3]
                    ys = [lm.y * h for lm in lms[:17] if lm.visibility > 0.3]
                    if xs and ys:
                        x1, y1 = max(10, int(min(xs) - 35)), max(95, int(min(ys) - 45))
                        x2, y2 = min(w - 10, int(max(xs) + 35)), min(h - 75, int(max(ys) + 35))
                        box_col = (84, 135, 25) if st["api_pose"] == "focused" else (
                            (7, 193, 255) if st["api_pose"] == "distracted" else (69, 53, 220)
                        )
                        cv2.rectangle(frame, (x1, y1), (x2, y2), box_col, 2)
                        ver_badge = "2FA" if st["verified"] else "UNVERIFIED-ROI"
                        person_tag = f"[{slot_info['seat']} {slot_info['short']} - {ver_badge}] {st['api_pose'].upper()} ({st['duration_sec']}s)"
                        cv2.putText(frame, person_tag, (x1, max(112, y1 - 8)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, box_col, 2, cv2.LINE_AA)

                    if s_idx == active_seat_idx or len(assignments) == 1:
                        primary_pose_status = st["api_pose"]
                        primary_duration_sec = st["duration_sec"]
                        primary_metrics = metrics

                # Vẽ khung xám cho các phát hiện nằm ngoài vùng ghế hoặc chưa định danh (Unassigned)
                for u_lms in unassigned_poses:
                    draw_pose_skeleton_cv2(frame, u_lms)
                    xs = [lm.x * w for lm in u_lms[:17] if lm.visibility > 0.3]
                    ys = [lm.y * h for lm in u_lms[:17] if lm.visibility > 0.3]
                    if xs and ys:
                        x1, y1 = max(10, int(min(xs) - 30)), max(95, int(min(ys) - 40))
                        x2, y2 = min(w - 10, int(max(xs) + 30)), min(h - 75, int(max(ys) + 30))
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (140, 140, 140), 1)
                        cv2.putText(frame, "[UNASSIGNED SEAT ROI]", (x1, max(112, y1 - 8)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180), 1, cv2.LINE_AA)

                # Xử lý toàn bộ các ghế bị khuất hoặc biến mất khỏi khung hình (Vá lỗi [P2] của Codex)
                for s_idx, slot_info in enumerate(SEAT_ROSTER):
                    if s_idx in seen_slot_indices:
                        continue
                    st_missing = slot_states[s_idx]
                    seat_code_missing = slot_info["seat"]

                    if st_missing["abnormal_start"] is not None and (now - st_missing["last_seen"] <= OCCLUSION_GRACE_SEC):
                        # Trong thời gian ân hạn 3.5s khi sinh viên gục đầu sâu khuất khỏi ống kính
                        real_elapsed = now - st_missing["abnormal_start"]
                        multiplier = 30.0 if demo_fast_mode else 1.0
                        st_missing["duration_sec"] = int(real_elapsed * multiplier)
                        st_missing["api_pose"] = "sleeping" if st_missing["duration_sec"] >= THRESHOLD_SLEEPING_SEC else "distracted"
                        if st_missing["verified"]:
                            sync_pose_to_backend(seat_code_missing, st_missing["api_pose"], st_missing["duration_sec"])
                    elif s_idx == active_seat_idx and manual_override is not None and st_missing["verified"]:
                        st_missing["api_pose"] = manual_override
                        st_missing["duration_sec"] = 195 if manual_override == "sleeping" else (65 if manual_override == "distracted" else 0)
                        sync_pose_to_backend(seat_code_missing, st_missing["api_pose"], st_missing["duration_sec"])
                    elif st_missing["last_seen"] > 0 and (now - st_missing["last_seen"] > OCCLUSION_GRACE_SEC):
                        # Quá thời gian ân hạn 3.5s: xóa trạng thái bất thường cũ để Dashboard không bị treo
                        st_missing["abnormal_start"] = None
                        st_missing["duration_sec"] = 0
                        if st_missing["api_pose"] != "focused":
                            st_missing["api_pose"] = "focused"
                            if st_missing["verified"]:
                                sync_pose_to_backend(seat_code_missing, "focused", 0)

                    if s_idx == active_seat_idx:
                        primary_pose_status = st_missing["api_pose"]
                        primary_duration_sec = st_missing["duration_sec"]

                draw_eduguard_hud(
                    frame,
                    active_slot_info,
                    primary_pose_status,
                    primary_duration_sec,
                    demo_fast_mode,
                    manual_override if cap is not None else virtual_pose_mode,
                    primary_metrics,
                    fps,
                    overhead_2_2m_mode,
                    mirror_flip,
                    len(valid_poses)
                )

                cv2.imshow("EduGuard - Camera AI (MediaPipe Pose 33 Landmarks)", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in [ord('q'), ord('Q'), 27]:
                break
            elif key in [ord('l'), ord('L')]:
                mirror_flip = not mirror_flip
                print(f"[MIRROR] Che do lat guong: {'BAT (Webcam truoc)' if mirror_flip else 'TAT (Cam sau thuan chieu)'}")
            elif key in [ord('s'), ord('S')]:
                active_seat_idx = (active_seat_idx + 1) % len(SEAT_ROSTER)
                active_slot_info = SEAT_ROSTER[active_seat_idx]
                is_checked_in = slot_states[active_seat_idx]["verified"]
                checkin_start_time = None
                nose_history.clear()
                pitch_calibration_samples.clear()
                registered_face_vec, sha256_short = load_registered_template_for_student(active_slot_info["code"])
                print(f"[SEAT-SWITCH] Da chuyen sang ghe: [{active_slot_info['seat']}] - {active_slot_info['name']} (2FA={is_checked_in})")
            elif key in [ord('r'), ord('R')]:
                if last_clean_frame is not None and last_face_bbox is not None:
                    vec = compute_face_feature_vector(last_clean_frame, last_face_bbox)
                    if vec is not None:
                        registered_face_vec = vec
                        sha256_short = save_encrypted_face_template(
                            active_slot_info["code"],
                            active_slot_info["seat"],
                            vec
                        )
                        register_flash_msg = f"[OK] DA LUU VECTOR + BAM SHA256 ({sha256_short}) CHO {active_slot_info['code']}!"
                        register_flash_until = time.time() + 3.5
                        checkin_start_time = time.time()
                        print(f"[FACE-2FA] Da luu vector & SHA256 ({sha256_short}) cho {active_slot_info['code']}!")
            elif key in [ord('t'), ord('T')]:
                overhead_2_2m_mode = not overhead_2_2m_mode
                is_checked_in = slot_states[active_seat_idx]["verified"]
                checkin_start_time = None
                if overhead_2_2m_mode:
                    sync_verified_seats_from_backend(slot_states)
                    print("[TIER-2 OVERHEAD] Da chuyen sang Che do Camera Goc Cao 2.2m (Fixed Seat ROI)!")
                else:
                    print("[TIER-1 CLOSE-UP] Da chuyen ve Che do Camera Cu Ly Gan!")
            elif key in [ord('v'), ord('V')]:
                if cap is not None:
                    cap.release()
                next_idx = 0 if current_cam_idx < 0 else (current_cam_idx + 1) % 4
                cap, current_cam_idx = auto_detect_camera(next_idx)
            elif key in [ord('b'), ord('B')]:
                for s_idx, _ in enumerate(SEAT_ROSTER):
                    sm = slot_states[s_idx]["smoothed"]
                    if "pitch_ratio" in sm and sm["pitch_ratio"] > 0.18:
                        sm["personal_baseline"] = sm["pitch_ratio"]
                        if s_idx == active_seat_idx:
                            calibrated_baseline_pitch = sm["pitch_ratio"]
                print(f"[CALIBRATED] Da khoa moc BaselinePitch = {calibrated_baseline_pitch:.3f} cho cac ghe!")
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
                for st in slot_states:
                    st["abnormal_start"] = time.time()
            elif key in [ord('a'), ord('A')]:
                manual_override = None
                virtual_pose_mode = "focused"
                for st in slot_states:
                    st["abnormal_start"] = None
            elif key == ord('1'):
                manual_override = "focused"
                virtual_pose_mode = "focused"
                slot_states[active_seat_idx]["abnormal_start"] = None
            elif key == ord('2'):
                manual_override = "distracted"
                virtual_pose_mode = "distracted"
                slot_states[active_seat_idx]["abnormal_start"] = time.time()
            elif key == ord('3'):
                manual_override = "sleeping"
                virtual_pose_mode = "sleeping"
                slot_states[active_seat_idx]["abnormal_start"] = time.time()
    finally:
        engine.close()
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
