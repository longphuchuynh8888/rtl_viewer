# automation/ui_parser.py
"""Parse kết quả uiautomator dump thành danh sách phần tử"""

import re

def parse_ui_dump(xml: str) -> list:
    """
    Trả về list dict:
    {
        "text": str,
        "resource_id": str,
        "content_desc": str,
        "class": str,
        "bounds": str,
        "cx": int, "cy": int,
        "clickable": bool,
        "enabled": bool
    }
    """
    elements = []
    nodes = re.findall(r'<node[^>]*>', xml)

    for node in nodes:
        def attr(name):
            m = re.search(rf'{name}="([^"]*)"', node)
            return m.group(1) if m else ""

        text = attr("text")
        rid = attr("resource-id")
        desc = attr("content-desc")
        cls = attr("class")
        bounds = attr("bounds")
        clickable = attr("clickable") == "true"
        enabled = attr("enabled") == "true"

        # Bỏ qua node không có thông tin hữu ích
        if not (text or rid or desc):
            continue

        cx = cy = 0
        m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        elements.append({
            "text": text,
            "resource_id": rid,
            "content_desc": desc,
            "class": cls,
            "bounds": bounds,
            "cx": cx,
            "cy": cy,
            "clickable": clickable,
            "enabled": enabled,
        })

    return elements