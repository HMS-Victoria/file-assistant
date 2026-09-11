"""Milestone 1 界面的自动测试。"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.config.settings import AiConfigurationError
from app.ui.main_window import MainWindow


def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_window_has_expected_controls() -> None:
    app()
    window = MainWindow()
    assert window.windowTitle() == "文件小助手"
    assert window.start_button.text() == "开始处理"
    assert "你想让我做什么" in window.centralWidget().findChild(type(window.file_label), "requestLabel").text()


def test_selecting_supported_file_displays_name(tmp_path: Path) -> None:
    app()
    file_path = tmp_path / "报销表.xlsx"
    file_path.touch()
    window = MainWindow()

    window.select_file(file_path)

    assert window.selected_file == file_path
    assert window.file_label.text() == "文件：报销表.xlsx"


def test_unsupported_file_is_not_selected(tmp_path: Path) -> None:
    app()
    file_path = tmp_path / "照片.jpg"
    file_path.touch()
    window = MainWindow()
    window._show_message = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    window.select_file(file_path)

    assert window.selected_file is None


def test_start_with_no_ai_configuration_shows_plain_language_error(tmp_path: Path, monkeypatch) -> None:
    app()
    file_path = tmp_path / "报销表.xlsx"
    file_path.touch()
    window = MainWindow()
    shown: list[tuple[str, str]] = []
    window._show_message = lambda title, message, *_args: shown.append((title, message))  # type: ignore[method-assign]
    def no_settings():
        raise AiConfigurationError("测试环境没有配置。")

    monkeypatch.setattr("app.ui.main_window.DeepSeekSettings.from_environment", no_settings)

    window.select_file(file_path)
    window.request_input.setText("帮我总结")
    window.handle_start()

    assert shown == [("暂时不能处理", "AI 服务暂时无法使用，请联系孩子帮忙检查。")]
