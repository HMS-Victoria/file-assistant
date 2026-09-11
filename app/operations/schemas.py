"""严格定义 AI 可返回的操作白名单。"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class OperationBase(BaseModel):
    """所有操作的共同安全约束：禁止附带未知字段或代码。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FindText(OperationBase):
    action: Literal["find_text"]
    target: str = Field(min_length=1, max_length=500)


class Summarize(OperationBase):
    action: Literal["summarize"]


class QuestionAnswer(OperationBase):
    action: Literal["question_answer"]
    question: str = Field(min_length=1, max_length=1000)


class Calculation(OperationBase):
    action: Literal["calculate_sum", "calculate_average", "calculate_max", "calculate_min"]
    sheet: str | None = Field(default=None, max_length=200)
    column: str | None = Field(default=None, max_length=200)


class FilterRows(OperationBase):
    action: Literal["filter_rows"]
    column: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=500)
    sheet: str | None = Field(default=None, max_length=200)


class ReplaceText(OperationBase):
    action: Literal["replace_text"]
    target: str = Field(min_length=1, max_length=1000)
    replacement: str = Field(max_length=1000)


class AppendText(OperationBase):
    action: Literal["append_text"]
    text: str = Field(min_length=1, max_length=3000)


class DeleteText(OperationBase):
    action: Literal["delete_text"]
    target: str = Field(min_length=1, max_length=1000)


class ReplaceCell(OperationBase):
    action: Literal["replace_cell"]
    sheet: str = Field(min_length=1, max_length=200)
    cell: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z]{1,3}[1-9][0-9]*$")
    value: str | int | float | None


class AppendRow(OperationBase):
    action: Literal["append_row"]
    sheet: str = Field(min_length=1, max_length=200)
    values: list[str | int | float | None] = Field(min_length=1, max_length=100)


class DeleteRow(OperationBase):
    action: Literal["delete_row"]
    sheet: str = Field(min_length=1, max_length=200)
    row: int = Field(ge=1, le=1_000_000)


class AppendColumn(OperationBase):
    action: Literal["append_column"]
    sheet: str = Field(min_length=1, max_length=200)
    values: list[str | int | float | None] = Field(min_length=1, max_length=100_000)


class DeleteColumn(OperationBase):
    action: Literal["delete_column"]
    sheet: str = Field(min_length=1, max_length=200)
    column: int = Field(ge=1, le=16_384)


Operation = Annotated[
    Union[
        FindText, Summarize, QuestionAnswer, Calculation, FilterRows,
        ReplaceText, AppendText, DeleteText, ReplaceCell, AppendRow,
        DeleteRow, AppendColumn, DeleteColumn,
    ],
    Field(discriminator="action"),
]


class OperationPlan(BaseModel):
    """经过 Schema 校验后才能传递给未来本地执行层的操作计划。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    explanation: str = Field(min_length=1, max_length=1000)
    operations: list[Operation] = Field(min_length=1, max_length=20)


_PLAN_ADAPTER = TypeAdapter(OperationPlan)


def validate_operation_plan(payload: str | bytes | dict[str, object]) -> OperationPlan:
    """验证 JSON 计划。未知操作、未知字段和无效参数一律拒绝。"""
    if isinstance(payload, (str, bytes)):
        return _PLAN_ADAPTER.validate_json(payload)
    return _PLAN_ADAPTER.validate_python(payload)
