# Knowledge Governance Console 知识治理控制台

项目仓库：[Knowledge-Governance-Console](https://github.com/miaojieyang1-wq/Knowledge-Governance-Console)

本地项目文件夹：`works/knowledge_governance_console/`

这份文档用于说明“知识治理控制台”作为作品集项目时的定位、功能、当前公开仓库结构和能力证明。当前 GitHub 仓库版本是一个独立 Streamlit 工具，只读写本地 JSON 文件，不依赖也不嵌入 AI 运营分身 Agent 代码。

## 项目定位

知识治理控制台用于注册、审计、追溯和回流知识库质量问题。它解决的是 Agent 或知识库项目长期维护中的一个基础问题：当知识不断增加、回答出现错误、规则需要修正时，需要有一个可视化入口记录知识单元、责任归属和 Badcase，而不是只靠手工改文档。

这个项目不是聊天 Agent，而是一个本地知识治理后台。它将知识库内容和 Badcase 分别保存到本地 JSON 文件中，便于在个人演示或轻量项目中快速运行、快速检查和快速修正。

## 当前公开仓库结构

当前仓库包含：

- `app.py`：Streamlit 前端入口，承载知识注册、仪表盘、清单筛选、责任追溯和 Badcase 看板。
- `utils.py`：本地 JSON 文件读写、知识 ID 生成和数据持久化工具。
- `config.yaml`：数据目录、知识库文件名、Badcase 文件名配置。
- `requirements.txt`：当前只依赖 `streamlit==1.56.0`。
- `data/knowledge_base.json`：本地知识库数据文件。
- `data/badcase_log.json`：Badcase 记录文件。

默认数据文件：

- `data/knowledge_base.json`
- `data/badcase_log.json`

## 核心功能

1. 知识单元注册中心：录入和维护结构化知识。
2. 知识库健康度仪表盘：查看知识库基础状态。
3. 知识清单筛选：按字段查看和筛选知识单元。
4. 责任归属与错误追溯工作台：保留来源、负责人、审核等治理线索。
5. Badcase 回流与审核看板：将错误案例记录下来，转化为后续修正依据。

## 与 AI 运营分身 Agent 的关系

AI 运营分身 Agent 解决的是“如何把作品集和运营工作流做成可交互系统”的问题；知识治理控制台解决的是“当知识库持续增加和修正时，如何治理知识质量”的问题。

当前公开仓库版本保持轻量：控制台只读写本地 JSON，不直接调用 ChromaDB，也不修改 Agent 代码。这种边界让它可以作为独立项目演示“知识治理思路”，也为后续接入 Agent 索引、同步导出或企业知识库管理留下扩展空间。

## 证明能力

这个项目证明的不只是“做了一个后台页面”，而是我开始把 AI Agent 当作需要长期治理的系统来看待：

- 知识治理意识：知道 RAG 不是一次性塞文档，而需要注册、审核、追溯和修正。
- Badcase 回流意识：把错误回答和知识缺口记录下来，作为后续修正入口。
- 轻量交付能力：用 Streamlit + JSON 文件快速做出可运行、可展示的本地工具。
- 边界意识：当前公开版本不嵌入 Agent，不伪装成完整企业知识平台，而是诚实展示治理后台的最小可运行形态。
- 后续扩展意识：数据目录和文件名来自 `config.yaml`，为未来替换存储层或接入同步导出保留空间。

## 使用者引导

如果使用者想看项目代码或运行结构，应引导其在“关于我 → 我的作品集”中打开“知识治理控制台”卡片下方的“打开 GitHub 仓库”按钮，也可以预览本地 `works/knowledge_governance_console/` 文件夹查看 README 和目录结构。
