"""录入服务：把用户输入(起点/终点/身份)构造成 Move 并校验。

强制约束：揭棋暗子涉及揭示时，身份必须由用户选择（程序不猜测）。
"""
from __future__ import annotations

from typing import Optional, Tuple

from core.events import CapturedPiece
from core.game_state import GameState
from core.move import Move
from core.piece import PieceType, Side
from core.position import Position
from rules.base_rules import rules_factory


class MoveInputService:
    @staticmethod
    def build_move(state: GameState, side: Side, frm: Position, to: Position,
                   reveal_type: Optional[PieceType] = None,
                   disclosed_type: Optional[PieceType] = None,
                   forced: bool = False) -> Tuple[bool, str, Optional[Move]]:
        """根据用户输入构造走法对象。返回 (ok, 错误信息, move)。"""
        board = state.board
        if not isinstance(frm, Position):
            frm = Position(*frm)
        if not isinstance(to, Position):
            to = Position(*to)
        piece = board.get(frm)
        if piece is None:
            return False, "起点没有棋子", None
        if piece.side is not side:
            return False, "棋子颜色与走子方不符", None
        rules = rules_factory(state.mode, state.dark_preset)
        # 捕获对象
        captured = None
        target = board.get(to) if frm != to else None
        if target is not None:
            if target.side is side:
                return False, "不能吃己方棋子", None
            disc = disclosed_type
            if target.revealed:
                disc = target.piece_type
            captured = CapturedPiece(
                side=target.side, piece_type=target.piece_type,
                revealed=target.revealed, position=target.position,
                disclosed_type=disc,
            )
        # 暗子移动/翻子必须携带揭示身份（本项目的硬性要求）
        if piece.is_unknown and not piece.revealed:
            if frm == to:
                if reveal_type is None:
                    return False, "必须选择该棋子揭开后的真实身份", None
                if not rules.legal_reveal_types(state, frm) or \
                        reveal_type not in rules.legal_reveal_types(state, frm):
                    return False, "所选揭示身份与剩余子力不符", None
            else:
                if reveal_type is None:
                    return False, "暗子走动后必须选择其真实身份", None
        move = Move(side=side, frm=frm, to=to, captured=captured,
                    reveal_type=reveal_type, forced=forced)
        # 揭示身份合法性（剩余子力）
        if reveal_type is not None:
            remaining = rules.remaining_counts(state, side)
            if remaining.get(reveal_type, 0) <= 0:
                return False, "所选揭示身份数量已用完", None
        # 强制录入跳过规则校验
        if forced:
            return True, "forced", move
        if not rules.is_legal(state, move):
            return False, "走法与当前规则不符（可用编辑/强制录入修正）", None
        return True, "ok", move

    @staticmethod
    def validate_turn_for_analysis(state: GameState) -> Tuple[bool, str]:
        """AI 分析前置：应轮到用户方。"""
        if state.turn is state.user_side:
            return True, ""
        return False, f"当前轮到{state.turn.label}，请先录入{state.turn.label}的现实走法，再分析你的下一步"