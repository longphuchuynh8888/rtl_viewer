# core/aws_relay.py
import json
import io
import base64
import urllib.request
import urllib.error
from PIL import Image

class AwsRelay:
    def __init__(self, base_url=""):
        self.base_url = (base_url or "").strip()
        if self.base_url and not self.base_url.endswith("/"):
            self.base_url += "/"

    def _url(self, op, serial):
        return "%s?op=%s&serial=%s" % (self.base_url, op, urllib.request.quote(serial or ""))

    def get_shot(self, serial):
        if not self.base_url or not serial:
            print("AWS get_shot thieu URL hoac serial", self.base_url, serial)
            return None
        url = self._url("shot", serial)
        try:
            req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
            raw = urllib.request.urlopen(req, timeout=20).read()
        except Exception as e:
            print("AWS get_shot HTTP loi:", e)
            return None
        if not raw:
            return None
        if raw[:2] == b"\xff\xd8":
            return Image.open(io.BytesIO(raw)).convert("RGB")
        try:
            obj = json.loads(raw.decode("utf-8", "ignore"))
            body = obj.get("body") or ""
            data = base64.b64decode(body) if obj.get("isBase64Encoded") else body.encode()
            return Image.open(io.BytesIO(data)).convert("RGB")
        except Exception as e:
            print("AWS get_shot parse loi:", e, "prefix=", raw[:80])
            return None

    def push_cmd(self, serial, cmd):
        if not self.base_url or not serial:
            return False
        url = self._url("cmd", serial)
        raw = json.dumps(cmd).encode()
        req = urllib.request.Request(url, data=raw, method="POST")
        try:
            urllib.request.urlopen(req, timeout=10).read()
            return True
        except Exception as e:
            print("AWS push_cmd loi:", e)
            return False