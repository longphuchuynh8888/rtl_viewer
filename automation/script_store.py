# automation/script_store.py
"""Một file JSON chứa nhiều kịch bản theo tên"""

import os
from utils.storage import load_json, save_json

DEFAULT_STORE = "ui_scripts/scripts_store.json"
os.makedirs("ui_scripts", exist_ok=True)


class ScriptStore:
    def __init__(self, path=DEFAULT_STORE):
        self.path = path
        self.data = load_json(path, {"scripts": {}})
        if "scripts" not in self.data:
            self.data = {"scripts": {}}

    def save(self):
        save_json(self.path, self.data)

    def names(self):
        return sorted(self.data["scripts"].keys())

    def get(self, name):
        return self.data["scripts"].get(name)

    def put(self, name, steps):
        name = (name or "").strip()
        if not name:
            return False
        self.data["scripts"][name] = steps
        self.save()
        return True

    def delete(self, name):
        if name in self.data["scripts"]:
            del self.data["scripts"][name]
            self.save()
            return True
        return False