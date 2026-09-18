# automation/script_runner.py
"""Chạy kịch bản: UIAutomator hoặc Hình ảnh/OCR"""

import os
import time
import subprocess

from automation.ui_parser import parse_ui_dump
from automation.conditions import evaluate_step_conditions
from automation.learning.action_memory import ActionMemory
from automation.learning.template_matcher import TemplateMatcher
from automation.vision import find_template, find_text, find_color


class ScriptRunner:
    def __init__(self, worker):
        self.worker = worker
        self.memory = ActionMemory()
        self.matcher = TemplateMatcher()
        self.engine = "uiautomator"

    def _device_size(self, img):
        worker = self.worker
        size = getattr(worker, "last_device_size", None)
        if size and size[0] > 0 and size[1] > 0:
            return size
        if img is not None:
            return img.size
        return (1, 1)

    def _refresh_preview(self):
        worker = self.worker
        worker.force_next = True
        preview = worker.get_screenshot()
        if preview:
            worker.last_image = preview.copy()
            worker.save_local(preview)
            worker.screenshot_ready.emit(preview)

    def _tap_from_image(self, img, x, y, long=False):
        dw, dh = self._device_size(img)
        iw, ih = img.size if img is not None else (dw, dh)
        if iw <= 0 or ih <= 0:
            nx, ny = int(x), int(y)
        else:
            nx = int(x * dw / iw)
            ny = int(y * dh / ih)
        if long:
            self.worker.long_press(nx, ny)
        else:
            self.worker.tap(nx, ny)
        self.worker.log(
            f"✓ Tap thiết bị ({nx},{ny}) từ ảnh ({int(x)},{int(y)}) "
            f"size={iw}x{ih} → {dw}x{dh}"
        )
        time.sleep(0.35)
        self._refresh_preview()

    def find_and_tap(self, elements, mode, value, long=False):
        if mode == "coords":
            try:
                x, y = map(int, value.split(","))
                if long:
                    self.worker.long_press(x, y)
                else:
                    self.worker.tap(x, y)
                return True
            except Exception:
                return False

        for el in elements or []:
            match = False
            if mode == "text" and el.get("text") == value:
                match = True
            elif mode == "resource_id" and el.get("resource_id") == value:
                match = True
            elif mode == "content_desc" and el.get("content_desc") == value:
                match = True
            if match and el.get("cx", 0) > 0:
                if long:
                    self.worker.long_press(el["cx"], el["cy"])
                else:
                    self.worker.tap(el["cx"], el["cy"])
                return True
        return False

    def run(self, steps, loop=1, delay_ms=800):
        worker = self.worker
        worker.script_running = True
        count = 0

        while worker.script_running and (loop <= 0 or count < loop):
            count += 1
            worker.log(f"--- Lần chạy {count} | engine={self.engine} ---")

            elements = []
            if self.engine == "uiautomator":
                worker.dump_ui()
                time.sleep(0.5)
                data = worker.adb_out(
                    ["exec-out", "cat", "/data/local/tmp/rtl_screens/window_dump.xml"],
                    8
                )
                elements = parse_ui_dump(data.decode(errors="ignore")) if data else []
            else:
                worker.log("Chế độ Hình ảnh/OCR — bỏ qua UIAutomator")

            for step in steps:
                if not worker.script_running:
                    break

                action = step.get("action")
                value = step.get("value", "")
                mode = step.get("mode", "coords")
                if self.engine == "vision":
                    img = worker.get_screenshot_full()
                else:
                    img = worker.get_screenshot()

                if not evaluate_step_conditions(
                    step, elements=elements, img=img, matcher=self.matcher
                ):
                    worker.log(f"⏭ Bỏ qua (điều kiện chưa thỏa): {value}")
                    continue

                if action in ("tap", "long_press"):
                    if self.engine == "vision" and mode in ("text", "content_desc"):
                        pos = find_text(img, value)
                        if pos:
                            self._tap_from_image(img, pos[0], pos[1], long=(action == "long_press"))
                        else:
                            worker.log(f"✗ OCR không thấy: {value}")
                    else:
                        ok = self.find_and_tap(
                            elements, mode, value, long=(action == "long_press")
                        )
                        if ok:
                            worker.log(f"✓ {action} ({mode}): {value}")
                            self._refresh_preview()
                        else:
                            self._handle_miss(worker, img, mode, value)

                elif action == "find_image":
                    pos = find_template(img, value)
                    if pos:
                        worker.log(f"Ảnh mẫu score={pos[2]:.2f}")
                        self._tap_from_image(img, pos[0], pos[1])
                    else:
                        worker.log(f"✗ Không thấy ảnh mẫu: {value}")

                elif action == "find_ocr":
                    pos = find_text(img, value)
                    if pos:
                        self._tap_from_image(img, pos[0], pos[1])
                    else:
                        worker.log(f"✗ OCR không thấy: {value}")

                elif action == "find_color":
                    try:
                        parts = [p.strip() for p in str(value).split(",")]
                        rgb = [int(parts[0]), int(parts[1]), int(parts[2])]
                    except Exception:
                        worker.log(f"✗ RGB không hợp lệ: {value}")
                        rgb = None
                    pos = find_color(img, rgb) if rgb else None
                    if pos:
                        self._tap_from_image(img, pos[0], pos[1])
                    elif rgb:
                        worker.log(f"✗ Không thấy màu {rgb}")

                elif action == "swipe":
                    parts = [p.strip() for p in str(value).split(",")]
                    if len(parts) >= 4:
                        dur = parts[4] if len(parts) > 4 else "300"
                        worker.adb(["shell", "input", "swipe",
                                    parts[0], parts[1], parts[2], parts[3], dur])
                        worker.log(f"✓ Swipe {value}")
                        self._refresh_preview()

                elif action == "text":
                    worker.send_text(value, press_enter=step.get("enter", True))
                    self._refresh_preview()
                elif action == "key":
                    worker.adb(["shell", "input", "keyevent", value])
                    worker.log(f"✓ Key: {value}")
                    self._refresh_preview()
                elif action == "launch":
                    worker.launch_app(value)
                    self._refresh_preview()
                elif action == "stop":
                    worker.force_stop_app(value)
                    self._refresh_preview()
                elif action == "uninstall":
                    worker.uninstall_app(value)
                elif action == "clear":
                    worker.clear_storage(value)
                elif action == "unlock":
                    worker.unlock_swipe_up()
                    worker.log("✓ Mở khóa")
                    self._refresh_preview()
                elif action == "rotate":
                    worker.rotate_screen(int(value or 0))
                    worker.log(f"✓ Xoay {value}")
                    self._refresh_preview()
                elif action == "wait":
                    try:
                        time.sleep(float(value) / 1000.0)
                    except Exception:
                        time.sleep(0.5)
                elif action == "run_python":
                    if value and os.path.exists(value):
                        worker.log(f"▶ Chạy Python: {value}")
                        subprocess.run(["python", value], timeout=60)
                    else:
                        worker.log(f"✗ Không thấy file: {value}")

                time.sleep(delay_ms / 1000.0)

            if loop > 0 and count >= loop:
                break

        worker.script_running = False
        self._refresh_preview()
        worker.log("✓ Kết thúc kịch bản")

    def _handle_miss(self, worker, img, mode, value):
        worker.log(f"✗ Không tìm thấy: {value}")
        reason = f"Không tìm thấy [{mode}] = {value}"
        found = None
        try:
            found = self.matcher.find(img, reason=reason)
        except Exception:
            found = None
        if found:
            x, y, score = found
            worker.log(f"Template score={score:.2f}")
            self._tap_from_image(img, x, y)
            return
        size = img.size if img else None
        sug = self.memory.suggest(reason, current_size=size)
        if sug and sug[0] is not None:
            self._tap_from_image(img, sug[0], sug[1])
            return
        if worker.help_enabled:
            result = worker.request_help(reason)
            if result is None or result == "stop":
                worker.script_running = False
            elif result == "skip":
                worker.log("⏭ Bỏ qua bước")
            elif isinstance(result, tuple) and result[0] == "tap":
                self._tap_from_image(img, result[1], result[2])
        else:
            worker.log("⚠ Bỏ qua (tắt hỗ trợ)")