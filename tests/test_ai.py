import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.game_state import GameMode, GameStatus
from core.piece import PieceType, Side
from models.settings import EngineSettings
from ai.ai_analysis_service import AIAnalysisService
from ai.search import AlphaBetaEngine
from tests.helpers import empty_board, normal_state, put

ENGINE = AlphaBetaEngine()


def test_engine_returns_legal_move_and_does_not_touch_state():
    from core.board import new_normal_board
    from core.game_state import new_game
    st = new_game(GameMode.NORMAL, Side.RED)
    before = len(st.moves)
    res = ENGINE.get_best_move(st, 0, 2, None)
    assert res.move is not None
    assert len(st.moves) == before  # AI 不自动执行走法
    from rules.normal_rules import NormalRules
    assert NormalRules().is_legal(st, res.move)


def test_engine_finds_hanging_rook_capture():
    b = empty_board()
    put(b, Side.RED, PieceType.GENERAL, 9, 3)
    put(b, Side.BLACK, PieceType.GENERAL, 0, 5)
    put(b, Side.RED, PieceType.ROOK, 9, 0)
    put(b, Side.BLACK, PieceType.ROOK, 8, 0)  # 悬挂车：红车可直接吃
    st = normal_state(b, Side.RED)
    res = ENGINE.get_best_move(st, 0, 3, None)
    assert res.move is not None and res.move.is_capture
    assert (res.move.to.row, res.move.to.col) == (8, 0)


def test_ai_analysis_targets_user_side():
    svc = AIAnalysisService(EngineSettings(engine="mock", max_depth=1))
    from core.board import new_normal_board
    from core.game_state import new_game
    # 用户执黑；红走一步后轮到黑方 → 分析黑方
    st = new_game(GameMode.NORMAL, Side.BLACK)
    from rules.normal_rules import NormalRules
    st = NormalRules().apply_move(st, NormalRules().generate_legal_moves(st, Side.RED)[0])
    assert st.turn is Side.BLACK
    res = svc.analyze(st)
    assert res.move is not None and res.move.side is Side.BLACK


def test_engine_failure_falls_back_to_builtin():
    # 指定的 pikafish 路径不存在 → 自动降级内置，程序不崩溃
    svc = AIAnalysisService(EngineSettings(engine="pikafish",
                                           pikafish_path="Z:/__no_such__/pikafish.exe",
                                           max_depth=2, time_limit_ms=200))
    from core.board import new_normal_board
    from core.game_state import new_game
    st = new_game(GameMode.NORMAL, Side.RED)
    res = svc.analyze(st)
    assert res.move is not None  # 未崩溃，降级内置成功
    assert res.engine == "builtin"


def test_simple_checkmate_detected_by_service():
    b = empty_board()
    put(b, Side.RED, PieceType.GENERAL, 9, 4)
    put(b, Side.RED, PieceType.ROOK, 0, 0)
    put(b, Side.RED, PieceType.ROOK, 1, 0)
    put(b, Side.BLACK, PieceType.GENERAL, 0, 4)
    st = normal_state(b, Side.BLACK)
    from rules import win_checker
    st.status = win_checker.status(st)
    st.over = st.status.game_over
    svc = AIAnalysisService(EngineSettings(engine="builtin", max_depth=1, time_limit_ms=100))
    res = svc.analyze(st)
    assert res.move is None
    assert "结束" in res.note


def test_dark_ai_returns_legal_recommendation():
    from core.board import new_dark_board
    from core.game_state import new_game
    import random
    st = new_game(GameMode.DARK, Side.RED, board=new_dark_board(random.Random(3)))
    svc = AIAnalysisService(EngineSettings(engine="builtin", max_depth=1, time_limit_ms=200))
    res = svc.analyze(st)
    if res.move is not None:
        from rules.dark_chess_rules import DarkChessRules
        assert DarkChessRules("preset_a").is_legal(st, res.move)
        assert len(st.moves) == 0  # 未自动落子