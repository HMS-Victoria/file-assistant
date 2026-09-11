"""Milestone 3：AI JSON 校验与网络客户端测试。"""

from __future__ import annotations

import json

import httpx
import pytest
from pydantic import ValidationError

from app.ai.deepseek_client import AiServiceError, DeepSeekClient
from app.ai.intent_parser import IntentParser, InvalidAiPlanError
from app.config.settings import AiConfigurationError, DeepSeekSettings
from app.operations.schemas import validate_operation_plan


class FakeClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.called_with: tuple[str, str] | None = None

    def create_json_completion(self, system_prompt: str, user_prompt: str) -> str:
        self.called_with = (system_prompt, user_prompt)
        return self.response


def test_intent_parser_returns_valid_whitelisted_plan() -> None:
    client = FakeClient('{"explanation":"查找姓名","operations":[{"action":"find_text","target":"张三"}]}')

    plan = IntentParser(client).parse("找一下张三", "excel")  # type: ignore[arg-type]

    assert plan.operations[0].action == "find_text"
    assert client.called_with is not None
    assert "用户要求：找一下张三" in client.called_with[1]
    assert "本机路径" not in client.called_with[1]


@pytest.mark.parametrize(
    "payload",
    [
        '{"explanation":"执行代码","operations":[{"action":"execute_python","code":"import os"}]}',
        '{"explanation":"替换","operations":[{"action":"replace_text","target":"张三","replacement":"李四","code":"x"}]}',
        '{"explanation":"空计划","operations":[]}',
    ],
)
def test_illegal_or_unknown_ai_operations_are_rejected(payload: str) -> None:
    with pytest.raises(ValidationError):
        validate_operation_plan(payload)


def test_intent_parser_converts_invalid_json_to_safe_error() -> None:
    parser = IntentParser(FakeClient('{"operations":[{"action":"exec"}]}'))  # type: ignore[arg-type]

    with pytest.raises(InvalidAiPlanError) as error:
        parser.parse("运行代码", "word")

    assert "代码" not in error.value.user_message


def test_missing_key_does_not_expose_configuration_details() -> None:
    with pytest.raises(AiConfigurationError) as error:
        DeepSeekSettings.from_environment({})

    assert "API" not in error.value.user_message


def test_client_requests_json_mode_without_leaking_key() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"explanation":"总结","operations":[{"action":"summarize"}]}'}}]})

    settings = DeepSeekSettings(api_key="secret-test-key", base_url="https://example.test")
    client = DeepSeekClient(settings, httpx.Client(transport=httpx.MockTransport(handler)))

    result = client.create_json_completion("系统提示", "用户提示")

    assert json.loads(result)["operations"][0]["action"] == "summarize"
    assert captured["url"] == "https://example.test/chat/completions"
    assert captured["authorization"] == "Bearer secret-test-key"
    assert captured["payload"] == {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": "系统提示"}, {"role": "user", "content": "用户提示"}],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }


def test_client_hides_network_errors_from_user() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid secret-test-key"}})

    client = DeepSeekClient(
        DeepSeekSettings(api_key="secret-test-key", base_url="https://example.test"),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(AiServiceError) as error:
        client.create_json_completion("系统提示", "用户提示")

    assert "secret-test-key" not in error.value.user_message
