import os
import subprocess
import tempfile
from pathlib import Path
from moviepy import AudioFileClip, CompositeAudioClip
from logger import add_log

DEFAULT_VOICE = "vi-VN-HoaiMyNeural" # Giọng nữ miền Bắc/chuẩn truyền cảm, mượt mà phong cách TikTok
MALE_VOICE = "vi-VN-NamMinhNeural"   # Giọng nam trầm ấm

def generate_tts_audio_clip(text: str, output_file: str, voice: str = DEFAULT_VOICE) -> bool:
    """
    Sinh file âm thanh từ văn bản tiếng Việt bằng Edge-TTS (fallback gTTS).
    """
    clean_text = text.strip()
    if not clean_text:
        return False

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Thử sinh qua edge-tts CLI
    try:
        cmd = [
            "edge-tts",
            "--voice", voice,
            "--text", clean_text,
            "--write-media", str(out_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        if res.returncode == 0 and out_path.exists() and out_path.stat().st_size > 1000:
            return True
    except Exception as e:
        add_log(f"Lỗi khi chạy edge-tts: {e}", level="warning")

    # 2. Fallback qua gTTS nếu edge-tts lỗi
    try:
        from gtts import gTTS
        tts = gTTS(text=clean_text, lang='vi', slow=False)
        tts.save(str(out_path))
        if out_path.exists() and out_path.stat().st_size > 1000:
            add_log("-> Đã sử dụng gTTS fallback tạo giọng đọc thành công.", level="info")
            return True
    except Exception as e:
        add_log(f"Lỗi fallback gTTS: {e}", level="error")

    return False

def create_synchronized_audio_track(
    voiceovers: list[str],
    segment_durations: list[float] = [10.0, 10.0, 10.0],
    output_audio_path: str = "full_voiceover.mp3",
    voice: str = DEFAULT_VOICE
) -> str | None:
    """
    Tạo 1 track âm thanh 30s với 3 đoạn thuyết minh khớp chính xác vào từng clip 10s:
    - Lời bình 1 bắt đầu ở giây 0.5 (Clip 1)
    - Lời bình 2 bắt đầu ở giây 10.5 (Clip 2)
    - Lời bình 3 bắt đầu ở giây 20.5 (Clip 3)
    """
    add_log(f"-> Đang tổng hợp giọng đọc AI cho {len(voiceovers)} phân cảnh...", level="info")
    out_path = Path(output_audio_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    temp_audio_files = []
    loaded_clips = []

    try:
        current_start = 0.5
        for i, text in enumerate(voiceovers[:len(segment_durations)]):
            seg_file = out_path.parent / f"temp_voice_{i+1}.mp3"
            success = generate_tts_audio_clip(text, str(seg_file), voice=voice)
            if success and seg_file.exists():
                temp_audio_files.append(seg_file)
                ac = AudioFileClip(str(seg_file))
                # Giới hạn độ dài audio không vượt quá độ dài clip
                clip_max_duration = segment_durations[i] - 0.8
                if ac.duration > clip_max_duration:
                    ac = ac.subclipped(0, clip_max_duration)
                
                # Đặt mốc thời gian phát cho từng đoạn
                ac = ac.with_start(current_start)
                loaded_clips.append(ac)
                add_log(f"   [Đoạn {i+1}] Giọng đọc ({round(ac.duration, 1)}s) bắt đầu tại {round(current_start, 1)}s: \"{text[:45]}...\"", level="info")
            
            current_start += segment_durations[i]

        if not loaded_clips:
            add_log("Không tạo được đoạn âm thanh giọng đọc nào!", level="error")
            return None

        # Tổng hợp thành track âm thanh duy nhất
        total_duration = sum(segment_durations)
        composite = CompositeAudioClip(loaded_clips)
        composite = composite.with_duration(total_duration)
        composite.write_audiofile(str(out_path), fps=44100, nbytes=2, codec='libmp3lame', logger=None)
        composite.close()

        add_log(f"-> ĐÃ XUẤT THÀNH CÔNG TRACK GIỌNG ĐỌC HOÀN CHỈNH ({round(total_duration, 1)}s)!", level="success")
        return str(out_path)

    except Exception as e:
        add_log(f"Lỗi khi tổng hợp track âm thanh: {e}", level="error")
        return None
    finally:
        for c in loaded_clips:
            try:
                c.close()
            except Exception:
                pass
        for tf in temp_audio_files:
            try:
                if tf.exists():
                    tf.unlink()
            except Exception:
                pass

if __name__ == "__main__":
    test_vo = [
        "Bạn có bao giờ tự hỏi vì sao các sếp lớn lại đưa ra quyết định sai lầm hàng triệu đô?",
        "Ảo tưởng sức mạnh khiến họ đánh giá quá cao năng lực và phớt lờ rủi ro thị trường!",
        "Bài học rút ra: Hãy luôn lắng nghe số liệu thực tế thay vì cái tôi của bản thân."
    ]
    create_synchronized_audio_track(test_vo, [10.0, 10.0, 10.0], "downloads/test_voiceover.mp3")
