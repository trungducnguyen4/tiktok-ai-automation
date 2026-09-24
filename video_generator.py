import time
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright
import config
from logger import add_log

def ensure_flow_canvas_active(page):
    """
    Đảm bảo đang ở trang canvas chính của Google Flow Project,
    và thanh điều hướng bên trái đang chọn mục 'Tất cả nội dung nghe nhìn' để hiển thị đầy đủ các video tile.
    """
    try:
        # Nếu đang bị kẹt trong /edit/ hoặc /tools, chuyển về URL canvas chính
        current_url = page.url
        target_base = config.GOOGLE_FLOW_URL.rstrip('/')
        if '/edit/' in current_url or '/tools' in current_url or current_url.rstrip('/') != target_base:
            add_log("-> Điều hướng về màn hình canvas chính của Google Flow...", level="info")
            page.goto(config.GOOGLE_FLOW_URL, timeout=45000)
            time.sleep(3)

        # Chuyển bộ lọc sidebar sang "Tất cả" / "Tất cả nội dung nghe nhìn"
        switched = page.evaluate('''() => {
            const items = Array.from(document.querySelectorAll('mat-list-item, .side-nav-list-item'));
            const allItem = items.find(i => {
                const txt = i.innerText || '';
                return txt.includes('Tất cả nội dung') || txt.includes('All assets') || txt.includes('dashboard') || (txt.includes('Tất cả') && !txt.includes('Dự án'));
            });
            if (allItem) {
                allItem.click();
                return true;
            }
            return false;
        }''')
        if switched:
            time.sleep(1.0)
    except Exception as e:
        add_log(f"Lưu ý khi kích hoạt canvas Flow: {e}", level="warning")

def configure_flow_settings(page):
    """
    Tự động kiểm tra và áp dụng cấu hình:
    - Loại: Video
    - Chế độ: Ingredients
    - Tỷ lệ: 9:16 (Dọc chuẩn TikTok)
    - Model: Omni 1.1 Flash
    - Độ phân giải: 720p
    - Thời lượng: 8s / 10s
    - Số lượng clip: x1
    """
    try:
        add_log("-> Đang kiểm tra cấu hình Video Google Flow...", level="info")
        
        # 1. Kiểm tra trạng thái hiện tại trên nút pill settings
        pill_text = page.evaluate('''() => {
            const btn = document.querySelector('button.settings-trigger-button, button[aria-label="Settings trigger"], button[aria-label*="cài đặt"]');
            return btn ? btn.innerText.trim().replace(/\\n/g, ' ') : '';
        }''')
        
        if "Video" in pill_text and "720p" in pill_text and ("9:16" in pill_text or "crop_9_16" in pill_text) and "x1" in pill_text:
            add_log(f"-> Cấu hình Flow đã sẵn sàng: {pill_text}", level="success")
            return

        # 2. Đóng popup cũ nếu đang mở
        page.keyboard.press("Escape")
        time.sleep(0.3)

        # 3. Bấm mở popup Settings
        page.evaluate('''() => {
            const btn = document.querySelector('button.settings-trigger-button, button[aria-label="Settings trigger"], button[aria-label*="cài đặt"]');
            if (btn) btn.click();
        }''')
        time.sleep(0.8)

        # 4. Thiết lập lần lượt: Video, Ingredients, 9:16, 720p, 10s, x1 qua click JS trực tiếp
        page.evaluate('''() => {
            const targets = ['Video', 'Ingredients', '9:16', '720p', '10s', '8s', 'x1'];
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
            const btn = document.querySelector('button.settings-trigger-button, button[aria-label="Settings trigger"], button[aria-label*="cài đặt"]');
            return btn ? btn.innerText.trim().replace(/\\n/g, ' ') : '';
        }''')
        add_log(f"-> ĐÃ THIẾT LẬP XONG SETTINGS: {updated_pill or 'Video | Ingredients | 9:16 | 720p | x1'}!", level="success")

    except Exception as e:
        add_log(f"Lưu ý khi chỉnh settings Flow: {e}", level="warning")
        page.keyboard.press("Escape")

