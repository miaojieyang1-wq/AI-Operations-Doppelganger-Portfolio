# Knowledge Governance Console

独立的知识治理控制台，用于注册、审计、追溯和回流知识库质量问题。控制台只读写本地 JSON 文件，不依赖也不嵌入任何 AI 运营分身 Agent 代码。

## 功能

- 知识单元注册中心
- 知识库健康度仪表盘
- 知识清单筛选
- 责任归属与错误追溯工作台
- Badcase 回流与审核看板

## 启动

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

默认数据文件：

- `data/knowledge_base.json`
- `data/badcase_log.json`

可在 `config.yaml` 中调整数据目录和文件名。
