"""文件拖放区域。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


SUPPORTED_SUFFIXES = {".docx", ".xlsx", ".pdf"}


class DropArea(QFrame):
    """接收一个受支持文件的醒目拖放区域。"""

    def __init__(self, on_file_dropped: Callable[[Path], None]) -> None:
        super().__init__()
        self._on_file_dropped = on_file_dropped
        self.setAcceptDrops(True)
        self.setObjectName("dropArea")
        self.setMinimumHeight(180)

        label = QLabel("把 Word、Excel 或 PDF 文件拖到这里")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        label.setObjectName("dropHint")

        layout = QVBoxLayout(self)
        layout.addWidget(label)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        """仅在拖入单个本地文件时允许放置。"""
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        """将拖入的文件交给主窗口校验。"""
        file_path = Path(event.mimeData().urls()[0].toLocalFile())
        self._on_file_dropped(file_path)
        event.acceptProposedAction()
