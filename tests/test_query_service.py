"""Milestone 4 查询功能测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.operations.schemas import validate_operation_plan
from app.processors.base_processor import FileReadResult
from app.services.query_service import MAX_AI_CONTENT_CHARS, QueryError, QueryService


SAMPLES = Path(__file__).parent / "sample_files"


def plan(action: dict[str, object]):
    return validate_operation_plan({"explanation": "测试查询", "operations": [action]})


def test_find_text_in_word_pdf_and_excel() -> None:
    service = QueryService()

    assert "张三" in service.execute(SAMPLES / "会议通知.docx", plan({"action": "find_text", "target": "张三"})).text
    assert "2026" in service.execute(SAMPLES / "报销通知.pdf", plan({"action": "find_text", "target": "2026"})).text
    assert "张三" in service.execute(SAMPLES / "报销表.xlsx", plan({"action": "find_text", "target": "张三"})).text


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        ("calculate_sum", "200"),
        ("calculate_average", "200"),
        ("calculate_max", "200"),
        ("calculate_min", "200"),
    ],
)
def test_excel_calculations_are_local(action: str, expected: str) -> None:
    result = QueryService().execute(
        SAMPLES / "报销表.xlsx",
        plan({"action": action, "sheet": "报销表", "column": "金额"}),
    )

    assert expected in result.text
    assert result.used_ai is False


def test_excel_filter_rows() -> None:
    result = QueryService().execute(
        SAMPLES / "报销表.xlsx",
        plan({"action": "filter_rows", "sheet": "报销表", "column": "姓名", "value": "张三"}),
    )

    assert "找到 1 条记录" in result.text
    assert "张三 | 200" in result.text


class FakeAnswerClient:
    def __init__(self) -> None:
        self.user_prompt = ""

    def create_text_completion(self, _system_prompt: str, user_prompt: str) -> str:
        self.user_prompt = user_prompt
        return "这是一份报销通知。"


@pytest.mark.parametrize(
    ("filename", "operation"),
    [
        ("会议通知.docx", {"action": "summarize"}),
        ("报销通知.pdf", {"action": "summarize"}),
        ("会议通知.docx", {"action": "question_answer", "question": "会议是什么时候？"}),
        ("报销通知.pdf", {"action": "question_answer", "question": "什么时候提交？"}),
    ],
)
def test_word_and_pdf_summary_or_question_answer_use_ai(filename: str, operation: dict[str, object]) -> None:
    client = FakeAnswerClient()
    result = QueryService(client).execute(SAMPLES / filename, plan(operation))

    assert result.text == "这是一份报销通知。"
    assert result.used_ai is True
    assert str(SAMPLES) not in client.user_prompt


def test_pdf_question_answer_uses_ai() -> None:
    client = FakeAnswerClient()
    result = QueryService(client).execute(
        SAMPLES / "报销通知.pdf",
        plan({"action": "question_answer", "question": "什么时候提交？"}),
    )

    assert result.used_ai is True
    assert "什么时候提交" in client.user_prompt


def test_excel_question_answer_uses_ai() -> None:
    client = FakeAnswerClient()
    result = QueryService(client).execute(
        SAMPLES / "报销表.xlsx",
        plan({"action": "question_answer", "question": "金额是多少？"}),
    )

    assert result.used_ai is True
    assert "张三 | 200" in client.user_prompt


def test_ai_content_is_capped_for_large_files() -> None:
    content = FileReadResult(file_path=Path("很长的文件.pdf"), kind="pdf", pages=["内容" * MAX_AI_CONTENT_CHARS])

    limited = QueryService._content_for_ai(content)

    assert len(limited) == MAX_AI_CONTENT_CHARS


def test_modification_plan_is_rejected_before_file_changes() -> None:
    source = SAMPLES / "会议通知.docx"
    before = source.read_bytes()

    with pytest.raises(QueryError, match="不能修改"):
        QueryService().execute(source, plan({"action": "replace_text", "target": "张三", "replacement": "李四"}))

    assert source.read_bytes() == before
