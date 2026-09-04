"""走法对象。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.events import CapturedPiece
from core.piece import PieceType, Side
from core.position import Position


@dataclass
class Move:
    side: Side
    frm: Position
    to: Position
    captured: Optional[CapturedPiece] = None
    reveal_type: Optional[PieceType] = None  # 走子后移动方棋子揭示成的身份(暗子移动/翻子)
    notation: str = ""
    forced: bool = False                     # 强制录入标记

    @property
    def is_reveal_in_place(self) -> bool:
        """原地翻子：起点==终点。"""
        return self.frm == self.to

    @property
    def has_reveal(self) -> bool:
        return self.reveal_type is not None

    @property
    def is_capture(self) -> bool:
        return self.captured is not None

    def describe(self) -> str:
        return self.notation or f"{self.side.short}:{self.frm}->{self.to}"