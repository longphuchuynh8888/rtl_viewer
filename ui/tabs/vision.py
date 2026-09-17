# automation/vision.py
"""Nhận diện ảnh + chữ từ screenshot, không dùng UIAutomator"""

from PIL import Image

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False

try:
    import pytesseract
    HAS_OCR = True
except Exception:
    HAS_OCR = False


def find_template(screen_img, template_path, threshold=0.72):
    """
    Tìm ảnh mẫu trên screenshot.
    Trả về (cx, cy, score) hoặc None.
    """
    if not HAS_CV2 or screen_img is None:
        return None
    screen = cv2.cvtColor(np.array(screen_img.convert("RGB")), cv2.COLOR_RGB2BGR)
    tpl = cv2.imread(template_path)
    if tpl is None:
        return None
    if tpl.shape[0] > screen.shape[0] or tpl.shape[1] > screen.shape[1]:
        return None
    res = cv2.matchTemplate(screen, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    if max_val < threshold:
        return None
    h, w = tpl.shape[:2]
    cx = max_loc[0] + w // 2
    cy = max_loc[1] + h // 2
    return cx, cy, float(max_val)


def find_color(screen_img, rgb, tolerance=30, region=None):
    """Tìm pixel gần màu target. region=(x1,y1,x2,y2) hoặc None = cả ảnh."""
    if screen_img is None:
        return None
    img = screen_img.convert("RGB")
    x1, y1, x2, y2 = region or (0, 0, img.size[0], img.size[1])
    crop = img.crop((x1, y1, x2, y2))
    target = tuple(rgb)
    best = None
    for y in range(0, crop.size[1], 3):
        for x in range(0, crop.size[0], 3):
            p = crop.getpixel((x, y))
            d = abs(p[0]-target[0]) + abs(p[1]-target[1]) + abs(p[2]-target[2])
            if d <= tolerance * 3:
                return x1 + x, y1 + y
    return best


def ocr_text(screen_img, region=None, lang="eng"):
    """Đọc chữ từ ảnh hoặc một vùng. Trả về list {text,x,y,w,h}."""
    if not HAS_OCR or screen_img is None:
        return []
    img = screen_img.convert("RGB")
    if region:
        img = img.crop(region)
        ox, oy = region[0], region[1]
    else:
        ox = oy = 0
    data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    items = []
    for i, txt in enumerate(data.get("text", [])):
        txt = (txt or "").strip()
        if not txt:
            continue
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        items.append({
            "text": txt,
            "x": ox + x + w // 2,
            "y": oy + y + h // 2,
            "w": w, "h": h,
        })
    return items


def find_text(screen_img, needle, region=None, lang="eng"):
    """Tìm chữ (không phân biệt hoa thường). Trả về (x,y) hoặc None."""
    needle = (needle or "").strip().lower()
    if not needle:
        return None
    for item in ocr_text(screen_img, region=region, lang=lang):
        if needle in item["text"].lower():
            return item["x"], item["y"]
    return None