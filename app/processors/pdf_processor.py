"""PDF 文件的只读文本提取处理器。"""

from __future__ import annotations

from pathlib import Path

import pymupdf

from app.processors.base_processor import FileProcessor, FileReadResult


class PdfProcessor(FileProcessor):
    """逐页提取 PDF 文字；不尝试编辑或改变 PDF 排版。"""

    supported_suffixes = frozenset({".pdf"})
    kind = "pdf"

    def read(self, file_path: Path) -> FileReadResult:
        self._validate_file(file_path)
        with pymupdf.open(file_path) as document:
            pages = [page.get_text("text") for page in document]
        return FileReadResult(file_path=file_path, kind="pdf", pages=pages)
