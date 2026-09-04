"""走法排序：吃子优先（MVV-LVA 简化），提升剪枝效率。"""
from __future__ import annotations

from typing import List

from core.game_state import GameState
from core.move import Move
from ai.evaluation import PIECE_VALUE


def order_moves(state: GameState, moves: List[Move]) -> List[Move]:
    def key(m: Move) -> int:
        if m.captured is None:
            return 0
        vt = m.captured.effective_type
        val = PIECE_VALUE.get(vt, 0)
        return val
    return sorted(moves, key=key, reverse=True)