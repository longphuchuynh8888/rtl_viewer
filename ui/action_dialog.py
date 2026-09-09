# ui/action_dialog.py
"""Dialog thêm hành động vào kịch bản"""

from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QLineEdit, QDialogButtonBox,
    QFileDialog, QPushButton
)

class ActionDialog(QDialog):
    def __init__(self, parent=None, packages=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm hành động")
        self.setMinimumWidth(460)
        self.packages = packages or []

        layout = QFormLayout(self)

        self.combo_action = QComboBox()
        items = [
            ("Tap tọa độ", "tap"),
            ("Long press", "long_press"),
            ("Vuốt (swipe)", "swipe"),
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
        self.value.setPlaceholderText("tọa độ 540,120 hoặc text hoặc số ms")
        layout.addRow("Giá trị:", self.value)

        self.swipe = QLineEdit()
        self.swipe.setPlaceholderText("x1,y1,x2,y2,duration")
        layout.addRow("Swipe:", self.swipe)

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
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file Python", filter="Python (*.py)")
        if path:
            self.py_path.setText(path)

    def get_step(self):
        act = self.combo_action.currentData()
        pkg = self.combo_pkg.currentText().strip()
        val = self.value.text().strip()

        if act in ("tap", "long_press"):
            return {"action": act, "mode": "coords", "value": val}
        if act == "swipe":
            return {"action": "swipe", "value": self.swipe.text().strip()}
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