"""设置持久化（JSON，存于 %LOCALAPPDATA%/XiangqiAssistant）。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from models.settings import AppSettings


def default_settings_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "XiangqiAssistant" / "settings.json"


def load_settings(path: Optional[Path] = None) -> AppSettings:
    p = path or default_settings_path()
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return AppSettings.from_dict(json.load(f))
        except Exception:
            pass
    return AppSettings()


def save_settings(settings: AppSettings, path: Optional[Path] = None) -> None:
    p = path or default_settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(settings.to_dict(), f, ensure_ascii=False, indent=2)