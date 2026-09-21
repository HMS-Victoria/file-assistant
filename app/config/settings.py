"""固定用户配置位置；Windows DPAPI 保护密钥，不搜索工作目录。"""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Mapping

class AiConfigurationError(RuntimeError):
    """AI 服务尚未完成配置；异常文本不包含密钥。"""

    user_message = "尚未设置 AI 服务。请打开‘设置’，填写密钥并测试连接；本地查找和统计仍可使用。"


class SettingsStorageError(AiConfigurationError):
    user_message = "无法读取或保存设置。请检查当前用户目录的写入权限；若换过电脑或账户，请在设置中重新填写密钥。"


def settings_path() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    return (Path(root) if root else Path.home() / "AppData" / "Local") / "FileAssistant" / "settings.json"


def _protect(data: bytes, *, decrypt: bool = False) -> bytes:
    """使用当前 Windows 用户的 DPAPI；禁止任何交互式系统提示。"""
    if os.name != "nt":
        raise SettingsStorageError("密钥保存仅支持 Windows。")

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    operation = crypt32.CryptUnprotectData if decrypt else crypt32.CryptProtectData
    operation.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                          ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    operation.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    if not operation(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise SettingsStorageError("Windows 无法保护此配置。")
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        kernel32.LocalFree(output.data)


@dataclass(frozen=True)
class DeepSeekSettings:
    """密钥不参与对象文本显示；持久化时只存 DPAPI 密文。"""

    api_key: str = field(repr=False)
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    timeout_seconds: float = 30.0

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "DeepSeekSettings":
        """保留显式传入环境的开发接口；桌面端仅加载固定用户配置。"""
        if environment is None:
            settings = cls.load()
        else:
            settings = cls(
                api_key=environment.get("DEEPSEEK_API_KEY", "").strip(),
                model=environment.get("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat",
                base_url=environment.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            )
        if not settings.api_key:
            raise AiConfigurationError("未设置 AI 服务所需配置。")
        return settings

    @classmethod
    def load(cls) -> "DeepSeekSettings":
        path = settings_path()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("version") != 1 or not isinstance(payload.get("model"), str):
                raise ValueError("未知配置格式。")
            encrypted = payload["protected_key"]
            key = _protect(base64.b64decode(encrypted, validate=True), decrypt=True).decode("utf-8") if encrypted else ""
            return cls(api_key=key, model=payload["model"] or "deepseek-chat")
        except FileNotFoundError:
            return cls(api_key="")
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
            raise SettingsStorageError("无法读取用户配置。") from error

    def save(self) -> None:
        temporary: Path | None = None
        try:
            key = self.api_key.strip()
            payload = {"version": 1, "model": self.model.strip() or "deepseek-chat",
                       "protected_key": base64.b64encode(_protect(key.encode("utf-8"))).decode("ascii") if key else ""}
            path = settings_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            temporary.replace(path)
        except OSError as error:
            raise SettingsStorageError("无法保存用户配置。") from error
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
