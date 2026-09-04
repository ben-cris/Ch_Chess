"""Mock 引擎：测试/冒烟用。默认返回第一个合法走法。"""
from __future__ import annotations

from threading import Event
from typing import Optional

from core.game_state import GameState
from core.move import Move
from rules.base_rules import rules_factory
from ai.chess_engine import ChessEngine, EngineResult


class MockEngine(ChessEngine):
    name = "mock"

    def __init__(self) -> None:
        self.forced_move: Optional[Move] = None
        self.raise_error: bool = False

    def get_best_move(self, state: GameState, time_limit_ms: int,
                      max_depth: int, stop_event: Event) -> EngineResult:
        if self.raise_error:
            raise RuntimeError("mock engine failure")
        rules = rules_factory(state.mode, state.dark_preset)
        moves = rules.generate_legal_moves(state, state.turn)
        if not moves:
            return EngineResult(move=None, engine=self.name, note="无合法走法")
        mv = self.forced_move if self.forced_move in moves else moves[0]
        return EngineResult(move=mv, score=0.0, depth=1, time_ms=0, engine=self.name, pv=[mv])