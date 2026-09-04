"""棋局保存/加载（JSON）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core.board import Board
from core.events import CapturedPiece, RevealEvent
from core.game_state import GameMode, GameState, GameStatus
from core.move import Move
from core.piece import Piece, PieceType, Side
from core.position import Position
from rules.base_rules import rules_factory

SCHEMA_VERSION = 1


def _side(v: str) -> Side:
    return Side(v)


def _ptype(v: str) -> PieceType:
    return PieceType(v)


def _pos(v: List[int]) -> Position:
    return Position(int(v[0]), int(v[1]))


def _piece_dict(p: Piece) -> Dict[str, Any]:
    return {"side": p.side.value, "type": p.piece_type.value,
            "revealed": p.revealed, "pos": [p.position.row, p.position.col]}


def _captured_dict(c: CapturedPiece) -> Dict[str, Any]:
    return {"side": c.side.value, "type": c.piece_type.value, "revealed": c.revealed,
            "pos": [c.position.row, c.position.col],
            "disclosed": c.disclosed_type.value if c.disclosed_type else None}


def _move_dict(m: Move) -> Dict[str, Any]:
    return {"side": m.side.value, "frm": [m.frm.row, m.frm.col], "to": [m.to.row, m.to.col],
            "captured": _captured_dict(m.captured) if m.captured else None,
            "reveal_type": m.reveal_type.value if m.reveal_type else None,
            "notation": m.notation, "forced": m.forced}


def _reveal_dict(e: RevealEvent) -> Dict[str, Any]:
    return {"pos": [e.pos.row, e.pos.col], "side": e.side.value,
            "type": e.piece_type.value, "source": e.source, "note": e.note, "ts": e.ts}


def state_to_dict(state: GameState) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": state.mode.value,
        "user_side": state.user_side.value,
        "turn": state.turn.value,
        "dark_preset": state.dark_preset,
        "board": [_piece_dict(p) for p in state.board.pieces()],
        "move_history": [_move_dict(m) for m in state.moves],
        "reveal_history": [_reveal_dict(e) for e in state.reveal_history],
        "captured_log": [_captured_dict(c) for c in state.captured_log],
        "position_counts": dict(state.position_counts),
        "status": state.status.value,
        "game_over": state.over,
    }


def state_from_dict(d: Dict[str, Any]) -> GameState:
    if d.get("schema_version", 1) != SCHEMA_VERSION:
        raise ValueError("不支持的存档版本")
    board = Board()
    for pd in d.get("board", []):
        p = Piece(_side(pd["side"]), _ptype(pd["type"]), bool(pd["revealed"]), _pos(pd["pos"]))
        board.put(p)

    def _cap(cd: Dict[str, Any]) -> CapturedPiece:
        return CapturedPiece(
            side=_side(cd["side"]), piece_type=_ptype(cd["type"]),
            revealed=bool(cd["revealed"]), position=_pos(cd["pos"]),
            disclosed_type=_ptype(cd["disclosed"]) if cd.get("disclosed") else None,
        )

    moves: List[Move] = []
    for md in d.get("move_history", []):
        moves.append(Move(
            side=_side(md["side"]), frm=_pos(md["frm"]), to=_pos(md["to"]),
            captured=_cap(md["captured"]) if md.get("captured") else None,
            reveal_type=_ptype(md["reveal_type"]) if md.get("reveal_type") else None,
            notation=md.get("notation", ""), forced=bool(md.get("forced", False)),
        ))
    reveals = [RevealEvent(pos=_pos(rd["pos"]), side=_side(rd["side"]),
                           piece_type=_ptype(rd["type"]), source=rd.get("source", "user"),
                           note=rd.get("note", ""), ts=rd.get("ts", ""))
               for rd in d.get("reveal_history", [])]
    captured_log = [_cap(cd) for cd in d.get("captured_log", [])]
    counts = {str(k): int(v) for k, v in d.get("position_counts", {}).items()}
    state = GameState(
        mode=GameMode(d["mode"]),
        user_side=_side(d.get("user_side", "red")),
        turn=_side(d.get("turn", "red")),
        board=board,
        moves=moves,
        reveal_history=reveals,
        captured_log=captured_log,
        dark_preset=d.get("dark_preset", "preset_a"),
        status=GameStatus(d.get("status", "playing")),
        over=bool(d.get("game_over", False)),
        position_counts=counts,
    )
    # 用当前规则重算状态，避免旧档不一致
    rules = rules_factory(state.mode, state.dark_preset)
    state.status = rules.status(state)
    state.over = state.status.game_over
    return state


def save_game(state: GameState, path: str | Path) -> None:
    data = state_to_dict(state)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_game(path: str | Path) -> GameState:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return state_from_dict(data)