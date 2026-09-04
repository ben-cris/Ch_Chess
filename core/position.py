"""棋盘坐标。约定：row 0=黑方底线(上)，row 9=红方底线(下)，col 0..8 从左到右。"""
from __future__ import annotations

from dataclasses import dataclass

from core.piece import Side

ROWS = 10
COLS = 9
RIVER_ROW = 4  # row<=4 为黑方半场/红方过河侧；row>=5 为红方半场


def _in_palace(row: int, col: int, side: Side) -> bool:
    if col < 3 or col > 5:
        return False
    if side is Side.RED:
        return 7 <= row <= 9
    return 0 <= row <= 2


@dataclass(frozen=True)
class Position:
    row: int
    col: int

    def in_board(self) -> bool:
        return 0 <= self.row < ROWS and 0 <= self.col < COLS

    def in_palace(self, side: Side) -> bool:
        return _in_palace(self.row, self.col, side)

    def crossed_river(self, side: Side) -> bool:
        """该位置是否已越过河界（对红方：row<=4；对黑方：row>=5）。"""
        if side is Side.RED:
            return self.row <= RIVER_ROW
        return self.row >= RIVER_ROW + 1

    def forward(self, side: Side) -> "Position":
        """向对方底线前进一步后的坐标（红方 row-1，黑方 row+1）。"""
        if side is Side.RED:
            return Position(self.row - 1, self.col)
        return Position(self.row + 1, self.col)

    def step(self, dr: int, dc: int) -> "Position":
        return Position(self.row + dr, self.col + dc)

    def __str__(self) -> str:  # 便捷：坐标用 (r,c)
        return f"({self.row},{self.col})"