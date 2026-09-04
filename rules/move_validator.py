"""合法走法校验门面。"""
from __future__ import annotations

from typing import List, Tuple

from core.game_state import GameState
from core.move import Move
from core.piece import Side
from .base_rules import BaseRules, rules_factory


class MoveValidator:
    """对当前状态做走法校验（含模式自动路由）。"""

    @staticmethod
    def rules(state: GameState) -> BaseRules:
        return rules_factory(state.mode, state.dark_preset)

    @staticmethod
    def generate_legal_moves(state: GameState, side: Side) -> List[Move]:
        return MoveValidator.rules(state).generate_legal_moves(state, side)

    @staticmethod
    def validate(state: GameState, move: Move) -> Tuple[bool, str]:
        r = MoveValidator.rules(state)
        if r.is_legal(state, move):
            return True, ""
        return False, "走法不合法（与当前规则不符）"