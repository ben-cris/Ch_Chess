import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.game_state import GameStatus
from core.move import Move
from core.piece import PieceType, Side
from core.position import Position
from rules.normal_rules import NormalRules
from tests.helpers import empty_board, normal_state, put

R = NormalRules()


def can(board, side, frm, to):
    return R.is_legal(normal_state(board, side), Move(side, Position(*frm), Position(*to)))


def test_rook_cannot_jump():
    b = empty_board()
    put(b, Side.RED, PieceType.ROOK, 9, 0)
    put(b, Side.BLACK, PieceType.PAWN, 7, 0)
    assert not can(b, Side.RED, (9, 0), (6, 0))
    assert can(b, Side.RED, (9, 0), (8, 0))


def test_horse_leg_blocked():
    b = empty_board()
    put(b, Side.RED, PieceType.HORSE, 9, 1)
    put(b, Side.RED, PieceType.PAWN, 8, 1)
    assert not can(b, Side.RED, (9, 1), (7, 0))
    assert can(b, Side.RED, (9, 1), (8, 3))


def test_elephant_eye_and_river():
    b = empty_board()
    put(b, Side.RED, PieceType.ELEPHANT, 9, 2)
    put(b, Side.RED, PieceType.PAWN, 8, 3)
    assert not can(b, Side.RED, (9, 2), (7, 4))
    b2 = empty_board()
    put(b2, Side.RED, PieceType.ELEPHANT, 9, 2)
    assert can(b2, Side.RED, (9, 2), (7, 4))
    assert not can(b2, Side.RED, (7, 0), (5, 2))


def test_cannon_capture_needs_screen():
    b = empty_board()
    put(b, Side.RED, PieceType.CANNON, 7, 1)
    put(b, Side.BLACK, PieceType.PAWN, 5, 1)
    assert not can(b, Side.RED, (7, 1), (5, 1))
    b2 = empty_board()
    put(b2, Side.RED, PieceType.CANNON, 7, 1)
    put(b2, Side.RED, PieceType.PAWN, 6, 1)
    put(b2, Side.BLACK, PieceType.PAWN, 5, 1)
    assert can(b2, Side.RED, (7, 1), (5, 1))


def test_advisor_stays_in_palace():
    b = empty_board()
    put(b, Side.RED, PieceType.ADVISOR, 9, 4)
    assert can(b, Side.RED, (9, 4), (8, 3))
    # 士只能斜走，不能直走
    assert not can(b, Side.RED, (9, 4), (9, 5))
    # 士从九宫角落(8,3) 只能回(9,4)，不能斜到宫外(7,4 在宫内? 检查)：红九宫 row7-9,col3-5
    b2 = empty_board()
    put(b2, Side.RED, PieceType.ADVISOR, 8, 3)
    assert can(b2, Side.RED, (8, 3), (9, 4))
    # (8,3) 斜到 (7,2) 出九宫(col2<3) → 非法
    assert not can(b2, Side.RED, (8, 3), (7, 2))


def test_pawn_no_retreat_and_sideways_after_river():
    b = empty_board()
    put(b, Side.RED, PieceType.PAWN, 6, 0)
    assert not can(b, Side.RED, (6, 0), (7, 0))
    assert can(b, Side.RED, (6, 0), (5, 0))
    b2 = empty_board()
    put(b2, Side.RED, PieceType.PAWN, 4, 0)
    assert can(b2, Side.RED, (4, 0), (4, 1))
    assert not can(b2, Side.RED, (4, 1), (5, 1))


def test_flying_general_illegal():
    b = empty_board()
    put(b, Side.RED, PieceType.GENERAL, 9, 4)
    put(b, Side.BLACK, PieceType.GENERAL, 0, 4)
    assert not can(b, Side.RED, (9, 4), (8, 4))


def test_cannot_move_into_check():
    b = empty_board()
    put(b, Side.RED, PieceType.GENERAL, 9, 4)
    put(b, Side.BLACK, PieceType.ROOK, 0, 4)
    assert not can(b, Side.RED, (9, 4), (8, 4))


def test_check_detection():
    b = empty_board()
    put(b, Side.RED, PieceType.GENERAL, 9, 4)
    put(b, Side.RED, PieceType.ROOK, 0, 0)
    put(b, Side.BLACK, PieceType.GENERAL, 0, 4)
    st = normal_state(b, Side.BLACK)
    assert R.is_in_check(st, Side.BLACK)


def test_checkmate():
    b = empty_board()
    put(b, Side.RED, PieceType.GENERAL, 9, 4)
    put(b, Side.RED, PieceType.ROOK, 0, 0)
    put(b, Side.RED, PieceType.ROOK, 1, 0)
    put(b, Side.BLACK, PieceType.GENERAL, 0, 4)
    st = normal_state(b, Side.BLACK)
    assert R.is_in_check(st, Side.BLACK)
    assert not R.generate_legal_moves(st, Side.BLACK)
    assert R.status(st) is GameStatus.RED_WIN