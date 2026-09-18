# -*- coding: utf-8 -*-
# core/adb_worker.py
"""Giao tiep ADB + Service + lenh dieu khien thiet bi"""

import subprocess
import time
import io
import os
import tempfile
import urllib.request
import json
from datetime import datetime

from PyQt5.QtCore import QObject, pyqtSignal
from PIL import Image, ImageChops

DEVICE_DIR = "/data/local/tmp/rtl_screens"
DEVICE_LATEST = DEVICE_DIR + "/latest.jpg"
DEVICE_TEXT = DEVICE_DIR + "/screen_text.txt"
DEVICE_DUMP = DEVICE_DIR + "/window_dump.xml"
DEVICE_IPINFO = DEVICE_DIR + "/ipinfo.json"
SERVICE_SCRIPT = "/data/local/tmp/screen_service.sh"
SAVE_DIR = "rtl_screenshots"
os.makedirs(SAVE_DIR, exist_ok=True)


class ADBWorker(QObject):
    screenshot_ready = pyqtSignal(object)
    status_message = pyqtSignal(str)
    log_message = pyqtSignal(str)
    packages_ready = pyqtSignal(list)
    running_ready = pyqtSignal(list)
    device_info_ready = pyqtSignal(dict)
    screen_text_ready = pyqtSignal(str)
    ui_elements_ready = pyqtSignal(list)
    need_help = pyqtSignal(object, str)

    def __init__(self):
        super(ADBWorker, self).__init__()
        self.running = True
        self.auto_refresh = True
        self.interval = 1.8
        self.mode = "service"
        self.auto_unlock = False
        self.quality = 0.5
        self.jpeg_quality = 40
        self.change_threshold = 8.0
        self.last_image = None
        self.last_device_size = (1080, 2340)
        self.force_next = False
        self.script_running = False
        self.help_enabled = True
        self._help_result = None

    def adb(self, args, timeout=15):
        try:
            r = subprocess.run(["adb"] + args, capture_output=True, timeout=timeout)
            return r.stdout, r.stderr, r.returncode
        except Exception:
            return None, b"", -1

    def adb_out(self, args, timeout=15):
        out, _, _ = self.adb(args, timeout)
        return out

    def log(self, msg):
        self.log_message.emit(msg)

    def get_resolution(self):
        out = self.adb_out(["shell", "wm", "size"], 6)
        if out:
            for line in out.decode(errors="ignore").splitlines():
                if "Physical size:" in line or "Override size:" in line:
                    try:
                        return tuple(map(int, line.split(":")[-1].strip().split("x")))
                    except Exception:
                        pass
        return 1080, 2340

    def get_current_rotation(self):
        out = self.adb_out(["shell", "settings", "get", "system", "user_rotation"], 5)
        try:
            return int(out.decode().strip())
        except Exception:
            return 0

    def correct_orientation(self, img):
        if img is None:
            return None
        try:
            rotation = self.get_current_rotation()
            w, h = img.size
            if rotation in (1, 3) and h > w:
                img = img.rotate(-90 if rotation == 1 else 90, expand=True)
            elif rotation in (0, 2) and w > h:
                img = img.rotate(90 if rotation == 0 else -90, expand=True)
        except Exception:
            pass
        return img

    def take_screenshot_service_pull(self):
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name
            code = self.adb(["pull", DEVICE_LATEST, tmp_path], timeout=12)[2]
            if code != 0 or not os.path.exists(tmp_path) or os.path.getsize(tmp_path) < 500:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                return None
            img = Image.open(tmp_path).convert("RGB")
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            return img
        except Exception:
            return None

    def take_screenshot_service_cat(self):
        data = self.adb_out(["exec-out", "cat", DEVICE_LATEST], 10)
        if data and len(data) > 500:
            try:
                return Image.open(io.BytesIO(data)).convert("RGB")
            except Exception:
                pass
        return None

    def take_screenshot_adb(self):
        data = self.adb_out(["exec-out", "screencap", "-p"], 20)
        if data and len(data) > 1000:
            try:
                return Image.open(io.BytesIO(data)).convert("RGB")
            except Exception:
                pass
        return None

    def get_screenshot_full(self):
        if self.mode == "service":
            img = (self.take_screenshot_service_pull()
                   or self.take_screenshot_service_cat()
                   or self.take_screenshot_adb())
        else:
            img = self.take_screenshot_adb()
        img = self.correct_orientation(img)
        if img:
            self.last_device_size = img.size
        return img

    def get_screenshot(self):
        img = self.get_screenshot_full()
        if img and self.quality < 1.0:
            w, h = img.size
            img = img.resize(
                (max(1, int(w * self.quality)), max(1, int(h * self.quality))),
                Image.LANCZOS
            )
        return img

    def get_screenshot_live(self):
        img = self.take_screenshot_adb()
        if img is None:
            img = self.get_screenshot_full()
        img = self.correct_orientation(img)
        if img:
            self.last_device_size = img.size
        if img and self.quality < 1.0:
            w, h = img.size
            img = img.resize(
                (max(1, int(w * self.quality)), max(1, int(h * self.quality))),
                Image.LANCZOS
            )
        return img

    def has_changed(self, new_img):
        if self.force_next or self.last_image is None:
            self.force_next = False
            return True
        try:
            a = self.last_image.resize((64, 64), Image.BILINEAR).convert("L")
            b = new_img.resize((64, 64), Image.BILINEAR).convert("L")
            avg = sum(ImageChops.difference(a, b).getdata()) / (64.0 * 64.0)
            return avg > self.change_threshold
        except Exception:
            return True

    def save_local(self, img):
        if not img:
            return
        path = os.path.join(SAVE_DIR, datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg")
        try:
            img.save(path, "JPEG", quality=self.jpeg_quality, optimize=True)
        except Exception:
            pass

    def start_loop(self):
        while self.running:
            if self.auto_refresh and not self.script_running:
                img = self.get_screenshot()
                if img:
                    if self.has_changed(img):
                        self.last_image = img.copy()
                        self.save_local(img)
                        self.screenshot_ready.emit(img)
                        self.status_message.emit(
                            "Thay doi • " + datetime.now().strftime("%H:%M:%S")
                        )
                    else:
                        self.status_message.emit(
                            "Khong doi • " + datetime.now().strftime("%H:%M:%S")
                        )
                else:
                    self.status_message.emit("Khong co anh")
            if self.auto_unlock:
                self.try_auto_unlock()
            time.sleep(self.interval)

    def stop(self):
        self.running = False
        self.script_running = False

    def install_service(self):
        script = """#!/system/bin/sh
DIR="/data/local/tmp/rtl_screens"
mkdir -p "$DIR"
LATEST="$DIR/latest.jpg"
LATEST_PNG="$DIR/latest_full.png"
TEXTFILE="$DIR/screen_text.txt"
IPFILE="$DIR/ipinfo.json"
HUB="http://127.0.0.1:8765"
SERIAL=$(getprop ro.serialno)
CLOUD="/sdcard/Download/rtl_cloud/$SERIAL"
mkdir -p "$CLOUD"
echo "[RTL Service] Started $(date) serial=$SERIAL" > "$DIR/service.log"

get_ip_info() {
    if command -v curl >/dev/null 2>&1; then
        curl -s --max-time 8 "https://ipapi.co/json/" -o "$IPFILE" 2>/dev/null && return
    fi
    echo '{"ip":"unknown"}' > "$IPFILE"
}

dump_screen_text() {
    uiautomator dump "$DIR/window_dump.xml" >/dev/null 2>&1
    if [ -f "$DIR/window_dump.xml" ]; then
        grep -o 'text="[^"]*"' "$DIR/window_dump.xml" 2>/dev/null | sed 's/text="//g; s/"//g' | grep -v '^$' > "$TEXTFILE"
    fi
}

handle_cmd() {
    CMD="$1"
    [ -z "$CMD" ] && return
    echo "$CMD" | grep -q tap || return
    X=$(echo "$CMD" | sed -n 's/.*"x":[ ]*\\([0-9][0-9]*\\).*/\\1/p')
    Y=$(echo "$CMD" | sed -n 's/.*"y":[ ]*\\([0-9][0-9]*\\).*/\\1/p')
    if [ -n "$X" ] && [ -n "$Y" ]; then
        input tap "$X" "$Y"
        echo "[CMD] tap $X $Y" >> "$DIR/service.log"
    fi
}

do_hub() {
    [ -f "$LATEST" ] || return
    if command -v curl >/dev/null 2>&1; then
        curl -s --max-time 4 -X POST --data-binary @"$LATEST" "$HUB/shot/$SERIAL" >/dev/null 2>&1
        CMD=$(curl -s --max-time 3 "$HUB/cmd/$SERIAL" 2>/dev/null)
        handle_cmd "$CMD"
    fi
}
do_aws() {
    [ -f "$DIR/cloud.url" ] || return
    [ -f "$LATEST" ] || return
    URL=$(cat "$DIR/cloud.url")
    command -v curl >/dev/null 2>&1 || return
    curl -s --max-time 8 -X POST --data-binary @"$LATEST" \
        "$URL?op=shot&serial=$SERIAL" >/dev/null 2>&1
    CMD=$(curl -s --max-time 5 "$URL?op=cmd&serial=$SERIAL")
    handle_cmd "$CMD"
}
do_cloud() {
    [ -f "$LATEST" ] || return
    cp "$LATEST" "$CLOUD/latest.jpg" 2>/dev/null
    if [ -f "$CLOUD/cmd.json" ]; then
        CMD=$(cat "$CLOUD/cmd.json")
        rm -f "$CLOUD/cmd.json"
        handle_cmd "$CMD"
    fi
}

get_ip_info
COUNTER=0
while true; do
    screencap -p "$LATEST_PNG"
    if command -v convert >/dev/null 2>&1; then
        convert "$LATEST_PNG" -quality 35 "$LATEST" 2>/dev/null
    else
        cp "$LATEST_PNG" "$LATEST" 2>/dev/null
    fi
    do_hub
    do_aws
    do_cloud
    if [ $((COUNTER % 3)) -eq 0 ]; then
        dump_screen_text
    fi
    COUNTER=$((COUNTER+1))
    sleep 1.6
done
"""
        local = "screen_service_temp.sh"
        with open(local, "w") as f:
            f.write(script.replace("\r\n", "\n"))
        self.adb(["push", local, SERVICE_SCRIPT])
        try:
            os.remove(local)
        except Exception:
            pass
        self.adb(["shell", "chmod", "755", SERVICE_SCRIPT])
        self.adb(["shell", "mkdir -p " + DEVICE_DIR])
        self.adb(["reverse", "tcp:8765", "tcp:8765"])
        self.log("Da cai Service + adb reverse :8765")

    def start_service(self):
        self.adb(["shell", "pkill", "-f", "screen_service.sh"])
        time.sleep(0.4)
        self.adb(["shell", "nohup " + SERVICE_SCRIPT + " > " + DEVICE_DIR + "/service.log 2>&1 &"])
        self.log("Da Start Service")

    def stop_service(self):
        self.adb(["shell", "pkill", "-f", "screen_service.sh"])
        self.log("Da Stop Service")

    def check_service(self):
        out = self.adb_out(["shell", "ps -A | grep screen_service"], 6)
        running = out and b"screen_service" in out
        self.log("Service dang chay" if running else "Service khong chay")
        return running

    def get_screen_text(self):
        data = self.adb_out(["exec-out", "cat", DEVICE_TEXT], 8)
        if data:
            text = data.decode(errors="ignore").strip()
            self.screen_text_ready.emit(text if text else "(Khong co text)")
        else:
            self.screen_text_ready.emit("(Chua co du lieu)")

    def dump_ui(self):
        self.adb(["shell", "uiautomator", "dump", DEVICE_DUMP], timeout=10)
        data = self.adb_out(["exec-out", "cat", DEVICE_DUMP], 10)
        if not data:
            self.ui_elements_ready.emit([])
            return
        from automation.ui_parser import parse_ui_dump
        elements = parse_ui_dump(data.decode(errors="ignore"))
        self.ui_elements_ready.emit(elements)
        self.log("Dump UI: %d phan tu" % len(elements))

    def tap(self, x, y):
        self.adb(["shell", "input", "tap", str(int(x)), str(int(y))])

    def long_press(self, x, y, duration=800):
        self.adb(["shell", "input", "swipe",
                  str(int(x)), str(int(y)), str(int(x)), str(int(y)), str(duration)])

    def push_file(self, local_path, remote_path=None):
        if not remote_path:
            remote_path = "/sdcard/Download/" + os.path.basename(local_path)
        code = self.adb(["push", local_path, remote_path], timeout=60)[2]
        self.log("Gui file: " + os.path.basename(local_path))

    def pull_file(self, remote_path, local_path=None):
        if not local_path:
            local_path = os.path.basename(remote_path)
        self.adb(["pull", remote_path, local_path], timeout=60)

    def list_packages(self, pkg_type="user"):
        cmd = ["shell", "pm", "list", "packages"] if pkg_type == "all" else ["shell", "pm", "list", "packages", "-3"]
        out = self.adb_out(cmd, 25)
        packages = []
        if out:
            for line in out.decode(errors="ignore").splitlines():
                if line.startswith("package:"):
                    packages.append(line.replace("package:", "").strip())
        packages.sort()
        self.packages_ready.emit(packages)

    def list_running_apps(self):
        out = self.adb_out(["shell", "ps -A -o NAME"], 12)
        running = set()
        if out:
            for line in out.decode(errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("NAME") and "." in line:
                    running.add(line)
        self.running_ready.emit(sorted(list(running)))

    def launch_app(self, package):
        self.adb(["shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"])
        self.log("Da mo: " + package)

    def force_stop_app(self, package):
        self.adb(["shell", "am", "force-stop", package])
        self.log("Da dung: " + package)

    def uninstall_app(self, package):
        self.adb(["shell", "pm", "uninstall", package])

    def clear_storage(self, package):
        self.adb(["shell", "pm", "clear", package])

    def clear_cache(self, package):
        self.adb(["shell", "pm", "clear", package])

    def send_text(self, text, press_enter=True, mode="auto", is_password=False):
        if not text:
            return
        if mode == "auto":
            mode = "char" if is_password else "input"
        if mode == "adbkeyboard":
            if not self.send_text_adbkeyboard(text):
                mode = "input"
        if mode == "char":
            self._send_text_char_by_char(text)
        elif mode == "input":
            self.adb(["shell", "input", "text", self._escape_adb_text(text)])
        if press_enter:
            time.sleep(0.15)
            self.adb(["shell", "input", "keyevent", "KEYCODE_ENTER"])

    def _escape_adb_text(self, text):
        mapping = {
            " ": "%s", "%": "%%", "'": "\\'", '"': '\\"', "\\": "\\\\",
            "&": "\\&", "<": "\\<", ">": "\\>", "|": "\\|", ";": "\\;",
            "(": "\\(", ")": "\\)", "#": "\\#", "$": "\\$", "`": "\\`",
        }
        return "".join(mapping.get(ch, ch) for ch in text)

    def _send_text_char_by_char(self, text):
        key_alias = {
            "@": "AT", "#": "POUND", "*": "STAR", "/": "SLASH",
            "\\": "BACKSLASH", ",": "COMMA", ".": "PERIOD",
            "-": "MINUS", "=": "EQUALS", "+": "PLUS",
            " ": "SPACE", "\n": "ENTER", "\t": "TAB",
        }
        try:
            for ch in text:
                if ch in key_alias:
                    self.adb(["shell", "input", "keyevent", "KEYCODE_" + key_alias[ch]])
                elif ch.isalnum():
                    self.adb(["shell", "input", "text", ch])
                else:
                    self.adb(["shell", "input", "text", self._escape_adb_text(ch)])
                time.sleep(0.03)
            return True
        except Exception:
            return False

    def send_text_adbkeyboard(self, text):
        _, _, code = self.adb([
            "shell", "am", "broadcast", "-a", "ADB_INPUT_TEXT", "--es", "msg", text
        ])
        return code == 0

    def install_apk(self, apk_path):
        self.adb(["install", "-r", apk_path], timeout=120)

    def install_adb_keyboard(self, apk_path):
        self.install_apk(apk_path)
        self.enable_adb_keyboard()

    def enable_adb_keyboard(self):
        ime = "com.android.adbkeyboard/.AdbIME"
        self.adb(["shell", "ime", "enable", ime])
        self.adb(["shell", "ime", "set", ime])

    def disable_adb_keyboard(self):
        self.adb(["shell", "ime", "reset"])

    def install_from_url(self, url):
        try:
            local = "temp_download.apk"
            urllib.request.urlretrieve(url, local)
            self.install_apk(local)
            os.remove(local)
        except Exception as e:
            self.log(str(e))

    def open_play_store(self, package):
        self.adb(["shell", "am", "start", "-a", "android.intent.action.VIEW",
                  "-d", "market://details?id=" + package])

    def rotate_screen(self, orientation):
        self.adb(["shell", "settings", "put", "system", "accelerometer_rotation", "0"])
        self.adb(["shell", "settings", "put", "system", "user_rotation", str(orientation)])

    def unlock_swipe_up(self):
        self.adb(["shell", "input", "keyevent", "KEYCODE_WAKEUP"])
        time.sleep(0.4)
        w, h = self.get_resolution()
        self.adb(["shell", "input", "swipe",
                  str(w // 2), str(int(h * 0.85)),
                  str(w // 2), str(int(h * 0.25)), "300"])

    def try_auto_unlock(self):
        self.unlock_swipe_up()

    def get_device_info(self):
        info = {}
        for name, prop in {
            "Model": "ro.product.model",
            "Manufacturer": "ro.product.manufacturer",
            "Android": "ro.build.version.release",
            "Serial": "ro.serialno"
        }.items():
            out = self.adb_out(["shell", "getprop", prop], 5)
            info[name] = out.decode(errors="ignore").strip() if out else "-"
        w, h = self.get_resolution()
        info["Resolution"] = "%sx%s" % (w, h)
        data = self.adb_out(["exec-out", "cat", DEVICE_IPINFO], 8)
        if data:
            try:
                j = json.loads(data.decode(errors="ignore"))
                info["Public IP"] = j.get("ip", "-")
                info["Country"] = j.get("country_name", "-")
            except Exception:
                pass
        self.device_info_ready.emit(info)

    def request_help(self, reason="Khong tim thay"):
        img = self.get_screenshot_full() or self.take_screenshot_adb()
        self._help_result = None
        self.need_help.emit(img, reason)
        waited = 0
        while self._help_result is None and self.script_running and waited < 120:
            time.sleep(0.4)
            waited += 0.4
        result = self._help_result
        self._help_result = None
        return result

    def set_help_result(self, result):
        self._help_result = result