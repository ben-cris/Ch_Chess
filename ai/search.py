"""内置搜索引擎：α-β + 迭代加深 + 杀棋分。

正常玩法与揭棋玩法共用：走法由 rules_factory(mode) 提供；
揭棋对暗子采用“期望值评估”，且搜索不主动展开原地翻子（翻子由用户决定）。
"""
from __future__ import annotations

import time
from threading import Event
from typing import List, Optional, Tuple

from core.game_state import GameMode, GameState, GameStatus
from core.move import Move
from core.notation import format_move
from core.piece import Side
from rules.base_rules import BaseRules, rules_factory
from ai.chess_engine import ChessEngine, EngineResult
from ai.evaluation import evaluate_state
from ai.move_ordering import order_moves
from ai.opening_book import get_book
from app.logger import get_logger

log = get_logger("search")

MATE = 1_000_000
MATE_LIMIT = MATE - 10_000


class _Ctx:
    __slots__ = ("deadline", "stop_event", "nodes")

    def __init__(self, deadline: Optional[float], stop_event: Event) -> None:
        self.deadline = deadline
        self.stop_event = stop_event
        self.nodes = 0

    def aborted(self) -> bool:
        if self.stop_event is not None and self.stop_event.is_set():
            return True
        if self.deadline is not None and time.monotonic() > self.deadline:
            return True
        return False


def _eval_from_side(state: GameState, side: Side) -> float:
    v = evaluate_state(state)
    return v if side is Side.RED else -v


def _node_score(state: GameState, ply: int) -> Optional[float]:
    """已终局节点的分值（从 state.turn 视角）。"""
    st = state.status
    if st is GameStatus.DRAW:
        return 0.0
    if st is GameStatus.PLAYING:
        return None
    side = state.turn
    won = (st is GameStatus.RED_WIN and side is Side.RED) or \
          (st is GameStatus.BLACK_WIN and side is Side.BLACK)
    return float(MATE - ply) if won else float(-(MATE - ply))


class AlphaBetaEngine(ChessEngine):
    name = "builtin"

    def __init__(self) -> None:
        self._rules: Optional[BaseRules] = None

    def _rules_for(self, state: GameState) -> BaseRules:
        return rules_factory(state.mode, state.dark_preset)

    def get_best_move(self, state: GameState, time_limit_ms: int,
                      max_depth: int, stop_event: Event) -> EngineResult:
        t0 = time.monotonic()
        rules = self._rules_for(state)
        side = state.turn
        if state.over or state.status is not GameStatus.PLAYING:
            return EngineResult(move=None, engine=self.name, time_ms=0, note="棋局已结束")

        if state.mode is GameMode.DARK:
            # 揭棋分支大：使用专用快速搜索（就地 make/unmake + 宽度控制）
            from ai.dark_search import dark_get_best_move
            try:
                return dark_get_best_move(state, time_limit_ms, max_depth, stop_event)
            except Exception:
                log.exception("揭棋快速搜索异常，回退通用搜索")

        moves = rules.generate_legal_moves(state, side)
        if state.mode.value == "dark":
            # 揭棋：搜索不主动翻子（由用户决定），控制分支
            moves = [m for m in moves if not m.is_reveal_in_place]
        if not moves:
            return EngineResult(move=None, engine=self.name, note="无合法走法")

        # 内置开局库：正常玩法开局命中主流棋谱 → 毫秒级直接返回。
        # 只采用“当前局面确实合法”的招法；书内招法来自常见棋谱（非必胜保证）。
        if state.mode is GameMode.NORMAL:
            try:
                pair = get_book().first(state)
                if pair is not None:
                    for mv in moves:
                        if (mv.frm, mv.to) == pair:
                            if not mv.notation:
                                try:
                                    mv.notation = format_move(state.board, mv)
                                except Exception:
                                    mv.notation = mv.describe()
                            return EngineResult(
                                move=mv, engine=self.name,
                                time_ms=int((time.monotonic() - t0) * 1000),
                                pv=[mv],
                                note="命中内置开局库（常见棋谱主流开局招法，非必胜保证）")
            except Exception:
                log.exception("开局库查询失败，改用搜索")

        deadline = time.monotonic() + time_limit_ms / 1000.0 if time_limit_ms > 0 else None
        ctx = _Ctx(deadline, stop_event)
        best_move: Optional[Move] = None
        best_score = float("-inf")
        reached = 0
        for depth in range(1, max_depth + 1):
            if ctx.aborted():
                break
            score, mv = self._root_search(state, rules, side, moves, depth, ctx)
            if mv is not None:
                best_move = mv
                best_score = score
                reached = depth
        mate_in = None
        if best_score >= MATE_LIMIT and best_move is not None:
            mate_in = max(1, round((MATE - best_score) / 2))
        return EngineResult(
            move=best_move, score=best_score, depth=reached,
            time_ms=int((time.monotonic() - t0) * 1000), engine=self.name,
            pv=[best_move] if best_move else [], mate_in=mate_in,
        )

    def _root_search(self, state: GameState, rules: BaseRules, side: Side,
                     moves: List[Move], depth: int, ctx: _Ctx) -> Tuple[float, Optional[Move]]:
        best_score = float("-inf")
        best_move: Optional[Move] = None
        alpha = float("-inf")
        beta = float("inf")
        for mv in order_moves(state, moves):
            if ctx.aborted():
                break
            child = rules.apply_move(state, mv)
            sc = self._negamax(child, depth - 1, -beta, -alpha, 1, ctx)
            score = -sc
            if score > best_score:
                best_score = score
                best_move = mv
            if best_score > alpha:
                alpha = best_score
            if alpha >= beta:
                break
        return best_score, best_move

    def _negamax(self, state: GameState, depth: int, alpha: float, beta: float,
                 ply: int, ctx: _Ctx) -> float:
        ctx.nodes += 1
        if ctx.aborted():
            return 0.0
        term = _node_score(state, ply)
        if term is not None:
            return term
        rules = self._rules_for(state)
        moves = rules.generate_legal_moves(state, state.turn)
        if state.mode.value == "dark":
            moves = [m for m in moves if not m.is_reveal_in_place]
        if not moves:
            return float(-(MATE - ply))
        if depth <= 0:
            return _eval_from_side(state, state.turn)
        best = float("-inf")
        for mv in order_moves(state, moves):
            child = rules.apply_move(state, mv)
            sc = -self._negamax(child, depth - 1, -beta, -alpha, ply + 1, ctx)
            if sc > best:
                best = sc
            if best > alpha:
                alpha = best
            if alpha >= beta:
                break
        return best