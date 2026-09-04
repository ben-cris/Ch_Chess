import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.board import new_dark_board, new_normal_board
from core.piece import PieceType, Side


def test_initial_layout_count():
    b = new_normal_board()
    assert b.count() == 32
    assert len(b.pieces_of(Side.RED)) == 16
    assert len(b.pieces_of(Side.BLACK)) == 16


def test_initial_key_positions():
    b = new_normal_board()
    assert b.find(Side.RED, PieceType.GENERAL) is not None
    assert b.find(Side.BLACK, PieceType.GENERAL) is not None
    red_pawns = [p for p in b.pieces_of(Side.RED) if p.piece_type is PieceType.PAWN]
    assert len(red_pawns) == 5


def test_dark_board_generals_fixed_and_others_hidden():
    """揭棋：将/帅固定原位亮明，其余 15 子/方暗置。"""
    b = new_dark_board()
    assert b.count() == 32
    red_gen = b.find(Side.RED, PieceType.GENERAL)
    black_gen = b.find(Side.BLACK, PieceType.GENERAL)
    assert red_gen is not None and (red_gen.row, red_gen.col) == (9, 4)
    assert black_gen is not None and (black_gen.row, black_gen.col) == (0, 4)
    hidden = [p for p in b.pieces() if not p.revealed]
    revealed = [p for p in b.pieces() if p.revealed]
    assert len(hidden) == 30
    assert len(revealed) == 2
    assert all(p.piece_type is PieceType.GENERAL for p in revealed)