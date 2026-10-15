# ui/toolbar.py
"""Thanh tren: kenh, Function URL, may, serial."""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QComboBox, QInputDialog, QMessageBox
)
from PyQt5.QtWidgets import QApplication


class TopToolbar(QWidget):
    def __init__(self, main):
        super(TopToolbar, self).__init__()
        self.main = main
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.btn_toggle_screen = QPushButton("An/Hien man hinh")
        self.btn_toggle_screen.setCheckable(True)
        self.btn_toggle_screen.setChecked(True)
        self.btn_toggle_screen.clicked.connect(self.main.toggle_screen)
        layout.addWidget(self.btn_toggle_screen)

        layout.addWidget(QLabel("Kenh:"))
        self.combo_transport = QComboBox()
        self.combo_transport.addItem("ADB (1 may)", "adb")
        self.combo_transport.addItem("HTTP Hub", "http")
        self.combo_transport.addItem("AWS Lambda", "aws")
        self.combo_transport.addItem("Thu muc / Terabox", "folder")
        self.combo_transport.currentIndexChanged.connect(self.on_transport_changed)
        layout.addWidget(self.combo_transport)

        btn_http = QPushButton("Start HTTP + adb reverse")
        btn_http.clicked.connect(self.main.start_http_hub)
        layout.addWidget(btn_http)

        layout.addWidget(QLabel("Function URL:"))
        self.combo_aws_url = QComboBox()
        self.combo_aws_url.setMinimumWidth(200)
        self.combo_aws_url.currentIndexChanged.connect(self.on_url_chosen)
        layout.addWidget(self.combo_aws_url)

        btn_url_add = QPushButton("Them URL")
        btn_url_add.clicked.connect(self.add_aws_url)
        btn_url_edit = QPushButton("Sua URL")
        btn_url_edit.clicked.connect(self.edit_aws_url)
        btn_url_del = QPushButton("Xoa URL")
        btn_url_del.clicked.connect(self.delete_aws_url)
        layout.addWidget(btn_url_add)
        layout.addWidget(btn_url_edit)
        layout.addWidget(btn_url_del)

        layout.addWidget(QLabel("May:"))
        self.combo_device = QComboBox()
        self.combo_device.setMinimumWidth(220)
        self.combo_device.currentIndexChanged.connect(self.on_device_chosen)
        layout.addWidget(self.combo_device)

        btn_add_dev = QPushButton("Them serial")
        btn_add_dev.clicked.connect(self.add_device_manual)
        btn_copy = QPushButton("Chep serial")
        btn_copy.clicked.connect(self.copy_serial)
        layout.addWidget(btn_add_dev)
        layout.addWidget(btn_copy)
        layout.addStretch()

    # ----- device -----
    def reload_device_combo(self):
        current = self.main.aws_serial
        self.combo_device.blockSignals(True)
        self.combo_device.clear()
        for serial in self.main.device_store.serials():
            self.combo_device.addItem(self.main.device_store.label(serial), serial)
        self.combo_device.blockSignals(False)
        idx = self.combo_device.findData(current)
        if idx >= 0:
            self.combo_device.setCurrentIndex(idx)
        elif self.combo_device.count():
            self.on_device_chosen()

    def on_device_chosen(self):
        self.main.aws_serial = self.combo_device.currentData() or ""
        if self.main.aws_serial:
            self.main.append_log("Chon may: " + self.main.aws_serial)

    def add_device_manual(self):
        serial, ok = QInputDialog.getText(self, "Them may", "Serial:")
        if not ok or not (serial or "").strip():
            return
        name, ok2 = QInputDialog.getText(self, "Them may", "Ten may:", text=serial.strip())
        self.main.device_store.upsert(
            serial.strip(), name=(name.strip() if ok2 else serial.strip())
        )
        self.reload_device_combo()
        idx = self.combo_device.findData(serial.strip())
        if idx >= 0:
            self.combo_device.setCurrentIndex(idx)

    def copy_serial(self):
        serial = self.combo_device.currentData() or self.main.aws_serial or ""
        if not serial:
            self.main.append_log("Chua chon may")
            return
        QApplication.clipboard().setText(serial)
        self.main.append_log("Da chep serial: " + serial)

    # ----- URL -----
    def reload_url_combo(self):
        current = self.combo_aws_url.currentData()
        self.combo_aws_url.blockSignals(True)
        self.combo_aws_url.clear()
        for name in self.main.url_store.names():
            url = self.main.url_store.get(name)
            self.combo_aws_url.addItem("%s | %s" % (name, url[:32]), name)
        self.combo_aws_url.blockSignals(False)
        if current:
            idx = self.combo_aws_url.findData(current)
            if idx >= 0:
                self.combo_aws_url.setCurrentIndex(idx)
        self.on_url_chosen()

    def on_url_chosen(self):
        from core.aws_relay import AwsRelay
        name = self.combo_aws_url.currentData()
        url = self.main.url_store.get(name) if name else ""
        self.main.relay = AwsRelay(url)
        if url:
            self.main.append_log("URL: " + name)

    def add_aws_url(self):
        name, ok = QInputDialog.getText(self, "Them Function URL", "Ten:")
        if not ok or not name.strip():
            return
        url, ok2 = QInputDialog.getText(self, "Them Function URL", "URL:")
        if not ok2 or not url.strip():
            return
        self.main.url_store.upsert(name.strip(), url.strip())
        self.reload_url_combo()
        idx = self.combo_aws_url.findData(name.strip())
        if idx >= 0:
            self.combo_aws_url.setCurrentIndex(idx)

    def edit_aws_url(self):
        name = self.combo_aws_url.currentData()
        if not name:
            return
        url, ok = QInputDialog.getText(
            self, "Sua URL", "URL:", text=self.main.url_store.get(name)
        )
        if not ok:
            return
        new_name, ok2 = QInputDialog.getText(self, "Sua URL", "Ten:", text=name)
        if not ok2:
            return
        if new_name.strip() != name:
            self.main.url_store.delete(name)
        self.main.url_store.upsert(new_name.strip(), url.strip())
        self.reload_url_combo()

    def delete_aws_url(self):
        name = self.combo_aws_url.currentData()
        if not name:
            return
        if QMessageBox.question(self, "Xoa", "Xoa %s?" % name) != QMessageBox.Yes:
            return
        self.main.url_store.delete(name)
        self.reload_url_combo()

    # ----- transport -----
    def on_transport_changed(self):
        self.main.transport = self.combo_transport.currentData()
        self.main.append_log("Kenh: " + str(self.main.transport))
        if self.main.transport == "aws":
            self.main.apply_aws_settings()
        self.main.worker.skip_auto = self.main.transport in ("aws", "http")

    def apply_aws_settings(self):
        self.on_url_chosen()
        self.main.aws_serial = self.combo_device.currentData() or ""
