"""Pikafish 引擎集成测试：FEN/坐标、默认引擎解析、端到端走法。

未随包 Pikafish（engine/bin）时相关用例自动跳过，不影响其余测试。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from core.game_state import GameMode, new_game
from core.piece import PieceType, Side
from engine.engine_manager import (EngineManager, bundled_pikafish_path,
                                   resolve_engine)
from engine.pikafish_adapter import _parse_square, _square, board_to_fen
from models.settings import EngineSettings
from rules.normal_rules import NormalRules


# ---------- FEN 与坐标 ----------

def test_board_to_fen_initial_position():
    st = new_game(GameMode.NORMAL, Side.RED)
    fen = board_to_fen(st.board, st.turn)
    assert fen == "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"


def test_board_to_fen_black_to_move_uses_b():
    st = new_game(GameMode.NORMAL, Side.RED)
    fen = board_to_fen(st.board, Side.BLACK)
    assert fen.endswith(" b - - 0 1")


def test_square_mapping_roundtrip():
    for row, col in ((0, 0), (0, 4), (2, 7), (7, 7), (7, 4), (9, 3), (6, 2)):
        pos = _parse_square(_square(_Pos(row, col)))
        assert (pos.row, pos.col) == (row, col)


def _Pos(r, c):
    from core.position import Position
    return Position(r, c)


# ---------- 默认引擎解析 ----------

def test_resolve_engine_rules():
    has_bundled = bundled_pikafish_path() is not None
    # 揭棋永远内置
    assert resolve_engine("auto", is_dark=True) == "builtin"
    assert resolve_engine("pikafish", is_dark=True) == "builtin"
    # 显式选择
    assert resolve_engine("builtin", is_dark=False) == "builtin"
    assert resolve_engine("pikafish", is_dark=False) == "pikafish"
    assert resolve_engine("mock", is_dark=False) == "mock"
    # auto：有随包 pikafish → pikafish；没有 → builtin
    assert resolve_engine("auto", is_dark=False) == ("pikafish" if has_bundled else "builtin")
    assert resolve_engine(None, is_dark=False) == ("pikafish" if has_bundled else "builtin")


def test_engine_settings_default_is_auto():
    assert EngineSettings().engine == "auto"


# ---------- 端到端（需要随包二进制） ----------

pytestmark = pytest.mark.skipif(bundled_pikafish_path() is None,
                                reason="未随包 Pikafish（运行 scripts/fetch_pikafish.ps1）")


def test_bundled_engine_found_and_red_opening_legal():
    path = bundled_pikafish_path()
    assert path is not None and Path(path).is_file()
    from engine.pikafish_adapter import PikafishAdapter
    eng = PikafishAdapter(path)
    try:
        st = new_game(GameMode.NORMAL, Side.RED)
        res = eng.get_best_move(st, 1200, 24, None)
        assert res.move is not None
        assert NormalRules().is_legal(st, res.move)
        assert res.move.side is Side.RED
        assert res.engine == "pikafish"
        # 移动的应为红方炮（炮二平五或炮八平五皆为主流开局）
        piece = st.board.get(res.move.frm)
        assert piece is not None and piece.piece_type is PieceType.CANNON
    finally:
        eng.close()


def test_bundled_engine_black_reply_matches_manual_entry():
    from engine.pikafish_adapter import PikafishAdapter
    st = new_game(GameMode.NORMAL, Side.BLACK)
    rules = NormalRules()
    red = next(m for m in rules.generate_legal_moves(st, Side.RED)
               if (m.frm.row, m.frm.col) == (7, 7) and (m.to.row, m.to.col) == (7, 4))
    st = rules.apply_move(st, red)
    eng = PikafishAdapter(bundled_pikafish_path())
    try:
        res = eng.get_best_move(st, 1200, 24, None)
        assert res.move is not None and NormalRules().is_legal(st, res.move)
        assert res.move.side is Side.BLACK
    finally:
        eng.close()


def test_manager_uses_bundled_when_path_empty():
    eng = EngineManager.get_engine("pikafish", EngineSettings(engine="pikafish"))
    try:
        st = new_game(GameMode.NORMAL, Side.RED)
        res = eng.get_best_move(st, 1000, 20, None)
        assert res.move is not None and NormalRules().is_legal(st, res.move)
    finally:
        EngineManager.clear_cache()
