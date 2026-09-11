"""文件读取处理器的统一接口与结果模型。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


FileKind = Literal["word", "excel", "pdf"]


@dataclass(frozen=True)
class TableData:
    """Word 表格的纯文本表示。"""

    rows: list[list[str]]


@dataclass(frozen=True)
class WorksheetData:
    """Excel 工作表的基础内容。"""

    name: str
    rows: list[list[object | None]]


@dataclass(frozen=True)
class FileReadResult:
    """统一的只读文件内容；本阶段不包含任何修改指令。"""

    file_path: Path
    kind: FileKind
    paragraphs: list[str] = field(default_factory=list)
    tables: list[TableData] = field(default_factory=list)
    worksheets: list[WorksheetData] = field(default_factory=list)
    pages: list[str] = field(default_factory=list)


class FileProcessor(ABC):
    """所有文件处理器均实现此只读接口。"""

    supported_suffixes: frozenset[str]
    kind: FileKind

    @abstractmethod
    def read(self, file_path: Path) -> FileReadResult:
        """读取文件为安全的本地内存结果，不写回原文件。"""

    def _validate_file(self, file_path: Path) -> None:
        if not file_path.is_file():
            raise FileNotFoundError("没有找到要读取的文件。")
        if file_path.suffix.lower() not in self.supported_suffixes:
            raise ValueError("文件格式不受此处理器支持。")
