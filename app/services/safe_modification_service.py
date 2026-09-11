"""修改前预览、备份、输出命名与保存验证。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import copy2

from app.operations.schemas import (
    AppendColumn, AppendRow, AppendText, DeleteColumn, DeleteRow, DeleteText,
    OperationPlan, ReplaceCell, ReplaceText,
)
from app.processors.factory import get_processor
from app.services.modification_service import ModificationResult, ModificationService


MODIFICATION_ACTIONS = {
    "replace_text", "append_text", "delete_text", "replace_cell", "append_row",
    "delete_row", "append_column", "delete_column",
}
DANGEROUS_ACTIONS = {"delete_text", "delete_row", "delete_column"}


class SafetyError(RuntimeError):
    """安全工作流中的可读错误。"""

    user_message = "为了保护原文件，这次没有生成新文件。请稍后再试。"


@dataclass(frozen=True)
class ModificationPreview:
    """确认前展示给用户的完整修改说明。"""

    source_path: Path
    output_path: Path
    description: str
    is_dangerous: bool


@dataclass(frozen=True)
class SafeModificationResult:
    """已备份、已验证的新文件结果。"""

    output_path: Path
    backup_path: Path
    changes: list[str]


class BackupService:
    """将原文件复制到应用内部备份目录，便于恢复。"""

    directory_name = ".file_assistant_backups"

    def create_backup(self, source_path: Path, output_path: Path) -> Path:
        backup_directory = source_path.parent / self.directory_name
        backup_directory.mkdir(exist_ok=True)
        backup_path = backup_directory / f"{output_path.stem}_原文件备份{source_path.suffix}"
        if backup_path.exists():
            raise SafetyError("备份文件已存在。")
        copy2(source_path, backup_path)
        if backup_path.read_bytes() != source_path.read_bytes():
            backup_path.unlink(missing_ok=True)
            raise SafetyError("原文件备份验证失败。")
        return backup_path

    def restore_to_new_file(self, backup_path: Path, restore_path: Path) -> Path:
        """从备份恢复为新文件，仍不允许覆盖任何现有文件。"""
        if not backup_path.is_file():
            raise SafetyError("找不到原文件备份。")
        if restore_path.exists():
            raise SafetyError("恢复位置已有同名文件。")
        if backup_path.suffix.lower() != restore_path.suffix.lower():
            raise SafetyError("恢复文件类型不一致。")
        copy2(backup_path, restore_path)
        if restore_path.read_bytes() != backup_path.read_bytes():
            restore_path.unlink(missing_ok=True)
            raise SafetyError("恢复文件验证失败。")
        return restore_path


class SafeModificationService:
    """协调“预览 → 确认后调用 execute → 备份和验证”的安全流程。"""

    def __init__(self, modifier: ModificationService | None = None, backups: BackupService | None = None) -> None:
        self._modifier = modifier or ModificationService()
        self._backups = backups or BackupService()

    def prepare(self, source_path: Path, plan: OperationPlan) -> ModificationPreview:
        source = source_path.resolve()
        if not source.is_file() or source.suffix.lower() not in {".docx", ".xlsx"}:
            raise SafetyError("目前只能修改 Word 或 Excel 文件。")
        if not plan.operations or any(operation.action not in MODIFICATION_ACTIONS for operation in plan.operations):
            raise SafetyError("这不是可以安全修改的请求。")
        output = self._new_output_path(source)
        return ModificationPreview(
            source_path=source,
            output_path=output,
            description=self._describe(plan),
            is_dangerous=any(operation.action in DANGEROUS_ACTIONS for operation in plan.operations),
        )

    def execute(self, preview: ModificationPreview, plan: OperationPlan) -> SafeModificationResult:
        """仅在界面确认后调用；先备份，再生成、验证新文件。"""
        if preview.output_path.exists() or preview.source_path == preview.output_path:
            raise SafetyError("新文件名已被占用，请重新开始。")
        backup = self._backups.create_backup(preview.source_path, preview.output_path)
        try:
            result = self._modifier.apply(preview.source_path, preview.output_path, plan)
            self._validate_output(preview.source_path, result)
        except Exception as error:
            preview.output_path.unlink(missing_ok=True)
            if isinstance(error, SafetyError):
                raise
            raise SafetyError("生成新文件时发生问题。") from error
        return SafeModificationResult(result.output_path, backup, result.changes)

    @staticmethod
    def _new_output_path(source: Path) -> Path:
        base_name = f"{source.stem}_AI修改"
        candidate = source.with_name(f"{base_name}{source.suffix}")
        number = 2
        while candidate.exists():
            candidate = source.with_name(f"{base_name}_{number}{source.suffix}")
            number += 1
        return candidate

    @staticmethod
    def _validate_output(source: Path, result: ModificationResult) -> None:
        output = result.output_path
        if not output.is_file() or output.stat().st_size == 0:
            raise SafetyError("新文件保存不完整。")
        if get_processor(source).kind != get_processor(output).kind:
            raise SafetyError("新文件类型验证失败。")
        get_processor(output).read(output)

    @staticmethod
    def _describe(plan: OperationPlan) -> str:
        descriptions: list[str] = []
        for operation in plan.operations:
            if isinstance(operation, ReplaceText):
                descriptions.append(f"将“{operation.target}”替换为“{operation.replacement}”")
            elif isinstance(operation, DeleteText):
                descriptions.append(f"删除所有“{operation.target}”")
            elif isinstance(operation, AppendText):
                descriptions.append("在文档最后增加一段文字")
            elif isinstance(operation, ReplaceCell):
                descriptions.append(f"修改“{operation.sheet}”的 {operation.cell}")
            elif isinstance(operation, AppendRow):
                descriptions.append(f"在“{operation.sheet}”最后增加一行")
            elif isinstance(operation, DeleteRow):
                descriptions.append(f"删除“{operation.sheet}”的第 {operation.row} 行")
            elif isinstance(operation, AppendColumn):
                descriptions.append(f"在“{operation.sheet}”最后增加一列")
            elif isinstance(operation, DeleteColumn):
                descriptions.append(f"删除“{operation.sheet}”的第 {operation.column} 列")
        return "\n".join(f"- {description}" for description in descriptions)
