"""测试工具：局面构造。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.board import Board, new_normal_board  # noqa: E402
from core.game_state import GameMode, GameState  # noqa: E402
from core.piece import Piece, PieceType, Side  # noqa: E402
from core.position import Position  # noqa: E402


def empty_board() -> Board:
    return Board()


def put(board: Board, side: Side, typ: PieceType, r: int, c: int) -> None:
    board.put(Piece(side, typ, True, Position(r, c)))


def normal_state(board: Board, turn: Side = Side.RED, user_side: Side = Side.RED) -> GameState:
    st = GameState(GameMode.NORMAL, user_side, turn, board)
    st.record_position()
    return st


def dark_state(board: Board, turn: Side = Side.RED, user_side: Side = Side.RED) -> GameState:
    st = GameState(GameMode.DARK, user_side, turn, board, dark_preset="preset_a")
    st.record_position()
    return st