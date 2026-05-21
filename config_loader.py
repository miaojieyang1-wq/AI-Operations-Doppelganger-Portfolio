# -*- coding: utf-8 -*-
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import runtime_paths


PROJECT_DIR = Path(__file__).parent
APP_CONFIG_FILE = PROJECT_DIR / "config" / "app.yaml"
WRITABLE_PATH_KEYS = {"reports", "activity_plans", "collaboration_reports"}

DEFAULT_APP_CONFIG: dict[str, Any] = {
    "app": {
        "name": "oz的AI运营分身",
        "page_title": "oz的 AI 运营分身",
        "page_icon": "🎮",
    },
    "model": {
        "provider": "deepseek",
        "default_model": "deepseek-chat",
        "default_base_url": "https://api.deepseek.com",
        "default_temperature": 0.7,
        "collaboration_role_temperature": 0.6,
        "collaboration_coordinator_temperature": 0.5,
        "connection_test_temperature": 0,
        "connect_timeout_seconds": 5,
        "read_timeout_seconds": 120,
        "max_retries": 2,
    },
    "paths": {
        "works": "works",
        "reports": "reports",
        "activity_plans": "activity_plans",
        "static": "static",
        "entry_image": "static/nkx.png",
        "entry_image_fast": "static/nkx_entry.webp",
        "collaboration_reports": "reports/collaboration",
    },
    "admin": {
        "password_hash_env": "AI_OPS_ADMIN_PASSWORD_HASH",
    },
}


