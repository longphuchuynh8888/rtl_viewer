# ui/color_picker.py
"""Chọn màu từ ảnh màn hình, ảnh file, hoặc nhập tay"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QPixmap, QImage, QCursor, QColor
from PyQt5.QtCore import Qt
from PIL import Image

class ColorPickerDialog(QDialog):
    def __init__(self, parent=None, img=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn màu")
        self.setMinimumSize(720, 560)
        self.img = img
        self.scale = 1.0
        self.img_w = self.img_h = 1
        self.chosen_rgb = None
        self.chosen_xy = None

        layout = QVBoxLayout(self)

        hint = QLabel("Click vào ảnh để lấy màu. Hoặc nhập mã màu bên dưới.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.image_label = QLabel("Chưa có ảnh")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(280)
        self.image_label.setStyleSheet("background:#111; border:1px solid #444;")
        self.image_label.setCursor(QCursor(Qt.CrossCursor))
        self.image_label.mousePressEvent = self.on_click
        layout.addWidget(self.image_label, 1)

        row = QHBoxLayout()
        btn_screen = QPushButton("📷 Dùng ảnh màn hình")
        btn_screen.clicked.connect(self.use_screen)
        btn_file = QPushButton("🖼 Mở ảnh bất kỳ")
        btn_file.clicked.connect(self.open_file)
        row.addWidget(btn_screen)
        row.addWidget(btn_file)
        layout.addLayout(row)

        form = QHBoxLayout()
        form.addWidget(QLabel("Mã màu:"))
        self.color_edit = QLineEdit()
        self.color_edit.setPlaceholderText("#FFFFFF hoặc 255,255,255")
        form.addWidget(self.color_edit)
        btn_parse = QPushButton("Áp dụng mã")
        btn_parse.clicked.connect(self.apply_text)
        form.addWidget(btn_parse)
        layout.addLayout(form)

        self.preview = QLabel("Chưa chọn màu")
        self.preview.setMinimumHeight(36)
        self.preview.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview)

        self.coord_label = QLabel("Tọa độ: —")
        layout.addWidget(self.coord_label)

        btns = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept_color)
        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

        if img is not None:
            self.show_image(img)

    def show_image(self, img: Image.Image):
        self.img = img.convert("RGB")
        w, h = self.img.size
        self.img_w, self.img_h = w, h
        max_w, max_h = 860, 420
        self.scale = min(max_w / w, max_h / h, 1.0)
        nw, nh = max(1, int(w * self.scale)), max(1, int(h * self.scale))
        img2 = self.img.resize((nw, nh), Image.LANCZOS)
        data = img2.tobytes("raw", "RGB")
        qimg = QImage(data, nw, nh, nw * 3, QImage.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(qimg))

    def use_screen(self):
        parent = self.parent()
        img = None
        if parent is not None and hasattr(parent, "main"):
            worker = getattr(parent.main, "worker", None)
            if worker:
                img = worker.get_screenshot()
        elif parent is not None and hasattr(parent, "worker"):
            img = parent.worker.get_screenshot()
        if img is None:
            QMessageBox.information(self, "Thông báo", "Không lấy được ảnh màn hình")
            return
        self.show_image(img)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh", filter="Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return
        try:
            self.show_image(Image.open(path))
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", str(e))

    def on_click(self, event):
        if self.img is None:
            return
        pix = self.image_label.pixmap()
        if pix is None:
            return
        lw, lh = self.image_label.width(), self.image_label.height()
        nw, nh = pix.width(), pix.height()
        ox = (lw - nw) // 2
        oy = (lh - nh) // 2
        x = int((event.pos().x() - ox) / self.scale)
        y = int((event.pos().y() - oy) / self.scale)
        x = max(0, min(x, self.img_w - 1))
        y = max(0, min(y, self.img_h - 1))
        rgb = self.img.getpixel((x, y))
        self.set_color(rgb, (x, y))

    def apply_text(self):
        text = self.color_edit.text().strip()
        rgb = parse_color(text)
        if rgb is None:
            QMessageBox.information(self, "Thông báo", "Mã màu không hợp lệ")
            return
        self.set_color(rgb, None)

    def set_color(self, rgb, xy):
        self.chosen_rgb = tuple(int(v) for v in rgb[:3])
        self.chosen_xy = xy
        hex_code = "#{:02X}{:02X}{:02X}".format(*self.chosen_rgb)
        self.color_edit.setText(hex_code)
        self.preview.setText(f"{hex_code}  RGB{self.chosen_rgb}")
        self.preview.setStyleSheet(
            f"background: rgb{self.chosen_rgb}; color: {'#000' if sum(self.chosen_rgb)>400 else '#fff'};"
        )
        if xy:
            self.coord_label.setText(f"Tọa độ: ({xy[0]}, {xy[1]})")
        else:
            self.coord_label.setText("Tọa độ: — (nhập tay)")

    def accept_color(self):
        if self.chosen_rgb is None:
            rgb = parse_color(self.color_edit.text().strip())
            if rgb is None:
                QMessageBox.information(self, "Thông báo", "Chưa chọn màu")
                return
            self.chosen_rgb = rgb
        self.accept()

    def get_result(self):
        return {
            "rgb": list(self.chosen_rgb) if self.chosen_rgb else [255, 255, 255],
            "x": self.chosen_xy[0] if self.chosen_xy else 0,
            "y": self.chosen_xy[1] if self.chosen_xy else 0,
        }


def parse_color(text):
    if not text:
        return None
    text = text.strip()
    try:
        if text.startswith("#"):
            h = text[1:]
            if len(h) == 3:
                h = "".join(ch * 2 for ch in h)
            if len(h) != 6:
                return None
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        parts = [int(p.strip()) for p in text.replace(" ", "").split(",")]
        if len(parts) >= 3:
            return tuple(max(0, min(255, v)) for v in parts[:3])
    except Exception:
        return None
    return None