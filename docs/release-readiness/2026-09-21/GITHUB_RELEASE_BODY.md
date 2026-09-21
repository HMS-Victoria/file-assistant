这是供真实电脑验收的 Windows x64 **预发布测试版**，尚未宣称完成新电脑及本人密钥的全部验收。

## 下载与运行

下载下面 Assets 中的 **FileAssistant-0.1.0-rc1-windows-x64.zip**，完整解压后双击 **FileAssistant/文件小助手.exe**。
请保留 `_internal` 文件夹；无需自行安装 Python 或 Office。
`source.zip` 和 GitHub 自动生成的 Source code 供开发者使用，普通测试者请选择 `windows-x64.zip`。

适用：Windows 10（1809 或更新版本）/11，x64。

## 请优先测试

1. 不填密钥，拖入自己创建的 Word、Excel、PDF 样例，完成一次本地文字查找和 Excel 求和。
2. 点击“设置”，自行填写本人的 DeepSeek 密钥及模型，测试连接并保存。请不要在问题反馈或截图中暴露密钥。
3. 请求一次 AI 修改计划，先检查预览并取消，确认没有产生新文件；再确认一次修改。
4. 检查原文件保持不变，新文件可以打开；测试中文/空格目录及无法写入的目录提示。

请反馈 Windows 版本、出错步骤、截图和具体提示。PDF 只读，没有 OCR；Word 替换可能改变段内格式。AI 处理期间主窗口可能短暂无响应。程序尚未签名。

## 已做的验证

55 项源码自动测试通过；完整 ZIP 独立解压后的程序自检通过，包括无密钥查找/统计、DOCX/XLSX 备份与另存、重开、恢复、三类原件哈希不变，以及 Windows DPAPI 加密。
开发机隔离验证不能代替无 Python 的新电脑人工测试。本人真实密钥下的 AI 预览仍待测试。

## 文件校验与来源

`SHA256SUMS` 提供程序 ZIP 和准确源码快照 ZIP 的 SHA-256。第三方许可说明随程序包提供。项目尚未声明自身许可证，第三方组件按各自许可使用。

源码提交：`abff6dac6fd1129fb1721f09ca64a273b6981d89`。

```text
4b1a54a40ac037c7a3b9b3a008458e0098ccbee14677c9c9482d4539d66ce6ba  FileAssistant-0.1.0-rc1-windows-x64.zip
72e40c63cbbd2fec929428c00da50628321ccf61a2c5d4435d989574d033ae1a  FileAssistant-0.1.0-rc1-source.zip
```
