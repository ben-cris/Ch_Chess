"""应用与引擎设置。"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict

DEFAULT_ENGINE = "auto"  # auto=有内置 Pikafish 则优先，否则内置；也可显式 builtin/pikafish


@dataclass
class EngineSettings:
    engine: str = DEFAULT_ENGINE            # auto | builtin | pikafish | elephant_eye | mock
    pikafish_path: str = ""
    elephant_eye_path: str = ""
    time_limit_ms: int = 2000              # 每步思考时间上限
    # 深度上限：内置引擎受时间限制实际只到数层；Pikafish 会用它跑满思考时间
    max_depth: int = 64

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EngineSettings":
        kw = {k: d[k] for k in cls.__dataclass_fields__ if k in d}
        return cls(**kw)


@dataclass
class AppSettings:
    engine: EngineSettings = field(default_factory=EngineSettings)
    last_dir: str = ""
    auto_play: bool = True  # 对家走完后自动代走我方最优步

    def to_dict(self) -> Dict[str, Any]:
        return {"engine": self.engine.to_dict(), "last_dir": self.last_dir,
                "auto_play": self.auto_play}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AppSettings":
        eng = EngineSettings.from_dict(d.get("engine", {}))
        return cls(engine=eng, last_dir=d.get("last_dir", ""),
                   auto_play=bool(d.get("auto_play", True)))