import os
import subprocess
import config
from logger import add_log

def open_browser_for_login():
    """
    Mở trực tiếp Chrome với Profile 6 (profile có sẵn NotebookLM và TikTok của bạn)
    """
    add_log(f"Đang mở Chrome với {config.CHROME_PROFILE_NAME}...", level="info")
    
    cmd = [
        config.CHROME_EXECUTABLE_PATH,
        f"--user-data-dir={config.CHROME_USER_DATA_DIR}",
        f"--profile-directory={config.CHROME_PROFILE_NAME}",
        config.NOTEBOOKLM_URL,
        config.TIKTOK_UPLOAD_URL
    ]

    try:
        proc = subprocess.Popen(cmd)
        add_log(f"-> Đã mở cửa sổ Chrome ({config.CHROME_PROFILE_NAME}) thành công!", level="success")
        return proc
    except Exception as e:
        add_log(f"Lỗi khi mở Chrome: {e}", level="error")
        raise e

if __name__ == "__main__":
    open_browser_for_login()
