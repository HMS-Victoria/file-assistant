"""DeepSeek Chat Completions API 的最小客户端。"""

from __future__ import annotations

from typing import Any

import httpx

from app.config.settings import DeepSeekSettings


class AiServiceError(RuntimeError):
    """可安全呈现给用户的 AI 服务异常。"""

    user_message = "AI 服务暂时无法使用。请检查网络，并在‘设置’中核对密钥和模型、测试连接。"

    def __init__(self, message: str, user_message: str | None = None):
        super().__init__(message)
        if user_message:
            self.user_message = user_message


def _service_error(error: Exception) -> AiServiceError:
    message = None
    if isinstance(error, httpx.HTTPStatusError):
        message = {
            401: "密钥无效。请打开‘设置’，重新粘贴 DeepSeek 密钥后测试连接。",
            402: "AI 账户余额不足。请在 DeepSeek 开放平台检查余额后重试。",
            403: "AI 服务拒绝访问。请检查账户权限和密钥是否已启用。",
            400: "模型或请求无法使用。请在‘设置’中核对模型名称后重试。",
            404: "没有找到此模型或服务。请在‘设置’中核对模型名称。",
            429: "请求过于频繁，请稍等片刻再试。",
        }.get(error.response.status_code)
    elif isinstance(error, httpx.TimeoutException):
        message = "连接超时。请检查网络后重试；本地查找和统计仍可使用。"
    return AiServiceError("AI 服务返回了无法使用的结果。", message)


class DeepSeekClient:
    """只请求结构化意图，密钥不记录也不显示。"""

    def __init__(self, settings: DeepSeekSettings, client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = client or httpx.Client(timeout=settings.timeout_seconds)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def create_json_completion(self, system_prompt: str, user_prompt: str) -> str:
        """请求 JSON 对象；网络或响应格式异常转换为安全错误。"""
        payload: dict[str, Any] = {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        try:
            response = self._client.post(
                f"{self._settings.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._settings.api_key}"},
                json=payload,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("AI 响应内容为空。")
            return content
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            raise _service_error(error) from error

    def create_text_completion(self, system_prompt: str, user_prompt: str) -> str:
        """请求纯文本回答，供总结和问答使用。"""
        payload: dict[str, Any] = {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
        }
        try:
            response = self._client.post(
                f"{self._settings.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._settings.api_key}"},
                json=payload,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("AI 响应内容为空。")
            return content.strip()
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            raise _service_error(error) from error
