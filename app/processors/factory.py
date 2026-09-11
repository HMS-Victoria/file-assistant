"""根据文件扩展名选择正确的本地处理器。"""

from __future__ import annotations

from pathlib import Path

from app.processors.base_processor import FileProcessor
from app.processors.excel_processor import ExcelProcessor
from app.processors.pdf_processor import PdfProcessor
from app.processors.word_processor import WordProcessor


_PROCESSORS: tuple[FileProcessor, ...] = (WordProcessor(), ExcelProcessor(), PdfProcessor())


def get_processor(file_path: Path) -> FileProcessor:
    """返回对应处理器；不支持的格式给出适合上层翻译的错误。"""
    suffix = file_path.suffix.lower()
    for processor in _PROCESSORS:
        if suffix in processor.supported_suffixes:
            return processor
    raise ValueError("暂只支持 Word、Excel 和 PDF 文件。")
