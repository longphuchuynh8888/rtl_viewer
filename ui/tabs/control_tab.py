# ui/tabs/control_tab.py
"""Tab Điều khiển: Service, file, xoay, danh sách app trên thiết bị..."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QLabel, QComboBox, QLineEdit, QListWidget, QTextEdit, QPlainTextEdit
)
from PyQt5.QtCore import QTimer
import threading

class ControlTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.worker = main_window.worker
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Thông tin thiết bị
        info_box = QGroupBox("Thông tin thiết bị")
        il = QVBoxLayout(info_box)
        self.info_label = QLabel("Đang tải...")
        self.info_label.setWordWrap(True)
        il.addWidget(self.info_label)
        layout.addWidget(info_box)

        # Chế độ lấy ảnh
        mode_box = QGroupBox("Chế độ lấy ảnh")
        ml = QVBoxLayout(mode_box)
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("Device Service (Khuyên dùng)", "service")
        self.combo_mode.addItem("ADB Direct", "adb")
        self.combo_mode.currentIndexChanged.connect(self._change_mode)
        ml.addWidget(self.combo_mode)
        layout.addWidget(mode_box)

        # Service
        svc_box = QGroupBox("Service")
        sl = QVBoxLayout(svc_box)
        btn_install = QPushButton("📦 Cài đặt Service")
        btn_install.clicked.connect(lambda: self.worker.install_service())
        sl.addWidget(btn_install)
        row = QHBoxLayout()
        btn_start = QPushButton("▶ Start")
        btn_start.clicked.connect(lambda: (
            self.worker.start_service(),
            QTimer.singleShot(1000, self.worker.check_service)
        ))
        btn_stop = QPushButton("⏹ Stop")
        btn_stop.clicked.connect(lambda: self.worker.stop_service())
        row.addWidget(btn_start)
        row.addWidget(btn_stop)
        sl.addLayout(row)
        layout.addWidget(svc_box)

        # Nội dung màn hình (text)
        text_box = QGroupBox("Nội dung màn hình")
        tl = QVBoxLayout(text_box)
        btn_text = QPushButton("📄 Xem nội dung màn hình")
        btn_text.clicked.connect(
            lambda: threading.Thread(target=self.worker.get_screen_text, daemon=True).start()
        )
        tl.addWidget(btn_text)
        self.screen_text_view = QPlainTextEdit()
        self.screen_text_view.setReadOnly(True)
        self.screen_text_view.setMaximumHeight(80)
        self.screen_text_view.setPlaceholderText("Nội dung text sẽ hiện ở đây...")
        tl.addWidget(self.screen_text_view)
        layout.addWidget(text_box)

        # Gửi / Lấy file
        file_box = QGroupBox("Gửi / Lấy file")
        fl = QVBoxLayout(file_box)
        row_f = QHBoxLayout()
        btn_push = QPushButton("📤 Gửi file")
        btn_push.clicked.connect(self.main.do_push_file)
        btn_pull = QPushButton("📥 Lấy file")
        btn_pull.clicked.connect(self.main.do_pull_file)
        row_f.addWidget(btn_push)
        row_f.addWidget(btn_pull)
        fl.addLayout(row_f)
        layout.addWidget(file_box)

        # Xoay & Mở khóa
        orient_box = QGroupBox("Xoay & Mở khóa")
        ol = QVBoxLayout(orient_box)
        r = QHBoxLayout()
        for text, val in [("Portrait", 0), ("Landscape", 1)]:
            b = QPushButton(text)
            b.clicked.connect(lambda _, v=val: self.main.do_rotate(v))
            r.addWidget(b)
        ol.addLayout(r)
        btn_unlock = QPushButton("🔓 Mở khóa")
        btn_unlock.clicked.connect(
            lambda: (self.worker.unlock_swipe_up(), self.main.delayed_refresh())
        )
        ol.addWidget(btn_unlock)
        layout.addWidget(orient_box)

        # Ứng dụng trên thiết bị
        pkg_box = QGroupBox("Ứng dụng trên thiết bị")
        pl = QVBoxLayout(pkg_box)

        self.combo_pkg_type = QComboBox()
        self.combo_pkg_type.addItem("Tất cả ứng dụng", "all")
        self.combo_pkg_type.addItem("Chỉ ứng dụng người dùng", "user")
        pl.addWidget(self.combo_pkg_type)

        self.pkg_search = QLineEdit()
        self.pkg_search.setPlaceholderText("Tìm kiếm package...")
        self.pkg_search.textChanged.connect(self.main.filter_packages)
        pl.addWidget(self.pkg_search)

        btn_reload = QPushButton("🔄 Tải danh sách")
        btn_reload.clicked.connect(self.main.reload_device_packages)
        pl.addWidget(btn_reload)

        self.pkg_list = QListWidget()
        self.pkg_list.setMaximumHeight(100)
        pl.addWidget(self.pkg_list)

        pkg_btn = QHBoxLayout()
        btn_run = QPushButton("▶ Chạy")
        btn_run.clicked.connect(self.main.do_launch)
        btn_stop = QPushButton("⏹ Dừng")
        btn_stop.clicked.connect(self.main.do_force_stop)
        btn_uninstall = QPushButton("🗑 Gỡ")
        btn_uninstall.clicked.connect(self.main.do_uninstall)
        pkg_btn.addWidget(btn_run)
        pkg_btn.addWidget(btn_stop)
        pkg_btn.addWidget(btn_uninstall)
        pl.addLayout(pkg_btn)
        layout.addWidget(pkg_box)

        # Nhật ký
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(90)
        layout.addWidget(self.log)

        layout.addStretch()

    def _change_mode(self):
        self.worker.mode = self.combo_mode.currentData()
        self.main.append_log(f"Chế độ: {self.worker.mode}")