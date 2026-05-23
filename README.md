# AI 运营分身作品集

这是一个面向游戏运营场景的 AI 作品集与工作流 Demo。项目把个人经历、作品集文档、AI 工作流和运营分析工具整合到一个可交互的网站中，让查看者可以通过对话、看板和分析模块了解作品能力。

## 外部参考与来源声明

本项目中的「星铁战术引擎」是作品集中的系统设计原型与技术蓝图，当前未集成下列外部项目，也不包含其代码或文件。相关工具仅作为设计背景、能力边界和灵感来源进行引用：

- 伤害即时引擎参考：[hessiser/veritas](https://github.com/hessiser/veritas/wiki#1-install-the-loader)。该项目提供《崩坏：星穹铁道》相关的实时数据/覆盖层分析能力；本作品集仅引用其作为“即时伤害/战斗数据读取类工具”的外部参考来源。
- 穷举排轴模拟器来源：[夸克网盘资料](https://pan.quark.cn/s/c62926dcbea7)，作者来自 Bilibili：命途行者 fateholder。本作品集仅引用其作为“穷举排轴/行动序列模拟器”的外部参考来源。

如需真实接入此类外部工具，应另行确认其许可协议、使用风险、游戏服务条款、数据来源合规性和版本兼容性。

## 核心能力

- 模拟面试：通过 AI 运营分身了解经历、作品集、项目方法论和游戏理解。
- 作品集展示：集中展示 SEO Prompt 工程、AI 运营分身 Agent、知识治理控制台、帕姆帮帮黑箱测试方案、星铁战术引擎、线下活动经历等内容。
- 外部项目入口：知识治理控制台与星铁战术引擎已整理为独立 GitHub 仓库，作品集页面会提供明显按钮引导查看。
- 版本决策：支持版本公告分析、竞品雷达和多职能协作讨论。
- 用户洞察：支持访谈助手、问卷工坊和反馈清洗。
- 活动策划：生成活动方案、风险预判、宣发节奏和后续追踪建议。
- 自然语言编排：用户可以用自然语言描述运营目标，系统自动生成调用链；常见流程会优先走本地快速规划，规划失败时自动回退到可执行默认流程，多步骤依赖会自动压缩上下文以控制等待时间。
- 本地知识库：使用本地索引检索 works/ 文件夹中的作品集文档。
- 演示模式：无 API Key 时也可使用本地预设结果进行演示。

## 技术栈

- Python
- Streamlit
- LangGraph
- LangChain
- ChromaDB / 本地轻量检索方案
- DeepSeek API
- YAML 配置中心
- FastAPI 预留接口
- matplotlib

## Windows 运行指引

以下步骤适用于首次在新设备上运行本项目。流程尽量以图形界面和复制命令为主
### 1. 下载并解压项目

1. 打开本仓库页面。
2. 点击绿色按钮 `Code`。
3. 选择 `Download ZIP`。
4. 下载完成后，右键压缩包，选择 `全部解压缩`。
5. 进入解压后的项目文件夹。

请确认当前打开的是项目根目录。该目录中应能看到以下文件或文件夹：

- `app.py`
- `check_env.ps1`
- `requirements.txt`
- `build_index.py`
- `.env.example`
- `works`

如果当前只看到一个同名文件夹，请继续进入下一层，直到能看到上述文件。

### 2. 安装 Python

本项目需要 Python 3.10 或以上版本。

1. 打开 [python.org/downloads](https://www.python.org/downloads/)。
2. 下载最新版 Python。
3. 安装时请务必勾选 `Add python.exe to PATH`。
4. 安装完成后，关闭并重新打开命令窗口。

如需确认 Python 是否安装成功，可在项目文件夹的地址栏输入 `powershell` 并回车，然后运行：

```powershell
python --version
```

若显示 `Python 3.10`、`Python 3.11`、`Python 3.12` 或更高版本，则说明版本符合要求。

### 3. 运行 `check_env.ps1` 一键检查并修复环境

在项目文件夹中，按住 `Shift` 并右键空白处，选择 `在终端中打开` 或 `在 PowerShell 中打开`。

请确认项目文件夹中存在 `check_env.ps1` 文件。复制以下命令并回车执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\check_env.ps1
```

该脚本会自动检查并尽可能修复以下内容：

- Python 版本
- Visual C++ 运行时
- Python 依赖包
- `.env`、`works`、索引目录等关键文件
- 本地嵌入模型是否可加载

如果脚本提示 Visual C++ 运行时缺失，请下载并安装：

[vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe)

这个组件缺失时，`onnxruntime`、`chromadb` 或默认嵌入模型可能在新设备上加载失败。

### 4. 配置 API Key

如需使用实时 AI 生成能力，请配置 DeepSeek API Key。

如暂时没有 API Key，也可以使用网页中的“演示模式”。演示模式会读取本地预设结果，不会实时调用 AI 服务。

### 5. 构建知识库索引

知识库索引用于检索 `works` 文件夹中的作品集文档。首次在新设备运行时，需要重新构建索引。

在 PowerShell 中运行：

```powershell
python build_index.py
```

构建完成后，可运行以下诊断命令确认索引是否可用：

```powershell
python diagnose_index.py
```

若看到 `Index looks available on this device.`，说明当前设备的知识库索引已可用。

索引默认保存在当前设备的用户数据目录，不会随 GitHub 仓库一起迁移。更详细的迁移说明见 `KNOWLEDGE_INDEX_MIGRATION.md`。

本项目已修复跨设备迁移时的一个常见问题：新设备如果只有空的 `chroma_db` 文件夹，不会再被误判为“已有旧索引”并卡在交互确认。

### 6. 启动应用

完成环境检查和索引构建后，在 PowerShell 中运行：

```powershell
streamlit run app.py
```

正常情况下，浏览器会自动打开本地网页。如未自动打开，请复制终端中显示的 `http://localhost:xxxx` 地址到浏览器访问。

也可以在项目文件夹中双击以下文件启动：

```text
start_app.bat
```

如果双击后提示缺少依赖，请先返回第 3 步运行 `check_env.ps1`。

也可以运行安装向导：

```powershell
python install.py
```

### 7. 下次再打开

后续在同一台设备上运行时，通常只需要执行：

```powershell
streamlit run app.py
```

只有在换电脑、重新下载项目、更新 `works` 文档，或页面提示知识库不可用时，才需要重新运行：

```powershell
python build_index.py
```

## 目录说明

- `app.py`：Streamlit 前端入口。
- `agent_graph.py`：LangGraph 流程编排。
- `core.py`：核心业务编排层。
- `rag_engine.py`：本地知识库检索。
- `build_index.py`：知识库索引构建脚本。
- `diagnose_index.py`：知识库索引迁移诊断脚本。
- `check_env.ps1`：Windows 一键环境检查与自动修复脚本。
- `KNOWLEDGE_INDEX_MIGRATION.md`：跨设备迁移知识库索引的说明。
- `config/`：配置中心，包含提示词、角色配置和 UI 配置。
- `works/`：作品集文档与项目材料。
- `static/`：图片等静态资源。
- `reports/`：本地生成报告目录，默认不上传 GitHub。

## 数据与隐私

请不要上传 `.env`、个人运行缓存、本地数据库、生成报告和本地索引。项目中的 `.gitignore` 已默认排除这些内容。

注意：演示模式会读取本地预设结果，不会使用 RAG 检索结果。验证知识库索引效果时，请关闭演示模式并连接可用 API。

## 自检

Windows 新设备首次运行前，建议先执行完整环境检查与自动修复：

```powershell
powershell -ExecutionPolicy Bypass -File .\check_env.ps1
```

也可以运行 Python 版基础环境检查：

```bash
python check_env.py
```

如果只想确认知识库索引是否已经在当前设备上可用：

```bash
python diagnose_index.py
```

每次修改后，可以先跑冒烟测试：

```bash
python smoke_test.py
```

上传或交付前建议运行完整自检：

```bash
python health_check.py
```

完整自检会检查语法、提示词配置、文本编码、核心模块和首页入口。

## 说明

这个项目定位为个人作品集 Demo 和 AI 运营工作流原型，不等同于生产环境系统。涉及竞品、市场、用户反馈和活动方案的分析均基于用户输入与 AI 推理，关键决策前应与官方数据、真实用户反馈或业务数据交叉验证。
