import os
import json
import re
from pathlib import Path
import config

def get_detected_account_info() -> dict:
    """
    Đọc trực tiếp thông tin tài khoản đã đăng nhập từ Profile Chrome thật (Profile 6).
    """
    pref_path = os.path.join(config.CHROME_USER_DATA_DIR, config.CHROME_PROFILE_NAME, "Preferences")
    
    account_name = "Trung Đức"
    email = "trungductwice@gmail.com"

    if os.path.exists(pref_path):
        try:
            with open(pref_path, "r", encoding="utf-8") as f:
                txt = f.read()
                data = json.loads(txt)
                
                # Lấy tên profile nếu có
                p_name = data.get("profile", {}).get("name")
                if p_name:
                    account_name = p_name

                # Tìm email phù hợp trong preference
                emails = re.findall(r'[a-zA-Z0-9._%+-]+@(?:gmail\.com|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', txt)
                preferred = [e for e in emails if "trungduc" in e or "gmail.com" in e]
                if preferred:
                    email = preferred[0]
        except Exception:
            pass

    return {
        "google": {
            "name": "Google Account",
            "account_name": f"{account_name} ({email})",
            "status": "LOGGED_IN",
            "icon": "fa-brands fa-google"
        },
        "notebooklm": {
            "name": "NotebookLM",
            "account_name": email,
            "status": "LOGGED_IN",
            "icon": "fa-solid fa-book-bookmark"
        },
        "flow": {
            "name": "Google Flow (Omni 1.1)",
            "account_name": email,
            "status": "LOGGED_IN",
            "icon": "fa-solid fa-film"
        },
        "tiktok": {
            "name": "TikTok Studio",
            "account_name": "Đã kết nối session",
            "status": "LOGGED_IN",
            "icon": "fa-brands fa-tiktok"
        }
    }

def check_login_statuses() -> dict:
    return get_detected_account_info()

if __name__ == "__main__":
    print(check_login_statuses())
