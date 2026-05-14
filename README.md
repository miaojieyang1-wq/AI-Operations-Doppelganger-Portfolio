# AI运营分身

这是一个面向游戏运营场景的 AI 作品集与工作流 Demo。项目包含 Streamlit 前端、本地知识库索引、LangGraph 流程编排、多职能协作讨论、演示模式、FastAPI 后端预留和数据库接口预留。

## 快速开始

### 1. 运行安装向导

在项目根目录运行：

```bash
python install.py
```

安装向导会依次完成环境检查、依赖安装、DeepSeek API Key 配置、知识库索引构建、桌面启动器创建和应用启动。

如果只是想先体验页面，也可以在首次配置页面选择“跳过配置，进入演示模式”。演示模式会读取本地预设结果，不需要实时调用 API。

### 2. 直接启动应用

安装完成后，可以运行桌面上的启动脚本：

- Windows：`AI运营分身-run.bat`
- Mac/Linux：`AI运营分身-run.sh`

也可以在项目根目录手动运行：

```bash
streamlit run app.py
```

### 3. 重新配置

如果需要重新配置 API Key，可以删除项目根目录下的 `.env` 文件，然后重新运行：

```bash
python install.py
```

如果只是想更新知识库索引，可以运行：

```bash
python build_index.py
```

### 4. 自检项目

在发给别人或打包前，建议运行：

```bash
python health_check.py
```

自检会检查 Python 语法、提示词配置、文本编码、核心模块和首页入口。文本编码检查可以拦截常见中文乱码，避免提示词或安装说明被错误编码写坏。

## 配置说明

运行时配置以 `config/` 文件夹下的 YAML 文件为准。旧版 txt 提示词文件只作为历史存档，不再作为运行时数据源。

常见配置位置：

- `config/app.yaml`：应用名称、模型参数、路径、管理后台密码
- `config/agents/*.yaml`：多职能协作讨论中的运营角色配置
- `config/prompts/tasks/*.yaml`：访谈、问卷、反馈清洗、竞品分析、活动策划等任务提示词
- `config/prompts/modules/*.yaml`：关于我、作品集、自我诊断等模块提示词

## 数据与隐私

- `.env` 中保存本地 API Key，请不要公开分享。
- `reports/`、`activity_plans/`、`local_demo.db` 属于本地生成数据，打包发给他人前建议删除。
- 本地知识库索引默认保存在 `chroma_db/` 目录中，当前实现是本地轻量索引，不依赖外部 Embedding API。

## API 后端

如果需要测试 FastAPI 后端，可运行：

```bash
uvicorn api:app --reload
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

聊天接口示例：

```bash
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"user_input\":\"请介绍你的作品集\",\"session_id\":\"demo\"}"
```

## 分发与数据安全说明

当前包是“源代码分发版”，不是内置 Python 的完全独立运行包。使用前请先安装 Python 3.10 或更高版本，然后运行：

```powershell
python install.py
```

也可以安装依赖后直接启动：

```powershell
python -m streamlit run app.py
```

### 用户数据目录

运行时产生的数据不会再写入安装目录。默认位置为：

- Windows：`%LocalAppData%/AI_Ops_Agent`
- macOS：`~/Library/Application Support/AI_Ops_Agent`
- Linux：`~/.local/share/AI_Ops_Agent`

其中会保存 `.env`、后台密码哈希、数据库、报告、JSON 附加文件、知识库索引和缓存。可以通过环境变量 `AI_OPS_DATA_DIR` 覆盖这个位置。

### 后台密码

项目不再提供公开默认后台密码。首次进入管理后台或运行安装向导时，必须设置后台密码。密码只保存带盐哈希，不会明文写入 `config/app.yaml`。

### 本地保存策略

聊天和分析结果默认只展示在页面中，不会自动保存到本地。只有用户点击“保存”或“导出”按钮时，才会写入用户数据目录。

可选开关：

- `AI_OPS_ENABLE_LOCAL_SAVE=0`：彻底关闭本地报告保存。
- `AI_OPS_SAVE_JSON_SIDECAR=0`：保存 Markdown 时不额外生成 JSON 附加文件。

### FastAPI 安全边界

API 默认建议只监听 `127.0.0.1`。如需保护接口，请设置：

```powershell
$env:AI_OPS_API_TOKEN="your-token"
```

之后业务接口必须携带：`Authorization: Bearer your-token`。

API 默认不写数据库。只有同时满足以下两个条件才会持久化：

1. 环境变量 `AI_OPS_API_PERSISTENCE=1`
2. 请求体传入 `"persist": true`

数据库默认位于用户数据目录，不建议写入安装目录。
