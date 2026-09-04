"""引擎管理器：按名称创建/缓存引擎，校验外部引擎可用性。

默认引擎为 auto：正常玩法若检测到随包内置 Pikafish（engine/bin/pikafish）则自动使用，
否则退回内置搜索引擎；揭棋模式始终使用内置引擎。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from ai.chess_engine import ChessEngine
from models.settings import EngineSettings


class EngineUnavailable(Exception):
    pass


# 随包内置 Pikafish 的候选可执行文件名（按兼容性优先排序）
_BUNDLED_PIKAFISH_CANDIDATES: List[str] = [
    "pikafish-sse41-popcnt.exe",   # 近 15 年 x86-64 CPU 基本都支持
    "pikafish-avx2.exe",           # 需 AVX2；若 CPU 不支持启动会失败并自动降级
    "pikafish-bmi2.exe",
]


def bundled_pikafish_path() -> Optional[str]:
    """返回随包 Pikafish 可执行文件路径（engine/bin/pikafish/）。未随包时 None。"""
    base = Path(__file__).resolve().parent.parent / "engine" / "bin" / "pikafish"
    for name in _BUNDLED_PIKAFISH_CANDIDATES:
        p = base / name
        if p.is_file():
            return str(p)
    return None


def resolve_engine(name: Optional[str], is_dark: bool) -> str:
    """把设置里的引擎名解析为实际使用的引擎。

    - 揭棋：始终内置（Pikafish 仅支持正常明子局面）；
    - auto/空：正常玩法有随包 Pikafish 则用它，否则内置；
    - 显式 builtin/pikafish/elephant_eye/mock：原样使用。
    """
    name = (name or "auto").lower()
    if is_dark or name == "builtin":
        return "builtin"
    if name in ("auto", ""):
        return "pikafish" if bundled_pikafish_path() else "builtin"
    if name == "mock":
        return "mock"
    if name in ("pikafish", "elephant_eye"):
        return name
    return "builtin"


class EngineManager:
    _cache: Dict[str, ChessEngine] = {}

    @classmethod
    def get_engine(cls, name: str, settings: EngineSettings) -> ChessEngine:
        name = name or "builtin"
        if name == "pikafish":
            path = settings.pikafish_path or bundled_pikafish_path() or ""
        elif name == "elephant_eye":
            path = settings.elephant_eye_path or ""
        else:
            path = ""
        key = name if name in ("builtin", "mock") else f"{name}:{path}"
        if key in cls._cache:
            return cls._cache[key]
        if name == "mock":
            from engine.mock_engine import MockEngine
            engine: ChessEngine = MockEngine()
        elif name == "builtin":
            from ai.search import AlphaBetaEngine
            engine = AlphaBetaEngine()
        elif name in ("pikafish", "elephant_eye"):
            if not path or not os.path.isfile(path):
                raise EngineUnavailable(f"{name} 引擎文件不存在: {path or '(未设置)'}")
            if name == "pikafish":
                from engine.pikafish_adapter import PikafishAdapter
                engine = PikafishAdapter(path)
            else:
                from engine.elephant_eye_adapter import ElephantEyeAdapter
                engine = ElephantEyeAdapter(path)
        else:
            raise EngineUnavailable(f"未知引擎: {name}")
        cls._cache[key] = engine
        return engine

    @classmethod
    def clear_cache(cls) -> None:
        for e in cls._cache.values():
            try:
                e.close()
            except Exception:
                pass
        cls._cache.clear()