import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.game_state import GameStatus
from core.piece import PieceType, Side
from rules import win_checker
from tests.helpers import empty_board, normal_state, put


def test_checkmate_via_win_checker():
    b = empty_board()
    put(b, Side.RED, PieceType.GENERAL, 9, 4)
    put(b, Side.RED, PieceType.ROOK, 0, 0)
    put(b, Side.RED, PieceType.ROOK, 1, 0)
    put(b, Side.BLACK, PieceType.GENERAL, 0, 4)
    st = normal_state(b, Side.BLACK)
    assert win_checker.is_in_check(st, Side.BLACK)
    assert not win_checker.has_legal_moves(st, Side.BLACK)
    assert win_checker.status(st) is GameStatus.RED_WIN