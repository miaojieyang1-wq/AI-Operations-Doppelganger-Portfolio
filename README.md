# AI 运营分身作品集

这是一个面向游戏运营场景的 AI 作品集与工作流 Demo。项目把个人经历、作品集文档、AI 工作流和运营分析工具整合到一个可交互的网站中，让查看者可以通过对话、看板和分析模块了解作品能力。

## 核心能力

- 模拟面试：通过 AI 运营分身了解经历、作品集、项目方法论和游戏理解。
- 作品集展示：集中展示 SEO Prompt 工程、AI 运营分身 Agent、帕姆帮帮黑箱测试方案、星铁战术引擎、线下活动经历等内容。
- 版本决策：支持版本公告分析、竞品雷达和多职能协作讨论。
- 用户洞察：支持访谈助手、问卷工坊和反馈清洗。
- 活动策划：生成活动方案、风险预判、宣发节奏和后续追踪建议。
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

## 快速开始

### 1. 安装依赖

建议使用 Python 3.10 或以上版本。

```bash
python -m pip install -r requirements.txt
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，并填写你的 DeepSeek API Key。

```bash
DEEPSEEK_API_KEY=sk-your-key
```

如果没有 API Key，也可以进入演示模式。

### 3. 构建知识库索引

```bash
python build_index.py
```

脚本会读取 `works/` 文件夹下的作品集文档，并构建本地索引。

### 4. 启动应用

```bash
streamlit run app.py
```

也可以运行：

```bash
python install.py
```

使用安装向导完成环境检查、配置和启动。

## 目录说明

- `app.py`：Streamlit 前端入口。
- `agent_graph.py`：LangGraph 流程编排。
- `core.py`：核心业务编排层。
- `rag_engine.py`：本地知识库检索。
- `build_index.py`：知识库索引构建脚本。
- `config/`：配置中心，包含提示词、角色配置和 UI 配置。
- `works/`：作品集文档与项目材料。
- `static/`：图片等静态资源。
- `reports/`：本地生成报告目录，默认不上传 GitHub。

## 数据与隐私

请不要上传 `.env`、真实 API Key、个人运行缓存、本地数据库、生成报告和本地索引。项目中的 `.gitignore` 已默认排除这些内容。

## 自检

首次运行前，建议先检查环境：

```bash
python check_env.py
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
