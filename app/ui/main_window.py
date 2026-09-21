"""Milestone 1 的单窗口主界面。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ai.deepseek_client import AiServiceError, DeepSeekClient
from app.ai.intent_parser import IntentParser, InvalidAiPlanError
from app.config.settings import AiConfigurationError, DeepSeekSettings
from app.operations.schemas import validate_operation_plan
from pydantic import ValidationError
from app.processors.factory import get_processor
from app.services.safe_modification_service import SafeModificationService, SafetyError
from app.services.query_service import QueryError, QueryService
from app.ui.drop_area import DropArea, SUPPORTED_SUFFIXES
from app.ui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """让用户完成“拖文件、说需求、开始处理”的第一阶段界面。"""

    def __init__(self) -> None:
        super().__init__()
        self.selected_file: Path | None = None
        self.setWindowTitle("文件小助手")
        self.setMinimumSize(700, 760)
        self._build_ui()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(12)

        title = QLabel("文件小助手")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("title")
        layout.addWidget(title)

        self.settings_button = QPushButton("设置")
        self.settings_button.setMinimumHeight(44)
        self.settings_button.clicked.connect(lambda: SettingsDialog(self).exec())
        layout.addWidget(self.settings_button)

        drop_area = DropArea(self.select_file)
        drop_area.setMinimumHeight(130)
        layout.addWidget(drop_area)

        self.file_label = QLabel("文件：还没有选择文件")
        self.file_label.setObjectName("fileLabel")
        self.file_label.setWordWrap(True)
        layout.addWidget(self.file_label)

        self.mode_input = QComboBox()
        self.mode_input.setMinimumHeight(40)
        self.mode_input.setAccessibleName("处理方式")
        for label, action in [("AI 帮我处理（需要设置）", "ai"), ("本地查找文字（无需联网）", "find_text"),
                              ("Excel 求和（无需联网）", "calculate_sum"), ("Excel 平均值（无需联网）", "calculate_average"),
                              ("Excel 最大值（无需联网）", "calculate_max"), ("Excel 最小值（无需联网）", "calculate_min"),
                              ("Excel 筛选（无需联网）", "filter_rows")]:
            self.mode_input.addItem(label, action)
        layout.addWidget(self.mode_input)
        self.sheet_input = QLineEdit()
        self.sheet_input.setMaxLength(200)
        self.sheet_input.setPlaceholderText("工作表名称（留空使用第一个工作表）")
        self.sheet_input.setAccessibleName("工作表名称")
        layout.addWidget(self.sheet_input)
        self.column_input = QLineEdit()
        self.column_input.setMaxLength(200)
        self.column_input.setPlaceholderText("第一行的列名，例如：金额")
        self.column_input.setAccessibleName("统计或筛选列名")
        layout.addWidget(self.column_input)

        request_label = QLabel("你想让我做什么？")
        self.request_label = request_label
        request_label.setObjectName("requestLabel")
        layout.addWidget(request_label)

        self.request_input = QLineEdit()
        self.request_input.setPlaceholderText("例如：帮我看看这个文件里写了什么")
        self.request_input.setMinimumHeight(54)
        self.request_input.setAccessibleName("处理要求")
        self.request_input.setMaxLength(1000)
        layout.addWidget(self.request_input)
        self.mode_input.currentIndexChanged.connect(self._update_mode)
        self._update_mode()

        self.start_button = QPushButton("开始处理")
        self.start_button.setMinimumHeight(62)
        self.start_button.clicked.connect(self.handle_start)
        layout.addWidget(self.start_button)
        layout.addStretch()

        self.setCentralWidget(central_widget)
        self.setStyleSheet(
            "QWidget { font-family: 'Microsoft YaHei'; font-size: 18px; }"
            "#title { font-size: 32px; font-weight: 700; color: #2374b6; }"
            "#dropArea { border: 3px dashed #5b8fc7; border-radius: 14px; background: #f3f8ff; }"
            "#dropHint { font-size: 23px; font-weight: 600; color: #295a8b; }"
            "#fileLabel, #requestLabel { font-size: 19px; font-weight: 600; }"
            "QLineEdit { border: 2px solid #9bb8d5; border-radius: 8px; padding: 8px; }"
            "QPushButton { background: #2374b6; color: white; border: 0; border-radius: 10px; font-size: 22px; font-weight: 700; }"
            "QPushButton:hover { background: #185d96; }"
        )

    def select_file(self, file_path: Path) -> None:
        """校验拖入的文件，显示给用户但不读取它的内容。"""
        if not file_path.is_file():
            self._show_message("没有找到这个文件", "请重新把文件拖进窗口。")
            return
        if file_path.suffix.lower() not in SUPPORTED_SUFFIXES:
            self._show_message("暂不支持这个文件", "请拖入 Word（.docx）、Excel（.xlsx）或 PDF（.pdf）文件。")
            return

        self.selected_file = file_path
        self.file_label.setText(f"文件：{file_path.name}")

    def handle_start(self) -> None:
        """执行查询，或让用户确认后生成已验证的新文件。"""
        if self.selected_file is None:
            self._show_message("请先选择文件", "把 Word、Excel 或 PDF 文件拖到上面的区域。")
            return
        mode = self.mode_input.currentData()
        if mode in {"ai", "find_text", "filter_rows"} and not self.request_input.text().strip():
            self._show_message("还没有告诉我怎么处理", "请在输入框中写下您想让我帮忙做的事。")
            return
        try:
            if mode != "ai":
                operation = {"action": mode}
                if mode == "find_text":
                    operation["target"] = self.request_input.text().strip()
                else:
                    operation["sheet"] = self.sheet_input.text().strip() or None
                    operation["column"] = self.column_input.text().strip() or None
                    if mode == "filter_rows":
                        operation["value"] = self.request_input.text().strip()
                plan = validate_operation_plan({"explanation": "在本机查询，不修改文件。", "operations": [operation]})
                result = QueryService().execute(self.selected_file, plan)
                self._show_message("处理结果", result.text, QMessageBox.Icon.Information)
                return
            settings = DeepSeekSettings.from_environment()
            client = DeepSeekClient(settings)
            try:
                plan = IntentParser(client).parse(
                    self.request_input.text(),
                    get_processor(self.selected_file).kind,
                )
                safety_service = SafeModificationService()
                if any(operation.action in {"replace_text", "append_text", "delete_text", "replace_cell", "append_row", "delete_row", "append_column", "delete_column"} for operation in plan.operations):
                    preview = safety_service.prepare(self.selected_file, plan)
                    if not self._confirm_modification(preview.description, preview.is_dangerous):
                        return
                    modification = safety_service.execute(preview, plan)
                    self._show_message(
                        "处理完成 ✓",
                        f"已经生成新文件：\n{modification.output_path.name}\n\n原文件没有被修改，已创建内部备份。",
                        QMessageBox.Icon.Information,
                    )
                    return
                result = QueryService(client).execute(self.selected_file, plan)
            finally:
                client.close()
        except (AiConfigurationError, AiServiceError, InvalidAiPlanError, QueryError, SafetyError) as error:
            self._show_message("暂时不能处理", error.user_message)
            return
        except ValidationError:
            self._show_message("请检查填写内容", "查找文字或筛选值最多 500 字；筛选时请填写第一行的列名。")
            return
        except OSError:
            self._show_message("文件无法读取或保存", "请确认文件仍存在，关闭占用它的程序，并将文件复制到您有写入权限的文件夹后重试。原文件不会被覆盖。")
            return

        self._show_message(
            "处理结果",
            f"我理解到：\n{plan.explanation}\n\n结果：\n{result.text}",
            QMessageBox.Icon.Information,
        )

    def _update_mode(self) -> None:
        mode = self.mode_input.currentData()
        excel = mode.startswith("calculate_") or mode == "filter_rows"
        self.sheet_input.setVisible(excel)
        self.column_input.setVisible(excel)
        self.request_input.setVisible(not mode.startswith("calculate_"))
        self.request_label.setVisible(not mode.startswith("calculate_"))
        self.request_input.setPlaceholderText(
            "输入要查找的原文" if mode == "find_text" else
            "输入要筛选的值，例如：张三" if mode == "filter_rows" else
            "例如：把张三替换成李四（修改前会请您确认）"
        )

    def _confirm_modification(self, description: str, is_dangerous: bool) -> bool:
        """明确显示修改内容，删除类操作使用更醒目的确认说明。"""
        warning = "\n\n注意：这项操作会删除内容。" if is_dangerous else ""
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("请确认修改")
        dialog.setText(f"我准备这样处理：\n\n{description}{warning}\n\n原文件不会被覆盖。确认后将生成一个新文件。")
        confirm = dialog.addButton("确认修改", QMessageBox.ButtonRole.AcceptRole)
        dialog.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(confirm)
        dialog.exec()
        return dialog.clickedButton() is confirm

    def _show_message(self, title: str, message: str, icon: QMessageBox.Icon = QMessageBox.Icon.Warning) -> None:
        dialog = QMessageBox(self)
        dialog.setIcon(icon)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.exec()
