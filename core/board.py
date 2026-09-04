"""棋盘：9x10，管理棋子放置与查询。"""
from __future__ import annotations

import random
from typing import Dict, Iterator, List, Optional

from core.piece import Piece, PieceType, Side
from core.position import COLS, Position, ROWS


class Board:
    def __init__(self) -> None:
        self._cells: Dict[Position, Piece] = {}

    # ---- 基础操作 ----
    def get(self, pos: Position) -> Optional[Piece]:
        return self._cells.get(pos)

    def put(self, piece: Piece) -> None:
        if not piece.position.in_board():
            raise ValueError(f"位置越界: {piece.position}")
        self._cells[piece.position] = piece

    def remove(self, pos: Position) -> Optional[Piece]:
        return self._cells.pop(pos, None)

    def clone(self) -> "Board":
        b = Board()
        for pos, p in self._cells.items():
            b._cells[pos] = p.clone()
        return b

    def clear(self) -> None:
        self._cells.clear()

    # ---- 查询 ----
    def pieces(self) -> Iterator[Piece]:
        return iter(self._cells.values())

    def pieces_of(self, side: Side) -> List[Piece]:
        return [p for p in self._cells.values() if p.side is side]

    def find(self, side: Side, piece_type: PieceType, revealed: bool = True) -> Optional[Position]:
        for p in self._cells.values():
            if p.side is side and p.piece_type is piece_type and p.revealed == revealed:
                return p.position
        return None

    def king_position(self, side: Side) -> Optional[Position]:
        """返回该方已揭示的将/帅位置；未揭示(揭棋)时返回 None。"""
        return self.find(side, PieceType.GENERAL, revealed=True)

    def count(self) -> int:
        return len(self._cells)

    def empty(self) -> bool:
        return not self._cells

    def move_piece(self, frm: Position, to: Position) -> Optional[Piece]:
        """把 frm 的棋子移到 to，返回 to 处被吃的棋子（若有）。"""
        piece = self.remove(frm)
        if piece is None:
            return None
        captured = self.remove(to)
        piece.position = to
        self.put(piece)
        return captured


# --------------------------------------------------------------------------
# 初始布局
# --------------------------------------------------------------------------
def _back_row(side: Side) -> List[PieceType]:
    return [
        PieceType.ROOK, PieceType.HORSE, PieceType.ELEPHANT, PieceType.ADVISOR,
        PieceType.GENERAL,
        PieceType.ADVISOR, PieceType.ELEPHANT, PieceType.HORSE, PieceType.ROOK,
    ]


def _side_starting_squares(side: Side) -> List[Position]:
    """某方 16 个初始占位（正常玩法中该方棋子的初始位置）。"""
    if side is Side.RED:
        rows = {9: list(range(9)), 7: [1, 7], 6: [0, 2, 4, 6, 8]}
    else:
        rows = {0: list(range(9)), 2: [1, 7], 3: [0, 2, 4, 6, 8]}
    out: List[Position] = []
    for r, cols in rows.items():
        for c in cols:
            out.append(Position(r, c))
    return out


def new_normal_board() -> Board:
    """标准中国象棋初始布局。"""
    board = Board()
    for side in (Side.RED, Side.BLACK):
        back = _back_row(side)
        if side is Side.RED:
            back_row, cannon_row, pawn_row = 9, 7, 6
        else:
            back_row, cannon_row, pawn_row = 0, 2, 3
        for c, pt in enumerate(back):
            board.put(Piece(side, pt, True, Position(back_row, c)))
        for c in (1, 7):
            board.put(Piece(side, PieceType.CANNON, True, Position(cannon_row, c)))
        for c in (0, 2, 4, 6, 8):
            board.put(Piece(side, PieceType.PAWN, True, Position(pawn_row, c)))
    return board


def new_dark_board(rng: Optional[random.Random] = None) -> Board:
    """揭棋初始棋盘（用户确认规则版）。

    - 将/帅不参与随机揭棋：红帅固定于(9,4)、黑将固定于(0,4)，开局即亮明；
    - 其余 15 颗子/方以暗子(身份未知)占住己方其余初始格位。
    暗子没有“隐藏真相”，身份只在用户录入揭示/被吃事件时由用户指定，
    因此具体排列顺序无游戏性影响（格位仅决定暗子“位置模板走法”）。
    """
    board = Board()
    for side in (Side.RED, Side.BLACK):
        general_pos = Position(9, 4) if side is Side.RED else Position(0, 4)
        for pos in _side_starting_squares(side):
            if pos == general_pos:
                board.put(Piece(side, PieceType.GENERAL, True, pos))
            else:
                board.put(Piece(side, PieceType.UNKNOWN, False, pos))
    return board