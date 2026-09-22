import threading
import json

_lock = threading.Lock()

_default_state = {
    "step1": {
        "status": "IDLE",
        "topic": None,
        "title": None,
        "hashtags": [],
        "prompts": [],
        "voiceovers": [],
        "captions": [],
        "raw_json": None
    },
    "step2": {
        "status": "IDLE",
        "clips": [],
        "total": 3
    },
    "step3": {
        "status": "IDLE",
        "video_url": "/videos/final_tiktok_video.mp4",
        "duration": "30s",
        "resolution": "720x1280 (9:16)",
        "file_size": None,
        "has_audio": False,
        "has_subtitles": False,
        "voice_name": "Hoài My (Edge-TTS)"
    },
    "step4": {
        "status": "IDLE",
        "tiktok_title": None,
        "publish_status": "IDLE"
    }
}

current_pipeline_state = json.loads(json.dumps(_default_state))

# Khởi tạo sẵn dữ liệu thực trích xuất thành công từ The Psychology of Decision Making and Behavioral Economics
current_pipeline_state["step1"] = {
    "status": "COMPLETED",
    "topic": "Sự tự tin thái quá của CEO (CEO Overconfidence)",
    "title": "Vì sao các Sếp lớn hay đưa ra quyết định sai lầm hàng triệu đô?",
    "hashtags": [
        "#CEOOverconfidence",
        "#TamLyHocHanhVi",
        "#KinhTeHocHanhVi",
        "#QuanTriDoanhNghiep",
        "#DauTu"
    ],
    "prompts": [
        "Simple 2D flat vector animation of a stylized CEO character looking into a mirror that reflects a glowing superhero cape, on a minimal pastel background (10s)",
        "Simple 2D flat vector animation of a glowing growth arrow soaring rapidly before suddenly dipping downward into red financial loss icons (10s)",
        "Simple 2D flat vector animation of a balance scale comparing objective data reports with a giant crown icon to illustrate biased judgment (10s)"
    ],
    "voiceovers": [
        "Bạn có bao giờ tự hỏi vì sao các sếp lớn lại hay đưa ra những quyết định sai lầm tiền tỷ?",
        "Tất cả là do ảo tưởng năng lực! Họ đánh giá quá cao sự kiểm soát và phớt lờ các cảnh báo rủi ro.",
        "Bài học tài chính đắt giá: Hãy luôn tôn trọng dữ liệu khách quan thay vì cái tôi của chính mình."
    ],
    "captions": [
        "VÌ SAO SẾP LỚN HAY SAI LẦM?",
        "ẢO TƯỞNG ĐÁNH BẠI SỰ THẬT!",
        "TÔN TRỌNG DỮ LIỆU THAY VÌ CÁI TÔI!"
    ],
    "raw_json": {
        "topic": "Sự tự tin thái quá của CEO (CEO Overconfidence)",
        "title": "Vì sao các Sếp lớn hay đưa ra quyết định sai lầm hàng triệu đô?",
        "hashtags": [
            "#CEOOverconfidence",
            "#TamLyHocHanhVi",
            "#KinhTeHocHanhVi",
            "#QuanTriDoanhNghiep",
            "#DauTu"
        ],
        "prompts": [
            "Simple 2D flat vector animation of a stylized CEO character looking into a mirror that reflects a glowing superhero cape, on a minimal pastel background (10s)",
            "Simple 2D flat vector animation of a glowing growth arrow soaring rapidly before suddenly dipping downward into red financial loss icons (10s)",
            "Simple 2D flat vector animation of a balance scale comparing objective data reports with a giant crown icon to illustrate biased judgment (10s)"
        ],
        "voiceovers": [
            "Bạn có bao giờ tự hỏi vì sao các sếp lớn lại hay đưa ra những quyết định sai lầm tiền tỷ?",
            "Tất cả là do ảo tưởng năng lực! Họ đánh giá quá cao sự kiểm soát và phớt lờ các cảnh báo rủi ro.",
            "Bài học tài chính đắt giá: Hãy luôn tôn trọng dữ liệu khách quan thay vì cái tôi của chính mình."
        ],
        "captions": [
            "VÌ SAO SẾP LỚN HAY SAI LẦM?",
            "ẢO TƯỞNG ĐÁNH BẠI SỰ THẬT!",
            "TÔN TRỌNG DỮ LIỆU THAY VÌ CÁI TÔI!"
        ]
    }
}

current_pipeline_state["step2"] = {
    "status": "COMPLETED",
    "clips": [
        {
            "name": "Clip 1 (10s)",
            "file": "clip_1.mp4",
            "url": "/downloads/clip_1.mp4",
            "prompt": current_pipeline_state["step1"]["prompts"][0]
        },
        {
            "name": "Clip 2 (10s)",
            "file": "clip_2.mp4",
            "url": "/downloads/clip_2.mp4",
            "prompt": current_pipeline_state["step1"]["prompts"][1]
        },
        {
            "name": "Clip 3 (10s)",
            "file": "clip_3.mp4",
            "url": "/downloads/clip_3.mp4",
            "prompt": current_pipeline_state["step1"]["prompts"][2]
        }
    ],
    "total": 3
}

current_pipeline_state["step3"] = {
    "status": "COMPLETED",
    "video_url": "/videos/final_tiktok_video.mp4",
    "duration": "30s",
    "resolution": "720x1280 (9:16)",
    "file_size": "3.96 MB",
    "has_audio": True,
    "has_subtitles": True,
    "voice_name": "Hoài My (Edge-TTS)"
}

def get_pipeline_data() -> dict:
    with _lock:
        return json.loads(json.dumps(current_pipeline_state))

def reset_pipeline_data():
    global current_pipeline_state
    with _lock:
        current_pipeline_state = json.loads(json.dumps(_default_state))

def update_step_data(step_key: str, data_dict: dict):
    global current_pipeline_state
    with _lock:
        if step_key in current_pipeline_state:
            current_pipeline_state[step_key].update(data_dict)
