"""开局库（Opening Book）测试：常见棋谱解析、命中与合法性。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from core.game_state import GameMode, new_game
from core.piece import Side
from rules.normal_rules import NormalRules

from ai.opening_book import BOOK_LINES, OpeningBook, get_book


@pytest.fixture(scope="module")
def book() -> OpeningBook:
    return OpeningBook()


def test_all_book_lines_parse(book: OpeningBook) -> None:
    # 每条棋谱要么完整走通、要么保留可走通前缀；不能整行失败
    assert book.failed == 0
    assert book.loaded + book.partial == len(BOOK_LINES)
    assert book.loaded >= len(BOOK_LINES) - 1
    assert len(book) > 0


def test_book_hits_standard_opening(book: OpeningBook) -> None:
    st = new_game(GameMode.NORMAL, Side.RED)
    pair = book.first(st)
    assert pair is not None
    # 红方第一步主流 = 炮二平五：右炮平至中路 (row 7, col 7) -> (row 7, col 4)
    assert (pair[0].row, pair[0].col, pair[1].row, pair[1].col) == (7, 7, 7, 4)


def test_book_entry_moves_are_legal(book: OpeningBook) -> None:
    st = new_game(GameMode.NORMAL, Side.RED)
    rules = NormalRules()
    legal = {(m.frm, m.to) for m in rules.generate_legal_moves(st, Side.RED)}
    for pair in book.lookup(st) or []:
        assert pair in legal


def test_follow_book_until_exhausted(book: OpeningBook) -> None:
    """双方交替走书招，直到离开棋谱；走过的每一步都必须合法。"""
    st = new_game(GameMode.NORMAL, Side.RED)
    rules = NormalRules()
    plies = 0
    while not st.over:
        pair = book.first(st)
        if pair is None:
            break
        mv = next(m for m in rules.generate_legal_moves(st, st.turn)
                  if (m.frm, m.to) == pair)
        st = rules.apply_move(st, mv)
        plies += 1
    assert plies >= 10  # 至少覆盖 5 个回合的主流开局


def test_book_returns_none_for_nonbook_position(book: OpeningBook) -> None:
    st = new_game(GameMode.NORMAL, Side.RED)
    rules = NormalRules()
    # 红走“炮八平五”（左炮平中）——不在收录棋谱内
    mv = next(m for m in rules.generate_legal_moves(st, Side.RED)
              if (m.frm.row, m.frm.col) == (7, 1) and (m.to.row, m.to.col) == (7, 4))
    st = rules.apply_move(st, mv)
    assert book.first(st) is None


def test_book_ignored_in_dark_mode(book: OpeningBook) -> None:
    from core.board import new_dark_board
    import random
    st = new_game(GameMode.DARK, Side.RED, board=new_dark_board(random.Random(7)))
    assert book.lookup(st) is None
    assert book.first(st) is None


def test_builtin_engine_returns_book_move_without_mutating_state(book: OpeningBook) -> None:
    from ai.search import AlphaBetaEngine
    st = new_game(GameMode.NORMAL, Side.RED)
    before = len(st.moves)
    res = AlphaBetaEngine().get_best_move(st, 0, 2, None)
    assert res.move is not None
    assert len(st.moves) == before          # AI 不自动落子
    assert NormalRules().is_legal(st, res.move)
    assert "开局库" in res.note
    # 引擎返回的正是棋谱首招
    first = book.first(st)
    assert (res.move.frm, res.move.to) == first


def test_engine_falls_back_to_search_outside_book() -> None:
    from ai.search import AlphaBetaEngine
    st = new_game(GameMode.NORMAL, Side.RED)
    rules = NormalRules()
    mv = next(m for m in rules.generate_legal_moves(st, Side.RED)
              if (m.frm.row, m.frm.col) == (7, 1) and (m.to.row, m.to.col) == (7, 4))
    st = rules.apply_move(st, mv)
    res = AlphaBetaEngine().get_best_move(st, 0, 2, None)
    assert res.move is not None
    assert NormalRules().is_legal(st, res.move)
    assert "开局库" not in (res.note or "")


def test_ai_service_uses_book_for_user_side() -> None:
    from ai.ai_analysis_service import AIAnalysisService
    from models.settings import EngineSettings
    st = new_game(GameMode.NORMAL, Side.RED)
    svc = AIAnalysisService(EngineSettings(engine="builtin", max_depth=2, time_limit_ms=100))
    res = svc.analyze(st)
    assert res.move is not None
    assert res.move.side is Side.RED
    assert res.engine == "builtin"
    assert "开局库" in (res.note or "")
    assert len(st.moves) == 0


def test_singleton_book_consistent() -> None:
    assert get_book() is get_book()
