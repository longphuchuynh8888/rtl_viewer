# automation/vision.py
"""Nhận diện ảnh + chữ từ screenshot, không dùng UIAutomator / Tesseract"""

from PIL import Image, ImageChops

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False
    np = None

try:
    from rapidocr_onnxruntime import RapidOCR
    _OCR = RapidOCR()
    HAS_OCR = True
except Exception:
    _OCR = None
    HAS_OCR = False


def find_template(screen_img, template_path, threshold=0.72):
    """Tìm ảnh mẫu trên screenshot. Trả về (cx, cy, score) hoặc None."""
    if screen_img is None:
        return None

    if HAS_CV2:
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
        return max_loc[0] + w // 2, max_loc[1] + h // 2, float(max_val)

    return _find_template_pil(screen_img, template_path, threshold)


def _find_template_pil(screen_img, template_path, threshold=0.72):
    """Fallback khi không có OpenCV: quét thô bằng Pillow."""
    try:
        tpl = Image.open(template_path).convert("RGB")
    except Exception:
        return None
    screen = screen_img.convert("RGB")
    sw, sh = screen.size
    tw, th = tpl.size
    if tw >= sw or th >= sh:
        return None

    best = None
    step = max(4, min(tw, th) // 8)
    tpl_s = tpl.resize((max(1, tw // 4), max(1, th // 4)))
    for y in range(0, sh - th, step):
        for x in range(0, sw - tw, step):
            crop = screen.crop((x, y, x + tw, y + th)).resize(tpl_s.size)
            diff = ImageChops.difference(crop, tpl_s).convert("L")
            avg = sum(diff.getdata()) / float(tpl_s.size[0] * tpl_s.size[1] * 255)
            score = 1.0 - avg
            if best is None or score > best[2]:
                best = (x + tw // 2, y + th // 2, score)
    if best and best[2] >= threshold:
        return best
    return None


def find_color(screen_img, rgb, tolerance=30, region=None):
    """Tìm pixel gần màu target. region=(x1,y1,x2,y2) hoặc cả ảnh."""
    if screen_img is None:
        return None
    img = screen_img.convert("RGB")
    x1, y1, x2, y2 = region or (0, 0, img.size[0], img.size[1])
    crop = img.crop((x1, y1, x2, y2))
    target = tuple(rgb[:3])
    for y in range(0, crop.size[1], 3):
        for x in range(0, crop.size[0], 3):
            p = crop.getpixel((x, y))
            d = abs(p[0] - target[0]) + abs(p[1] - target[1]) + abs(p[2] - target[2])
            if d <= tolerance * 3:
                return x1 + x, y1 + y
    return None


def ocr_text(screen_img, region=None, lang="eng"):
    """Đọc chữ bằng RapidOCR. Trả về list {text,x,y,w,h,score}."""
    if not HAS_OCR or screen_img is None:
        return []
    img = screen_img.convert("RGB")
    if region:
        img = img.crop(region)
        ox, oy = region[0], region[1]
    else:
        ox = oy = 0

    try:
        import numpy as np
        result, _ = _OCR(np.array(img))
    except Exception:
        return []

    items = []
    if not result:
        return items
    for row in result:
        try:
            box, txt, score = row[0], row[1], row[2]
        except Exception:
            continue
        if not txt or float(score) < 0.4:
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        items.append({
            "text": str(txt),
            "x": int(ox + (x1 + x2) / 2),
            "y": int(oy + (y1 + y2) / 2),
            "w": int(x2 - x1),
            "h": int(y2 - y1),
            "score": float(score),
        })
    return items


def find_text(screen_img, needle, region=None, lang="eng"):
    """Tìm chữ (không phân biệt hoa thường). Trả về (x, y) hoặc None."""
    needle = (needle or "").strip().lower()
    if not needle:
        return None
    for item in ocr_text(screen_img, region=region, lang=lang):
        if needle in item["text"].lower():
            return item["x"], item["y"]
    return None


def vision_status():
    return {
        "opencv": HAS_CV2,
        "ocr": HAS_OCR,
        "ocr_engine": "rapidocr" if HAS_OCR else None,
    }