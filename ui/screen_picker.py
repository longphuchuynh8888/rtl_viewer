# ui/screen_picker.py
"""Chọn màu / vùng trực tiếp trên ảnh màn hình thiết bị Android"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
)
from PyQt5.QtGui import QPixmap, QImage, QCursor, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect, QPoint
from PIL import Image

class ScreenPickerDialog(QDialog):
    def __init__(self, parent=None, img=None, mode="color"):
        """
        mode: "color"  → click 1 điểm
              "region" → kéo chọn vùng
        """
        super().__init__(parent)
        self.setWindowTitle("Chọn trên màn hình thiết bị")
        self.setMinimumSize(760, 600)
        self.img = None
        self.mode = mode
        self.scale = 1.0
        self.offset_x = self.offset_y = 0
        self.img_w = self.img_h = 1
        self.chosen_rgb = None
        self.chosen_xy = None
        self.region = None
        self.drag_start = None
        self.drag_end = None

        layout = QVBoxLayout(self)
        self.hint = QLabel(
            "Click một điểm để lấy màu." if mode == "color"
            else "Kéo chuột trên ảnh để chọn vùng."
        )
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        self.image_label = QLabel("Đang tải ảnh thiết bị...")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(360)
        self.image_label.setStyleSheet("background:#111; border:2px solid #0a84ff;")
        self.image_label.setCursor(QCursor(Qt.CrossCursor))
        self.image_label.mousePressEvent = self.on_press
        self.image_label.mouseMoveEvent = self.on_move
        self.image_label.mouseReleaseEvent = self.on_release
        layout.addWidget(self.image_label, 1)

        self.info = QLabel("Chưa chọn")
        layout.addWidget(self.info)

        row = QHBoxLayout()
        btn_reload = QPushButton("🔄 Lấy lại ảnh thiết bị")
        btn_reload.clicked.connect(self.load_from_device)
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept_choice)
        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)
        row.addWidget(btn_reload)
        row.addWidget(btn_ok)
        row.addWidget(btn_cancel)
        layout.addLayout(row)

        if img is not None:
            self.show_image(img)
        else:
            self.load_from_device()

    def _get_worker(self):
        parent = self.parent()
        if parent is None:
            return None
        if hasattr(parent, "main") and hasattr(parent.main, "worker"):
            return parent.main.worker
        if hasattr(parent, "worker"):
            return parent.worker
        return None

    def load_from_device(self):
        worker = self._get_worker()
        if worker is None:
            QMessageBox.information(self, "Thông báo", "Không kết nối được worker")
            return
        img = worker.get_screenshot()
        if img is None:
            QMessageBox.information(self, "Thông báo", "Không lấy được ảnh thiết bị")
            return
        self.show_image(img)

    def show_image(self, img: Image.Image):
        self.img = img.convert("RGB")
        self.img_w, self.img_h = self.img.size
        self._redraw()

    def _redraw(self, extra_rect=None):
        if self.img is None:
            return
        lw = max(self.image_label.width(), 400)
        lh = max(self.image_label.height(), 280)
        self.scale = min(lw / self.img_w, lh / self.img_h, 1.0)
        nw = max(1, int(self.img_w * self.scale))
        nh = max(1, int(self.img_h * self.scale))
        img2 = self.img.resize((nw, nh), Image.LANCZOS)
        data = img2.tobytes("raw", "RGB")
        qimg = QImage(data, nw, nh, nw * 3, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        if extra_rect:
            painter = QPainter(pix)
            painter.setPen(QPen(QColor(10, 132, 255), 2))
            painter.drawRect(extra_rect)
            painter.end()
        self.image_label.setPixmap(pix)
        self.offset_x = (self.image_label.width() - nw) // 2
        self.offset_y = (self.image_label.height() - nh) // 2

    def map_to_image(self, pos):
        if self.img is None or self.scale <= 0:
            return None
        pix = self.image_label.pixmap()
        if pix is None:
            return None
        ox = (self.image_label.width() - pix.width()) // 2
        oy = (self.image_label.height() - pix.height()) // 2
        x = int((pos.x() - ox) / self.scale)
        y = int((pos.y() - oy) / self.scale)
        if x < 0 or y < 0 or x >= self.img_w or y >= self.img_h:
            return None
        return x, y

    def on_press(self, event):
        mapped = self.map_to_image(event.pos())
        if not mapped:
            return
        if self.mode == "color":
            x, y = mapped
            rgb = self.img.getpixel((x, y))
            self.chosen_xy = (x, y)
            self.chosen_rgb = rgb
            hex_code = "#{:02X}{:02X}{:02X}".format(*rgb)
            self.info.setText(f"Màu {hex_code} RGB{rgb} tại ({x}, {y})")
        else:
            self.drag_start = event.pos()
            self.drag_end = event.pos()

    def on_move(self, event):
        if self.mode != "region" or self.drag_start is None:
            return
        self.drag_end = event.pos()
        rect = QRect(self.drag_start, self.drag_end).normalized()
        pix = self.image_label.pixmap()
        if pix is None:
            return
        ox = (self.image_label.width() - pix.width()) // 2
        oy = (self.image_label.height() - pix.height()) // 2
        r = QRect(rect.x() - ox, rect.y() - oy, rect.width(), rect.height())
        self._redraw(extra_rect=r)

    def on_release(self, event):
        if self.mode != "region" or self.drag_start is None:
            return
        p1 = self.map_to_image(self.drag_start)
        p2 = self.map_to_image(event.pos())
        self.drag_start = None
        if not p1 or not p2:
            return
        x1, y1 = min(p1[0], p2[0]), min(p1[1], p2[1])
        x2, y2 = max(p1[0], p2[0]), max(p1[1], p2[1])
        if x2 - x1 < 4 or y2 - y1 < 4:
            return
        self.region = (x1, y1, x2, y2)
        self.info.setText(f"Vùng [{x1},{y1}] → [{x2},{y2}]")

    def accept_choice(self):
        if self.mode == "color" and self.chosen_rgb is None:
            QMessageBox.information(self, "Thông báo", "Hãy click một điểm trên ảnh")
            return
        if self.mode == "region" and self.region is None:
            QMessageBox.information(self, "Thông báo", "Hãy kéo chuột để chọn vùng")
            return
        self.accept()

    def get_color(self):
        return {
            "rgb": list(self.chosen_rgb) if self.chosen_rgb else [255, 255, 255],
            "x": self.chosen_xy[0] if self.chosen_xy else 0,
            "y": self.chosen_xy[1] if self.chosen_xy else 0,
        }

    def get_region(self):
        if not self.region:
            return {"x1": 0, "y1": 0, "x2": 0, "y2": 0}
        x1, y1, x2, y2 = self.region
        return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}