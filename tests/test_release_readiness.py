"""发行路径回归：真实 DPAPI、离线界面、取消与保存失败。"""
from pathlib import Path
import json
import os
import shutil

import httpx
import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QLineEdit

from app.ai.deepseek_client import AiServiceError, DeepSeekClient
from app.config.settings import AiConfigurationError, DeepSeekSettings, SettingsStorageError, settings_path
from app.operations.schemas import validate_operation_plan
from app.services.safe_modification_service import OutputAccessError, SafeModificationService
from app.ui.main_window import MainWindow
from app.ui.settings_dialog import SettingsDialog

SAMPLES = Path(__file__).parent / "sample_files"


@pytest.fixture
def user_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "独立 用户"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_settings_ignore_cwd_dotenv_and_ambient_key(user_dir, monkeypatch):
    (user_dir / ".env").write_text("DEEPSEEK_API_KEY=never-read", encoding="utf-8")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "never-read")
    with pytest.raises(AiConfigurationError):
        DeepSeekSettings.from_environment()
    assert settings_path() == user_dir / "独立 用户/FileAssistant/settings.json"


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI")
def test_real_dpapi_roundtrip_clear_and_corruption(user_dir):
    settings = DeepSeekSettings(api_key="synthetic-secret", model="model-test")
    settings.save()
    assert "synthetic-secret" not in settings_path().read_text(encoding="utf-8")
    assert "synthetic-secret" not in repr(settings)
    assert DeepSeekSettings.load() == settings
    payload = json.loads(settings_path().read_text(encoding="utf-8"))
    payload["protected_key"] = "not-valid-base64!"
    settings_path().write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SettingsStorageError):
        DeepSeekSettings.load()
    DeepSeekSettings(api_key="").save()
    assert DeepSeekSettings.load().api_key == ""


def test_settings_unwritable_location_has_safe_error(user_dir):
    settings_path().parent.parent.mkdir(parents=True)
    settings_path().parent.write_text("synthetic obstruction", encoding="utf-8")
    with pytest.raises(SettingsStorageError):
        DeepSeekSettings(api_key="").save()


@pytest.mark.parametrize("filename,target", [("会议通知.docx", "张三"), ("报销表.xlsx", "张三"), ("报销通知.pdf", "2026")])
def test_ui_local_search_never_constructs_ai_client(user_dir, monkeypatch, filename, target):
    application = QApplication.instance() or QApplication([])
    def forbidden(*args):
        pytest.fail("local operation tried to construct an AI client")
    monkeypatch.setattr("app.ui.main_window.DeepSeekClient", forbidden)
    window = MainWindow()
    shown = []
    window._show_message = lambda *args: shown.append(args)
    window.select_file(SAMPLES / filename)
    window.mode_input.setCurrentIndex(window.mode_input.findData("find_text"))
    window.request_input.setText(target)
    window.handle_start()
    assert shown[-1][0] == "处理结果"
    assert "找到" in shown[-1][1]
    window.close()


def test_ui_local_statistics_and_filter(user_dir, monkeypatch):
    application = QApplication.instance() or QApplication([])
    monkeypatch.setattr("app.ui.main_window.DeepSeekClient", lambda *args: pytest.fail("network path"))
    window = MainWindow()
    shown = []
    window._show_message = lambda *args: shown.append(args)
    window.select_file(SAMPLES / "报销表.xlsx")
    window.column_input.setText("金额")
    for mode in ("calculate_sum", "calculate_average", "calculate_max", "calculate_min"):
        window.mode_input.setCurrentIndex(window.mode_input.findData(mode))
        window.handle_start()
        assert shown[-1][0] == "处理结果" and "200" in shown[-1][1]
    window.mode_input.setCurrentIndex(window.mode_input.findData("filter_rows"))
    window.column_input.setText("姓名")
    window.request_input.setText("张三")
    window.handle_start()
    assert "找到 1 条记录" in shown[-1][1]
    window.close()


def test_ui_cancel_ai_modification_writes_nothing(user_dir, monkeypatch):
    application = QApplication.instance() or QApplication([])
    source = user_dir / "中文 空格.docx"
    shutil.copy2(SAMPLES / "会议通知.docx", source)
    before = source.read_bytes()
    plan = validate_operation_plan({"explanation": "测试", "operations": [{"action": "replace_text", "target": "张三", "replacement": "李四"}]})
    monkeypatch.setattr(DeepSeekSettings, "from_environment", lambda: DeepSeekSettings(api_key="synthetic"))
    class FakeClient:
        def __init__(self, *args): pass
        def close(self): pass
    monkeypatch.setattr("app.ui.main_window.DeepSeekClient", FakeClient)
    monkeypatch.setattr("app.ui.main_window.IntentParser.parse", lambda *args: plan)
    window = MainWindow()
    window.select_file(source)
    window.request_input.setText("替换姓名")
    previews = []
    window._confirm_modification = lambda *args: previews.append(args) or False
    window.handle_start()
    assert previews and "张三" in previews[0][0]
    assert source.read_bytes() == before
    assert list(user_dir.iterdir()) == [source]
    window.close()


def test_backup_permission_failure_preserves_original(user_dir, monkeypatch):
    source = user_dir / "测试.docx"
    shutil.copy2(SAMPLES / "会议通知.docx", source)
    before = source.read_bytes()
    plan = validate_operation_plan({"explanation": "测试", "operations": [{"action": "append_text", "text": "新内容"}]})
    service = SafeModificationService()
    preview = service.prepare(source, plan)
    def denied(*args): raise PermissionError("simulated denied")
    monkeypatch.setattr(service._backups, "create_backup", denied)
    with pytest.raises(OutputAccessError) as caught:
        service.execute(preview, plan)
    assert "写入权限" in caught.value.user_message
    assert source.read_bytes() == before
    assert not preview.output_path.exists()


def test_settings_dialog_cancel_and_background_connection(user_dir, monkeypatch):
    application = QApplication.instance() or QApplication([])
    dialog = SettingsDialog()
    assert dialog.key_input.echoMode() == QLineEdit.EchoMode.Password
    dialog.key_input.setText("synthetic")
    dialog.reject()
    assert not settings_path().exists()
    dialog = SettingsDialog()
    dialog.key_input.setText("synthetic")
    monkeypatch.setattr(DeepSeekClient, "create_text_completion", lambda *args: "连接成功")
    loop = QEventLoop()
    dialog.test_connection()
    dialog.worker.finished.connect(loop.quit)
    QTimer.singleShot(10000, loop.quit)
    loop.exec()
    application.processEvents()
    assert "连接成功" in dialog.status_label.text()
    assert dialog.worker is None
    dialog.close()


@pytest.mark.parametrize("status,expected", [(401, "密钥无效"), (402, "余额不足"), (429, "频繁"), (404, "模型")])
def test_actionable_connection_errors_hide_secrets(status, expected):
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status, json={"error": "synthetic-secret"}))) as transport:
        client = DeepSeekClient(DeepSeekSettings(api_key="synthetic-secret"), transport)
        with pytest.raises(AiServiceError) as caught:
            client.create_text_completion("test", "test")
        assert expected in caught.value.user_message
        assert "synthetic-secret" not in caught.value.user_message
