import os
from pathlib import Path
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips
)
import config
from logger import add_log
from tts_engine import create_synchronized_audio_track

def get_vietnamese_font() -> str:
    """Tìm font Windows hỗ trợ 100% tiếng Việt có dấu"""
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf",  # Segoe UI Bold (chuẩn giao diện Windows)
        "C:/Windows/Fonts/arialbd.ttf",   # Arial Bold
        "C:/Windows/Fonts/tahomabd.ttf",  # Tahoma Bold
        "C:/Windows/Fonts/calibrib.ttf",  # Calibri Bold
        "C:/Windows/Fonts/arial.ttf"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "Arial"

def stitch_videos(
    clip_paths: list[str],
    voiceovers: list[str] = None,
    captions: list[str] = None,
    topic: str = None,
    output_filename: str = "final_tiktok_video.mp4",
    render_external_elements: bool = False
) -> str:
    """
    Nối 3 video clip 10s thành 1 video 30s hoàn chỉnh chuẩn TikTok:
    - Video tỷ lệ dọc 9:16 (720x1280)
    - Tích hợp Giọng đọc AI tiếng Việt (Edge-TTS) đồng bộ theo cảnh
    - Tích hợp Chữ chạy / Phụ đề TikTok (Kinetic Subtitles) viền đen chữ vàng nổi bật
    - Tích hợp Tag chủ đề mini cố định ở đầu video
    """
    add_log(f"=== BƯỚC 3/4: DỰNG VIDEO + LỒNG TIẾNG AI + TẠO CHỮ CHẠY TIKTOK ===", level="info")
    add_log(f"-> Đang tải {len(clip_paths)} clips video thành phần...", level="info")

    if not clip_paths:
        raise ValueError("Danh sách video đầu vào trống!")

    output_path = config.OUTPUT_DIR / output_filename
    loaded_clips = []
    text_clips = []
    final_audio_clip = None
    final_composite = None

    try:
        # 1. Nạp các clips video
        for p in clip_paths:
            if not Path(p).exists():
                raise FileNotFoundError(f"Không tìm thấy file clip: {p}")
            clip = VideoFileClip(p)
            loaded_clips.append(clip)

        segment_durations = [c.duration for c in loaded_clips]
        total_duration = sum(segment_durations)
        stitched = concatenate_videoclips(loaded_clips, method="compose")
        w, h = stitched.size
        add_log(f"-> Đã ghép nối xong hình ảnh: kích thước {w}x{h}, tổng độ dài {round(total_duration, 1)}s", level="success")

        # 2. Xử lý âm thanh
        temp_audio_file = config.DOWNLOADS_DIR / "temp_pipeline_voiceover.mp3"
        has_native_audio = stitched.audio is not None

        if has_native_audio and not render_external_elements:
            add_log("-> Giữ nguyên vẹn âm thanh lời thoại sinh trực tiếp từ Google Flow (Omni 1.1)!", level="success")
        elif voiceovers and len(voiceovers) >= 1:
            add_log("-> Đang tạo track thuyết minh AI đồng bộ theo từng phân cảnh (dự phòng)...", level="info")
            audio_track_path = create_synchronized_audio_track(
                voiceovers=voiceovers,
                segment_durations=segment_durations,
                output_audio_path=str(temp_audio_file)
            )
            if audio_track_path and Path(audio_track_path).exists():
                final_audio_clip = AudioFileClip(audio_track_path)
                stitched = stitched.with_audio(final_audio_clip)
                add_log("-> ĐÃ LỒNG TRACK GIỌNG ĐỌC AI VÀO VIDEO THÀNH CÔNG!", level="success")

        # 3. Tạo chữ chạy / phụ đề TikTok (chỉ kích hoạt nếu render_external_elements=True)
        if render_external_elements:
            font_path = get_vietnamese_font()
            add_log(f"-> Đang tạo chữ chạy phụ đề phong cách TikTok (Font: {Path(font_path).stem})...", level="info")

            # 3a. Header badge cố định trên cùng: Chủ đề video
            if topic:
                short_topic = topic.strip().upper()
                if len(short_topic) > 30:
                    short_topic = short_topic[:30] + "..."
                top_badge = TextClip(
                    text=f"• {short_topic} •",
                    font=font_path,
                    font_size=28,
                    color="#00FFFF",
                    stroke_color="black",
                    stroke_width=3
                ).with_position(("center", int(h * 0.07))).with_duration(total_duration)
                text_clips.append(top_badge)

            # 3b. Phụ đề chữ chạy theo từng phân cảnh ở vùng an toàn TikTok (y = 73% chiều cao)
            if captions and len(captions) >= 1:
                current_start = 0.0
                for idx, cap_text in enumerate(captions[:len(loaded_clips)]):
                    dur = loaded_clips[idx].duration
                    clean_cap = cap_text.strip().upper()
                    if clean_cap:
                        caption_clip = TextClip(
                            text=clean_cap,
                            font=font_path,
                            font_size=38,
                            color="#FFE600",
                            stroke_color="black",
                            stroke_width=4,
                            method="caption",
                            size=(w - 90, None)
                        ).with_position(("center", int(h * 0.73))).with_start(current_start + 0.3).with_duration(dur - 0.5)
                        text_clips.append(caption_clip)
                        add_log(f"   [Chữ chạy Cảnh {idx + 1}] \"{clean_cap}\" ({round(current_start, 1)}s -> {round(current_start + dur, 1)}s)", level="info")
                    current_start += dur
        else:
            add_log("-> Phụ đề chữ chạy & Lời thoại đã được sinh trực tiếp trên khung hình bởi Google Flow!", level="info")

        # 4. Tổng hợp video hoàn chỉnh
        if text_clips:
            final_composite = CompositeVideoClip([stitched] + text_clips, size=(w, h))
        else:
            final_composite = stitched

        add_log("-> Đang xuất file video hoàn chỉnh (H.264 / AAC 30 FPS + FastStart cho web)...", level="info")
        final_composite.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            fps=30,
            preset="fast",
            ffmpeg_params=["-movflags", "+faststart"],
            logger=None
        )

        size_mb = round(output_path.stat().st_size / (1024 * 1024), 2)
        add_log(f"-> ĐÃ XUẤT VIDEO TIKTOK HOÀN CHỈNH THÀNH CÔNG! ({size_mb} MB tại {output_path.name})", level="success")
        return str(output_path)

    finally:
        # Dọn dẹp tài nguyên MoviePy an toàn
        for c in loaded_clips:
            try:
                c.close()
            except Exception:
                pass
        for tc in text_clips:
            try:
                tc.close()
            except Exception:
                pass
        if final_audio_clip:
            try:
                final_audio_clip.close()
            except Exception:
                pass
        if final_composite:
            try:
                final_composite.close()
            except Exception:
                pass

if __name__ == "__main__":
    clips = [
        str(config.DOWNLOADS_DIR / "clip_1.mp4"),
        str(config.DOWNLOADS_DIR / "clip_2.mp4"),
        str(config.DOWNLOADS_DIR / "clip_3.mp4")
    ]
    sample_vo = [
        "Tại sao tiền thưởng Tết ta tiêu rất nhanh, còn tiền lương lại chắt chiu từng đồng?",
        "Đó chính là kế toán tâm lý! Não bộ tự chia tiền vào các ngăn vô hình và đối xử khác nhau.",
        "Mọi đồng tiền đều có giá trị như nhau. Đừng để cảm xúc đánh lừa chiếc ví của bạn!"
    ]
    sample_caps = [
        "BẪY KẾ TOÁN TÂM LÝ!",
        "TIỀN NÀO CŨNG LÀ TIỀN CỦA BẠN!",
        "TẬP TRUNG VÀO GIÁ TRỊ THỰC!"
    ]
    existing = [c for c in clips if Path(c).exists()]
    if existing:
        stitch_videos(existing, voiceovers=sample_vo, captions=sample_caps, topic="Kế toán tâm lý")
    else:
        print("Chưa có file clip mẫu trong ./downloads để test nối video.")
