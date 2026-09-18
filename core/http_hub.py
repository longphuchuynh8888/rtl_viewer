# core/http_hub.py
"""Hub HTTP: nhận ảnh từ thiết bị, phát lệnh tap/swipe."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from urllib.parse import urlparse

from PIL import Image


class DeviceHub:
    def __init__(self):
        self.shots = {}       # serial -> PIL Image
        self.cmds = {}        # serial -> list[dict]
        self.lock = threading.Lock()

    def put_shot(self, serial, img):
        with self.lock:
            self.shots[serial] = img

    def get_shot(self, serial):
        with self.lock:
            return self.shots.get(serial)

    def serials(self):
        with self.lock:
            return list(self.shots.keys())

    def push_cmd(self, serial, cmd):
        with self.lock:
            self.cmds.setdefault(serial, []).append(cmd)

    def pop_cmd(self, serial):
        with self.lock:
            lst = self.cmds.get(serial) or []
            if not lst:
                return None
            return lst.pop(0)


HUB = DeviceHub()


class HubHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _send(self, code=200, body=b"ok", ctype="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path.strip("/")
        parts = path.split("/")
        if len(parts) == 2 and parts[0] == "cmd":
            cmd = HUB.pop_cmd(parts[1])
            raw = json.dumps(cmd or {}).encode()
            self._send(200, raw, "application/json")
            return
        if path == "devices":
            raw = json.dumps(HUB.serials()).encode()
            self._send(200, raw, "application/json")
            return
        self._send(404, b"not found")

    def do_POST(self):
        path = urlparse(self.path).path.strip("/")
        parts = path.split("/")
        length = int(self.headers.get("Content-Length", "0") or 0)
        data = self.rfile.read(length) if length else b""

        if len(parts) == 2 and parts[0] == "shot":
            serial = parts[1] or "unknown"
            try:
                img = Image.open(BytesIO(data)).convert("RGB")
                HUB.put_shot(serial, img)
                self._send(200, b"ok")
            except Exception:
                self._send(400, b"bad image")
            return

        if len(parts) == 2 and parts[0] == "cmd":
            try:
                cmd = json.loads(data.decode() or "{}")
            except Exception:
                cmd = {}
            HUB.push_cmd(parts[1], cmd)
            self._send(200, b"queued")
            return

        self._send(404, b"not found")


class HubServer:
    def __init__(self, port=8765):
        self.port = port
        self.httpd = None
        self.thread = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), HubHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()