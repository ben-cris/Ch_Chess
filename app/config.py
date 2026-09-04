"""全局配置常量。"""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "象棋辅助工具"
APP_VERSION = "1.0.0"
ORG_NAME = "XiangqiAssistant"

ROWS = 10
COLS = 9


def data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    d = Path(base) / ORG_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_dir() -> Path:
    d = data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d