# GitHub 测试版发布与交接

用户于 2026-09-21 明确授权：“你先推送上去吧，我找别人从 github 上面下载测试”。本记录更新此前仅本地交付、未推送发布的状态；2026-09-20 记录保留作历史追溯。

- 发布页：https://github.com/HMS-Victoria/file-assistant/releases/tag/v0.1.0-rc1
- 标签：`v0.1.0-rc1`；公开 prerelease，非草稿。
- 发布时刻（UTC）：`2026-09-21T02:02:00Z`。
- 程序源码提交：`abff6dac6fd1129fb1721f09ca64a273b6981d89`，已推送 main；Release 标签固定在此提交。后续主分支仅补充本文和发布证据。
- 本次源码快照：`5119f21204981f7c79ca3b52ca6fdcfe9db7912bb54b74ed886aeacb383782fa`。
- 本地同批资产：`D:\desktop\obj_ai\文件处理助手\release\0.1.0-rc1-20260921T015704Z`。

## 公开下载与复核

已匿名从三个公开资产链接重新下载，内容与本地完全一致。以下为实际下载文件：

- [FileAssistant-0.1.0-rc1-source.zip](https://github.com/HMS-Victoria/file-assistant/releases/download/v0.1.0-rc1/FileAssistant-0.1.0-rc1-source.zip)，103,291 字节，SHA-256 `72e40c63cbbd2fec929428c00da50628321ccf61a2c5d4435d989574d033ae1a`。
- [FileAssistant-0.1.0-rc1-windows-x64.zip](https://github.com/HMS-Victoria/file-assistant/releases/download/v0.1.0-rc1/FileAssistant-0.1.0-rc1-windows-x64.zip)，78,007,052 字节，SHA-256 `4b1a54a40ac037c7a3b9b3a008458e0098ccbee14677c9c9482d4539d66ce6ba`。
- [SHA256SUMS](https://github.com/HMS-Victoria/file-assistant/releases/download/v0.1.0-rc1/SHA256SUMS)，209 字节，SHA-256 `6afa8d37ddf37c3508509b33500d09edb598dd05bd3da5a6cbc3d9cc1c83dc53`。

公开下载的 Windows ZIP 再次解压到独立中文/空格目录，移除 Python/DeepSeek 外部环境变量并仅保留 System32 命令路径，自检返回 0。DOCX/XLSX/PDF 无密钥查找、Excel 求和、Word/Excel 备份/新文件重开/恢复、三类原件 SHA-256 不变、Windows DPAPI 合成凭据读回及清空均通过。

证据：`evidence/PUBLISHED.json`、`PUBLIC_DOWNLOAD_VERIFICATION.json`、`public-package-verification.json`、`BUILD_INFO.json`、`SHA256SUMS`。发布页文案见 `GITHUB_RELEASE_BODY.md`。

## 给测试者

下载 `windows-x64.zip`，完整解压后双击 `FileAssistant/文件小助手.exe`，保留 `_internal` 文件夹。无需自行安装 Python 或 Office。不要把源码 ZIP 当作程序包。

新电脑双击、拖放、中文输入及本人真实密钥下的 AI 计划预览仍待测试者验证。请沿用 [新电脑验收清单](../2026-09-20/NEW_PC_ACCEPTANCE.md)，反馈系统版本、重现步骤和中文错误提示，不反馈密钥或真实文档内容。

本次没有读取已有 `.env`、真实文档或修改系统 PATH；凭据仅通过 Git 已配置的凭据管理器取得并在发布进程内使用，没有输出或写入记录。未替作者指定项目许可证；保留第三方许可说明。
