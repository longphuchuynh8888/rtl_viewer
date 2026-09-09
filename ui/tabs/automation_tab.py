# ui/tabs/automation_tab.py
"""Tab Tự động hoá UI + Human-in-the-loop + Kịch bản"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QLabel, QComboBox, QLineEdit, QListWidget, QListWidgetItem,
    QSpinBox, QCheckBox, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt
import threading
import os

from utils.storage import load_json, save_json
from ui.dialogs import ConditionDialog
from ui.action_dialog import ActionDialog
SCRIPT_DIR = "ui_scripts"
os.makedirs(SCRIPT_DIR, exist_ok=True)

class AutomationTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.worker = main_window.worker
        self.ui_elements = []
        self.script_steps = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Bật/tắt Human-in-the-loop
        self.chk_help = QCheckBox("Bật hỗ trợ khi kẹt (Human-in-the-loop)")
        self.chk_help.setChecked(True)
        self.chk_help.stateChanged.connect(
            lambda s: setattr(self.worker, "help_enabled", bool(s))
        )
        layout.addWidget(self.chk_help)

        # Chế độ click
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Chế độ click:"))
        self.combo_click_mode = QComboBox()
        self.combo_click_mode.addItem("Theo tọa độ (bounds)", "coords")
        self.combo_click_mode.addItem("Theo text", "text")
        self.combo_click_mode.addItem("Theo resource-id", "resource_id")
        self.combo_click_mode.addItem("Theo content-desc", "content_desc")
        mode_row.addWidget(self.combo_click_mode)
        layout.addLayout(mode_row)

        # Dump UI
        btn_dump = QPushButton("📥 Dump UI Hierarchy")
        btn_dump.clicked.connect(
            lambda: threading.Thread(target=self.worker.dump_ui, daemon=True).start()
        )
        layout.addWidget(btn_dump)

        self.ui_search = QLineEdit()
        self.ui_search.setPlaceholderText("Tìm phần tử...")
        self.ui_search.textChanged.connect(self.filter_elements)
        layout.addWidget(self.ui_search)

        self.ui_list = QListWidget()
        self.ui_list.setMaximumHeight(140)
        layout.addWidget(self.ui_list)

        ui_btn = QHBoxLayout()
        btn_click = QPushButton("👆 Click")
        btn_click.clicked.connect(self.click_selected)
        btn_long = QPushButton("👇 Long Press")
        btn_long.clicked.connect(self.long_selected)
        btn_add = QPushButton("➕ Thêm vào kịch bản")
        btn_add.clicked.connect(self.add_to_script)
        ui_btn.addWidget(btn_click)
        ui_btn.addWidget(btn_long)
        ui_btn.addWidget(btn_add)
        layout.addLayout(ui_btn)

        # Kịch bản
        script_box = QGroupBox("Kịch bản hành động")
        sb = QVBoxLayout(script_box)

        self.script_list = QListWidget()
        self.script_list.setMaximumHeight(120)
        sb.addWidget(self.script_list)

        ctrl_row = QHBoxLayout()
        btn_del = QPushButton("🗑 Xóa bước")
        btn_del.clicked.connect(self.delete_step)
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.clear_script)
        ctrl_row.addWidget(btn_del)
        ctrl_row.addWidget(btn_clear)
        sb.addLayout(ctrl_row)

        run_row = QHBoxLayout()
        run_row.addWidget(QLabel("Lặp:"))
        self.spin_loop = QSpinBox()
        self.spin_loop.setRange(0, 999)
        self.spin_loop.setValue(1)
        self.spin_loop.setSpecialValueText("∞")
        run_row.addWidget(self.spin_loop)
        run_row.addWidget(QLabel("Delay (ms):"))
        self.spin_delay = QSpinBox()
        self.spin_delay.setRange(100, 10000)
        self.spin_delay.setValue(800)
        run_row.addWidget(self.spin_delay)
        sb.addLayout(run_row)

        run_btn = QHBoxLayout()
        btn_run = QPushButton("▶ Chạy kịch bản")
        btn_run.clicked.connect(self.run_script)
        btn_stop = QPushButton("⏹ Dừng")
        btn_stop.clicked.connect(lambda: setattr(self.worker, "script_running", False))
        run_btn.addWidget(btn_run)
        run_btn.addWidget(btn_stop)
        sb.addLayout(run_btn)

        save_row = QHBoxLayout()
        btn_save = QPushButton("💾 Lưu kịch bản")
        btn_save.clicked.connect(self.save_script)
        btn_load = QPushButton("📂 Tải kịch bản")
        btn_load.clicked.connect(self.load_script)
        save_row.addWidget(btn_save)
        save_row.addWidget(btn_load)
        sb.addLayout(save_row)

        layout.addWidget(script_box)
        layout.addStretch()
        cond_box = QGroupBox("Điều kiện của bước đang chọn")
        cl = QVBoxLayout(cond_box)
        
        logic_row = QHBoxLayout()
        logic_row.addWidget(QLabel("Kết hợp:"))
        self.combo_logic = QComboBox()
        self.combo_logic.addItem("AND (tất cả đúng)", "AND")
        self.combo_logic.addItem("OR (một cái đúng)", "OR")
        self.combo_logic.currentIndexChanged.connect(self.update_step_logic)
        logic_row.addWidget(self.combo_logic)
        cl.addLayout(logic_row)
        
        self.cond_list = QListWidget()
        self.cond_list.setMaximumHeight(80)
        cl.addWidget(self.cond_list)
        
        cond_btn = QHBoxLayout()
        btn_add_cond = QPushButton("➕ Thêm điều kiện")
        btn_add_cond.clicked.connect(self.add_condition)
        btn_del_cond = QPushButton("🗑 Xóa điều kiện")
        btn_del_cond.clicked.connect(self.delete_condition)
        cond_btn.addWidget(btn_add_cond)
        cond_btn.addWidget(btn_del_cond)
        cl.addLayout(cond_btn)
        
        sb.addWidget(cond_box)
        self.script_list.itemClicked.connect(self.show_step_conditions)
        btn_add_action = QPushButton("➕ Thêm hành động")
        btn_add_action.clicked.connect(self.add_action)
        ui_btn.addWidget(btn_add_action)

    # ---------- UI Elements ----------
    def fill_elements(self, elements):
        self.ui_elements = elements
        self.filter_elements()

    def filter_elements(self):
        keyword = self.ui_search.text().strip().lower()
        self.ui_list.clear()
        for el in self.ui_elements:
            label = f"[{el['cx']},{el['cy']}] "
            if el.get("text"):
                label += f"text=\"{el['text'][:40]}\" "
            if el.get("resource_id"):
                label += f"id={el['resource_id'].split('/')[-1]} "
            if el.get("content_desc"):
                label += f"desc=\"{el['content_desc'][:30]}\""
            if keyword in label.lower():
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, el)
                self.ui_list.addItem(item)

    def click_selected(self):
        item = self.ui_list.currentItem()
        if not item:
            return
        el = item.data(Qt.UserRole)
        self.worker.tap(el["cx"], el["cy"])
        self.main.delayed_refresh()

    def long_selected(self):
        item = self.ui_list.currentItem()
        if not item:
            return
        el = item.data(Qt.UserRole)
        self.worker.long_press(el["cx"], el["cy"])
        self.main.delayed_refresh()

    def add_to_script(self):
        item = self.ui_list.currentItem()
        if not item:
            return
        el = item.data(Qt.UserRole)
        mode = self.combo_click_mode.currentData()

        if mode == "coords":
            value = f"{el['cx']},{el['cy']}"
        elif mode == "text":
            value = el.get("text", "")
        elif mode == "resource_id":
            value = el.get("resource_id", "")
        else:
            value = el.get("content_desc", "")

        if not value:
            QMessageBox.information(self, "Thông báo", f"Phần tử không có {mode}")
            return

        self.script_steps.append({
            "action": "tap",
            "mode": mode,
            "value": value
        })
        self.refresh_script_list()

    # ---------- Script ----------
    def refresh_script_list(self):
        self.script_list.clear()
        for i, s in enumerate(self.script_steps):
            self.script_list.addItem(
                f"{i+1}. {s['action']} ({s.get('mode', '')}) = {s.get('value', '')}"
            )

    def delete_step(self):
        row = self.script_list.currentRow()
        if row >= 0:
            self.script_steps.pop(row)
            self.refresh_script_list()

    def clear_script(self):
        self.script_steps.clear()
        self.refresh_script_list()

    def run_script(self):
        if not self.script_steps:
            QMessageBox.information(self, "Thông báo", "Kịch bản trống")
            return
        from automation.script_runner import ScriptRunner
        runner = ScriptRunner(self.worker)
        loop = self.spin_loop.value()
        delay = self.spin_delay.value()
        threading.Thread(
            target=runner.run,
            args=(self.script_steps, loop, delay),
            daemon=True
        ).start()

    def save_script(self):
        if not self.script_steps:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Lưu kịch bản", SCRIPT_DIR, "JSON (*.json)"
        )
        if path:
            save_json(path, self.script_steps)
            self.main.append_log(f"✓ Đã lưu: {os.path.basename(path)}")

    def load_script(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Tải kịch bản", SCRIPT_DIR, "JSON (*.json)"
        )
        if path:
            self.script_steps = load_json(path, [])
            self.refresh_script_list()
            self.main.append_log(f"✓ Đã tải: {os.path.basename(path)}")
    def show_step_conditions(self):
        row = self.script_list.currentRow()
        self.cond_list.clear()
        if row < 0 or row >= len(self.script_steps):
            return
        step = self.script_steps[row]
        logic = step.get("logic", "AND")
        idx = self.combo_logic.findData(logic)
        if idx >= 0:
            self.combo_logic.setCurrentIndex(idx)
        for c in step.get("conditions", []):
            self.cond_list.addItem(str(c))
    
    def update_step_logic(self):
        row = self.script_list.currentRow()
        if row < 0:
            return
        self.script_steps[row]["logic"] = self.combo_logic.currentData()
    
    def add_condition(self):
        row = self.script_list.currentRow()
        if row < 0:
            QMessageBox.information(self, "Thông báo", "Hãy chọn 1 bước kịch bản trước")
            return
        dlg = ConditionDialog(self, ui_elements=self.ui_elements)
        if dlg.exec_() == ConditionDialog.Accepted:
            cond = dlg.get_data()
            self.script_steps[row].setdefault("conditions", []).append(cond)
            self.show_step_conditions()
    
    def delete_condition(self):
        row = self.script_list.currentRow()
        crow = self.cond_list.currentRow()
        if row < 0 or crow < 0:
            return
        self.script_steps[row]["conditions"].pop(crow)
        self.show_step_conditions()
    def add_action(self):
        packages = getattr(self.main, "all_packages", [])
        dlg = ActionDialog(self, packages=packages)
        if dlg.exec_() == ActionDialog.Accepted:
            self.script_steps.append(dlg.get_step())
            self.refresh_script_list()