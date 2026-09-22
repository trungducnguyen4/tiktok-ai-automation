import json
import threading
from mcp.server.mcpserver import MCPServer
from pipeline import execute_daily_pipeline
import config

# Khởi tạo MCPServer (MCP SDK v2)
mcp = MCPServer("Auto-Video-Workflow-MCP")

# Biến lưu trữ trạng thái chạy gần nhất
latest_run_state = {
    "status": "IDLE",
    "last_run": None,
    "last_result": None
}

@mcp.tool()
def trigger_daily_workflow(headless: bool = True) -> str:
    """
    Kích hoạt ngay lập tức toàn bộ quy trình:
    NotebookLM -> Gen 3 Clip 10s -> Ghép nối video -> Đăng lên TikTok Studio.
    """
    global latest_run_state
    if latest_run_state["status"] == "RUNNING":
        return "Quy trình đang chạy dở! Vui lòng đợi quy trình trước hoàn thành."

    def run_worker():
        global latest_run_state
        latest_run_state["status"] = "RUNNING"
        res = execute_daily_pipeline(headless=headless)
        latest_run_state["status"] = "FINISHED"
        latest_run_state["last_run"] = res.get("start_time")
        latest_run_state["last_result"] = res

    # Chạy trong luồng riêng để phản hồi MCP không bị block timeout
    worker_thread = threading.Thread(target=run_worker)
    worker_thread.start()

    return "Đã kích hoạt thành công quy trình tự động hóa video! Bạn có thể gọi tool 'get_workflow_status' để theo dõi tiến trình."

@mcp.tool()
def get_workflow_status() -> str:
    """
    Lấy trạng thái thực thi hiện tại và kết quả của lần chạy gần nhất.
    """
    global latest_run_state
    return json.dumps(latest_run_state, indent=2, ensure_ascii=False)

@mcp.tool()
def get_config_info() -> str:
    """
    Xem cấu hình hiện tại: link NotebookLM, thời gian hẹn giờ (12h trưa), đường dẫn lưu video.
    """
    info = {
        "notebooklm_url": config.NOTEBOOKLM_URL,
        "schedule_time": f"{config.SCHEDULE_HOUR:02d}:{config.SCHEDULE_MINUTE:02d}",
        "downloads_dir": str(config.DOWNLOADS_DIR),
        "output_dir": str(config.OUTPUT_DIR),
        "profile_dir": config.BROWSER_PROFILE_DIR
    }
    return json.dumps(info, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    print("Khởi động Auto-Video MCP Server qua stdio...")
    mcp.run(transport="stdio")
