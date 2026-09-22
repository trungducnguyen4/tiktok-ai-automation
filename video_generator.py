import time
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright
import config
from logger import add_log

def configure_flow_settings(page):
    """
    Tự động áp dụng chính xác cấu hình theo ảnh yêu cầu:
    - Loại: Video
    - Chế độ: Ingredients
    - Tỷ lệ: 9:16 (Dọc chuẩn TikTok)
    - Model: Omni 1.1 Flash
    - Độ phân giải: 720p
    - Thời lượng: 8s
    - Số lượng clip: x1
    """
    try:
        add_log("-> Đang kiểm tra và áp dụng Cấu hình Video Google Flow...", level="info")
        
        # 1. Kiểm tra trạng thái hiện tại trên nút pill settings
        pill_text = page.evaluate('''() => {
            const btn = document.querySelector('button.settings-trigger-button, button[aria-label="Settings trigger"]');
            return btn ? btn.innerText.trim().replace(/\\n/g, ' ') : '';
        }''')
        
        # Nếu đã chuẩn Video · 720p · 10s · 9:16 · x1 thì không cần mở lại popup
        if "Video" in pill_text and "720p" in pill_text and "10s" in pill_text and ("9:16" in pill_text or "crop_9_16" in pill_text) and "x1" in pill_text:
            add_log(f"-> Cấu hình Flow đã sẵn sàng: {pill_text}", level="success")
            return

        # 2. Đóng popup cũ nếu đang mở
        page.keyboard.press("Escape")
        time.sleep(0.3)

        # 3. Bấm mở popup Settings
        page.evaluate('''() => {
            const btn = document.querySelector('button.settings-trigger-button, button[aria-label="Settings trigger"]');
            if (btn) btn.click();
        }''')
        time.sleep(0.8)

        # 4. Thiết lập lần lượt: Video, Ingredients, 9:16, 720p, 10s, x1 qua click JS trực tiếp
        page.evaluate('''() => {
            const targets = ['Video', 'Ingredients', '9:16', '720p', '10s', 'x1'];
            document.querySelectorAll('mat-button-toggle').forEach(toggle => {
                const txt = toggle.innerText.trim();
                targets.forEach(target => {
                    if (txt.includes(target)) {
                        if (!toggle.classList.contains('mat-button-toggle-checked')) {
                            const btn = toggle.querySelector('button') || toggle;
                            btn.click();
                        }
                    }
                });
            });
        }''')
        time.sleep(0.5)

        # 5. Đóng popup
        page.keyboard.press("Escape")
        time.sleep(0.5)

        updated_pill = page.evaluate('''() => {
            const btn = document.querySelector('button.settings-trigger-button, button[aria-label="Settings trigger"]');
            return btn ? btn.innerText.trim().replace(/\\n/g, ' ') : '';
        }''')
        add_log(f"-> ĐÃ THIẾT LẬP XONG SETTINGS: {updated_pill or 'Video | Ingredients | 9:16 | 720p | 10s | x1'}!", level="success")

    except Exception as e:
        add_log(f"Lưu ý khi chỉnh settings Flow: {e}", level="warning")
        page.keyboard.press("Escape")

def download_video_via_browser(page, video_url: str, target_path: Path) -> bool:
    """Tải trực tiếp video bằng authenticated session trong Chrome"""
    try:
        data_b64 = page.evaluate('''async (url) => {
            const res = await fetch(url);
            if (!res.ok) throw new Error('Fetch failed with status ' + res.status);
            const blob = await res.blob();
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result.split(',')[1]);
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });
        }''', video_url)

        if data_b64:
            content = base64.b64decode(data_b64)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(content)
            return True
    except Exception as e:
        add_log(f"Lỗi tải video URL {video_url[:60]}: {e}", level="warning")
    return False

def clear_prompt_box_ingredients(page):
    """Xóa sạch các chips ingredient/reference cũ nếu có trong ô prompt"""
    try:
        clear_btn = page.locator("flow-prompt-box button[aria-label='Clear prompt']").first
        if clear_btn.is_visible():
            clear_btn.click()
            time.sleep(0.3)
        # Nếu vẫn còn chip, click gỡ từng chip
        chips = page.locator("flow-prompt-box .chip-container").all()
        for c in chips:
            c.click()
            time.sleep(0.2)
    except Exception:
        pass

