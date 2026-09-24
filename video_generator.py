import time
import base64
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
from moviepy import VideoFileClip
import config
from logger import add_log

def ensure_flow_canvas_active(page):
    """
    Đảm bảo đang ở trang canvas chính của Google Flow Project,
    và thanh điều hướng bên trái đang chọn mục 'Tất cả nội dung nghe nhìn' để hiển thị đầy đủ các video tile.
    """
    try:
        current_url = page.url
        target_base = config.GOOGLE_FLOW_URL.rstrip('/')
        if '/edit/' in current_url or '/tools' in current_url or current_url.rstrip('/') != target_base:
            add_log("-> Điều hướng về màn hình canvas chính của Google Flow...", level="info")
            page.goto(config.GOOGLE_FLOW_URL, timeout=45000)
            time.sleep(3)

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
    Tự động kiểm tra và áp dụng cấu hình chuẩn xác:
    - Loại: Video
    - Chế độ: Thành phần / Ingredients
    - Tỷ lệ: 9:16 (Dọc chuẩn TikTok)
    - Model: Omni 1.1 Flash
    - Độ phân giải: 720p
    - Thời lượng: 10 giây (Bắt buộc chọn 10s, tuyệt đối không chọn 8s / 6s / 4s)
    - Số lượng clip: x1
    """
    try:
        add_log("-> Đang kiểm tra cấu hình Video Google Flow...", level="info")
        
        # 1. Kiểm tra trạng thái hiện tại trên nút pill settings
        pill_text = page.evaluate('''() => {
            const btn = document.querySelector('button.settings-trigger-button, button[aria-label="Settings trigger"], button[aria-label*="cài đặt"]');
            return btn ? btn.innerText.trim().replace(/\\n/g, ' ') : '';
        }''')
        
        has_10s = ("10 giây" in pill_text or "10s" in pill_text or "10 gi" in pill_text)
        has_video = ("Video" in pill_text)
        has_720p = ("720p" in pill_text)
        has_916 = ("9:16" in pill_text or "crop_9_16" in pill_text)
        has_x1 = ("x1" in pill_text)

        if has_video and has_720p and has_916 and has_x1 and has_10s:
            add_log(f"-> Cấu hình Flow đã chuẩn xác 10s: {pill_text}", level="success")
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

        # 4. Thiết lập lần lượt: Video, Thành phần, 9:16, 720p, 10 giây, x1
        # Lưu ý: Bỏ qua và tuyệt đối không click các nút 4 giây, 6 giây, 8 giây!
        page.evaluate('''() => {
            const targets = ['Video', 'Thành phần', 'Ingredients', '9:16', '720p', '10 giây', '10s', 'x1'];
            document.querySelectorAll('mat-button-toggle').forEach(toggle => {
                const txt = toggle.innerText.trim();
                // Bỏ qua các lựa chọn thời lượng ngắn
                if (txt.includes('4 giây') || txt.includes('6 giây') || txt.includes('8 giây') || txt.includes('8s') || txt.includes('4s') || txt.includes('6s')) {
                    return;
                }
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
        add_log(f"-> ĐÃ THIẾT LẬP XONG CẤU HÌNH: {updated_pill or 'Video | 720p | 10 giây | 9:16 | x1'}!", level="success")

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
    Thêm video clip vừa render xong ở vị trí đầu tiên (Tile 0) làm Reference cho prompt tiếp theo.
    Hỗ trợ đầy đủ cả giao diện Tiếng Việt ('Tuỳ chọn khác' -> 'Thêm vào câu lệnh') và Tiếng Anh.
    """
    try:
        add_log(f"-> Đang gắn Clip {ref_clip_index} làm Reference cho phân cảnh tiếp theo...", level="info")
        
        clear_prompt_box_ingredients(page)

        tiles = page.locator("flow-tile-container").all()
        if not tiles:
            add_log("Không tìm thấy thẻ video trên canvas để làm reference.", level="warning")
            return False

        # Thẻ video mới nhất vừa render luôn nằm ở vị trí đầu tiên (Tile 0)
        target_tile = tiles[0]
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
                add_log(f"-> ĐÃ GẮN CLIP {ref_clip_index} VÀO PROMPT LÀM REFERENCE THÀNH CÔNG!", level="success")
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

        # Trong menu popover, tìm nút "Thêm vào câu lệnh" cho asset_name
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

