# core/device_store.py
import os
from utils.storage import load_json, save_json

PATH = "devices.json"

class DeviceStore:
    def __init__(self, path=PATH):
        self.path = path
        data = load_json(path, {"devices": {}})
        self.devices = data.get("devices") or {}

    def save(self):
        save_json(self.path, {"devices": self.devices})

    def upsert(self, serial, name="", country="", ip=""):
        serial = (serial or "").strip()
        if not serial:
            return
        old = self.devices.get(serial) or {}
        self.devices[serial] = {
            "serial": serial,
            "name": name or old.get("name") or serial,
            "country": country or old.get("country") or "-",
            "ip": ip or old.get("ip") or "-",
        }
        self.save()

    def serials(self):
        return sorted(self.devices.keys())

    def label(self, serial):
        d = self.devices.get(serial) or {}
        return "%s | %s | %s" % (
            d.get("name") or serial,
            serial,
            d.get("country") or "-",
        )

    def get(self, serial):
        return self.devices.get(serial)