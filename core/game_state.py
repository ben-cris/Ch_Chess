"""棋局状态：模式、回合、用户方、棋盘、历史。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

from core.board import Board
from core.events import CapturedPiece, RevealEvent
from core.move import Move
from core.piece import Side


class GameMode(Enum):
    NORMAL = "normal"
    DARK = "dark"


class GameStatus(Enum):
    PLAYING = "playing"
    RED_WIN = "red_win"
    BLACK_WIN = "black_win"
    DRAW = "draw"

    @property
    def game_over(self) -> bool:
        return self is not GameStatus.PLAYING


def other(status_side: Side) -> GameStatus:
    return GameStatus.RED_WIN if status_side is Side.BLACK else GameStatus.BLACK_WIN


@dataclass
class GameState:
    mode: GameMode
    user_side: Side
    turn: Side
    board: Board
    moves: List[Move] = field(default_factory=list)
    reveal_history: List[RevealEvent] = field(default_factory=list)
    captured_log: List[CapturedPiece] = field(default_factory=list)
    dark_preset: str = "preset_a"
    status: GameStatus = GameStatus.PLAYING
    over: bool = False
    position_counts: Dict[str, int] = field(default_factory=dict)

    def clone(self) -> "GameState":
        return GameState(
            mode=self.mode,
            user_side=self.user_side,
            turn=self.turn,
            board=self.board.clone(),
            moves=list(self.moves),
            reveal_history=list(self.reveal_history),
            captured_log=list(self.captured_log),
            dark_preset=self.dark_preset,
            status=self.status,
            over=self.over,
            position_counts=dict(self.position_counts),
        )

    def position_key(self) -> str:
        """局面指纹（用于重复检测）。只含棋盘与轮到方。"""
        items = []
        for p in self.board.pieces():
            items.append(f"{p.position.row},{p.position.col}:{p.side.value}:{p.piece_type.value}:{int(p.revealed)}")
        items.sort()
        return self.turn.value + "|" + ";".join(items)

    def record_position(self) -> None:
        key = self.position_key()
        self.position_counts[key] = self.position_counts.get(key, 0) + 1

    def repeated_times(self, key: str) -> int:
        return self.position_counts.get(key, 0)


def new_game(mode: GameMode, user_side: Side, dark_preset: str = "preset_a",
             board: Board | None = None) -> GameState:
    """创建新棋局：红方先手。"""
    from .board import new_dark_board, new_normal_board
    if board is None:
        board = new_normal_board() if mode is GameMode.NORMAL else new_dark_board()
    state = GameState(mode=mode, user_side=user_side, turn=Side.RED,
                      board=board, dark_preset=dark_preset)
    state.record_position()
    return state