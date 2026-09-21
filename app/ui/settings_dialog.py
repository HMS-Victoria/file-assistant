"""首次配置窗口：密钥遮挡、当前用户加密存储、后台连接测试。"""

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QPushButton

from app.ai.deepseek_client import AiServiceError, DeepSeekClient
from app.config.settings import AiConfigurationError, DeepSeekSettings


class ConnectionTest(QThread):
    result = Signal(str)

    def __init__(self, settings: DeepSeekSettings, parent=None):
        super().__init__(parent)
        self.settings = settings

    def run(self):
        try:
            client = DeepSeekClient(self.settings)
            try:
                client.create_text_completion("请只回复：连接成功", "这是连接测试，不包含用户文件。")
            finally:
                client.close()
            message = "连接成功，可以保存设置。"
        except AiServiceError as error:
            message = error.user_message
        except Exception:
            message = "连接测试失败。请检查网络、密钥、账户余额和模型名称后重试。"
        self.result.emit(message)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.setWindowTitle("AI 服务设置")
        self.setMinimumWidth(530)
        layout = QFormLayout(self)
        hint = QLabel("本地查找和统计无需设置。\n需要 AI 时，填写您在 DeepSeek 开放平台申请的密钥。\n测试连接会发送简短测试文字，可能产生少量服务费用。")
        hint.setWordWrap(True)
        layout.addRow(hint)
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setAccessibleName("服务密钥")
        self.key_input.setPlaceholderText("粘贴 API Key；清空后保存可停用 AI")
        self.model_input = QLineEdit("deepseek-chat")
        self.model_input.setMaxLength(200)
        self.status_label = QLabel("密钥由 Windows 加密，仅当前电脑的当前账户可用。")
        self.status_label.setWordWrap(True)
        layout.addRow("服务密钥", self.key_input)
        layout.addRow("模型名称", self.model_input)
        self.test_button = QPushButton("测试连接")
        self.save_button = QPushButton("保存设置")
        self.cancel_button = QPushButton("取消")
        for button in (self.test_button, self.save_button, self.cancel_button):
            button.setMinimumHeight(44)
            layout.addRow(button)
        layout.addRow(self.status_label)
        self.test_button.clicked.connect(self.test_connection)
        self.save_button.clicked.connect(self.save_settings)
        self.cancel_button.clicked.connect(self.reject)
        try:
            saved = DeepSeekSettings.load()
            self.key_input.setText(saved.api_key)
            self.model_input.setText(saved.model)
        except AiConfigurationError as error:
            self.status_label.setText(error.user_message)

    def settings(self):
        return DeepSeekSettings(api_key=self.key_input.text().strip(), model=self.model_input.text().strip() or "deepseek-chat")

    def save_settings(self):
        try:
            self.settings().save()
        except AiConfigurationError as error:
            self.status_label.setText(error.user_message)
            return
        self.accept()

    def test_connection(self):
        settings = self.settings()
        if not settings.api_key:
            self.status_label.setText("请先填写服务密钥，再测试连接。")
            return
        self.test_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.status_label.setText("正在连接，请稍候（约 30 秒）……")
        self.worker = ConnectionTest(settings, self)
        self.worker.result.connect(self.status_label.setText)
        self.worker.finished.connect(self._test_finished)
        self.worker.start()

    def _test_finished(self):
        self.test_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.worker.deleteLater()
        self.worker = None

    def reject(self):
        if self.worker is not None:
            self.status_label.setText("请等待连接测试结束后再关闭。")
            return
        super().reject()

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
        else:
            super().closeEvent(event)
