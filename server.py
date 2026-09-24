import json
import re
import threading
import subprocess
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, HTTPServer
import urllib.parse

import config
import db
import logger
import pipeline_state
from pipeline import execute_daily_pipeline
from setup_profile import open_browser_for_login
from auth_checker import check_login_statuses

PORT = 8080

latest_execution_state = {
    "status": "IDLE",
    "last_run": None,
    "last_result": None
}

cached_auth_status = {
    "google": {"name": "Google Account", "status": "UNKNOWN", "icon": "fa-brands fa-google"},
    "notebooklm": {"name": "NotebookLM", "status": "UNKNOWN", "icon": "fa-solid fa-book-bookmark"},
    "flow": {"name": "Google Flow (Omni 1.1)", "status": "UNKNOWN", "icon": "fa-solid fa-wand-magic"},
    "tiktok": {"name": "TikTok Studio", "status": "UNKNOWN", "icon": "fa-brands fa-tiktok"}
}
is_checking_auth = False

def update_auth_async():
    global is_checking_auth, cached_auth_status
    if is_checking_auth:
        return
    is_checking_auth = True
    try:
        res = check_login_statuses()
        cached_auth_status.update(res)
    finally:
        is_checking_auth = False

class DashboardHandler(SimpleHTTPRequestHandler):
    def serve_video_stream(self, video_file: Path):
        """Phục vụ file video MP4 hỗ trợ đầy đủ HTTP Range (206 Partial Content) cho trình duyệt xem mượt mà"""
        file_size = video_file.stat().st_size
        range_header = self.headers.get("Range")

        if not range_header:
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            with open(video_file, "rb") as f:
                while chunk := f.read(65536):
                    self.wfile.write(chunk)
            return

        try:
            range_match = re.match(r"bytes=(\d+)-(\d*)", range_header.strip())
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            else:
                start = 0
                end = file_size - 1
        except Exception:
            start = 0
            end = file_size - 1

        if start >= file_size or end >= file_size or start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{file_size}")
            self.end_headers()
            return

        content_length = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.send_header("Content-Length", str(content_length))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()

        with open(video_file, "rb") as f:
            f.seek(start)
            bytes_to_send = content_length
            while bytes_to_send > 0:
                chunk = f.read(min(bytes_to_send, 65536))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                    break
                bytes_to_send -= len(chunk)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(config.BASE_DIR / "index.html", "rb") as f:
                self.wfile.write(f.read())
            return

        elif parsed.path == "/api/videos":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            videos = db.load_history()
            self.wfile.write(json.dumps(videos, ensure_ascii=False).encode("utf-8"))
            return

        elif parsed.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(latest_execution_state, ensure_ascii=False).encode("utf-8"))
            return

        elif parsed.path == "/api/logs":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            logs = logger.get_logs()
            self.wfile.write(json.dumps(logs, ensure_ascii=False).encode("utf-8"))
            return

        elif parsed.path == "/api/auth-status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(cached_auth_status, ensure_ascii=False).encode("utf-8"))
            return

        elif parsed.path == "/api/pipeline-data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            data = pipeline_state.get_pipeline_data()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            return

        elif parsed.path.startswith("/downloads/"):
            filename = parsed.path.replace("/downloads/", "")
            clip_file = config.DOWNLOADS_DIR / filename
            if clip_file.exists():
                self.serve_video_stream(clip_file)
                return
            else:
                self.send_error(404, "Clip Not Found")
                return

        elif parsed.path.startswith("/videos/"):
            filename = parsed.path.replace("/videos/", "")
            video_file = config.OUTPUT_DIR / filename
            if not video_file.exists():
                video_file = config.OUTPUT_DIR / "final_tiktok_video.mp4"

            if video_file.exists():
                self.serve_video_stream(video_file)
                return
            else:
                self.send_error(404, "Video Not Found")
                return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/trigger":
            global latest_execution_state
            if latest_execution_state["status"] == "RUNNING":
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"message": "Quy trình đang chạy dở!"}).encode("utf-8"))
                return

            from_step = 1
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                try:
                    body = self.rfile.read(content_length)
                    payload = json.loads(body.decode("utf-8"))
                    from_step = int(payload.get("from_step", 1))
                except Exception:
                    pass
            else:
                query = urllib.parse.parse_qs(parsed.query)
                if "from_step" in query:
                    try: from_step = int(query["from_step"][0])
                    except Exception: pass

            latest_execution_state["status"] = "RUNNING"
            latest_execution_state["step"] = from_step

            def run_job(step):
                global latest_execution_state
                res = execute_daily_pipeline(from_step=step, headless=False)
                latest_execution_state["status"] = "FINISHED"
                latest_execution_state["last_run"] = res.get("start_time")
                latest_execution_state["last_result"] = res
                # Cập nhật lại auth sau khi chạy
                threading.Thread(target=update_auth_async).start()

            t = threading.Thread(target=run_job, args=(from_step,))
            t.start()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "message": f"Đã bắt đầu chạy quy trình từ Bước {from_step}!",
                "from_step": from_step
            }, ensure_ascii=False).encode("utf-8"))
            return

        elif parsed.path == "/api/setup-login":
            open_browser_for_login()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Trình duyệt Chrome đã được mở trên màn hình máy tính của bạn!"}, ensure_ascii=False).encode("utf-8"))
            return

        elif parsed.path == "/api/check-auth":
            t = threading.Thread(target=update_auth_async)
            t.start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Đang kiểm tra phiên đăng nhập..."}, ensure_ascii=False).encode("utf-8"))
            return

        self.send_error(404, "Endpoint Not Found")

def start_server():
    server = HTTPServer(("localhost", PORT), DashboardHandler)
    print("=" * 65)
    print(f"DASHBOARD UI IS RUNNING AT: http://localhost:{PORT}")
    print("=" * 65)
    # Tự động kiểm tra auth lần đầu
    threading.Thread(target=update_auth_async).start()
    server.serve_forever()

if __name__ == "__main__":
    start_server()
