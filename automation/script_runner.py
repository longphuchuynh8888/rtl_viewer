# automation/script_runner.py
"""Chạy kịch bản tự động + hỗ trợ Human-in-the-loop"""

import time
import subprocess
import os
from automation.ui_parser import parse_ui_dump
from automation.learning.action_memory import ActionMemory
from automation.learning.template_matcher import TemplateMatcher
from automation.conditions import evaluate_step_conditions
class ScriptRunner:
    def __init__(self, worker):
        """
        worker: instance của ADBWorker
        """
        self.worker = worker
        self.memory = ActionMemory()
        self.matcher = TemplateMatcher()

    def find_and_tap(self, elements, mode, value, long=False):
        """Tìm phần tử và click. Trả về True nếu thành công."""
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

        for el in elements:
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
            worker.log(f"--- Lần chạy {count} ---")
    
            worker.dump_ui()
            time.sleep(0.5)
    
            data = worker.adb_out(
                ["exec-out", "cat", "/data/local/tmp/rtl_screens/window_dump.xml"],
                8
            )
            elements = parse_ui_dump(data.decode(errors="ignore")) if data else []
    
            for step in steps:
                if not worker.script_running:
                    break
    
                action = step.get("action")
                value = step.get("value", "")
                mode = step.get("mode", "coords")
    
                img = worker.get_screenshot()
                if not evaluate_step_conditions(
                    step, elements=elements, img=img, matcher=self.matcher
                ):
                    worker.log(f"⏭ Bỏ qua bước (điều kiện chưa thỏa): {value}")
                    continue
    
                if action in ("tap", "long_press"):
                    ok = self.find_and_tap(
                        elements, mode, value,
                        long=(action == "long_press")
                    )
                    if ok:
                        worker.log(f"✓ {action} ({mode}): {value}")
                    else:
                        worker.log(f"✗ Không tìm thấy: {value}")
                        reason = f"Không tìm thấy [{mode}] = {value}"
                        found = None
                        try:
                            found = self.matcher.find(img, reason=reason)
                        except Exception:
                            found = None
    
                        if found:
                            x, y, score = found
                            worker.tap(x, y)
                            worker.log(f"✓ Template match ({x},{y}) score={score:.2f}")
                        else:
                            size = img.size if img else None
                            sug = self.memory.suggest(reason, current_size=size)
                            if sug and sug[0] is not None:
                                worker.tap(sug[0], sug[1])
                                worker.log(f"✓ Dùng thao tác đã học ({sug[0]},{sug[1]})")
                            elif worker.help_enabled:
                                result = worker.request_help(reason)
                                if result is None or result == "stop":
                                    worker.script_running = False
                                    break
                                elif result == "skip":
                                    worker.log("⏭ Đã bỏ qua bước")
                                    continue
                                elif isinstance(result, tuple) and result[0] == "tap":
                                    _, x, y = result
                                    worker.tap(x, y)
                                    worker.log(f"✓ Người dùng chọn ({x},{y})")
                            else:
                                worker.log("⚠ Bỏ qua (tắt hỗ trợ)")
    
                elif action == "text":
                    worker.send_text(value, press_enter=step.get("enter", True))
    
                elif action == "key":
                    worker.adb(["shell", "input", "keyevent", value])
                    worker.log(f"✓ Key: {value}")
    
                elif action == "wait":
                    try:
                        time.sleep(float(value) / 1000.0)
                    except Exception:
                        time.sleep(0.5)
                elif action == "run_python":
                    path = step.get("value") or step.get("python_file")
                    if path and os.path.exists(path):
                        worker.log(f"▶ Chạy Python: {path}")
                        subprocess.run(["python", path], timeout=60)
                    else:
                        worker.log(f"✗ Không thấy file Python: {path}")
                elif action == "swipe":
                    parts = [p.strip() for p in str(value).split(",")]
                    if len(parts) >= 4:
                        dur = parts[4] if len(parts) > 4 else "300"
                        worker.adb(["shell", "input", "swipe", parts[0], parts[1], parts[2], parts[3], dur])
                        worker.log(f"✓ Swipe {value}")
                
                elif action == "launch":
                    worker.launch_app(value)
                elif action == "stop":
                    worker.force_stop_app(value)
                elif action == "uninstall":
                    worker.uninstall_app(value)
                elif action == "clear":
                    worker.clear_storage(value)
                elif action == "unlock":
                    worker.unlock_swipe_up()
                    worker.log("✓ Mở khóa")
                elif action == "rotate":
                    worker.rotate_screen(int(value or 0))
                    worker.log(f"✓ Xoay {value}")
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
        worker.log("✓ Kết thúc kịch bản")