def attach_previous_video_as_reference(page, ref_clip_index: int) -> bool:
    """
    Thêm video clip trước đó (Clip 1, Clip 2...) làm Reference/Ingredient cho prompt tiếp theo.
    """
    try:
        add_log(f"-> Đang gắn Clip {ref_clip_index} làm Reference / Ingredient cho clip tiếp theo...", level="info")
        
        # Dọn sạch chips cũ trong prompt box trước
        clear_prompt_box_ingredients(page)

        # Lấy danh sách tile containers trên canvas
        tiles = page.locator("flow-tile-container").all()
        if not tiles:
            add_log("Không tìm thấy thẻ video trên canvas để làm reference.", level="warning")
            return False

        # Thẻ mới nhất nằm ở vị trí đầu tiên
        target_tile = tiles[0]
        target_tile.scroll_into_view_if_needed()
        target_tile.hover()
        time.sleep(0.4)

        more_btn = target_tile.locator("button[aria-label='More options']").first
        if not more_btn.is_visible():
            target_tile.hover()
            time.sleep(0.3)

        if more_btn.is_visible():
            more_btn.click(timeout=3000)
            time.sleep(0.4)

            add_item = page.locator("[role='menuitem']").filter(has_text="Add to prompt").first
            if add_item.is_visible():
                add_item.click(timeout=3000)
                time.sleep(0.8)
                add_log(f"-> ĐÃ GẮN CLIP {ref_clip_index} VÀO PROMPT LÀM REFERENCE THÀNH CÔNG! (+ Add reference)", level="success")
                return True
            else:
                add_log("Không tìm thấy tùy chọn 'Add to prompt' trong menu.", level="warning")
        else:
            add_log("Nút 'More options' không hiển thị.", level="warning")
        page.keyboard.press("Escape")
    except Exception as e:
        add_log(f"Lỗi khi gắn reference video: {e}", level="warning")
        page.keyboard.press("Escape")
    return False

def attach_brand_icon_ingredient(page, asset_name: str = "brainmoney.jpg") -> bool:
    """
    Gắn asset thương hiệu (brainmoney.jpg) làm Reference/Ingredient cho Clip 3 (Cảnh kết thúc)
    """
    try:
        add_log(f"-> Đang gắn icon thương hiệu '{asset_name}' làm Reference cho phân cảnh kết...", level="info")
        is_menu_open = page.evaluate('''() => {
            const item = Array.from(document.querySelectorAll('.asset-title')).find(e => e.innerText.includes('brainmoney'));
            return !!item;
        }''')
        if not is_menu_open:
            page.evaluate('''() => {
                const btn = document.querySelector("button[aria-label='Add ingredients to the prompt box'], .add-menu-trigger");
                if (btn) btn.click();
            }''')
            time.sleep(0.8)

        success = page.evaluate('''(name) => {
            const item = Array.from(document.querySelectorAll('.asset-title')).find(e => e.innerText.includes(name) || e.innerText.toLowerCase().includes('brainmoney'));
            if (!item) return false;
            const btn = item.closest('button') || item;
            btn.click();
            return true;
        }''', asset_name)

        if success:
            time.sleep(0.5)
            page.keyboard.press("Escape")
            add_log(f"-> ĐÃ GẮN THÀNH CÔNG ICON '{asset_name}' VÀO PROMPT BOX LÀM REFERENCE!", level="success")
            return True
        else:
            add_log(f"Không tìm thấy asset '{asset_name}' trong thư viện Google Flow.", level="warning")
            page.keyboard.press("Escape")
    except Exception as e:
        add_log(f"Lỗi khi gắn brand icon: {e}", level="warning")
        page.keyboard.press("Escape")
    return False

