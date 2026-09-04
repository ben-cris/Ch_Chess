"""AI 后台任务：把 AIAnalysisService 放到线程，回调回主线程，支持取消。"""
from __future__ import annotations

import threading
from typing import Callable, Optional

from core.game_state import GameState
from models.analysis_result import AnalysisResult
from models.settings import EngineSettings
from ai.ai_analysis_service import AIAnalysisService


class AnalysisJob:
    def __init__(self, state: GameState, settings: EngineSettings,
                 on_done: Callable[[AnalysisResult], None],
                 on_error: Callable[[Exception], None]) -> None:
        self._service = AIAnalysisService(settings)
        self._state = state
        self._on_done = on_done
        self._on_error = on_error
        self._thread: Optional[threading.Thread] = None

    def start(self) -> "AnalysisJob":
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def _run(self) -> None:
        try:
            result = self._service.analyze(self._state)
            self._on_done(result)
        except Exception as e:  # 兜底：后台异常也通过回调上报，不崩 GUI
            self._on_error(e)

    def cancel(self) -> None:
        self._service.stop()

    def join(self, timeout: Optional[float] = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)