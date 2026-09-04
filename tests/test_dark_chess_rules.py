import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import random

from core.board import new_dark_board
from core.game_state import GameMode, new_game
from core.move import Move
from core.piece import PieceType, Side
from core.position import Position
from rules.dark_chess_rules import DarkChessRules
from services.game_service import GameService
from services.move_input_service import MoveInputService

RULES = DarkChessRules("preset_a")


def test_dark_initial_state():
    from core.game_state import new_game
    from core.piece import PieceType
    st = new_game(GameMode.DARK, Side.RED, board=new_dark_board(random.Random(1)))
    hidden = [p for p in st.board.pieces() if not p.revealed]
    generals = [p for p in st.board.pieces() if p.revealed]
    assert len(hidden) == 30
    assert len(generals) == 2
    assert all(p.piece_type is PieceType.GENERAL for p in generals)


def test_unknown_piece_cannot_move_without_reveal_identity():
    st = new_game(GameMode.DARK, Side.RED, board=new_dark_board(random.Random(1)))
    ok, msg, move = MoveInputService.build_move(st, Side.RED, (6, 0), (5, 0))
    assert not ok
    assert "身份" in msg


def test_dark_move_with_reveal_applies():
    st = new_game(GameMode.DARK, Side.RED, board=new_dark_board(random.Random(1)))
    ok, msg, move = MoveInputService.build_move(st, Side.RED, (6, 0), (5, 0),
                                                reveal_type=PieceType.ROOK)
    assert ok, msg
    nxt = RULES.apply_move(st, move)
    p = nxt.board.get(Position(5, 0))
    assert p is not None and p.revealed and p.piece_type is PieceType.ROOK
    assert nxt.turn is Side.BLACK
    assert len(nxt.reveal_history) == 1


def test_reveal_identity_must_be_valid_count():
    st = new_game(GameMode.DARK, Side.RED, board=new_dark_board(random.Random(1)))
    # 已揭示两个车后再把另一个暗子设为车 → 剩余 0，应被拒绝（构造：先揭示两个车）
    for _ in range(2):
        # 找两个不同位置的暗子都设为车
        cand = None
        for p in st.board.pieces_of(Side.RED):
            if not p.revealed and p.position.row == 9:
                cand = p
                break
        ok, msg, mv = MoveInputService.build_move(st, Side.RED, cand.position, cand.position,
                                                  reveal_type=PieceType.ROOK)
        assert ok, msg
        st = RULES.apply_move(st, mv)
    some = [p for p in st.board.pieces_of(Side.RED) if not p.revealed][0]
    ok, msg, _ = MoveInputService.build_move(st, Side.RED, some.position, some.position,
                                             reveal_type=PieceType.ROOK)
    assert not ok


def test_dark_apply_requires_reveal_identity():
    st = new_game(GameMode.DARK, Side.RED, board=new_dark_board(random.Random(1)))
    mv = Move(Side.RED, Position(6, 0), Position(5, 0))
    try:
        RULES.apply_move(st, mv)
        assert False, "应抛出异常"
    except ValueError:
        pass


def test_dark_capture_hidden_victim():
    st = new_game(GameMode.DARK, Side.RED, board=new_dark_board(random.Random(1)))
    # 在(5,0)放置黑方暗子，红(6,0)前进一步吃掉并揭示
    st.board.put(__import__('core.piece', fromlist=['Piece']).Piece(
        Side.BLACK, PieceType.UNKNOWN, False, Position(5, 0)))
    ok, msg, move = MoveInputService.build_move(
        st, Side.RED, (6, 0), (5, 0), reveal_type=PieceType.CANNON,
        disclosed_type=PieceType.HORSE)
    assert ok, msg
    nxt = RULES.apply_move(st, move)
    assert nxt.board.get(Position(5, 0)) is not None  # 红炮在此
    assert nxt.board.get(Position(5, 0)).piece_type is PieceType.CANNON
    assert len(nxt.captured_log) == 1
    assert nxt.captured_log[0].disclosed_type is PieceType.HORSE


def test_service_dark_full_round():
    svc = GameService()
    svc.new_game(GameMode.DARK, Side.RED)
    # 红暗子(6,0)前进一步揭示为马
    ok, msg, mv = MoveInputService.build_move(svc.current(), Side.RED, (6, 0), (5, 0),
                                              reveal_type=PieceType.HORSE)
    assert ok, msg
    ok2, msg2 = svc.apply_move(mv)
    assert ok2, msg2
    assert svc.current().turn is Side.BLACK
    # 黑暗子(3,0)前进一步揭示为炮
    ok, msg, mv2 = MoveInputService.build_move(svc.current(), Side.BLACK, (3, 0), (4, 0),
                                               reveal_type=PieceType.CANNON)
    assert ok, msg
    ok2, msg2 = svc.apply_move(mv2)
    assert ok2, msg2
    assert svc.current().turn is Side.RED
    assert len(svc.current().moves) == 2

