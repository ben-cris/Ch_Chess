"""揭示身份规则测试（候选过滤、不可跳过、事件记录）。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import random

from core.board import new_dark_board
from core.game_state import GameMode, new_game
from core.piece import PieceType, Side
from core.position import Position
from rules.dark_chess_rules import DarkChessRules

RULES = DarkChessRules("preset_a")


def _game():
    return new_game(GameMode.DARK, Side.RED, board=new_dark_board(random.Random(2)))


def test_reveal_options_match_remaining():
    st = _game()
    opts = RULES.legal_reveal_types(st, Position(6, 0))
    assert PieceType.ROOK in opts
    # 将/帅固定在原位且已亮明，暗子不可能再翻出将/帅
    assert PieceType.GENERAL not in opts
    assert len(opts) == 6


def test_no_options_for_revealed_piece():
    st = _game()
    # 先揭示一个棋子
    ok, msg, mv = __import__('services.move_input_service', fromlist=['MoveInputService']).MoveInputService.build_move(
        st, Side.RED, (6, 0), (5, 0), reveal_type=PieceType.ROOK)
    nxt = RULES.apply_move(st, mv)
    assert RULES.legal_reveal_types(nxt, Position(5, 0)) == []


def test_reveal_history_recorded():
    st = _game()
    ok, msg, mv = __import__('services.move_input_service', fromlist=['MoveInputService']).MoveInputService.build_move(
        st, Side.RED, (6, 0), (5, 0), reveal_type=PieceType.CANNON)
    nxt = RULES.apply_move(st, mv)
    assert len(nxt.reveal_history) == 1
    ev = nxt.reveal_history[0]
    assert ev.piece_type is PieceType.CANNON
    assert ev.side is Side.RED