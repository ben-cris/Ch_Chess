"""规则抽象基类与规则工厂。两种玩法共用同一接口，互不混淆。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from core.game_state import GameMode, GameState, GameStatus
from core.move import Move
from core.piece import PieceType, Side
from core.position import Position


class BaseRules(ABC):
    """规则引擎统一接口。

    正常玩法与揭棋玩法各自实现；GameService / AI 通过 rules_factory(mode)
    获得对应实现，保证模式不会混淆。
    """

    mode: GameMode

    def __init__(self, preset_name: str = "preset_a") -> None:
        self.preset_name = preset_name

    # ---- 走法 ----
    @abstractmethod
    def generate_legal_moves(self, state: GameState, side: Side) -> List[Move]:
        """返回可直接 apply_move 的具体合法走法（AI/测试/后台使用）。"""

    @abstractmethod
    def legal_actions(self, state: GameState, side: Side) -> List[Move]:
        """返回动作级合法操作（UI 高亮用；暗子的揭示身份可为空占位）。"""

    def is_legal(self, state: GameState, move: Move) -> bool:
        return move in self.generate_legal_moves(state, move.side) or move in self.legal_actions(state, move.side)

    # ---- 应用 ----
    @abstractmethod
    def apply_move(self, state: GameState, move: Move) -> GameState:
        """应用走法，返回新状态（纯函数，不改动入参）。"""

    # ---- 揭示 ----
    def legal_reveal_types(self, state: GameState, pos: Position) -> List[PieceType]:
        """该位置暗子可揭示成的身份候选（按剩余子力过滤）。"""
        return []

    def remaining_counts(self, state: GameState, side: Side) -> Dict[PieceType, int]:
        """该方尚未“上盘明示或已消耗”的子力计数（含暗置子）。"""
        counts: Dict[PieceType, int] = {}
        return counts

    # ---- 状态 ----
    @abstractmethod
    def status(self, state: GameState) -> GameStatus: ...

    def is_in_check(self, state: GameState, side: Side) -> bool:
        return False

    def winner(self, state: GameState) -> Optional[Side]:
        st = self.status(state)
        if st is GameStatus.RED_WIN:
            return Side.RED
        if st is GameStatus.BLACK_WIN:
            return Side.BLACK
        return None


def rules_factory(mode: GameMode, preset_name: str = "preset_a") -> BaseRules:
    """按模式创建规则实例。"""
    if mode is GameMode.NORMAL:
        from .normal_rules import NormalRules
        return NormalRules()
    from .dark_chess_rules import DarkChessRules
    return DarkChessRules(preset_name=preset_name)