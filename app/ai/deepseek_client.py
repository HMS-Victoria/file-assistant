"""DeepSeek Chat Completions API 的最小客户端。"""

from __future__ import annotations

from typing import Any

import httpx

from app.config.settings import DeepSeekSettings


class AiServiceError(RuntimeError):
    """可安全呈现给用户的 AI 服务异常。"""

    user_message = "AI 服务暂时无法使用，请稍后再试；如果一直无法使用，请联系孩子帮忙检查。"


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
            raise AiServiceError("AI 服务返回了无法使用的结果。") from error

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
            raise AiServiceError("AI 服务返回了无法使用的结果。") from error