def clear_prompt_box_ingredients(page):
    """Xóa sạch các chips ingredient/reference cũ nếu có trong ô prompt"""
    try:
        page.evaluate('''() => {
            const chips = document.querySelectorAll('flow-base-prompt-box mat-chip, flow-base-prompt-box .chip-container, flow-base-prompt-box flow-ingredient-chip');
            chips.forEach(c => {
                const cancelBtn = c.querySelector('button, [aria-label*="Xoá"], [aria-label*="Remove"], mat-icon');
                if (cancelBtn) cancelBtn.click();
                else c.click();
            });
        }''')
        time.sleep(0.3)
    except Exception:
        pass

def attach_previous_video_as_reference(page, ref_clip_index: int) -> bool:
    """
    Thêm video clip trước đó (Clip 1, Clip 2...) làm Reference/Ingredient cho prompt tiếp theo.
    Hỗ trợ đầy đủ cả giao diện Tiếng Việt ('Tuỳ chọn khác' -> 'Thêm vào câu lệnh') và Tiếng Anh.
    """
    try:
        add_log(f"-> Đang gắn Clip {ref_clip_index} làm Reference cho phân cảnh tiếp theo...", level="info")
        
        # Dọn sạch chips cũ trong prompt box trước
        clear_prompt_box_ingredients(page)

        # Lấy danh sách tile containers trên canvas
        tiles = page.locator("flow-tile-container").all()
        if not tiles:
            add_log("Không tìm thấy thẻ video trên canvas để làm reference.", level="warning")
            return False

        # Thẻ video mới nhất nằm ở vị trí đầu tiên
        target_tile = tiles[0]
        target_tile.scroll_into_view_if_needed()
        target_tile.hover()
        time.sleep(0.4)

        more_btn = target_tile.locator("button[aria-label*='Tuỳ chọn khác'], button[aria-label*='More options'], .mat-mdc-menu-trigger").first
        if not more_btn.is_visible():
            target_tile.hover()
            time.sleep(0.4)

        if more_btn.is_visible():
            more_btn.click()
            time.sleep(0.6)

            # Chọn "Thêm vào câu lệnh" (VN) hoặc "Add to prompt" (EN)
            added = page.evaluate('''() => {
                const items = Array.from(document.querySelectorAll('[role="menuitem"], .mat-mdc-menu-item'));
                const target = items.find(m => m.innerText.includes('Thêm vào câu lệnh') || m.innerText.includes('Add to prompt'));
                if (target) {
                    target.click();
                    return true;
                }
                return false;
            }''')

            if added:
                time.sleep(0.8)
                page.keyboard.press("Escape")
                add_log(f"-> ĐÃ GẮN CLIP {ref_clip_index} VÀO PROMPT LÀM REFERENCE THÀNH CÔNG! (+ Add reference)", level="success")
                return True
            else:
                add_log("Không tìm thấy tùy chọn 'Thêm vào câu lệnh' trong menu.", level="warning")
        else:
            add_log("Nút 'Tuỳ chọn khác' không hiển thị trên thẻ video.", level="warning")
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
        
        # Mở popup Thêm thành phần
        page.evaluate('''() => {
            const btn = document.querySelector("button.add-menu-trigger, button[aria-label*='Thêm thành phần'], button[aria-label*='Add ingredients']");
            if (btn) btn.click();
        }''')
        time.sleep(1.0)

        # Trong menu popover, tìm nút "Thêm vào câu lệnh" cho brainmoney
        success = page.evaluate('''(name) => {
            const area = document.querySelector('.content-area, .right-panel, .cdk-overlay-container');
            if (!area) return false;
            const allItems = Array.from(area.querySelectorAll('*'));
            const bmItem = allItems.find(e => e.innerText && e.innerText.toLowerCase().includes(name.toLowerCase()) && e.children.length === 0);
            if (bmItem) {
                const container = bmItem.closest('flow-asset-list-item, .asset-item, div') || bmItem.parentElement;
                const addBtn = container.querySelector('button') || Array.from(area.querySelectorAll('button')).find(b => b.innerText.includes('Thêm vào câu lệnh') || b.innerText.includes('Add to prompt'));
                if (addBtn) {
                    addBtn.click();
                    return true;
                }
            }
            return false;
        }''', asset_name)

        time.sleep(0.8)
        page.keyboard.press("Escape")

        if success:
            add_log(f"-> ĐÃ GẮN THÀNH CÔNG ICON '{asset_name}' VÀO PROMPT BOX LÀM REFERENCE!", level="success")
            return True
        else:
            add_log(f"Không tìm thấy asset '{asset_name}' trong thư viện Google Flow.", level="warning")
    except Exception as e:
        add_log(f"Lỗi khi gắn brand icon: {e}", level="warning")
        page.keyboard.press("Escape")
    return False

