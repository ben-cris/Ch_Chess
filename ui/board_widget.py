"""棋盘控件：绘制 9x10 中国象棋棋盘与棋子，处理点击与高亮。"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.constants import (COLOR_BLACK, COLOR_BOARD_BG, COLOR_CANDIDATE,
                           COLOR_HIDDEN, COLOR_LINE, COLOR_LAST_MOVE,
                           COLOR_MOVED, COLOR_RECOMMEND, COLOR_RED, COLOR_SELECT)
from core.game_state import GameState
from core.piece import Side
from core.position import COLS, Position, ROWS


class BoardWidget(QWidget):
    square_clicked = Signal(int, int)  # (row, col)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.state: Optional[GameState] = None
        self.selected: Optional[Position] = None
        self.candidates: List[Position] = []
        self.recommend: Optional[tuple] = None  # (frm, to)
        self.last_move: Optional[tuple] = None  # (frm, to)
        self.flipped: bool = False              # 我执黑时黑方显示在下方
        self.setMinimumSize(500, 560)

    def set_state(self, state: GameState) -> None:
        self.state = state
        # 需求：位于下方的始终是我方（我执黑时整体旋转 180° 显示）
        self.flipped = bool(state and state.user_side is Side.BLACK)
        self.selected = None
        self.candidates = []
        self.recommend = None
        if state.moves:
            m = state.moves[-1]
            self.last_move = (m.frm, m.to)
        else:
            self.last_move = None
        self.update()

    def set_selection(self, pos: Optional[Position],
                      candidates: Optional[List[Position]] = None) -> None:
        self.selected = pos
        self.candidates = candidates or []
        self.update()

    def set_recommend(self, frm: Optional[Position], to: Optional[Position]) -> None:
        self.recommend = (frm, to) if frm and to else None
        self.update()

    # ---------------- 视角变换 ----------------
    def display_position(self, pos: Position) -> Position:
        """内部坐标 -> 屏幕视角坐标（我执黑时旋转 180°）。"""
        if self.flipped:
            return Position(ROWS - 1 - pos.row, COLS - 1 - pos.col)
        return pos

    def board_position(self, pos: Position) -> Position:
        """屏幕视角坐标 -> 内部坐标。"""
        if self.flipped:
            return Position(ROWS - 1 - pos.row, COLS - 1 - pos.col)
        return pos

    # ---------------- geometry ----------------
    def _margins(self) -> int:
        return 30

    def _cell(self) -> float:
        m = self._margins()
        return min((self.width() - 2 * m) / 9.0, (self.height() - 2 * m) / 10.0)

    def _origin(self) -> tuple:
        m = self._margins()
        cell = self._cell()
        x0 = (self.width() - cell * 9) / 2.0
        y0 = (self.height() - cell * 10) / 2.0
        return x0, y0

    def _center(self, pos: Position) -> QPointF:
        x0, y0 = self._origin()
        cell = self._cell()
        vp = self.display_position(pos)
        return QPointF(x0 + vp.col * cell, y0 + vp.row * cell)

    def _to_pos(self, x: float, y: float) -> Optional[Position]:
        x0, y0 = self._origin()
        cell = self._cell()
        col = round((x - x0) / cell)
        row = round((y - y0) / cell)
        p = Position(row, col)
        if not p.in_board():
            return None
        return self.board_position(p)

    # ---------------- events ----------------
    def mousePressEvent(self, e) -> None:  # noqa: N802
        p = self._to_pos(e.position().x(), e.position().y())
        if p is not None:
            self.square_clicked.emit(p.row, p.col)

    # ---------------- paint ----------------
    def paintEvent(self, e) -> None:  # noqa: N802
        if self.state is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(COLOR_BOARD_BG))
        cell = self._cell()
        x0, y0 = self._origin()
        pen = QPen(QColor(COLOR_LINE), 1.4)
        painter.setPen(pen)

        # 横线 10 条、竖线（河界断开）
        for r in range(10):
            painter.drawLine(QPointF(x0, y0 + r * cell), QPointF(x0 + 8 * cell, y0 + r * cell))
        for c in range(9):
            painter.drawLine(QPointF(x0 + c * cell, y0), QPointF(x0 + c * cell, y0 + 4 * cell))
            painter.drawLine(QPointF(x0 + c * cell, y0 + 5 * cell), QPointF(x0 + c * cell, y0 + 9 * cell))
        # 九宫斜线
        for (r0, r1) in ((0, 2), (7, 9)):
            painter.drawLine(QPointF(x0 + 3 * cell, y0 + r0 * cell), QPointF(x0 + 5 * cell, y0 + r1 * cell))
            painter.drawLine(QPointF(x0 + 5 * cell, y0 + r0 * cell), QPointF(x0 + 3 * cell, y0 + r1 * cell))
        # 楚河汉界
        painter.setFont(QFont("Microsoft YaHei", max(10, int(cell * 0.3))))
        painter.drawText(QRectF(x0, y0 + 4 * cell, 4.5 * cell, cell), Qt.AlignCenter, "楚  河")
        painter.drawText(QRectF(x0 + 4.5 * cell, y0 + 4 * cell, 4.5 * cell, cell), Qt.AlignCenter, "漢  界")

        self._draw_last_move(painter, cell)
        self._draw_candidates(painter, cell)
        self._draw_pieces(painter, cell)
        self._draw_selection(painter, cell)
        self._draw_recommend(painter, cell)

    def _piece_rect(self, center: QPointF, cell: float) -> QRectF:
        r = cell * 0.42
        return QRectF(center.x() - r, center.y() - r, 2 * r, 2 * r)

    def _draw_last_move(self, painter: QPainter, cell: float) -> None:
        if self.last_move is None:
            return
        for p in self.last_move:
            c = self._center(p)
            painter.setBrush(QColor(COLOR_LAST_MOVE))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(c, cell * 0.18, cell * 0.18)
        # 在“刚走动的棋子（落点）”上画一个小圆环高亮
        dest = self.last_move[1]
        c = self._center(dest)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(COLOR_MOVED), max(2.0, cell * 0.06)))
        painter.drawEllipse(c, cell * 0.52, cell * 0.52)

    def _draw_candidates(self, painter: QPainter, cell: float) -> None:
        painter.setBrush(QColor(COLOR_CANDIDATE))
        painter.setPen(Qt.NoPen)
        for p in self.candidates:
            c = self._center(p)
            painter.drawEllipse(c, cell * 0.12, cell * 0.12)

    def _draw_pieces(self, painter: QPainter, cell: float) -> None:
        for piece in self.state.board.pieces():
            c = self._center(piece.position)
            rect = self._piece_rect(c, cell)
            if piece.is_unknown:
                painter.setBrush(QColor(COLOR_HIDDEN))
                painter.setPen(QPen(QColor("#D5D8DC"), 1.5))
                painter.drawEllipse(rect)
                painter.setPen(QColor("white"))
                painter.setFont(QFont("Microsoft YaHei", max(10, int(cell * 0.42)), QFont.Bold))
                painter.drawText(rect, Qt.AlignCenter, "暗")
                continue
            color = QColor(COLOR_RED if piece.side is Side.RED else COLOR_BLACK)
            painter.setBrush(QColor("#FDFEFE"))
            painter.setPen(QPen(color, 2.2))
            painter.drawEllipse(rect)
            painter.setPen(color)
            painter.setFont(QFont("KaiTi", max(10, int(cell * 0.5)), QFont.Bold))
            painter.drawText(rect, Qt.AlignCenter, piece.piece_type.display_name(piece.side))

    def _draw_selection(self, painter: QPainter, cell: float) -> None:
        if self.selected is None:
            return
        c = self._center(self.selected)
        painter.setPen(QPen(QColor(COLOR_SELECT), 3))
        painter.setBrush(Qt.NoBrush)
        r = cell * 0.48
        painter.drawEllipse(c, r, r)

    def _draw_recommend(self, painter: QPainter, cell: float) -> None:
        if self.recommend is None:
            return
        pen = QPen(QColor(COLOR_RECOMMEND), 4)
        painter.setPen(pen)
        a = self._center(self.recommend[0])
        b = self._center(self.recommend[1])
        painter.drawLine(a, b)
        painter.setBrush(QColor(COLOR_RECOMMEND))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(b, cell * 0.3, cell * 0.3)