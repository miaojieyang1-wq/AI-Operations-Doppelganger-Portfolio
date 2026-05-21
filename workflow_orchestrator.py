# -*- coding: utf-8 -*-
"""自然语言驱动的运营工作流编排层。"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

import api_runtime
import config_loader


logger = logging.getLogger(__name__)

WORKFLOW_SYSTEM_PROMPT = """你是一个工作流编排引擎。用户会用自然语言描述运营分析需求。你需要将用户的需求解析为一系列可执行的步骤，每个步骤对应一个已有的功能模块。

可用模块列表：
- 版本分析：输入版本公告，输出六模块分析报告（版本内容拆解、三层卖点矩阵、多平台宣发文案、内容效果预判、音乐专业分析、宣发节奏建议）
- 竞品雷达：输入竞品公告或从本地加载，输出竞品分类、三段式策略分析、借鉴优先级矩阵、版本趋势追踪、借鉴风险自查
- 反馈清洗：输入玩家反馈文本，输出情绪分类、动机识别、可视化图表、优先级排序、处理建议
- 问卷工坊：输入调研目标，输出多题型问卷、信效度控制、反向计分双版本、预测试机制
- 访谈助手：输入访谈目标，输出结构化访谈提纲、五层用户画像、追问预案、观察记录表
- 活动策划：输入活动目标、资源量级、目标用户，输出设计推导链路、多方案比选、线下支援策略、活动剧情和小游戏建议
- 协作讨论：输入版本公告，选择参与角色和运营目标，输出十个职能角色并发分析和协调者综合方案
- 自我诊断：输入对话历史或报告文本，输出回答质量评估、能力盲区识别、优化建议

输出格式：纯JSON数组，每个元素为一个步骤对象，包含以下字段：
- step：步骤序号，整数
- module：模块名称，字符串，必须从上述可用模块列表中选择
- action：该步骤要执行的具体操作，用自然语言描述
- input_from：该步骤的输入来源。如果从用户指令中获取，填“user_input”；如果依赖前面步骤的输出，填“step_N”，N为前面某步的序号
- params：额外参数，JSON对象，可为空对象

不要输出任何JSON之外的内容。不要用代码块包裹。确保JSON格式正确可解析。"""

REVISE_DAG_SYSTEM_PROMPT = """你收到一个正在执行的工作流DAG、用户的修改指令、以及已经执行完毕的步骤结果。请根据修改指令重新生成一个完整的DAG。

修改指令可能是：小范围调整（如修改某一步的分析方向）、中范围调整（如替换部分步骤、调整顺序）、大范围调整（如推倒重来、重新定义工作流目标）。你需要自行判断修改范围，采用最小必要的重规划策略，不预设任何固定的修改模式。

