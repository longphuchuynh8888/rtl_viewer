# ui/tabs/app_tab.py
"""Tab quản lý Ứng dụng (cài đặt, Clear Storage/Cache...)"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QMessageBox, QFileDialog
)
import threading

from ui.dialogs import AppDialog
from utils.storage import load_json, save_json

APPS_FILE = "managed_apps.json"

class AppTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.worker = main_window.worker
        self.apps = load_json(APPS_FILE, [])
        self.current_app = None
        self._build_ui()
        self.reload()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.app_list = QListWidget()
        self.app_list.itemClicked.connect(self.on_selected)
        layout.addWidget(self.app_list)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("➕ Thêm")
        btn_add.clicked.connect(self.add)
        btn_edit = QPushButton("✏️ Sửa")
        btn_edit.clicked.connect(self.edit)
        btn_del = QPushButton("🗑 Xóa")
        btn_del.clicked.connect(self.delete)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_del)
        layout.addLayout(btn_row)

        self.detail = QLabel("Chọn ứng dụng")
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet("background:#1a1a1a; padding:8px;")
        layout.addWidget(self.detail)

        action_row = QHBoxLayout()
        btn_url = QPushButton("📦 Cài từ URL")
        btn_url.clicked.connect(self.install_url)
        btn_apk = QPushButton("📁 Cài từ APK")
        btn_apk.clicked.connect(self.install_apk)
        btn_store = QPushButton("🛒 Play Store")
        btn_store.clicked.connect(self.open_store)
        action_row.addWidget(btn_url)
        action_row.addWidget(btn_apk)
        action_row.addWidget(btn_store)
        layout.addLayout(action_row)

        clear_row = QHBoxLayout()
        btn_storage = QPushButton("🗑 Clear Storage")
        btn_storage.clicked.connect(self.clear_storage)
        btn_cache = QPushButton("🧹 Clear Cache")
        btn_cache.clicked.connect(self.clear_cache)
        clear_row.addWidget(btn_storage)
        clear_row.addWidget(btn_cache)
        layout.addLayout(clear_row)

        layout.addStretch()

    def reload(self):
        self.app_list.clear()
        for app in self.apps:
            self.app_list.addItem(app.get("name", "No name"))

    def on_selected(self, item):
        idx = self.app_list.currentRow()
        if idx < 0:
            return
        self.current_app = self.apps[idx]
        self.detail.setText(
            f"<b>Tên:</b> {self.current_app.get('name')}<br>"
            f"<b>Package:</b> {self.current_app.get('package') or '—'}<br>"
            f"<b>URL:</b> {self.current_app.get('url') or '—'}"
        )

    def add(self):
        dlg = AppDialog(self)
        if dlg.exec_() == AppDialog.Accepted:
            self.apps.append(dlg.get_data())
            save_json(APPS_FILE, self.apps)
            self.reload()
            self.main.append_log("✓ Đã thêm ứng dụng")

    def edit(self):
        idx = self.app_list.currentRow()
        if idx < 0:
            return
        dlg = AppDialog(self, self.apps[idx])
        if dlg.exec_() == AppDialog.Accepted:
            self.apps[idx] = dlg.get_data()
            save_json(APPS_FILE, self.apps)
            self.reload()
            self.main.append_log("✓ Đã cập nhật ứng dụng")

    def delete(self):
        idx = self.app_list.currentRow()
        if idx < 0:
            return
        if QMessageBox.question(self, "Xác nhận", "Xóa ứng dụng này?") == QMessageBox.Yes:
            self.apps.pop(idx)
            save_json(APPS_FILE, self.apps)
            self.reload()
            self.detail.setText("Chọn ứng dụng")

    def install_url(self):
        if not self.current_app:
            return
        url = self.current_app.get("url", "")
        if url:
            threading.Thread(
                target=self.worker.install_from_url, args=(url,), daemon=True
            ).start()
        else:
            QMessageBox.information(self, "Thông báo", "Chưa có URL")

    def install_apk(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file APK", filter="APK (*.apk)")
        if path:
            threading.Thread(
                target=self.worker.install_apk, args=(path,), daemon=True
            ).start()

    def open_store(self):
        if not self.current_app:
            return
        package = self.current_app.get("package", "")
        if package:
            self.worker.open_play_store(package)
        else:
            QMessageBox.information(self, "Thông báo", "Chưa có package")

    def clear_storage(self):
        if not self.current_app:
            QMessageBox.information(self, "Thông báo", "Hãy chọn ứng dụng")
            return
        package = self.current_app.get("package", "")
        if not package:
            QMessageBox.information(self, "Thông báo", "Chưa có package")
            return
        if QMessageBox.question(
            self, "Xác nhận",
            f"Clear Storage?\n{package}\nToàn bộ dữ liệu sẽ bị xóa!"
        ) == QMessageBox.Yes:
            threading.Thread(
                target=self.worker.clear_storage, args=(package,), daemon=True
            ).start()

    def clear_cache(self):
        if not self.current_app:
            QMessageBox.information(self, "Thông báo", "Hãy chọn ứng dụng")
            return
        package = self.current_app.get("package", "")
        if not package:
            QMessageBox.information(self, "Thông báo", "Chưa có package")
            return
        if QMessageBox.question(self, "Xác nhận", f"Clear Cache?\n{package}") == QMessageBox.Yes:
            threading.Thread(
                target=self.worker.clear_cache, args=(package,), daemon=True
            ).start()