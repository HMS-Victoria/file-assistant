"""Milestone 5 的 Word、Excel 副本修改测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.operations.schemas import validate_operation_plan
from app.processors.factory import get_processor
from app.services.modification_service import ModificationError, ModificationService


SAMPLES = Path(__file__).parent / "sample_files"


def plan(*operations: dict[str, object]):
    return validate_operation_plan({"explanation": "测试修改", "operations": list(operations)})


def test_word_replace_append_and_delete_write_new_file_only(tmp_path: Path) -> None:
    source = SAMPLES / "会议通知.docx"
    output = tmp_path / "会议通知_AI修改.docx"
    original = source.read_bytes()

    result = ModificationService().apply(
        source,
        output,
        plan(
            {"action": "replace_text", "target": "张三", "replacement": "李四"},
            {"action": "delete_text", "target": "2026 年 9 月 10 日"},
            {"action": "append_text", "text": "请准时参加。"},
        ),
    )
    content = get_processor(output).read(output)

    assert source.read_bytes() == original
    assert result.output_path == output.resolve()
    assert "李四" in content.tables[0].rows[1]
    assert "2026 年 9 月 10 日" not in "\n".join(content.paragraphs)
    assert "请准时参加。" in content.paragraphs
    assert len(result.changes) == 3


def test_excel_replace_append_and_delete_write_expected_output(tmp_path: Path) -> None:
    source = SAMPLES / "报销表.xlsx"
    output = tmp_path / "报销表_AI修改.xlsx"
    original = source.read_bytes()

    ModificationService().apply(
        source,
        output,
        plan(
            {"action": "replace_cell", "sheet": "报销表", "cell": "B2", "value": 300},
            {"action": "append_row", "sheet": "报销表", "values": ["李四", 400]},
            {"action": "append_column", "sheet": "报销表", "values": ["备注", "已审核", "待审核"]},
            {"action": "delete_column", "sheet": "报销表", "column": 3},
            {"action": "delete_row", "sheet": "报销表", "row": 3},
        ),
    )
    content = get_processor(output).read(output)

    assert source.read_bytes() == original
    assert content.worksheets[0].rows == [["姓名", "金额"], ["张三", 300]]


def test_source_overwrite_and_existing_output_are_rejected(tmp_path: Path) -> None:
    source = SAMPLES / "报销表.xlsx"
    output = tmp_path / "已经存在.xlsx"
    output.write_bytes(b"keep")
    modification_plan = plan({"action": "append_row", "sheet": "报销表", "values": ["李四", 400]})

    with pytest.raises(ModificationError, match="不允许覆盖原文件"):
        ModificationService().apply(source, source, modification_plan)
    with pytest.raises(ModificationError, match="已存在"):
        ModificationService().apply(source, output, modification_plan)
    assert output.read_bytes() == b"keep"


def test_wrong_file_operation_is_rejected_before_output(tmp_path: Path) -> None:
    output = tmp_path / "错误操作.docx"

    with pytest.raises(ModificationError, match="只能执行"):
        ModificationService().apply(
            SAMPLES / "会议通知.docx",
            output,
            plan({"action": "append_row", "sheet": "报销表", "values": ["李四", 400]}),
        )
    assert not output.exists()
