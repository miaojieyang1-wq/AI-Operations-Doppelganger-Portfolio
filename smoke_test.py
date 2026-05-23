"""AI 运营分身冒烟测试。

测试目标：
- 正常输入：Agent 可返回本地演示回答
- 边界输入：空输入不会导致核心模块崩溃
- 特殊输入：完整公式组可从独立文件直接读取
- 多轮追问：战术引擎语境下输入“公式”可直接读取完整公式组
- 工作流编排：常见需求应走本地快速规划，规划 API 失败时应自动降级

本脚本不依赖真实外部 API。
"""

from __future__ import annotations

import os
import tempfile
import logging
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


def test_math_followup_direct_read() -> None:
    """多轮追问：战术引擎语境下只输入“公式”也应走完整公式组直读。"""
    import agent_graph

    response = agent_graph.run(
        "公式",
        messages=[
            {"role": "user", "content": "你的战术引擎的数学思路是怎么样的？"},
            {"role": "assistant", "content": "它是基于状态空间、目标泛函和搜索剪枝的系统。"},
            {"role": "user", "content": "公式"},
        ],
    )
    assert response.startswith("$$$LATEX_START$$$")
    assert response.endswith("$$$LATEX_END$$$")
    assert "\\boxed{S_t" in response


def test_workflow_fast_planning() -> None:
    """常见工作流需求应直接生成本地 DAG，减少规划等待。"""
    import workflow_orchestrator

    dag = workflow_orchestrator.parse_intent_to_dag(
        "分析这个版本公告，先提炼核心卖点，然后和竞品A最新动态做对比"
    )
    modules = [step["module"] for step in dag]
    assert modules == ["版本分析", "竞品雷达"]
    assert dag[0]["input_from"] == "user_input"
    assert dag[1]["input_from"] == "step_1"


def test_workflow_planning_fallback() -> None:
    """规划 API 不可用时仍应返回保底 DAG。"""
    import workflow_orchestrator

    original_call = workflow_orchestrator.api_runtime.call_chat_completion
    original_level = workflow_orchestrator.logger.level

    def raise_api_error(*_args, **_kwargs):
        raise RuntimeError("simulated planning failure")

    workflow_orchestrator.api_runtime.call_chat_completion = raise_api_error
    workflow_orchestrator.logger.setLevel(logging.CRITICAL)
    try:
        dag = workflow_orchestrator.parse_intent_to_dag("请把这个复杂运营目标拆成可执行流程")
    finally:
        workflow_orchestrator.api_runtime.call_chat_completion = original_call
        workflow_orchestrator.logger.setLevel(original_level)

    assert dag
    assert dag[0]["module"] == "版本分析"


def test_workflow_dependency_context_trim() -> None:
    """长步骤结果传给下一步时应压缩，避免链路越跑越慢。"""
    import workflow_orchestrator

    content = "A" * (workflow_orchestrator.WORKFLOW_DEPENDENCY_CONTEXT_CHARS + 2000)
    trimmed = workflow_orchestrator._trim_dependency_context(content)
    assert len(trimmed) < len(content)
    assert "中间内容已压缩" in trimmed


def main() -> int:
    """执行冒烟测试。"""
    setup_test_env()
    cases = [
        ("demo_chat", test_demo_chat),
        ("empty_input_fallback", test_empty_input_fallback),
        ("math_full_direct_read", test_math_full_direct_read),
        ("math_followup_direct_read", test_math_followup_direct_read),
        ("workflow_fast_planning", test_workflow_fast_planning),
        ("workflow_planning_fallback", test_workflow_planning_fallback),
        ("workflow_dependency_context_trim", test_workflow_dependency_context_trim),
    ]
    results = [run_case(name, func) for name, func in cases]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
