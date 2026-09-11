"""Milestone 2 文件读取处理器的自动测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.processors.factory import get_processor


SAMPLES = Path(__file__).parent / "sample_files"


def test_word_reader_extracts_paragraphs_and_tables() -> None:
    result = get_processor(SAMPLES / "会议通知.docx").read(SAMPLES / "会议通知.docx")

    assert result.kind == "word"
    assert "会议通知" in result.paragraphs
    assert result.tables[0].rows[1] == ["张三", "200"]


def test_excel_reader_extracts_sheets_and_cells() -> None:
    result = get_processor(SAMPLES / "报销表.xlsx").read(SAMPLES / "报销表.xlsx")

    assert result.kind == "excel"
    assert [sheet.name for sheet in result.worksheets] == ["报销表", "说明"]
    assert result.worksheets[0].rows[1] == ["张三", 200]


def test_pdf_reader_extracts_pages_and_text() -> None:
    result = get_processor(SAMPLES / "报销通知.pdf").read(SAMPLES / "报销通知.pdf")

    assert result.kind == "pdf"
    assert len(result.pages) == 1
    assert "2026" in result.pages[0]


def test_unsupported_file_is_rejected(tmp_path: Path) -> None:
    unsupported_file = tmp_path / "照片.jpg"
    unsupported_file.touch()

    with pytest.raises(ValueError, match="暂只支持"):
        get_processor(unsupported_file)


def test_reading_never_changes_source_file() -> None:
    source = SAMPLES / "报销表.xlsx"
    before = source.read_bytes()

    get_processor(source).read(source)

    assert source.read_bytes() == before
