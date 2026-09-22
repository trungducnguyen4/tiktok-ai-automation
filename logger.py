import datetime
import threading
import json
import sys

# Đảm bảo in ký tự tiếng Việt an toàn trên terminal Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

logs_lock = threading.Lock()
realtime_logs = []

def add_log(message: str, level: str = "success"):
    """
    level: 'success' (màu xanh lá - đang đúng hướng)
           'info' (màu xanh ngọc/xanh dương - tiến trình)
           'error' (màu đỏ - lỗi)
           'warning' (màu vàng - cảnh báo)
    """
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_entry = {
        "time": timestamp,
        "message": message,
        "level": level
    }
    with logs_lock:
        realtime_logs.append(log_entry)
        # Giữ tối đa 500 logs gần nhất
        if len(realtime_logs) > 500:
            realtime_logs.pop(0)
    print(f"[{timestamp}] [{level.upper()}] {message}")

def get_logs() -> list[dict]:
    with logs_lock:
        return list(realtime_logs)

def clear_logs():
    with logs_lock:
        realtime_logs.clear()
