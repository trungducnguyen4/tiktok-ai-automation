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
from tts_engine import create_synchronized_audio_track, generate_tts_audio_clip

def get_vietnamese_font() -> str:
    """Tìm font Windows hỗ trợ 100% tiếng Việt có dấu, sắc nét, không lỗi font"""
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf",   # Arial Bold (chuẩn quốc tế, hỗ trợ 100% Unicode tiếng Việt)
        "C:/Windows/Fonts/segoeuib.ttf",  # Segoe UI Bold (chuẩn giao diện Windows hiện đại)
        "C:/Windows/Fonts/tahomabd.ttf",  # Tahoma Bold
        "C:/Windows/Fonts/calibrib.ttf",  # Calibri Bold
        "C:/Windows/Fonts/arial.ttf"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "Arial"

def synchronize_single_clip(
    clip_path: str,
    voiceover_text: str = None,
    caption_text: str = None,
    output_path: str = None,
    voice: str = None,
    use_native_audio: bool = True
) -> str:
    """
    Đồng bộ 1 clip video lẻ:
    1. Giữ nguyên 100% âm thanh gốc trực tiếp từ Gemini (Google Flow) nếu use_native_audio=True.
    2. Chữ phụ đề TikTok tiếng Việt sắc nét (vàng viền đen, chuẩn 100% không lỗi dấu/font).
    """
    if output_path is None:
        output_path = clip_path
    
    out_p = Path(output_path)
    temp_output = out_p.parent / f"temp_sync_{out_p.name}"
    font_path = get_vietnamese_font()
    
    clip = VideoFileClip(clip_path)
    w, h = clip.size
    dur = clip.duration
    
    # 1. Âm thanh: giữ nguyên âm thanh gốc Gemini hoặc tạo TTS nếu yêu cầu
    temp_audio = None
    audio_clip = None
    if not use_native_audio and voiceover_text and voiceover_text.strip():
        temp_audio = out_p.parent / f"temp_vo_{out_p.stem}.mp3"
        if generate_tts_audio_clip(voiceover_text, str(temp_audio), voice=voice):
            audio_clip = AudioFileClip(str(temp_audio)).with_start(0.3)
            if audio_clip.duration > dur - 0.5:
                audio_clip = audio_clip.subclipped(0, dur - 0.5)
    elif use_native_audio and clip.audio is not None:
        audio_clip = clip.audio
    
    # 2. Tạo phụ đề chữ chạy TikTok sắc nét không lỗi dấu
    text_clips = []
    if caption_text and caption_text.strip():
        clean_cap = caption_text.strip().upper()
        tc = TextClip(
            text=clean_cap,
            font=font_path,
            font_size=36,
            color="#FFE600",
            stroke_color="black",
            stroke_width=4,
            method="caption",
            size=(w - 140, None)
        ).with_position(("center", int(h * 0.70))).with_start(0.2).with_duration(dur - 0.4)
        text_clips.append(tc)
    
    # 3. Ghép video với text và audio đồng bộ
    comp = CompositeVideoClip([clip] + text_clips, size=(w, h)) if text_clips else clip
    if audio_clip:
        comp = comp.with_audio(audio_clip)
        
    comp.write_videofile(
        str(temp_output),
        codec="libx264",
        audio_codec="aac",
        fps=30,
        preset="ultrafast",
        ffmpeg_params=["-movflags", "+faststart"],
        logger=None
    )
    
    clip.close()
    if audio_clip and not use_native_audio: audio_clip.close()
    for tc in text_clips: tc.close()
    comp.close()
    
    if temp_audio and temp_audio.exists():
        try: temp_audio.unlink()
        except Exception: pass
        
    # Thay thế file gốc bằng file đã đồng bộ hoàn hảo
    if temp_output.exists():
        if out_p.exists():
            try: out_p.unlink()
            except Exception: pass
        temp_output.replace(out_p)
        
    return str(out_p)

