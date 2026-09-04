"""统一引擎接口：正常/揭棋、内置/外部引擎都实现它。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from threading import Event
from typing import List, Optional

from core.game_state import GameState
from core.move import Move
from models.settings import EngineSettings


@dataclass
class EngineResult:
    move: Optional[Move] = None
    score: float = 0.0            # 正=对轮到方有利
    depth: int = 0
    time_ms: int = 0
    engine: str = ""
    pv: List[Move] = field(default_factory=list)
    mate_in: Optional[int] = None
    note: str = ""


class ChessEngine(ABC):
    """所有引擎的统一接口。"""

    name = "base"

    def configure(self, settings: EngineSettings) -> None:  # noqa: B027
        pass

    @abstractmethod
    def get_best_move(self, state: GameState, time_limit_ms: int,
                      max_depth: int, stop_event: Event) -> EngineResult:
        """返回最佳走法（必须为合法走法；失败时 move=None）。"""

    def stop(self) -> None:  # noqa: B027
        pass

    def close(self) -> None:  # noqa: B027
        pass