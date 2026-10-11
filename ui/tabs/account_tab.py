# ui/tabs/account_tab.py
"""Tab quan ly Tai khoan Google"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QGroupBox, QMessageBox, QFileDialog, QComboBox
)
from PyQt5.QtGui import QGuiApplication

from ui.dialogs import AccountDialog
from utils.crypto import encrypt_text, decrypt_text
from utils.storage import load_json, save_json
from core.paths import ACCOUNTS

ACCOUNTS_FILE = ACCOUNTS


class AccountTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.worker = main_window.worker
        self.accounts = load_json(ACCOUNTS_FILE, [])
        self.current_account = None
        self._build_ui()
        self.reload()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.acc_list = QListWidget()
        self.acc_list.itemClicked.connect(self.on_selected)
        layout.addWidget(self.acc_list)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("Them")
        btn_add.clicked.connect(self.add)
        btn_edit = QPushButton("Sua")
        btn_edit.clicked.connect(self.edit)
        btn_del = QPushButton("Xoa")
        btn_del.clicked.connect(self.delete)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_del)
        layout.addLayout(btn_row)

        self.detail = QLabel("Chon tai khoan")
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet("background:#1a1a1a; padding:8px;")
        layout.addWidget(self.detail)

        mode_box = QGroupBox("Cach gui text")
        ml = QVBoxLayout(mode_box)
        self.combo_send_mode = QComboBox()
        self.combo_send_mode.addItem("Tu dong (mat khau = tung ky tu)", "auto")
        self.combo_send_mode.addItem("ADB input text", "input")
        self.combo_send_mode.addItem("Tung ky tu", "char")
        self.combo_send_mode.addItem("ADB Keyboard (broadcast)", "adbkeyboard")
        ml.addWidget(self.combo_send_mode)

        kb_row = QHBoxLayout()
        btn_install_kb = QPushButton("Cai ADB Keyboard")
        btn_install_kb.clicked.connect(self.install_keyboard)
        btn_on_kb = QPushButton("Bat ADB Keyboard")
        btn_on_kb.clicked.connect(lambda: self.worker.enable_adb_keyboard())
        btn_off_kb = QPushButton("Tra ban phim mac dinh")
        btn_off_kb.clicked.connect(lambda: self.worker.disable_adb_keyboard())
        kb_row.addWidget(btn_install_kb)
        kb_row.addWidget(btn_on_kb)
        kb_row.addWidget(btn_off_kb)
        ml.addLayout(kb_row)
        layout.addWidget(mode_box)

        send_box = QGroupBox("Gui / Sao chep")
        sb = QVBoxLayout(send_box)
        for field, label in [
            ("username", "Username"),
            ("password", "Password"),
            ("phone", "Phone"),
            ("recovery_email", "Recovery Email"),
            ("recovery_phone", "Recovery Phone"),
        ]:
            row = QHBoxLayout()
            btn_send = QPushButton("Gui %s" % label)
            btn_send.clicked.connect(lambda _, f=field: self.send_field(f))
            btn_copy = QPushButton("Copy")
            btn_copy.setFixedWidth(50)
            btn_copy.clicked.connect(lambda _, f=field: self.copy_field(f))
            row.addWidget(btn_send)
            row.addWidget(btn_copy)
            sb.addLayout(row)
        layout.addWidget(send_box)
        layout.addStretch()

    def reload(self):
        self.acc_list.clear()
        for acc in self.accounts:
            self.acc_list.addItem(acc.get("username", "No name"))

    def on_selected(self, item):
        idx = self.acc_list.currentRow()
        if idx < 0:
            return
        self.current_account = self.accounts[idx]
        pwd = decrypt_text(self.current_account.get("password", ""))
        self.detail.setText(
            "<b>Username:</b> %s<br>"
            "<b>Password:</b> %s<br>"
            "<b>Phone:</b> %s<br>"
            "<b>Recovery Email:</b> %s<br>"
            "<b>Recovery Phone:</b> %s" % (
                self.current_account.get("username"),
                ("*" * len(pwd)) if pwd else "-",
                self.current_account.get("phone") or "-",
                self.current_account.get("recovery_email") or "-",
                self.current_account.get("recovery_phone") or "-",
            )
        )

    def add(self):
        dlg = AccountDialog(self)
        if dlg.exec_() == AccountDialog.Accepted:
            data = dlg.get_data()
            data["password"] = encrypt_text(data["password"])
            self.accounts.append(data)
            save_json(ACCOUNTS_FILE, self.accounts)
            self.reload()
            self.main.append_log("Da them tai khoan")

    def edit(self):
        idx = self.acc_list.currentRow()
        if idx < 0:
            return
        data = self.accounts[idx].copy()
        data["password"] = decrypt_text(data.get("password", ""))
        dlg = AccountDialog(self, data)
        if dlg.exec_() == AccountDialog.Accepted:
            new_data = dlg.get_data()
            new_data["password"] = encrypt_text(new_data["password"])
            self.accounts[idx] = new_data
            save_json(ACCOUNTS_FILE, self.accounts)
            self.reload()
            self.main.append_log("Da cap nhat tai khoan")

    def delete(self):
        idx = self.acc_list.currentRow()
        if idx < 0:
            return
        if QMessageBox.question(self, "Xac nhan", "Xoa tai khoan nay?") == QMessageBox.Yes:
            self.accounts.pop(idx)
            save_json(ACCOUNTS_FILE, self.accounts)
            self.reload()
            self.detail.setText("Chon tai khoan")
            self.main.append_log("Da xoa tai khoan")

    def send_field(self, field):
        if not self.current_account:
            return
        value = self.current_account.get(field, "")
        if field == "password":
            value = decrypt_text(value)
        if not value:
            return
        mode = self.combo_send_mode.currentData()
        self.worker.send_text(
            value,
            press_enter=True,
            mode=mode,
            is_password=(field == "password"),
        )
        self.main.delayed_refresh()

    def copy_field(self, field):
        if not self.current_account:
            return
        value = self.current_account.get(field, "")
        if field == "password":
            value = decrypt_text(value)
        if value:
            QGuiApplication.clipboard().setText(value)
            self.main.status.showMessage("Da sao chep %s" % field, 2000)

    def install_keyboard(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chon ADBKeyboard.apk", filter="APK (*.apk)"
        )
        if path:
            self.worker.install_adb_keyboard(path)

    def list_accounts(self):
        return list(self.accounts)

    def get_field(self, account_id, field):
        for acc in self.accounts:
            if acc.get("username") == account_id or acc.get("id") == account_id:
                value = acc.get(field) or ""
                if field == "password":
                    return decrypt_text(value)
                return value
        return ""
