# 构建与验证故障记录

## 已修复：QtWidgets DLL 启动失败

初次包 `release/0.1.0-rc1-20260920T122332Z/` **已拒收，不能交付**。
首次从 ZIP 解压后运行超时；进一步捕获到 `ImportError: DLL load failed while importing QtWidgets`。
构建 Analysis-00.toc 显示 `icuuc.dll` 来自 Codex 附带 Poppler 的 Library/bin，而非 Windows 系统。
该同名 ICU 的导出符号与 Qt 需要的 Windows ICU 不一致。诊断包仅移出这个库后，冻结程序自检即通过。

最终修复：构建子进程 PATH 只含隔离构建环境、Python 基础目录、Windows System32；清除外部 Python/Qt 搜索变量；spec 显式排除 `icuuc.dll`，使用受支持 Windows 自带 ICU。公开系统说明细化到 Windows 10 1809 或更新版本 / Windows 11 x64。

参考原始文档：
- Qt Windows 支持：https://doc.qt.io/qt-6/windows.html
- Windows 内置 ICU：https://learn.microsoft.com/en-us/windows/win32/intl/international-components-for-unicode--icu-

诊断包与初次失败包仅保留在本仓库隔离构建目录以供追溯；最终交付目录见 VERIFICATION.md。不能上传旧 ZIP。

## 验证脚本调整

- 首轮 pytest 的基目录父目录尚不存在，导致临时目录 setup 错误；创建项目内 build/ 并用全新绝对基目录后 55 项通过。
- 包内隐私文件名扫描起初把 python-docx 自带的 `docx/templates/default.docx` 视作用户文档。改为只允许这一个官方空白模板，其他 DOCX/XLSX/PDF、配置和日志仍拒绝进入用户包。
- 真实 ACL 拒绝写入测试中，Windows 同时拒绝了当时的目录枚举；把最终目录清单核对移到恢复测试目录 ACL 之后。中文错误与原件哈希核对均通过，测试目录权限已恢复。
- 初次离屏图缺少系统中文字体，且发现原尺寸下统计控件拥挤。调整主窗口布局后改用 Windows Qt 平台插件渲染，中文可读、控件无重叠；这不是人工桌面交互验收。
- 执行中沙箱服务账户出现 CreateProcessWithLogonW 1909 登录错误；随后经工具自动审核使用受限任务范围的主机执行完成构建和合成验证。没有读取已有密钥、真实文档或改全局 PATH。

## 已修复：第三方元数据序列化

第二次构建生成的窗口版程序已完成，但收集许可说明时把已解析的包元数据重新作为邮件头序列化，遇到 altgraph 多行说明导致 HeaderParseError。已改为直接读取原始 METADATA/PKG-INFO，并先验证全部已安装分发元数据均可读取。该中间目录没有最终 ZIP，最终候选重新完整构建。

## 最后界面修正

在最终冻结程序的 Windows 深色主题截图中发现主标题对比度偏低，已仅调整标题蓝色，并重新构建和复验同批源码与 ZIP。未重做界面或改变业务流程。最后源码回归为 55 passed in 3.88s，原始输出见 evidence/final-pytest.txt。
