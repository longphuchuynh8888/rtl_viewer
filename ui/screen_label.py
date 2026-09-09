# ui/screen_label.py
"""Widget hiển thị màn hình thiết bị + xử lý chuột"""

from PyQt5.QtWidgets import QLabel, QSizePolicy
from PyQt5.QtGui import QPixmap, QImage, QCursor
from PyQt5.QtCore import Qt, QTimer
from PIL import Image

class ScreenLabel(QLabel):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color:#111; border:2px solid #333;")
        self.setCursor(QCursor(Qt.CrossCursor))
        self.setMinimumSize(320, 400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.device_w = 1080
        self.device_h = 2340
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.press_pos = None
        self.is_dragging = False
        self.long_press_done = False

    def update_image(self, img: Image.Image):
        if not img:
            return
        self.device_w, self.device_h = img.size
        lw = max(self.width(), 1)
        lh = max(self.height(), 1)
        self.scale = min(lw / self.device_w, lh / self.device_h)
        nw = max(1, int(self.device_w * self.scale))
        nh = max(1, int(self.device_h * self.scale))

        img_resized = img.resize((nw, nh), Image.LANCZOS)
        data = img_resized.tobytes("raw", "RGB")
        qimg = QImage(data, nw, nh, nw * 3, QImage.Format_RGB888)
        self.setPixmap(QPixmap.fromImage(qimg))

        self.offset_x = (lw - nw) // 2
        self.offset_y = (lh - nh) // 2

    def map_to_device(self, pos):
        x = pos.x() - self.offset_x
        y = pos.y() - self.offset_y
        if (self.scale <= 0 or x < 0 or y < 0
                or x > self.device_w * self.scale
                or y > self.device_h * self.scale):
            return None
        return (
            max(0, min(int(x / self.scale), self.device_w - 1)),
            max(0, min(int(y / self.scale), self.device_h - 1))
        )

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.press_pos = e.pos()
            self.is_dragging = False
            self.long_press_done = False
            QTimer.singleShot(550, self._check_long_press)

    def _check_long_press(self):
        if self.press_pos and not self.is_dragging and not self.long_press_done:
            mapped = self.map_to_device(self.press_pos)
            if mapped:
                self.long_press_done = True
                self.main.send_long_press(*mapped)

    def mouseMoveEvent(self, e):
        if self.press_pos and (e.pos() - self.press_pos).manhattanLength() > 14:
            self.is_dragging = True

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or not self.press_pos:
            return
        start = self.map_to_device(self.press_pos)
        end = self.map_to_device(e.pos())
        self.press_pos = None

        if not start:
            return
        if self.long_press_done:
            return
        if self.is_dragging and end:
            self.main.send_swipe(*start, *end)
        else:
            self.main.send_tap(*start)

        self.is_dragging = False
        self.long_press_done = False