def test_hidden_cannon_position_moves_like_cannon():
    """暗子在炮位：第一步按炮的走法（可平移、可隔子吃）。"""
    import random
    from core.board import new_dark_board
    from core.game_state import new_game
    st = new_game(GameMode.DARK, Side.RED, board=new_dark_board(random.Random(7)))
    # (7,1) 是红炮初始位 → 平移 (7,1)->(7,4)
    ok, msg, mv = MoveInputService.build_move(st, Side.RED, (7, 1), (7, 4),
                                              reveal_type=PieceType.ROOK)
    assert ok, msg
    nxt = RULES.apply_move(st, mv)
    p = nxt.board.get(Position(7, 4))
    assert p is not None and p.revealed and p.piece_type is PieceType.ROOK
    # 隔子吃：红(7,1)炮位暗子 借黑炮(2,1)为炮架 吃黑(0,1)暗子
    ok2, msg2, mv2 = MoveInputService.build_move(st, Side.RED, (7, 1), (0, 1),
                                                 reveal_type=PieceType.CANNON,
                                                 disclosed_type=PieceType.HORSE)
    assert ok2, msg2
    nxt2 = RULES.apply_move(st, mv2)
    assert nxt2.board.get(Position(0, 1)) is not None
    assert nxt2.board.get(Position(0, 1)).piece_type is PieceType.CANNON


def test_hidden_rook_position_moves_like_rook():
    """暗子在车位的暗子按车走，且不能越过挡子。"""
    import random
    from core.board import new_dark_board
    from core.game_state import new_game
    st = new_game(GameMode.DARK, Side.RED, board=new_dark_board(random.Random(8)))
    # 先移开己方(6,0)兵，使车路畅通（否则会被己方兵挡住，属正常规则）
    st.board.remove(Position(6, 0))
    ok, msg, mv = MoveInputService.build_move(st, Side.RED, (9, 0), (8, 0),
                                              reveal_type=PieceType.ROOK)
    assert ok, msg
    # 黑(3,0)暗兵挡路：(9,0)车位暗子可吃(3,0)，但不能越过到(2,0)
    ok2, msg2, mv2 = MoveInputService.build_move(st, Side.RED, (9, 0), (3, 0),
                                                 reveal_type=PieceType.ROOK,
                                                 disclosed_type=PieceType.PAWN)
    assert ok2, msg2
    ok3, msg3, _ = MoveInputService.build_move(st, Side.RED, (9, 0), (2, 0),
                                               reveal_type=PieceType.ROOK)
    assert not ok3

def test_dark_advisor_can_leave_palace():
    """揭棋：士/仕可出九宫（正常玩法不可，见 normal 测试）。"""
    from tests.helpers import dark_state, empty_board, put
    from core.piece import PieceType, Side as S
    b = empty_board()
    put(b, S.RED, PieceType.GENERAL, 9, 4)
    put(b, S.BLACK, PieceType.GENERAL, 0, 5)
    put(b, S.RED, PieceType.ADVISOR, 9, 3)
    st = dark_state(b, S.RED)
    ok, msg, mv = MoveInputService.build_move(st, S.RED, (9, 3), (8, 2))
    assert ok, msg  # (8,2) 在九宫(col3-5)之外 → 已出九宫


def test_dark_elephant_can_cross_river():
    """揭棋：象/相可过河（正常玩法不可）。"""
    from tests.helpers import dark_state, empty_board, put
    from core.piece import PieceType, Side as S
    b = empty_board()
    put(b, S.RED, PieceType.GENERAL, 9, 4)
    put(b, S.BLACK, PieceType.GENERAL, 0, 5)
    put(b, S.RED, PieceType.ELEPHANT, 5, 2)
    st = dark_state(b, S.RED)
    # 红相 (5,2) -> (3,4)：越过河界到黑方半场（row<=4）
    ok, msg, mv = MoveInputService.build_move(st, S.RED, (5, 2), (3, 4))
    assert ok, msg


def test_dark_general_stays_in_palace():
    """揭棋：将/帅仍只能在九宫内走动。"""
    from tests.helpers import dark_state, empty_board, put
    from core.piece import PieceType, Side as S
    b = empty_board()
    put(b, S.RED, PieceType.GENERAL, 7, 4)
    put(b, S.BLACK, PieceType.GENERAL, 0, 5)
    st = dark_state(b, S.RED)
    ok, msg, _ = MoveInputService.build_move(st, S.RED, (7, 4), (6, 4))
    assert not ok  # 出九宫非法
    ok2, msg2, _ = MoveInputService.build_move(st, S.RED, (7, 4), (8, 4))
    assert ok2, msg2  # 九宫内可走