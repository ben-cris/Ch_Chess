"""AI 分析编排：按模式选引擎、控制深度/时间、校验合法性、映射评分视角。"""
from __future__ import annotations

from threading import Event
from typing import Optional

from core.game_state import GameState, GameStatus
from models.analysis_result import AnalysisResult
from models.settings import EngineSettings
from rules.base_rules import rules_factory
from engine.engine_manager import EngineManager, resolve_engine


class AIAnalysisService:
    """分析对象 = 用户在现实棋局中的下一步。永远只返回建议，不自动落子。"""

    def __init__(self, settings: Optional[EngineSettings] = None) -> None:
        self.settings = settings or EngineSettings()
        self._stop = Event()

    def set_settings(self, settings: EngineSettings) -> None:
        self.settings = settings

    def stop(self) -> None:
        self._stop.set()

    def reset_stop(self) -> None:
        self._stop.clear()

    def analyze(self, state: GameState) -> AnalysisResult:
        """同步分析（通常在后台线程调用）。返回分析方视角的结果。"""
        self.reset_stop()
        if state.over or state.status is not GameStatus.PLAYING:
            return AnalysisResult(move=None, engine="", note="棋局已结束，无法分析")
        work = state.clone()
        is_dark = work.mode.value == "dark"
        engine_name = resolve_engine(self.settings.engine, is_dark)
        depth = self.settings.max_depth
        time_ms = self.settings.time_limit_ms
        if is_dark:
            # 揭棋用专用快速搜索：深度上限交给引擎（受思考时间约束）
            depth = max(1, min(depth, 8))

        try:
            engine = EngineManager.get_engine(engine_name, self.settings)
            engine.configure(self.settings)
            result = engine.get_best_move(work, time_ms, depth, self._stop)
        except Exception as exc:  # 引擎缺失/异常 → 降级内置，程序不崩溃
            fallback = EngineManager.get_engine("builtin", self.settings)
            try:
                result = fallback.get_best_move(work, time_ms, depth, self._stop)
                result.note = f"{result.note} (原引擎 {engine_name} 异常: {exc}，已用内置引擎)"
            except Exception as exc2:
                return AnalysisResult(move=None, note=f"分析失败: {exc2}", engine=engine_name)

        if result.move is None:
            return AnalysisResult(
                move=None, depth=result.depth, time_ms=result.time_ms,
                engine=result.engine, note=result.note or "未找到推荐走法",
            )
        rules = rules_factory(work.mode, work.dark_preset)
        if not rules.is_legal(work, result.move):
            return AnalysisResult(move=None, note="引擎返回非法走法，已丢弃", engine=result.engine)
        score = result.score
        if work.user_side is not None and work.user_side is not work.turn:
            score = -score
        # 补记谱文本，便于面板直接显示“车二平五”等
        if not result.move.notation:
            from core.notation import format_move
            try:
                result.move.notation = format_move(work.board, result.move)
            except Exception:
                result.move.notation = result.move.describe()
        uncertainty = "基于假设分布的期望推荐（置信度受暗子影响）" if is_dark else ""
        return AnalysisResult(
            move=result.move,
            score=score,
            depth=result.depth,
            time_ms=result.time_ms,
            engine=result.engine,
            mate_in=result.mate_in,
            forced_win=result.mate_in is not None,
            candidate_scores=[(result.move, score)],
            note=result.note,
            uncertainty=uncertainty,
        )