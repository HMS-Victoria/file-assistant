"""用户文件异常时的安全提示测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.operations.schemas import validate_operation_plan
from app.services.query_service import QueryError, QueryService


def test_corrupted_file_becomes_safe_query_error(tmp_path: Path) -> None:
    broken = tmp_path / "损坏的表格.xlsx"
    broken.write_text("这不是 Excel 文件", encoding="utf-8")
    plan = validate_operation_plan({"explanation": "查找", "operations": [{"action": "find_text", "target": "内容"}]})

    with pytest.raises(QueryError) as error:
        QueryService().execute(broken, plan)

    assert error.value.user_message == "这次没有得到结果，请换一种说法后再试。"
