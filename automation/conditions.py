# automation/conditions.py
"""Kiểm tra điều kiện kết hợp AND / OR cho từng bước kịch bản"""

def _color_distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def check_ui_exists(elements, cond):
    """cond: {type: text|resource_id|content_desc, value, op: exists|not_exists}"""
    key = cond.get("type", "text")
    value = cond.get("value", "")
    op = cond.get("op", "exists")
    found = False
    for el in elements or []:
        if el.get(key) == value:
            found = True
            break
    return found if op == "exists" else (not found)


def check_color(img, cond):
    """
    cond: {type: color, x, y, rgb: [r,g,b], tolerance}
    """
    if img is None:
        return False
    try:
        x = int(cond.get("x", 0))
        y = int(cond.get("y", 0))
        target = tuple(cond.get("rgb", [0, 0, 0]))
        tol = int(cond.get("tolerance", 30))
        w, h = img.size
        x = max(0, min(x, w - 1))
        y = max(0, min(y, h - 1))
        pixel = img.convert("RGB").getpixel((x, y))
        return _color_distance(pixel, target) <= tol * 3
    except Exception:
        return False


def check_region_image(img, cond, matcher=None):
    """
    cond: {type: region_image, x1, y1, x2, y2}
    Cắt vùng rồi đưa vào TemplateMatcher.find()
    """
    if img is None:
        return False
    try:
        x1 = int(cond.get("x1", 0))
        y1 = int(cond.get("y1", 0))
        x2 = int(cond.get("x2", 0))
        y2 = int(cond.get("y2", 0))
        if x2 <= x1 or y2 <= y1:
            return False
        crop = img.crop((x1, y1, x2, y2))
        if matcher is None:
            return True
        found = matcher.find(crop, reason=cond.get("reason", ""))
        return found is not None
    except Exception:
        return False


def evaluate_condition(cond, elements=None, img=None, matcher=None):
    ctype = cond.get("type")
    if ctype in ("text", "resource_id", "content_desc"):
        return check_ui_exists(elements, cond)
    if ctype == "color":
        return check_color(img, cond)
    if ctype == "region_image":
        return check_region_image(img, cond, matcher=matcher)
    if ctype == "run_python":
    	return check_run_python(cond)
    return False


def evaluate_step_conditions(step, elements=None, img=None, matcher=None):
    """
    Trả về True nếu bước được phép chạy.
    Không có conditions → luôn True.
    logic: AND | OR
    """
    conditions = step.get("conditions") or []
    if not conditions:
        return True

    logic = (step.get("logic") or "AND").upper()
    results = [
        evaluate_condition(c, elements=elements, img=img, matcher=matcher)
        for c in conditions
    ]
    if logic == "OR":
        return any(results)
    return all(results)
def check_run_python(cond):
	path = cond.get("python_file", "")
	return bool(path) and os.path.exists(path)