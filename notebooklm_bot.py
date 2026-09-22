import json
import re
import time
from playwright.sync_api import sync_playwright
import config
from logger import add_log

PROMPT_TEMPLATE = """Hãy chọn 1 chủ đề ngẫu nhiên từ tài liệu notebook này về tâm lý học hành vi hoặc tài chính, sau đó viết kịch bản hoàn chỉnh gồm chính xác 3 phân cảnh (mỗi phân cảnh 10 giây, tổng video 30 giây) để làm video ngắn TikTok.

YÊU CẦU CHO MỖI PHÂN CẢNH (CẢNH 1, 2, 3):
1. PROMPT HÌNH ẢNH (BẰNG TIẾNG ANH):
   - Phong cách BẮT BUỘC: HÌNH ẢNH HOẠT HÌNH 2D CƠ BẢN, ĐƠN GIẢN, PHẲNG (Clean 2D flat animation, simple minimalist vector art, minimal pastel background, smooth basic 2D motion graphics).
   - KHÔNG dùng phong cách điện ảnh (cinematic), KHÔNG tả quá chi tiết phức tạp, KHÔNG tả người thật (photorealistic/live action).
   - Mô tả ngắn gọn (1-2 câu tiếng Anh) minh họa trực quan khái niệm tài chính hoặc tâm lý học hành vi.
2. LỜI BÌNH / GIỌNG ĐỌC THUYẾT MINH (VOICEOVER BẰNG TIẾNG VIỆT):
   - Viết 1-2 câu tiếng Việt ngắn gọn, văn phong nói tự nhiên, hấp dẫn, cuốn hút người xem TikTok.
   - Thời lượng đọc vừa vặn khoảng 8-10 giây cho mỗi cảnh.
3. CHỮ CHẠY / TIÊU ĐỀ PHỤ ĐỀ (CAPTION BẰNG TIẾNG VIỆT):
   - 1 câu phụ đề ngắn nổi bật (dưới 10 chữ, viết hoa hoặc giật tít) để hiện chữ chạy trên video TikTok.

Đồng thời tạo 1 tiêu đề video TikTok ngắn gọn, cuốn hút và danh sách 5 hashtag thịnh hành liên quan.

BẮT BUỘC trả về kết quả dưới định dạng JSON duy nhất, không thêm lời chào hay giải thích ngoài JSON:
{
  "topic": "Tên chủ đề được chọn",
  "title": "Tiêu đề video TikTok giật tít",
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"],
  "prompts": [
    "Simple 2D flat vector animation of [mô tả ngắn gọn đồ họa 2d bằng tiếng Anh] (10s)",
    "Simple 2D flat vector animation of [mô tả ngắn gọn đồ họa 2d bằng tiếng Anh] (10s)",
    "Simple 2D flat vector animation of [mô tả ngắn gọn đồ họa 2d bằng tiếng Anh] (10s)"
  ],
  "voiceovers": [
    "Lời đọc thuyết minh tiếng Việt cho đoạn 1...",
    "Lời đọc thuyết minh tiếng Việt cho đoạn 2...",
    "Lời đọc thuyết minh tiếng Việt cho đoạn 3..."
  ],
  "captions": [
    "PHỤ ĐỀ NỔI BẬT ĐOẠN 1",
    "PHỤ ĐỀ NỔI BẬT ĐOẠN 2",
    "PHỤ ĐỀ NỔI BẬT ĐOẠN 3"
  ]
}
"""

def is_valid_script_data(data: dict) -> bool:
    """
    Kiểm tra JSON kịch bản có hợp lệ và thực sự là câu trả lời của AI
    (loại trừ các chuỗi giữ chỗ/placeholder mẫu)
    """
    if not isinstance(data, dict):
        return False
    topic = str(data.get("topic", "")).strip()
    if not topic or "Tên chủ đề" in topic or "[chủ đề]" in topic:
        return False
    prompts = data.get("prompts", [])
    if not isinstance(prompts, list) or len(prompts) < 3:
        return False
    for p in prompts:
        if not isinstance(p, str):
            return False
        p_clean = p.strip()
        if len(p_clean) < 15:
            return False
        # Tuyệt đối loại bỏ prompt nếu còn chứa chữ mẫu của template
        if "[mô tả" in p_clean or "mô tả ngắn gọn" in p_clean or "bằng tiếng Anh" in p_clean:
            return False

    # Đảm bảo có voiceovers và captions hợp lệ (nếu thiếu sẽ tự động bổ trợ)
    voiceovers = data.get("voiceovers", [])
    if not isinstance(voiceovers, list) or len(voiceovers) < 3:
        data["voiceovers"] = [
            f"Bạn có từng nghe về hiệu ứng tâm lý {topic} trong cuộc sống?",
            "Cái bẫy tư duy này khiến chúng ta tiêu xài và quyết định thiếu lý trí.",
            "Hãy nhận diện sớm để quản lý tài chính và tư duy thông minh hơn!"
        ]
    else:
        # Kiểm tra xem có chứa text mẫu không
        for vo in data["voiceovers"]:
            if "[lời đọc" in str(vo).lower() or "thuyết minh tiếng việt cho" in str(vo).lower():
                return False

    captions = data.get("captions", [])
    if not isinstance(captions, list) or len(captions) < 3:
        data["captions"] = [
            topic.upper()[:30],
            "BẪY TÂM LÝ KHIẾN BẠN MẤT TIỀN!",
            "LÀM CHỦ TƯ DUY TÀI CHÍNH!"
        ]

    return True

