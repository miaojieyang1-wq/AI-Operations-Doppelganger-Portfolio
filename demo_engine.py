"""演示模式响应引擎。

开启演示模式后，所有大模型调用都会从 demo_responses.json 读取预设结果，
用于稳定演示和离线兜底，不访问外部 API。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from functools import lru_cache


PROJECT_DIR = Path(__file__).parent
DEMO_RESPONSE_FILE = PROJECT_DIR / "demo_responses.json"


def is_demo_mode() -> bool:
    """判断当前是否开启演示模式。"""
    return os.getenv("AI_OPS_DEMO_MODE", "0") == "1"


def load_demo_responses() -> dict[str, str]:
    """读取本地演示结果文件。"""
    if not DEMO_RESPONSE_FILE.exists():
        return {
            "fallback": "演示模式已开启，但还没有找到本地演示结果文件 demo_responses.json。请先补充该文件后再试。"
        }
    file_stat = DEMO_RESPONSE_FILE.stat()
    return load_demo_responses_by_signature(file_stat.st_mtime_ns, file_stat.st_size)


@lru_cache(maxsize=1)
def load_demo_responses_by_signature(file_mtime_ns: int, file_size: int) -> dict[str, str]:
    """缓存读取演示结果；JSON 文件更新后自动刷新。"""

    try:
        data = json.loads(DEMO_RESPONSE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {
            "fallback": "演示模式已开启，但本地演示结果文件暂时无法读取。请检查 demo_responses.json 的格式。"
        }

    return {str(key): str(value) for key, value in data.items()}


def classify_demo_response(system_prompt: str, user_content: str) -> str:
    """根据当前任务文本选择对应演示结果。"""
    combined = f"{system_prompt}\n{user_content}"
    feature_keywords = [
        "运营路线图",
        "决策看板",
        "用户洞察",
        "访谈助手",
        "问卷工坊",
        "反馈清洗",
        "版本决策",
        "版本分析",
        "竞品雷达",
        "协作讨论",
        "多职能协作",
        "活动策划模式",
        "活动工坊",
        "演示模式",
        "数据源真实性预警",
        "数据源预警",
        "结果定位",
    ]
    usage_keywords = ["怎么用", "如何用", "如何操作", "操作指引", "是什么", "功能", "介绍", "指引"]
    if any(keyword in user_content for keyword in ["本Agent", "本 Agent", "这个Agent", "这个 Agent", "所有功能", "功能并指引"]) or (
        any(keyword in user_content for keyword in feature_keywords)
        and any(keyword in user_content for keyword in usage_keywords)
    ):
        return "agent_overview"
    if any(keyword in user_content for keyword in ["作品集", "提示词工程", "SEO文章", "迭代记录"]):
        return "personal"
    rules = [
        ("personal", ["了解我", "作品集", "实习", "提示词工程", "游戏理解", "全面介绍"]),
        ("collaboration_coordinator", ["运营总监", "职能专家的分析观点", "目标导向的协同行动方案"]),
        ("collaboration_role", ["市场运营专家", "用户运营专家", "社区运营专家", "产品运营专家", "活动运营专家", "渠道运营专家", "数据运营专家", "内容运营专家", "版本运营专家", "商业化运营专家"]),
        ("feedback_clean", ["反馈清洗", "玩家反馈", "开始清洗", "情绪分析", "发言动机"]),
        ("survey", ["问卷", "量化分析框架", "调研目标", "题型"]),
        ("interview", ["访谈", "访谈提纲", "追问策略", "访谈对象"]),
        ("competitor", ["竞品雷达", "竞品版本", "竞品分析"]),
        ("activity", ["活动策划", "活动方案", "奖励梯度", "活动目标"]),
        ("diagnosis", ["自我诊断", "能力盲区", "表现评估"]),
        ("version_analysis", ["版本公告", "版本分析", "宣发决策", "卖点矩阵"]),
    ]
    for response_key, keywords in rules:
        if any(keyword in combined for keyword in keywords):
            return response_key
    return "fallback"


def get_demo_response(system_prompt: str, user_content: str) -> str:
    """返回匹配当前任务的本地演示结果。"""
    responses = load_demo_responses()
    response_key = classify_demo_response(system_prompt, user_content)
    return responses.get(response_key) or responses.get("fallback", "")
