"""揭棋快速搜索测试：走法集与规则一致、返回合法、能更深搜索、评分有限。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import random
import math

from core.board import new_dark_board
from core.game_state import GameMode, new_game
from core.piece import PieceType, Side
from rules.dark_chess_rules import DarkChessRules
from tests.helpers import empty_board, put

from ai.search import AlphaBetaEngine


def _norm(state, side, rules) -> set:
    out = set()
    for m in rules.generate_legal_moves(state, side):
        if m.is_reveal_in_place:
            continue
        rt = m.reveal_type.value if m.reveal_type is not None else -1
        out.add((m.frm.row, m.frm.col, m.to.row, m.to.col, rt))
    return out


def test_dark_fast_gen_matches_rules():
    from ai.dark_search import _DarkSearcher
    rng = random.Random(21)
    rules = DarkChessRules("preset_a")
    st = new_game(GameMode.DARK, Side.RED, board=new_dark_board(rng))
    for _ in range(6):
        if st.over:
            break
        searcher = _DarkSearcher(st)
        fast = {(m.frm.row, m.frm.col, m.to.row, m.to.col,
                 (m.reveal_type.value if m.reveal_type is not None else -1))
                for m in searcher.gen(st.turn)}
        assert fast == _norm(st, st.turn, rules)
        mv = [m for m in rules.generate_legal_moves(st, st.turn)
              if not m.is_reveal_in_place]
        if not mv:
            break
        st = rules.apply_move(st, rng.choice(mv))


def test_dark_engine_returns_legal_and_does_not_mutate():
    rng = random.Random(11)
    rules = DarkChessRules("preset_a")
    st = new_game(GameMode.DARK, Side.RED, board=new_dark_board(rng))
    for _ in range(8):
        mv = [m for m in rules.generate_legal_moves(st, st.turn)
              if not m.is_reveal_in_place]
        if not mv or st.over:
            break
        st = rules.apply_move(st, rng.choice(mv))
    snap = st.clone()
    res = AlphaBetaEngine().get_best_move(st, 2000, 6, None)
    assert res.move is not None
    assert rules.is_legal(snap, res.move)
    assert len(st.moves) == len(snap.moves)   # 未自动落子
    assert math.isfinite(res.score)           # 不再出现 inf 崩溃


def test_dark_engine_reaches_deeper_search_on_small_board():
    """小盘面（无暗子、走法少）应能稳定搜索到较深，验证快速搜索本身有效。"""
    b = empty_board()
    put(b, Side.RED, PieceType.GENERAL, 9, 3)
    put(b, Side.BLACK, PieceType.GENERAL, 0, 5)
    put(b, Side.RED, PieceType.ROOK, 9, 0)
    put(b, Side.BLACK, PieceType.ROOK, 0, 0)
    put(b, Side.RED, PieceType.CANNON, 7, 7)
    put(b, Side.BLACK, PieceType.CANNON, 2, 7)
    from core.game_state import GameState
    st = GameState(GameMode.DARK, Side.RED, Side.RED, b, dark_preset="preset_a")
    st.record_position()
    res = AlphaBetaEngine().get_best_move(st, 3000, 6, None)
    assert res.move is not None
    from rules.dark_chess_rules import DarkChessRules
    assert DarkChessRules("preset_a").is_legal(st, res.move)
    assert res.depth >= 3  # 小盘面应明显深于旧版（旧版中局仅 1 层）


def test_dark_ai_service_analyzes_user_side():
    from ai.ai_analysis_service import AIAnalysisService
    from models.settings import EngineSettings
    rng = random.Random(5)
    rules = DarkChessRules("preset_a")
    st = new_game(GameMode.DARK, Side.BLACK, board=new_dark_board(rng))
    # 红方走一步后轮到黑方（用户方）
    red_moves = [m for m in rules.generate_legal_moves(st, Side.RED)
                 if not m.is_reveal_in_place]
    st = rules.apply_move(st, red_moves[0])
    assert st.turn is Side.BLACK
    svc = AIAnalysisService(EngineSettings(engine="builtin", max_depth=4, time_limit_ms=1500))
    res = svc.analyze(st)
    assert res.move is not None and res.move.side is Side.BLACK
    assert rules.is_legal(st, res.move)
