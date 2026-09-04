"""AI 分析结果（展示用）。评分约定：以分析方(用户方)视角，正=有利。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from core.move import Move


@dataclass
class AnalysisResult:
    move: Optional[Move]
    score: float = 0.0            # 分析方视角，单位“分”
    depth: int = 0
    time_ms: int = 0
    engine: str = ""
    mate_in: Optional[int] = None  # 强制将死剩余步数（引擎证明时）
    forced_win: bool = False
    candidate_scores: List[tuple] = field(default_factory=list)  # [(Move, score)]
    note: str = ""
    uncertainty: str = ""          # 揭棋：基于假设分布的提示

    def score_text(self) -> str:
        if self.mate_in is not None:
            return f"杀棋(约{self.mate_in}步)"
        v = int(round(self.score))
        if v > 0:
            return f"+{v}"
        return str(v)