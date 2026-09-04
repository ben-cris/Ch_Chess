"""棋子领域模型：颜色(Side)、类型(PieceType)、棋子(Piece)。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Side(Enum):
    RED = "red"
    BLACK = "black"

    @property
    def opponent(self) -> "Side":
        return Side.BLACK if self is Side.RED else Side.RED

    @property
    def label(self) -> str:
        return "红方" if self is Side.RED else "黑方"

    @property
    def short(self) -> str:
        return "红" if self is Side.RED else "黑"


class PieceType(Enum):
    UNKNOWN = 0
    GENERAL = 1   # 帅/将
    ADVISOR = 2   # 仕/士
    ELEPHANT = 3  # 相/象
    HORSE = 4     # 马
    ROOK = 5      # 车
    CANNON = 6    # 炮
    PAWN = 7      # 兵/卒

    @property
    def is_real(self) -> bool:
        return self is not PieceType.UNKNOWN

    def display_name(self, side: Side) -> str:
        """用于界面显示的棋子字符（红黑用不同字形，便于区分）。"""
        if side is Side.RED:
            return {
                PieceType.UNKNOWN: "？",
                PieceType.GENERAL: "帥",
                PieceType.ADVISOR: "仕",
                PieceType.ELEPHANT: "相",
                PieceType.HORSE: "傌",
                PieceType.ROOK: "俥",
                PieceType.CANNON: "炮",
                PieceType.PAWN: "兵",
            }[self]
        return {
            PieceType.UNKNOWN: "？",
            PieceType.GENERAL: "將",
            PieceType.ADVISOR: "士",
            PieceType.ELEPHANT: "象",
            PieceType.HORSE: "馬",
            PieceType.ROOK: "車",
            PieceType.CANNON: "砲",
            PieceType.PAWN: "卒",
        }[self]

    def notation_name(self, side: Side) -> str:
        """中国象棋记谱用名。"""
        if side is Side.RED:
            return {
                PieceType.GENERAL: "帅",
                PieceType.ADVISOR: "仕",
                PieceType.ELEPHANT: "相",
                PieceType.HORSE: "马",
                PieceType.ROOK: "车",
                PieceType.CANNON: "炮",
                PieceType.PAWN: "兵",
            }[self]
        return {
            PieceType.GENERAL: "将",
            PieceType.ADVISOR: "士",
            PieceType.ELEPHANT: "象",
            PieceType.HORSE: "马",
            PieceType.ROOK: "车",
            PieceType.CANNON: "炮",
            PieceType.PAWN: "卒",
        }[self]


PIECE_TOTAL = {
    PieceType.GENERAL: 1,
    PieceType.ADVISOR: 2,
    PieceType.ELEPHANT: 2,
    PieceType.HORSE: 2,
    PieceType.ROOK: 2,
    PieceType.CANNON: 2,
    PieceType.PAWN: 5,
}


@dataclass
class Piece:
    """棋盘上的一颗棋子。

    正常玩法：revealed=True，piece_type 为真实类型。
    揭棋：未揭示棋子 piece_type=UNKNOWN 且 revealed=False；
          已揭示棋子 piece_type=真实类型 且 revealed=True。
    """
    side: Side
    piece_type: PieceType
    revealed: bool
    position: Optional["Position"] = None

    def __post_init__(self) -> None:
        if self.piece_type is PieceType.UNKNOWN and self.revealed:
            raise ValueError("已揭示棋子不能是 UNKNOWN 类型")

    @property
    def is_unknown(self) -> bool:
        return self.piece_type is PieceType.UNKNOWN

    def clone(self) -> "Piece":
        return Piece(self.side, self.piece_type, self.revealed, self.position)

    def describe(self) -> str:
        if self.is_unknown:
            return f"{self.side.short}暗子"
        name = self.piece_type.notation_name(self.side)
        return f"{self.side.short}{name}"