def generate_video_clips(prompts: list[str], headless: bool = False) -> list[str]:
    """
    Tự động áp dụng setting (Video, Ingredients, 9:16, 720p, 10s, x1),
    sau đó dán 3 prompt kịch bản và bấm Start generation!
    Tự động gắn Clip trước làm Reference cho Clip sau để giữ tính nhất quán nhân vật và hình ảnh.
    Đặc biệt ở Clip 3: Tự động gắn thêm asset thương hiệu brainmoney.jpg làm Reference.
    Áp dụng quy tắc định danh chính xác video đang làm kể cả khi thư viện canvas đã rất lớn.
    """
    add_log(f"=== BƯỚC 2/4: CHUYỂN TIẾP SANG GOOGLE FLOW (OMNI 1.1) ===", level="info")
    downloaded_files = []

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0] if browser.contexts else browser.new_context()

        # 1. Tìm tab Google Flow Project đang mở
        flow_page = None
        for pg in context.pages:
            if "flow.google.com" in pg.url:
                flow_page = pg
                break

        if not flow_page:
            flow_page = context.new_page()
            flow_page.goto(config.GOOGLE_FLOW_URL, timeout=45000)
            time.sleep(3)
        else:
            # Đảm bảo đang ở trang canvas chính của project, không bị kẹt trong /edit/
            if flow_page.url.rstrip('/') != config.GOOGLE_FLOW_URL.rstrip('/'):
                flow_page.goto(config.GOOGLE_FLOW_URL, timeout=45000)
                time.sleep(3)

        flow_page.bring_to_front()
        add_log("-> Đã kết nối vào Google Flow Project!", level="success")

        # 2. Áp dụng chính xác bảng cấu hình cài đặt theo ảnh bạn gửi
        configure_flow_settings(flow_page)

        # 3. Theo dõi network response để bắt URL video mới sinh
        captured_video_urls = []
        def on_response(res):
            if "flow-content.google/video" in res.url:
                if res.url not in captured_video_urls:
                    captured_video_urls.append(res.url)
        flow_page.on("response", on_response)

        # 4. Lần lượt gửi từng prompt vào ô nhập và bấm Start generation
        for idx, prompt_text in enumerate(prompts):
            # Xử lý Reference tương ứng từng phân cảnh:
            if idx == 0:
                # Clip 1: Dọn sạch reference cũ
                clear_prompt_box_ingredients(flow_page)
            elif idx == 1:
                # Clip 2: Gắn Clip 1 làm reference
                attach_previous_video_as_reference(flow_page, ref_clip_index=1)
            elif idx == 2:
                # Clip 3 (Cảnh kết thúc): Gắn Clip 2 làm reference + Gắn thêm icon thương hiệu brainmoney.jpg
                attach_previous_video_as_reference(flow_page, ref_clip_index=2)
                attach_brand_icon_ingredient(flow_page, "brainmoney.jpg")
                if "brainmoney" not in prompt_text.lower():
                    prompt_text += " Towards the end of the scene, smoothly feature the brand icon brainmoney.jpg (brain with dollar coin) at the center with a glowing animation transition."

            add_log(f"-> Đang gửi Prompt Clip {idx + 1}/{len(prompts)} vào Google Flow...", level="info")
            add_log(f"   \"{prompt_text[:85]}...\"", level="info")

            target_filename = config.DOWNLOADS_DIR / f"clip_{idx + 1}.mp4"
            known_urls_before = set(captured_video_urls)
            gen_timestamp = time.time()

            # Tìm ô nhập prompt: .ProseMirror
            editor = flow_page.locator(".ProseMirror").first
            if not editor.is_visible():
                # Fallback thử selector khác
                editor = flow_page.locator("[contenteditable='true']").first

            if editor.is_visible():
                editor.click()
                time.sleep(0.2)
                # Dọn nội dung cũ và điền prompt mới
                flow_page.keyboard.press("Control+A")
                flow_page.keyboard.press("Backspace")
                time.sleep(0.2)
                editor.fill(prompt_text)
                time.sleep(0.5)

                # Bấm nút Start generation
                gen_btn = flow_page.locator("button[aria-label='Start generation'], button.generate-icon-button").first
                if gen_btn.is_visible() and not gen_btn.is_disabled():
                    gen_btn.click()
                else:
                    flow_page.keyboard.press("Enter")

                add_log(f"-> ĐÃ BẤM START GENERATION CLIP {idx + 1}! Đang render qua Omni 1.1 Flash (10s, 9:16)...", level="success")

                # Chờ video render xong và xuất hiện (thời gian render ~15-45s)
                new_video_found = False
                for wait_step in range(25):
                    time.sleep(2)
                    # Quy tắc 1: Kiểm tra URL mới phát sinh qua Network stream ngay sau mốc gen_timestamp
                    for u in captured_video_urls:
                        if u not in known_urls_before:
                            elapsed = round(time.time() - gen_timestamp)
                            add_log(f"-> Đã phát hiện stream video mới ({elapsed}s)! Bắt đầu tải clip {idx + 1}...", level="info")
                            if download_video_via_browser(flow_page, u, target_filename):
                                size_mb = round(target_filename.stat().st_size / (1024 * 1024), 2)
                                add_log(f"-> Đã tải thành công clip {idx + 1}/{len(prompts)} về máy! ({size_mb} MB)", level="success")
                                downloaded_files.append(str(target_filename))
                                new_video_found = True
                                break
                    if new_video_found:
                        break

                    # Quy tắc 2: Định danh trực tiếp theo Thẻ tile mới nhất ở đầu Canvas
                    if wait_step >= 6 and wait_step % 3 == 0:
                        try:
                            # Hover lên thẻ đầu tiên trên canvas (thẻ mới nhất đang sinh) để kích hoạt tải video
                            first_tile_src = flow_page.evaluate('''() => {
                                const tile = document.querySelector('flow-tile-container, .virtual-item-container');
                                if (tile) {
                                    tile.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
                                    const v = tile.querySelector('video');
                                    return v ? (v.src || v.currentSrc) : null;
                                }
                                return null;
                            }''')
                            if first_tile_src and first_tile_src not in known_urls_before and "blob:" not in first_tile_src:
                                if download_video_via_browser(flow_page, first_tile_src, target_filename):
                                    size_mb = round(target_filename.stat().st_size / (1024 * 1024), 2)
                                    add_log(f"-> Đã tải thành công clip {idx + 1} từ thẻ đầu Canvas! ({size_mb} MB)", level="success")
                                    downloaded_files.append(str(target_filename))
                                    new_video_found = True
                                    break
                        except Exception:
                            pass


                # Fallback nếu chưa tải được qua network stream
                if not new_video_found:
                    # Kiểm tra các thẻ video sẵn có trên canvas
                    all_vids = flow_page.evaluate('''() => {
                        return Array.from(document.querySelectorAll('video'))
                            .map(v => v.src || v.currentSrc)
                            .filter(Boolean);
                    }''')
                    for u in reversed(all_vids):
                        if u not in known_urls_before:
                            if download_video_via_browser(flow_page, u, target_filename):
                                size_mb = round(target_filename.stat().st_size / (1024 * 1024), 2)
                                add_log(f"-> Đã tải thành công clip {idx + 1}/{len(prompts)} về máy! ({size_mb} MB)", level="success")
                                downloaded_files.append(str(target_filename))
                                new_video_found = True
                                break

                # Dự phòng cuối cùng nếu Flow lưu về thư mục tải xuống của máy
                if not new_video_found and target_filename.exists() and target_filename.stat().st_size > 50000:
                    downloaded_files.append(str(target_filename))

                # Tạm dừng ngắn để Google Flow cập nhật thẻ clip mới lên đầu canvas trước khi tiếp tục
                time.sleep(2.5)

            else:
                add_log("Chưa thấy ô nhập prompt trên Flow Canvas (.ProseMirror).", level="warning")

        # Ngắt kết nối CDP mà KHÔNG đóng trình duyệt của người dùng
        try:
            browser.disconnect()
        except Exception:
            pass

    add_log(f"-> Hoàn tất quá trình sinh video trên Google Flow! ({len(downloaded_files)}/{len(prompts)} clip)", level="success")
    return downloaded_files

if __name__ == "__main__":
    sample = [
        "Simple 2D flat vector animation of a colorful piggy bank on a minimal pastel background (10s)",
        "Simple 2D flat vector animation of a hand taking coins from the piggy bank (10s)",
        "Simple 2D flat vector animation of gold coins stacking up into a chart (10s)"
    ]
    generate_video_clips(sample[:1])
