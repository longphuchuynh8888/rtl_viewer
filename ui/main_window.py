# ui/main_window.py
"""Cua so chinh"""

import subprocess
import threading
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QCheckBox, QSpinBox, QComboBox, QStatusBar, QTabWidget,
    QFileDialog, QInputDialog, QMessageBox, QSplitter, QTextEdit,
    QApplication
)
from PyQt5.QtCore import Qt, QTimer

from core.adb_worker import ADBWorker
from core.aws_relay import AwsRelay
from core.device_store import DeviceStore
from core.url_store import UrlStore
from core.http_hub import HubServer, HUB
from ui.screen_label import ScreenLabel
from ui.tabs.control_tab import ControlTab
from ui.tabs.account_tab import AccountTab
from ui.tabs.app_tab import AppTab
from ui.tabs.automation_tab import AutomationTab
from automation.human_loop import HelpDialog
from automation.learning.action_memory import ActionMemory


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
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
        self.relay = AwsRelay("")
        self.device_store = DeviceStore()
        self.url_store = UrlStore()
        self.transport = "adb"
        self.aws_serial = ""
        self.all_packages = []

        self.screen = ScreenLabel(self)
        self.control_tab = ControlTab(self)
        self.account_tab = AccountTab(self)
        self.app_tab = AppTab(self)
        self.automation_tab = AutomationTab(self)

        self._build_ui()
        self._connect_signals()
        self._start_loops()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)

        top = QHBoxLayout()
        self.btn_toggle_screen = QPushButton("An/Hien man hinh")
        self.btn_toggle_screen.setCheckable(True)
        self.btn_toggle_screen.setChecked(True)
        self.btn_toggle_screen.clicked.connect(self.toggle_screen)
        top.addWidget(self.btn_toggle_screen)

        top.addWidget(QLabel("Kenh:"))
        self.combo_transport = QComboBox()
        self.combo_transport.addItem("ADB (1 may)", "adb")
        self.combo_transport.addItem("HTTP Hub", "http")
        self.combo_transport.addItem("AWS Lambda", "aws")
        self.combo_transport.addItem("Thu muc / Terabox", "folder")
        self.combo_transport.currentIndexChanged.connect(self.on_transport_changed)
        top.addWidget(self.combo_transport)

        btn_http = QPushButton("Start HTTP + adb reverse")
        btn_http.clicked.connect(self.start_http_hub)
        top.addWidget(btn_http)

        top.addWidget(QLabel("Function URL:"))
        self.combo_aws_url = QComboBox()
        self.combo_aws_url.setMinimumWidth(200)
        self.combo_aws_url.currentIndexChanged.connect(self.on_url_chosen)
        top.addWidget(self.combo_aws_url)

        btn_url_add = QPushButton("Them URL")
        btn_url_add.clicked.connect(self.add_aws_url)
        btn_url_edit = QPushButton("Sua URL")
        btn_url_edit.clicked.connect(self.edit_aws_url)
        btn_url_del = QPushButton("Xoa URL")
        btn_url_del.clicked.connect(self.delete_aws_url)
        top.addWidget(btn_url_add)
        top.addWidget(btn_url_edit)
        top.addWidget(btn_url_del)

        top.addWidget(QLabel("May:"))
        self.combo_device = QComboBox()
        self.combo_device.setMinimumWidth(220)
        self.combo_device.currentIndexChanged.connect(self.on_device_chosen)
        top.addWidget(self.combo_device)

        btn_add_dev = QPushButton("Them serial")
        btn_add_dev.clicked.connect(self.add_device_manual)
        btn_copy = QPushButton("Chep serial")
        btn_copy.clicked.connect(self.copy_serial)
        top.addWidget(btn_add_dev)
        top.addWidget(btn_copy)
        top.addStretch()
        root.addLayout(top)

        self.splitter = QSplitter(Qt.Horizontal)
        self.screen_panel = QWidget()
        left = QVBoxLayout(self.screen_panel)
        left.setContentsMargins(0, 0, 0, 0)
        left.addWidget(self.screen, 1)

        quick = QHBoxLayout()
        btn_rf = QPushButton("Refresh")
        btn_rf.clicked.connect(self.manual_refresh)
        quick.addWidget(btn_rf)

        self.chk_auto = QCheckBox("Tu lam moi")
        self.chk_auto.setChecked(True)
        self.chk_auto.stateChanged.connect(
            lambda s: setattr(self.worker, "auto_refresh", bool(s))
        )
        quick.addWidget(self.chk_auto)

        quick.addWidget(QLabel("Giay:"))
        self.spin = QSpinBox()
        self.spin.setRange(1, 30)
        self.spin.setValue(2)
        self.spin.valueChanged.connect(
            lambda v: setattr(self.worker, "interval", float(v))
        )
        quick.addWidget(self.spin)

        quick.addWidget(QLabel("Chat luong:"))
        self.combo_quality = QComboBox()
        self.combo_quality.addItem("Cao", 1.0)
        self.combo_quality.addItem("Trung binh", 0.5)
        self.combo_quality.addItem("Thap", 0.3)
        self.combo_quality.setCurrentIndex(1)
        self.combo_quality.currentIndexChanged.connect(self.change_quality)
        quick.addWidget(self.combo_quality)
        quick.addStretch()
        left.addLayout(quick)

        keys = QHBoxLayout()
        for text, key in [
            ("Back", "KEYCODE_BACK"),
            ("Home", "KEYCODE_HOME"),
            ("Recent", "KEYCODE_APP_SWITCH"),
            ("Power", "KEYCODE_POWER"),
        ]:
            b = QPushButton(text)
            b.clicked.connect(lambda _, k=key: self.send_key(k))
            keys.addWidget(b)
        left.addLayout(keys)
        self.splitter.addWidget(self.screen_panel)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.control_tab, "Dieu khien")
        self.tabs.addTab(self.account_tab, "Tai khoan Google")
        self.tabs.addTab(self.app_tab, "Ung dung")
        self.tabs.addTab(self.automation_tab, "Tu dong hoa UI")
        self.splitter.addWidget(self.tabs)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        root.addWidget(self.splitter, 3)

        log_head = QHBoxLayout()
        log_head.addWidget(QLabel("Nhat ky"))
        btn_clear_log = QPushButton("Xoa log")
        btn_clear_log.clicked.connect(lambda: self.log.clear())
        log_head.addStretch()
        log_head.addWidget(btn_clear_log)
        root.addLayout(log_head)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(180)
        root.addWidget(self.log)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.reload_device_combo()
        self.reload_url_combo()

    def reload_device_combo(self):
        current = self.aws_serial
        self.combo_device.blockSignals(True)
        self.combo_device.clear()
        for serial in self.device_store.serials():
            self.combo_device.addItem(self.device_store.label(serial), serial)
        self.combo_device.blockSignals(False)
        idx = self.combo_device.findData(current)
        if idx >= 0:
            self.combo_device.setCurrentIndex(idx)
        elif self.combo_device.count():
            self.on_device_chosen()

    def reload_url_combo(self):
        current = self.combo_aws_url.currentData()
        self.combo_aws_url.blockSignals(True)
        self.combo_aws_url.clear()
        for name in self.url_store.names():
            url = self.url_store.get(name)
            self.combo_aws_url.addItem("%s | %s" % (name, url[:32]), name)
        self.combo_aws_url.blockSignals(False)
        if current:
            idx = self.combo_aws_url.findData(current)
            if idx >= 0:
                self.combo_aws_url.setCurrentIndex(idx)
        self.on_url_chosen()

    def on_device_chosen(self):
        self.aws_serial = self.combo_device.currentData() or ""
        if self.aws_serial:
            self.append_log("Chon may: " + self.aws_serial)

    def on_url_chosen(self):
        name = self.combo_aws_url.currentData()
        url = self.url_store.get(name) if name else ""
        self.relay = AwsRelay(url)
        if url:
            self.append_log("URL: " + name)

    def add_device_manual(self):
        serial, ok = QInputDialog.getText(self, "Them may", "Serial:")
        if not ok or not (serial or "").strip():
            return
        name, ok2 = QInputDialog.getText(self, "Them may", "Ten may:", text=serial.strip())
        self.device_store.upsert(serial.strip(), name=(name.strip() if ok2 else serial.strip()))
        self.reload_device_combo()
        idx = self.combo_device.findData(serial.strip())
        if idx >= 0:
            self.combo_device.setCurrentIndex(idx)

    def copy_serial(self):
        serial = self.combo_device.currentData() or self.aws_serial or ""
        if not serial:
            self.append_log("Chua chon may")
            return
        QApplication.clipboard().setText(serial)
        self.append_log("Da chep serial: " + serial)

    def add_aws_url(self):
        name, ok = QInputDialog.getText(self, "Them Function URL", "Ten:")
        if not ok or not name.strip():
            return
        url, ok2 = QInputDialog.getText(self, "Them Function URL", "URL:")
        if not ok2 or not url.strip():
            return
        self.url_store.upsert(name.strip(), url.strip())
        self.reload_url_combo()
        idx = self.combo_aws_url.findData(name.strip())
        if idx >= 0:
            self.combo_aws_url.setCurrentIndex(idx)

    def edit_aws_url(self):
        name = self.combo_aws_url.currentData()
        if not name:
            return
        url, ok = QInputDialog.getText(self, "Sua URL", "URL:", text=self.url_store.get(name))
        if not ok:
            return
        new_name, ok2 = QInputDialog.getText(self, "Sua URL", "Ten:", text=name)
        if not ok2:
            return
        if new_name.strip() != name:
            self.url_store.delete(name)
        self.url_store.upsert(new_name.strip(), url.strip())
        self.reload_url_combo()

    def delete_aws_url(self):
        name = self.combo_aws_url.currentData()
        if not name:
            return
        if QMessageBox.question(self, "Xoa", "Xoa %s?" % name) != QMessageBox.Yes:
            return
        self.url_store.delete(name)
        self.reload_url_combo()

    def apply_aws_settings(self):
        self.on_url_chosen()
        self.aws_serial = self.combo_device.currentData() or ""

    def on_transport_changed(self):
        self.transport = self.combo_transport.currentData()
        self.append_log("Kenh: " + str(self.transport))
        if self.transport == "aws":
            self.apply_aws_settings()

    def _connect_signals(self):
        self.worker.screenshot_ready.connect(self.on_new_frame)
        self.worker.status_message.connect(self.status.showMessage)
        self.worker.log_message.connect(self.append_log)
        self.worker.packages_ready.connect(self.fill_packages)
        self.worker.device_info_ready.connect(self.show_device_info)
        self.worker.screen_text_ready.connect(self.show_screen_text)
        self.worker.ui_elements_ready.connect(self.automation_tab.fill_elements)
        self.worker.need_help.connect(self.on_need_help)

    def _start_loops(self):
        threading.Thread(target=self.worker.start_loop, daemon=True).start()
        QTimer.singleShot(1000, self.manual_refresh)
        QTimer.singleShot(
            1800,
            lambda: threading.Thread(target=self.worker.get_device_info, daemon=True).start()
        )

    def toggle_screen(self):
        self.screen_panel.setVisible(self.btn_toggle_screen.isChecked())

    def on_need_help(self, img, reason):
        dlg = HelpDialog(img, reason, self, memory=self.memory)
        dlg.coordinate_chosen.connect(
            lambda x, y: self.worker.set_help_result(("tap", x, y))
        )
        dlg.skip_step.connect(lambda: self.worker.set_help_result("skip"))
        dlg.stop_script.connect(lambda: self.worker.set_help_result("stop"))
        dlg.exec_()

    def append_log(self, text):
        self.log.append("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), text))

    def show_device_info(self, info):
        serial = info.get("Serial") or ""
        name = ("%s %s" % (info.get("Manufacturer", ""), info.get("Model", ""))).strip()
        if serial:
            self.device_store.upsert(
                serial,
                name=name,
                country=info.get("Country", "-"),
                ip=info.get("Public IP", "-"),
            )
            self.reload_device_combo()
            idx = self.combo_device.findData(serial)
            if idx >= 0:
                self.combo_device.setCurrentIndex(idx)
        self.control_tab.info_label.setText(
            "<b>%s</b><br>Android: %s<br>Serial: %s<br>IP: %s | %s" % (
                name,
                info.get("Android", "-"),
                serial or "-",
                info.get("Public IP", "-"),
                info.get("Country", "-"),
            )
        )

    def show_screen_text(self, text):
        self.control_tab.screen_text_view.setPlainText(text)

    def reload_device_packages(self):
        self.worker.list_packages(self.control_tab.combo_pkg_type.currentData())

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
            if QMessageBox.question(self, "Xac nhan", "Go %s?" % pkg) == QMessageBox.Yes:
                self.worker.uninstall_app(pkg)
                QTimer.singleShot(1200, self.reload_device_packages)

    def do_push_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chon file")
        if path:
            threading.Thread(target=self.worker.push_file, args=(path,), daemon=True).start()

    def do_pull_file(self):
        remote, ok = QInputDialog.getText(self, "Lay file", "Duong dan:", text="/sdcard/Download/")
        if ok and remote:
            threading.Thread(target=self.worker.pull_file, args=(remote,), daemon=True).start()

    def change_quality(self):
        self.worker.quality = self.combo_quality.currentData()
        self.manual_refresh()

    def delayed_refresh(self):
        self.worker.force_next = True
        QTimer.singleShot(900, self.manual_refresh)

    def do_rotate(self, orientation):
        self.worker.rotate_screen(orientation)
        QTimer.singleShot(1300, self.manual_refresh)

    def on_new_frame(self, img):
        if img:
            self.screen.update_image(img)

    def manual_refresh(self):
        self.worker.force_next = True
        self.apply_aws_settings()

        def _do():
            img = None
            if self.transport == "aws":
                img = self.relay.get_shot(self.aws_serial)
            elif self.transport == "http":
                serials = HUB.serials()
                img = HUB.get_shot(serials[0]) if serials else None
            else:
                img = self.worker.get_screenshot_live()
            if img:
                self.worker.last_image = img.copy()
                self.worker.last_device_size = img.size
                self.worker.save_local(img)
                self.worker.screenshot_ready.emit(img)
            elif self.transport == "aws":
                self.worker.log_message.emit("AWS: khong tai duoc anh")

        threading.Thread(target=_do, daemon=True).start()

    def adb_cmd(self, args):
        try:
            subprocess.run(["adb"] + args, capture_output=True, timeout=6)
        except Exception:
            pass

    def send_tap(self, x, y):
        if self.transport == "aws":
            self.apply_aws_settings()
            ok = self.relay.push_cmd(
                self.aws_serial, {"action": "tap", "x": int(x), "y": int(y)}
            )
            self.append_log("AWS tap %s,%s %s" % (x, y, "ok" if ok else "fail"))
        elif self.transport == "http":
            serials = HUB.serials()
            if serials:
                HUB.push_cmd(serials[0], {"action": "tap", "x": int(x), "y": int(y)})
        else:
            self.adb_cmd(["shell", "input", "tap", str(int(x)), str(int(y))])
        self.delayed_refresh()

    def send_swipe(self, x1, y1, x2, y2, d=300):
        self.adb_cmd(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(d)])
        self.delayed_refresh()

    def send_long_press(self, x, y, d=900):
        self.adb_cmd(["shell", "input", "swipe", str(x), str(y), str(x), str(y), str(d)])
        self.delayed_refresh()

    def send_key(self, key):
        self.adb_cmd(["shell", "input", "keyevent", key])
        self.delayed_refresh()

    def start_http_hub(self):
        if not hasattr(self, "hub"):
            self.hub = HubServer(8765)
        self.hub.start()
        self.worker.adb(["reverse", "tcp:8765", "tcp:8765"])
        self.append_log("HTTP Hub :8765 + adb reverse")

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()