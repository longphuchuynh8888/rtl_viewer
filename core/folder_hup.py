# core/folder_hub.py
"""Kênh không ADB: thư mục chia sẻ / Tegrabox / Drive Desktop."""

import json
import os
from PIL import Image

ROOT = "rtl_cloud"

class FolderHub:
    def __init__(self, root=ROOT):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def device_dir(self, serial):
        path = os.path.join(self.root, serial)
        os.makedirs(path, exist_ok=True)
        return path

    def serials(self):
        if not os.path.isdir(self.root):
            return []
        return sorted(
            name for name in os.listdir(self.root)
            if os.path.isdir(os.path.join(self.root, name))
        )

    def get_shot(self, serial):
        path = os.path.join(self.device_dir(serial), "latest.jpg")
        if not os.path.exists(path) or os.path.getsize(path) < 500:
            return None
        try:
            return Image.open(path).convert("RGB")
        except Exception:
            return None

    def push_cmd(self, serial, cmd):
        path = os.path.join(self.device_dir(serial), "cmd.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cmd, f)