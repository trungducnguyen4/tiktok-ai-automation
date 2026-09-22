import json
import os
from pathlib import Path
from datetime import datetime
import config

HISTORY_FILE = config.BASE_DIR / "history.json"

def load_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history_item(item: dict):
    history = load_history()
    history.insert(0, item) # Mới nhất lên đầu
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
