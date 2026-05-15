"""AI 运营分身冒烟测试。

测试目标：
- 正常输入：Agent 可返回本地演示回答
- 边界输入：空输入不会导致核心模块崩溃
- 特殊输入：完整公式组可从独立文件直接读取

本脚本不依赖真实外部 API。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent


def run_case(name: str, func) -> bool:
    """运行单个测试场景。"""
    try:
        func()
        print(f"PASS {name}")
        return True
    except Exception as exc:  # noqa: BLE001 - 冒烟测试需要捕获所有异常并继续执行
        print(f"FAIL {name}: {exc}")
        return False


def setup_test_env() -> None:
    """设置不依赖真实用户数据的测试环境。"""
    temp_dir = Path(tempfile.gettempdir()) / "ai_ops_agent_smoke_test"
    temp_dir.mkdir(parents=True, exist_ok=True)
    os.environ["AI_OPS_DATA_DIR"] = str(temp_dir)
    os.environ["AI_OPS_DEMO_MODE"] = "1"


def test_demo_chat() -> None:
    """正常输入：本地演示回答应可用。"""
    import demo_engine

    response = demo_engine.get_demo_response("了解我", "请介绍你的作品集")
    assert isinstance(response, str)
    assert response.strip()


def test_empty_input_fallback() -> None:
    """边界输入：核心兜底回答函数不应崩溃。"""
    import app

    response = app.build_personal_local_fallback("")
    assert isinstance(response, str)
    assert response.strip()


def test_math_full_direct_read() -> None:
    """特殊输入：完整公式组应走独立读取通道。"""
    import agent_graph

    response = agent_graph.run("展示完整公式组")
    assert response.startswith("$$$LATEX_START$$$")
    assert response.endswith("$$$LATEX_END$$$")
    assert "\\boxed{S_t" in response


def main() -> int:
    """执行冒烟测试。"""
    setup_test_env()
    cases = [
        ("demo_chat", test_demo_chat),
        ("empty_input_fallback", test_empty_input_fallback),
        ("math_full_direct_read", test_math_full_direct_read),
    ]
    results = [run_case(name, func) for name, func in cases]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
