"""中国象棋文字记谱生成（用于显示，不影响规则正确性）。"""
from __future__ import annotations

from core.board import Board
from core.move import Move
from core.piece import PieceType, Side

_FILE_CN = ["一", "二", "三", "四", "五", "六", "七", "八", "九"]
_NUM_CN = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]


def _file_number(side: Side, col: int) -> int:
    """记谱文件号：红方在下方时其右侧为 col8 → 红方文件号=9-col；
    黑方在下方(我执黑视角)时其右侧为 col0 → 黑方文件号=col+1。"""
    if side is Side.RED:
        return 9 - col
    return col + 1


def format_move(board: Board, move: Move) -> str:
    """依据走子前棋盘生成记谱。"""
    piece = board.get(move.frm)
    if piece is None:
        return ""
    if piece.is_unknown:
        if move.is_reveal_in_place:
            return f"{move.side.short}翻子"
        return f"{move.side.short}暗子行动"
    pt = piece.piece_type
    name = pt.notation_name(move.side)
    f0 = _file_number(move.side, move.frm.col)
    f1 = _file_number(move.side, move.to.col)
    if move.frm.row == move.to.row:
        return f"{name}{_FILE_CN[f0 - 1]}平{_FILE_CN[f1 - 1]}"
    forward = (move.to.row < move.frm.row) if move.side is Side.RED else (move.to.row > move.frm.row)
    verb = "进" if forward else "退"
    if pt in (PieceType.ROOK, PieceType.CANNON, PieceType.PAWN, PieceType.GENERAL):
        steps = abs(move.to.row - move.frm.row)
        return f"{name}{_FILE_CN[f0 - 1]}{verb}{_NUM_CN[steps]}"
    # 马/相/士/帅斜走：以落点文件记
    return f"{name}{_FILE_CN[f0 - 1]}{verb}{_FILE_CN[f1 - 1]}"