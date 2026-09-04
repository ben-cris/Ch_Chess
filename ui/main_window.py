"""主窗口：主菜单页 → 对局页（棋盘 + 控制 + 分析 + 状态 + 自动代走）。"""
from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QPushButton, QSplitter,
                               QStackedWidget, QVBoxLayout, QWidget)

from app.config import APP_NAME, APP_VERSION
from app.logger import get_logger
from core.game_state import GameMode, GameStatus
from core.move import Move
from core.piece import Side
from core.position import Position
from models.analysis_result import AnalysisResult
from models.settings import AppSettings
from services.ai_service import AnalysisJob
from services.game_service import GameService
from services.move_input_service import MoveInputService
from services.save_service import load_game, save_game
from services.settings_service import load_settings, save_settings
from ui.analysis_panel import AnalysisPanel
from ui.board_widget import BoardWidget
from ui.edit_board_dialog import EditBoardDialog
from ui.main_menu import MainMenuWidget
from ui.move_input_dialog import MoveInputDialog
from ui.reveal_piece_dialog import RevealPieceDialog
from ui.settings_dialog import SettingsDialog

log = get_logger("main")


class _Bridge(QObject):
    done = Signal(object)       # 手动分析结果
    error = Signal(object)
    auto_done = Signal(object)  # 自动代走结果
    auto_error = Signal(object)


