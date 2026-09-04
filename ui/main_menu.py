"""主菜单页：选模式 → 选我执红/黑 → 开始。"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QGroupBox, QHBoxLayout, QLabel,
                               QPushButton, QRadioButton, QVBoxLayout, QWidget)

from core.game_state import GameMode
from core.piece import Side
from app.config import APP_NAME, APP_VERSION


class MainMenuWidget(QWidget):
    start_requested = Signal(object, object)  # (GameMode, Side)
    exit_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel(f"{APP_NAME}")
        title.setStyleSheet("font-size: 34px; font-weight: bold; color: #7B3F00;")
        title.setAlignment(Qt.AlignCenter)
        sub = QLabel(f"v{APP_VERSION} · 现实棋局模拟、记录与分析（非在线对战）")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #666;")
        layout.addSpacing(20)
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addSpacing(20)

        # 第一步：选择模式
        mode_box = QGroupBox("① 请选择游戏模式")
        ml = QHBoxLayout(mode_box)
        self.rb_normal = QRadioButton("正常玩法")
        self.rb_dark = QRadioButton("揭棋")
        self.rb_normal.setChecked(True)
        self.rb_normal.setStyleSheet("font-size: 16px;")
        self.rb_dark.setStyleSheet("font-size: 16px;")
        ml.addWidget(self.rb_normal)
        ml.addWidget(self.rb_dark)
        ml.addStretch(1)
        layout.addWidget(mode_box)

        # 第二步：选择我执
        side_box = QGroupBox("② 请选择你执哪一方（对家由程序记录/分析）")
        sl = QHBoxLayout(side_box)
        self.rb_red = QRadioButton("我执红方（先走）")
        self.rb_black = QRadioButton("我执黑方（后走）")
        self.rb_red.setChecked(True)
        self.rb_red.setStyleSheet("font-size: 16px;")
        self.rb_black.setStyleSheet("font-size: 16px;")
        sl.addWidget(self.rb_red)
        sl.addWidget(self.rb_black)
        sl.addStretch(1)
        layout.addWidget(side_box)

        self.lbl_tip = QLabel("")
        self.lbl_tip.setWordWrap(True)
        self.lbl_tip.setStyleSheet("color: #555;")
        layout.addWidget(self.lbl_tip)

        # 开始/退出
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("开始对局")
        self.btn_start.setStyleSheet("font-size: 18px; padding: 10px 30px; background: #7B3F00; color: white;")
        self.btn_start.clicked.connect(self._start)
        btn_quit = QPushButton("退出")
        btn_quit.clicked.connect(self.exit_requested.emit)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(btn_quit)
        btn_row.addStretch(1)
        layout.addStretch(1)
        layout.addLayout(btn_row)
        layout.addSpacing(20)

        self.rb_normal.toggled.connect(self._update_tip)
        self.rb_red.toggled.connect(self._update_tip)
        self._update_tip()

    def _update_tip(self) -> None:
        mode = "揭棋" if self.rb_dark.isChecked() else "正常玩法"
        if self.rb_red.isChecked():
            self.lbl_tip.setText(
                f"你执红方：红方先走。你走出第一步后，在程序里录入你的走法；"
                f"对家（黑方）在现实中的走法也由你录入。")
        else:
            self.lbl_tip.setText(
                f"你执黑方：红方（对家）先走。请先录入对家在现实中的第一步，"
                f"再轮到你录入黑方走法。")

    def selected_mode(self) -> GameMode:
        return GameMode.DARK if self.rb_dark.isChecked() else GameMode.NORMAL

    def selected_side(self) -> Side:
        return Side.BLACK if self.rb_black.isChecked() else Side.RED

    def _start(self) -> None:
        self.start_requested.emit(self.selected_mode(), self.selected_side())