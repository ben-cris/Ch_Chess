import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.game_state import GameMode, GameStatus
from core.piece import Side
from services.game_service import GameService
from services.move_input_service import MoveInputService
from services.save_service import load_game, save_game, state_to_dict


def test_save_load_roundtrip(tmp_path):
    svc = GameService()
    svc.new_game(GameMode.NORMAL, Side.RED)
    ok, msg, mv = MoveInputService.build_move(svc.current(), Side.RED, (6, 0), (5, 0))
    assert ok
    svc.apply_move(mv)
    ok, msg, mv2 = MoveInputService.build_move(svc.current(), Side.BLACK, (3, 0), (4, 0))
    assert ok
    svc.apply_move(mv2)
    p = tmp_path / "game.json"
    save_game(svc.current(), p)
    st2 = load_game(p)
    assert st2.mode is GameMode.NORMAL
    assert st2.turn is Side.RED
    assert len(st2.moves) == 2
    assert st2.board.count() == 32
    d1 = state_to_dict(svc.current())
    d2 = state_to_dict(st2)
    assert d1["move_history"] == d2["move_history"]


def test_save_load_dark_with_reveal(tmp_path):
    from core.board import new_dark_board
    from core.game_state import new_game
    from core.piece import PieceType
    from rules.dark_chess_rules import DarkChessRules
    import random
    st = new_game(GameMode.DARK, Side.RED, board=new_dark_board(random.Random(4)))
    ok, msg, mv = MoveInputService.build_move(st, Side.RED, (6, 0), (5, 0),
                                              reveal_type=PieceType.ROOK)
    assert ok
    st = DarkChessRules("preset_a").apply_move(st, mv)
    p = tmp_path / "dark.json"
    save_game(st, p)
    st2 = load_game(p)
    assert st2.mode is GameMode.DARK
    assert len(st2.reveal_history) == 1
    assert st2.board.count() == 32