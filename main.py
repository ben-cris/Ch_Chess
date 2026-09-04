"""象棋辅助工具 - 程序入口。

运行方式（PyCharm）：直接运行本文件；或 python main.py
"""
from __future__ import annotations

import sys


def main() -> int:
    from app.config import APP_NAME, log_dir
    from app.logger import get_logger, setup_logging
    setup_logging(log_dir())
    log = get_logger("main")

    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    def excepthook(etype, value, tb):
        log.critical("未处理异常", exc_info=(etype, value, tb))
        try:
            QMessageBox.critical(None, "程序错误",
                                 f"发生未处理异常：{value}\n详情已写入日志。")
        except Exception:
            pass

    sys.excepthook = excepthook

    from ui.main_window import MainWindow
    win = MainWindow()
    win.resize(1080, 700)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())