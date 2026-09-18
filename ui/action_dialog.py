# ui/action_dialog.py
"""Dialog thêm hành động vào kịch bản"""

import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QLineEdit, QDialogButtonBox,
    QFileDialog, QPushButton
)

from ui.screen_picker import ScreenPickerDialog


class ActionDialog(QDialog):
    def __init__(self, parent=None, packages=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm hành động")
        self.setMinimumWidth(480)
        self.packages = packages or []

        layout = QFormLayout(self)

        self.combo_action = QComboBox()
        items = [
            ("Tap tọa độ", "tap"),
            ("Long press", "long_press"),
            ("Vuốt (swipe)", "swipe"),
            ("Tìm ảnh mẫu (game)", "find_image"),
            ("Tìm chữ OCR (game)", "find_ocr"),
            ("Tìm màu", "find_color"),
            ("Phím Back", "key_back"),
            ("Phím Home", "key_home"),
            ("Phím Recent", "key_recent"),
            ("Phím Enter", "key_enter"),
            ("Phím Power", "key_power"),
            ("Mở ứng dụng", "launch"),
            ("Dừng ứng dụng", "stop"),
            ("Gỡ ứng dụng", "uninstall"),
            ("Clear Storage", "clear"),
            ("Gửi text", "text"),
            ("Đợi (ms)", "wait"),
            ("Mở khóa", "unlock"),
            ("Xoay Portrait", "rotate_0"),
            ("Xoay Landscape", "rotate_1"),
            ("Chạy file Python", "run_python"),
        ]
        for label, data in items:
            self.combo_action.addItem(label, data)
        layout.addRow("Hành động:", self.combo_action)

        self.combo_pkg = QComboBox()
        self.combo_pkg.setEditable(True)
        for p in self.packages:
            self.combo_pkg.addItem(p)
        layout.addRow("Package:", self.combo_pkg)

        self.value = QLineEdit()
        self.value.setPlaceholderText("tọa độ 540,120 | chữ OCR | RGB 255,255,255 | số ms")
        layout.addRow("Giá trị:", self.value)

        self.swipe = QLineEdit()
        self.swipe.setPlaceholderText("x1,y1,x2,y2,duration")
        layout.addRow("Swipe:", self.swipe)

        self.img_path = QLineEdit()
        btn_img = QPushButton("📁 Chọn ảnh mẫu từ máy")
        btn_img.clicked.connect(self._pick_image)
        btn_region = QPushButton("⬛ Chọn vùng trên màn hình thiết bị")
        btn_region.clicked.connect(self._pick_region_from_screen)
        layout.addRow("Ảnh mẫu:", self.img_path)
        layout.addRow(btn_img)
        layout.addRow(btn_region)

        self.py_path = QLineEdit()
        btn_py = QPushButton("Chọn file .py")
        btn_py.clicked.connect(self._pick_py)
        layout.addRow("File Python:", self.py_path)
        layout.addRow(btn_py)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _pick_py(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file Python", filter="Python (*.py)"
        )
        if path:
            self.py_path.setText(path)

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh mẫu",
            filter="Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.img_path.setText(path)
            self.value.setText(path)
            idx = self.combo_action.findData("find_image")
            if idx >= 0:
                self.combo_action.setCurrentIndex(idx)

    def _get_worker(self):
        parent = self.parent()
        if parent is None:
            return None
        if hasattr(parent, "main") and hasattr(parent.main, "worker"):
            return parent.main.worker
        if hasattr(parent, "worker"):
            return parent.worker
        return None

    def _pick_region_from_screen(self):
        worker = self._get_worker()
        img = worker.get_screenshot() if worker else None
        dlg = ScreenPickerDialog(self, img=img, mode="region")
        if dlg.exec_() != ScreenPickerDialog.Accepted:
            return

        region = dlg.get_region()
        x1, y1, x2, y2 = region["x1"], region["y1"], region["x2"], region["y2"]
        if x2 - x1 < 4 or y2 - y1 < 4:
            return

        src = dlg.img
        if src is None:
            return
        crop = src.crop((x1, y1, x2, y2))

        folder = "learned_templates"
        os.makedirs(folder, exist_ok=True)
        name = datetime.now().strftime("tpl_%Y%m%d_%H%M%S.jpg")
        path = os.path.join(folder, name)
        crop.save(path, "JPEG", quality=85)

        self.img_path.setText(path)
        self.value.setText(path)
        idx = self.combo_action.findData("find_image")
        if idx >= 0:
            self.combo_action.setCurrentIndex(idx)

    def get_step(self):
        act = self.combo_action.currentData()
        pkg = self.combo_pkg.currentText().strip()
        val = self.value.text().strip()

        if act in ("tap", "long_press"):
            return {"action": act, "mode": "coords", "value": val}
        if act == "swipe":
            return {"action": "swipe", "value": self.swipe.text().strip()}
        if act == "find_image":
            return {"action": "find_image", "value": self.img_path.text().strip() or val}
        if act == "find_ocr":
            return {"action": "find_ocr", "value": val}
        if act == "find_color":
            return {"action": "find_color", "value": val}
        if act.startswith("key_"):
            keys = {
                "key_back": "KEYCODE_BACK",
                "key_home": "KEYCODE_HOME",
                "key_recent": "KEYCODE_APP_SWITCH",
                "key_enter": "KEYCODE_ENTER",
                "key_power": "KEYCODE_POWER",
            }
            return {"action": "key", "value": keys[act]}
        if act in ("launch", "stop", "uninstall", "clear"):
            return {"action": act, "value": pkg}
        if act == "text":
            return {"action": "text", "value": val, "enter": True}
        if act == "wait":
            return {"action": "wait", "value": val or "800"}
        if act == "unlock":
            return {"action": "unlock"}
        if act == "rotate_0":
            return {"action": "rotate", "value": "0"}
        if act == "rotate_1":
            return {"action": "rotate", "value": "1"}
        if act == "run_python":
            return {"action": "run_python", "value": self.py_path.text().strip()}
        return {"action": "wait", "value": "200"}