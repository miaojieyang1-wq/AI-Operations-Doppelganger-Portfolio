# 知识库索引迁移说明

本项目的知识库索引不是源码文件，而是运行时数据。它默认保存在当前系统用户的数据目录下：

```text
Windows: %LOCALAPPDATA%/AI_Ops_Agent/chroma_db/local_vectors.json
macOS: ~/Library/Application Support/AI_Ops_Agent/chroma_db/local_vectors.json
Linux: ~/.local/share/AI_Ops_Agent/chroma_db/local_vectors.json
```

因此，把项目代码复制到另一台设备后，`works/` 文档会随仓库存在，但旧设备上生成的索引不会自动存在于新设备。新设备需要重新构建索引。

## 推荐处理方式

1. 确认 `works/` 目录里有 `.md` 或 `.docx` 文档。
2. 安装依赖：

```bash
python -m pip install -r requirements.txt
```

3. 构建索引：

```bash
python build_index.py
```

4. 检查索引状态：

```bash
python diagnose_index.py
```

5. 启动应用：

```bash
streamlit run app.py
```

## 常见误解

- `chroma_db/` 和 `local_vectors.json` 默认不上传 GitHub，这是为了避免提交本地缓存和运行时数据。
- 开启演示模式时，应用会读取本地预设结果，不会使用 RAG 检索结果。想验证知识库索引效果，需要关闭演示模式并连接可用 API。
- 如果设置了 `AI_OPS_DATA_DIR`，索引会写入这个自定义目录，而不是系统默认用户数据目录。

