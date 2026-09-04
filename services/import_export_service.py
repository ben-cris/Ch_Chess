"""导入/导出（v1：正常玩法支持 FEN 导出/导入；揭棋暂不支持）。"""
from __future__ import annotations

from core.game_state import GameMode, GameState
from core.piece import Side
from engine.pikafish_adapter import board_to_fen


def export_fen(state: GameState) -> str:
    if state.mode is not GameMode.NORMAL:
        raise ValueError("揭棋不支持 FEN 导出")
    return board_to_fen(state.board, state.turn)


def export_fen_save(state: GameState, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(export_fen(state) + "\n")