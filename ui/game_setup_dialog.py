"""新建棋局对话框：模式 + 我执红/黑 + 揭棋规则预置。"""
from __future__ import annotations

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox,
                               QFormLayout, QGroupBox, QHBoxLayout,
                               QRadioButton, QVBoxLayout)

from core.game_state import GameMode
from core.piece import Side


class GameSetupDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新建棋局")
        layout = QVBoxLayout(self)

        mode_box = QGroupBox("游戏模式")
        ml = QHBoxLayout(mode_box)
        self.rb_normal = QRadioButton("正常玩法")
        self.rb_dark = QRadioButton("揭棋")
        self.rb_normal.setChecked(True)
        ml.addWidget(self.rb_normal)
        ml.addWidget(self.rb_dark)
        layout.addWidget(mode_box)

        side_box = QGroupBox("我执")
        sl = QHBoxLayout(side_box)
        self.rb_red = QRadioButton("红方")
        self.rb_black = QRadioButton("黑方")
        self.rb_red.setChecked(True)
        sl.addWidget(self.rb_red)
        sl.addWidget(self.rb_black)
        layout.addWidget(side_box)

        form = QFormLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("预置 A（默认）", "preset_a")
        form.addRow("揭棋规则预置", self.preset_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result(self) -> tuple:
        mode = GameMode.DARK if self.rb_dark.isChecked() else GameMode.NORMAL
        side = Side.BLACK if self.rb_black.isChecked() else Side.RED
        preset = self.preset_combo.currentData()
        return mode, side, preset