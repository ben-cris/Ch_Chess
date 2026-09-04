"""历史事件：被吃棋子快照、揭示事件。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.piece import PieceType, Side
from core.position import Position


@dataclass
class CapturedPiece:
    """被吃棋子的记录。

    piece_type/revealed 为“被吃时程序已知”的状态；
    disclosed_type 为被吃暗子的真实身份（由用户确认），明子时为原类型。
    """
    side: Side
    piece_type: PieceType
    revealed: bool
    position: Position
    disclosed_type: Optional[PieceType] = None

    @property
    def effective_type(self) -> PieceType:
        if self.disclosed_type is not None:
            return self.disclosed_type
        return self.piece_type


@dataclass
class RevealEvent:
    """一次揭示事件（身份由用户选择，程序不猜测）。"""
    pos: Position
    side: Side
    piece_type: PieceType
    source: str = "user"          # user | capture | correction
    note: str = ""
    ts: str = field(default="")