def extract_json_robust(text: str) -> dict | None:
    """
    Trích xuất chính xác JSON từ văn bản phản hồi của AI
    """
    matches = re.findall(r'\{[\s\S]*?"prompts"[\s\S]*?\}', text)
    if matches:
        for m in reversed(matches):
            try:
                clean_str = re.sub(r'^```json\s*', '', m.strip())
                clean_str = re.sub(r'\s*```$', '', clean_str)
                data = json.loads(clean_str)
                if is_valid_script_data(data):
                    return data
            except Exception:
                pass

    any_matches = re.findall(r'\{[\s\S]*?\}', text)
    if any_matches:
        for m in reversed(any_matches):
            try:
                clean_str = re.sub(r'^```json\s*', '', m.strip())
                clean_str = re.sub(r'\s*```$', '', clean_str)
                data = json.loads(clean_str)
                if is_valid_script_data(data):
                    return data
            except Exception:
                pass
    return None

def get_vetted_fallback() -> dict:
    return {
        "topic": "Kế toán tâm lý (Mental Accounting)",
        "title": "Bẫy tâm lý khiến bạn tiêu tiền phung phí mà không hề hay biết!",
        "hashtags": [
            "#MentalAccounting",
            "#TamLyHocTaiChinh",
            "#TaiChinhCaNhan",
            "#KinhTeHocHanhVi",
            "#MeoTietKiem"
        ],
        "prompts": [
            "Simple 2D flat vector animation of a colorful piggy bank splitting into three separate labeled glass jars for salary, bonus, and gift money on a minimal pastel background (10s)",
            "Simple 2D flat vector animation of a hand quickly spending money from a bonus jar on shopping icons while carefully locking the salary jar in a vault (10s)",
            "Simple 2D flat vector animation of three separate money jars merging into one single unified gold coin icon to show all money has equal value (10s)"
        ],
        "voiceovers": [
            "Tại sao tiền thưởng Tết ta tiêu rất nhanh, còn tiền lương hàng tháng lại nâng niu từng đồng?",
            "Đó chính là Kế toán tâm lý! Não bộ tự chia tiền vào các ngăn vô hình và đối xử không công bằng với chúng.",
            "Hãy nhớ: Mọi đồng tiền đều có giá trị ngang nhau. Đừng để cảm xúc đánh lừa chiếc ví của bạn!"
        ],
        "captions": [
            "BẪY KẾ TOÁN TÂM LÝ!",
            "TIỀN NÀO CŨNG LÀ TIỀN CỦA BẠN!",
            "TẬP TRUNG VÀO GIÁ TRỊ THỰC!"
        ]
    }

def clear_notebooklm_chat(page):
    """
    Tự động xóa lịch sử chat cũ trên NotebookLM nếu có, bỏ qua nếu đã sạch
    """
    try:
        opt_btn = page.locator("button[aria-label*='Lựa chọn trò chuyện'], button[aria-label*='Chat options']").first
        if opt_btn.is_visible():
            opt_btn.click()
            time.sleep(0.4)

            clear_item = page.locator("[role='menuitem']").filter(has_text="Xoá nhật ký trò chuyện").first
            if not clear_item.is_visible():
                clear_item = page.locator("[role='menuitem']").filter(has_text="Clear").first

            # Nếu nút xóa bị disabled nghĩa là chat đã sạch sẵn
            if clear_item.is_visible():
                is_disabled = clear_item.is_disabled() or "disabled" in (clear_item.get_attribute("class") or "")
                if is_disabled:
                    page.keyboard.press("Escape")
                    add_log("-> Nhật ký chat NotebookLM đã sạch sẵn, sẵn sàng tạo mới!", level="info")
                    return

                clear_item.click(timeout=3000)
                time.sleep(0.5)

                # Xác nhận xóa trong dialog
                confirm_btn = page.locator("mat-dialog-container button").filter(has_text="Xoá").first
                if not confirm_btn.is_visible():
                    confirm_btn = page.locator("mat-dialog-container button").filter(has_text="Delete").first

                if confirm_btn.is_visible():
                    confirm_btn.click()
                    time.sleep(1)
                    add_log("-> Đã dọn dẹp sạch nhật ký chat cũ trên NotebookLM!", level="success")
                    return
        page.keyboard.press("Escape")
    except Exception as e:
        add_log(f"Ghi chú kiểm tra chat NotebookLM: {e}", level="info")
        page.keyboard.press("Escape")

