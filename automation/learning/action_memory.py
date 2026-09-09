# automation/learning/action_memory.py
"""Ghi nhớ thao tác người dùng khi hỗ trợ kịch bản bị kẹt"""

import os
import time
from datetime import datetime
from PIL import Image

from utils.storage import load_json, save_json

MEMORY_DIR = "learned_actions"
MEMORY_FILE = os.path.join(MEMORY_DIR, "memory.json")
os.makedirs(MEMORY_DIR, exist_ok=True)


class ActionMemory:
    def __init__(self, memory_file=MEMORY_FILE):
        self.memory_file = memory_file
        self.records = load_json(memory_file, [])

    def save(self):
        save_json(self.memory_file, self.records)

    def add(self, img, x, y, reason="", extra=None):
        """
        Lưu 1 thao tác người dùng.
        img: PIL Image
        x, y: tọa độ click trên ảnh gốc
        reason: lý do kẹt (text / resource-id / ...)
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_name = f"action_{ts}.jpg"
        img_path = os.path.join(MEMORY_DIR, img_name)

        try:
            if img:
                w, h = img.size
                img.save(img_path, "JPEG", quality=55, optimize=True)
            else:
                w = h = 0
                img_path = ""
        except Exception:
            w = h = 0
            img_path = ""

        record = {
            "id": ts,
            "time": datetime.now().isoformat(timespec="seconds"),
            "reason": reason or "",
            "x": int(x),
            "y": int(y),
            "image": img_path,
            "width": w,
            "height": h,
            "rel_x": round(x / w, 4) if w else 0,
            "rel_y": round(y / h, 4) if h else 0,
            "extra": extra or {},
        }
        self.records.append(record)
        self.save()
        return record

    def all(self):
        return list(self.records)

    def find_similar_by_reason(self, reason, limit=5):
        """Tìm các thao tác đã lưu có reason giống nhau."""
        if not reason:
            return []
        key = reason.lower().strip()
        hits = [r for r in self.records if key in (r.get("reason") or "").lower()]
        return hits[-limit:]

    def suggest(self, reason="", current_size=None):
        """
        Gợi ý tọa độ dựa trên thao tác đã học.
        Ưu tiên reason giống nhau, lấy bản ghi mới nhất.
        current_size: (w, h) của ảnh hiện tại để quy đổi tọa độ tương đối.
        """
        hits = self.find_similar_by_reason(reason, limit=1)
        if not hits:
            if not self.records:
                return None
            hits = [self.records[-1]]

        rec = hits[-1]
        if current_size and rec.get("rel_x") is not None:
            w, h = current_size
            return int(rec["rel_x"] * w), int(rec["rel_y"] * h)
        return rec.get("x"), rec.get("y")

    def count(self):
        return len(self.records)