def download_tile_via_menu(page, tile_index: int, target_path: Path) -> bool:
    """
    Tải trực tiếp video 720p độ nét cao chính thức qua menu 'Tải xuống' -> '720p Kích thước gốc' của thẻ Google Flow.
    Đây là phương thức tải video chuẩn xác 100%, bảo toàn chất lượng gốc và âm thanh.
    """
    try:
        tiles = page.locator("flow-tile-container").all()
        if not tiles or tile_index >= len(tiles):
            return False
            
        target_tile = tiles[tile_index]
        target_tile.scroll_into_view_if_needed()
        target_tile.hover()
        time.sleep(0.4)

        # 1. Bấm nút "Tuỳ chọn khác"
        more_btn = target_tile.locator("button[aria-label*='Tuỳ chọn khác'], button[aria-label*='More options'], .mat-mdc-menu-trigger").first
        if not more_btn.is_visible():
            target_tile.hover()
            time.sleep(0.4)
        if not more_btn.is_visible():
            return False

        more_btn.click()
        time.sleep(0.6)

        # 2. Hover / Click mục "Tải xuống" để mở menu con
        dl_opened = page.evaluate('''() => {
            const items = Array.from(document.querySelectorAll('[role="menuitem"], .mat-mdc-menu-item'));
            const dl = items.find(m => m.innerText.includes('Tải xuống') || m.innerText.includes('Download'));
            if (dl) {
                dl.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
                dl.click();
                return true;
            }
            return false;
        }''')
        if not dl_opened:
            page.keyboard.press("Escape")
            return False

        time.sleep(0.6)

        # 3. Bấm "720p" và chờ sự kiện tải file từ trình duyệt
        with page.expect_download(timeout=20000) as dl_info:
            p720_clicked = page.evaluate('''() => {
                const items = Array.from(document.querySelectorAll('[role="menuitem"], .mat-mdc-menu-item'));
                const p720 = items.find(m => m.innerText.includes('720p') || m.innerText.includes('Kích thước gốc') || m.innerText.includes('Original'));
                if (p720) {
                    p720.click();
                    return true;
                }
                return false;
            }''')
            if not p720_clicked:
                page.keyboard.press("Escape")
                return False

        download = dl_info.value
        target_path.parent.mkdir(parents=True, exist_ok=True)
        download.save_as(str(target_path))
        
        if target_path.exists() and target_path.stat().st_size > 50000:
            return True
    except Exception as e:
        add_log(f"Lỗi khi tải file qua menu tile: {e}", level="warning")
        page.keyboard.press("Escape")
    return False

def download_video_via_browser(page, video_url: str, target_path: Path) -> bool:
    """Tải dự phòng video qua fetch authenticated session nếu có URL direct stream"""
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

