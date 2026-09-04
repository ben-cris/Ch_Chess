"""Pikafish（UCCI）适配器：仅用于正常玩法明子局面。

坐标转换约定（UCCI 标准）：
- FEN：首行 = 最上方黑方底线，即按 board row0..9 自顶向下输出；
- 走法坐标：文件 a-i 对应 col0-8（自左向右）；行号 0-9 自红方底线向上数，
  即 rank = 9 - row（红方底线 row9 → rank0，黑方底线 row0 → rank9）。
  红方右炮(7,7) 记为 h2，炮二平五 = h2e2。
外部引擎为可选：未配置/失败时由 AIAnalysisService 降级到内置引擎。
"""
from __future__ import annotations

from threading import Event
from typing import Optional

from core.board import Board
from core.game_state import GameState
from core.move import Move
from core.piece import PieceType, Side
from core.position import Position
from models.settings import EngineSettings
from rules.base_rules import rules_factory
from ai.chess_engine import ChessEngine, EngineResult
from engine.ucci_client import UcciClient

_PIECE_CHAR = {
    (Side.RED, PieceType.GENERAL): "K", (Side.RED, PieceType.ADVISOR): "A",
    (Side.RED, PieceType.ELEPHANT): "B", (Side.RED, PieceType.HORSE): "N",
    (Side.RED, PieceType.ROOK): "R", (Side.RED, PieceType.CANNON): "C",
    (Side.RED, PieceType.PAWN): "P",
    (Side.BLACK, PieceType.GENERAL): "k", (Side.BLACK, PieceType.ADVISOR): "a",
    (Side.BLACK, PieceType.ELEPHANT): "b", (Side.BLACK, PieceType.HORSE): "n",
    (Side.BLACK, PieceType.ROOK): "r", (Side.BLACK, PieceType.CANNON): "c",
    (Side.BLACK, PieceType.PAWN): "p",
}
_CHAR_PIECE = {v: k for k, v in _PIECE_CHAR.items()}


def board_to_fen(board: Board, turn_side: Side) -> str:
    rows = []
    for r in range(10):
        row = ""
        empty = 0
        for c in range(9):
            p = board.get(Position(r, c))
            if p is None or not p.revealed:
                empty += 1
                continue
            if empty:
                row += str(empty)
                empty = 0
            row += _PIECE_CHAR[(p.side, p.piece_type)]
        if empty:
            row += str(empty)
        rows.append(row if row else "9")
    side_char = "w" if turn_side is Side.RED else "b"
    return "/".join(rows) + f" {side_char} - - 0 1"


def _square(pos: Position) -> str:
    # UCCI 行号 0 在红方底线（row9），自下往上数
    return chr(ord("a") + pos.col) + str(9 - pos.row)


def _parse_square(s: str) -> Position:
    return Position(9 - int(s[1:]), ord(s[0]) - ord("a"))


class PikafishAdapter(ChessEngine):
    name = "pikafish"

    def __init__(self, path: str) -> None:
        self.client = UcciClient(path)
        self.client.start()
        self._path = path

    def configure(self, settings: EngineSettings) -> None:
        pass

    def get_best_move(self, state: GameState, time_limit_ms: int,
                      max_depth: int, stop_event: Event) -> EngineResult:
        if state.mode.value != "normal":
            raise RuntimeError("Pikafish 仅支持正常玩法明子局面")
        import time
        t0 = time.monotonic()
        fen = board_to_fen(state.board, state.turn)
        ucci_move, depth, cp, mate = self.client.search(fen, max_depth, time_limit_ms)
        if ucci_move is None or len(ucci_move) < 4:
            return EngineResult(move=None, engine=self.name,
                                depth=max(0, depth), time_ms=int((time.monotonic() - t0) * 1000),
                                note="引擎未返回走法")
        frm = _parse_square(ucci_move[0:2])
        to = _parse_square(ucci_move[2:4])
        rules = rules_factory(state.mode, state.dark_preset)
        # 找到对应的合法走法对象（坐标相等即可）
        move = None
        for m in rules.generate_legal_moves(state, state.turn):
            if m.frm == frm and m.to == to:
                move = m
                break
        if move is None:
            return EngineResult(move=None, engine=self.name,
                                depth=max(0, depth), time_ms=int((time.monotonic() - t0) * 1000),
                                note="引擎走法非法，已忽略")
        score, mate_in = 0.0, None
        if mate > 0:
            mate_in = mate
        elif mate < 0:
            score = -900000.0 - abs(mate)   # 轮到方将被杀：给极大负分
        else:
            score = cp * 1.2                # 引擎分(cp)换算到本程序子力分（兵=120）
        return EngineResult(
            move=move, score=score, depth=max(0, depth), mate_in=mate_in,
            time_ms=int((time.monotonic() - t0) * 1000), engine=self.name,
            pv=[move], note="",
        )

    def stop(self) -> None:
        try:
            self.client.send("stop")
        except Exception:
            pass

    def close(self) -> None:
        self.client.close()