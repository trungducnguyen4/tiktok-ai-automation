# 🚀 TikTok AI Automation Studio

> **Hệ thống tự động hóa khép kín: Trích xuất tri thức từ NotebookLM ➔ Tạo đồ họa 2D trên Google Flow (Omni 1.1) ➔ Thuyết minh AI & Phụ đề TikTok ➔ Tự động đăng tải lên TikTok Studio.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Automated_CDP-green.svg)](https://playwright.dev/)
[![MoviePy](https://img.shields.io/badge/MoviePy-2.x-orange.svg)](https://zulko.github.io/moviepy/)
[![Edge-TTS](https://img.shields.io/badge/Edge--TTS-HoaiMyNeural-purple.svg)](https://github.com/rany2/edge-tts)

---

## 🌟 Tính Năng Nổi Bật

1. **🧠 Tự động hóa sáng tạo nội dung với NotebookLM:**
   * Tự động truy cập notebook chuyên ngành (Tâm lý học hành vi, Tài chính cá nhân...).
   * Chọn chủ đề ngẫu nhiên, sinh kịch bản gồm **3 phân cảnh (10s/cảnh = video 30s)**.
   * Tạo song song: Prompt tạo video 2D (tiếng Anh) + Lời bình thuyết minh (tiếng Việt) + Tiêu đề phụ đề giật tít + Hashtags thịnh hành.

2. **🎨 Tạo video hoạt hình 2D qua Google Flow (Omni 1.1 Flash):**
   * Tự động thiết lập thông số chuẩn: Tỷ lệ dọc **9:16**, Độ phân giải **720p**, Thời lượng **10s**, Chế độ **Ingredients**.
   * **Cơ chế Reference Chaining (`+ Add reference`):** Tự động đưa clip trước vào làm reference cho clip sau để đảm bảo phong cách hình ảnh và nhân vật nhất quán xuyên suốt.
   * **Nhận diện thương hiệu (`brainmoney.jpg`):** Tự động gắn asset thương hiệu vào Clip 3 (cảnh kết thúc) và hiển thị logo chuyển động phát sáng mượt mà.
   * **Quy tắc định danh khi thư viện lớn:** Bot bắt chính xác 100% video vừa sinh ra qua Network Stream Response mới nhất và Tile State đầu Canvas, không bao giờ nhầm lẫn với các clip cũ.

3. **🎙️ Nhúng Lời Thoại & Chữ Chạy Trực Tiếp Vào Prompt:**
   * **Prompt tích hợp 3-trong-1:** Mỗi prompt gửi cho Google Flow chứa đầy đủ: mô tả visual 2D tối giản + lời thuyết minh tiếng Việt (`Spoken Vietnamese voiceover audio: "..."`) + chỉ dẫn phụ đề TikTok (`On-screen kinetic TikTok subtitles in bold yellow font with black outline: "..."`). AI của Google tự tổng hợp giọng nói và chữ trực tiếp trong video.
   * **Web FastStart & Tương thích phát tức thì:** Tự động đưa `moov` atom lên đầu file MP4 giúp video phát mượt mà trên Dashboard và TikTok.

4. **📱 Tự động xuất bản lên TikTok Studio:**
   * Tải video 30s hoàn chỉnh lên TikTok Creator Center.
   * Tự động điền tiêu đề giật tít và các hashtag thịnh hành liên quan.

5. **📊 Web Dashboard & Data Inspector trực quan (`localhost:8080`):**
   * **Sơ đồ quy trình động (Flowchart):** Bấm xem chi tiết dữ liệu đầu ra của từng node (Prompt, Voiceover, Chữ chạy, Clips).
   * **Trình phát video HTML5 tích hợp:** Hỗ trợ đầy đủ chuẩn HTTP Range (206 Partial Content).
   * **Kiểm tra trạng thái đăng nhập:** Realtime badge cho Google, NotebookLM, Google Flow, TikTok Studio.

6. **🤖 Tích hợp MCP Server:**
   * Tương thích với Antigravity, Claude Desktop, Cursor để điều khiển quy trình bằng câu lệnh chat tự nhiên.

---

## 📁 Cấu Trúc Dự Án

```
├── auth_checker.py       # Kiểm tra trạng thái đăng nhập các nền tảng
├── config.py             # Cấu hình đường dẫn, URL NotebookLM, Google Flow, TikTok
├── db.py                 # Lưu trữ và tải lịch sử xuất bản video
├── index.html            # Giao diện Web Dashboard & Sơ đồ Data Inspector
├── logger.py             # Hệ thống ghi log realtime
├── mcp_server.py         # MCP Server chuẩn giao thức Model Context Protocol
├── notebooklm_bot.py     # Bot tương tác NotebookLM trích xuất kịch bản 3 phân cảnh
├── pipeline.py           # Điều phối toàn bộ quy trình 4 bước từ A-Z
├── pipeline_state.py     # Quản lý trạng thái realtime phục vụ Dashboard
├── requirements.txt      # Danh sách thư viện Python cần thiết
├── scheduler.py          # Dịch vụ hẹn giờ chạy ngầm định kỳ hàng ngày (12:00 trưa)
├── server.py             # Máy chủ web cục bộ phục vụ Dashboard & HTTP 206 Streaming
├── setup_profile.py      # Mở trình duyệt để đăng nhập tài khoản lần đầu
├── tiktok_publisher.py   # Bot tự động tải và xuất bản video lên TikTok Studio
├── tts_engine.py         # Module sinh giọng đọc AI tiếng Việt đồng bộ cảnh
├── video_editor.py       # Nối video, lồng tiếng AI, tạo chữ chạy và gắn cờ FastStart
└── video_generator.py    # Bot tương tác Google Flow, cấu hình setting và render clips
```

---

## 🚀 Hướng Dẫn Cài Đặt & Sử Dụng

### 1. Cài đặt môi trường

Yêu cầu máy tính đã cài đặt Python 3.10+:

```bash
# Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt

# Cài đặt trình điều khiển Playwright
playwright install
```

### 2. Đăng nhập tài khoản (Chỉ cần làm 1 lần duy nhất)

Khởi chạy script mở cửa sổ Chrome với thư mục profile riêng biệt:

```bash
python setup_profile.py
```

* Trình duyệt sẽ mở sẵn các tab: Google Account, NotebookLM, Google Flow, TikTok Studio.
* Bạn đăng nhập vào tài khoản của mình trên các tab này.
* Sau khi đăng nhập xong, bạn có thể đóng trình duyệt. Session sẽ được lưu lại trong `./browser_profile` (file này đã được bảo vệ trong `.gitignore` không bao giờ đẩy lên Git).

### 3. Khởi chạy Web Dashboard

Khởi chạy máy chủ giao diện quản lý:

```bash
python server.py
```

Truy cập trình duyệt: **`http://localhost:8080`**

Tại đây bạn có thể:
* Xem trạng thái đăng nhập các tài khoản.
* Bấm **"Chạy Quy Trình Ngay"** để kích hoạt toàn bộ quy trình tự động.
* Xem trực tiếp sơ đồ Flowchart và Data Output của từng bước.
* Xem lại các video đã render ngay trên trình phát video tích hợp.

### 4. Thiết lập chạy tự động hàng ngày (12:00 Trưa)

Khởi động background scheduler:

```bash
python scheduler.py
```

### 5. Tích hợp MCP Server vào AI Assistant (Antigravity / Claude / Cursor)

Thêm cấu hình vào file cài đặt MCP của bạn:

```json
{
  "mcpServers": {
    "tiktok-ai-studio": {
      "command": "python",
      "args": [
        "c:\\Users\\Trung Duc\\Documents\\antigravity\\wise-tesla\\mcp_server.py"
      ]
    }
  }
}
```

---

## 🔒 Bảo Mật & Lưu Ý

* Thư mục `browser_profile/` chứa cookie phiên đăng nhập và dữ liệu duyệt web cá nhân của bạn, đã được khai báo trong `.gitignore` để bảo đảm **an toàn 100% không bị lộ ra ngoài**.
* Các thư mục `output/` và `downloads/` chỉ lưu video tạm thời và không được commit lên kho mã nguồn.

---

## 📄 Bản Quyền

Phát triển bởi **Nguyễn Trung Đức** (@trungducnguyen4).
Giấy phép: [MIT](LICENSE)
