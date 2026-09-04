"""手动录入走法对话框：起点/终点/走子方（键盘录入；也可用棋盘点击录入）。"""
from __future__ import annotations

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox,
                               QFormLayout, QSpinBox, QVBoxLayout)

from core.piece import Side
from core.position import Position


class MoveInputDialog(QDialog):
    def __init__(self, parent, default_side: Side) -> None:
        super().__init__(parent)
        self.setWindowTitle("录入走法")
        form = QFormLayout(self)
        self.side_combo = QComboBox()
        self.side_combo.addItem("红方", Side.RED)
        self.side_combo.addItem("黑方", Side.BLACK)
        self.side_combo.setCurrentIndex(0 if default_side is Side.RED else 1)
        form.addRow("走子方", self.side_combo)

        def spin(vmin, vmax, val):
            s = QSpinBox()
            s.setRange(vmin, vmax)
            s.setValue(val)
            return s

        self.frm_r = spin(0, 9, 9)
        self.frm_c = spin(0, 8, 0)
        self.to_r = spin(0, 9, 8)
        self.to_c = spin(0, 8, 0)
        form.addRow("起点 行/列", self._pair(self.frm_r, self.frm_c))
        form.addRow("终点 行/列", self._pair(self.to_r, self.to_c))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    @staticmethod
    def _pair(a: QSpinBox, b: QSpinBox):
        from PySide6.QtWidgets import QHBoxLayout, QWidget
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(a)
        lay.addWidget(b)
        return w

    def values(self) -> tuple:
        return (self.side_combo.currentData(), Position(self.frm_r.value(), self.frm_c.value()),
                Position(self.to_r.value(), self.to_c.value()))