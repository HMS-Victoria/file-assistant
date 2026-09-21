# 文件小助手（file-assistant）

> 让长辈一句话安全处理本机 Office 文件

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-%E6%9C%AA%E5%A3%B0%E6%98%8E-lightgrey)](#背景说明)

一个面向 Windows 10/11 的 PySide6 桌面小工具：把 `.docx`、`.xlsx`、`.pdf` 拖进窗口，用一句日常中文说清想做什么，程序就会去办。

**Windows 测试版 0.1.0-rc1**：[前往 GitHub Release 下载完整 ZIP](https://github.com/HMS-Victoria/file-assistant/releases/tag/v0.1.0-rc1)。完整解压后双击 `FileAssistant/文件小助手.exe`，保留 `_internal` 文件夹。已通过本地自动化与独立解压验证；无 Python 的新电脑及本人密钥实际验收仍待完成。见 [使用说明](docs/便携版使用说明.md) 和 [测试清单](docs/release-readiness/2026-09-20/NEW_PC_ACCEPTANCE.md)。

**这个项目最核心的设计不是"AI 能做什么"，而是"AI 被严格限制成不能做什么"。**

DeepSeek 只负责把自然语言翻译成一份 JSON **操作计划**；这份计划必须通过本地白名单与 Pydantic Schema 双重校验才能执行；执行层永远只生成**新文件**，原文件在代码层面就不可能被覆盖。

## 项目亮点

- **AI 只能"提名"，不能"动手"**。`app/ai/intent_parser.py` 里的 `IntentParser` 类注释写得很直白：*"AI 仅负责理解；本类不访问、更不修改用户文件。"* 它拿到的是 JSON 字符串，交出去的是校验过的 `OperationPlan` 对象，仅此而已。所有文件读写都发生在另一个进程内的本地服务里。
- **13 个操作的白名单 + 三重拒绝机制**。`app/operations/schemas.py` 用 Pydantic 判别联合（`Field(discriminator="action")`）定义唯一允许的动作集合，并叠加三层防护：① `extra="forbid"` 拒绝任何计划外字段；② `Literal[...]` 判别器拒绝任何白名单外的 action；③ `Field` 约束逐参数限界——查找词 ≤500 字、问题 ≤1000 字、Excel 单元格必须匹配 `^[A-Za-z]{1,3}[1-9][0-9]*$`、行号 `1..1_000_000`、列号 `1..16_384`、单次计划最多 20 个操作。系统提示词（`app/ai/prompts.py`）另外明确禁止模型生成 Python / Shell / SQL / 公式 / HTML **或任何可执行代码**。
- **"永不覆盖原文件"是代码级不变量，而不是一句承诺**。`SafeModificationService._new_output_path()` 自动派生 `原名_AI修改.docx`，若已存在则依次尝试 `_AI修改_2`、`_AI修改_3`……；`ModificationService.apply()` 在执行第一步就断言 `source != output` 且 `output` 不存在，否则直接抛错；保存走同目录 `NamedTemporaryFile` 再 `replace()` 的原子流程，任何异常都会把半成品 `unlink` 掉。
- **先备份、再生成、后复验**。修改前把原文件 `copy2` 到应用内部 `.file_assistant_backups/`，并**逐字节比对**确认备份完整（不完整就删掉备份并报错）；新文件写完后重新打开读取一次，验证类型一致、非空、可正常解析。备份还能"恢复为另一个新文件"——恢复路径同样禁止覆盖任何已存在的文件。
- **预览确认，删除类操作加倍提醒**。任何修改都先弹出中文逐条预览（"将"A"替换为"B""、"删除"账"这一列的第 3 列"），用户点"确认修改"才继续；`delete_text` / `delete_row` / `delete_column` 会被标记为危险操作，在确认框里额外追加一行"**注意：这项操作会删除内容。**"
- **能本地算的绝不出网**。查找文字、Excel 求和 / 平均值 / 最大值 / 最小值 / 按条件筛选，全部由 `openpyxl` 在本机完成，**一次网络请求都不发**。只有"总结"和"问答"才调用 AI，且单次最多发送 12,000 字符的必要正文，`build_user_prompt()` 只携带文件类型与用户原话，**不含本机路径、不含文件名**。
- **密钥加密保存**。设置窗口中的密钥输入为遮挡模式；`DeepSeekSettings` 使用 Windows 当前用户 DPAPI，加密后写入 `%LOCALAPPDATA%/FileAssistant/settings.json`。界面错误只展示中文操作提示，不回显密钥或原始堆栈；不再自动搜索 `.env`。
- **有真测试、有真样例**。8 个 pytest 测试文件覆盖意图解析、查询服务、修改服务、安全修改服务、错误路径与处理器；`tests/sample_files/` 里有三份**真实可解析的中文样例文件**（`会议通知.docx`、`报销表.xlsx`、`报销通知.pdf`）。

## 技术栈

- **语言**：Python 3.12
- **界面**：PySide6（Qt6），单窗口 + 拖放区，微软雅黑，大字号大按钮（面向不熟悉电脑的使用者）
- **数据校验**：pydantic v2（`TypeAdapter` + 判别联合 + `Literal` 白名单）
- **AI 服务**：DeepSeek Chat Completions API（`response_format: json_object`，`temperature=0`），HTTP 客户端用 `httpx`
- **配置**：固定用户目录 + Windows DPAPI（标准库调用）
- **文件处理**：`python-docx`（Word 段落与表格）、`openpyxl`（Excel 工作表与单元格）、`PyMuPDF`（PDF 页数与文字）
- **测试**：`pytest`

## 系统架构

```text
┌─ 界面层 app/ui/ ────────────────────────────────────────────────────────┐
│  MainWindow（单窗口）                                                    │
│   · DropArea 拖入 .docx/.xlsx/.pdf，只校验后缀与存在性，不读内容         │
│   · QLineEdit 单行输入"你想让我做什么？"                                 │
│   · handle_start()：唯一的编排入口                                       │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─ 意图层 app/ai/（唯一联网的地方）──────────────────────────────────────┐
│  IntentParser.parse(用户原话, 文件类型)                                  │
│     │                                                                    │
│     ├─ prompts.build_user_prompt()                                       │
│     │    只输出「文件类型 + 用户要求」，不含路径、不含文件名              │
│     │                                                                    │
│     ├─ DeepSeekClient.create_json_completion()                           │
│     │    POST /chat/completions                                          │
│     │    response_format={"type":"json_object"}  temperature=0           │
│     │    Authorization: Bearer <内存中的密钥，从不记录>                  │
│     │                                                                    │
│     └─ validate_operation_plan(响应字符串)                               │
│           Pydantic 判别联合校验                                          │
│           ✗ 未知 action      → 拒绝                                      │
│           ✗ 计划外字段       → 拒绝                                      │
│           ✗ 参数超限/格式错  → 拒绝                                      │
│                     │                                                    │
│                     ▼  校验通过，得到 OperationPlan（13 种动作之一）      │
└─────────────────────┼──────────────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │ 按动作分流                │
        ▼                           ▼
┌─ 只读查询 ────────────┐   ┌─ 修改流程 ───────────────────────────────┐
│ QueryService          │   │ SafeModificationService                  │
│ · 前置断言：动作必须  │   │ ① prepare()：校验后缀 ∈ {docx,xlsx}、    │
│   全在 READ_ONLY_     │   │    动作全在 MODIFICATION_ACTIONS、       │
│   ACTIONS 内，否则    │   │    派生不冲突的新文件名、生成中文预览、  │
│   抛 QueryError       │   │    标记是否为危险操作                    │
│ · 一次只允许 1 个动作 │   │              │                           │
│ · 全程只在内存中读    │   │              ▼ 界面弹窗让用户确认         │
│   文件，从不保存      │   │ ② execute()：                            │
│                       │   │    · 断言 output 不存在且 ≠ source       │
│ ┌ 本机计算（零网络）┐ │   │    · copy2 备份 + 逐字节比对验证         │
│ │ find_text         │ │   │    · ModificationService.apply()         │
│ │ calculate_sum/avg │ │   │        Word：替换/增加/删除文字          │
│ │   /max/min        │ │   │        Excel：改单元格、增删行/列        │
│ │ filter_rows       │ │   │        写临时文件 → replace() 原子就位   │
│ └───────────────────┘ │   │    · 重新打开新文件复验：类型一致、      │
│ ┌ AI 回答（联网）  ┐ │   │      非空、可解析                        │
│ │ summarize         │ │   │    · 任何异常 → unlink 半成品 + 抛错     │
│ │ question_answer   │ │   │ ③ 返回新文件路径 + 内部备份路径          │
│ │ 上限 12000 字符   │ │   └──────────────────────────────────────────┘
│ └───────────────────┘ │
└───────────────────────┘
                      │
                      ▼
┌─ 处理器层 app/processors/ ──────────────────────────────────────────────┐
│  factory.get_processor(path) → 按后缀分派                                │
│   WordProcessor（python-docx）：段落 + 表格                              │
│   ExcelProcessor（openpyxl）：多工作表 + 单元格值                        │
│   PdfProcessor（PyMuPDF）：页数与文字                                    │
│  统一返回 FileReadResult / WorksheetData，查询与修改服务都只面向这个抽象 │
└──────────────────────────────────────────────────────────────────────────┘
```

**模块职责**

| 模块 | 职责 |
|---|---|
| `app/ui/main_window.py` | 唯一编排入口：解析意图 → 判断只读还是修改 → 修改则先预览确认 → 分派到对应服务 |
| `app/ui/drop_area.py` | 拖放区，只校验后缀与文件存在性 |
| `app/operations/schemas.py` | **安全边界的第一道闸门**：13 种操作的 Pydantic 定义与 `validate_operation_plan()` |
| `app/ai/prompts.py` | 受限系统提示词与最小化用户提示（不带路径） |
| `app/ai/deepseek_client.py` | DeepSeek 最小客户端，只请求 JSON 对象或纯文本，异常统一转成安全错误 |
| `app/ai/intent_parser.py` | 自然语言 → 已验证 `OperationPlan`；不接触文件 |
| `app/config/settings.py` | 固定当前用户配置目录，Windows DPAPI 加密保存密钥 |
| `app/processors/factory.py` | 按后缀分派处理器 |
| `app/processors/base_processor.py` | 统一的读取结果数据结构 |
| `app/services/query_service.py` | 只读查询：本机查找与统计零网络，总结/问答走 AI 且限 12,000 字符 |
| `app/services/modification_service.py` | 受限副本修改，禁止覆盖，临时文件 + 原子替换 |
| `app/services/safe_modification_service.py` | **安全工作流**：预览、备份、命名、保存后复验、从备份恢复 |

更详细的安全模型分析见 [`docs/safety.md`](docs/safety.md)。

## 目录结构

```text
文件处理助手/
├── app/
│   ├── main.py                    # 程序入口：创建 QApplication 与主窗口
│   ├── ai/
│   │   ├── prompts.py             # 受限系统提示词 + 最小化用户提示
│   │   ├── deepseek_client.py     # DeepSeek JSON/文本补全客户端
│   │   └── intent_parser.py       # 自然语言 → 已验证操作计划
│   ├── config/
│   │   └── settings.py            # DeepSeekSettings.from_environment()
│   ├── operations/
│   │   └── schemas.py             # 13 种操作的白名单 + 计划校验入口
│   ├── processors/
│   │   ├── base_processor.py      # FileReadResult / WorksheetData
│   │   ├── factory.py             # 按后缀分派
│   │   ├── word_processor.py      # python-docx 读段落与表格
│   │   ├── excel_processor.py     # openpyxl 读工作表与单元格
│   │   └── pdf_processor.py       # PyMuPDF 读页数与文字
│   ├── services/
│   │   ├── query_service.py           # 只读查询（本机统计 + AI 问答）
│   │   ├── modification_service.py    # 受限副本修改（原子保存）
│   │   └── safe_modification_service.py  # 预览 / 备份 / 命名 / 复验 / 恢复
│   └── ui/
│       ├── main_window.py         # 主窗口与流程编排
│       └── drop_area.py           # 拖放区
├── tests/
│   ├── test_ai_intent_parser.py          # 非法计划一律被拒
│   ├── test_query_service.py             # 查询服务
│   ├── test_query_errors.py              # 查询错误路径
│   ├── test_modification_service.py      # 修改服务
│   ├── test_safe_modification_service.py # 备份 / 命名 / 复验 / 恢复
│   ├── test_processors.py                # 三种处理器
│   ├── test_milestone_1.py               # 界面层基础行为
│   ├── create_sample_files.py            # 生成样例文件
│   └── sample_files/                     # 中文名样例：会议通知.docx / 报销表.xlsx / 报销通知.pdf
├── docs/
│   ├── safety.md                  # 安全模型详解
│   └── images/                    # 截图目录（待补充）
├── .env.example                   # 环境变量模板（密钥留空）
├── requirements.txt
├── README.md
└── .gitignore
```

> `.venv/`、`.env`、`.file_assistant_backups/`、`__pycache__/`、`.pytest_cache/` 均被 `.gitignore` 排除。
> **仓库中不含任何 API 密钥**——只提交密钥留空的 `.env.example`。

## 运行方法

### 1. 创建虚拟环境并安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. 配置 AI 服务（可选）

选择窗口内明确标为“无需联网”的查找、Excel 统计或筛选功能时**不需要配置**。
需要自然语言理解、总结、问答或 AI 修改计划时，打开“设置”，填入自己的 DeepSeek 密钥与模型，测试连接后保存。
配置固定保存在 `%LOCALAPPDATA%/FileAssistant/settings.json`，密钥为 Windows 当前用户 DPAPI 密文。
旧 `.env` 保留在本机但不再读取；升级后请在设置中重新填写。桌面版使用官方 DeepSeek 服务地址。

### 3. 启动

```powershell
.\.venv\Scripts\python.exe -m app.main
```

### 4. 使用

1. 把 `.docx` / `.xlsx` / `.pdf` 拖进窗口。
2. 选择处理方式：
   - 本地查找：输入 `报销`，全程无需联网。
   - Excel 求和：填写列名 `金额`，全程无需联网。
   - AI 帮我处理：输入 `帮我总结一下这份文件` 或 `把张三替换成李四`；自然语言理解需要联网，修改会先预览确认。
3. 点"开始处理"。若是修改类操作，会先显示具体变更清单，确认后才生成 `原名_AI修改.docx`。

### 5. 运行测试

```powershell
.\.venv\Scripts\python.exe -m pytest
```

### 截图

界面截图请放在 [`docs/images/`](docs/images/)，该目录下的 README 列出了建议补充的截图清单。

### 构建 Windows x64 便携包

在 Windows x64 / Python 3.12 下执行唯一构建入口：

```powershell
python scripts/build_portable.py
```

脚本使用仓库内独立的 `.build-venv`，按 `requirements-build.lock` 安装固定版本，不改全局 PATH。
输出到 `release/0.1.0-rc1-时间戳/`：完整 onedir ZIP、对应源码 ZIP、SHA256SUMS、逐文件源码哈希及构建记录。
完整 ZIP 包含 Python、Qt 平台插件和文档处理运行库。构建记录不默认打入用户包。
开发者可运行 `文件小助手.exe --self-test <全新目录>`，在指定目录生成合成文档、独立用户配置和结果记录；此命令不能代替新电脑人工验收。

## 已知限制

诚实列出当前的真实边界（项目自述完成到 Milestone 6，以下是尚未覆盖的部分）：

- **只有 Word 和 Excel 能被修改**。PDF 是**只读**的，只能查找文字、看页数、做总结问答。`SafeModificationService.prepare()` 会拒绝 `.pdf` 的修改请求。
- **查询一次只能提一个要求**。`QueryService.execute()` 里 `if len(plan.operations) != 1: raise QueryError`——想同时问两件事得分两次问。
- **段落级格式会被重置**。`_replace_in_paragraphs()` 用的是 `paragraph.text = paragraph.text.replace(...)` 整体赋值，Python-docx 在这种赋值下会把该段落**压平成单一 run**，段落内的加粗、字号、颜色、局部字体等 run 级格式会丢失。修改后的文件内容是对的，但排版可能需要手工恢复。
- **备份名是固定的，同一文件不能反复改两次同名输出**。备份文件名由 `{输出文件名}_原文件备份{后缀}` 决定，若该备份已存在会直接抛 `SafetyError`。想再改一次需要先手工整理 `.file_assistant_backups/`。
- **Excel 列名自动识别有前提**。不带列名时，只有"恰好一列是数值列"才能自动定位；有多个数值列时会提示用户明确指定列名，而不是猜。
- **便携包尚待新电脑验收**。现有 PyInstaller onedir 构建入口与完整 ZIP 候选；没有安装向导或代码签名，尚不能称为已完成全部“下载即用”验收。
- **依赖云端 AI**。总结与问答需要联网调用 DeepSeek，没有离线模型方案；网络不可用时这两个功能整体失败（会给出中文提示，不会崩溃）。
- **扫描版 PDF 读不到文字**。`PyMuPDF` 提取的是 PDF 内嵌文本层，**没有 OCR**，图片型 PDF 会返回空内容并提示"这个文件里没有可读取的文字"。
- **12,000 字符是硬截断**。`MAX_AI_CONTENT_CHARS = 12_000` 处直接切片，超长文档的总结只覆盖前 12,000 字符，后半部分会被静默丢弃。
- **没有多文件批处理和撤销栈**。一次只能处理一个文件；唯一的"回退"方式是从 `.file_assistant_backups/` 恢复，而且恢复出来的是**另一个新文件**，不会覆盖当前文件。
- **文字替换会穿透到表格单元格**。`_word_paragraphs()` 会把文档正文与所有表格单元格的段落合并处理，因此 `把"张三"替换成"李四"` 也会改到表格里的"张三"——设计上是有意为之，但用户未必预期。
- **输入框是单行**。面向易用性选了 `QLineEdit`，长要求写起来不方便。

## 背景说明

### 设计出发点

这个工具的目标用户是**不熟悉电脑的长辈**。设置和错误提示使用中文，并给出可自行操作的下一步。

因此本项目的取舍非常明确：**宁可功能少，也不能让 AI 有破坏用户文件的机会**。它能做的事被压缩到 13 个可枚举的动作，而每一个动作的参数区间都被 Schema 钉死。

### 数据隐私处理方式

1. **本地优先**。查找文字、Excel 统计与筛选 100% 在本机由 `openpyxl` / `python-docx` 完成，不产生任何网络请求。
2. **不泄露路径**。发给 AI 的提示词只包含"文件类型（word/excel/pdf）+ 用户原话"，**不含本机路径、不含文件名**（见 `build_user_prompt()`）。
3. **最小化外发内容**。需要 AI 时只发送完成任务所必需的正文，上限 12,000 字符。
4. **密钥加密保存**。`DeepSeekSettings` 将密钥用 Windows DPAPI 加密后保存在固定当前用户目录；界面使用遮挡输入及不含密钥的错误提示。
5. **本仓库不含密钥**。`.env` 已被 `.gitignore` 排除，仓库中只有密钥留空的 `.env.example`。
6. **原文件不离开本机、不被覆盖**。所有修改都是"读原文件 → 在内存中改 → 写入新文件"，原文件与内部备份都留在用户自己的磁盘上。

### 第三方组件与来源

| 组件 | 用途 | 许可 |
|---|---|---|
| PySide6（Qt for Python） | 桌面界面 | LGPLv3 / 商业双许可 |
| python-docx | 读写 `.docx` | MIT |
| openpyxl | 读写 `.xlsx` | MIT |
| PyMuPDF | 读取 PDF | AGPLv3 / 商业双许可 |
| pydantic | 操作计划 Schema 校验 | MIT |
| httpx | HTTP 客户端 | BSD-3-Clause |
| DeepSeek API | 自然语言 → 操作计划、总结与问答 | 商业服务，遵循其服务条款 |
| pytest | 测试 | MIT |

> ⚠️ 注意：**PyMuPDF 采用 AGPLv3**。若你打算把本项目用于分发或商业用途，需要先确认 AGPLv3 的合规要求，或替换为许可更宽松的 PDF 解析方案。

### 用途与合规声明

本项目是个人技术学习项目，用于探索"如何让大模型在高风险操作（文件修改）中只做它能安全做的事"。使用时请自行遵守 DeepSeek 的服务条款及所在地区法律法规。

### 本项目不含 LICENSE

本仓库暂未声明开源许可证。如需转载或复用其中的代码，请先联系作者。
