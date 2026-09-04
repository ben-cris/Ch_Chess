"""AI 分析面板：推荐走法、评分、深度、时间、说明。"""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from models.analysis_result import AnalysisResult


class AnalysisPanel(QGroupBox):
    def __init__(self, parent=None) -> None:
        super().__init__("AI 推荐", parent)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.lbl_move = QLabel("—")
        self.lbl_score = QLabel("—")
        self.lbl_depth = QLabel("—")
        self.lbl_time = QLabel("—")
        self.lbl_engine = QLabel("—")
        self.lbl_note = QLabel("")
        self.lbl_note.setWordWrap(True)
        form.addRow("推荐走法", self.lbl_move)
        form.addRow("评分", self.lbl_score)
        form.addRow("搜索深度", self.lbl_depth)
        form.addRow("思考时间", self.lbl_time)
        form.addRow("引擎", self.lbl_engine)
        lay.addLayout(form)
        lay.addWidget(self.lbl_note)

    def show_result(self, r: Optional[AnalysisResult]) -> None:
        if r is None:
            self.lbl_move.setText("—")
            self.lbl_score.setText("—")
            self.lbl_depth.setText("—")
            self.lbl_time.setText("—")
            self.lbl_engine.setText("—")
            self.lbl_note.setText("")
            return
        if r.move is None:
            self.lbl_move.setText("（无推荐）")
            self.lbl_score.setText("—")
            self.lbl_depth.setText(str(r.depth) if r.depth else "—")
            self.lbl_time.setText(f"{r.time_ms / 1000.0:.1f} 秒" if r.time_ms else "—")
            self.lbl_engine.setText(r.engine or "—")
            self.lbl_note.setText(r.note or "")
            return
        self.lbl_move.setText(f"{r.move.notation or r.move.describe()}  "
                              f"({'吃子' if r.move.is_capture else '—'})")
        self.lbl_score.setText(r.score_text())
        self.lbl_depth.setText(str(r.depth))
        self.lbl_time.setText(f"{r.time_ms / 1000.0:.1f} 秒")
        self.lbl_engine.setText(r.engine)
        parts = [p for p in (r.uncertainty, r.note) if p]
        self.lbl_note.setText("；".join(parts))