规则：
- 已执行步骤的结果保留在executed_results中，新DAG可以引用这些结果作为输入（input_from填”executed_step_N“），避免重复执行
- 已执行步骤如果与修改后的需求不再相关，新DAG中直接废弃该步骤，不引用其结果
- 新DAG必须完整，覆盖从当前节点到最终目标的所有必要步骤
- 如果用户指令是推倒重来，生成一个全新的DAG，不保留原DAG的结构
- 输出格式与parse_intent_to_dag完全相同：纯JSON数组，每个元素包含step、module、action、input_from、params字段
- 不要输出任何JSON之外的内容，确保JSON格式正确可解析"""

ALLOWED_MODULES = {
    "版本分析",
    "竞品雷达",
    "反馈清洗",
    "问卷工坊",
    "访谈助手",
    "活动策划",
    "协作讨论",
    "自我诊断",
}

DEFAULT_DAG = [
    {
        "step": 1,
        "module": "版本分析",
        "action": "基于用户自然语言需求生成基础运营分析报告",
        "input_from": "user_input",
        "params": {},
    }
]


def parse_intent_to_dag(user_instruction: str) -> list[dict[str, Any]]:
    """把自然语言运营需求解析为已有模块组成的 DAG 步骤列表。"""
    instruction = str(user_instruction or "").strip()
    if not instruction:
        return []

    response = api_runtime.call_chat_completion(
        [
            {"role": "system", "content": WORKFLOW_SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ],
        temperature=0,
    )
    return _normalize_dag(_parse_json_array(response))


def execute_dag(dag: list[dict[str, Any]], user_inputs: str | dict[str, Any], orchestrator: Any) -> dict[int, dict[str, Any]]:
    """按步骤执行工作流，并保留每一步的结果与依赖关系。"""
    executed_results: dict[int, dict[str, Any]] = {}
    if isinstance(user_inputs, dict) and isinstance(user_inputs.get("_executed_results"), dict):
        executed_results.update(_normalize_result_keys(user_inputs["_executed_results"]))
    for step in sorted(dag, key=_step_number):
        step_number = _step_number(step)
        input_from = str(step.get("input_from", "user_input")).strip() or "user_input"
        source_content = _resolve_step_input(input_from, user_inputs, executed_results)
        if source_content is None:
            executed_results[step_number] = _build_step_result(
                step,
                success=False,
                content="",
                error=f"依赖步骤不可用：{input_from}",
            )
            continue
        executed_results[step_number] = _execute_step_safely(step, source_content, orchestrator)
    return executed_results


def format_dag_result(dag: list[dict[str, Any]], results: dict[int | str, dict[str, Any]]) -> str:
    """将工作流执行结果格式化为可读 Markdown 报告。"""
    lines = ["# 工作流执行报告", ""]
    normalized_results = _normalize_result_keys(results)
    for step in sorted(dag, key=_step_number):
        step_number = _step_number(step)
        result = normalized_results.get(step_number, {})
        status = "成功" if result.get("success") else "失败"
        lines.extend(
            [
                f"## Step {step_number}：{step.get('module', '')}",
                f"- 执行动作：{step.get('action', '')}",
                f"- 数据依赖：{step.get('input_from', 'user_input')}",
                f"- 执行状态：{status}",
            ]
        )
        if result.get("error"):
            lines.append(f"- 错误信息：{result['error']}")
        content = str(result.get("content", "")).strip()
        if content:
            lines.extend(["", content])
        lines.append("")
    return "\n".join(lines).strip()


def revise_dag(
    original_dag: list[dict[str, Any]],
    revision_instruction: str,
    executed_results: dict[int | str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """根据用户修改指令和已执行结果重规划完整 DAG。"""
    payload = {
        "original_dag": original_dag,
        "revision_instruction": revision_instruction,
        "executed_results": _normalize_result_keys(executed_results),
    }
    response = api_runtime.call_chat_completion(
        [
            {"role": "system", "content": REVISE_DAG_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
        ],
        temperature=0,
    )
    return _normalize_dag(_parse_json_array(response))


def execute_dag_interactively(user_instruction: str, orchestrator: Any) -> dict[str, Any]:
    """初始化交互式执行状态，并执行第一步。"""
    initial_dag = parse_intent_to_dag(user_instruction)
    executed_results = execute_dag(initial_dag[:1], {"user_input": user_instruction}, orchestrator) if initial_dag else {}
    return {
        "original_instruction": user_instruction,
        "initial_dag": initial_dag,
        "final_dag": initial_dag,
        "executed_results": executed_results,
        "revision_history": [],
        "current_step_index": 1 if executed_results else 0,
        "status": "completed" if len(executed_results) >= len(initial_dag) else "waiting",
    }


def format_interactive_result(
    original_instruction: str,
    final_dag: list[dict[str, Any]],
    executed_results: dict[int | str, dict[str, Any]],
    revision_history: list[dict[str, Any]],
) -> str:
    """把交互式执行全过程格式化为 Markdown 报告。"""
    normalized_results = _normalize_result_keys(executed_results)
    lines = [
        "# 交互式工作流执行报告",
        "",
        "## 用户原始指令",
        str(original_instruction or "").strip() or "未提供",
        "",
        "## 初始DAG",
    ]
    initial_dag = revision_history[0].get("dag_before", final_dag) if revision_history else final_dag
    for step in sorted(initial_dag, key=_step_number):
        lines.append(f"- Step {_step_number(step)}｜{step.get('module', '')}｜{step.get('input_from', 'user_input')}｜{step.get('action', '')}")

    lines.extend([
        "",
        "## 修改历史",
    ])
    if revision_history:
        for item in revision_history:
            lines.extend(
                [
                    f"- 时间：{item.get('time', '')}",
                    f"  修改指令：{item.get('instruction', '')}",
                    f"  废弃步骤：{', '.join(str(step) for step in item.get('discarded_steps', [])) or '无'}",
                    f"  废弃原因：{item.get('discard_reason', '无')}",
                ]
            )
    else:
        lines.append("无")

    lines.extend(["", "## 最终DAG"])
    for step in sorted(final_dag, key=_step_number):
        lines.append(f"- Step {_step_number(step)}｜{step.get('module', '')}｜{step.get('input_from', 'user_input')}｜{step.get('action', '')}")

    discarded_steps = _collect_discarded_steps(revision_history)
    lines.extend(["", "## 被废弃的步骤"])
    if discarded_steps:
        for step_number, reason in discarded_steps.items():
            lines.append(f"- Step {step_number}：{reason}")
    else:
        lines.append("无")

    lines.extend(["", "## 所有步骤执行结果"])
    lines.append(format_dag_result(final_dag, normalized_results).replace("# 工作流执行报告\n\n", ""))
    return "\n".join(lines).strip()


def _parse_json_array(response_text: str) -> list[Any]:
    """从模型输出中解析 JSON 数组，兼容偶发代码块包裹。"""
    text = str(response_text or "").strip()
    if not text:
        return DEFAULT_DAG
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return DEFAULT_DAG
        parsed = json.loads(match.group(0))
    return parsed if isinstance(parsed, list) else DEFAULT_DAG


def _normalize_dag(raw_dag: list[Any]) -> list[dict[str, Any]]:
    """清洗模型输出，保证只包含可执行模块。"""
    dag: list[dict[str, Any]] = []
    for index, raw_step in enumerate(raw_dag, start=1):
        if not isinstance(raw_step, dict):
            continue
        module = str(raw_step.get("module", "")).strip()
        if module not in ALLOWED_MODULES:
            continue
        params = raw_step.get("params")
        dag.append(
            {
                "step": _coerce_step_number(raw_step.get("step"), index),
                "module": module,
                "action": str(raw_step.get("action", "")).strip() or f"执行{module}",
                "input_from": str(raw_step.get("input_from", "user_input")).strip() or "user_input",
                "params": params if isinstance(params, dict) else {},
            }
        )
    return sorted(dag or DEFAULT_DAG, key=_step_number)


def _execute_step_safely(step: dict[str, Any], source_content: str, orchestrator: Any) -> dict[str, Any]:
    try:
        result = _execute_step(step, source_content, orchestrator)
        success = bool(result.get("success", True))
        error = str(result.get("error", ""))
        content = _extract_result_content(result)
        if not success and not content.strip():
            content = _build_failure_content(step, error)
        return _build_step_result(
            step,
            success=success,
            content=content,
            error=error,
            raw=result,
        )
    except Exception as exc:
        error = _format_workflow_error(exc)
        if _is_timeout_error(exc):
            logger.warning("Workflow step timed out: step=%s module=%s error=%s", step.get("step"), step.get("module", ""), exc)
        else:
            logger.exception("Workflow step failed: step=%s module=%s", step.get("step"), step.get("module", ""))
        return _build_step_result(step, success=False, content=_build_failure_content(step, error), error=error)


def _execute_step(step: dict[str, Any], source_content: str, orchestrator: Any) -> dict[str, Any]:
    module = str(step.get("module", "")).strip()
    params = step.get("params") if isinstance(step.get("params"), dict) else {}
    if module == "版本分析":
        return orchestrator.run_version_analysis(source_content, config_loader.get_system_prompt("modules/version_analysis"))
    if module == "竞品雷达":
        return orchestrator.run_competitor_analysis(source_content, config_loader.get_system_prompt("tasks/competitor"))
    if module == "反馈清洗":
        return orchestrator.run_feedback_clean(source_content, config_loader.get_system_prompt("tasks/feedback_clean"))
    if module == "问卷工坊":
        return orchestrator.run_task("insight:survey", source_content, config_loader.get_system_prompt("tasks/survey"))
    if module == "访谈助手":
        return orchestrator.run_task("insight:interview", source_content, config_loader.get_system_prompt("tasks/interview"))
    if module == "活动策划":
        return orchestrator.run_activity_workshop(source_content, config_loader.get_system_prompt("tasks/activity_workshop"))
    if module == "协作讨论":
        return orchestrator.run_collaboration(
            source_content,
            agents=params.get("agents"),
            goal=str(params.get("goal", "无特定目标（综合评估）")),
        )
    if module == "自我诊断":
        return orchestrator.run_task("personal:diagnosis", source_content, config_loader.get_system_prompt("modules/diagnosis"))
    return {"success": False, "content": "", "error": f"未知模块：{module}"}


def _resolve_step_input(input_from: str, user_inputs: str | dict[str, Any], results: dict[int, dict[str, Any]]) -> str | None:
    if input_from == "user_input":
        return _stringify_user_input(user_inputs)
    match = re.fullmatch(r"(?:step|executed_step)_(\d+)", input_from)
    if not match:
        return _stringify_user_input(user_inputs)
    source = results.get(int(match.group(1)))
    if not source or not source.get("success"):
        return None
    return str(source.get("content", "")).strip()


def _stringify_user_input(user_inputs: str | dict[str, Any]) -> str:
    if isinstance(user_inputs, dict):
        value = user_inputs.get("user_input", user_inputs)
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return str(user_inputs)


def _extract_result_content(result: dict[str, Any]) -> str:
    if "content" in result:
        return str(result.get("content", ""))
    if "coordinator_result" in result:
        return str(result.get("coordinator_result", ""))
    return json.dumps(result, ensure_ascii=False, indent=2)


def _is_timeout_error(exc: Exception) -> bool:
    text = f"{exc.__class__.__name__}: {exc}"
    return "Timeout" in text or "timed out" in text.lower()


def _format_workflow_error(exc: Exception) -> str:
    if _is_timeout_error(exc):
        return (
            "模型响应超时：请求已到达 API，但生成或回传超过了本地等待时间。"
            "建议缩短输入、拆分步骤或稍后重试。"
        )
    return str(exc)


def _build_failure_content(step: dict[str, Any], error: str) -> str:
    module = str(step.get("module", "当前模块") or "当前模块")
    action = str(step.get("action", "") or "")
    lines = [
        f"{module}未能完成。",
        "",
        f"失败原因：{error or '未知错误'}",
    ]
    if action:
        lines.extend(["", f"原计划动作：{action}"])
    lines.extend(
        [
            "",
            "处理建议：可以缩短输入文本、减少单次工作流步骤，或稍后重新执行该步骤。",
        ]
    )
    return "\n".join(lines)


def _build_step_result(
    step: dict[str, Any],
    success: bool,
    content: str,
    error: str,
    raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "success": success,
        "module": step.get("module", ""),
        "action": step.get("action", ""),
        "input_from": step.get("input_from", "user_input"),
        "content": content,
        "raw": raw or {},
        "error": error,
    }


def _normalize_result_keys(results: dict[int | str, dict[str, Any]]) -> dict[int, dict[str, Any]]:
    normalized: dict[int, dict[str, Any]] = {}
    for key, value in results.items():
        if isinstance(key, int):
            normalized[key] = value
            continue
        match = re.search(r"(\d+)$", str(key))
        if match:
            normalized[int(match.group(1))] = value
    return normalized


def _step_number(step: dict[str, Any]) -> int:
    return _coerce_step_number(step.get("step"), 0)


def _coerce_step_number(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _collect_discarded_steps(revision_history: list[dict[str, Any]]) -> dict[int, str]:
    discarded: dict[int, str] = {}
    for item in revision_history:
        reason = str(item.get("discard_reason", "修改后不再引用该步骤"))
        for step_number in item.get("discarded_steps", []):
            discarded[_coerce_step_number(step_number, 0)] = reason
    return {key: value for key, value in discarded.items() if key}


def utc_timestamp() -> str:
    """生成交互式修改历史使用的 UTC 时间戳。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
