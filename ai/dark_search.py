"""揭棋（暗棋）专用快速搜索。

揭棋分支巨大（早期每节点约 150~200 个合法走法），且走子即揭示、身份未知。
通用 α-β 搜索因每节点大量棋盘克隆与重复终局判定，2 秒内往往只能算 1 层，
几乎没有“预见性”。本模块在搜索内：
- 就地 make/unmake（不克隆棋盘、不重复走全量 status）；
- 每节点只生成一次走法，合法性用“临时落子-检查-撤销”完成；
- 叶子节点不再全量生成走法判终局（将/帅被吃在 make 时立即判胜）；
- 吃子优先排序 + 非吃子走法宽度上限，控制分支；
与 DarkChessRules 语义保持一致：位置模板暗子走法、暗子行动后按候选身份
展开揭示（AI 仍不“猜”身份，仅把各候选身份作为可选分支求最大值）、
士/相可出九宫过河、将/帅限九宫、吃将/帅即胜。
"""
from __future__ import annotations

import math
import time
from threading import Event
from typing import Dict, List, Optional, Tuple

from core.game_state import GameMode, GameState, GameStatus
from core.move import Move
from core.piece import PIECE_TOTAL, Piece, PieceType, Side
from core.position import Position
from rules.dark_chess_rules import DarkChessRules, _TYPE_ORDER, position_template_type
from rules.piece_move_generator import is_square_attacked, kings_facing, pseudo_targets
from ai.chess_engine import EngineResult
from ai.evaluation import CROSSED_PAWN_BONUS, PIECE_VALUE

MATE = 1_000_000
MATE_LIMIT = MATE - 10_000

# 宽度控制：根节点/内部节点考虑的前 N 个走法（吃子经排序天然排前）。
# 经实测 (64,10) 让中局揭棋在 2 秒内可达 4 层；(96,16) 只能 3 层。
ROOT_CAP = 64
INTERIOR_CAP = 10
# 深度上限（实际受思考时间约束）
MAX_DARK_DEPTH = 6


# --------------------------------------------------------------------------
# 子力池计数：remaining = PIECE_TOTAL - onboard
# onboard = 已揭示在盘 + 已被吃（已“入账”），只随“揭示/撤销揭示”变化。
# --------------------------------------------------------------------------
def _empty_counts() -> Dict[PieceType, int]:
    return {t: 0 for t in PIECE_TOTAL}


def _init_onboard(state: GameState) -> Dict[Side, Dict[PieceType, int]]:
    ob = {Side.RED: _empty_counts(), Side.BLACK: _empty_counts()}
    for p in state.board.pieces():
        if p.revealed and not p.is_unknown:
            ob[p.side][p.piece_type] += 1
    for cp in state.captured_log:
        et = cp.effective_type
        if et.is_real:
            ob[cp.side][et] += 1
    return ob


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


