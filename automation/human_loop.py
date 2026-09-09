# automation/human_loop.py
"""Dialog hỗ trợ khi kịch bản bị kẹt + ghi nhớ thao tác"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
)
from PyQt5.QtGui import QPixmap, QImage, QCursor
from PyQt5.QtCore import Qt, pyqtSignal
from PIL import Image

from automation.learning.action_memory import ActionMemory
from automation.learning.template_matcher import TemplateMatcher

class HelpDialog(QDialog):
    coordinate_chosen = pyqtSignal(int, int)
    skip_step = pyqtSignal()
    stop_script = pyqtSignal()

    def __init__(self, img, reason="", parent=None, memory=None):
        super().__init__(parent)
        self.setWindowTitle("Cần hỗ trợ – Chọn vị trí click")
        self.setMinimumSize(720, 520)
        self.img = img
        self.reason = reason
        self.memory = memory or ActionMemory()
        self.chosen = None
        self.scale = 1.0
        self.img_w = self.img_h = 1
        self.matcher = TemplateMatcher()
        layout = QVBoxLayout(self)

        info = QLabel(
            f"<b>Kịch bản bị kẹt:</b> {reason}<br>"
            "Hãy click vào vị trí muốn nhấn trên ảnh bên dưới."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.suggest_label = QLabel("")
        self.suggest_label.setWordWrap(True)
        layout.addWidget(self.suggest_label)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background:#111; border:2px solid #0a84ff;")
        self.label.setCursor(QCursor(Qt.CrossCursor))
        self.label.mousePressEvent = self.on_click
        layout.addWidget(self.label, 1)

        self.coord_label = QLabel("Chưa chọn tọa độ")
        layout.addWidget(self.coord_label)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("✓ Gửi tọa độ & Tiếp tục")
        btn_ok.clicked.connect(self.accept_coord)
        btn_suggest = QPushButton("💡 Dùng gợi ý đã học")
        btn_suggest.clicked.connect(self.use_suggestion)
        btn_skip = QPushButton("⏭ Bỏ qua bước này")
        btn_skip.clicked.connect(self.do_skip)
        btn_stop = QPushButton("⏹ Dừng kịch bản")
        btn_stop.clicked.connect(self.do_stop)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_suggest)
        btn_row.addWidget(btn_skip)
        btn_row.addWidget(btn_stop)
        layout.addLayout(btn_row)

        if img:
            self.show_image(img)
        self.show_suggestion()

    def show_image(self, img: Image.Image):
        w, h = img.size
        max_w, max_h = 900, 600
        scale = min(max_w / w, max_h / h, 1.0)
        self.scale = scale
        self.img_w, self.img_h = w, h
        nw, nh = int(w * scale), int(h * scale)
        img2 = img.resize((nw, nh), Image.LANCZOS)
        data = img2.tobytes("raw", "RGB")
        qimg = QImage(data, nw, nh, nw * 3, QImage.Format_RGB888)
        self.label.setPixmap(QPixmap.fromImage(qimg))

    def show_suggestion(self):
        size = (self.img_w, self.img_h) if self.img else None
        sug = self.memory.suggest(self.reason, current_size=size)
        if sug and sug[0] is not None:
            self.suggested = sug
            self.suggest_label.setText(
                f"💡 Gợi ý từ thao tác đã học: ({sug[0]}, {sug[1]})"
            )
        else:
            self.suggested = None
            self.suggest_label.setText("Chưa có thao tác đã học cho tình huống này.")

    def on_click(self, event):
        pix = self.label.pixmap()
        if pix is None:
            return
        lw, lh = self.label.width(), self.label.height()
        nw, nh = pix.width(), pix.height()
        ox = (lw - nw) // 2
        oy = (lh - nh) // 2
        x = int((event.pos().x() - ox) / self.scale)
        y = int((event.pos().y() - oy) / self.scale)
        x = max(0, min(x, self.img_w - 1))
        y = max(0, min(y, self.img_h - 1))
        self.chosen = (x, y)
        self.coord_label.setText(f"Đã chọn: ({x}, {y})")

    def use_suggestion(self):
        if not getattr(self, "suggested", None):
            QMessageBox.information(self, "Thông báo", "Chưa có gợi ý")
            return
        self.chosen = self.suggested
        self.coord_label.setText(f"Đã chọn gợi ý: {self.chosen}")
        self.accept_coord()

    def accept_coord(self):
        if not self.chosen:
            QMessageBox.information(self, "Thông báo", "Hãy click vào ảnh để chọn tọa độ trước")
            return
        x, y = self.chosen
        try:
            self.memory.add(self.img, x, y, reason=self.reason)
            try:
                self.matcher.add_from_image(self.img, x, y, reason=self.reason)
            except Exception:
                pass
        except Exception:
            pass
        self.coordinate_chosen.emit(x, y)
        self.accept()

    def do_skip(self):
        self.skip_step.emit()
        self.reject()

    def do_stop(self):
        self.stop_script.emit()
        self.reject()