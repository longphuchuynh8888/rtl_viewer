# ui/main_window.py
"""Cửa sổ chính – kết nối tất cả tab và worker"""

import subprocess
import threading
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QCheckBox, QSpinBox, QComboBox, QStatusBar, QTabWidget,
    QFileDialog, QInputDialog, QMessageBox
)
from PyQt5.QtCore import QTimer

from core.adb_worker import ADBWorker
from ui.screen_label import ScreenLabel
from ui.tabs.control_tab import ControlTab
from ui.tabs.account_tab import AccountTab
from ui.tabs.app_tab import AppTab
from ui.tabs.automation_tab import AutomationTab
from automation.human_loop import HelpDialog
from automation.learning.action_memory import ActionMemory
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Samsung RTL Viewer - Modular")
        self.resize(1400, 960)

        self.setStyleSheet("""
            QMainWindow { background-color: #0d0d0d; }
            QGroupBox { color: #ddd; border: 1px solid #333; margin-top: 6px; padding-top: 8px; font-weight: bold; }
            QPushButton {
                background-color: #2c2c2c; color: white; border: 1px solid #444;
                border-radius: 5px; padding: 5px 9px;
            }
            QPushButton:hover { background-color: #3c3c3c; }
            QPushButton:pressed { background-color: #0a84ff; }
            QComboBox, QSpinBox, QCheckBox, QLineEdit, QTextEdit, QPlainTextEdit,
            QListWidget, QLabel, QTabWidget {
                background-color: #1e1e1e; color: #eee; border: 1px solid #444; padding: 3px;
            }
            QStatusBar { background-color: #151515; color: #bbb; }
            QTabBar::tab { background: #2a2a2a; color: #ccc; padding: 8px 12px; }
            QTabBar::tab:selected { background: #0a84ff; color: white; }
        """)
        self.memory = ActionMemory()
        self.worker = ADBWorker()
        self.all_packages = []

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        # ===== Cột trái: Màn hình =====
        left = QVBoxLayout()
        self.screen = ScreenLabel(self)
        left.addWidget(self.screen)

        quick = QHBoxLayout()
        btn_rf = QPushButton("🔄 Refresh")
        btn_rf.clicked.connect(self.manual_refresh)
        quick.addWidget(btn_rf)

        self.chk_auto = QCheckBox("Tự làm mới")
        self.chk_auto.setChecked(True)
        self.chk_auto.stateChanged.connect(
            lambda s: setattr(self.worker, "auto_refresh", bool(s))
        )
        quick.addWidget(self.chk_auto)

        quick.addWidget(QLabel("Giây:"))
        self.spin = QSpinBox()
        self.spin.setRange(1, 30)
        self.spin.setValue(2)
        self.spin.valueChanged.connect(
            lambda v: setattr(self.worker, "interval", float(v))
        )
        quick.addWidget(self.spin)

        quick.addWidget(QLabel("Chất lượng:"))
        self.combo_quality = QComboBox()
        self.combo_quality.addItem("Cao", 1.0)
        self.combo_quality.addItem("Trung bình", 0.5)
        self.combo_quality.addItem("Thấp", 0.3)
        self.combo_quality.setCurrentIndex(1)
        self.combo_quality.currentIndexChanged.connect(self.change_quality)
        quick.addWidget(self.combo_quality)
        quick.addStretch()
        left.addLayout(quick)

        keys = QHBoxLayout()
        for text, key in [
            ("◀ Back", "KEYCODE_BACK"),
            ("● Home", "KEYCODE_HOME"),
            ("■ Recent", "KEYCODE_APP_SWITCH"),
            ("⏻ Power", "KEYCODE_POWER"),
        ]:
            b = QPushButton(text)
            b.clicked.connect(lambda _, k=key: self.send_key(k))
            keys.addWidget(b)
        left.addLayout(keys)
        root.addLayout(left, 3)

        # ===== Cột phải: Tabs =====
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 2)

        self.control_tab = ControlTab(self)
        self.account_tab = AccountTab(self)
        self.app_tab = AppTab(self)
        self.automation_tab = AutomationTab(self)

        self.tabs.addTab(self.control_tab, "Điều khiển")
        self.tabs.addTab(self.account_tab, "Tài khoản Google")
        self.tabs.addTab(self.app_tab, "Ứng dụng")
        self.tabs.addTab(self.automation_tab, "Tự động hoá UI")

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Kết nối signal
        self.worker.screenshot_ready.connect(self.on_new_frame)
        self.worker.status_message.connect(self.status.showMessage)
        self.worker.log_message.connect(self.append_log)
        self.worker.packages_ready.connect(self.fill_packages)
        self.worker.device_info_ready.connect(self.show_device_info)
        self.worker.screen_text_ready.connect(self.show_screen_text)
        self.worker.ui_elements_ready.connect(self.automation_tab.fill_elements)
        self.worker.need_help.connect(self.on_need_help)

        # Khởi động vòng lặp ảnh
        threading.Thread(target=self.worker.start_loop, daemon=True).start()
        QTimer.singleShot(1000, self.manual_refresh)
        QTimer.singleShot(
            1800,
            lambda: threading.Thread(target=self.worker.get_device_info, daemon=True).start()
        )

    # ---------- Human-in-the-loop ----------
    def on_need_help(self, img, reason):
        dlg = HelpDialog(img, reason, self, memory=self.memory)
        dlg.coordinate_chosen.connect(
            lambda x, y: self.worker.set_help_result(("tap", x, y))
        )
        dlg.skip_step.connect(lambda: self.worker.set_help_result("skip"))
        dlg.stop_script.connect(lambda: self.worker.set_help_result("stop"))
        dlg.exec_()
    # ---------- Log & Info ----------
    def append_log(self, text):
        self.control_tab.log.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] {text}"
        )

    def show_device_info(self, info):
        self.control_tab.info_label.setText(
            f"<b>{info.get('Manufacturer', '')} {info.get('Model', '')}</b><br>"
            f"Android: {info.get('Android', '—')}<br>"
            f"Serial: {info.get('Serial', '—')}<br>"
            f"IP: {info.get('Public IP', '—')} | {info.get('Country', '—')}"
        )

    def show_screen_text(self, text):
        self.control_tab.screen_text_view.setPlainText(text)

    # ---------- Packages ----------
    def reload_device_packages(self):
        pkg_type = self.control_tab.combo_pkg_type.currentData()
        self.worker.list_packages(pkg_type)

    def fill_packages(self, packages):
        self.all_packages = packages
        self.filter_packages()

    def filter_packages(self):
        keyword = self.control_tab.pkg_search.text().strip().lower()
        self.control_tab.pkg_list.clear()
        for pkg in self.all_packages:
            if keyword in pkg.lower():
                self.control_tab.pkg_list.addItem(pkg)

    def do_launch(self):
        item = self.control_tab.pkg_list.currentItem()
        if item:
            self.worker.launch_app(item.text())
            self.delayed_refresh()

    def do_force_stop(self):
        item = self.control_tab.pkg_list.currentItem()
        if item:
            self.worker.force_stop_app(item.text())
            self.delayed_refresh()

    def do_uninstall(self):
        item = self.control_tab.pkg_list.currentItem()
        if item:
            pkg = item.text()
            if QMessageBox.question(self, "Xác nhận", f"Gỡ {pkg}?") == QMessageBox.Yes:
                self.worker.uninstall_app(pkg)
                QTimer.singleShot(1200, self.reload_device_packages)

    # ---------- File ----------
    def do_push_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file gửi lên thiết bị")
        if path:
            threading.Thread(
                target=self.worker.push_file, args=(path,), daemon=True
            ).start()

    def do_pull_file(self):
        remote, ok = QInputDialog.getText(
            self, "Lấy file", "Đường dẫn trên thiết bị:",
            text="/sdcard/Download/"
        )
        if ok and remote:
            threading.Thread(
                target=self.worker.pull_file, args=(remote,), daemon=True
            ).start()

    # ---------- Ảnh & Input ----------
    def change_quality(self):
        self.worker.quality = self.combo_quality.currentData()
        self.worker.force_next = True
        self.manual_refresh()

    def delayed_refresh(self):
        self.worker.force_next = True
        QTimer.singleShot(700, self.manual_refresh)

    def do_rotate(self, orientation):
        self.worker.rotate_screen(orientation)
        self.worker.force_next = True
        QTimer.singleShot(1300, self.manual_refresh)

    def on_new_frame(self, img):
        if img:
            self.screen.update_image(img)

    def manual_refresh(self):
        self.worker.force_next = True

        def _do():
            img = self.worker.get_screenshot()
            if img:
                self.worker.last_image = img.copy()
                self.worker.save_local(img)
                self.worker.screenshot_ready.emit(img)

        threading.Thread(target=_do, daemon=True).start()

    def adb_cmd(self, args):
        try:
            subprocess.run(["adb"] + args, capture_output=True, timeout=6)
        except Exception:
            pass

    def send_tap(self, x, y):
        self.adb_cmd(["shell", "input", "tap", str(x), str(y)])
        self.delayed_refresh()

    def send_swipe(self, x1, y1, x2, y2, d=300):
        self.adb_cmd(["shell", "input", "swipe",
                      str(x1), str(y1), str(x2), str(y2), str(d)])
        self.delayed_refresh()

    def send_long_press(self, x, y, d=900):
        self.adb_cmd(["shell", "input", "swipe",
                      str(x), str(y), str(x), str(y), str(d)])
        self.delayed_refresh()

    def send_key(self, key):
        self.adb_cmd(["shell", "input", "keyevent", key])
        self.delayed_refresh()

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()