# AI 运营分身项目运行指南

## 1. 项目简介

这是一个基于 Streamlit 的 AI 运营分身作品集网站，包含：

- 关于我：模拟面试、作品集展示、自我诊断
- 决策看板：按运营生命周期进入不同工作台
- 用户洞察：访谈助手、问卷工坊、反馈清洗
- 版本决策：版本分析、竞品雷达、多职能协作讨论
- 活动策划：生成活动方案并导出 Markdown
- 演示模式：无需实时调用 API，可读取本地预设结果稳定演示
- 一键自检：检查项目是否可运行

## 2. 环境要求

建议使用：

- Windows 10/11
- Python 3.10 或以上
- 能正常访问命令行 PowerShell

## 3. 安装依赖

解压项目后，进入项目文件夹，在 PowerShell 中运行：

```powershell
python -m pip install -r requirements.txt
```

如果你的电脑同时装了多个 Python，可以改用：

```powershell
py -m pip install -r requirements.txt
```

## 4. 配置 API Key

项目支持两种方式配置 DeepSeek API Key。

### 方式一：网页内填写

启动网站后，在侧边栏找到“连接我的 API”，填入 API Key、Base URL 和模型名。

默认配置：

- Base URL: `https://api.deepseek.com/v1`
- Model: `deepseek-chat`

### 方式二：使用 .env 文件

复制 `.env.example` 为 `.env`，然后填入：

```env
DEEPSEEK_API_KEY=你的key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

注意：正式发给别人前，不要把自己的真实 API Key 写进 `.env`。

## 5. 启动项目

### 方法一：双击启动

双击：

```text
start_app.bat
```

然后在浏览器打开：

```text
http://127.0.0.1:8501/
```

### 方法二：命令行启动

```powershell
python -m streamlit run app.py --server.port 8501
```

## 6. 演示模式

如果不想实时调用 API，可以在网页侧边栏打开“演示模式”。

开启后，所有主要分析功能会读取 `demo_responses.json` 中的本地预设结果。

适合：

- 面试演示
- 离线展示
- API 不稳定时兜底
- 发给别人快速预览项目效果

## 7. 本地知识库

项目包含本地知识库索引文件：

```text
chroma_db/local_vectors.json
```

如果 `works/` 文件夹内容有更新，可以重新构建索引：

```powershell
python build_index.py
```

## 8. 一键自检

启动前建议运行：

```powershell
python health_check.py
```

如果看到：

```text
全部通过，可以启动或打包演示。
```

说明核心文件、提示词、演示模式和首页渲染都正常。

## 9. 常见问题

### Q1：没有 API Key 能不能看？

可以。打开侧边栏“演示模式”即可体验预设结果。

### Q2：运行时报缺少依赖怎么办？

重新运行：

```powershell
python -m pip install -r requirements.txt
```

### Q3：网页打不开怎么办？

确认命令行里 Streamlit 已启动，然后打开：

```text
http://127.0.0.1:8501/
```

如果 8501 被占用，可以换端口：

```powershell
python -m streamlit run app.py --server.port 8502
```

### Q4：分析结果是否实时准确？

不保证。项目内置了数据源真实性预警。所有 AI 分析建议在正式决策前与官方公告、真实用户反馈或实时数据交叉验证。

## 10. 推荐体验顺序

1. 打开首页“运营路线图”
2. 进入“关于我”了解作品集和 Agent 自身设计
3. 打开“演示模式”
4. 尝试“版本决策”中的版本分析和多职能协作讨论
5. 尝试“用户洞察”中的反馈清洗
6. 运行 `health_check.py` 查看项目自检能力
