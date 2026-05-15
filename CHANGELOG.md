# 变更记录

## 未发布

### 阶段一：零风险基础加固

- 保留并补强 `.gitignore`，默认排除密钥、数据库、报告、索引、缓存、构建产物和快捷方式。
- 修复 `.env.example` 的中文乱码，补齐当前项目使用的环境变量模板。
- 新增 `check_env.py`，用于手动检查 Python 版本、运行目录可写性、关键目录和 API/演示模式状态。

### 阶段三：日志与错误处理

- 新增 `middleware.py`，提供统一日志格式和 request_id 注入工具，供后续渐进式接入。

### 阶段六：可观测性

- `middleware.py` 提供 `RequestIdFilter` 与 `with_request_id` 装饰器，可为函数调用链路自动生成 request_id。

### 阶段七：交付与文档

- 新增 `smoke_test.py`，覆盖本地演示回答、空输入兜底、完整公式组直接读取三个核心冒烟场景。

### 影响范围

- 本轮新增脚本与文档为独立文件，除 `.env.example` 模板修复外，不修改核心业务入口。
- 不改变 Streamlit 页面、LangGraph 流程、RAG 检索、报告生成或 API 调用逻辑。

### 回归测试建议

```bash
python check_env.py
python smoke_test.py
python health_check.py
```
