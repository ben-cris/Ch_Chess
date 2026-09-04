"""揭棋规则（预置 A，按用户确认的位置模板规则）。

核心规则：
- 每个暗子没有“隐藏真相”，身份只在揭示/被吃事件中由用户指定（程序不猜测）。
- 暗子（未揭示）的行动走法 = 该子所在初始格“原本棋子”的走法（位置模板）。
  例：位于炮位的暗子按炮的走法行动；位于车位的暗子按车走。
- 暗子移动/吃子后必须揭示身份（reveal_type，由用户选择）；原地翻子算一步。
- 已揭示明子复用正常几何走法原语。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from core.board import Board, new_normal_board
from core.events import CapturedPiece, RevealEvent
from core.game_state import GameMode, GameState, GameStatus
from core.move import Move
from core.piece import PIECE_TOTAL, Piece, PieceType, Side
from core.position import Position
from rules.base_rules import BaseRules
from rules.dark_presets import DarkPreset, get_preset
from rules.piece_move_generator import is_square_attacked, kings_facing, pseudo_targets

_TYPE_ORDER = [
    PieceType.GENERAL, PieceType.ROOK, PieceType.CANNON, PieceType.HORSE,
    PieceType.ELEPHANT, PieceType.ADVISOR, PieceType.PAWN,
]

# 位置模板：{(side, Position) -> 该格原本棋子类型}
_TEMPLATE_MAP: Optional[Dict] = None


def _template_map() -> Dict:
    global _TEMPLATE_MAP
    if _TEMPLATE_MAP is None:
        m: Dict = {}
        for p in new_normal_board().pieces():
            m[(p.side, p.position)] = p.piece_type
        _TEMPLATE_MAP = m
    return _TEMPLATE_MAP


def position_template_type(side: Side, pos: Position) -> Optional[PieceType]:
    """返回该格在正常布局中原本应放的棋子类型；非初始格返回 None。"""
    return _template_map().get((side, pos))


class DarkChessRules(BaseRules):
    mode = GameMode.DARK

    def __init__(self, preset_name: str = "preset_a") -> None:
        super().__init__(preset_name)
        self.preset: DarkPreset = get_preset(preset_name)

    # ---------------- 子力计数 / 揭示候选 ----------------
    def remaining_counts(self, state: GameState, side: Side) -> Dict[PieceType, int]:
        counts = dict(PIECE_TOTAL)
        for p in state.board.pieces_of(side):
            if p.revealed and not p.is_unknown:
                counts[p.piece_type] -= 1
        for cp in state.captured_log:
            if cp.side is side and cp.effective_type.is_real:
                counts[cp.effective_type] -= 1
        return {t: c for t, c in counts.items() if c > 0}

    def legal_reveal_types(self, state: GameState, pos: Position) -> List[PieceType]:
        p = state.board.get(pos)
        if p is None or not p.is_unknown:
            return []
        remaining = self.remaining_counts(state, p.side)
        return [t for t in _TYPE_ORDER if t in remaining]

    # ---------------- 暗子走法：位置模板 ----------------
    def _hidden_targets(self, board: Board, piece: Piece) -> List[Position]:
        """暗子可到达的位置（按所在初始格原兵种走法；非初始格回退为“前进一步”）。"""
        pos = piece.position
        ttype = position_template_type(piece.side, pos)
        if ttype is not None and self.preset.hidden_uses_position_template:
            synthetic = Piece(piece.side, ttype, True, pos)
            targets = pseudo_targets(board, synthetic, relaxed_elephant_advisor=True)
            if not self.preset.dark_move_capture:
                targets = [t for t in targets if board.get(t) is None]
            return targets
        # 回退（旧版/非初始格）：暗子只进不退
        if self.preset.dark_move_reveals:
            to = pos.forward(piece.side)
            if to.in_board():
                occ = board.get(to)
                if occ is None or (occ.side is not piece.side and self.preset.dark_move_capture):
                    return [to]
        return []

    def _hidden_concrete_moves(self, state: GameState, piece: Piece) -> List[Move]:
        """暗子的具体走法：按候选身份展开（AI/测试用）。"""
        moves: List[Move] = []
        pos = piece.position
        candidates = self.legal_reveal_types(state, pos)
        if self.preset.allow_in_place_reveal:
            for rt in candidates:
                moves.append(Move(piece.side, pos, pos, reveal_type=rt))
        if not self.preset.dark_move_reveals:
            return moves
        for to in self._hidden_targets(state.board, piece):
            occ = state.board.get(to)
            if occ is not None and occ.side is piece.side:
                continue
            captured = self._snapshot(occ)
            for rt in candidates:
                mv = Move(piece.side, pos, to, captured=captured, reveal_type=rt)
                if self._legal_after(state.board, mv):
                    moves.append(mv)
        return moves

    # ---------------- 走法生成 ----------------
    def generate_legal_moves(self, state: GameState, side: Side) -> List[Move]:
        moves: List[Move] = []
        for piece in state.board.pieces_of(side):
            if piece.revealed:
                for to in pseudo_targets(state.board, piece, relaxed_elephant_advisor=True):
                    mv = Move(side, piece.position, to, captured=self._snapshot(state.board.get(to)))
                    if self._legal_after(state.board, mv):
                        moves.append(mv)
            else:
                moves.extend(self._hidden_concrete_moves(state, piece))
        return moves

    def legal_actions(self, state: GameState, side: Side) -> List[Move]:
        """动作级（UI 高亮）：暗子动作不含身份，身份由用户随后选择。"""
        actions: List[Move] = []
        for piece in state.board.pieces_of(side):
            if piece.revealed:
                for to in pseudo_targets(state.board, piece, relaxed_elephant_advisor=True):
                    mv = Move(side, piece.position, to)
                    if self._legal_after(state.board, mv):
                        actions.append(mv)
            else:
                pos = piece.position
                if self.preset.allow_in_place_reveal:
                    actions.append(Move(side, pos, pos, reveal_type=None))
                if self.preset.dark_move_reveals:
                    for to in self._hidden_targets(state.board, piece):
                        occ = state.board.get(to)
                        if occ is not None and occ.side is piece.side:
                            continue
                        actions.append(Move(side, pos, to, captured=self._snapshot(occ)))
        return actions

    @staticmethod
    def _snapshot(piece: Optional[Piece]) -> Optional[CapturedPiece]:
        if piece is None:
            return None
        return CapturedPiece(side=piece.side, piece_type=piece.piece_type,
                             revealed=piece.revealed, position=piece.position)

    def is_legal(self, state: GameState, move: Move) -> bool:
        piece = state.board.get(move.frm)
        if piece is None or piece.side is not move.side:
            return False
        if piece.revealed:
            if move.has_reveal or move.frm == move.to:
                return False
            if move.to not in pseudo_targets(state.board, piece, relaxed_elephant_advisor=True):
                return False
            return self._legal_after(state.board, move)
        # 暗子动作
        if not move.has_reveal:
            return move in self.legal_actions(state, move.side)
        remaining = self.remaining_counts(state, piece.side)
        if remaining.get(move.reveal_type, 0) <= 0:
            return False
        if move.frm == move.to:
            return self.preset.allow_in_place_reveal and self._legal_after(state.board, move)
        if not self.preset.dark_move_reveals:
            return False
        if move.to not in self._hidden_targets(state.board, piece):
            return False
        occ = state.board.get(move.to)
        if occ is not None and not self.preset.dark_move_capture:
            return False
        return self._legal_after(state.board, move)

    def _legal_after(self, board: Board, move: Move) -> bool:
        nxt = self._dry_apply(board, move)
        if self.preset.revealed_king_facing and kings_facing(nxt):
            return False
        king = nxt.king_position(move.side)
        if king is not None and self._attacked(nxt, king, move.side.opponent):
            return False
        return True

    def _attacked(self, board: Board, target: Position, by_side: Side) -> bool:
        if is_square_attacked(board, target, by_side, relaxed_elephant_advisor=True):
            return True
        if not self.preset.dark_move_capture:
            return False
        # 暗子威胁 = 该暗子按“位置模板”若能吃掉 target 即构成威胁
        for p in board.pieces_of(by_side):
            if p.revealed:
                continue
            ttype = position_template_type(p.side, p.position)
            if ttype is not None and self.preset.hidden_uses_position_template:
                synthetic = Piece(p.side, ttype, True, p.position)
                if target in pseudo_targets(board, synthetic, relaxed_elephant_advisor=True):
                    return True
            elif p.position.forward(by_side) == target:
                return True
        return False

    @staticmethod
    def _dry_apply(board: Board, move: Move) -> Board:
        b = board.clone()
        piece = b.get(move.frm)
        if piece is None:
            return b
        captured = b.remove(move.to) if move.frm != move.to else None
        if move.frm != move.to:
            b.remove(move.frm)
            piece.position = move.to
            b.put(piece)
        if move.has_reveal:
            piece.revealed = True
            piece.piece_type = move.reveal_type  # type: ignore[assignment]
        return b

    # ---------------- 应用 ----------------
    def apply_move(self, state: GameState, move: Move) -> GameState:
        piece = state.board.get(move.frm)
        if piece is None or piece.side is not move.side:
            raise ValueError("起点无该方棋子")
        if piece.is_unknown and not move.has_reveal:
            raise ValueError("暗子走子必须携带揭示身份（用户选择，程序不猜测）")
        if move.has_reveal:
            remaining = self.remaining_counts(state, piece.side)
            if remaining.get(move.reveal_type, 0) <= 0:
                raise ValueError(f"揭示身份不合法（子力不足）: {move.reveal_type}")
        if not self.is_legal(state, move):
            raise ValueError(f"非法走法: {move.side.short} {move.frm}->{move.to}")

        nxt = state.clone()
        board = nxt.board
        notation = self._notation(board, move)
        captured_piece = board.move_piece(move.frm, move.to) if move.frm != move.to else None

        captured = None
        if captured_piece is not None:
            disclosed = move.captured.disclosed_type if move.captured is not None else None
            captured = CapturedPiece(
                side=captured_piece.side,
                piece_type=captured_piece.piece_type,
                revealed=captured_piece.revealed,
                position=captured_piece.position,
                disclosed_type=disclosed,
            )
            nxt.captured_log.append(captured)
        if move.has_reveal:
            p = board.get(move.to if move.frm != move.to else move.frm)
            p.revealed = True
            p.piece_type = move.reveal_type  # type: ignore[assignment]
            nxt.reveal_history.append(RevealEvent(
                pos=move.to if move.frm != move.to else move.frm,
                side=move.side, piece_type=move.reveal_type,
                source="capture" if move.is_capture else "user",
            ))
        final = Move(move.side, move.frm, move.to, captured=captured,
                     reveal_type=move.reveal_type, notation=notation, forced=move.forced)
        nxt.moves.append(final)
        nxt.turn = nxt.turn.opponent
        nxt.record_position()
        nxt.status = self.status(nxt)
        nxt.over = nxt.status.game_over
        return nxt

    @staticmethod
    def _notation(board: Board, move: Move) -> str:
        piece = board.get(move.frm)
        if piece is None:
            return ""
        if move.frm == move.to:
            return f"{move.side.short}翻子"
        ttype = position_template_type(piece.side, piece.position)
        if ttype is not None:
            name = ttype.notation_name(piece.side)
            return f"暗{name}走"
        return f"{move.side.short}暗走"

    # ---------------- 状态 ----------------
    def status(self, state: GameState) -> GameStatus:
        # 将/帅被吃（含暗子被吃后由用户确认为将/帅）→ 对方胜
        for cp in state.captured_log:
            if cp.effective_type is PieceType.GENERAL:
                return GameStatus.RED_WIN if cp.side is Side.BLACK else GameStatus.BLACK_WIN
        if not self.generate_legal_moves(state, state.turn):
            return GameStatus.RED_WIN if state.turn is Side.BLACK else GameStatus.BLACK_WIN
        key = state.position_key()
        if state.position_counts.get(key, 0) >= 3:
            return GameStatus.DRAW
        return GameStatus.PLAYING

    def is_in_check(self, state: GameState, side: Side) -> bool:
        king = state.board.king_position(side)
        if king is None:
            return False
        return self._attacked(state.board, king, side.opponent)