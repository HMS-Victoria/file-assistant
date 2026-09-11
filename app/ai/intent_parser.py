"""将用户自然语言转换为已验证的受限操作计划。"""

from __future__ import annotations

from pydantic import ValidationError

from app.ai.deepseek_client import AiServiceError, DeepSeekClient
from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.operations.schemas import OperationPlan, validate_operation_plan


class InvalidAiPlanError(RuntimeError):
    """AI 返回了不符合安全白名单的计划。"""

    user_message = "AI 服务这次没有理解清楚，请换一种说法后再试。"


class IntentParser:
    """AI 仅负责理解；本类不访问、更不修改用户文件。"""

    def __init__(self, client: DeepSeekClient) -> None:
        self._client = client

    def parse(self, user_request: str, file_kind: str) -> OperationPlan:
        """返回严格校验的计划，拒绝非法 JSON 与不在白名单中的动作。"""
        request = user_request.strip()
        if not request:
            raise ValueError("请先告诉我想怎样处理这个文件。")
        try:
            response_content = self._client.create_json_completion(
                SYSTEM_PROMPT,
                build_user_prompt(request, file_kind),
            )
            return validate_operation_plan(response_content)
        except ValidationError as error:
            raise InvalidAiPlanError("AI 计划没有通过本地安全校验。") from error
        except AiServiceError:
            raise
