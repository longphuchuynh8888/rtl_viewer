# main.py
"""Điểm khởi chạy Samsung RTL Viewer"""

import sys
import subprocess
from PyQt5.QtWidgets import QApplication, QMessageBox

from ui.main_window import MainWindow


def check_device() -> bool:
    try:
        out = subprocess.check_output(["adb", "devices"], timeout=5).decode()
        return any("\tdevice" in line for line in out.splitlines())
    except Exception:
        return False


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    if not check_device():
        QMessageBox.warning(
            None,
            "Cảnh báo ADB",
            "Không tìm thấy thiết bị ADB.\n"
            "Bạn vẫn có thể dùng các tính năng quản lý tài khoản / ứng dụng."
        )

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())