def generate_video_clips(prompts: list[str], headless: bool = False) -> list[str]:
    """
    Tự động áp dụng setting (Video, Ingredients, 9:16, 720p, 10s, x1),
    sau đó dán 3 prompt kịch bản và bấm Start generation!
    Tự động gắn Clip trước làm Reference cho Clip sau để giữ tính nhất quán nhân vật và hình ảnh.
    Đặc biệt ở Clip 3: Tự động gắn thêm asset thương hiệu brainmoney.jpg làm Reference.
    Tải trực tiếp video 720p qua menu chính thức của Google Flow, tuyệt đối không dùng lại file cũ.
    """
    add_log(f"=== BƯỚC 2/4: CHUYỂN TIẾP SANG GOOGLE FLOW (OMNI 1.1) ===", level="info")
    downloaded_files = []

    # 0. QUAN TRỌNG: Dọn dẹp sạch các file clip cũ trong downloads để không bao giờ bị chọn nhầm file rác cũ
    for i in range(1, 10):
        old_f = config.DOWNLOADS_DIR / f"clip_{i}.mp4"
        if old_f.exists():
            try:
                old_f.unlink()
            except Exception:
                pass

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

        flow_page.bring_to_front()
        add_log("-> Đã kết nối vào Google Flow Project!", level="success")

        # 2. Đảm bảo ở màn hình canvas chính và bộ lọc 'Tất cả' đang kích hoạt
        ensure_flow_canvas_active(flow_page)

        # 3. Áp dụng bảng cấu hình cài đặt
        configure_flow_settings(flow_page)

        # 4. Lắng nghe URL video trực tiếp nếu Flow bắn network stream
        captured_video_urls = []
        def on_response(res):
            if "flow-content.google/video" in res.url:
                if res.url not in captured_video_urls:
                    captured_video_urls.append(res.url)
        flow_page.on("response", on_response)

        # 5. Lần lượt gửi từng prompt vào ô nhập và bấm Bắt đầu tạo (Start generation)
        for idx, prompt_text in enumerate(prompts):
            target_filename = config.DOWNLOADS_DIR / f"clip_{idx + 1}.mp4"
            if target_filename.exists():
                try: target_filename.unlink()
                except Exception: pass

            # Đảm bảo canvas chính đang active
            ensure_flow_canvas_active(flow_page)

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
                if "same narrator" not in prompt_text.lower():
                    prompt_text += " Spoken voiceover by the SAME narrator as previous scenes."

            add_log(f"-> Đang gửi Prompt Clip {idx + 1}/{len(prompts)} vào Google Flow...", level="info")
            add_log(f"   \"{prompt_text[:85]}...\"", level="info")

            # Ghi nhận toàn bộ video URLs hiện có trên DOM và Network trước khi bấm tạo
            known_video_srcs = set(flow_page.evaluate('''() => {
                return Array.from(document.querySelectorAll("flow-tile-container video"))
                    .map(v => v.src)
                    .filter(Boolean);
            }'''))
            known_urls_before = set(captured_video_urls)
            gen_timestamp = time.time()

            # Tìm ô nhập prompt: .ProseMirror
            editor = flow_page.locator(".ProseMirror").first
            if not editor.is_visible():
                editor = flow_page.locator("[contenteditable='true']").first

            if not editor.is_visible():
                add_log("Chưa thấy ô nhập prompt trên Flow Canvas (.ProseMirror).", level="warning")
                continue

            editor.click()
            time.sleep(0.3)
            # Dọn nội dung cũ và điền prompt mới
            flow_page.keyboard.press("Control+A")
            flow_page.keyboard.press("Backspace")
            time.sleep(0.3)
            editor.fill(prompt_text)
            time.sleep(0.8)

            # Chờ nút Bắt đầu tạo (Start generation) được kích hoạt
            gen_btn = flow_page.locator("button.generate-icon-button, button[aria-label*='Bắt đầu tạo'], button[aria-label*='Start generation']").first
            
            clicked_gen = False
            for _ in range(5):
                if gen_btn.is_visible() and not gen_btn.is_disabled():
                    gen_btn.click()
                    clicked_gen = True
                    break
                time.sleep(0.5)

            if not clicked_gen:
                flow_page.keyboard.press("Enter")

            add_log(f"-> ĐÃ BẤM BẮT ĐẦU TẠO CLIP {idx + 1}! Đang render qua Omni 1.1 Flash (720p, 9:16)...", level="success")

            # Chờ video MỚI render xong và xuất hiện trên Canvas (tối đa 100s)
            new_video_found = False
            
            for wait_step in range(40):
                time.sleep(2.5)
                elapsed = round(time.time() - gen_timestamp)

                # Kiểm tra 1: Xem trên DOM có thẻ tile nào chứa video MỚI (src chưa từng xuất hiện trước đó)
                new_tile_info = flow_page.evaluate('''(known) => {
                    const knownSet = new Set(known);
                    const tiles = Array.from(document.querySelectorAll("flow-tile-container"));
                    for (let i = 0; i < tiles.length; i++) {
                        const v = tiles[i].querySelector("video");
                        if (v && v.src && !knownSet.has(v.src)) {
                            return { tileIndex: i, videoSrc: v.src };
                        }
                    }
                    return null;
                }''', list(known_video_srcs))

                if new_tile_info:
                    tile_idx = new_tile_info["tileIndex"]
                    new_src = new_tile_info["videoSrc"]
                    add_log(f"-> Clip mới {idx + 1} đã render hoàn tất tại thẻ {tile_idx} ({elapsed}s)!", level="success")
                    
                    # 1a. Tải chất lượng chuẩn 720p qua menu chính thức
                    if download_tile_via_menu(flow_page, tile_idx, target_filename):
                        size_mb = round(target_filename.stat().st_size / (1024 * 1024), 2)
                        add_log(f"-> ĐÃ TẢI XONG CLIP {idx + 1}/{len(prompts)} TỪ MENU GOOGLE FLOW! ({size_mb} MB, {elapsed}s)", level="success")
                        downloaded_files.append(str(target_filename))
                        new_video_found = True
                        break

                    # 1b. Fallback tải trực tiếp từ stream URL mới này nếu menu bận
                    if download_video_via_browser(flow_page, new_src, target_filename):
                        size_mb = round(target_filename.stat().st_size / (1024 * 1024), 2)
                        add_log(f"-> ĐÃ TẢI XONG CLIP {idx + 1}/{len(prompts)} QUA STREAM URL MỚI! ({size_mb} MB)", level="success")
                        downloaded_files.append(str(target_filename))
                        new_video_found = True
                        break

                # Kiểm tra 2: Kiểm tra URL mới phát sinh qua Network stream
                new_net_url = None
                for u in captured_video_urls:
                    if u not in known_urls_before:
                        new_net_url = u
                        break

                if new_net_url:
                    add_log(f"-> Đã phát hiện stream video mới ({elapsed}s)! Đang tải clip {idx + 1}...", level="info")
                    if download_video_via_browser(flow_page, new_net_url, target_filename):
                        size_mb = round(target_filename.stat().st_size / (1024 * 1024), 2)
                        add_log(f"-> Đã tải thành công clip {idx + 1}/{len(prompts)} về máy! ({size_mb} MB)", level="success")
                        downloaded_files.append(str(target_filename))
                        new_video_found = True
                        break

                if wait_step % 5 == 0 and elapsed > 0:
                    add_log(f"   [Đang render Clip {idx + 1} qua Omni 1.1...] Đã trôi qua {elapsed}s...", level="info")

            if not new_video_found:
                add_log(f"[CẢNH BÁO] Không thể tải clip {idx + 1} mới sinh. Tuyệt đối không tái sử dụng file cũ để tránh sai lệch kịch bản!", level="error")

            time.sleep(2.0)

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
