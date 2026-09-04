"""胜负/将军判定门面：供 services/UI/AI 统一调用（按状态模式自动路由）。"""
from __future__ import annotations

from core.game_state import GameState, GameStatus
from core.piece import Side
from .base_rules import BaseRules, rules_factory


def get_rules(state: GameState) -> BaseRules:
    return rules_factory(state.mode, state.dark_preset)


def status(state: GameState) -> GameStatus:
    return get_rules(state).status(state)


def is_in_check(state: GameState, side: Side) -> bool:
    return get_rules(state).is_in_check(state, side)


def has_legal_moves(state: GameState, side: Side) -> bool:
    return bool(get_rules(state).generate_legal_moves(state, side))