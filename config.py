import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Đường dẫn Chrome hệ thống
CHROME_EXECUTABLE_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# Thư mục Chrome User Data thật của máy tính
CHROME_USER_DATA_DIR = r"C:\Users\Trung Duc\AppData\Local\Google\Chrome\User Data"
CHROME_PROFILE_NAME = "Profile 6"

# Thư mục lưu cache cục bộ
BROWSER_PROFILE_DIR = CHROME_USER_DATA_DIR

# Thư mục chứa video tải về và xuất file
DOWNLOADS_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "output"

DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# URL mục tiêu
NOTEBOOKLM_URL = "https://notebook.google.com/notebook/ddbc4753-9564-4e91-b58a-912bd0ef40b1"
TIKTOK_UPLOAD_URL = "https://www.tiktok.com/creator-center/upload?from=creator_center"
GOOGLE_FLOW_URL = "https://flow.google.com/project/a85fdaa4-0c21-4fcb-b2ca-0a9c07891ed1"

# Cấu hình giờ chạy (12:00 trưa hàng ngày)
SCHEDULE_HOUR = 12
SCHEDULE_MINUTE = 0

# Cấu hình giọng đọc AI đồng bộ (Edge-TTS chuẩn TikTok tiếng Việt)
# "vi-VN-NamMinhNeural": Giọng nam miền Bắc, trầm ấm, truyền cảm, phong cách chuyên gia tài chính/tâm lý
# "vi-VN-HoaiMyNeural": Giọng nữ miền Bắc, mượt mà, cuốn hút chuẩn TikTok
DEFAULT_VOICE = "vi-VN-NamMinhNeural"
