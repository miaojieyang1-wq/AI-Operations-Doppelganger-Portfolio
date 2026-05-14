"""按需加载 Prompt 模块，减少单次调用的上下文负担。

运行时只读取 config/prompts/ 下的 YAML 配置，不再读取旧版 txt Prompt。
这个模块负责根据用户问题选择最相关的少量 Prompt 模块。
"""

from __future__ import annotations

import config_loader


MODULE_PATHS = {
    "base_identity": "modules/base_identity",
    "profile_core": "modules/profile_core",
    "internships": "modules/internships",
    "projects": "modules/projects",
    "game_understanding": "modules/game_understanding",
    "portfolio": "modules/portfolio",
    "prompt_engineering": "modules/prompt_engineering",
    "version_analysis": "modules/version_analysis",
    "diagnosis": "modules/diagnosis",
}


def read_prompt_module(module_name: str) -> str:
    """读取单个 Prompt 模块，只从 config/prompts/*.yaml 获取。"""
    prompt_id = MODULE_PATHS.get(module_name)
    if not prompt_id:
        return ""
    return config_loader.get_system_prompt(prompt_id)


def detect_topic(user_input: str, intent: str = "") -> str:
    """根据用户问题识别更细的主题，用于加载更少、更准的 Prompt。"""
    text = user_input.lower()

    agent_keywords = [
        "本agent",
        "本 agent",
        "这个agent",
        "这个 agent",
        "所有功能",
        "功能并指引",
        "功能介绍",
        "操作指引",
        "如何操作",
        "怎么使用",
    ]
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
        "活动策划",
        "活动工坊",
        "演示模式",
        "数据源真实性预警",
        "数据源预警",
        "结果定位",
    ]
    usage_keywords = ["怎么用", "如何用", "如何操作", "操作指引", "是什么", "功能", "介绍", "指引"]

    if any(keyword in text for keyword in agent_keywords) or (
        any(keyword in user_input for keyword in feature_keywords)
        and any(keyword in user_input for keyword in usage_keywords)
    ):
        return "portfolio"

    if any(
        keyword in user_input
        for keyword in ["提示词工程", "四层缝合", "渐进约束", "协同演进", "方法论迁移", "V4", "prompt", "Prompt"]
    ):
        return "prompt_engineering"

    if any(
        keyword in user_input
        for keyword in [
            "作品集",
            "原文",
            "文章",
            "SEO",
            "blog",
            "Blog",
            "Agent 设计",
            "迭代记录",
            "完整公式组",
            "数学骨架",
            "整套数学体系",
            "状态转移函数",
            "目标泛函",
            "模块写入权",
            "剪枝条件",
            "受击分支",
        ]
    ):
        return "portfolio"

    if any(keyword in user_input for keyword in ["实习", "工作经历", "盛天", "AI音乐", "客服", "付费数据", "Google Play"]):
        return "internships"

    if any(keyword in user_input for keyword in ["游戏理解", "哪款游戏", "崩坏", "星穹铁道", "明日方舟", "米哈游"]):
        return "game_understanding"

    if any(keyword in user_input for keyword in ["活动", "策划", "演出", "统筹", "项目经历", "志愿者", "会议汇报"]):
        return "projects"

    if any(keyword in user_input for keyword in ["自我诊断", "诊断", "短板", "盲区", "优化建议", "局限性"]):
        return "diagnosis"

    if intent == "works":
        return "portfolio"
    if intent == "analysis":
        return "version_analysis"
    return "general_chat"


def select_modules(user_input: str, intent: str = "") -> list[str]:
    """选择本次调用需要加载的 Prompt 模块。"""
    topic = detect_topic(user_input, intent)
    modules = ["base_identity"]

    if intent == "analysis" or topic == "version_analysis":
        return [*modules, "version_analysis"]

    if topic == "portfolio":
        return [*modules, "portfolio"]

    if topic == "prompt_engineering":
        return [*modules, "portfolio", "prompt_engineering"]

    if topic == "internships":
        return [*modules, "profile_core", "internships"]

    if topic == "game_understanding":
        return [*modules, "game_understanding"]

    if topic == "projects":
        return [*modules, "projects"]

    if topic == "diagnosis":
        return [*modules, "profile_core", "internships", "projects", "portfolio", "diagnosis"]

    return [*modules, "profile_core"]


def compose_prompt(user_input: str, intent: str = "", retrieved_context: str = "") -> tuple[str, list[str]]:
    """组合本次调用的最小 Prompt，并返回实际加载的模块列表。"""
    modules = select_modules(user_input, intent)
    prompt_parts = [read_prompt_module(module) for module in modules]
    prompt_parts = [part for part in prompt_parts if part]

    if retrieved_context.strip():
        prompt_parts.append(
            "以下是从本地知识库索引中检索到的相关内容，请优先参考；"
            "如果检索内容与问题无关，请以当前问题和 Prompt 规则为准。\n\n"
            f"{retrieved_context.strip()}"
        )

    return "\n\n---\n\n".join(prompt_parts), modules
