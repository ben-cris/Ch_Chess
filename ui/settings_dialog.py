"""设置对话框：引擎选择/路径/思考时间/深度 + 自动代走开关。"""
from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QSpinBox,
                               QVBoxLayout, QWidget)

from models.settings import AppSettings, EngineSettings


class SettingsDialog(QDialog):
    def __init__(self, parent, settings: AppSettings) -> None:
        super().__init__(parent)
        self.setWindowTitle("设置")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        eng = settings.engine

        self.engine_combo = QComboBox()
        for label, key in (("自动（推荐）：随包 Pikafish，没有则内置", "auto"),
                           ("内置搜索引擎", "builtin"),
                           ("Pikafish（外部，正常模式）", "pikafish"),
                           ("ElephantEye（外部，预留）", "elephant_eye"),
                           ("Mock（测试）", "mock")):
            self.engine_combo.addItem(label, key)
        idx = self.engine_combo.findData(eng.engine)
        self.engine_combo.setCurrentIndex(max(0, idx))
        form.addRow("分析引擎", self.engine_combo)

        self.path_edit = QLineEdit(eng.pikafish_path)
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.path_edit, 1)
        row.addWidget(browse)
        w = QWidget()
        w.setLayout(row)
        form.addRow("引擎路径", w)

        self.time_spin = QSpinBox()
        self.time_spin.setRange(100, 60000)
        self.time_spin.setSingleStep(100)
        self.time_spin.setValue(eng.time_limit_ms)
        self.time_spin.setSuffix(" ms")
        form.addRow("思考时间", self.time_spin)

        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(1, 64)
        self.depth_spin.setValue(eng.max_depth)
        form.addRow("搜索深度", self.depth_spin)
        layout.addLayout(form)

        self.chk_auto = QCheckBox("对家走完后，自动代走我方最优一步")
        self.chk_auto.setChecked(settings.auto_play)
        layout.addWidget(self.chk_auto)

        tip = QLabel("提示：自动模式会优先使用随包内置的 Pikafish 强引擎（engine/bin，可用 scripts/fetch_pikafish.ps1 下载），缺失或异常时自动退回内置引擎。外部引擎也可手动填写路径。")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择引擎程序", "", "可执行文件 (*.exe);;所有文件 (*)")
        if path:
            self.path_edit.setText(path)

    def engine_settings(self) -> EngineSettings:
        return EngineSettings(
            engine=self.engine_combo.currentData(),
            pikafish_path=self.path_edit.text().strip(),
            time_limit_ms=self.time_spin.value(),
            max_depth=self.depth_spin.value(),
        )

    def auto_play_enabled(self) -> bool:
        return self.chk_auto.isChecked()