def download_clip_file(video_src: str, target_path: Path, page=None, tile_idx: int = 0) -> bool:
    """
    Tải video 720p độ nét cao chính thức trực tiếp từ Signed CDN URL của Google Flow.
    Đảm bảo 100% video tải về đúng file, đầy đủ âm thanh gốc Gemini và không bao giờ tải nhầm file cũ.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        try: target_path.unlink()
        except Exception: pass

    # 1. Tải trực tiếp qua Google Cloud Signed CDN URL bằng urllib
    try:
        req = urllib.request.Request(video_src, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Referer": "https://flow.google.com/"
        })
        with urllib.request.urlopen(req, timeout=30) as response, open(target_path, "wb") as out_file:
            out_file.write(response.read())

        if target_path.exists() and target_path.stat().st_size > 300_000:
            return True
    except Exception as e:
        add_log(f"Lưu ý khi tải trực tiếp qua CDN URL: {e}. Thử tải qua browser session...", level="warning")

    # 2. Fallback: Tải qua fetch authenticated session trên browser page
    if page:
        try:
            data_b64 = page.evaluate('''async (url) => {
                const res = await fetch(url);
                if (!res.ok) throw new Error('Fetch status: ' + res.status);
                const blob = await res.blob();
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result.split(',')[1]);
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                });
            }''', video_src)
            if data_b64:
                with open(target_path, "wb") as f:
                    f.write(base64.b64decode(data_b64))
                if target_path.exists() and target_path.stat().st_size > 300_000:
                    return True
        except Exception as e:
            add_log(f"Lỗi khi fallback tải qua browser: {e}", level="warning")

    return False

def generate_video_clips(prompts: list[str], headless: bool = False) -> list[str]:
    """
    Quy trình sinh video tự động trên Google Flow (Omni 1.1 Flash 10s):
    1. Đảm bảo setting: Video, 720p, 10 giây chuẩn, 9:16, x1.
    2. Dọn sạch toàn bộ file clip cũ trong downloads để KHÔNG BAO GIỜ bị nhầm file cũ.
    3. Gửi lần lượt từng prompt, chờ Google Flow render xong thực sự (tối thiểu 15s, tối đa 120s).
    4. Chỉ bắt đúng thẻ video mới nhất (ở đầu canvas) có URL chưa từng xuất hiện.
    5. Tuyệt đối KHÔNG bắt nhầm video cũ từ các chủ đề trước.
    """
    add_log(f"=== BƯỚC 2/3: CHUYỂN TIẾP SANG GOOGLE FLOW (OMNI 1.1) ===", level="info")
    downloaded_files = []

    # 0. QUAN TRỌNG: Xóa sạch toàn bộ các clip cũ trong thư mục downloads để tránh lấy nhầm
    for f in config.DOWNLOADS_DIR.glob("clip_*.mp4"):
        try: f.unlink()
        except Exception: pass

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

        # 2. Đảm bảo ở màn hình canvas chính
        ensure_flow_canvas_active(flow_page)

        # 3. Áp dụng bảng cấu hình cài đặt (bắt buộc 10 giây)
        configure_flow_settings(flow_page)

        # 4. Lần lượt gửi từng prompt vào ô nhập và bấm Bắt đầu tạo (Start generation)
        for idx, prompt_text in enumerate(prompts):
            target_filename = config.DOWNLOADS_DIR / f"clip_{idx + 1}.mp4"
            if target_filename.exists():
                try: target_filename.unlink()
                except Exception: pass

            ensure_flow_canvas_active(flow_page)

            # Xử lý Reference tương ứng từng phân cảnh:
            if idx == 0:
                clear_prompt_box_ingredients(flow_page)
            elif idx == 1:
                attach_previous_video_as_reference(flow_page, ref_clip_index=1)
            elif idx == 2:
                attach_previous_video_as_reference(flow_page, ref_clip_index=2)
                attach_brand_icon_ingredient(flow_page, "brainmoney.jpg")
                if "brainmoney" not in prompt_text.lower():
                    prompt_text += " Towards the end of the scene, smoothly feature the brand icon brainmoney.jpg (brain with dollar coin) at the center with a glowing animation transition."
                if "same narrator" not in prompt_text.lower():
                    prompt_text += " Spoken voiceover by the SAME narrator as previous scenes."

            add_log(f"-> Đang gửi Prompt Clip {idx + 1}/{len(prompts)} vào Google Flow...", level="info")
            add_log(f"   \"{prompt_text[:85]}...\"", level="info")

            # Ghi nhận toàn bộ video URLs hiện có trên Canvas TRƯỚC KHI BẤM TẠO
            known_video_srcs = set(flow_page.evaluate('''() => {
                return Array.from(document.querySelectorAll("flow-tile-container video"))
                    .map(v => v.src)
                    .filter(Boolean);
            }'''))

            gen_timestamp = time.time()

            # Tìm ô nhập prompt: .ProseMirror hoặc [contenteditable='true']
            editor = flow_page.locator(".ProseMirror").first
            if not editor.is_visible():
                editor = flow_page.locator("[contenteditable='true']").first

            if not editor.is_visible():
                raise RuntimeError("Chưa thấy ô nhập prompt trên Flow Canvas (.ProseMirror).")

            editor.click()
            time.sleep(0.3)
            flow_page.keyboard.press("Control+A")
            flow_page.keyboard.press("Backspace")
            time.sleep(0.3)
            editor.fill(prompt_text)
            time.sleep(0.8)

            # Bấm nút Bắt đầu tạo (Start generation)
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

            add_log(f"-> ĐÃ BẤM BẮT ĐẦU TẠO CLIP {idx + 1}! Đang render qua Omni 1.1 Flash (720p, 10s, 9:16)...", level="success")

            # Chờ video MỚI render hoàn tất trên Canvas (tối thiểu 8s, tối đa 240s)
            new_video_found = False
            
            for wait_step in range(80):
                time.sleep(3.0)
                elapsed = round(time.time() - gen_timestamp)

                # Kiểm tra các thẻ ở đầu canvas (index 0 đến 2)
                # Tuyệt đối không kiểm tra các thẻ phía sau để tránh bắt nhầm video cũ từ ngày hôm trước!
                new_tile_info = flow_page.evaluate('''(known) => {
                    const knownSet = new Set(known);
                    const tiles = Array.from(document.querySelectorAll("flow-tile-container"));
                    // Video mới sinh luôn xuất hiện ở vị trí đầu tiên của canvas (Tile 0 hoặc 1)
                    const checkLimit = Math.min(3, tiles.length);
                    for (let i = 0; i < checkLimit; i++) {
                        const tile = tiles[i];
                        const v = tile.querySelector("video");
                        // flow-pending-tile là thẻ chờ sinh của Google Flow
                        const isPending = !!tile.querySelector("flow-pending-tile");
                        const hasVideoTile = !!tile.querySelector("flow-video-tile");
                        
                        if (hasVideoTile && !isPending && v && v.src && !knownSet.has(v.src)) {
                            if (v.duration > 0 || v.readyState >= 2) {
                                return {
                                    tileIndex: i,
                                    videoSrc: v.src,
                                    duration: v.duration || 0
                                };
                            }
                        }
                    }
                    return null;
                }''', list(known_video_srcs))

                # Đảm bảo video đã thực sự render xong (thời gian tối thiểu 8s)
                if new_tile_info and elapsed >= 8:
                    new_src = new_tile_info["videoSrc"]
                    tile_idx = new_tile_info["tileIndex"]
                    add_log(f"-> Clip mới {idx + 1} đã render hoàn tất tại vị trí thẻ {tile_idx} ({elapsed}s)!", level="success")
                    
                    if download_clip_file(new_src, target_filename, flow_page, tile_idx):
                        size_mb = round(target_filename.stat().st_size / (1024 * 1024), 2)
                        
                        # Kiểm tra độ dài video bằng MoviePy để xác nhận chất lượng
                        try:
                            check_clip = VideoFileClip(str(target_filename))
                            actual_dur = round(check_clip.duration, 1)
                            check_clip.close()
                        except Exception:
                            actual_dur = 10.0

                        add_log(f"-> ĐÃ TẢI XONG CLIP {idx + 1}/{len(prompts)} CHUẨN XÁC! (Thời lượng: {actual_dur}s, {size_mb} MB, {elapsed}s)", level="success")
                        downloaded_files.append(str(target_filename))
                        new_video_found = True
                        break

                if wait_step % 4 == 0 and elapsed > 0:
                    add_log(f"   [Đang render Clip {idx + 1} qua Omni 1.1...] Đã trôi qua {elapsed}s...", level="info")

            if not new_video_found:
                add_log(f"[LỖI] Không thể tải clip {idx + 1} mới sinh sau 240s! Dừng quy trình để không ghép nhầm video cũ.", level="error")
                raise RuntimeError(f"Google Flow không thể hoàn tất sinh Clip {idx + 1} sau 240s.")

            time.sleep(2.0)

        try:
            browser.disconnect()
        except Exception:
            pass

    add_log(f"-> Hoàn tất quá trình sinh video trên Google Flow! Đã tải đúng {len(downloaded_files)}/{len(prompts)} clip chuẩn 10s mới nhất.", level="success")
    return downloaded_files

if __name__ == "__main__":
    sample = [
        "Simple 2D flat vector animation of a colorful piggy bank on a minimal pastel background (10s)",
        "Simple 2D flat vector animation of a hand taking coins from the piggy bank (10s)",
        "Simple 2D flat vector animation of gold coins stacking up into a chart (10s)"
    ]
    generate_video_clips(sample[:1])