def deep_merge(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Merge nested configuration while keeping defaults for missing keys."""
    merged = deepcopy(defaults)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


@lru_cache(maxsize=1)
def load_app_config() -> dict[str, Any]:
    """Load config/app.yaml; fall back to hardcoded defaults if it is missing or invalid."""
    runtime_paths.load_runtime_env()
    if not APP_CONFIG_FILE.exists():
        return deepcopy(DEFAULT_APP_CONFIG)

    try:
        import yaml

        loaded = yaml.safe_load(APP_CONFIG_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return deepcopy(DEFAULT_APP_CONFIG)

    if not isinstance(loaded, dict):
        return deepcopy(DEFAULT_APP_CONFIG)
    return deep_merge(DEFAULT_APP_CONFIG, loaded)


def config_path(config: dict[str, Any], key: str) -> Path:
    """Resolve a path from config.

    Writable runtime data is resolved under the user data directory; app resources stay
    relative to the project/application directory.
    """
    value = str(config.get("paths", {}).get(key, DEFAULT_APP_CONFIG["paths"][key]))
    path = Path(value)
    if path.is_absolute():
        return path
    if key in WRITABLE_PATH_KEYS:
        return runtime_paths.data_path(path)
    return PROJECT_DIR / path


DEFAULT_SYSTEM_PROMPTS: dict[str, str] = {
    "prompt_background": "你是一位专业、清晰、可靠的游戏运营分析助手。请基于用户输入给出具体、自然、可执行的回答。",
    "tasks/interview": "你是一名游戏用户研究访谈助手。请基于访谈目标输出可直接执行的访谈提纲，必须包含访谈开场白、核心问题、追问策略、对象筛选建议、结束语和致谢模板。",
    "tasks/survey": "你是一名游戏用户研究问卷设计助手。请基于调研目标和目标用户描述输出结构化问卷，包含题目、测量目的、题型分布和投放建议。",
    "tasks/feedback_clean": "你是一名游戏玩家反馈清洗助手。请对玩家反馈进行分类、情绪分析、去重合并、优先级排序，并给出处理建议。",
    "tasks/competitor": "你是一名游戏竞品运营分析助手。请基于竞品公告和自家版本基准，输出竞品摘要、对比分析、可借鉴策略、风险预警和行动建议。",
    "tasks/activity_workshop": "你是一名游戏活动运营策划助手。请基于活动目标和背景，生成可落地的活动方案，包含玩法、路径、奖励、风险、宣发和复盘指标。",
    "tasks/comment_analysis": "你是一名游戏视频舆情分析助手。请基于用户提供的评论样本，分析情绪、话题、风险和可执行运营建议。",
    "tasks/collaboration_coordinator": "你是游戏运营团队的运营总监。请综合多个职能专家的观点，围绕本次运营目标输出共识、分歧、行动方案和风险预警。",
    "modules/base_identity": "你是 oz 的 AI 运营分身，回答要自然、具体、有运营判断，并优先基于已知作品集和项目资料。",
    "modules/profile_core": "请围绕 oz 的个人背景、运营能力、AI 工具实践和游戏理解回答问题，避免空泛套话。",
    "modules/internships": "请优先结合 oz 的真实实习和项目经历回答，包括 AI 音乐产品运营、教育相关正式实习、社会演出统筹等经历。",
    "modules/projects": "请结合活动统筹、项目管理、志愿教学、国际会议论文汇报等项目经历，说明能力与岗位关联。",
    "modules/game_understanding": "当被问到游戏理解时，优先选择《崩坏：星穹铁道》，并从玩家视角、运营目的、社区讨论和内容节奏分析。",
    "modules/portfolio": "请介绍本 Agent、SEO 提示词工程、迭代记录和文章作品集，并说明它们分别验证哪些能力。",
    "modules/prompt_engineering": "请围绕 SEO 提示词工程的迭代、渐进约束模式、结构控制和产出验证回答。",
    "modules/version_analysis": "请基于游戏版本公告输出结构化版本分析报告，包含内容拆解、卖点矩阵、宣发建议、效果预判、风险和后续追踪。",
    "modules/diagnosis": "请面向面试官对 oz 的 AI 运营能力进行诊断，包含优势、短板、Prompt 优化建议、知识库补充建议和后续可问问题。",
}


AGENT_PROMPT_TEMPLATE = """你是游戏运营团队中的{role_name}。你的核心职责是{core_responsibility}。

你的分析框架：
{analysis_framework}

你的输出风格：{style}。经常使用{terminology}等术语。输出控制在{output_limit}字以内。{deterministic_rules_section}

### 回答边界规则
{boundary_rule_template}"""


DEFAULT_AGENT_PROMPTS: dict[str, str] = {
    "market_ops": "你是游戏市场运营专家，请从市场定位、核心卖点、目标人群、渠道投放和品牌传播角度分析版本公告。若信息不足，请明确说明缺乏市场运营相关内容，并给出1-2条参考建议。输出300字以内。",
    "user_ops": "你是游戏用户运营专家，请从用户分层、生命周期、留存、流失预警和用户激励角度分析版本公告。若信息不足，请明确说明缺乏用户运营相关内容，并给出1-2条参考建议。输出300字以内。",
    "community_ops": "你是游戏社区运营专家，请从社区热点、二创潜力、互动活动和舆情风险角度分析版本公告。若信息不足，请明确说明缺乏社区运营相关内容，并给出1-2条参考建议。输出300字以内。",
    "product_ops": "你是游戏产品运营专家，请从功能闭环、用户痛点、体验路径和迭代节奏角度分析版本公告。若信息不足，请明确说明缺乏产品运营相关内容，并给出1-2条参考建议。输出300字以内。",
    "event_ops": "你是游戏活动运营专家，请从活动矩阵、参与路径、奖励梯度和活动效果角度分析版本公告。若信息不足，请明确说明缺乏活动运营相关内容，并给出1-2条参考建议。输出300字以内。",
    "channel_ops": "你是游戏渠道运营专家，请从渠道矩阵、素材准备、流量获取、转化漏斗和投放ROI角度分析版本公告。若信息不足，请明确说明缺乏渠道运营相关内容，并给出1-2条参考建议。输出300字以内。",
    "data_ops": "你是游戏数据运营专家，请从核心指标、数据监控、归因分析和A/B测试角度分析版本公告。若信息不足，请明确说明缺乏数据运营相关内容，并给出1-2条参考建议。输出300字以内。",
    "content_ops": "你是游戏内容运营专家，请从内容亮点、内容矩阵、叙事节奏、二创生态和内容分发角度分析版本公告。若信息不足，请明确说明缺乏内容运营相关内容，并给出1-2条参考建议。输出300字以内。",
    "version_ops": "你是游戏版本运营专家，请从版本节奏、内容量级、上线流程、技术风险和回滚预案角度分析版本公告。若信息不足，请明确说明缺乏版本运营相关内容，并给出1-2条参考建议。输出300字以内。",
    "monetization_ops": "你是游戏商业化运营专家，请从付费设计、商业化节奏、ARPU、付费转化和收入增长角度分析版本公告。若信息不足，请明确说明缺乏商业化运营相关内容，并给出1-2条参考建议。输出300字以内。",
}


def load_yaml_config(config_path: str | Path) -> dict[str, Any] | None:
    """Read a YAML config file and return a dictionary; return None on missing or invalid files."""
    file_path = Path(config_path)
    if not file_path.is_absolute():
        file_path = PROJECT_DIR / file_path
    if not file_path.exists():
        return None

    try:
        import yaml

        loaded = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None

    return loaded if isinstance(loaded, dict) else None


def translate_agent_config_to_prompt(agent_config: dict[str, Any]) -> str:
    """Translate structured YAML role config into a natural-language system prompt."""
    framework_items = agent_config.get("analysis_framework") or []
    if isinstance(framework_items, list):
        analysis_framework = "\n".join(f"- {item}" for item in framework_items)
    else:
        analysis_framework = str(framework_items)

    terminology_items = agent_config.get("terminology") or []
    if isinstance(terminology_items, list):
        terminology = "、".join(str(item) for item in terminology_items)
    else:
        terminology = str(terminology_items)

    deterministic_rule_items = agent_config.get("deterministic_rules") or []
    deterministic_rules_section = ""
    if isinstance(deterministic_rule_items, list) and deterministic_rule_items:
        deterministic_rules = "\n".join(f"- {item}" for item in deterministic_rule_items)
        deterministic_rules_section = (
            "\n\n### 前置确定性规则\n"
            "在开始分析前，先执行以下确定性规则。这些规则不需要调用LLM推理，"
            f"直接采用规则中的输出内容：\n{deterministic_rules}"
        )

    return AGENT_PROMPT_TEMPLATE.format(
        role_name=agent_config.get("role_name", ""),
        core_responsibility=agent_config.get("core_responsibility", ""),
        analysis_framework=analysis_framework,
        style=agent_config.get("style", ""),
        terminology=terminology,
        output_limit=agent_config.get("output_limit", ""),
        deterministic_rules_section=deterministic_rules_section,
        boundary_rule_template=agent_config.get("boundary_rule_template", ""),
    ).strip()


def get_agent_prompt(agent_id: str) -> str:
    """Load config/agents/{agent_id}.yaml and translate it to a model-ready prompt."""
    config_path = PROJECT_DIR / "config" / "agents" / f"{agent_id}.yaml"
    agent_config = load_yaml_config(config_path)
    if agent_config:
        prompt = translate_agent_config_to_prompt(agent_config)
        if prompt:
            return prompt
    return DEFAULT_AGENT_PROMPTS.get(agent_id, "你是游戏运营分析助手，请基于用户提供的内容给出简洁、具体、可执行的分析建议。")


def get_prompt_config_path(prompt_id: str) -> Path:
    """Resolve a prompt YAML path under config/prompts/."""
    normalized_id = prompt_id.strip().strip("/").replace("\\", "/")
    return PROJECT_DIR / "config" / "prompts" / f"{normalized_id}.yaml"


def translate_prompt_config_to_prompt(prompt_config: dict[str, Any]) -> str:
    """Translate a YAML prompt config into the natural-language prompt sent to the model."""
    for key in ("prompt", "system_prompt", "content"):
        value = prompt_config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    parts: list[str] = []
    for key in ("role", "goal", "rules", "output_format", "data_source_declaration"):
        value = prompt_config.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
        elif isinstance(value, list):
            parts.extend(str(item).strip() for item in value if str(item).strip())
    return "\n\n".join(parts).strip()


def get_system_prompt(prompt_id: str, default_prompt: str = "") -> str:
    """Load a system prompt only from config/prompts/*.yaml; fall back to code defaults."""
    prompt_config = load_yaml_config(get_prompt_config_path(prompt_id))
    if prompt_config:
        prompt = translate_prompt_config_to_prompt(prompt_config)
        if prompt:
            return prompt
    return default_prompt or DEFAULT_SYSTEM_PROMPTS.get(prompt_id, DEFAULT_SYSTEM_PROMPTS["prompt_background"])
