# ui/tabs/automation_tab.py
"""Tab Tự động hoá UI + Human-in-the-loop + nhiều kịch bản"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QLabel, QComboBox, QLineEdit, QListWidget, QListWidgetItem,
    QSpinBox, QCheckBox, QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt
import threading

from ui.dialogs import ConditionDialog
from ui.action_dialog import ActionDialog
from automation.script_store import ScriptStore


class AutomationTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.worker = main_window.worker
        self.ui_elements = []
        self.script_steps = []
        self.store = ScriptStore()
        self.current_script_name = None
        self._build_ui()
        self.reload_script_lib()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.chk_help = QCheckBox("Bật hỗ trợ khi kẹt (Human-in-the-loop)")
        self.chk_help.setChecked(True)
        self.chk_help.stateChanged.connect(
            lambda s: setattr(self.worker, "help_enabled", bool(s))
        )
        layout.addWidget(self.chk_help)
        engine_row = QHBoxLayout()
        engine_row.addWidget(QLabel("Công cụ nhận diện:"))
        self.combo_engine = QComboBox()
        self.combo_engine.addItem("UIAutomator (app thường)", "uiautomator")
        self.combo_engine.addItem("Hình ảnh / OCR (game)", "vision")
        engine_row.addWidget(self.combo_engine)
        layout.addLayout(engine_row)
		
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Chế độ click:"))
        self.combo_click_mode = QComboBox()
        self.combo_click_mode.addItem("Theo tọa độ (bounds)", "coords")
        self.combo_click_mode.addItem("Theo text", "text")
        self.combo_click_mode.addItem("Theo resource-id", "resource_id")
        self.combo_click_mode.addItem("Theo content-desc", "content_desc")
        mode_row.addWidget(self.combo_click_mode)
        layout.addLayout(mode_row)

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
        self.ui_list.setMaximumHeight(110)
        layout.addWidget(self.ui_list)

        ui_btn = QHBoxLayout()
        btn_click = QPushButton("👆 Click")
        btn_click.clicked.connect(self.click_selected)
        btn_long = QPushButton("👇 Long Press")
        btn_long.clicked.connect(self.long_selected)
        btn_add = QPushButton("➕ Thêm vào kịch bản")
        btn_add.clicked.connect(self.add_to_script)
        btn_add_action = QPushButton("➕ Thêm hành động")
        btn_add_action.clicked.connect(self.add_action)
        ui_btn.addWidget(btn_click)
        ui_btn.addWidget(btn_long)
        ui_btn.addWidget(btn_add)
        ui_btn.addWidget(btn_add_action)
        layout.addLayout(ui_btn)

        lib_box = QGroupBox("Danh sách kịch bản")
        ll = QVBoxLayout(lib_box)
        self.script_lib = QListWidget()
        self.script_lib.setMaximumHeight(90)
        self.script_lib.itemClicked.connect(self.on_script_selected)
        ll.addWidget(self.script_lib)

        lib_btn = QHBoxLayout()
        btn_new = QPushButton("➕ Mới")
        btn_new.clicked.connect(self.new_script)
        btn_rename = QPushButton("✏️ Đổi tên")
        btn_rename.clicked.connect(self.rename_script)
        btn_del_script = QPushButton("🗑 Xóa kịch bản")
        btn_del_script.clicked.connect(self.delete_script)
        lib_btn.addWidget(btn_new)
        lib_btn.addWidget(btn_rename)
        lib_btn.addWidget(btn_del_script)
        ll.addLayout(lib_btn)
        layout.addWidget(lib_box)

        script_box = QGroupBox("Các bước của kịch bản đang chọn")
        sb = QVBoxLayout(script_box)

        self.lbl_current = QLabel("Chưa chọn kịch bản")
        sb.addWidget(self.lbl_current)

        self.script_list = QListWidget()
        self.script_list.setMaximumHeight(110)
        self.script_list.itemClicked.connect(self.show_step_conditions)
        sb.addWidget(self.script_list)

        ctrl_row = QHBoxLayout()
        btn_del = QPushButton("🗑 Xóa bước")
        btn_del.clicked.connect(self.delete_step)
        btn_clear = QPushButton("Clear bước")
        btn_clear.clicked.connect(self.clear_script)
        btn_save = QPushButton("💾 Lưu")
        btn_save.clicked.connect(self.save_script)
        ctrl_row.addWidget(btn_del)
        ctrl_row.addWidget(btn_clear)
        ctrl_row.addWidget(btn_save)
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
        self.cond_list.setMaximumHeight(70)
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

        layout.addWidget(script_box)
        layout.addStretch()

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
        if not self._ensure_script():
            return
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
        self.script_steps.append({"action": "tap", "mode": mode, "value": value})
        self.refresh_script_list()
        self._persist_current()

    def add_action(self):
        if not self._ensure_script():
            return
        packages = getattr(self.main, "all_packages", [])
        dlg = ActionDialog(self, packages=packages)
        if dlg.exec_() == ActionDialog.Accepted:
            self.script_steps.append(dlg.get_step())
            self.refresh_script_list()
            self._persist_current()

    def refresh_script_list(self):
        self.script_list.clear()
        for i, s in enumerate(self.script_steps):
            self.script_list.addItem(
                f"{i+1}. {s.get('action')} ({s.get('mode', '')}) = {s.get('value', '')}"
            )
        name = self.current_script_name or "Chưa chọn kịch bản"
        self.lbl_current.setText(f"Đang chọn: {name}")

    def delete_step(self):
        row = self.script_list.currentRow()
        if row >= 0:
            self.script_steps.pop(row)
            self.refresh_script_list()
            self._persist_current()

    def clear_script(self):
        self.script_steps.clear()
        self.refresh_script_list()
        self._persist_current()

    def run_script(self):
        if not self.script_steps:
            QMessageBox.information(self, "Thông báo", "Kịch bản trống")
            return
        from automation.script_runner import ScriptRunner
        runner = ScriptRunner(self.worker)
        runner.engine = self.combo_engine.currentData()
        threading.Thread(
            target=runner.run,
            args=(self.script_steps, self.spin_loop.value(), self.spin_delay.value()),
            daemon=True
        ).start()
    def save_script(self):
        if not self._ensure_script():
            return
        self.store.put(self.current_script_name, self.script_steps)
        self.main.append_log(f"✓ Đã lưu: {self.current_script_name}")

    def reload_script_lib(self):
        self.script_lib.clear()
        for name in self.store.names():
            self.script_lib.addItem(name)

    def _persist_current(self):
        if self.current_script_name:
            self.store.put(self.current_script_name, self.script_steps)

    def _ensure_script(self):
        if self.current_script_name:
            return True
        QMessageBox.information(self, "Thông báo", "Hãy tạo hoặc chọn một kịch bản trước")
        return False

    def on_script_selected(self, item):
        self._persist_current()
        name = item.text()
        self.current_script_name = name
        self.script_steps = list(self.store.get(name) or [])
        self.refresh_script_list()
        self.cond_list.clear()
        self.main.append_log(f"Đang dùng kịch bản: {name}")

    def new_script(self):
        name, ok = QInputDialog.getText(self, "Kịch bản mới", "Tên:")
        name = (name or "").strip()
        if not ok or not name:
            return
        if name in self.store.names():
            QMessageBox.information(self, "Thông báo", "Tên đã tồn tại")
            return
        self._persist_current()
        self.current_script_name = name
        self.script_steps = []
        self.store.put(name, self.script_steps)
        self.reload_script_lib()
        self.refresh_script_list()

    def rename_script(self):
        if not self.current_script_name:
            return
        name, ok = QInputDialog.getText(
            self, "Đổi tên", "Tên mới:", text=self.current_script_name
        )
        name = (name or "").strip()
        if not ok or not name or name == self.current_script_name:
            return
        steps = self.script_steps
        self.store.delete(self.current_script_name)
        self.store.put(name, steps)
        self.current_script_name = name
        self.reload_script_lib()
        self.refresh_script_list()

    def delete_script(self):
        if not self.current_script_name:
            return
        if QMessageBox.question(
            self, "Xác nhận", f"Xóa kịch bản {self.current_script_name}?"
        ) != QMessageBox.Yes:
            return
        self.store.delete(self.current_script_name)
        self.current_script_name = None
        self.script_steps = []
        self.reload_script_lib()
        self.refresh_script_list()
        self.cond_list.clear()

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
        self._persist_current()

    def add_condition(self):
        row = self.script_list.currentRow()
        if row < 0:
            QMessageBox.information(self, "Thông báo", "Hãy chọn 1 bước kịch bản trước")
            return
        dlg = ConditionDialog(self, ui_elements=self.ui_elements)
        if dlg.exec_() == ConditionDialog.Accepted:
            self.script_steps[row].setdefault("conditions", []).append(dlg.get_data())
            self.show_step_conditions()
            self._persist_current()

    def delete_condition(self):
        row = self.script_list.currentRow()
        crow = self.cond_list.currentRow()
        if row < 0 or crow < 0:
            return
        self.script_steps[row]["conditions"].pop(crow)
        self.show_step_conditions()
        self._persist_current()