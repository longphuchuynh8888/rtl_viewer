# ui/dialogs.py
"""Các dialog dùng chung"""

from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QComboBox, QPushButton, QFileDialog
)
from PyQt5.QtWidgets import QLineEdit as QL
from ui.color_picker import ColorPickerDialog
from ui.screen_picker import ScreenPickerDialog
class AccountDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Tài khoản Google")
        self.setMinimumWidth(420)
        layout = QFormLayout(self)

        self.username = QLineEdit(data.get("username", "") if data else "")
        self.password = QLineEdit(data.get("password", "") if data else "")
        self.password.setEchoMode(QL.Password)
        self.phone = QLineEdit(data.get("phone", "") if data else "")
        self.recovery_email = QLineEdit(data.get("recovery_email", "") if data else "")
        self.recovery_phone = QLineEdit(data.get("recovery_phone", "") if data else "")

        layout.addRow("Username:", self.username)
        layout.addRow("Password:", self.password)
        layout.addRow("Phone:", self.phone)
        layout.addRow("Recovery Email:", self.recovery_email)
        layout.addRow("Recovery Phone:", self.recovery_phone)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {
            "username": self.username.text().strip(),
            "password": self.password.text(),
            "phone": self.phone.text().strip(),
            "recovery_email": self.recovery_email.text().strip(),
            "recovery_phone": self.recovery_phone.text().strip(),
        }


class AppDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Ứng dụng")
        self.setMinimumWidth(420)
        layout = QFormLayout(self)

        self.name = QLineEdit(data.get("name", "") if data else "")
        self.package = QLineEdit(data.get("package", "") if data else "")
        self.url = QLineEdit(data.get("url", "") if data else "")

        layout.addRow("Tên:", self.name)
        layout.addRow("Package:", self.package)
        layout.addRow("URL:", self.url)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {
            "name": self.name.text().strip(),
            "package": self.package.text().strip(),
            "url": self.url.text().strip(),
        }

class ConditionDialog(QDialog):
    def __init__(self, parent=None, data=None, ui_elements=None):
        super().__init__(parent)
        self.setWindowTitle("Điều kiện")
        self.setMinimumWidth(460)
        self.ui_elements = ui_elements or []
        layout = QFormLayout(self)

        self.combo_type = QComboBox()
        self.combo_type.addItem("Có text", "text")
        self.combo_type.addItem("Có resource-id", "resource_id")
        self.combo_type.addItem("Có content-desc", "content_desc")
        self.combo_type.addItem("Màu tại điểm", "color")
        self.combo_type.addItem("Ảnh trong vùng", "region_image")
        self.combo_type.addItem("Chạy file Python", "run_python")
        layout.addRow("Loại:", self.combo_type)

        self.combo_op = QComboBox()
        self.combo_op.addItem("Tồn tại", "exists")
        self.combo_op.addItem("Không tồn tại", "not_exists")
        layout.addRow("Toán tử UI:", self.combo_op)

        self.combo_from_dump = QComboBox()
        self.combo_from_dump.setEditable(True)
        self._fill_dump_combo("text")
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        layout.addRow("Chọn từ dump:", self.combo_from_dump)

        self.value = QLineEdit()
        layout.addRow("Giá trị UI:", self.value)

        self.python_path = QLineEdit()
        btn_py = QPushButton("Chọn file .py")
        btn_py.clicked.connect(self._pick_python)
        layout.addRow("File Python:", self.python_path)
        layout.addRow(btn_py)

        self.x = QLineEdit("0")
        self.y = QLineEdit("0")
        self.rgb = QLineEdit("255,255,255")
        self.tol = QLineEdit("30")
        layout.addRow("X:", self.x)
        layout.addRow("Y:", self.y)
        layout.addRow("RGB:", self.rgb)
        layout.addRow("Tolerance:", self.tol)

        self.x1 = QLineEdit("0")
        self.y1 = QLineEdit("0")
        self.x2 = QLineEdit("100")
        self.y2 = QLineEdit("100")
        layout.addRow("X1:", self.x1)
        layout.addRow("Y1:", self.y1)
        layout.addRow("X2:", self.x2)
        layout.addRow("Y2:", self.y2)

        btn_pick_color = QPushButton("🎨 Chọn màu trên màn hình thiết bị")
        btn_pick_color.clicked.connect(self.pick_color)
        layout.addRow(btn_pick_color)
        btn_pick_region = QPushButton("⬛ Chọn vùng trên màn hình thiết bị")
        btn_pick_region.clicked.connect(self.pick_region)
        layout.addRow(btn_pick_region)

        if data:
            self._load(data)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.combo_from_dump.currentTextChanged.connect(self._sync_value)

    def _fill_dump_combo(self, field):
        self.combo_from_dump.clear()
        seen = set()
        for el in self.ui_elements:
            val = (el.get(field) or "").strip()
            if val and val not in seen:
                seen.add(val)
                self.combo_from_dump.addItem(val)

    def _on_type_changed(self):
        ctype = self.combo_type.currentData()
        if ctype in ("text", "resource_id", "content_desc"):
            self._fill_dump_combo(ctype)

    def _sync_value(self, text):
        if text:
            self.value.setText(text)

    def _pick_python(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file Python", filter="Python (*.py)")
        if path:
            self.python_path.setText(path)

    def pick_color(self):
        from ui.screen_picker import ScreenPickerDialog
        dlg = ScreenPickerDialog(self, mode="color")
        if dlg.exec_() == ScreenPickerDialog.Accepted:
            result = dlg.get_color()
            self.rgb.setText(",".join(str(v) for v in result["rgb"]))
            self.x.setText(str(result["x"]))
            self.y.setText(str(result["y"]))

    def pick_region(self):
        from ui.screen_picker import ScreenPickerDialog
        dlg = ScreenPickerDialog(self, mode="region")
        if dlg.exec_() == ScreenPickerDialog.Accepted:
            r = dlg.get_region()
            self.x1.setText(str(r["x1"]))
            self.y1.setText(str(r["y1"]))
            self.x2.setText(str(r["x2"]))
            self.y2.setText(str(r["y2"]))

    def _load(self, data):
        t = data.get("type", "text")
        idx = self.combo_type.findData(t)
        if idx >= 0:
            self.combo_type.setCurrentIndex(idx)
        self.value.setText(str(data.get("value", "")))
        self.python_path.setText(str(data.get("python_file", "")))

    def get_data(self):
        ctype = self.combo_type.currentData()
        cond = {"type": ctype}
        if ctype in ("text", "resource_id", "content_desc"):
            cond["value"] = self.value.text().strip() or self.combo_from_dump.currentText().strip()
            cond["op"] = self.combo_op.currentData()
        elif ctype == "color":
            rgb = [int(v.strip()) for v in self.rgb.text().split(",")[:3]]
            cond.update({
                "x": int(self.x.text() or 0),
                "y": int(self.y.text() or 0),
                "rgb": rgb,
                "tolerance": int(self.tol.text() or 30),
            })
        elif ctype == "region_image":
            cond.update({
                "x1": int(self.x1.text() or 0),
                "y1": int(self.y1.text() or 0),
                "x2": int(self.x2.text() or 0),
                "y2": int(self.y2.text() or 0),
            })
        elif ctype == "run_python":
            cond["python_file"] = self.python_path.text().strip()
        return cond