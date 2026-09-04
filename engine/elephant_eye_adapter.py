"""ElephantEye（UCCI）适配器：预留，与 Pikafish 同为 UCCI 协议。"""
from __future__ import annotations

from engine.pikafish_adapter import PikafishAdapter


class ElephantEyeAdapter(PikafishAdapter):
    name = "elephant_eye"