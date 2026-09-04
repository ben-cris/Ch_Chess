"""规则层：BaseRules 抽象 + 正常玩法/揭棋玩法实现。"""
from .base_rules import BaseRules, rules_factory
from .dark_presets import DarkPreset, get_preset
from .dark_chess_rules import DarkChessRules
from .normal_rules import NormalRules

__all__ = [
    "BaseRules", "rules_factory", "DarkPreset", "get_preset",
    "DarkChessRules", "NormalRules",
]