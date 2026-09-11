"""文件小助手的应用入口（Milestone 1）。"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def main() -> int:
    """启动桌面应用。"""
    application = QApplication(sys.argv)
    application.setApplicationName("文件小助手")
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