def stitch_videos(
    clip_paths: list[str],
    voiceovers: list[str] = None,
    captions: list[str] = None,
    topic: str = None,
    output_filename: str = "final_tiktok_video.mp4",
    render_external_elements: bool = True,
    use_native_audio: bool = True
) -> str:
    """
    Nối 3 video clip 10s thành 1 video 30s hoàn chỉnh chuẩn TikTok:
    - Video tỷ lệ dọc 9:16 (720x1280)
    - Giữ nguyên 100% ÂM THANH GỐC TRỰC TIẾP TỪ GEMINI (Google Flow)
    - Tích hợp Chữ chạy / Phụ đề TikTok (Kinetic Subtitles) viền đen chữ vàng nổi bật, 100% chuẩn tiếng Việt có dấu
    - Tích hợp Tag chủ đề mini cố định ở đầu video
    """
    add_log(f"=== BƯỚC 3/4: DỰNG VIDEO + GIỮ ÂM THANH GỐC GEMINI + TẠO PHỤ ĐỀ TIKTOK ===", level="info")
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
        if not use_native_audio and voiceovers and len(voiceovers) >= 1:
            voice_id = getattr(config, "DEFAULT_VOICE", "vi-VN-NamMinhNeural")
            add_log(f"-> Đang lồng tiếng AI bên ngoài ({voice_id})...", level="info")
            audio_track_path = create_synchronized_audio_track(
                voiceovers=voiceovers,
                segment_durations=segment_durations,
                output_audio_path=str(temp_audio_file),
                voice=voice_id
            )
            if audio_track_path and Path(audio_track_path).exists():
                final_audio_clip = AudioFileClip(audio_track_path)
                stitched = stitched.with_audio(final_audio_clip)
                add_log("-> Đã lồng tiếng AI bên ngoài thành công!", level="success")
        elif stitched.audio is not None:
            add_log("-> GIỮ NGUYÊN VẸN 100% ÂM THANH GỐC TRỰC TIẾP TỪ GEMINI (GOOGLE FLOW)!", level="success")
        else:
            add_log("Lưu ý: Video không chứa track âm thanh gốc.", level="warning")

        # 3. Tạo chữ chạy / phụ đề TikTok sắc nét không lỗi dấu
        if render_external_elements:
            font_path = get_vietnamese_font()
            add_log(f"-> Đang tạo phụ đề phong cách TikTok (Font: {Path(font_path).stem}, chữ vàng viền đen chuẩn tiếng Việt)...", level="info")

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

            # 3b. Phụ đề chữ chạy theo từng phân cảnh ở vùng an toàn TikTok (y = 70% chiều cao)
            if captions and len(captions) >= 1:
                current_start = 0.0
                for idx, cap_text in enumerate(captions[:len(loaded_clips)]):
                    dur = loaded_clips[idx].duration
                    clean_cap = cap_text.strip().upper()
                    if clean_cap:
                        caption_clip = TextClip(
                            text=clean_cap,
                            font=font_path,
                            font_size=36,
                            color="#FFE600",
                            stroke_color="black",
                            stroke_width=4,
                            method="caption",
                            size=(w - 140, None)
                        ).with_position(("center", int(h * 0.70))).with_start(current_start + 0.2).with_duration(dur - 0.4)
                        text_clips.append(caption_clip)
                        add_log(f"   [Phụ đề Cảnh {idx + 1}] \"{clean_cap}\" ({round(current_start, 1)}s -> {round(current_start + dur, 1)}s)", level="info")
                    current_start += dur

        # 4. Tổng hợp video hoàn chỉnh và bảo tồn âm thanh gốc
        final_composite = CompositeVideoClip([stitched] + text_clips, size=(w, h)) if text_clips else stitched
        if stitched.audio is not None:
            final_composite = final_composite.with_audio(stitched.audio)

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
            try: c.close()
            except Exception: pass
        for tc in text_clips:
            try: tc.close()
            except Exception: pass
        if final_audio_clip:
            try: final_audio_clip.close()
            except Exception: pass
        if final_composite:
            try: final_composite.close()
            except Exception: pass

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
