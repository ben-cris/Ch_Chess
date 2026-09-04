"""正常中国象棋规则。"""
from __future__ import annotations

from typing import List

from core.board import Board
from core.events import CapturedPiece
from core.game_state import GameMode, GameState, GameStatus
from core.move import Move
from core.notation import format_move
from core.piece import Side
from core.position import Position
from .base_rules import BaseRules
from .piece_move_generator import is_square_attacked, kings_facing, pseudo_targets


class NormalRules(BaseRules):
    mode = GameMode.NORMAL

    # ---------------- 走法生成 ----------------
    def generate_legal_moves(self, state: GameState, side: Side) -> List[Move]:
        moves: List[Move] = []
        for piece in state.board.pieces_of(side):
            if piece.is_unknown or not piece.revealed:
                continue
            for to in pseudo_targets(state.board, piece):
                occ = state.board.get(to)
                captured = None
                if occ is not None and occ.side is not side:
                    captured = CapturedPiece(side=occ.side, piece_type=occ.piece_type,
                                             revealed=occ.revealed, position=to)
                mv = Move(side, piece.position, to, captured=captured)
                if self._legal_after(state.board, mv):
                    moves.append(mv)
        return moves

    def legal_actions(self, state: GameState, side: Side) -> List[Move]:
        return self.generate_legal_moves(state, side)

    def is_legal(self, state: GameState, move: Move) -> bool:
        piece = state.board.get(move.frm)
        if piece is None or piece.side is not move.side:
            return False
        if piece.is_unknown or not piece.revealed:
            return False
        if move.frm == move.to:
            return False
        if move.to not in pseudo_targets(state.board, piece):
            return False
        return self._legal_after(state.board, move)

    def _legal_after(self, board: Board, move: Move) -> bool:
        """走子后：不得照面，不得让自己的将/帅被吃/被攻击。"""
        nxt = self._dry_apply(board, move)
        if kings_facing(nxt):
            return False
        king = nxt.king_position(move.side)
        if king is not None and is_square_attacked(nxt, king, move.side.opponent):
            return False
        return True

    @staticmethod
    def _dry_apply(board: Board, move: Move) -> Board:
        b = board.clone()
        b.move_piece(move.frm, move.to)
        return b

    # ---------------- 应用 ----------------
    def apply_move(self, state: GameState, move: Move) -> GameState:
        if not self.is_legal(state, move):
            raise ValueError(f"非法走法: {move.side.short} {move.frm}->{move.to}")
        nxt = state.clone()
        board = nxt.board
        notation = format_move(board, move)
        captured_piece = board.move_piece(move.frm, move.to)
        captured = None
        if captured_piece is not None:
            captured = CapturedPiece(
                side=captured_piece.side,
                piece_type=captured_piece.piece_type,
                revealed=captured_piece.revealed,
                position=captured_piece.position,
                disclosed_type=captured_piece.piece_type if captured_piece.revealed else None,
            )
            nxt.captured_log.append(captured)
        final = Move(move.side, move.frm, move.to, captured=captured,
                     reveal_type=move.reveal_type, notation=notation, forced=move.forced)
        nxt.moves.append(final)
        nxt.turn = nxt.turn.opponent
        nxt.record_position()
        nxt.status = self.status(nxt)
        nxt.over = nxt.status.game_over
        return nxt

    # ---------------- 状态 ----------------
    def status(self, state: GameState) -> GameStatus:
        from core.piece import PieceType
        # 将/帅缺失（编辑导致）→ 对方胜
        for side in (Side.RED, Side.BLACK):
            if state.board.king_position(side) is None and state.board.find(side, PieceType.GENERAL, revealed=True) is None:
                return GameStatus.RED_WIN if side is Side.BLACK else GameStatus.BLACK_WIN
        if not self.generate_legal_moves(state, state.turn):
            # 将死或困毙：无子可走的一方负
            return GameStatus.RED_WIN if state.turn is Side.BLACK else GameStatus.BLACK_WIN
        key = state.position_key()
        if state.position_counts.get(key, 0) >= 3:
            return GameStatus.DRAW
        return GameStatus.PLAYING

    def is_in_check(self, state: GameState, side: Side) -> bool:
        king = state.board.king_position(side)
        if king is None:
            return False
        return is_square_attacked(state.board, king, side.opponent)