def _pos_key(p: Position):
    return (p.row, p.col)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.service = GameService()
        self.settings: AppSettings = load_settings()
        self._job: Optional[AnalysisJob] = None
        self._auto_job: Optional[AnalysisJob] = None
        self._auto: bool = False
        self._selected: Optional[Position] = None
        self._actions_by_to: Dict[Position, List[Move]] = {}
        self._bridge = _Bridge()
        self._bridge.done.connect(self._on_analysis_done)
        self._bridge.error.connect(self._on_analysis_error)
        self._bridge.auto_done.connect(self._on_auto_done)
        self._bridge.auto_error.connect(self._on_auto_error)
        self._build_ui()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")

    # ================= UI =================
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()

        self.menu_page = MainMenuWidget()
        self.menu_page.start_requested.connect(self._start_from_menu)
        self.menu_page.exit_requested.connect(self.close)
        self.stack.addWidget(self.menu_page)

        self.game_page = self._build_game_page()
        self.stack.addWidget(self.game_page)

        root.addWidget(self.stack)
        self.stack.setCurrentWidget(self.menu_page)
        self.statusBar().showMessage("请选择模式与我执方后开始")

    def _build_game_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        splitter = QSplitter()
        layout.addWidget(splitter)

        self.board = BoardWidget()
        self.board.square_clicked.connect(self._on_square_clicked)
        splitter.addWidget(self.board)

        right = QWidget()
        rl = QVBoxLayout(right)
        info = QGroupBox("棋局信息")
        form = QFormLayout(info)
        self.lbl_mode = QLabel("")
        self.lbl_user = QLabel("")
        self.lbl_opponent = QLabel("")
        self.lbl_turn = QLabel("")
        self.lbl_analyze = QLabel("")
        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        form.addRow("模式", self.lbl_mode)
        form.addRow("我执", self.lbl_user)
        form.addRow("对家", self.lbl_opponent)
        form.addRow("当前回合", self.lbl_turn)
        form.addRow("分析方", self.lbl_analyze)
        form.addRow("状态", self.lbl_status)
        rl.addWidget(info)

        btn_box = QGroupBox("操作")
        bl = QVBoxLayout(btn_box)
        def mk(text, slot):
            b = QPushButton(text)
            b.clicked.connect(slot)
            bl.addWidget(b)
            return b
        mk("返回主菜单 / 新建棋局", self._to_menu)
        mk("录入走法（手动）", self._manual_move)
        self.btn_analyze = mk("分析我的最佳走法", self._analyze)
        self.btn_undo = mk("悔棋", self._undo)
        self.btn_redo = mk("重做", self._redo)
        mk("编辑棋局", self._edit_game)
        mk("保存棋局", self._save)
        mk("加载棋局", self._load)
        mk("设置", self._open_settings)
        self.chk_auto = QCheckBox("对家走完后，自动代走我方最优步")
        self.chk_auto.setChecked(self.settings.auto_play)
        self.chk_auto.toggled.connect(self._on_auto_toggled)
        bl.addWidget(self.chk_auto)
        rl.addWidget(btn_box)

        turn_box = QGroupBox("回合控制")
        tl = QVBoxLayout(turn_box)
        self.turn_combo = QComboBox()
        self.turn_combo.addItem("红方走", Side.RED)
        self.turn_combo.addItem("黑方走", Side.BLACK)
        self.turn_combo.currentIndexChanged.connect(self._turn_changed)
        tl.addWidget(QLabel("与现实不一致时，手动设定“下一步由谁走”"))
        tl.addWidget(self.turn_combo)
        rl.addWidget(turn_box)

        self.panel = AnalysisPanel()
        rl.addWidget(self.panel)
        rl.addStretch(1)
        splitter.addWidget(right)
        splitter.setSizes([620, 360])
        return page

    # ================= 开始对局 =================
    def _start_from_menu(self, mode: GameMode, user_side: Side) -> None:
        self.service.new_game(mode, user_side)
        self._selected = None
        self._actions_by_to = {}
        self.panel.show_result(None)
        self.stack.setCurrentWidget(self.game_page)
        self._refresh()
        st = self.service.current()
        if user_side is Side.RED:
            self.statusBar().showMessage("你执红方，先走（AI 将代你走第一步）")
        else:
            self.statusBar().showMessage("你执黑方，红方（对家）先走：请录入对家第一步现实走法")
        self._maybe_auto_play()

    def _to_menu(self) -> None:
        if self._busy():
            return
        st = self.service.current()
        if st is not None and st.moves:
            ret = QMessageBox.question(
                self, "返回主菜单",
                "当前棋局尚未保存，返回主菜单将开始新对局。是否继续？")
            if ret != QMessageBox.Yes:
                return
        if self._auto_job is not None:
            self._auto_job.cancel()
        self.stack.setCurrentWidget(self.menu_page)
        self.statusBar().showMessage("请选择模式与我执方后开始")

    # ================= busy 保护 =================
    def _busy(self) -> bool:
        return self._auto or self._job is not None or self._auto_job is not None

    # ================= refresh =================
    def _refresh(self) -> None:
        st = self.service.current()
        self.board.set_state(st)
        self._selected = None
        self._actions_by_to = {}
        self.board.set_recommend(None, None)
        self.lbl_mode.setText("揭棋" if st.mode is GameMode.DARK else "正常玩法")
        self.lbl_user.setText(st.user_side.label)
        self.lbl_opponent.setText(st.user_side.opponent.label)
        self.lbl_turn.setText(st.turn.label)
        self.lbl_analyze.setText(st.user_side.label)
        self._update_status_label()
        self.turn_combo.blockSignals(True)
        self.turn_combo.setCurrentIndex(0 if st.turn is Side.RED else 1)
        self.turn_combo.blockSignals(False)
        self.btn_undo.setEnabled(not self._busy() and bool(self.service._undo))
        self.btn_redo.setEnabled(not self._busy() and bool(self.service._redo))
        self.btn_analyze.setEnabled(not self._busy() and not st.over)

    def _update_status_label(self) -> None:
        st = self.service.current()
        if st.status is GameStatus.RED_WIN:
            self.lbl_status.setText("红方胜")
        elif st.status is GameStatus.BLACK_WIN:
            self.lbl_status.setText("黑方胜")
        elif st.status is GameStatus.DRAW:
            self.lbl_status.setText("和棋（重复局面）")
        elif self._check_turn():
            self.lbl_status.setText(f"{st.turn.label}被将军！请应对")
        elif st.turn is st.user_side:
            if self._auto:
                self.lbl_status.setText(f"轮到你（{st.user_side.label}），AI 正在计算最优步…")
            elif not st.moves:
                self.lbl_status.setText(f"轮到你（{st.user_side.label}）先走")
            else:
                self.lbl_status.setText(f"轮到你（{st.user_side.label}）")
        else:
            self.lbl_status.setText(f"对家（{st.turn.label}）走：请录入对家在现实中的这一步")

    def _check_turn(self) -> bool:
        from rules.win_checker import is_in_check
        st = self.service.current()
        return is_in_check(st, st.turn)

    # ================= 棋盘点击录入 =================
    def _on_square_clicked(self, row: int, col: int) -> None:
        if self._busy():
            self.statusBar().showMessage("AI 计算中，请稍候…")
            return
        st = self.service.current()
        if st.over:
            return
        pos = Position(row, col)
        piece = st.board.get(pos)
        if self._selected is None:
            if piece is None:
                return
            actions = self._actions_for(piece.side, pos)
            if not actions:
                self.statusBar().showMessage("该棋子当前无合法走法")
                return
            if piece.side is not st.turn:
                ret = QMessageBox.question(
                    self, "回合提示",
                    f"程序记录为：当前轮到{st.turn.label}。\n若现实中是{piece.side.label}走子，将先切换到{piece.side.label}再录入。是否继续？")
                if ret != QMessageBox.Yes:
                    return
                self.service.set_turn(piece.side)
                self._refresh()
            self._select(pos, actions)
            return
        # 已有选择
        if pos == self._selected:
            self._deselect()
            return
        other = st.board.get(pos)
        selected_piece = st.board.get(self._selected)
        if other is not None and selected_piece is not None and other.side is selected_piece.side:
            actions = self._actions_for(other.side, pos)
            if actions:
                self._select(pos, actions)
            else:
                self._deselect()
            return
        if pos in self._actions_by_to:
            action = self._actions_by_to[pos][0]
            self._deselect()
            self._try_record(action.side, action.frm, action.to)
        else:
            self._deselect()

    def _select(self, pos: Position, actions: List[Move]) -> None:
        self._selected = pos
        self._actions_by_to = {}
        for a in actions:
            self._actions_by_to.setdefault(a.to, []).append(a)
        self.board.set_selection(pos, sorted(self._actions_by_to.keys(), key=_pos_key))

    def _deselect(self) -> None:
        self._selected = None
        self._actions_by_to = {}
        self.board.set_selection(None, [])

    def _actions_for(self, side: Side, pos: Position) -> List[Move]:
        st = self.service.current()
        return [a for a in self.service.rules().legal_actions(st, side) if a.frm == pos]

    def _manual_move(self) -> None:
        if self._busy():
            return
        st = self.service.current()
        if st.over:
            QMessageBox.information(self, "提示", "棋局已结束")
            return
        dlg = MoveInputDialog(self, st.turn)
        if dlg.exec():
            side, frm, to = dlg.values()
            self._try_record(side, frm, to)

    def _try_record(self, side: Side, frm: Position, to: Position) -> None:
        st = self.service.current()
        reveal_type, disclosed = self._resolve_reveals(st, side, frm, to)
        if reveal_type is None and self._needs_mover_reveal(st, frm):
            return  # 用户取消
        ok, msg, move = MoveInputService.build_move(
            st, side, frm, to, reveal_type=reveal_type, disclosed_type=disclosed)
        if not ok:
            QMessageBox.warning(self, "无法录入", msg)
            return
        ok2, msg2 = self.service.apply_move(move)
        if not ok2:
            QMessageBox.warning(self, "无法录入", msg2)
            return
        self.panel.show_result(None)
        self._refresh()
        self.statusBar().showMessage(f"已记录：{move.notation or move.describe()}")
        # 若现在轮到我方，自动代走
        self._maybe_auto_play()

    @staticmethod
    def _needs_mover_reveal(st, frm: Position) -> bool:
        p = st.board.get(frm)
        return bool(p and p.is_unknown and not p.revealed)

    def _resolve_reveals(self, st, side: Side, frm: Position, to: Position):
        """返回 (移动方揭示身份, 被吃暗子揭示身份)；任一取消则返回 (None, None)。"""
        rules = self.service.rules()
        reveal_type = None
        disclosed = None
        if self._needs_mover_reveal(st, frm):
            opts = rules.legal_reveal_types(st, frm)
            if not opts:
                QMessageBox.warning(self, "无法录入", "无法确定可揭示身份（子力数据不一致）")
                return None, None
            dlg = RevealPieceDialog(self, side, opts,
                                    remaining=rules.remaining_counts(st, side),
                                    title="请选择走子方棋子揭开后的真实身份")
            if dlg.exec() != RevealPieceDialog.Accepted or dlg.selected_type is None:
                return None, None
            reveal_type = dlg.selected_type
        target = st.board.get(to) if to != frm else None
        if target is not None and target.is_unknown and not target.revealed:
            opts = rules.legal_reveal_types(st, to)
            if not opts:
                QMessageBox.warning(self, "无法录入", "被吃暗子身份无法确定（子力数据不一致）")
                return None, None
            dlg = RevealPieceDialog(self, target.side, opts,
                                    remaining=rules.remaining_counts(st, target.side),
                                    title="请选择被吃暗子的真实身份")
            if dlg.exec() != RevealPieceDialog.Accepted or dlg.selected_type is None:
                return None, None
            disclosed = dlg.selected_type
        return reveal_type, disclosed

    # ================= 自动代走 =================
    def _on_auto_toggled(self, checked: bool) -> None:
        self.settings.auto_play = bool(checked)
        save_settings(self.settings)

    def _maybe_auto_play(self) -> None:
        """轮到己方时自动代走（若开启且空闲）。"""
        if self._busy():
            return
        st = self.service.current()
        if not self.settings.auto_play or st.over or st.turn is not st.user_side:
            return
        self._auto = True
        self.btn_analyze.setEnabled(False)
        self.board.setEnabled(False)
        self.statusBar().showMessage(f"轮到你（{st.user_side.label}），AI 正在计算最优步…")
        self._update_status_label()
        self._auto_job = AnalysisJob(st.clone(), self.settings.engine,
                                     self._bridge.auto_done.emit,
                                     self._bridge.auto_error.emit).start()

    def _on_auto_done(self, result: AnalysisResult) -> None:
        self._auto_job = None
        self._auto = False
        self.board.setEnabled(True)
        st = self.service.current()
        if not self.settings.auto_play:
            self._refresh()
            self.statusBar().showMessage("已取消自动代走（你可在需要时重新开启）")
            return
        if st.over:
            self._refresh()
            return
        if result.move is None or st.turn is not st.user_side:
            self._refresh()
            self.statusBar().showMessage(f"AI 未自动代走：{result.note or '未找到走法'}")
            return
        applied, msg = self._apply_ai_move(st, result.move)
        if applied:
            self.panel.show_result(result)
            self._refresh()
            self.statusBar().showMessage(
                f"AI 已代你走出：{result.move.notation or result.move.describe()}  "
                f"（评分 {result.score_text()}，高亮为刚走的棋子）")
        else:
            self._refresh()
            self.statusBar().showMessage(f"AI 未自动代走：{msg}")

    def _on_auto_error(self, exc: Exception) -> None:
        self._auto_job = None
        self._auto = False
        self.board.setEnabled(True)
        log.exception("自动代走异常")
        self._refresh()
        self.statusBar().showMessage(f"自动代走失败：{exc}")

    def _apply_ai_move(self, st, ai_move: Move):
        """把 AI 推荐步应用到当前棋局；揭棋暗子身份仍由用户确认。"""
        side = st.user_side
        if st.mode is GameMode.DARK:
            rules = self.service.rules()
            mover = st.board.get(ai_move.frm)
            reveal_type = None
            if mover is not None and mover.is_unknown:
                opts = rules.legal_reveal_types(st, ai_move.frm)
                if not opts:
                    return False, "暗子身份无法确定"
                dlg = RevealPieceDialog(self, side, opts,
                                        remaining=rules.remaining_counts(st, side),
                                        title="AI 代走暗子——请选择该棋子揭开后的真实身份")
                if dlg.exec() != RevealPieceDialog.Accepted or dlg.selected_type is None:
                    return False, "身份未确认，未自动代走"
                reveal_type = dlg.selected_type
            target = st.board.get(ai_move.to) if ai_move.frm != ai_move.to else None
            disclosed = None
            if target is not None and target.is_unknown and not target.revealed:
                opts = rules.legal_reveal_types(st, ai_move.to)
                if not opts:
                    return False, "被吃暗子身份无法确定"
                dlg = RevealPieceDialog(self, target.side, opts,
                                        remaining=rules.remaining_counts(st, target.side),
                                        title="AI 吃暗子——请选择被吃暗子的真实身份")
                if dlg.exec() != RevealPieceDialog.Accepted or dlg.selected_type is None:
                    return False, "被吃身份未确认，未自动代走"
                disclosed = dlg.selected_type
            ok, msg, move = MoveInputService.build_move(
                st, side, ai_move.frm, ai_move.to,
                reveal_type=reveal_type, disclosed_type=disclosed)
            if not ok:
                return False, msg
            ok2, msg2 = self.service.apply_move(move)
            return (ok2, msg2) if ok2 else (False, msg2)
        # 正常玩法
        ok, msg = self.service.apply_move(ai_move)
        return (ok, msg) if ok else (False, msg)

    # ================= 操作 =================
    def _undo(self) -> None:
        if self._busy():
            return
        if self.service.undo():
            self.panel.show_result(None)
            self._refresh()
            self.statusBar().showMessage("已悔棋")

    def _redo(self) -> None:
        if self._busy():
            return
        if self.service.redo():
            self.panel.show_result(None)
            self._refresh()
            self.statusBar().showMessage("已重做")

    def _turn_changed(self, _idx: int) -> None:
        if self._busy():
            return
        side = self.turn_combo.currentData()
        st = self.service.current()
        if st.turn is not side:
            self.service.set_turn(side)
            self.panel.show_result(None)
            self._refresh()
            self.statusBar().showMessage(f"当前回合已手动切换为 {side.label}")

    def _edit_game(self) -> None:
        if self._busy():
            return
        dlg = EditBoardDialog(self, self.service)
        if dlg.exec():
            self.service._recompute()
            self.panel.show_result(None)
            self._refresh()

    def _save(self) -> None:
        st = self.service.current()
        path, _ = QFileDialog.getSaveFileName(self, "保存棋局", "棋局.json", "JSON 文件 (*.json)")
        if path:
            try:
                save_game(st, path)
                self.statusBar().showMessage(f"已保存：{path}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", str(e))

    def _load(self) -> None:
        if self._busy():
            return
        path, _ = QFileDialog.getOpenFileName(self, "加载棋局", "", "JSON 文件 (*.json)")
        if path:
            try:
                state = load_game(path)
            except Exception as e:
                QMessageBox.critical(self, "加载失败", str(e))
                return
            self.service.set_state(state)
            self.panel.show_result(None)
            self.stack.setCurrentWidget(self.game_page)
            self._refresh()
            self.statusBar().showMessage(f"已加载：{path}")
            self._maybe_auto_play()

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self, self.settings)
        if dlg.exec():
            self.settings.engine = dlg.engine_settings()
            self.settings.auto_play = dlg.auto_play_enabled()
            self.chk_auto.setChecked(self.settings.auto_play)
            save_settings(self.settings)
            self.statusBar().showMessage("设置已保存")

    # ================= 手动分析 =================
    def _analyze(self) -> None:
        if self._busy():
            return
        st = self.service.current()
        if st.over:
            QMessageBox.information(self, "提示", "棋局已结束")
            return
        ok, msg = MoveInputService.validate_turn_for_analysis(st)
        if not ok:
            ret = QMessageBox.question(
                self, "分析提示", msg + "\n\n仍要查看该方最佳走法吗？（仅参考，非本回合推荐）")
            if ret != QMessageBox.Yes:
                return
        self.btn_analyze.setEnabled(False)
        self.statusBar().showMessage("AI 分析中…")
        self._job = AnalysisJob(st.clone(), self.settings.engine,
                                self._bridge.done.emit, self._bridge.error.emit).start()

    def _on_analysis_done(self, result: AnalysisResult) -> None:
        self._job = None
        self.panel.show_result(result)
        if result.move is not None:
            self.board.set_recommend(result.move.frm, result.move.to)
            self.statusBar().showMessage(
                f"分析完成：{result.move.notation or result.move.describe()}  评分 {result.score_text()}")
        else:
            self.statusBar().showMessage(f"分析完成：{result.note or '无推荐'}")
        st = self.service.current()
        self.btn_analyze.setEnabled(not st.over)

    def _on_analysis_error(self, exc: Exception) -> None:
        self._job = None
        log.exception("AI 分析异常")
        QMessageBox.warning(self, "分析失败", f"AI 分析出错：{exc}")
        self.btn_analyze.setEnabled(True)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._job is not None:
            self._job.cancel()
        if self._auto_job is not None:
            self._auto_job.cancel()
        # 关闭外部引擎子进程，避免退出后残留
        from engine.engine_manager import EngineManager
        EngineManager.clear_cache()
        super().closeEvent(event)