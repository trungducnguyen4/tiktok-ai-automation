import datetime
import traceback
import config
import db
from logger import add_log, clear_logs
from notebooklm_bot import fetch_notebooklm_prompts
from video_generator import generate_video_clips
from video_editor import stitch_videos, synchronize_single_clip
from tiktok_publisher import publish_to_tiktok
import pipeline_state

def execute_daily_pipeline(headless: bool = False) -> dict:
    start_time = datetime.datetime.now()
    clear_logs()
    pipeline_state.reset_pipeline_data()
    add_log("=== KHỞI ĐỘNG QUY TRÌNH TỰ ĐỘNG TẠO VIDEO & ĐĂNG TIKTOK ===", level="info")

    status_report = {
        "start_time": str(start_time),
        "status": "RUNNING",
        "topic": None,
        "title": None,
        "video_path": None,
        "error": None
    }

    try:
        # Bước 1: Mở NotebookLM
        add_log("[Bước 1/4] Đang mở NotebookLM để lấy chủ đề ngẫu nhiên và kịch bản 3 prompt...", level="info")
        pipeline_state.update_step_data("step1", {"status": "RUNNING"})
        script_data = fetch_notebooklm_prompts(headless=headless)
        
        topic = script_data.get("topic", "Chủ đề ngẫu nhiên")
        title = script_data.get("title", "Video ngắn AI")
        hashtags = script_data.get("hashtags", ["#ai", "#trending"])
        prompts = script_data.get("prompts", [])
        voiceovers = script_data.get("voiceovers", [])
        captions = script_data.get("captions", [])

        status_report["topic"] = topic
        status_report["title"] = title

        pipeline_state.update_step_data("step1", {
            "status": "COMPLETED",
            "topic": topic,
            "title": title,
            "hashtags": hashtags,
            "prompts": prompts,
            "voiceovers": voiceovers,
            "captions": captions,
            "raw_json": script_data
        })

        add_log(f"-> Chủ đề được chọn: '{topic}'", level="success")
        add_log(f"-> Tiêu đề TikTok: '{title}'", level="success")
        add_log(f"-> Hashtags: {' '.join(hashtags)}", level="success")
        add_log(f"-> Đã trích xuất thành công {len(prompts)} prompts video (10s)!", level="success")
        add_log(f"-> Đã chuẩn bị {len(voiceovers)} đoạn thuyết minh giọng đọc AI!", level="success")
        add_log(f"-> Đã chuẩn bị {len(captions)} dòng chữ chạy phụ đề TikTok!", level="success")

        if len(prompts) < 3:
            add_log(f"Cảnh báo: Chỉ nhận được {len(prompts)} prompt thay vì 3 prompt.", level="warning")

        # Bước 2: Sinh 3 clip video qua Google Flow
        add_log("[Bước 2/4] Đang chuyển 3 prompt sang Google Flow (Omni 1.1) để render clip...", level="info")
        pipeline_state.update_step_data("step2", {"status": "RUNNING"})
        clip_paths = generate_video_clips(prompts[:3], headless=headless)
        
        if len(clip_paths) == 0:
            pipeline_state.update_step_data("step2", {"status": "ERROR"})
            raise RuntimeError("Không thể tải về bất kỳ clip video nào từ Google Flow.")

        # Giữ nguyên 100% âm thanh gốc trực tiếp từ Gemini (Google Flow), không ghi đè TTS
        add_log("-> Giữ nguyên vẹn 100% âm thanh gốc trực tiếp từ Gemini (Google Flow) cho 3 clip 10s!", level="success")

        pipeline_state.update_step_data("step2", {
            "status": "COMPLETED",
            "clips": [
                {
                    "name": f"Clip {i+1} (10s)",
                    "file": f"clip_{i+1}.mp4",
                    "url": f"/downloads/clip_{i+1}.mp4?t={int(datetime.datetime.now().timestamp())}",
                    "prompt": prompts[i] if i < len(prompts) else ""
                } for i in range(len(clip_paths))
            ],
            "total": len(clip_paths)
        })
        add_log(f"-> Đã tạo thành công {len(clip_paths)}/3 clip video 10s (kèm âm thanh gốc Gemini)!", level="success")

        # Bước 3: Nối clip + giữ âm thanh gốc Gemini + tạo phụ đề chuẩn TikTok
        add_log("[Bước 3/4] Đang dùng MoviePy nối các clip, giữ âm thanh gốc Gemini và tạo phụ đề TikTok...", level="info")
        pipeline_state.update_step_data("step3", {"status": "RUNNING"})
        final_video_path = stitch_videos(
            clip_paths=clip_paths,
            voiceovers=None,
            captions=captions,
            topic=topic,
            use_native_audio=True
        )
        status_report["video_path"] = final_video_path
        
        import os
        sz_mb = round(os.path.getsize(final_video_path) / (1024 * 1024), 2)
        pipeline_state.update_step_data("step3", {
            "status": "COMPLETED",
            "video_url": f"/videos/final_tiktok_video.mp4?t={int(datetime.datetime.now().timestamp())}",
            "duration": "30s",
            "resolution": "720x1280 (9:16)",
            "file_size": f"{sz_mb} MB",
            "has_audio": True,
            "has_subtitles": True,
            "voice_name": "Gemini Native (Google Flow)"
        })
        add_log(f"-> Video 30s hoàn chỉnh (âm thanh gốc Gemini + phụ đề TikTok) đã được xuất tại: {final_video_path}", level="success")

        # Bước 4: Đăng lên TikTok Studio
        add_log("[Bước 4/4] Đang mở TikTok Studio để tải video và xuất bản...", level="info")
        pipeline_state.update_step_data("step4", {
            "status": "RUNNING",
            "tiktok_title": title
        })
        publish_success = publish_to_tiktok(
            video_path=final_video_path,
            title=title,
            hashtags=hashtags,
            headless=headless
        )

        pipeline_state.update_step_data("step4", {
            "status": "COMPLETED" if publish_success else "ERROR",
            "tiktok_title": title,
            "publish_status": "Đã xuất bản thành công lên TikTok Studio" if publish_success else "Chưa hoàn tất xuất bản"
        })

        if publish_success:
            status_report["status"] = "SUCCESS"
            add_log("-> XUẤT BẢN THÀNH CÔNG! Video đã được đăng trực tiếp lên TikTok Studio!", level="success")
            add_log("=== QUY TRÌNH ĐÃ HOÀN TẤT TRỌN VẸN 100% ===", level="success")
        else:
            status_report["status"] = "UPLOAD_FAILED"
            add_log("-> Không thể hoàn tất nút Publish trên TikTok Studio (vui lòng kiểm tra đăng nhập hoặc duyệt nháp).", level="error")

        # Lưu file video phiên bản riêng và tạo thumbnail riêng biệt cho lịch sử
        import shutil
        run_id = start_time.strftime("%Y%m%d_%H%M%S")
        versioned_filename = f"video_{run_id}.mp4"
        versioned_path = config.OUTPUT_DIR / versioned_filename
        try:
            shutil.copy2(final_video_path, versioned_path)
        except Exception:
            versioned_filename = "final_tiktok_video.mp4"
            versioned_path = Path(final_video_path)

        thumb_filename = f"thumb_{run_id}.jpg"
        thumb_path = config.OUTPUT_DIR / thumb_filename
        try:
            from moviepy import VideoFileClip
            v_clip = VideoFileClip(str(final_video_path))
            v_clip.save_frame(str(thumb_path), t=min(1.0, max(0.1, v_clip.duration / 2)))
            v_clip.close()
        except Exception as e:
            add_log(f"Lưu ý tạo thumbnail: {e}", level="warning")

        # Lưu lịch sử
        db.save_history_item({
            "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "date": start_time.strftime("%Y-%m-%d"),
            "topic": topic,
            "title": title,
            "hashtags": hashtags,
            "prompts": prompts,
            "video_path": str(versioned_path),
            "video_filename": versioned_filename,
            "thumbnail": f"/videos/{thumb_filename}" if thumb_path.exists() else None,
            "status": status_report["status"]
        })

        return status_report

    except Exception as e:
        err_msg = traceback.format_exc()
        add_log(f"LỖI: {str(e)}", level="error")
        add_log(f"Chi tiết lỗi kỹ thuật: {err_msg.splitlines()[-1]}", level="error")
        status_report["status"] = "ERROR"
        status_report["error"] = str(e)
        return status_report

if __name__ == "__main__":
    execute_daily_pipeline(headless=False)
