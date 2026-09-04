import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.game_state import GameMode
from core.piece import Side
from services.game_service import GameService
from services.move_input_service import MoveInputService


def make_service(mode=GameMode.NORMAL, user_side=Side.RED):
    svc = GameService()
    svc.new_game(mode, user_side)
    return svc


def record(svc, side, frm, to):
    ok, msg, move = MoveInputService.build_move(svc.current(), side,
                                                frm, to)
    assert ok, msg
    ok2, msg2 = svc.apply_move(move)
    assert ok2, msg2
    return move


def test_record_red_and_black_and_turn_switch():
    svc = make_service()
    record(svc, Side.RED, (6, 0), (5, 0))
    assert svc.current().turn is Side.BLACK
    record(svc, Side.BLACK, (3, 0), (4, 0))
    assert svc.current().turn is Side.RED


def test_record_black_first_with_turn_override():
    svc = make_service()
    # 用户执红，但现实中黑方先走：手动切到黑方再录入
    svc.set_turn(Side.BLACK)
    record(svc, Side.BLACK, (3, 0), (4, 0))
    assert svc.current().turn is Side.RED


def test_user_side_decides_analysis_target():
    svc = make_service(user_side=Side.BLACK)
    ok, msg = MoveInputService.validate_turn_for_analysis(svc.current())
    assert not ok  # 当前红方走，用户执黑
    record(svc, Side.RED, (6, 0), (5, 0))
    ok, msg = MoveInputService.validate_turn_for_analysis(svc.current())
    assert ok


def test_undo_redo():
    svc = make_service()
    record(svc, Side.RED, (6, 0), (5, 0))
    record(svc, Side.BLACK, (3, 0), (4, 0))
    assert len(svc.current().moves) == 2
    assert svc.undo()
    assert len(svc.current().moves) == 1
    assert svc.current().turn is Side.BLACK
    assert svc.redo()
    assert len(svc.current().moves) == 2


def test_illegal_move_rejected():
    svc = make_service()
    # 红兵(6,0) 后退非法
    ok, msg, move = MoveInputService.build_move(svc.current(), Side.RED,
                                                (6, 0), (7, 0))
    assert not ok
    assert len(svc.current().moves) == 0