class _DarkSearcher:
    """在单个可变棋盘上做揭棋搜索。"""

    def __init__(self, state: GameState) -> None:
        self.rules = DarkChessRules(state.dark_preset)
        self.preset = self.rules.preset
        self.board = state.board.clone()
        self.onboard = _init_onboard(state)
        self.turn = state.turn

    # ---------------- 子力查询 ----------------
    def _remaining(self, side: Side) -> Dict[PieceType, int]:
        d = {}
        for t, total in PIECE_TOTAL.items():
            n = total - self.onboard[side].get(t, 0)
            if n > 0:
                d[t] = n
        return d

    def _hidden_expected_value(self, side: Side) -> float:
        """该方一颗暗子的期望子力（按剩余子力均匀分布）。"""
        rem = self._remaining(side)
        total = sum(rem.values())
        if total <= 0:
            return 0.0
        return sum(PIECE_VALUE[t] * c for t, c in rem.items()) / total

    # ---------------- 走法生成（就地合法性） ----------------
    def _legal(self, mv: Move) -> bool:
        """把 mv 临时落到 self.board 上检查合法性后还原。"""
        board = self.board
        mover = board.get(mv.frm)
        if mover is None:
            return False
        captured = None
        if mv.frm != mv.to:
            captured = board.remove(mv.to)
            board.remove(mv.frm)
            mover.position = mv.to
            board.put(mover)
        if mv.has_reveal:
            mover.revealed = True
            mover.piece_type = mv.reveal_type  # type: ignore[assignment]
        ok = True
        if self.preset.revealed_king_facing and kings_facing(board):
            ok = False
        if ok:
            king = board.king_position(mv.side)
            if king is not None and self._attacked(king, mv.side.opponent):
                ok = False
        # 还原
        if mv.has_reveal:
            mover.revealed = False
            mover.piece_type = PieceType.UNKNOWN
        if mv.frm != mv.to:
            board.remove(mv.to)
            mover.position = mv.frm
            board.put(mover)
            if captured is not None:
                board.put(captured)
        return ok

    def _attacked(self, target: Position, by_side: Side) -> bool:
        """target 是否被 by_side 攻击（含暗子的位置模板威胁）。"""
        if is_square_attacked(self.board, target, by_side, relaxed_elephant_advisor=True):
            return True
        if not self.preset.dark_move_capture:
            return False
        for p in self.board.pieces_of(by_side):
            if p.revealed:
                continue
            ttype = position_template_type(p.side, p.position)
            if ttype is not None and self.preset.hidden_uses_position_template:
                synthetic = Piece(p.side, ttype, True, p.position)
                if target in pseudo_targets(self.board, synthetic, relaxed_elephant_advisor=True):
                    return True
            elif p.position.forward(by_side) == target:
                return True
        return False

    def _hidden_targets(self, piece: Piece) -> List[Position]:
        pos = piece.position
        ttype = position_template_type(piece.side, pos)
        if ttype is not None and self.preset.hidden_uses_position_template:
            synthetic = Piece(piece.side, ttype, True, pos)
            targets = pseudo_targets(self.board, synthetic, relaxed_elephant_advisor=True)
            if not self.preset.dark_move_capture:
                targets = [t for t in targets if self.board.get(t) is None]
            return targets
        if self.preset.dark_move_reveals:
            to = pos.forward(piece.side)
            if to.in_board():
                occ = self.board.get(to)
                if occ is None or (occ.side is not piece.side and self.preset.dark_move_capture):
                    return [to]
        return []

    def gen(self, side: Side, include_flip: bool = False) -> List[Move]:
        """生成 side 的合法具体走法（与 DarkChessRules 一致；默认不含原地翻子）。"""
        moves: List[Move] = []
        remaining = self._remaining(side) if not include_flip else self._remaining(side)
        cand_types = [t for t in _TYPE_ORDER if t in remaining]
        for piece in self.board.pieces_of(side):
            if piece.revealed:
                for to in pseudo_targets(self.board, piece, relaxed_elephant_advisor=True):
                    mv = Move(side, piece.position, to)
                    if self._legal(mv):
                        moves.append(mv)
            else:
                if include_flip and self.preset.allow_in_place_reveal:
                    for rt in cand_types:
                        mv = Move(side, piece.position, piece.position, reveal_type=rt)
                        if self._legal(mv):
                            moves.append(mv)
                if not self.preset.dark_move_reveals:
                    continue
                for to in self._hidden_targets(piece):
                    occ = self.board.get(to)
                    if occ is not None and occ.side is piece.side:
                        continue
                    for rt in cand_types:
                        mv = Move(side, piece.position, to, reveal_type=rt)
                        if self._legal(mv):
                            moves.append(mv)
        return moves

    # ---------------- make / unmake ----------------
    def make(self, mv: Move) -> Optional[Piece]:
        """执行走法（含揭示），返回被吃棋子（若有）。将/帅被吃时调用方判胜。"""
        board = self.board
        mover = board.get(mv.frm)
        captured = None
        if mv.frm != mv.to:
            captured = board.remove(mv.to)
            board.remove(mv.frm)
            mover.position = mv.to
            board.put(mover)
        if mv.has_reveal:
            mover.revealed = True
            mover.piece_type = mv.reveal_type  # type: ignore[assignment]
            self.onboard[mover.side][mv.reveal_type] += 1
        self.turn = self.turn.opponent
        return captured

    def unmake(self, mv: Move, captured: Optional[Piece]) -> None:
        board = self.board
        mover = board.get(mv.to if mv.frm != mv.to else mv.frm)
        if mv.has_reveal:
            mover.revealed = False
            mover.piece_type = PieceType.UNKNOWN
            self.onboard[mover.side][mv.reveal_type] -= 1  # type: ignore[assignment]
        if mv.frm != mv.to:
            board.remove(mv.to)
            mover.position = mv.frm
            board.put(mover)
            if captured is not None:
                board.put(captured)
        self.turn = self.turn.opponent

    # ---------------- 评估（红方为正，与 evaluate_state 口径一致） ----------------
    def eval_score(self) -> float:
        score = 0.0
        for p in self.board.pieces():
            if not p.revealed or p.is_unknown:
                continue
            v = PIECE_VALUE[p.piece_type]
            if p.piece_type is PieceType.PAWN and p.position.crossed_river(p.side):
                v += CROSSED_PAWN_BONUS
            score += v if p.side is Side.RED else -v
        for side in (Side.RED, Side.BLACK):
            hidden = [p for p in self.board.pieces_of(side) if not p.revealed]
            if not hidden:
                continue
            delta = self._hidden_expected_value(side) * len(hidden)
            score += delta if side is Side.RED else -delta
        return score

    def _eval_side(self, side: Side) -> float:
        v = self.eval_score()
        return v if side is Side.RED else -v

    # ---------------- 排序与宽度 ----------------
    def _ordered(self, moves: List[Move], side: Side) -> List[Move]:
        def key(mv: Move):
            cap_v = 0.0
            occ = self.board.get(mv.to) if mv.frm != mv.to else None
            if occ is not None:
                if occ.revealed and not occ.is_unknown:
                    cap_v = float(PIECE_VALUE[occ.piece_type])
                else:
                    cap_v = self._hidden_expected_value(occ.side)
            reveal_v = 0.0
            if mv.has_reveal:
                reveal_v = float(PIECE_VALUE.get(mv.reveal_type, 0)) * 0.4
            return (cap_v + reveal_v,)
        moves.sort(key=key, reverse=True)
        return moves

    def _cap(self, moves: List[Move], root: bool) -> List[Move]:
        n = ROOT_CAP if root else INTERIOR_CAP
        return moves[:n]

    # ---------------- 搜索 ----------------
    def search(self, time_limit_ms: int, max_depth: int,
               stop_event: Event) -> EngineResult:
        t0 = time.monotonic()
        side = self.turn
        root_moves = self._ordered(self.gen(side), side)[:ROOT_CAP]
        if not root_moves:
            return EngineResult(move=None, engine="builtin", note="无合法走法")
        deadline = time.monotonic() + time_limit_ms / 1000.0 if time_limit_ms > 0 else None
        ctx = _Ctx(deadline, stop_event)
        best_move: Optional[Move] = None
        best_score = float("-inf")
        reached = 0
        max_depth = max(1, min(max_depth, MAX_DARK_DEPTH))
        for depth in range(1, max_depth + 1):
            if ctx.aborted():
                break
            # 把上一轮最佳走法放最前，提升剪枝
            if best_move is not None:
                root_moves = [best_move] + [m for m in root_moves if m is not best_move]
            score, mv = self._root_iter(root_moves, side, depth, ctx)
            if mv is not None:
                best_move, best_score, reached = mv, score, depth
        mate_in = None
        if best_move is not None and best_score >= MATE_LIMIT and math.isfinite(best_score):
            mate_in = max(1, round((MATE - best_score) / 2))
        return EngineResult(
            move=best_move, score=best_score, depth=reached,
            time_ms=int((time.monotonic() - t0) * 1000), engine="builtin",
            pv=[best_move] if best_move else [], mate_in=mate_in,
        )

    def _root_iter(self, moves: List[Move], side: Side, depth: int,
                   ctx: _Ctx) -> Tuple[float, Optional[Move]]:
        alpha = float("-inf")
        best = float("-inf")
        best_mv: Optional[Move] = None
        processed = False
        for mv in moves:
            if ctx.aborted():
                break
            processed = True
            captured = self.make(mv)
            if self._captured_general(captured):
                child_score = -(MATE - 1)          # 对方无将，负
            else:
                # 标准根节点窗口：子节点 alpha=-inf、beta=-best
                child_score = self._negamax(depth - 1, float("-inf"), -alpha, 1, ctx)
            self.unmake(mv, captured)
            score = -child_score
            if score > best:
                best = score
                best_mv = mv
            if best > alpha:
                alpha = best
        return (best, best_mv) if processed else (0.0, None)

    def _negamax(self, depth: int, alpha: float, beta: float,
                 ply: int, ctx: _Ctx) -> float:
        ctx.nodes += 1
        if ctx.aborted():
            return 0.0
        side = self.turn
        if depth <= 0:
            return self._eval_side(side)
        moves = self._ordered(self.gen(side), side)
        if not moves:
            return -(MATE - ply)
        moves = self._cap(moves, root=False)
        best = float("-inf")
        processed = False
        for mv in moves:
            if ctx.aborted():
                break
            processed = True
            captured = self.make(mv)
            if self._captured_general(captured):
                child_score = -(MATE - (ply + 1))
            else:
                child_score = self._negamax(depth - 1, -beta, -alpha, ply + 1, ctx)
            self.unmake(mv, captured)
            sc = -child_score
            if sc > best:
                best = sc
            if best > alpha:
                alpha = best
            if alpha >= beta:
                break
        return best if processed else 0.0

    @staticmethod
    def _captured_general(captured: Optional[Piece]) -> bool:
        return bool(captured is not None and captured.revealed
                    and captured.piece_type is PieceType.GENERAL)


def dark_get_best_move(state: GameState, time_limit_ms: int,
                       max_depth: int, stop_event: Event) -> EngineResult:
    """揭棋最佳走法（内置快速搜索）。与 AlphaBetaEngine 接口一致。"""
    if state.mode is not GameMode.DARK or state.over or state.status is not GameStatus.PLAYING:
        return EngineResult(move=None, engine="builtin", note="棋局已结束，无法分析")
    searcher = _DarkSearcher(state)
    result = searcher.search(time_limit_ms, max_depth, stop_event)
    if result.move is not None and result.move.notation == "":
        result.move.notation = result.move.describe()
    return result
