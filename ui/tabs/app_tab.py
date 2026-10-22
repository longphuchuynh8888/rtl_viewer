# ui/tabs/app_tab.py
"""Tab quan ly Ung dung + nut tuy chinh"""

import os
import threading
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QMessageBox, QFileDialog, QInputDialog, QGroupBox, QComboBox
)

from ui.dialogs import AppDialog
from utils.storage import load_json, save_json
from core.paths import ROOT

APPS_FILE = os.path.join(ROOT, "managed_apps.json")
BUTTONS_FILE = os.path.join(ROOT, "app_buttons.json")

ACTIONS = [
    ("install_url", "Cai tu URL"),
    ("install_apk", "Cai tu APK"),
    ("play_store", "Mo Play Store"),
    ("clear_storage", "Clear Storage"),
    ("clear_cache", "Clear Cache"),
    ("launch", "Mo app"),
    ("force_stop", "Dung app"),
    ("uninstall", "Go app"),
]


class AppTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.worker = main_window.worker
        self.apps = load_json(APPS_FILE, [])
        self.buttons = load_json(BUTTONS_FILE, {"global": [], "per_app": []})
        if "global" not in self.buttons:
            self.buttons = {"global": [], "per_app": []}
        self.current_app = None
        self._build_ui()
        self.reload()
        self.reload_buttons()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.app_list = QListWidget()
        self.app_list.itemClicked.connect(self.on_selected)
        layout.addWidget(self.app_list)

        btn_row = QHBoxLayout()
        for text, slot in [
            ("Them", self.add),
            ("Sua", self.edit),
            ("Xoa", self.delete),
        ]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        self.detail = QLabel("Chon ung dung")
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet("background:#1a1a1a; padding:8px;")
        layout.addWidget(self.detail)

        # Nut co dinh (giu nhu cu)
        action_row = QHBoxLayout()
        for text, slot in [
            ("Cai tu URL", self.install_url),
            ("Cai tu APK", self.install_apk),
            ("Play Store", self.open_store),
        ]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            action_row.addWidget(b)
        layout.addLayout(action_row)

        clear_row = QHBoxLayout()
        b1 = QPushButton("Clear Storage")
        b1.clicked.connect(self.clear_storage)
        b2 = QPushButton("Clear Cache")
        b2.clicked.connect(self.clear_cache)
        clear_row.addWidget(b1)
        clear_row.addWidget(b2)
        layout.addLayout(clear_row)

        # --- Nut tuy chinh ---
        box = QGroupBox("Nut tuy chinh")
        bl = QVBoxLayout(box)

        cfg = QHBoxLayout()
        self.combo_scope = QComboBox()
        self.combo_scope.addItem("Nut chung", "global")
        self.combo_scope.addItem("Nut theo app", "per_app")
        cfg.addWidget(self.combo_scope)

        self.combo_action = QComboBox()
        for key, label in ACTIONS:
            self.combo_action.addItem(label, key)
        cfg.addWidget(self.combo_action)

        btn_add_btn = QPushButton("Them nut")
        btn_add_btn.clicked.connect(self.add_button)
        btn_del_btn = QPushButton("Xoa nut dang chon")
        btn_del_btn.clicked.connect(self.delete_button)
        cfg.addWidget(btn_add_btn)
        cfg.addWidget(btn_del_btn)
        bl.addLayout(cfg)

        self.btn_list = QListWidget()
        self.btn_list.setMaximumHeight(80)
        bl.addWidget(self.btn_list)

        self.custom_btn_row = QHBoxLayout()
        bl.addLayout(self.custom_btn_row)
        layout.addWidget(box)
        layout.addStretch()

    def _save_buttons(self):
        save_json(BUTTONS_FILE, self.buttons)

    def reload_buttons(self):
        self.btn_list.clear()
        while self.custom_btn_row.count():
            item = self.custom_btn_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for scope in ("global", "per_app"):
            for btn in self.buttons.get(scope, []):
                label = "[Chung] %s" % btn["label"] if scope == "global" else "[App] %s" % btn["label"]
                self.btn_list.addItem("%s | %s" % (label, btn["action"]))

                b = QPushButton(btn["label"])
                b.setProperty("btn_id", btn["id"])
                b.setProperty("scope", scope)
                b.setProperty("action", btn["action"])
                b.clicked.connect(lambda _, a=btn["action"], s=scope: self.run_action(a, s))
                self.custom_btn_row.addWidget(b)

    def add_button(self):
        label, ok = QInputDialog.getText(self, "Them nut", "Ten nut:")
        if not ok or not (label or "").strip():
            return
        scope = self.combo_scope.currentData()
        action = self.combo_action.currentData()
        import uuid
        btn = {
            "id": str(uuid.uuid4())[:8],
            "label": label.strip(),
            "action": action,
        }
        self.buttons.setdefault(scope, []).append(btn)
        self._save_buttons()
        self.reload_buttons()
        self.main.append_log("Da them nut: %s (%s)" % (label, action))

    def delete_button(self):
        row = self.btn_list.currentRow()
        if row < 0:
            return
        # flatten order: global then per_app
        g = self.buttons.get("global", [])
        p = self.buttons.get("per_app", [])
        if row < len(g):
            g.pop(row)
        else:
            p.pop(row - len(g))
        self._save_buttons()
        self.reload_buttons()

    def run_action(self, action, scope):
        need_app = action != "install_apk"
        if need_app and scope == "per_app" and not self.current_app:
            QMessageBox.information(self, "Thong bao", "Hay chon ung dung truoc")
            return
        if need_app and not self.current_app and action != "install_apk":
            QMessageBox.information(self, "Thong bao", "Hay chon ung dung truoc")
            return

        if action == "install_url":
            self.install_url()
        elif action == "install_apk":
            self.install_apk()
        elif action == "play_store":
            self.open_store()
        elif action == "clear_storage":
            self.clear_storage()
        elif action == "clear_cache":
            self.clear_cache()
        elif action == "launch":
            pkg = (self.current_app or {}).get("package")
            if pkg:
                threading.Thread(target=self.worker.launch_app, args=(pkg,), daemon=True).start()
                self.main.delayed_refresh()
        elif action == "force_stop":
            pkg = (self.current_app or {}).get("package")
            if pkg:
                threading.Thread(target=self.worker.force_stop_app, args=(pkg,), daemon=True).start()
                self.main.delayed_refresh()
        elif action == "uninstall":
            pkg = (self.current_app or {}).get("package")
            if pkg and QMessageBox.question(self, "Xac nhan", "Go %s?" % pkg) == QMessageBox.Yes:
                threading.Thread(target=self.worker.uninstall_app, args=(pkg,), daemon=True).start()

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
            "<b>Ten:</b> %s<br><b>Package:</b> %s<br><b>URL:</b> %s" % (
                self.current_app.get("name"),
                self.current_app.get("package") or "-",
                self.current_app.get("url") or "-",
            )
        )

    def add(self):
        dlg = AppDialog(self)
        if dlg.exec_() == AppDialog.Accepted:
            self.apps.append(dlg.get_data())
            save_json(APPS_FILE, self.apps)
            self.reload()
            self.main.append_log("Da them ung dung")

    def edit(self):
        idx = self.app_list.currentRow()
        if idx < 0:
            return
        dlg = AppDialog(self, self.apps[idx])
        if dlg.exec_() == AppDialog.Accepted:
            self.apps[idx] = dlg.get_data()
            save_json(APPS_FILE, self.apps)
            self.reload()

    def delete(self):
        idx = self.app_list.currentRow()
        if idx < 0:
            return
        if QMessageBox.question(self, "Xac nhan", "Xoa ung dung nay?") == QMessageBox.Yes:
            self.apps.pop(idx)
            save_json(APPS_FILE, self.apps)
            self.reload()
            self.detail.setText("Chon ung dung")
            self.current_app = None

    def install_url(self):
        if not self.current_app:
            return
        url = self.current_app.get("url", "")
        if url:
            threading.Thread(target=self.worker.install_from_url, args=(url,), daemon=True).start()
        else:
            QMessageBox.information(self, "Thong bao", "Chua co URL")

    def install_apk(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chon file APK", filter="APK (*.apk)")
        if path:
            threading.Thread(target=self.worker.install_apk, args=(path,), daemon=True).start()

    def open_store(self):
        if not self.current_app:
            return
        package = self.current_app.get("package", "")
        if package:
            self.worker.open_play_store(package)
        else:
            QMessageBox.information(self, "Thong bao", "Chua co package")

    def clear_storage(self):
        if not self.current_app or not self.current_app.get("package"):
            QMessageBox.information(self, "Thong bao", "Hay chon ung dung co package")
            return
        package = self.current_app["package"]
        if QMessageBox.question(self, "Xac nhan", "Clear Storage?\n%s" % package) == QMessageBox.Yes:
            threading.Thread(target=self.worker.clear_storage, args=(package,), daemon=True).start()

    def clear_cache(self):
        if not self.current_app or not self.current_app.get("package"):
            QMessageBox.information(self, "Thong bao", "Hay chon ung dung co package")
            return
        package = self.current_app["package"]
        if QMessageBox.question(self, "Xac nhan", "Clear Cache?\n%s" % package) == QMessageBox.Yes:
            threading.Thread(target=self.worker.clear_cache, args=(package,), daemon=True).start()