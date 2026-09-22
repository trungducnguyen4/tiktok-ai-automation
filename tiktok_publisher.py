import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
import config
from logger import add_log

def publish_to_tiktok(video_path: str, title: str, hashtags: list[str], headless: bool = False) -> bool:
    """
    Kết nối tới Chrome CDP (port 9222) với Profile 6 của bạn để đăng video lên TikTok Studio.
    Hoàn toàn không bao giờ bị ProcessSingleton lock file!
    """
    add_log("Đang mở TikTok Studio để upload video...", level="info")
    caption = f"{title}\n\n" + " ".join(hashtags)

    if not Path(video_path).exists():
        raise FileNotFoundError(f"Không tìm thấy file video để đăng: {video_path}")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0] if browser.contexts else browser.new_context()

        # Tìm tab TikTok Creator nếu có sẵn
        page = None
        for pg in context.pages:
            if "tiktok.com" in pg.url and "creator" in pg.url:
                page = pg
                break

        if not page:
            page = context.new_page()
            page.goto(config.TIKTOK_UPLOAD_URL, timeout=45000)
            time.sleep(3)

        page.bring_to_front()

        # Kiểm tra trạng thái đăng nhập
        if "login" in page.url.lower():
            add_log("CHƯA ĐĂNG NHẬP TIKTOK: Trình duyệt đang ở trang đăng nhập TikTok!", level="error")
            browser.close()
            return False

        add_log("-> Đang tải tệp video lên TikTok Studio...", level="info")
        file_input = page.locator("input[type='file'], [type='file']").first
        file_input.set_input_files(video_path)

        add_log("-> Đang chờ TikTok xử lý video và điền Caption...", level="info")
        time.sleep(10)

        # Điền Caption
        caption_box = page.locator(".DraftEditor-root, [contenteditable='true'], textarea").first
        if caption_box.is_visible():
            caption_box.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(caption, delay=20)
            add_log(f"-> Đã điền tiêu đề và hashtag: '{title}'", level="success")

        time.sleep(12)

        # Bấm Publish / Post
        post_button = page.locator("button:has-text('Post'), button:has-text('Đăng'), button:has-text('Publish')").first
        success = False
        if post_button.is_visible():
            post_button.click()
            add_log("-> Đã bấm nút ĐĂNG VIDEO lên TikTok!", level="success")
            time.sleep(8)
            success = True
        else:
            add_log("-> Nút Đăng chưa sẵn sàng hoặc video đang xử lý trên TikTok.", level="warning")

        browser.close()
        return success

if __name__ == "__main__":
    test_video = config.OUTPUT_DIR / "final_tiktok_video.mp4"
    if test_video.exists():
        publish_to_tiktok(str(test_video), "Test video", ["#test"])
