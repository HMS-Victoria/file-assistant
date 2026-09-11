"""Milestone 6：预览、备份、输出验证与恢复测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.operations.schemas import validate_operation_plan
from app.processors.factory import get_processor
from app.services.safe_modification_service import SafeModificationService, SafetyError


SAMPLES = Path(__file__).parent / "sample_files"


def plan(*operations: dict[str, object]):
    return validate_operation_plan({"explanation": "测试安全修改", "operations": list(operations)})


def test_preview_generates_unique_name_and_marks_deletion_as_dangerous(tmp_path: Path) -> None:
    source = tmp_path / "通知.docx"
    source.write_bytes((SAMPLES / "会议通知.docx").read_bytes())
    (tmp_path / "通知_AI修改.docx").write_bytes(b"existing")

    preview = SafeModificationService().prepare(source, plan({"action": "delete_text", "target": "会议"}))

    assert preview.output_path.name == "通知_AI修改_2.docx"
    assert preview.is_dangerous is True
    assert "删除所有“会议”" in preview.description


def test_execute_creates_verified_output_and_exact_backup(tmp_path: Path) -> None:
    source = tmp_path / "报销表.xlsx"
    source.write_bytes((SAMPLES / "报销表.xlsx").read_bytes())
    original = source.read_bytes()
    service = SafeModificationService()
    modification_plan = plan({"action": "replace_cell", "sheet": "报销表", "cell": "B2", "value": 500})
    preview = service.prepare(source, modification_plan)

    result = service.execute(preview, modification_plan)

    assert source.read_bytes() == original
    assert result.backup_path.read_bytes() == original
    assert result.output_path.name == "报销表_AI修改.xlsx"
    assert get_processor(result.output_path).read(result.output_path).worksheets[0].rows[1] == ["张三", 500]


def test_backup_can_restore_to_a_new_file_without_overwriting(tmp_path: Path) -> None:
    source = tmp_path / "通知.docx"
    source.write_bytes((SAMPLES / "会议通知.docx").read_bytes())
    service = SafeModificationService()
    modification_plan = plan({"action": "append_text", "text": "新增内容"})
    result = service.execute(service.prepare(source, modification_plan), modification_plan)
    restored = tmp_path / "通知_恢复版.docx"

    restore_path = service._backups.restore_to_new_file(result.backup_path, restored)

    assert restore_path.read_bytes() == source.read_bytes()
    with pytest.raises(SafetyError, match="已有同名"):
        service._backups.restore_to_new_file(result.backup_path, restored)


def test_query_or_pdf_plan_cannot_enter_modification_flow() -> None:
    service = SafeModificationService()

    with pytest.raises(SafetyError):
        service.prepare(SAMPLES / "报销通知.pdf", plan({"action": "summarize"}))


def test_output_save_validation_rejects_file_that_cannot_be_read(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "通知.docx"
    source.write_bytes((SAMPLES / "会议通知.docx").read_bytes())
    service = SafeModificationService()
    modification_plan = plan({"action": "append_text", "text": "新增内容"})
    preview = service.prepare(source, modification_plan)

    monkeypatch.setattr("app.services.safe_modification_service.SafeModificationService._validate_output", lambda *_args: (_ for _ in ()).throw(SafetyError("验证失败")))
    with pytest.raises(SafetyError):
        service.execute(preview, modification_plan)

    assert not preview.output_path.exists()
