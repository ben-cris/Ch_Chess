"""棋局会话服务：新建、走子、悔棋/重做、回合切换、编辑。

GUI 与规则完全解耦：本服务不依赖任何 UI 模块。
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from core.game_state import GameMode, GameState, new_game
from core.move import Move
from core.piece import PieceType, Side
from core.position import Position
from rules.base_rules import BaseRules, rules_factory


class GameService:
    def __init__(self) -> None:
        self.state: Optional[GameState] = None
        self._rules: Optional[BaseRules] = None
        self._undo: List[GameState] = []
        self._redo: List[GameState] = []

    # ---------------- 新建/装载 ----------------
    def new_game(self, mode: GameMode, user_side: Side, dark_preset: str = "preset_a") -> GameState:
        self.state = new_game(mode, user_side, dark_preset)
        self._rules = rules_factory(mode, dark_preset)
        self._undo.clear()
        self._redo.clear()
        return self.state

    def set_state(self, state: GameState) -> None:
        """载入（保存文件恢复后调用）。"""
        self.state = state
        self._rules = rules_factory(state.mode, state.dark_preset)
        self._undo.clear()
        self._redo.clear()

    def rules(self) -> BaseRules:
        if self._rules is None or self.state is None:
            raise RuntimeError("尚未新建棋局")
        return self._rules

    def current(self) -> GameState:
        if self.state is None:
            raise RuntimeError("尚未新建棋局")
        return self.state

    # ---------------- 走子 ----------------
    def apply_move(self, move: Move) -> Tuple[bool, str]:
        st = self.current()
        if st.over:
            return False, "棋局已结束"
        try:
            if not self.rules().is_legal(st, move):
                return False, "走法不合法"
            nxt = self.rules().apply_move(st, move)
        except ValueError as e:
            return False, str(e)
        self._undo.append(st)
        self._redo.clear()
        self.state = nxt
        return True, "ok"

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(self.state)
        self.state = self._undo.pop()
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(self.state)
        self.state = self._redo.pop()
        return True

    # ---------------- 回合 ----------------
    def set_turn(self, side: Side) -> None:
        st = self.current()
        if st.turn is not side:
            self._undo.append(st.clone())
            self._redo.clear()
            self.state = st.clone()
            self.state.turn = side

    # ---------------- 编辑 ----------------
    def edit_remove(self, pos: Position) -> Tuple[bool, str]:
        st = self.current()
        if st.board.get(pos) is None:
            return False, "该位置无棋子"
        self._snapshot_edit()
        st.board.remove(pos)
        self._recompute()
        return True, "ok"

    def edit_place(self, pos: Position, side: Side, piece_type: PieceType,
                   revealed: bool) -> Tuple[bool, str]:
        from core.piece import Piece
        st = self.current()
        if st.board.get(pos) is not None:
            return False, "该位置已有棋子，请先删除"
        if piece_type is PieceType.UNKNOWN:
            revealed = False
        if piece_type is not PieceType.UNKNOWN and not revealed:
            return False, "真实棋子必须为已揭示状态"
        self._snapshot_edit()
        st.board.put(Piece(side, piece_type, revealed, pos))
        self._recompute()
        return True, "ok"

    def edit_set_revealed(self, pos: Position, piece_type: PieceType) -> Tuple[bool, str]:
        """把该位置棋子设为已揭示并指定身份（用于修正现实棋局）。"""
        st = self.current()
        p = st.board.get(pos)
        if p is None:
            return False, "该位置无棋子"
        self._snapshot_edit()
        p.piece_type = piece_type
        p.revealed = True
        self._recompute()
        return True, "ok"

    def edit_set_unknown(self, pos: Position) -> Tuple[bool, str]:
        st = self.current()
        p = st.board.get(pos)
        if p is None:
            return False, "该位置无棋子"
        self._snapshot_edit()
        p.piece_type = PieceType.UNKNOWN
        p.revealed = False
        self._recompute()
        return True, "ok"

    def _snapshot_edit(self) -> None:
        self._undo.append(self.current().clone())
        self._redo.clear()

    def _recompute(self) -> None:
        st = self.current()
        st.status = self.rules().status(st)
        st.over = st.status.game_over

    def reset_game(self) -> None:
        if self.state is not None:
            self.new_game(self.state.mode, self.state.user_side, self.state.dark_preset)