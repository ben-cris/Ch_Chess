"""明子几何走法原语：只关心“某类型明子在当前棋盘能到达哪些点”。

正常玩法直接使用；揭棋玩法对“已揭示明子”复用同一套逻辑，避免规则分叉。
"""
from __future__ import annotations

from typing import List

from core.board import Board
from core.piece import Piece, PieceType, Side
from core.position import COLS, Position, ROWS

_HORSE_OFFSETS = [
    (1, 2, 0, 1), (1, -2, 0, -1), (-1, 2, 0, 1), (-1, -2, 0, -1),
    (2, 1, 1, 0), (2, -1, 1, 0), (-2, 1, -1, 0), (-2, -1, -1, 0),
]
_ELEPHANT_OFFSETS = [(2, 2, 1, 1), (2, -2, 1, -1), (-2, 2, -1, 1), (-2, -2, -1, -1)]
_ADVISOR_OFFSETS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
_KING_OFFSETS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def _target(board: Board, pos: Position, side: Side) -> bool:
    p = board.get(pos)
    return p is None or p.side is not side


def rook_targets(board: Board, pos: Position, side: Side) -> List[Position]:
    res: List[Position] = []
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        r, c = pos.row + dr, pos.col + dc
        while 0 <= r < ROWS and 0 <= c < COLS:
            q = Position(r, c)
            p = board.get(q)
            if p is None:
                res.append(q)
            else:
                if p.side is not side:
                    res.append(q)
                break
            r += dr
            c += dc
    return res


def cannon_targets(board: Board, pos: Position, side: Side) -> List[Position]:
    res: List[Position] = []
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        r, c = pos.row + dr, pos.col + dc
        jumped = False
        while 0 <= r < ROWS and 0 <= c < COLS:
            q = Position(r, c)
            p = board.get(q)
            if p is None:
                if not jumped:
                    res.append(q)
            else:
                if not jumped:
                    jumped = True
                else:
                    if p.side is not side:
                        res.append(q)
                    break
            r += dr
            c += dc
    return res


def horse_targets(board: Board, pos: Position, side: Side) -> List[Position]:
    res: List[Position] = []
    for dr, dc, lr, lc in _HORSE_OFFSETS:
        leg = Position(pos.row + lr, pos.col + lc)
        if board.get(leg) is not None:
            continue  # 蹩马腿
        q = Position(pos.row + dr, pos.col + dc)
        if q.in_board() and _target(board, q, side):
            res.append(q)
    return res


def elephant_targets(board: Board, pos: Position, side: Side,
                     allow_cross: bool = False) -> List[Position]:
    res: List[Position] = []
    for dr, dc, lr, lc in _ELEPHANT_OFFSETS:
        leg = Position(pos.row + lr, pos.col + lc)
        if board.get(leg) is not None:
            continue  # 塞象眼
        q = Position(pos.row + dr, pos.col + dc)
        if not q.in_board():
            continue
        if not allow_cross:
            if side is Side.RED and q.row <= 4:
                continue  # 正常玩法：象不能过河
            if side is Side.BLACK and q.row >= 5:
                continue
        if _target(board, q, side):
            res.append(q)
    return res


def advisor_targets(board: Board, pos: Position, side: Side,
                    confine_to_palace: bool = True) -> List[Position]:
    res: List[Position] = []
    for dr, dc in _ADVISOR_OFFSETS:
        q = Position(pos.row + dr, pos.col + dc)
        if not q.in_board():
            continue
        if confine_to_palace and not q.in_palace(side):
            continue
        if _target(board, q, side):
            res.append(q)
    return res


def king_targets(board: Board, pos: Position, side: Side) -> List[Position]:
    res: List[Position] = []
    for dr, dc in _KING_OFFSETS:
        q = Position(pos.row + dr, pos.col + dc)
        if q.in_board() and q.in_palace(side) and _target(board, q, side):
            res.append(q)
    return res


def pawn_targets(board: Board, pos: Position, side: Side) -> List[Position]:
    res: List[Position] = []
    fwd = pos.forward(side)
    if fwd.in_board() and _target(board, fwd, side):
        res.append(fwd)
    if pos.crossed_river(side):
        for dc in (-1, 1):
            q = Position(pos.row, pos.col + dc)
            if q.in_board() and _target(board, q, side):
                res.append(q)
    return res


def pseudo_targets(board: Board, piece: Piece,
                   relaxed_elephant_advisor: bool = False) -> List[Position]:
    """某(已揭示)明子的全部可达点。暗子返回空（暗子规则由揭棋实现负责）。

    relaxed_elephant_advisor=True 时（揭棋规则）：士可出九宫、象可过河，
    将/帅仍限九宫。
    """
    if piece.is_unknown or not piece.revealed:
        return []
    pos = piece.position
    t = piece.piece_type
    if t is PieceType.ROOK:
        return rook_targets(board, pos, piece.side)
    if t is PieceType.CANNON:
        return cannon_targets(board, pos, piece.side)
    if t is PieceType.HORSE:
        return horse_targets(board, pos, piece.side)
    if t is PieceType.ELEPHANT:
        return elephant_targets(board, pos, piece.side, allow_cross=relaxed_elephant_advisor)
    if t is PieceType.ADVISOR:
        return advisor_targets(board, pos, piece.side,
                               confine_to_palace=not relaxed_elephant_advisor)
    if t is PieceType.GENERAL:
        return king_targets(board, pos, piece.side)
    if t is PieceType.PAWN:
        return pawn_targets(board, pos, piece.side)
    return []


def is_square_attacked(board: Board, target: Position, by_side: Side,
                       relaxed_elephant_advisor: bool = False) -> bool:
    """target 是否被 by_side 的已揭示明子攻击。"""
    for p in board.pieces_of(by_side):
        if not p.revealed or p.is_unknown:
            continue
        if target in pseudo_targets(board, p,
                                    relaxed_elephant_advisor=relaxed_elephant_advisor):
            return True
    return False


def kings_facing(board: Board) -> bool:
    """双方已揭示将/帅是否同列且中间无子（照面）。"""
    red = board.find(Side.RED, PieceType.GENERAL, revealed=True)
    black = board.find(Side.BLACK, PieceType.GENERAL, revealed=True)
    if red is None or black is None or red.col != black.col:
        return False
    lo, hi = sorted((red.row, black.row))
    for r in range(lo + 1, hi):
        if board.get(Position(r, red.col)) is not None:
            return False
    return True