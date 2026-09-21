# 验证记录

## 平台与范围

日期：2026-09-20。开发机 Windows 11 10.0.26200 x64，Python 3.12.13。构建环境在本仓库 `.build-venv`，固定依赖见 `requirements-build.lock`。没有更改全局 PATH，没有删除作者配置或缓存。

以下检查必须区分：源代码自动化测试、离屏 Qt 控件调用、Windows Qt 渲染、冻结 exe 的合成自检、人工新电脑验收。最后一类仍未执行。

## 已执行

| 验证 | 方法 | 结果 |
|---|---|---|
| 源码与远端基线 | Git 状态、公开 REST API 只读刷新 | 初始工作区干净，本地/远端 main 为 cca9b6de8efebed3e158888fc8777b99c671a62b，无 Release |
| 原有保护逻辑基线 | 原环境 pytest | 41 passed；退出清理旧共享临时目录时有权限警告，不涉及应用测试失败 |
| 最终源码回归 | 独立构建环境，offscreen Qt，全新项目内临时目录 | 55 passed in 3.88s |
| 无密钥离线入口 | Qt 控件程序化调用，AI 客户端构造设为禁止 | DOCX/XLSX/PDF 查找、四种 Excel 统计和筛选通过 |
| AI 取消 | 模拟合法 AI 计划，程序化选择取消 | 原件不变，无新输出或备份 |
| 设置安全 | 实际 Windows DPAPI，合成不可用密钥 | 加密读回、清空、损坏配置中文错误、忽略工作目录 .env/环境密钥通过 |
| 连接测试 | 后台线程 + 模拟响应、HTTP 错误模拟 | 成功、401/402/404/429 中文提示；不回显密钥 |
| 写入失败 | 首先模拟 PermissionError；另在全新合成目录设置真实 Windows ACL 拒绝写入 | 窗口显示中文权限提示；原件 SHA-256 不变，无输出，随后恢复测试目录 ACL |
| Windows Qt 界面 | Qt windows 插件渲染主窗口和设置窗口，检查截图 | 中文可读，无控件重叠；不是人工桌面操作 |
| 冻结窗口版自检 | 修复 ICU 收集冲突后运行窗口版 exe，自造三类样例 | 离线查找/统计、DOCX/XLSX 修改/重开/恢复、三类原件 SHA-256、DPAPI 均通过 |

逐项证据见 `evidence/test-results.txt`、`permission-result.json`、`source-windows-result.json`、界面截图。最终 ZIP 的独立验收信息在本文件末尾及 `evidence/package-verification.json`。

## 复验方式

源代码回归（先创建项目内 build 目录，每次使用新的临时目录名）：

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.build-venv\Scripts\python.exe -m pytest -q --basetemp D:\desktop\obj_ai\文件处理助手\build\pytest-new-run
```

冻结包自检：完整解压最终 ZIP，在任意工作目录运行 `文件小助手.exe --self-test <全新目录>`。它只写指定新目录中的合成文件和独立用户配置，并输出 `result.json`，拒绝已存在目录。

`evidence/verify_package.py <发行目录> <全新验证目录>` 会核对 ZIP 哈希与完整性、源码逐文件哈希、运行库与资源、敏感文件名排除，重新解压到含中文和空格路径，清除 Python/DeepSeek/Qt 外部环境变量并仅保留 System32 命令路径后运行冻结自检。

`evidence/verify_permission.py <全新目录>` 只在该目录中的合成文档文件夹上临时设置当前用户拒绝写入权限，用模拟 AI 计划触发真实写入错误，并在 finally 中恢复测试目录权限。

## 失败与修复

最初 ZIP 不合格，已在旧发行目录标记 REJECTED.txt，禁止交付。根因、诊断证据、后续元数据读取修复、验收脚本修正均见 `BUILD_NOTES.md`。不得引用初次 ZIP 的哈希作为最终版本。

## 未验证和下一步

- 无 Python/Office 的干净 Windows 电脑上的人工双击、拖放、中文输入、缩放及长路径边界；Windows 10 实机。
- 本人真实 DeepSeek 账号/密钥下的连接测试和 AI 计划预览。仅用了合成密钥与模拟服务，没有读取现有 .env，也没有把它当作联网验收。
- 数字签名、SmartScreen 实际表现。
- 未获得远端发布授权，未推送、上传或发布；公开下载后 SHA-256 复核尚无可用发布资产可执行。
- 项目自身许可证及 PyMuPDF/Qt 的公开分发安排由作者确定；本地提供组件许可文本、元数据和本项目准确源码 ZIP。

新电脑记录已单列 `NEW_PC_ACCEPTANCE.md`，每项当前明确为未执行。**包已生成，实际环境验收待完成**；不称“下载即用”。

## 最终交付（已验证）

- 目录：`D:\desktop\obj_ai\文件处理助手\release\0.1.0-rc1-20260920T124753Z`
- 版本：`0.1.0-rc1`，基线 commit：`cca9b6de8efebed3e158888fc8777b99c671a62b`，本次修改未提交。
- 准确源码快照 ID：`13febc223eb9787912bdb82c4909a5ed3ca7994a74d109788ba8967cccce737b`；逐文件哈希见 `evidence/BUILD_INFO.json`。
- 从完整 ZIP 重新解压到中文/空格目录；冻结 exe 返回 0，使用 Windows Qt 平台；只保留 System32 命令路径，移除 Python/DeepSeek 外部环境变量。
- 471 项归档成员完整性通过。必需 Python/Qt/证书/文档模板存在；不含 .env、用户配置、真实文档或内部日志；唯一 DOCX 是 python-docx 官方空白模板。
- 打包程序原件哈希、修改后重开、恢复和真实 DPAPI 合成凭据检查全部通过；证据见 `evidence/package-verification.json` 与 `synthetic-document-evidence.zip`。
- `FileAssistant-0.1.0-rc1-windows-x64.zip`：78,004,042 字节；SHA-256 `741990e5bd8038e702614f59fa3e1ded2e075fbef0a1eb567b2497651ba9bdca`。
- `FileAssistant-0.1.0-rc1-source.zip`：103,220 字节；SHA-256 `8e5ffff25601bb0d29cd82c972fbc8822027322373204fa434ffe2dae3fa6c17`。

最终原始测试输出：`evidence/final-pytest.txt`。最后冻结程序截图：`evidence/frozen-main-window.png`、`evidence/frozen-settings-dialog.png`。

最后仅规范了文件末尾空行，差异格式检查通过；再次完整构建并从最终 ZIP 独立解压自检通过。
