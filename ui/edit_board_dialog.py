"""编辑棋局对话框：删除/改身份/设暗子/新增棋子/改回合/重置。"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox,
                               QFormLayout, QHBoxLayout, QLabel, QPushButton,
                               QSpinBox, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from core.piece import Piece, PieceType, Side
from core.position import Position
from services.game_service import GameService


class EditBoardDialog(QDialog):
    def __init__(self, parent, service: GameService) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑棋局")
        self.service = service
        self._rows: List[Position] = []
        self.resize(600, 520)
        layout = QVBoxLayout(self)

        tip = QLabel("提示：编辑仅用于修正“现实棋局与程序不一致”的情况，会记录到撤销栈。")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["坐标(行,列)", "颜色", "类型", "状态", "棋子名"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        row = QHBoxLayout()
        btn_del = QPushButton("删除所选")
        btn_del.clicked.connect(self._delete)
        btn_hide = QPushButton("设为暗子")
        btn_hide.clicked.connect(self._to_unknown)
        btn_type = QPushButton("设为身份…")
        btn_type.clicked.connect(self._set_type)
        row.addWidget(btn_del)
        row.addWidget(btn_hide)
        row.addWidget(btn_type)
        layout.addLayout(row)

        form = QFormLayout()
        self.new_side = QComboBox()
        self.new_side.addItem("红方", Side.RED)
        self.new_side.addItem("黑方", Side.BLACK)
        self.new_type = QComboBox()
        for pt in (PieceType.ROOK, PieceType.CANNON, PieceType.HORSE,
                   PieceType.ELEPHANT, PieceType.ADVISOR, PieceType.GENERAL, PieceType.PAWN):
            self.new_type.addItem(pt.notation_name(Side.RED), pt)
        self.r_spin = QSpinBox(); self.r_spin.setRange(0, 9)
        self.c_spin = QSpinBox(); self.c_spin.setRange(0, 8)
        self.btn_add = QPushButton("新增明子")
        self.btn_add.clicked.connect(self._add)
        place = QHBoxLayout()
        place.addWidget(QLabel("行"))
        place.addWidget(self.r_spin)
        place.addWidget(QLabel("列"))
        place.addWidget(self.c_spin)
        place.addWidget(self.btn_add)
        form.addRow("放置新子", place)
        form.addRow("颜色", self.new_side)
        form.addRow("类型", self.new_type)
        layout.addLayout(form)

        self.turn_combo = QComboBox()
        self.turn_combo.addItem("红方走", Side.RED)
        self.turn_combo.addItem("黑方走", Side.BLACK)
        idx = 0 if service.current().turn is Side.RED else 1
        self.turn_combo.setCurrentIndex(idx)
        layout.addWidget(self.turn_combo)

        self.btn_reset = QPushButton("重置棋盘（恢复当前模式初始布局）")
        self.btn_reset.clicked.connect(self._reset)
        layout.addWidget(self.btn_reset)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("完成")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh()

    # ---------- helpers ----------
    def _selected_pos(self) -> Optional[Position]:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        idx = rows[0].row()
        if 0 <= idx < len(self._rows):
            return self._rows[idx]
        return None

    def _refresh(self) -> None:
        st = self.service.current()
        pieces = sorted(st.board.pieces(), key=lambda p: (p.position.row, p.position.col))
        self._rows = [p.position for p in pieces]
        self.table.setRowCount(len(pieces))
        for i, p in enumerate(pieces):
            self.table.setItem(i, 0, QTableWidgetItem(f"{p.position.row},{p.position.col}"))
            self.table.setItem(i, 1, QTableWidgetItem(p.side.label))
            self.table.setItem(i, 2, QTableWidgetItem(p.piece_type.display_name(p.side)))
            self.table.setItem(i, 3, QTableWidgetItem("已揭示" if p.revealed else "暗子"))
            self.table.setItem(i, 4, QTableWidgetItem(self._describe(p)))
        self.turn_combo.setCurrentIndex(0 if st.turn is Side.RED else 1)

    @staticmethod
    def _describe(p: Piece) -> str:
        if p.is_unknown:
            return "未知身份"
        return p.piece_type.notation_name(p.side)

    # ---------- actions ----------
    def _delete(self) -> None:
        pos = self._selected_pos()
        if pos is None:
            return
        self.service.edit_remove(pos)
        self._refresh()

    def _to_unknown(self) -> None:
        pos = self._selected_pos()
        if pos is None:
            return
        self.service.edit_set_unknown(pos)
        self._refresh()

    def _set_type(self) -> None:
        pos = self._selected_pos()
        if pos is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("修改身份")
        lay = QVBoxLayout(dlg)
        combo = QComboBox()
        st = self.service.current()
        piece = st.board.get(pos)
        side = piece.side if piece else Side.RED
        for pt in (PieceType.ROOK, PieceType.CANNON, PieceType.HORSE,
                   PieceType.ELEPHANT, PieceType.ADVISOR, PieceType.GENERAL, PieceType.PAWN):
            combo.addItem(pt.display_name(side), pt)
        lay.addWidget(combo)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec() and combo.currentData():
            self.service.edit_set_revealed(pos, combo.currentData())
            self._refresh()

    def _add(self) -> None:
        pos = Position(self.r_spin.value(), self.c_spin.value())
        ok, msg = self.service.edit_place(pos, self.new_side.currentData(),
                                          self.new_type.currentData(), revealed=True)
        if not ok:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "新增棋子", msg)
        self._refresh()

    def _reset(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        ret = QMessageBox.question(self, "重置棋盘", "确定重置为当前模式的初始布局吗？")
        if ret == QMessageBox.Yes:
            self.service.reset_game()
            self._refresh()

    def accept(self) -> None:  # noqa: N802
        st = self.service.current()
        st.turn = self.turn_combo.currentData()
        super().accept()