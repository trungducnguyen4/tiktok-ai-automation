import datetime
import traceback
import config
import db
from logger import add_log, clear_logs
from notebooklm_bot import fetch_notebooklm_prompts
from video_generator import generate_video_clips
from video_editor import stitch_videos, synchronize_single_clip
import pipeline_state

def execute_daily_pipeline(from_step: int = 1, headless: bool = False) -> dict:
    start_time = datetime.datetime.now()
    clear_logs()
    
    # Quản lý trạng thái theo bước khởi chạy
    if from_step <= 1:
        pipeline_state.reset_pipeline_data()
        add_log("=== KHỞI ĐỘNG TOÀN BỘ QUY TRÌNH (TỪ BƯỚC 1: NOTEBOOKLM AI) ===", level="info")
    elif from_step == 2:
        add_log("=== TIẾP TỤC QUY TRÌNH TỪ BƯỚC 2: RENDER GOOGLE FLOW ===", level="info")
    elif from_step == 3:
        add_log("=== CHẠY RIÊNG BƯỚC 3: DỰNG VIDEO 30S & PHỤ ĐỀ TIKTOK ===", level="info")

    current_data = pipeline_state.get_pipeline_data()
    status_report = {
        "start_time": str(start_time),
        "status": "RUNNING",
        "topic": None,
        "title": None,
        "video_path": None,
        "error": None
    }

    try:
        # BƯỚC 1: NotebookLM Script Data
        if from_step <= 1:
            add_log("[Bước 1/3] Đang mở NotebookLM để lấy chủ đề ngẫu nhiên và kịch bản 3 prompt...", level="info")
            pipeline_state.update_step_data("step1", {"status": "RUNNING"})
            script_data = fetch_notebooklm_prompts(headless=headless)
            
            topic = script_data.get("topic", "Chủ đề ngẫu nhiên")
            title = script_data.get("title", "Video ngắn AI")
            hashtags = script_data.get("hashtags", ["#ai", "#trending"])
            prompts = script_data.get("prompts", [])
            voiceovers = script_data.get("voiceovers", [])
            captions = script_data.get("captions", [])

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
        else:
            s1 = current_data.get("step1", {})
            topic = s1.get("topic") or "Sự tự tin thái quá của CEO"
            title = s1.get("title") or "Vì sao các Sếp lớn hay đưa ra quyết định sai lầm hàng triệu đô?"
            hashtags = s1.get("hashtags") or ["#TamLyHocHanhVi", "#KinhTeHoc", "#DauTu"]
            prompts = s1.get("prompts") or []
            voiceovers = s1.get("voiceovers") or []
            captions = s1.get("captions") or []
            if from_step == 2 and not prompts:
                raise RuntimeError("Chưa có kịch bản từ Bước 1! Vui lòng bấm chạy từ Bước 1 trước.")
            add_log(f"-> Dùng kịch bản có sẵn từ Bước 1: '{topic}' ({len(prompts)} prompts)", level="info")

        status_report["topic"] = topic
        status_report["title"] = title

        if from_step <= 1 and len(prompts) < 3:
            add_log(f"Cảnh báo: Chỉ nhận được {len(prompts)} prompt thay vì 3 prompt.", level="warning")

        # BƯỚC 2: Sinh 3 clip video qua Google Flow
        if from_step <= 2:
            add_log("[Bước 2/3] Đang chuyển 3 prompt sang Google Flow (Omni 1.1) để render clip...", level="info")
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
        else:
            # from_step == 3: Tận dụng các clip đã có trong downloads
            from pathlib import Path
            potential_clips = [str(config.DOWNLOADS_DIR / f"clip_{i}.mp4") for i in [1, 2, 3]]
            existing_clips = [p for p in potential_clips if Path(p).exists()]
            if len(existing_clips) < 2:
                raise RuntimeError("Không tìm thấy đủ video clip trong thư mục downloads/! Vui lòng chạy lại từ Bước 2.")
            clip_paths = existing_clips
            add_log(f"-> Sử dụng {len(clip_paths)} clips video có sẵn trong downloads/ để dựng video 30s...", level="info")

        # BƯỚC 3: Nối clip + giữ âm thanh gốc Gemini + tạo phụ đề chuẩn TikTok
        add_log("[Bước 3/3] Đang dùng MoviePy nối các clip, giữ âm thanh gốc Gemini và tạo phụ đề TikTok...", level="info")
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

        # Hoàn tất quy trình 3 bước: In rõ Tiêu đề, Hashtags và Caption để người dùng tự đăng TikTok
        tag_str = ' '.join(hashtags)
        status_report["status"] = "SUCCESS"
        add_log("=== QUY TRÌNH 3 BƯỚC HOÀN TẤT THÀNH CÔNG 100%! ===", level="success")
        add_log(f"-> [1] TIÊU ĐỀ TIKTOK: {title}", level="success")
        add_log(f"-> [2] BỘ HASHTAGS: {tag_str}", level="success")
        add_log(f"-> [3] NỘI DUNG CAPTION HOÀN CHỈNH:\n{title}\n\n{tag_str}", level="info")
        add_log(f"-> [4] FILE VIDEO 30S: {final_video_path}", level="success")
        add_log("-> SẴN SÀNG ĐĂNG: Bạn có thể tải video từ Dashboard và copy Tiêu đề + Hashtags để đăng thủ công lên TikTok!", level="success")

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
