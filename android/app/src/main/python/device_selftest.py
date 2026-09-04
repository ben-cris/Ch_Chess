# -*- coding: utf-8 -*-
"""M0 手机端 Python 自检：验证 core/rules/ai 在安卓(Chaquopy Python 3.11)上可用。

run_self_test() 返回人眼可读的多行文本，末尾 SELF_TEST PASS/FAIL。
该文件也可在 PC 上用 3.11/3.13 运行（把仓库根加入 sys.path 后 import 即可）。
"""
from __future__ import annotations

import json
import random
from typing import List


def _check(name: str, fn) -> dict:
    try:
        detail = fn()
        return {"name": name, "ok": True, "detail": str(detail)}
    except Exception as exc:
        return {"name": name, "ok": False, "detail": f"{type(exc).__name__}: {exc}"}


def _normal_check() -> str:
    from core.board import new_normal_board
    from core.game_state import new_game, GameMode
    from core.piece import Side
    from rules.normal_rules import NormalRules

    rules = NormalRules()
    st = new_game(GameMode.NORMAL, Side.RED)
    n = st.board.count()
    assert n == 32, f"初始棋子数应为 32，实际 {n}"
    moves = rules.generate_legal_moves(st, Side.RED)
    assert len(moves) >= 40, f"红方开局合法走法应很多，实际 {len(moves)}"
    mv = moves[0]
    after = rules.apply_move(st, mv)
    assert after.turn is Side.BLACK, "走子后应轮到黑方"
    assert len(after.moves) == 1 and after.board.count() == 32
    return f"初始 32 子；红方合法走法 {len(moves)}；首步后轮黑 ✓"


def _dark_check() -> str:
    from core.board import new_dark_board
    from core.game_state import new_game, GameMode
    from core.piece import Side
    from rules.dark_chess_rules import DarkChessRules

    rules = DarkChessRules("preset_a")
    st = new_game(GameMode.DARK, Side.RED, board=new_dark_board(random.Random(1)))
    moves = rules.generate_legal_moves(st, Side.RED)
    assert len(moves) > 0, "揭棋开局应有合法走法"
    mv = next((m for m in moves if not m.is_reveal_in_place and m.reveal_type is not None), None)
    assert mv is not None, "应存在带揭示身份的暗子行动"
    before_reveals = len(st.reveal_history)
    after = rules.apply_move(st, mv)
    assert after.turn is Side.BLACK, "揭棋走子后应轮对方"
    assert len(after.reveal_history) == before_reveals + 1, "应记录一条揭示事件"
    return f"揭棋合法走法 {len(moves)}；暗子行动+揭示事件记录 ✓"


def _ai_normal_check() -> str:
    from core.board import Board
    from core.game_state import GameMode, GameState
    from core.piece import Piece, PieceType, Side
    from core.position import Position
    from rules.normal_rules import NormalRules
    from ai.search import AlphaBetaEngine

    b = Board()
    b.put(Piece(Side.RED, PieceType.GENERAL, True, Position(9, 3)))
    b.put(Piece(Side.BLACK, PieceType.GENERAL, True, Position(0, 5)))
    b.put(Piece(Side.RED, PieceType.ROOK, True, Position(9, 0)))
    b.put(Piece(Side.BLACK, PieceType.ROOK, True, Position(0, 0)))
    b.put(Piece(Side.RED, PieceType.CANNON, True, Position(7, 7)))
    b.put(Piece(Side.BLACK, PieceType.CANNON, True, Position(2, 7)))
    st = GameState(GameMode.NORMAL, Side.RED, Side.RED, b)
    st.record_position()
    before = {p.position: (p.side, p.piece_type, p.revealed) for p in st.board.pieces()}
    res = AlphaBetaEngine().get_best_move(st, 300, 6, None)
    assert res.move is not None and res.depth >= 2, "内置搜索应给出 2 层以上结果"
    assert NormalRules().is_legal(st, res.move), "返回走法必须合法"
    now = {p.position: (p.side, p.piece_type, p.revealed) for p in st.board.pieces()}
    assert now == before and len(st.moves) == 0, "AI 不得改动输入局面"
    return f"内置 AI 返回合法走法（depth {res.depth}）且未改动局面 ✓"


def run_self_test() -> str:
    results: List[dict] = [
        _check("Python 版本", lambda: __import__("sys").version.split()[0]),
        _check("正常玩法 · 规则层", _normal_check),
        _check("揭棋 · 规则层", _dark_check),
        _check("内置 AI · 正常玩法", _ai_normal_check),
    ]
    lines = ["==== Ch_Chess Python 自检 (M0) ===="]
    for r in results:
        mark = "PASS" if r["ok"] else "FAIL"
        lines.append(f"[{mark}] {r['name']}: {r['detail']}")
    ok_all = all(r["ok"] for r in results)
    lines.append("SELF_TEST PASS" if ok_all else "SELF_TEST FAIL")
    return "\n".join(lines)


def run_self_test_json() -> str:
    results: List[dict] = [
        _check("Python 版本", lambda: __import__("sys").version.split()[0]),
        _check("正常玩法 · 规则层", _normal_check),
        _check("揭棋 · 规则层", _dark_check),
        _check("内置 AI · 正常玩法", _ai_normal_check),
    ]
    return json.dumps({"pass": all(r["ok"] for r in results), "items": results},
                      ensure_ascii=False)


if __name__ == "__main__":
    print(run_self_test())