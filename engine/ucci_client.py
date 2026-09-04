"""UCCI 协议子进程客户端（Pikafish / ElephantEye 通用）。

外部引擎为可选项；未配置或通信失败时上层会自动降级到内置引擎。
"""
from __future__ import annotations

import os
import queue
import re
import subprocess
import threading
from typing import List, Optional, Tuple


class UcciClient:
    def __init__(self, engine_path: str) -> None:
        self.path = engine_path
        self.proc: Optional[subprocess.Popen] = None
        self._q: "queue.Queue[str]" = queue.Queue()
        self._reader: Optional[threading.Thread] = None
        self.engine_name = ""
        self._lock = threading.Lock()

    def start(self) -> None:
        kwargs = {}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.proc = subprocess.Popen(
            [self.path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1, encoding="utf-8",
            cwd=os.path.dirname(os.path.abspath(self.path)) or None, **kwargs,
        )
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self.send("uci")
        deadline = self._wait_for("uciok", timeout=10.0)
        self.send("isready")
        self._wait_for("readyok", timeout=10.0)

    def _read_loop(self) -> None:
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            self._q.put(line.strip())

    def send(self, cmd: str) -> None:
        if self.proc is None or self.proc.stdin is None:
            raise RuntimeError("引擎未启动")
        with self._lock:
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()

    def _wait_for(self, token: str, timeout: float) -> List[str]:
        lines: List[str] = []
        try:
            while True:
                line = self._q.get(timeout=timeout)
                lines.append(line)
                if token in line:
                    if token == "uciok" and line.startswith("id name"):
                        self.engine_name = line.split("id name", 1)[1].strip()
                    return lines
        except queue.Empty:
            return lines

    def search(self, fen: str, depth: int, movetime_ms: int) -> Tuple[Optional[str], int, int, int]:
        """执行一次搜索。

        返回 (bestmove, depth, score_cp, mate)：
        - bestmove：UCCI 走法串（如 'h2e2'），失败为 None；
        - depth：搜索到的主线深度（info 中最高 depth）；
        - score_cp：该深度对应的分数（centipawn），mate 时无效；
        - mate：>0 表示轮到方 N 步杀，<0 表示轮到方将被 N 步杀，0 表示非杀棋。
        """
        self.send(f"position fen {fen}")
        self.send(f"go depth {depth} movetime {movetime_ms}")
        deadline = max(0.5, movetime_ms / 1000.0 + 1.0)
        info: dict = {"depth": -1, "cp": 0, "mate": 0}
        try:
            while True:
                line = self._q.get(timeout=deadline)
                if line.startswith("bestmove"):
                    parts = line.split()
                    mv = parts[1] if len(parts) > 1 else None
                    return mv, info["depth"], info["cp"], info["mate"]
                self._collect_info(line, info)
        except queue.Empty:
            try:
                self.send("stop")
                while True:
                    line = self._q.get(timeout=2.0)
                    if line.startswith("bestmove"):
                        parts = line.split()
                        mv = parts[1] if len(parts) > 1 else None
                        return mv, info["depth"], info["cp"], info["mate"]
                    self._collect_info(line, info)
            except queue.Empty:
                return None, info["depth"], info["cp"], info["mate"]
        return None, info["depth"], info["cp"], info["mate"]

    @staticmethod
    def _collect_info(line: str, info: dict) -> None:
        """从 info 行提取最高深度的 score cp/mate，供界面显示。"""
        try:
            md = re.search(r"\bdepth\s+(\d+)", line)
            ms = re.search(r"\bscore\s+(cp|mate)\s+(-?\d+)", line)
            if md is None or ms is None:
                return
            d = int(md.group(1))
            if d <= info["depth"]:
                return
            kind, val = ms.group(1), int(ms.group(2))
            info["depth"] = d
            if kind == "cp":
                info["cp"] = val
                info["mate"] = 0
            else:
                info["mate"] = val
                info["cp"] = 0
        except Exception:
            return

    def close(self) -> None:
        try:
            self.send("quit")
        except Exception:
            pass
        if self.proc is not None:
            try:
                self.proc.terminate()
            except Exception:
                pass