import time
import threading
import requests

BACKEND_BASE_URL = "http://localhost:5160"
_last_sent_time = 0.0
_THROTTLE_SECONDS = 1.0

def _post_worker(url: str, payload: dict):
    try:
        res = requests.post(url, json=payload, timeout=1.5)
        if res.status_code == 200:
            data = res.json()
            trig = data.get("triggeredAlert")
            msg = data.get("message")
            print(f"[AI->C#] Alert={trig} | {msg}")
    except Exception as e:
        print(f"[EduGuard Warning] {e}")

def send_pose_state(seat_code: str, pose_type: str = "focused", duration_seconds: int = 0, async_mode: bool = True):
    global _last_sent_time
    now = time.time()
    if async_mode and (now - _last_sent_time < _THROTTLE_SECONDS):
        return
    _last_sent_time = now
    url = f"{BACKEND_BASE_URL}/api/alerts/pose"
    payload = {
        "seatCode": seat_code,
        "poseType": pose_type,
        "durationSeconds": int(duration_seconds)
    }
    if async_mode:
        t = threading.Thread(target=_post_worker, args=(url, payload), daemon=True)
        t.start()
    else:
        _post_worker(url, payload)

def send_sleep_alert(seat_code: str, seconds: int):
    p = "sleeping" if seconds >= 180 else "distracted"
    send_pose_state(seat_code, p, seconds, False)

if __name__ == "__main__":
    print("=== TEST PYTHON AI -> C# (.NET 10) ===")
    send_pose_state("A2-01", "distracted", 60, False)
    send_pose_state("A2-01", "sleeping", 200, False)
    send_pose_state("A2-01", "sleeping", 205, False)