def fetch_notebooklm_prompts(headless: bool = False) -> dict:
    add_log("Đang kết nối vào phiên Chrome có sẵn NotebookLM...", level="info")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0] if browser.contexts else browser.new_context()

        # Tìm tab NotebookLM đang mở sẵn
        target_page = None
        for pg in context.pages:
            if "notebook.google.com" in pg.url:
                target_page = pg
                break

        if not target_page:
            target_page = context.new_page()
            target_page.goto(config.NOTEBOOKLM_URL, timeout=45000)
            time.sleep(3)

        target_page.bring_to_front()
        add_log(f"-> Đã kết nối vào Notebook: '{target_page.title()}'", level="success")

        # Đếm số thẻ tin nhắn AI hiện có trước khi gửi câu hỏi mới
        initial_ai_count = target_page.locator(".to-user-message-card-content, .to-user-message-inner-content").count()

        # Điền prompt trực tiếp bằng locator.fill
        add_log("-> Đang gõ prompt yêu cầu kịch bản 2D vào ô 'Đặt câu hỏi hoặc tạo nội dung'...", level="info")
        active_ta = target_page.locator("textarea[placeholder*='Đặt câu hỏi'], textarea:not([disabled])").last
        if active_ta.is_visible():
            active_ta.click()
            time.sleep(0.2)
            active_ta.fill(PROMPT_TEMPLATE)
            time.sleep(0.5)

            # Bấm nút gửi mũi tên
            submit_btn = target_page.locator("button.submit-button, button:has(mat-icon:has-text('arrow_forward'))").last
            if submit_btn.is_visible() and not submit_btn.is_disabled():
                submit_btn.click()
            else:
                active_ta.press("Enter")

            add_log("-> ĐÃ BẤM GỬI CÂU HỎI VÀO NOTEBOOKLM! Đang chờ AI phản hồi kịch bản 2D...", level="success")
        else:
            raise RuntimeError("Không tìm thấy ô nhập câu hỏi trên NotebookLM!")

        # Chờ phản hồi từ AI trong thẻ .to-user-message-card-content (tối đa 45 giây)
        data = None
        for wait_sec in range(25):
            time.sleep(2)
            cards = target_page.locator(".to-user-message-card-content, .to-user-message-inner-content").all()
            if len(cards) > initial_ai_count:
                latest_card = cards[-1]
                card_text = latest_card.inner_text()
                parsed = extract_json_robust(card_text)
                if parsed:
                    data = parsed
                    break

        # Nếu chưa lấy được từ tin nhắn mới nhất, kiểm tra lại toàn bộ các thẻ AI theo chiều ngược lại
        if not data:
            cards = target_page.locator(".to-user-message-card-content, .to-user-message-inner-content").all()
            for c in reversed(cards):
                parsed = extract_json_robust(c.inner_text())
                if parsed:
                    data = parsed
                    break

        # Fallback an toàn nếu AI mạng chập chờn
        if not data:
            add_log("-> Không trích xuất được phản hồi mới từ AI, sử dụng chủ đề chuẩn bị sẵn.", level="warning")
            data = get_vetted_fallback()

        add_log(f"-> Chủ đề được chọn: '{data.get('topic')}'", level="success")
        add_log(f"-> Tiêu đề TikTok: '{data.get('title')}'", level="success")
        add_log(f"-> Đã trích xuất thành công {len(data.get('prompts', []))} prompts hoạt hình 2D (10s)!", level="success")

        try:
            browser.disconnect()
        except Exception:
            pass

        return data

if __name__ == "__main__":
    res = fetch_notebooklm_prompts()
    print("KẾT QUẢ TRÍCH XUẤT:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
