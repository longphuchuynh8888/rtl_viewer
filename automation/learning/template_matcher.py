# automation/learning/template_matcher.py
"""Nhận diện vị trí click bằng template matching (OpenCV)"""

import os
from datetime import datetime

from utils.storage import load_json, save_json

TEMPLATE_DIR = "learned_templates"
TEMPLATE_FILE = os.path.join(TEMPLATE_DIR, "templates.json")
os.makedirs(TEMPLATE_DIR, exist_ok=True)

# OpenCV là tùy chọn
try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False


class TemplateMatcher:
    def __init__(self, threshold=0.72):
        self.threshold = threshold
        self.templates = load_json(TEMPLATE_FILE, [])

    def available(self):
        return HAS_CV2

    def save(self):
        save_json(TEMPLATE_FILE, self.templates)

    def add_from_image(self, img, x, y, reason="", box=80):
        """
        Cắt vùng quanh điểm click rồi lưu thành template.
        img: PIL Image
        x, y: tọa độ click
        box: kích thước cắt (pixel)
        """
        if img is None:
            return None

        w, h = img.size
        half = box // 2
        x1 = max(0, x - half)
        y1 = max(0, y - half)
        x2 = min(w, x + half)
        y2 = min(h, y + half)

        crop = img.crop((x1, y1, x2, y2))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"tpl_{ts}.jpg"
        path = os.path.join(TEMPLATE_DIR, name)
        crop.save(path, "JPEG", quality=70)

        rec = {
            "id": ts,
            "reason": reason or "",
            "path": path,
            "click_dx": x - x1,
            "click_dy": y - y1,
            "src_w": w,
            "src_h": h,
        }
        self.templates.append(rec)
        self.save()
        return rec

    def find(self, img, reason=""):
        """
        Tìm template trên ảnh hiện tại.
        Trả về (x, y, score) hoặc None.
        """
        if not HAS_CV2 or img is None or not self.templates:
            return None

        screen = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
        best = None

        candidates = self.templates
        if reason:
            filtered = [t for t in self.templates if reason.lower() in (t.get("reason") or "").lower()]
            if filtered:
                candidates = filtered

        for rec in reversed(candidates):
            path = rec.get("path")
            if not path or not os.path.exists(path):
                continue
            tpl = cv2.imread(path)
            if tpl is None:
                continue
            if tpl.shape[0] > screen.shape[0] or tpl.shape[1] > screen.shape[1]:
                continue

            result = cv2.matchTemplate(screen, tpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val >= self.threshold:
                x = max_loc[0] + int(rec.get("click_dx", tpl.shape[1] // 2))
                y = max_loc[1] + int(rec.get("click_dy", tpl.shape[0] // 2))
                if best is None or max_val > best[2]:
                    best = (x, y, float(max_val))

        return best