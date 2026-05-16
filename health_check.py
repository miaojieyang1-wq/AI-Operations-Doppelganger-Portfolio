"""
AI运营分身项目一键自检脚本。

作用：
- 检查核心 Python 文件是否能通过语法检查
- 检查必要 YAML 提示词配置是否存在且可读取
- 检查关键模块能否正常导入
- 检查本地知识库索引状态接口是否正常
- 检查演示模式预设结果是否可读取
- 检查首页入口模块是否可加载

运行方式：
python health_check.py
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).parent
os.environ.setdefault("AI_OPS_DATA_DIR", str(ROOT / "tmp_health_runtime"))
os.environ.setdefault("AI_OPS_DEMO_MODE", "1")

PYTHON_FILES = [
    "app.py",
    "api_runtime.py",
    "agent_graph.py",
    "rag_engine.py",
    "prompt_loader.py",
    "demo_engine.py",
    "build_index.py",
    "report_utils.py",
    "ui_components.py",
    "style_assets.py",
    "collaboration_config.py",
    "config_loader.py",
    "core.py",
    "api.py",
    "database.py",
    "install.py",
]

PROMPT_FILES = [
    "config/prompts/prompt_background.yaml",
    "config/prompts/tasks/interview.yaml",
    "config/prompts/tasks/survey.yaml",
    "config/prompts/tasks/feedback_clean.yaml",
    "config/prompts/tasks/competitor.yaml",
    "config/prompts/tasks/activity_workshop.yaml",
    "config/prompts/tasks/comment_analysis.yaml",
    "config/prompts/tasks/collaboration_coordinator.yaml",
    "config/prompts/modules/base_identity.yaml",
    "config/prompts/modules/profile_core.yaml",
    "config/prompts/modules/internships.yaml",
    "config/prompts/modules/projects.yaml",
    "config/prompts/modules/game_understanding.yaml",
    "config/prompts/modules/portfolio.yaml",
    "config/prompts/modules/prompt_engineering.yaml",
    "config/prompts/modules/version_analysis.yaml",
    "config/prompts/modules/diagnosis.yaml",
    "config/agents/market_ops.yaml",
    "config/agents/user_ops.yaml",
    "config/agents/community_ops.yaml",
    "config/agents/product_ops.yaml",
    "config/agents/event_ops.yaml",
    "config/agents/channel_ops.yaml",
    "config/agents/data_ops.yaml",
    "config/agents/content_ops.yaml",
    "config/agents/version_ops.yaml",
    "config/agents/monetization_ops.yaml",
]

TEXT_SUFFIXES = {".py", ".md", ".txt", ".yaml", ".yml", ".bat", ".sh", ".iss", ".spec"}
TEXT_FILENAMES = {".env.example", ".gitignore", ".editorconfig"}
ENCODING_SCAN_SKIP_DIRS = {
    ".git",
    ".python-core",
    ".python-runtime",
    "__pycache__",
    "archive",
    "backups",
    "dist",
    "build",
    "chroma_db",
    "chroma_db_backup",
    "tmp_health_runtime",
    "tmp_guided_installer",
    "tmp_runtime_test",
    "tmp_runtime_test_api",
    "tmp_runtime_test_api2",
    "tmp_runtime_verify",
    "tmp_validation_outputs",
}
MOJIBAKE_TOKEN_ESCAPES = [
    "\\u6d63\\u72b3\\u69f8",
    "\\u9428",
    "\\u951b",
    "\\u9983",
    "\\u9225",
    "\\u7ecb",
    "\\u93c4",
    "\\u6d93",
    "\\u6769",
    "\\u59af",
]
MOJIBAKE_TOKENS = ["?" * 4, *[token.encode("ascii").decode("unicode_escape") for token in MOJIBAKE_TOKEN_ESCAPES]]


def check_python_syntax() -> list[str]:
    issues: list[str] = []
    for filename in PYTHON_FILES:
        file_path = ROOT / filename
        if not file_path.exists():
            issues.append(f"缺少文件：{filename}")
            continue
        try:
            source = file_path.read_text(encoding="utf-8")
            compile(source, str(file_path), "exec")
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            issues.append(f"{filename} 语法检查失败：{exc}")
    return issues


def check_prompt_files() -> list[str]:
    issues: list[str] = []
    import config_loader

    for filename in PROMPT_FILES:
        file_path = ROOT / filename
        if not file_path.exists():
            issues.append(f"缺少 YAML 配置文件：{filename}")
        elif config_loader.load_yaml_config(file_path) is None:
            issues.append(f"YAML 配置格式异常：{filename}")

    if not config_loader.get_system_prompt("prompt_background").strip():
        issues.append("基础 Prompt 为空，可能无法正常回答关于我的问题")
    if not config_loader.get_system_prompt("tasks/not_exists_for_health_check").strip():
        issues.append("YAML 缺失时的默认 Prompt 兜底异常")
    return issues


def check_text_encoding() -> list[str]:
    """扫描项目文本文件，拦截常见中文乱码写入。"""
    issues: list[str] = []
    for file_path in ROOT.rglob("*"):
        if not file_path.is_file() or (file_path.suffix not in TEXT_SUFFIXES and file_path.name not in TEXT_FILENAMES):
            continue
        if any(part in ENCODING_SCAN_SKIP_DIRS for part in file_path.relative_to(ROOT).parts):
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            issues.append(f"文件不是有效 UTF-8 编码：{file_path.relative_to(ROOT)}")
            continue

        if "\ufffd" in text:
            issues.append(f"文件包含替换字符，疑似编码损坏：{file_path.relative_to(ROOT)}")
            continue

        for token in MOJIBAKE_TOKENS:
            if token in text:
                issues.append(f"文件疑似包含中文乱码 `{token}`：{file_path.relative_to(ROOT)}")
                break
    return issues


def check_core_imports() -> list[str]:
    issues: list[str] = []
    try:
        import app
        import collaboration_config
        import config_loader
        import demo_engine
        import rag_engine
        import report_utils
        import style_assets

        if len(collaboration_config.COLLABORATION_ROLES) != 10:
            issues.append("多职能协作角色数量不是 10 个")
        if len(collaboration_config.COLLABORATION_GOALS) < 1:
            issues.append("多职能协作目标列表为空")
        if "<style>" not in style_assets.MAIN_CSS:
            issues.append("主页面样式未正确加载")
        if "<style>" not in style_assets.ENTRY_CSS:
            issues.append("弹窗样式未正确加载")
        if not app.format_report_markdown("## 测试标题").strip():
            issues.append("报告格式化函数返回为空")
        rag_status = rag_engine.get_vectorstore_status()
        if not isinstance(rag_status, dict):
            issues.append("知识库索引状态返回异常")
        demo_result = demo_engine.get_demo_response("访谈助手", "生成访谈提纲")
        if not demo_result.strip():
            issues.append("演示模式访谈预设结果为空")
        for agent_id in [
            "market_ops",
            "user_ops",
            "community_ops",
            "product_ops",
            "event_ops",
            "channel_ops",
            "data_ops",
            "content_ops",
            "version_ops",
            "monetization_ops",
        ]:
            if not config_loader.get_agent_prompt(agent_id).strip():
                issues.append(f"运营角色配置生成提示词为空：{agent_id}")
    except Exception as exc:
        issues.append(f"核心模块导入失败：{exc}")
    return issues


def check_app_entry() -> list[str]:
    """检查首页入口是否存在，避免 Streamlit 测试器在 Windows 临时目录产生清理警告。"""
    issues: list[str] = []
    try:
        import app

        if not callable(getattr(app, "main", None)):
            issues.append("app.py 中没有找到可调用的 main() 入口")
        if not callable(getattr(app, "render_first_use_config_page", None)):
            issues.append("首次使用配置页面入口缺失")
    except Exception as exc:
        issues.append(f"首页入口检查失败：{exc}")
    return issues


def main() -> None:
    checks = [
        ("Python 语法", check_python_syntax),
        ("提示词配置", check_prompt_files),
        ("文本编码", check_text_encoding),
        ("核心模块", check_core_imports),
        ("首页入口", check_app_entry),
    ]

    all_issues: list[str] = []
    print("开始自检 AI 运营分身项目...\n")
    for name, check in checks:
        issues = check()
        if issues:
            print(f"[未通过] {name}")
            for issue in issues:
                print(f"  - {issue}")
            all_issues.extend(issues)
        else:
            print(f"[通过] {name}")

    print("\n自检结果：")
    if all_issues:
        print(f"发现 {len(all_issues)} 个需要处理的问题。")
        raise SystemExit(1)
    print("全部通过，可以启动或打包演示。")


if __name__ == "__main__":
    main()
