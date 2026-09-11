"""从环境变量安全读取 AI 服务配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from dotenv import load_dotenv


class AiConfigurationError(RuntimeError):
    """AI 服务尚未完成配置；异常文本不包含密钥。"""

    user_message = "AI 服务暂时无法使用，请联系孩子帮忙检查。"


@dataclass(frozen=True)
class DeepSeekSettings:
    """DeepSeek 连接设置。API 密钥仅保存在内存中。"""

    api_key: str
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    timeout_seconds: float = 30.0

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "DeepSeekSettings":
        """加载 `.env` 或系统环境变量，绝不回显 API 密钥。"""
        if environment is None:
            load_dotenv(override=False)
            environment = os.environ
        api_key = environment.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise AiConfigurationError("未设置 AI 服务所需配置。")
        return cls(
            api_key=api_key,
            model=environment.get("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat",
            base_url=environment.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        )
