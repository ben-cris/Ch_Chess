"""★ 揭示身份选择对话框（本项目核心交互）。

程序绝不自动猜测身份；候选按剩余子力过滤，用户必须选择或取消整个操作。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QGridLayout,
                               QLabel, QPushButton, QVBoxLayout)

from core.piece import PieceType, Side


class RevealPieceDialog(QDialog):
    def __init__(self, parent, side: Side, options: List[PieceType],
                 remaining: Optional[Dict[PieceType, int]] = None,
                 title: str = "请选择该棋子揭开后的真实身份") -> None:
        super().__init__(parent)
        self.setWindowTitle("揭示棋子身份")
        self._choice: Optional[PieceType] = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>{title}</b>"))
        layout.addWidget(QLabel(f"该棋子颜色：{side.label}"))
        grid = QGridLayout()
        remaining = remaining or {}
        for i, pt in enumerate(options):
            name = pt.display_name(side)
            text = f"{name}（{pt.notation_name(side)}）" if name != pt.notation_name(side) else name
            if remaining.get(pt, 0) > 0:
                text += f"  剩{remaining[pt]}"
            btn = QPushButton(text)
            btn.clicked.connect(lambda _=False, t=pt: self._pick(t))
            grid.addWidget(btn, i // 3, i % 3)
        layout.addLayout(grid)
        tip = QLabel("提示：请对照现实棋局选择。若不确定，请点“取消”后重新录入或编辑修正。")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        cancel = QDialogButtonBox(QDialogButtonBox.Cancel)
        cancel.rejected.connect(self.reject)
        layout.addWidget(cancel)

    def _pick(self, t: PieceType) -> None:
        self._choice = t
        self.accept()

    @property
    def selected_type(self) -> Optional[PieceType]:
        return self._choice