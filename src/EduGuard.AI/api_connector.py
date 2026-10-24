import time
import threading
import requests

BACKEND_BASE_URL = "http://localhost:5160"
_last_sent_by_seat = {}
_THROTTLE_SECONDS = 1.0

def _post_worker(url: str, payload: dict):
    try:
        res = requests.post(url, json=payload, timeout=1.5)
        if res.status_code == 200:
            data = res.json()
            trig = data.get("triggeredAlert")
            msg = data.get("message")
            print(f"[AI->C#] Alert={trig} | {msg}")
        else:
            print(f"[AI->C# Error] Status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[EduGuard Warning] {e}")

def send_pose_state(seat_code: str, pose_type: str = "focused", duration_seconds: int = 0, async_mode: bool = True):
    now = time.time()
    last_time = _last_sent_by_seat.get(seat_code, 0.0)
    if async_mode and (now - last_time < _THROTTLE_SECONDS):
        return
    _last_sent_by_seat[seat_code] = now

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

def send_sleep_alert(seat_code: str, duration_seconds: int = 180, seconds: int = None):
    dur = seconds if seconds is not None else duration_seconds
    p = "sleeping" if dur >= 180 else "distracted"
    send_pose_state(seat_code, p, dur, False)

if __name__ == "__main__":
    print("=== TEST MULTI-SEAT THROTTLE & ALIAS ===")
    send_pose_state("A1-01", "distracted", 60, False)
    send_pose_state("A2-01", "sleeping", 200, False)
    send_sleep_alert("A2-01", duration_seconds=185)
