"""各类文件的本地读取处理器。"""

from app.processors.base_processor import FileProcessor, FileReadResult
from app.processors.factory import get_processor

__all__ = ["FileProcessor", "FileReadResult", "get_processor"]
