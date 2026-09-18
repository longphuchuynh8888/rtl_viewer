# core/url_store.py
from utils.storage import load_json, save_json

PATH = "aws_urls.json"

class UrlStore:
    def __init__(self, path=PATH):
        data = load_json(path, {"urls": {}})
        self.urls = data.get("urls") or {}

    def save(self):
        save_json(PATH, {"urls": self.urls})

    def names(self):
        return sorted(self.urls.keys())

    def get(self, name):
        return (self.urls.get(name) or {}).get("url", "")

    def upsert(self, name, url):
        name = (name or "").strip()
        url = (url or "").strip()
        if not name or not url:
            return False
        self.urls[name] = {"name": name, "url": url}
        self.save()
        return True

    def delete(self, name):
        if name in self.urls:
            del self.urls[name]
            self.save()
            return True
        return False