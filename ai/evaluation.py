"""静态局面评价。内部以红方为正；搜索层转换为轮到方视角。"""
from __future__ import annotations

from typing import Dict

from core.board import Board
from core.game_state import GameState
from core.piece import PieceType, Side
from rules.dark_chess_rules import DarkChessRules

# 子力价值（分）
PIECE_VALUE: Dict[PieceType, int] = {
    PieceType.GENERAL: 100000,
    PieceType.ROOK: 1000,
    PieceType.CANNON: 550,
    PieceType.HORSE: 500,
    PieceType.ELEPHANT: 300,
    PieceType.ADVISOR: 300,
    PieceType.PAWN: 120,
}
CROSSED_PAWN_BONUS = 60


def evaluate_red(board: Board) -> float:
    """红方视角静态分（不含暗子期望）。"""
    score = 0.0
    for p in board.pieces():
        if p.is_unknown or not p.revealed:
            continue
        v = PIECE_VALUE[p.piece_type]
        if p.piece_type is PieceType.PAWN and p.position.crossed_river(p.side):
            v += CROSSED_PAWN_BONUS
        if p.side is Side.RED:
            score += v
        else:
            score -= v
    return score


def evaluate_state(state: GameState) -> float:
    """红方视角评价；揭棋模式对暗子用剩余子力期望值。"""
    score = evaluate_red(state.board)
    if state.mode.value == "dark":
        rules = DarkChessRules(state.dark_preset)
        for side in (Side.RED, Side.BLACK):
            remaining = rules.remaining_counts(state, side)
            total = sum(remaining.values())
            if total <= 0:
                continue
            hidden = [p for p in state.board.pieces_of(side) if not p.revealed]
            if not hidden:
                continue
            exp = sum(PIECE_VALUE[t] * c for t, c in remaining.items()) / total
            delta = exp * len(hidden)
            score += delta if side is Side.RED else -delta
    return score