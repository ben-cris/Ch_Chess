"""揭棋规则预置。

预置 A（默认）核心语义（2026-09 用户确认版）：
- 暗子（未揭示）的“第一步/暗子行动”按该子所在位置原本棋子的走法（位置模板）执行；
  例如位于炮位的暗子按炮的走法行动。
- 暗子移动或吃子后必须揭示身份（由用户选择），此后按真实身份走。
- 可原地翻子（算一步）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class DarkPreset:
    name: str
    hidden_uses_position_template: bool = True  # 暗子按所在初始格原兵种走法行动
    allow_in_place_reveal: bool = True          # 允许原地翻子（算一步）
    dark_move_reveals: bool = True              # 暗子行动后必须揭示
    dark_move_capture: bool = True              # 暗子（按模板）可吃子
    revealed_king_facing: bool = True           # 已揭示将/帅之间适用照面
    capture_king_wins: bool = True              # 吃掉将/帅即胜


PRESETS: Dict[str, DarkPreset] = {
    "preset_a": DarkPreset(name="preset_a"),
}


def get_preset(name: str) -> DarkPreset:
    if name not in PRESETS:
        raise ValueError(f"未知揭棋规则预置: {name}")
    return PRESETS[name]