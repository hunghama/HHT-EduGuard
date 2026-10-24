import requests

# CẤU HÌNH ĐỊA CHỈ BACKEND C# CỦA ANH HÙNG:
# - Chạy chung 1 máy: Giữ nguyên "http://localhost:5160"
# - Chạy 2 máy khác nhau cùng Wi-Fi: Đổi "localhost" thành IP máy của Hùng (VD: "http://192.168.1.15:5160")
BACKEND_BASE_URL = "http://localhost:5160"

def send_sleep_alert(seat_code: str, duration_seconds: int) -> bool:
    """
    Hàm gửi tín hiệu cảnh báo từ Camera AI (Python) sang Backend C# (.NET 10).
    Quỳnh chỉ cần import hàm này vào file chạy webcam và gọi khi phát hiện gục đầu!
    """
    url = f"{BACKEND_BASE_URL}/api/alerts/sleep"
    
    # Cấu trúc JSON chuẩn camelCase đồng bộ
    payload = {
        "seatCode": seat_code,
        "durationSeconds": int(duration_seconds)
    }
    
    try:
        response = requests.post(url, json=payload, timeout=2.0)
        if response.status_code == 200:
            data = response.json()
            triggered = data.get("triggeredAlert", False)
            print(f"[EduGuard API] Ghế {seat_code} ({duration_seconds}s) -> Bắn Telegram: {triggered} | {data.get('message')}")
            return triggered
        else:
            print(f"[EduGuard API Warning] Server trả về mã lỗi: {response.status_code}")
    except Exception as e:
        print(f"[EduGuard API Error] Không kết nối được tới Backend C# tại {url}: {e}")
    
    return False

if __name__ == "__main__":
    print("--- KIỂM TRA KẾT NỐI SANG BACKEND C# ---")
    print("1. Thử nghiệm ngủ 60s (Chưa vượt ngưỡng 180s):")
    send_sleep_alert(seat_code="A1-01", duration_seconds=60)
    
    print("\n2. Thử nghiệm ngủ 240s (Vượt ngưỡng 180s -> Rung máy Telegram):")
    send_sleep_alert(seat_code="A1-02", duration_seconds=240)
