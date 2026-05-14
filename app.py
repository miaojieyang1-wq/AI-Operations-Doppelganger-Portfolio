import base64
import contextlib
import io
import json
import os
import platform
import re
import subprocess
import sys
import time
import zipfile
import html
from datetime import datetime
from functools import lru_cache
from importlib import metadata as importlib_metadata
from pathlib import Path
from xml.etree import ElementTree

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

import prompt_loader
import rag_engine
import demo_engine
import api_runtime
from collaboration_config import COLLABORATION_GOALS, COLLABORATION_ROLES
import report_utils
import ui_components
import style_assets
import config_loader
import runtime_paths
import security_utils
from core import Orchestrator


runtime_paths.load_runtime_env()
load_dotenv(override=False)
ORIGINAL_API_ENV = {
    "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY", ""),
    "DEEPSEEK_BASE_URL": os.getenv("DEEPSEEK_BASE_URL", ""),
    "DEEPSEEK_MODEL": os.getenv("DEEPSEEK_MODEL", ""),
}

APP_CONFIG = config_loader.load_app_config()
PROJECT_DIR = config_loader.PROJECT_DIR
WORKS_DIR = config_loader.config_path(APP_CONFIG, "works")
REPORT_DIR = config_loader.config_path(APP_CONFIG, "reports")
JSON_REPORT_DIR = REPORT_DIR / "json"
COLLABORATION_REPORT_DIR = config_loader.config_path(APP_CONFIG, "collaboration_reports")
ACTIVITY_PLAN_DIR = config_loader.config_path(APP_CONFIG, "activity_plans")
STATIC_DIR = config_loader.config_path(APP_CONFIG, "static")
ENTRY_IMAGE = config_loader.config_path(APP_CONFIG, "entry_image")
ENTRY_IMAGE_FAST = config_loader.config_path(APP_CONFIG, "entry_image_fast")
DEFAULT_MODEL = api_runtime.DEFAULT_MODEL
DEFAULT_BASE_URL = api_runtime.DEFAULT_BASE_URL
DEFAULT_TEMPERATURE = float(APP_CONFIG["model"]["default_temperature"])
ENABLE_LOCAL_SAVE = os.getenv("AI_OPS_ENABLE_LOCAL_SAVE", "1").strip() != "0"
ENABLE_JSON_SIDECAR = os.getenv("AI_OPS_SAVE_JSON_SIDECAR", "1").strip() != "0"
COLLABORATION_ROLE_TEMPERATURE = float(APP_CONFIG["model"]["collaboration_role_temperature"])
COLLABORATION_COORDINATOR_TEMPERATURE = float(APP_CONFIG["model"]["collaboration_coordinator_temperature"])
ORCHESTRATOR = Orchestrator(
    default_temperature=DEFAULT_TEMPERATURE,
    role_temperature=COLLABORATION_ROLE_TEMPERATURE,
    coordinator_temperature=COLLABORATION_COORDINATOR_TEMPERATURE,
)
DOCX_HEADING_STYLE_RE = re.compile(r"heading(\d+)")
OUTLINE_MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
OUTLINE_SECTION_RE = re.compile(r"^([一二三四五六七八九十]+、|[0-9]+[.、])\s*(.{2,70})$")
DISTRIBUTION_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
DISTRIBUTION_COUNT_RE = re.compile(r"(\d+)\s*(?:条|次|个)")
REPORT_HEADING_RE = re.compile(r"^#{1,4}\s+(.+)$")
REPORT_NUMBERED_RE = re.compile(r"^(\d+[.、]\s*[^：:]{2,24})[：:]?\s*(.*)$")
LATEX_BLOCK_RE = re.compile(
    r"(\$\$\$LATEX_START\$\$\$.*?\$\$\$LATEX_END\$\$\$|\\\[(?:.|\n)*?\\\]|\\\((?:.|\n)*?\\\)|\\boxed\{(?:[^{}]|\{[^{}]*\})*\})",
    re.DOTALL,
)
LATEX_MARKER_RE = re.compile(r"^\$\$\$LATEX_START\$\$\$(.*?)\$\$\$LATEX_END\$\$\$$", re.DOTALL)
KATEX_CSS_URL = "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css"
KATEX_JS_URL = "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"
KATEX_AUTO_RENDER_URL = "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
AI_KNOWLEDGE_NOTICE = "基于AI模型内嵌知识，建议在使用前与官方公告核对"
DATA_SOURCE_WARNING_TEXT = "⚠️ 本分析基于 AI 模型内嵌知识与您提供的数据生成，未经过实时数据校验。部分判断可能存在偏差或与实际情况不符，建议在使用前与官方公告、真实用户反馈或实时数据进行交叉验证。"
DATA_SOURCE_DECLARATION_FALLBACK = "## ⚠️ 数据源声明\n本报告由 AI 运营分身自动生成。分析依据为用户提供的输入数据与 AI 模型内嵌知识。以下判断缺乏实时数据验证：报告中涉及效果预判、市场环境、竞品影响、用户行为趋势和执行结果的判断。建议在使用前通过官方数据源、用户调研或A/B测试进行验证。"
RISK_WARNING_BY_SOURCE = {
    "competitor": "当前竞品分析未接入实时数据源，竞品版本信息可能不是最新。建议手动核对竞品官方公告后使用。",
    "version": "版本卖点提炼和效果预判基于历史运营规律和AI推理，实际效果可能因市场环境变化而偏离预判。",
    "feedback": "反馈分析完全基于您提供的样本数据，分析结论的准确性取决于样本的代表性和完整性。",
    "survey": "问卷设计基于通用的调研方法论，建议根据实际投放平台和用户画像进行二次调整。",
    "interview": "访谈提纲基于通用的用户研究方法论生成，建议根据实际访谈场景和对象特征进行调整。",
    "activity": "活动方案基于运营方法论和AI推理生成，数值设计仅供参考，实际执行前建议进行小规模灰度测试。",
    "comment": "视频舆情分析基于您提供的评论样本与AI推理生成，建议结合平台后台数据、评论时间分布和真实互动数据验证。",
    "collaboration": "多职能协作结论由多个AI角色基于同一份输入独立生成后汇总，建议在正式决策前与真实业务数据、团队评审和官方公告交叉验证。",
}




WORKFLOWS = {
    "dashboard": {
        "label": "决策看板",
        "description": "从研发期到长线运营，按生命周期进入对应运营工作台。",
    },
    "personal": {
        "label": "个人运营分身",
        "description": "用你的背景、经历和表达方式回答问题，适合作品集自我介绍与面试准备。",
    },
    "version": {
        "label": "版本决策",
        "description": "分析自家版本内容，并用竞品雷达辅助判断宣发与运营策略。",
    },
    "feedback": {
        "label": "整理玩家反馈",
        "description": "你可以粘贴玩家评论、客服反馈或社区舆情，我会帮你判断问题类型和处理优先级。",
    },
    "bilingual": {
        "label": "中日双语宣发",
        "description": "把版本亮点或活动信息改写成中文与日文平台文案。",
    },
    "prompt": {
        "label": "优化工作指令",
        "description": "你可以粘贴一段粗略需求，我会帮你整理成更清晰、可复用、可测试的工作指令。",
    },
    "insight": {
        "label": "用户洞察",
        "description": "围绕访谈、问卷和反馈清洗，快速搭建玩家研究工作流。",
    },
    "activity": {
        "label": "活动策划",
        "description": "根据活动目标和版本背景，生成可落地的活动方案。",
    },
    "competitor": {
        "label": "竞品雷达",
        "description": "对比竞品版本动作，判断可借鉴策略和潜在风险。",
    },
}

WORK_TEST_KEYS = ["version", "feedback", "bilingual", "prompt"]

PORTFOLIO_CONTEXT = """
作品集完整文档存放在 works/ 文件夹。

一、SEO提示词工程（核心作品）
1. 迭代记录
- 文件：works/iteration-history.md
- 内容：从V0到V4的完整迭代历程，包含每次迭代的诊断、改进措施和验证要点
- 证明能力：提示词工程的系统化迭代能力、问题诊断与优化思维
- 关键迭代节点：V0（需求堆砌）→ V1（四层缝合+过渡段论证）→ V1.5（多场景分支）→ V2（结构化压缩）→ V3（模块化体系）→ V4（分阶段渐进式加载）

2. 工程本体
- 文件：works/prompt-engineering.md
- 内容：V4最终版是“渐进约束模式提示词”，通过分阶段加载任务目标、范文分析、结构控制、功能介绍、过渡段论证、叙事外壳和最终自检，减少长提示词带来的注意力稀释
- 证明能力：提示词工程的设计与落地能力、AI内容生产管线的搭建能力，以及通过分阶段约束提升模型遵从率的工程优化能力
- 重要口径：V3 才是模块化体系，V4 最终版是分阶段渐进式加载 / 渐进约束模式

二、SEO文章合集（工程产出验证）
- 文件夹：works/articles/
- 内容：使用该提示词工程生成并已发布的英文SEO文章，共十余篇，涵盖情感向推广软文、横向对比评测文章、深度教程文章、产品功能推荐文章
- 证明能力：该工程在不同场景下的稳定产出能力

三、能力验证闭环
1. 迭代记录 → 证明“我能持续优化AI系统”
2. 工程本体 → 证明“我能设计可复用的AI生产管线”
3. 文章成品 → 证明“这套管线确实能稳定产出高质量内容”

对话展示规则：
当被问到作品集时，先输出三层结构的摘要概览，再询问对方想深入了解哪一部分。
当被问到提示词工程时，先提取核心方法论（四层缝合、过渡段决策论证、禁令体系等），再补充关键迭代节点，必要时引用文章作为产出案例。
如果对方要求展开完整文档，再从对应文件中展示完整内容。
"""


def read_system_prompt() -> str:
    return config_loader.get_system_prompt("prompt_background")


@lru_cache(maxsize=1)
def read_system_prompt_by_signature(file_path_text: str, file_mtime_ns: int, file_size: int) -> str:
    """兼容旧调用；运行时系统提示词只从 YAML 配置读取。"""
    return config_loader.get_system_prompt("prompt_background")


def read_prompt_file(prompt_id: str, fallback_prompt: str) -> str:
    """读取指定功能的 YAML 系统提示词；失败时使用代码内置兜底提示。"""
    return config_loader.get_system_prompt(prompt_id, fallback_prompt)


@lru_cache(maxsize=32)
def read_prompt_file_by_signature(
    prompt_path_text: str,
    file_mtime_ns: int,
    file_size: int,
    fallback_prompt: str,
) -> str:
    """兼容旧调用；txt prompt 文件不再作为运行时数据源。"""
    return fallback_prompt


def get_collaboration_role_by_name(role_name: str) -> dict | None:
    """根据角色名称读取协作角色配置。"""
    return get_collaboration_role_map().get(role_name)


@lru_cache(maxsize=1)
def get_collaboration_role_map() -> dict[str, dict]:
    """缓存协作角色名称索引，避免多选角色反复线性查找。"""
    return {role["name"]: role for role in COLLABORATION_ROLES}


@lru_cache(maxsize=1)
def get_collaboration_role_names() -> list[str]:
    """缓存协作角色名称列表，供多选框复用。"""
    return [role["name"] for role in COLLABORATION_ROLES]


@lru_cache(maxsize=1)
def get_collaboration_role_order() -> dict[str, int]:
    """缓存协作角色展示顺序，避免每次排序前重建映射。"""
    return {role["key"]: index for index, role in enumerate(COLLABORATION_ROLES)}


def build_role_user_content(announcement: str, goal: str) -> str:
    """构造单个协作角色的用户输入内容。"""
    return ORCHESTRATOR.build_role_user_content(announcement, goal)

def call_collaboration_role(role: dict, announcement: str, goal: str) -> dict:
    """调用单个协作角色，不影响其他角色。"""
    return ORCHESTRATOR.run_collaboration_role(role, announcement, goal)

def build_coordinator_prompt() -> str:
    """读取协作讨论协调者提示词。"""
    return ORCHESTRATOR.build_coordinator_prompt()

def build_coordinator_user_content(role_results: list[dict], goal: str) -> str:
    """拼接所有角色观点，供协调者综合。"""
    return ORCHESTRATOR.build_coordinator_user_content(role_results, goal)

def build_collaboration_markdown(role_results: list[dict], coordinator_result: str, goal: str) -> str:
    """生成用于保存的协作讨论完整报告。"""
    lines = [
        "# 多职能协作讨论报告",
        f"本次使用的运营目标：{goal if goal != '无特定目标（综合评估）' else '综合评估'}",
        "",
        "## 各职能角色观点",
    ]
    for item in role_results:
        role = item["role"]
        suffix = "（视角建议）" if item.get("is_suggestion") else ""
        if not item.get("success"):
            suffix = "（生成失败）"
        lines.extend(
            [
                "",
                f"### {role['emoji']} {role['name']}{suffix}",
                item.get("content", "").strip() or "该视角分析生成失败",
            ]
        )
    lines.extend(["", f"## ⚖️ 协调者综合建议（目标：{goal}）", coordinator_result.strip()])
    return "\n".join(lines)


def infer_report_risk_level(report_text: str) -> str:
    """Infer a coarse risk level for the JSON sidecar without blocking report save."""
    text = report_text.lower()
    high_keywords = ["高风险", "严重", "紧急", "危机", "舆情", "回滚", "大量流失", "攻击性"]
    medium_keywords = ["中风险", "风险", "预警", "争议", "负面", "异常", "波动"]
    low_keywords = ["低风险", "轻微", "关注", "观察"]
    for keyword in high_keywords:
        if keyword in report_text or keyword in text:
            return "高"
    for keyword in medium_keywords:
        if keyword in report_text or keyword in text:
            return "中"
    for keyword in low_keywords:
        if keyword in report_text or keyword in text:
            return "低"
    return "无"


def extract_report_json_payload(
    report_text: str,
    report_type: str,
    extra_payload: dict | None = None,
) -> dict:
    """Create a stable JSON summary for saved reports; failure is handled by the caller."""
    clean_lines = []
    for line in report_text.splitlines():
        line = line.strip()
        if not line:
            continue
        clean_line = re.sub(r"^[#*\-\d.、\s]+", "", line).strip()
        if clean_line:
            clean_lines.append(clean_line)

    action_items = [
        line for line in clean_lines
        if any(keyword in line for keyword in ["建议", "行动", "处理", "优化", "复盘", "关注", "优先"])
    ][:10]
    payload = {
        "report_type": report_type,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "key_findings": clean_lines[:10],
        "metrics": {
            "word_count": len(report_text),
            "line_count": len(clean_lines),
            "action_item_count": len(action_items),
        },
        "risk_level": infer_report_risk_level(report_text),
        "action_items": action_items,
        "data_confidence": "由应用根据 Markdown 报告自动整理；建议结合原始输入、官方公告和真实数据复核。",
    }
    if extra_payload:
        payload.update(extra_payload)
    return payload


def save_report_json(
    report_path: Path,
    report_text: str,
    report_type: str,
    extra_payload: dict | None = None,
) -> Path | None:
    """Save a JSON sidecar into reports/json/; never interrupt the main Markdown save."""
    if not ENABLE_JSON_SIDECAR:
        return None
    try:
        JSON_REPORT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = JSON_REPORT_DIR / f"{report_path.stem}.json"
        payload = extract_report_json_payload(report_text, report_type, extra_payload)
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return json_path
    except Exception:
        return None


def build_collaboration_json_payload(role_results: list[dict], coordinator_result: str, goal: str) -> dict:
    """Build collaboration-specific fields for the JSON sidecar."""
    role_summaries = {}
    participant_roles = []
    for item in role_results:
        role = item.get("role", {})
        role_name = role.get("name", "")
        if role_name:
            participant_roles.append(role_name)
            content = item.get("content", "").strip()
            role_summaries[role_name] = content[:240] if content else "该视角分析生成失败"
    return {
        "participants": participant_roles,
        "operation_goal": goal,
        "role_summaries": role_summaries,
        "coordinator_summary": coordinator_result.strip(),
    }


def save_collaboration_report(
    report_text: str,
    goal: str,
    role_results: list[dict] | None = None,
    coordinator_result: str = "",
) -> Path:
    """保存协作讨论报告到 reports/collaboration/。"""
    if not ENABLE_LOCAL_SAVE:
        raise RuntimeError("本地保存已关闭，请在配置中开启 AI_OPS_ENABLE_LOCAL_SAVE 后再保存。")
    COLLABORATION_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_goal = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", goal if goal != "无特定目标（综合评估）" else "综合评估")
    report_path = COLLABORATION_REPORT_DIR / f"协作报告_{safe_goal}_{timestamp}.md"
    report_path.write_text(report_text, encoding="utf-8")
    extra_payload = build_collaboration_json_payload(role_results or [], coordinator_result, goal)
    save_report_json(report_path, report_text, "collaboration", extra_payload)
    return report_path


def get_prompt_signature() -> int:
    try:
        return config_loader.get_prompt_config_path("prompt_background").stat().st_mtime_ns
    except FileNotFoundError:
        return 0


def sync_session_api_config_to_env() -> None:
    """把网页中填写的 API 配置同步到当前会话环境，供 app / LangGraph / RAG 共用。"""
    api_key = st.session_state.get("user_api_key", "").strip()
    base_url = st.session_state.get("user_api_base_url", "").strip()
    model_name = st.session_state.get("user_api_model", "").strip()

    if api_key:
        os.environ["DEEPSEEK_API_KEY"] = api_key
    if base_url:
        os.environ["DEEPSEEK_BASE_URL"] = base_url.rstrip("/")
    if model_name:
        os.environ["DEEPSEEK_MODEL"] = model_name


def get_effective_api_config() -> dict[str, str]:
    """读取当前实际会使用的 API 配置，优先使用网页会话内配置。"""
    sync_session_api_config_to_env()
    return ORCHESTRATOR.get_api_config()


def mask_api_key(api_key: str) -> str:
    """隐藏密钥中间部分，只用于状态展示。"""
    if not api_key:
        return "未配置"
    if len(api_key) <= 10:
        return f"{api_key[:2]}***"
    return f"{api_key[:6]}***{api_key[-4:]}"


def ensure_default_config_files() -> bool:
    """缺少关键配置时自动生成 config/app.yaml。"""
    generated = False
    config_dir = PROJECT_DIR / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    app_config_file = config_dir / "app.yaml"
    if not app_config_file.exists():
        try:
            import yaml

            app_config_file.write_text(
                yaml.safe_dump(config_loader.DEFAULT_APP_CONFIG, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        except Exception:
            app_config_file.write_text(
                json.dumps(config_loader.DEFAULT_APP_CONFIG, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        generated = True
    return generated


def write_env_api_key(api_key: str) -> None:
    """将 API Key 写入 .env。"""
    env_file = runtime_paths.RUNTIME_ENV_FILE
    runtime_paths.ensure_runtime_dirs()
    existing_lines = []
    if env_file.exists():
        existing_lines = [
            line
            for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines()
            if not line.startswith("DEEPSEEK_API_KEY=")
        ]
    existing_lines.append(f"DEEPSEEK_API_KEY={api_key}")
    env_file.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")
    os.environ["DEEPSEEK_API_KEY"] = api_key


def has_available_model_access() -> bool:
    """检查当前会话是否具备模型调用条件：有 API Key 或已开启演示模式。"""
    runtime_paths.load_runtime_env()
    session_api_key = str(st.session_state.get("user_api_key", "")).strip()
    env_api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    return bool(session_api_key or env_api_key or os.getenv("AI_OPS_DEMO_MODE") == "1")


def build_personal_local_fallback(user_content: str) -> str:
    """了解我模式的本地兜底回答；API 不可用时保证页面仍能输出内容。"""
    demo_response = demo_engine.get_demo_response("了解我 作品集 实习 提示词工程 游戏理解", user_content)
    if demo_response and "当前问题没有命中具体场景" not in demo_response:
        return demo_response
    return (
        "我现在暂时没有连接到可用的模型接口，所以先用本地兜底模式回答。\n\n"
        "您可以继续在“了解我”里查看作品集、实习经历、游戏理解、活动策划经历和 Agent 设计思路。"
        "如果希望我生成更贴合具体问题的自然语言回答，请在侧边栏或首次配置页填写可用的 DeepSeek API Key，"
        "也可以开启演示模式进行稳定展示。"
    )


def render_first_use_config_page() -> None:
    """首次使用时配置 API Key，也允许直接进入演示模式。"""
    setup_page()
    st.markdown('<div class="section-title">首次使用配置</div>', unsafe_allow_html=True)
    if st.session_state.pop("default_config_generated", False):
        st.success("已自动生成默认配置文件，可在 config/ 文件夹中修改。")
    st.info("如果您有 DeepSeek API Key，可以在这里填写并保存；如果只是想先体验功能，也可以直接进入演示模式。")
    api_key = st.text_input("DeepSeek API Key", type="password", placeholder="请输入 sk- 开头的 API Key")
    col_save, col_demo = st.columns(2)
    with col_save:
        save_clicked = st.button("保存并进入应用", type="primary", use_container_width=True)
    with col_demo:
        demo_clicked = st.button("跳过配置，进入演示模式", use_container_width=True)

    if save_clicked:
        if not api_key.strip().startswith("sk-"):
            st.warning("API Key 格式看起来不正确，请确认它以 sk- 开头。")
            return
        write_env_api_key(api_key.strip())
        st.success("配置已保存，正在进入应用。")
        st.rerun()

    if demo_clicked:
        st.session_state.demo_mode = True
        st.session_state.skip_first_use_config = True
        os.environ["AI_OPS_DEMO_MODE"] = "1"
        st.success("已进入演示模式。本次会话会读取本地预设结果，不需要实时调用 API。")
        st.rerun()


def test_deepseek_connection(api_key: str, base_url: str, model_name: str) -> tuple[bool, str]:
    """用用户填写的配置发起一次极短连接测试。"""
    return ORCHESTRATOR.test_connection(api_key, base_url, model_name)


def create_deepseek_client():
    sync_session_api_config_to_env()
    return ORCHESTRATOR.create_client()


def run_agent_graph(agent_input: str, messages: list[dict[str, str]] | None = None) -> tuple[str, str]:
    """通过 core.Orchestrator 调用 LangGraph 聊天流程。"""
    result = ORCHESTRATOR.run_chat(agent_input, session_id="streamlit", messages=messages)
    if not result.get("success"):
        raise RuntimeError(result.get("error") or "LangGraph 调用失败")
    return result.get("content", ""), result.get("intent", "")

def run_agent_task(task_key: str, user_content: str, system_prompt: str = "") -> str:
    """通过 core.Orchestrator 调用 LangGraph 指定任务。"""
    result = ORCHESTRATOR.run_task(task_key, user_content, system_prompt)
    if not result.get("success"):
        raise RuntimeError(result.get("error") or f"{task_key} 调用失败")
    return result.get("content", "")

def get_agent_last_intent() -> str:
    """读取最近一次意图；未加载 LangGraph 时返回空值。"""
    if "agent_graph" not in sys.modules:
        return ""
    from agent_graph import get_last_intent

    return get_last_intent()


def get_agent_last_prompt_modules() -> list[str]:
    """读取最近一次 Prompt 模块；未加载 LangGraph 时不触发额外导入。"""
    if "agent_graph" not in sys.modules:
        return []
    from agent_graph import get_last_prompt_modules

    return get_last_prompt_modules()


def call_deepseek_api(messages: list[dict[str, str]], temperature: float | None = None) -> str:
    sync_session_api_config_to_env()
    return ORCHESTRATOR.call_chat_completion(messages, temperature=temperature)

def call_deepseek_with_system_prompt(system_prompt: str, user_content: str, temperature: float | None = None) -> str:
    """通过 core.Orchestrator 调用模型接口。"""
    sync_session_api_config_to_env()
    return ORCHESTRATOR.call_with_system_prompt(system_prompt, user_content, temperature=temperature)

def save_report(report_text: str, workflow_key: str, report_dir: Path | None = None) -> Path:
    if not ENABLE_LOCAL_SAVE:
        raise RuntimeError("本地保存已关闭，请在配置中开启 AI_OPS_ENABLE_LOCAL_SAVE 后再保存。")
    target_dir = report_dir or REPORT_DIR
    workflow_name = WORKFLOWS.get(workflow_key, WORKFLOWS["personal"])["label"]
    report_path = report_utils.write_timestamped_report(report_text, target_dir, workflow_name)
    save_report_json(report_path, report_text, workflow_key)
    return report_path


def append_ai_knowledge_notice(report_text: str) -> str:
    """在报告末尾追加 AI 知识核对提示。"""
    return report_utils.append_once(report_text, AI_KNOWLEDGE_NOTICE, AI_KNOWLEDGE_NOTICE)


def ensure_data_source_declaration(report_text: str) -> str:
    """确保报告末尾包含数据源声明。"""
    clean_report = report_text.strip()
    if "数据源声明" in clean_report or "所有分析基于用户提供的数据" in clean_report:
        return clean_report
    return report_utils.append_once(report_text, DATA_SOURCE_DECLARATION_FALLBACK[:12], DATA_SOURCE_DECLARATION_FALLBACK)


def is_data_source_warning_enabled() -> bool:
    """读取全局数据源真实性预警开关，默认开启。"""
    return bool(st.session_state.get("data_source_warning_enabled", True))


def get_risk_warning(source_type: str) -> str:
    """根据分析功能类型返回更具体的风险提示。"""
    return RISK_WARNING_BY_SOURCE.get(source_type, "")


def render_data_source_config() -> None:
    """改动位置：页面顶部统一配置数据源真实性预警。"""
    if "data_source_warning_enabled" not in st.session_state:
        st.session_state.data_source_warning_enabled = True
    st.toggle(
        "⚠️ 数据源真实性预警（默认开启）",
        key="data_source_warning_enabled",
        help="开启后，分析报告顶部会显示数据源真实性提醒；关闭后，新生成报告不再显示顶部横幅，但报告末尾的数据源声明仍会保留。",
    )


def render_first_analysis_notice(source_type: str) -> None:
    """改动位置：首次使用分析功能时展示一次性说明。"""
    notice_key = "analysis_first_use_notice_acknowledged"
    if st.session_state.get(notice_key):
        return
    st.info("提示：这是您首次使用本分析功能。所有分析结果均基于 AI 推理生成，建议在决策前通过官方数据和用户反馈进行验证。此提示本次会话不再显示。")
    if st.button("知道了", key=f"ack_analysis_notice_{source_type}"):
        st.session_state[notice_key] = True
        st.rerun()


def render_data_source_warning(source_type: str) -> None:
    """改动位置：在分析报告顶部展示统一数据源真实性预警。"""
    st.warning(DATA_SOURCE_WARNING_TEXT)
    risk_warning = get_risk_warning(source_type)
    if risk_warning:
        st.caption(f"风险提示：{risk_warning}")


def render_prompt_feature_guide(title: str, items: list[str], tip: str = "") -> None:
    """在输入区上方展示本功能已打磨的 Prompt 能力，引导用户把关键信息填完整。"""
    chips = "".join(
        (
            '<span style="display:inline-flex;align-items:center;border:1px solid #ccfbf1;'
            'border-radius:999px;background:#f0fdfa;color:#134e4a;font-size:0.82rem;'
            'line-height:1.3;padding:0.32rem 0.62rem;">'
            f"{html.escape(item)}</span>"
        )
        for item in items
    )
    tip_html = (
        f'<div style="color:#667085;font-size:0.86rem;line-height:1.6;margin-top:0.55rem;">{html.escape(tip)}</div>'
        if tip
        else ""
    )
    st.markdown(
        f"""
        <div style="border:1px solid #d7e5e1;border-radius:8px;background:#fbfefd;padding:0.85rem 0.95rem;margin:0.75rem 0 0.95rem;">
            <div style="color:#134e4a;font-size:0.92rem;font-weight:760;margin-bottom:0.55rem;">{html.escape(title)}</div>
            <div style="display:flex;flex-wrap:wrap;gap:0.45rem;">{chips}</div>
            {tip_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def mark_result_ready() -> None:
    """标记结果已生成，提示页面滚动到结果区域。"""
    ui_components.mark_result_ready()


def render_result_anchor() -> None:
    """渲染结果定位锚点，便于用户找到输出区域。"""
    ui_components.render_result_anchor()


def build_report_warning_block(source_type: str) -> str:
    """用于保存到文件的预警文本。"""
    risk_warning = get_risk_warning(source_type)
    if risk_warning:
        return f"{DATA_SOURCE_WARNING_TEXT}\n\n风险提示：{risk_warning}"
    return DATA_SOURCE_WARNING_TEXT


def prepare_analysis_report_for_save(report_text: str, source_type: str, include_warning: bool) -> str:
    """改动位置：保存/导出报告时按开关联动写入预警，并始终保留数据源声明。"""
    report_with_declaration = ensure_data_source_declaration(report_text)
    if include_warning:
        return f"{build_report_warning_block(source_type)}\n\n---\n\n{report_with_declaration}"
    return report_with_declaration


def infer_analysis_source_type(result_key: str) -> str:
    """根据结果状态键推断分析功能类型。"""
    mapping = {
        "interview_result": "interview",
        "survey_result": "survey",
        "clean_result": "feedback",
        "version_analysis_result": "version",
        "competitor_result": "competitor",
        "activity_plan_result": "activity",
        "comment_analysis_result": "comment",
        "collaboration_result": "collaboration",
    }
    return mapping.get(result_key, "version")


def render_katex_loader() -> None:
    """页面级加载 KaTeX 资源；具体公式块仍会自带兜底渲染，避免 Streamlit iframe 隔离失效。"""
    components.html(
        f"""
        <link rel="stylesheet" href="{KATEX_CSS_URL}">
        <script defer src="{KATEX_JS_URL}"></script>
        <script defer src="{KATEX_AUTO_RENDER_URL}"></script>
        <script>
        window.addEventListener("load", function() {{
            if (window.renderMathInElement) {{
                document.querySelectorAll(".math-render").forEach(function(element) {{
                    renderMathInElement(element, {{
                        delimiters: [
                            {{left: "\\\\[", right: "\\\\]", display: true}},
                            {{left: "\\\\(", right: "\\\\)", display: false}},
                            {{left: "$$", right: "$$", display: true}}
                        ],
                        throwOnError: false
                    }});
                }});
            }}
        }});
        </script>
        """,
        height=0,
    )


def normalize_latex_segment(segment: str) -> str:
    """把自定义公式分隔符和裸 boxed 公式整理成 KaTeX 可识别的 LaTeX。"""
    marker_match = LATEX_MARKER_RE.match(segment.strip())
    if marker_match:
        return normalize_bare_boxed_lines(marker_match.group(1).strip())
    stripped = segment.strip()
    if stripped.startswith(r"\boxed"):
        return rf"\[{stripped}\]"
    return stripped


def normalize_bare_boxed_lines(latex_code: str) -> str:
    """把单独成行的 \boxed{...} 包成块级公式，保留已包裹的公式不动。"""
    normalized_lines: list[str] = []
    for line in latex_code.splitlines():
        stripped = line.strip()
        if stripped.startswith(r"\boxed") and not (stripped.startswith(r"\[") or stripped.startswith(r"\(")):
            normalized_lines.append(rf"\[{stripped}\]")
        else:
            normalized_lines.append(line)
    return "\n".join(normalized_lines)


def split_markdown_and_math(text: str) -> list[tuple[str, str]]:
    """把 Markdown 文本拆成普通文本片段和 LaTeX 片段。"""
    if not text:
        return []

    pieces: list[tuple[str, str]] = []
    cursor = 0
    for match in LATEX_BLOCK_RE.finditer(text):
        if match.start() > cursor:
            pieces.append(("markdown", text[cursor : match.start()]))
        pieces.append(("math", normalize_latex_segment(match.group(0))))
        cursor = match.end()
    if cursor < len(text):
        pieces.append(("markdown", text[cursor:]))
    return pieces


def render_math_segment(latex_code: str) -> None:
    """使用 KaTeX 渲染单段公式；每段自带资源引用，保证在 Streamlit 组件 iframe 内可用。"""
    escaped_latex = html.escape(latex_code)
    estimated_height = min(520, max(72, 42 + 24 * max(1, latex_code.count("\n") + latex_code.count(r"\\") + 1)))
    components.html(
        f"""
        <link rel="stylesheet" href="{KATEX_CSS_URL}">
        <div class="math-render" style="font-size:1rem;line-height:1.75;color:#111827;overflow-x:auto;padding:0.35rem 0;">
        {escaped_latex}
        </div>
        <script src="{KATEX_JS_URL}"></script>
        <script src="{KATEX_AUTO_RENDER_URL}"></script>
        <script>
        const mathRoot = document.querySelector(".math-render");
        if (window.renderMathInElement && mathRoot) {{
            renderMathInElement(mathRoot, {{
                delimiters: [
                    {{left: "\\\\[", right: "\\\\]", display: true}},
                    {{left: "\\\\(", right: "\\\\)", display: false}},
                    {{left: "$$", right: "$$", display: true}}
                ],
                throwOnError: false
            }});
        }}
        </script>
        """,
        height=estimated_height,
        scrolling=True,
    )


def render_markdown_with_math(text: str) -> None:
    """展示包含 Markdown 与 LaTeX 的回答；纯文本走 Markdown，公式走 KaTeX。"""
    pieces = split_markdown_and_math(text)
    if not pieces:
        return
    for piece_type, content in pieces:
        if piece_type == "math":
            render_math_segment(content)
        elif content.strip():
            st.markdown(content)


def setup_page() -> None:
    st.set_page_config(
        page_title=APP_CONFIG["app"]["page_title"],
        page_icon=APP_CONFIG["app"]["page_icon"],
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_katex_loader()
    style_assets.apply_main_styles()


def setup_entry_page() -> None:
    """只为首次弹窗加载最小页面配置，减少打开网页时的首屏等待。"""
    st.set_page_config(
        page_title=APP_CONFIG["app"]["page_title"],
        page_icon=APP_CONFIG["app"]["page_icon"],
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    render_katex_loader()
    style_assets.apply_entry_styles()


@lru_cache(maxsize=1)
def get_entry_image_data_url() -> str:
    """把弹窗压缩图缓存为内嵌图片，减少首屏图片组件处理。"""
    entry_image_path = ENTRY_IMAGE_FAST if ENTRY_IMAGE_FAST.exists() else ENTRY_IMAGE
    if not entry_image_path.exists():
        return ""
    mime_type = "image/webp" if entry_image_path.suffix.lower() == ".webp" else "image/png"
    encoded_image = base64.b64encode(entry_image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded_image}"


def render_footer() -> None:
    st.markdown(
        '<div class="footer-note">由oz搭建 · 基于DeepSeek API希望您聊的愉快❤</div>',
        unsafe_allow_html=True,
    )


@st.dialog(" ", width="large")
def render_entry_dialog() -> None:
    copy_col, image_col = st.columns([1.08, 0.92], gap="large", vertical_alignment="center")

    with copy_col:
        st.markdown(
            """
            <div class="entry-welcome-copy">
                <p>亲爱的米哈游HR老师您好呀！</p>
                <p>欢迎您来到我的作品集展示网站！</p>
                <p>接下来，我将在这个弹窗简短为您介绍该网站的架构灵感和具体框架：</p>
                <p>本网站整合了一个我的AI数字分身 agent，我的思路是调用 DeepSeek 的 API，并进行了三个客制化改造：接入 RAG、prompt 前提调试，以及使用 LangGraph 加入流程编排层。收到用户问题之后，它会先做意图识别，再检索本地知识库，最后根据意图类型选择不同的人设和提示词来生成回复，并且可以调用作品集的素材全部内容为您展示 🎈</p>
                <p>它包括两个模块：模拟面试与工作能力，并设置了五个不同的模式。您可以通过第一个模式了解我的各种相关信息，并使用其余四个模式进行简单的运营工作辅助处理。</p>
                <p>我的所有实际写作 SEO 与 blog 文章的作品集（均已发布在互联网上），以及精心准备的 prompt 工程文件与迭代内容，还有我的简历内容均已纳入了文件内容和数据当中啦。</p>
                <p>您可以向我的分身进行进一步对话，向它了解我的工作能力与工作经验！</p>
                <p>点击下方确认按钮，让我们开始今天的“面试”吧！</p>
                <p class="entry-ps">PS：特别鸣谢神悟树庭的阿纳克萨戈拉斯教授！🌿他为向救援树庭的开拓者一行人传递消息而搭建的忆质分身给予了本工程重要的灵感，让我们说：谢谢小夏老师~☺️</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        ready_top = st.button("准备好啦！", type="primary", use_container_width=True, key="entry_ready_top")
        if ready_top:
            st.session_state.entry_confirmed = True
            st.rerun()

    with image_col:
        st.markdown('<div class="entry-loading-note">若图片暂未显示，请您耐心等待片刻。</div>', unsafe_allow_html=True)
        entry_image_data_url = get_entry_image_data_url()
        if entry_image_data_url:
            st.markdown(
                f'<img class="entry-dialog-image" src="{entry_image_data_url}" alt="作品集欢迎图">',
                unsafe_allow_html=True,
            )


def require_entry_confirmation() -> None:
    if "entry_confirmed" not in st.session_state:
        st.session_state.entry_confirmed = False

    if not st.session_state.entry_confirmed:
        render_entry_dialog()
        st.stop()


def render_header() -> None:
    st.markdown(
        """
        <div class="hero-band">
            <div class="hero-eyebrow">AI OPERATIONS PORTFOLIO</div>
            <h1 class="app-title">你好，我是oz的 AI 运营分身</h1>
            <div class="app-subtitle">
            你可以像面试官一样快速了解我的经历，也可以给我一段游戏版本公告，看看我如何拆解卖点、判断传播风险并生成宣发建议。
            </div>
            <div class="hero-proof-row">
                <span class="hero-proof">AI音乐产品运营实习</span>
                <span class="hero-proof">SEO提示词工程</span>
                <span class="hero-proof">社会商业演出统筹</span>
                <span class="hero-proof">日语N1 · 音乐学背景</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_mode_context(workflow_key: str) -> None:
    dashboard_class = "mode-tile mode-tile-active" if workflow_key == "dashboard" else "mode-tile"
    about_class = "mode-tile mode-tile-active" if workflow_key == "personal" else "mode-tile"
    insight_class = "mode-tile mode-tile-active" if workflow_key == "insight" else "mode-tile"
    activity_class = "mode-tile mode-tile-active" if workflow_key == "activity" else "mode-tile"
    work_class = "mode-tile mode-tile-active" if workflow_key == "version" else "mode-tile"
    st.markdown(
        f"""
        <div class="mode-strip">
            <div class="{dashboard_class}">
                <div class="mode-label">🧭 决策看板</div>
                <div class="mode-desc">按运营生命周期进入对应工作台。</div>
            </div>
            <div class="{about_class}">
                <div class="mode-label">💬 面试预演</div>
                <div class="mode-desc">用预设问题快速查看经历、优势、作品集和提示词工程。</div>
            </div>
            <div class="{work_class}">
                <div class="mode-label">📊 版本决策</div>
                <div class="mode-desc">分析自家版本公告，并用竞品雷达辅助判断策略。</div>
            </div>
            <div class="{insight_class}">
                <div class="mode-label">🔎 用户洞察</div>
                <div class="mode-desc">生成访谈提纲、调研问卷，或清洗玩家反馈。</div>
            </div>
            <div class="{activity_class}">
                <div class="mode-label">🎯 活动策划</div>
                <div class="mode-desc">围绕目标、奖励和节奏，生成活动方案。</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def init_runtime_status() -> None:
    if "runtime_status" not in st.session_state:
        st.session_state.runtime_status = {
            "api_success": None,
            "duration": None,
            "timestamp": None,
            "error": "",
            "intent": "",
        }


def update_runtime_status(
    api_success: bool,
    duration: float | None = None,
    error: str = "",
    intent: str = "",
) -> None:
    st.session_state.runtime_status = {
        "api_success": api_success,
        "duration": duration,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "error": error,
        "intent": intent,
    }


def render_runtime_status() -> None:
    status = st.session_state.runtime_status
    has_error = bool(status.get("error"))
    dot = "🟡" if has_error else "🟢"
    knowledge_status = rag_engine.get_vectorstore_status()

    with st.expander(f"{dot} 运行状态 ▾", expanded=False):
        api_success = status.get("api_success")
        if api_success is None:
            api_text = "还没有开始"
        else:
            api_text = "成功" if api_success else "失败"

        duration = status.get("duration")
        duration_text = "暂无" if duration is None else f"{duration:.2f} 秒"
        timestamp_text = status.get("timestamp") or "暂无"

        st.markdown(
            f'<div class="status-line">当前调用方式：{"演示模式，本地预设结果" if demo_engine.is_demo_mode() else "实时调用 AI 服务"}</div>',
            unsafe_allow_html=True,
        )
        api_config = get_effective_api_config()
        api_source = "网页内配置" if st.session_state.get("user_api_key") else "本地环境配置"
        st.markdown(
            f'<div class="status-line">API连接来源：{api_source} · {mask_api_key(api_config["api_key"])}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="status-line">当前模型：{api_config["model"]}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="status-line">我是否顺利完成：{api_text}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="status-line">生成报告用时：{duration_text}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="status-line">最近处理时间：{timestamp_text}</div>', unsafe_allow_html=True)
        # 改动位置：展示 LangGraph 流程编排状态和最近一次识别出的意图。
        st.markdown(
            '<div class="status-line">流程编排状态：已启用 LangGraph 引擎</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="status-line">最近识别意图：{status.get("intent") or "暂无"}</div>',
            unsafe_allow_html=True,
        )
        prompt_modules = get_agent_last_prompt_modules()
        if prompt_modules:
            st.markdown(
                f'<div class="status-line">本次调用Prompt模块：{", ".join(prompt_modules)}</div>',
                unsafe_allow_html=True,
            )
        # 改动位置：在运行状态中展示 RAG 知识库是否已经构建。
        st.markdown(
            f'<div class="status-line">知识库状态：已加载 {knowledge_status["chunk_count"]} 个文档块</div>',
            unsafe_allow_html=True,
        )
        # 改动位置：说明当前知识库使用完全本地的轻量向量方案。
        st.markdown(
            '<div class="status-line">知识库类型：本地轻量向量，不依赖外部 Embedding API</div>',
            unsafe_allow_html=True,
        )
        if not knowledge_status["exists"]:
            st.markdown(
                f'<div class="status-muted">{knowledge_status["message"]}</div>',
                unsafe_allow_html=True,
            )
            st.warning("知识库索引尚未构建，部分检索功能暂时不可用。")
            if st.button("构建知识库索引", use_container_width=True, key="sidebar_build_index"):
                with st.spinner("正在构建知识库索引..."):
                    log_buffer = io.StringIO()
                    try:
                        import build_index

                        with contextlib.redirect_stdout(log_buffer), contextlib.redirect_stderr(log_buffer):
                            build_index.main()
                        st.code(log_buffer.getvalue() or "索引构建完成。", language="text")
                        st.success("知识库索引已更新。")
                    except Exception as exc:
                        st.code(log_buffer.getvalue(), language="text")
                        st.warning(f"知识库索引构建失败：{exc}")

        if has_error:
            st.markdown("需要查看的情况")
            st.code(status["error"], language="text")
        else:
            st.markdown('<div class="status-muted">当前没有异常。</div>', unsafe_allow_html=True)


        if st.button("📈 查看工作流", use_container_width=True):
            try:
                from agent_graph import graph

                workflow_text = graph.get_graph().draw_mermaid()
            except Exception:
                try:
                    from agent_graph import graph

                    workflow_text = graph.get_graph().draw_ascii()
                except Exception:
                    workflow_text = ""

            if workflow_text:
                st.code(workflow_text, language="text")
            else:
                st.warning("工作流图生成失败")


def render_api_connection_panel() -> None:
    """侧边栏 API 连接面板：允许用户在网页内临时接入自己的 API。"""
    sync_session_api_config_to_env()
    if "user_api_base_url" not in st.session_state:
        st.session_state.user_api_base_url = os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)
    if "user_api_model" not in st.session_state:
        st.session_state.user_api_model = os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL)
    if "user_api_connected" not in st.session_state:
        st.session_state.user_api_connected = bool(os.getenv("DEEPSEEK_API_KEY"))
    if "user_api_status_message" not in st.session_state:
        st.session_state.user_api_status_message = ""

    with st.expander("🔑 连接我的 API", expanded=not st.session_state.user_api_connected):
        st.caption("这里的配置只保存在当前网页会话中。开启演示模式时，我会继续读取本地演示结果，不会调用 API。")
        api_key = st.text_input(
            "API Key",
            value=st.session_state.get("user_api_key", ""),
            type="password",
            placeholder="请输入您的 DeepSeek API Key",
            help="用于实时生成回答。当前会话内生效，刷新后如未保存到环境变量，需要重新填写。",
            key="api_key_input",
        )
        base_url = st.text_input(
            "接口地址",
            value=st.session_state.user_api_base_url,
            placeholder=DEFAULT_BASE_URL,
            key="api_base_url_input",
        )
        model_name = st.text_input(
            "模型名称",
            value=st.session_state.user_api_model,
            placeholder=DEFAULT_MODEL,
            key="api_model_input",
        )

        col_connect, col_clear = st.columns(2)
        with col_connect:
            connect_clicked = st.button("连接 API", use_container_width=True)
        with col_clear:
            clear_clicked = st.button("清除配置", use_container_width=True)

        if connect_clicked:
            api_key = api_key.strip()
            base_url = (base_url.strip() or DEFAULT_BASE_URL).rstrip("/")
            model_name = model_name.strip() or DEFAULT_MODEL
            if not api_key:
                st.session_state.user_api_connected = False
                st.session_state.user_api_status_message = "请先填写 API Key。"
            else:
                try:
                    ok, message = test_deepseek_connection(api_key, base_url, model_name)
                    st.session_state.user_api_key = api_key
                    st.session_state.user_api_base_url = base_url
                    st.session_state.user_api_model = model_name
                    st.session_state.user_api_connected = ok
                    st.session_state.user_api_status_message = f"连接成功：{message}"
                    sync_session_api_config_to_env()
                except Exception as exc:
                    st.session_state.user_api_connected = False
                    st.session_state.user_api_status_message = f"连接失败：{exc}"

        if clear_clicked:
            for key in ["user_api_key", "user_api_base_url", "user_api_model"]:
                st.session_state.pop(key, None)
            for key, original_value in ORIGINAL_API_ENV.items():
                if original_value:
                    os.environ[key] = original_value
                else:
                    os.environ.pop(key, None)
            st.session_state.user_api_base_url = os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)
            st.session_state.user_api_model = os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL)
            st.session_state.user_api_connected = bool(os.getenv("DEEPSEEK_API_KEY"))
            st.session_state.user_api_status_message = "已清除当前会话中的 API 配置。"

        current_config = get_effective_api_config()
        if st.session_state.user_api_connected:
            st.success(f"已连接：{mask_api_key(current_config['api_key'])}")
        elif st.session_state.user_api_status_message:
            st.warning(st.session_state.user_api_status_message)
        else:
            st.info("未连接时，将使用本地 .env 中已有配置；如果也没有配置，实时生成会提示连接失败。")

        if st.session_state.user_api_status_message and st.session_state.user_api_connected:
            st.caption(st.session_state.user_api_status_message)
        st.caption(f"当前模型：{current_config['model']}")


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-hello">👋</div>
                <div class="sidebar-title">请选择模式</div>
                <div class="sidebar-subtitle">先看人，或直接看我怎么做运营判断。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_api_connection_panel()
        # 改动位置：演示模式开关。开启后所有生成结果从本地 JSON 读取，保证现场演示稳定。
        if "demo_mode" not in st.session_state:
            st.session_state.demo_mode = False
        demo_mode = st.toggle(
            "演示模式",
            value=st.session_state.demo_mode,
            help="开启后，我会从本地 demo_responses.json 读取预设结果，不实时调用外部 AI 服务。适合面试、路演或网络不稳定时展示。",
        )
        st.session_state.demo_mode = demo_mode
        os.environ["AI_OPS_DEMO_MODE"] = "1" if demo_mode else "0"
        if demo_mode:
            st.info("演示模式已开启：回答来自本地预设结果，适合稳定展示和离线容灾演示。")
        else:
            st.caption("实时模式：我会按当前配置调用 AI 服务生成结果。")
        with st.expander("演示模式说明", expanded=False):
            st.markdown(
                """
                - 适合面试现场、网络不稳定或 API 额度不足时使用。
                - 开启后，所有生成结果都从本地 `demo_responses.json` 读取。
                - 这个设计用于证明项目考虑了稳定演示与离线容灾场景。
                - 如果想看真实生成效果，请关闭演示模式后再提交问题。
                """
            )

        if "dashboard_default_applied" not in st.session_state:
            st.session_state.dashboard_default_applied = True
            st.session_state.main_mode = "dashboard"
        elif "main_mode" not in st.session_state:
            st.session_state.main_mode = "dashboard"

        dashboard_selected = st.session_state.main_mode == "dashboard"
        about_selected = st.session_state.main_mode == "about"
        work_selected = st.session_state.main_mode == "work"
        insight_selected = st.session_state.main_mode == "insight"
        activity_selected = st.session_state.main_mode == "activity"
        admin_selected = st.session_state.main_mode == "admin"

        if st.button(
            "🧭 运营决策中心",
            type="primary" if dashboard_selected else "secondary",
            use_container_width=True,
        ):
            st.session_state.main_mode = "dashboard"
            st.rerun()

        if st.button(
            "💬 关于我",
            type="primary" if about_selected else "secondary",
            use_container_width=True,
        ):
            st.session_state.main_mode = "about"
            st.rerun()

        if st.button(
            "📊 进入版本决策",
            type="primary" if work_selected else "secondary",
            use_container_width=True,
        ):
            st.session_state.main_mode = "work"
            st.rerun()

        if st.button(
            "🔎 做一次用户洞察",
            type="primary" if insight_selected else "secondary",
            use_container_width=True,
        ):
            st.session_state.main_mode = "insight"
            st.rerun()

        if st.button(
            "🎯 设计活动方案",
            type="primary" if activity_selected else "secondary",
            use_container_width=True,
        ):
            st.session_state.main_mode = "activity"
            st.rerun()

        if st.button(
            "🛠️ 管理后台",
            type="primary" if admin_selected else "secondary",
            use_container_width=True,
        ):
            st.session_state.main_mode = "admin"
            st.rerun()

        if st.session_state.main_mode == "dashboard":
            workflow_key = "dashboard"
        elif st.session_state.main_mode == "about":
            workflow_key = "personal"
        elif st.session_state.main_mode == "insight":
            workflow_key = "insight"
        elif st.session_state.main_mode == "activity":
            workflow_key = "activity"
        elif st.session_state.main_mode == "admin":
            workflow_key = "admin"
        else:
            workflow_key = "version"

        if workflow_key in WORKFLOWS:
            st.caption(WORKFLOWS[workflow_key]["description"])
        else:
            st.caption("查看报告、知识库、配置和缓存状态。")
        st.markdown("<br>", unsafe_allow_html=True)
        render_runtime_status()

    return workflow_key


def build_system_prompt(workflow_key: str, user_content: str, extra_context: str = "") -> str:
    """构建兜底系统提示词；改为按需加载，避免一次性塞入完整背景。"""
    intent = "analysis" if workflow_key == "version" else "chat"
    context = f"补充背景：\n{extra_context.strip()}" if extra_context.strip() else ""
    system_prompt, _ = prompt_loader.compose_prompt(user_content, intent, context)
    return system_prompt


def build_messages(workflow_key: str, user_content: str, extra_context: str = "") -> list[dict[str, str]]:
    system_prompt = build_system_prompt(workflow_key, user_content, extra_context)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def get_workflow_prompt(workflow_key: str) -> str:
    prompts = {
        "personal": """
请以“个人运营分身”的方式回答我的问题。
要求：
1. 严格依据长期背景回答，优先使用具体经历，不要泛泛生成。
2. 回答实习经历时，必须优先提到湖北盛天网络公司的AI音乐生成产品线运营实习，不要说“没有传统实习”。
3. 用第一人称自然回答，不要输出“直接可复用的表达版本”“面试/作品集”等标签，也不要把回答放进引用号里。
4. 如果问题涉及作品集或提示词工程，先给摘要，再引导对方选择是否展开完整文档。
""",
        "version": """
请分析游戏版本公告或活动说明。
请生成一份“宣发决策报告”，模块标题必须清晰。
输出结构：
1. 内容摘要：用 3-5 条提炼核心更新。
2. 宣发主卖点：判断最值得对外传播的卖点。
3. 目标玩家与渠道：说明适合触达的人群和渠道。
4. 文案角度建议：给出 3 个可直接延展的宣发角度。
5. 风险与注意事项：指出可能引发误解或负反馈的点。
6. 下一步行动：给出可执行的宣发、社区和数据观察建议。
""",
        "feedback": """
请对玩家反馈进行归因分析。
输出结构：
1. 反馈分类：性能、付费、玩法、内容、社交、情绪等。
2. 严重程度与优先级：说明判断依据。
3. 可能根因：区分产品问题、沟通问题和预期管理问题。
4. 处理建议：客服回复、社区公告、产品改进、数据验证。
5. 可沉淀洞察：适合放入运营复盘的结论。
""",
        "bilingual": """
请基于输入内容生成中日双语宣发文案。
输出结构：
1. 中文短文案：适合社媒标题或推送。
2. 中文长文案：适合公告或社区帖子。
3. 日文短文案：自然、简洁，不要机械翻译。
4. 日文长文案：保留游戏运营语气。
5. 文案策略说明：解释卖点顺序和语气选择。
""",
        "prompt": """
请优化我提供的工作指令或工作需求。
输出结构：
1. 需求澄清：指出当前需求里缺失的信息。
2. 优化后的 Prompt：给出可直接复制使用的版本。
3. 输出格式建议：定义模型应该返回的结构。
4. 评估标准：说明如何判断输出好坏。
5. 迭代建议：给出下一轮可以补充的变量。
""",
    }
    return prompts[workflow_key].strip()


def resolve_work_document(relative_path: str) -> Path | None:
    """改动位置：作品集原文支持 Markdown 文档，也兼容当前 works/ 中的 .docx 文件。"""
    return resolve_work_document_cached(relative_path)


@lru_cache(maxsize=128)
def resolve_work_document_cached(relative_path: str) -> Path | None:
    """缓存作品集路径解析结果；作品卡片反复渲染时避免重复检查多个候选路径。"""
    target_path = WORKS_DIR / relative_path
    if target_path.exists() and target_path.is_dir():
        return target_path

    candidates = [
        target_path,
        Path(f"{target_path}.docx"),
        target_path.with_suffix(".docx"),
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def get_file_signature(file_path: Path) -> tuple[str, int, int]:
    """返回文件签名；文件内容更新后缓存会自动失效。"""
    file_stat = file_path.stat()
    return str(file_path), file_stat.st_mtime_ns, file_stat.st_size


def read_docx_text(file_path: Path) -> str:
    """读取 docx 里的正文文本，避免额外安装依赖。"""
    file_path_text, file_mtime_ns, file_size = get_file_signature(file_path)
    return read_docx_text_by_signature(file_path_text, file_mtime_ns, file_size)


@lru_cache(maxsize=32)
def read_docx_text_by_signature(file_path_text: str, file_mtime_ns: int, file_size: int) -> str:
    """缓存读取 docx 正文；文件签名变化时自动重新读取。"""
    file_path = Path(file_path_text)
    try:
        with zipfile.ZipFile(file_path) as docx_zip:
            xml_content = docx_zip.read("word/document.xml")
    except Exception:
        return ""

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    root = ElementTree.fromstring(xml_content)
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)).strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def read_docx_preview_markdown(file_path: Path) -> str:
    """改动位置：将 docx 的标题样式转换为 Markdown，提升网页预览的层级感。"""
    file_path_text, file_mtime_ns, file_size = get_file_signature(file_path)
    return read_docx_preview_markdown_by_signature(file_path_text, file_mtime_ns, file_size)


@lru_cache(maxsize=32)
def read_docx_preview_markdown_by_signature(file_path_text: str, file_mtime_ns: int, file_size: int) -> str:
    """缓存生成 docx 预览；文件签名变化时自动重新解析。"""
    file_path = Path(file_path_text)
    try:
        with zipfile.ZipFile(file_path) as docx_zip:
            xml_content = docx_zip.read("word/document.xml")
    except Exception:
        return ""

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    root = ElementTree.fromstring(xml_content)
    lines: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)).strip()
        if not text:
            continue

        style_node = paragraph.find("./w:pPr/w:pStyle", namespace)
        style_value = ""
        if style_node is not None:
            style_value = style_node.attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "")
        normalized_style = style_value.lower().replace(" ", "")
        heading_match = DOCX_HEADING_STYLE_RE.search(normalized_style)
        if heading_match:
            level = max(1, min(int(heading_match.group(1)), 4))
            lines.append(f"{'#' * level} {text}")
        else:
            lines.append(text)

    return "\n\n".join(lines)


def read_work_document(relative_path: str) -> tuple[str, Path | None]:
    """加载作品集原文；找不到时返回空文本。"""
    file_path = resolve_work_document(relative_path)
    if file_path is None:
        return "", None
    if file_path.is_dir():
        return build_work_directory_preview(file_path), file_path

    file_path_text, file_mtime_ns, file_size = get_file_signature(file_path)
    return read_work_document_by_signature(relative_path, file_path_text, file_mtime_ns, file_size)


def build_work_directory_preview(directory_path: Path) -> str:
    """改动位置：作品集条目支持项目文件夹，优先展示架构说明和目录结构。"""
    lines = [f"# {directory_path.name}", "", "这是一个作品项目文件夹。您可以点击“打开项目文件夹”查看完整代码、数据和说明文件。", ""]
    architecture_file = directory_path / "ARCHITECTURE.md"
    if architecture_file.exists() and architecture_file.is_file():
        try:
            lines.extend(["## 架构说明预览", "", architecture_file.read_text(encoding="utf-8", errors="replace").strip(), ""])
        except Exception:
            lines.extend(["## 架构说明预览", "", "暂时无法读取 ARCHITECTURE.md，但可以直接打开项目文件夹查看。", ""])

    visible_files = []
    try:
        for child in sorted(directory_path.iterdir(), key=lambda item: (item.is_file(), item.name.lower())):
            if child.name.startswith(".") and child.name not in {".env.example", ".gitignore"}:
                continue
            marker = "[目录]" if child.is_dir() else "[文件]"
            visible_files.append(f"- {marker} {child.name}")
            if len(visible_files) >= 80:
                visible_files.append("- ...")
                break
    except Exception:
        visible_files = ["- 暂时无法读取目录结构"]

    lines.extend(["## 项目目录", "", *visible_files])
    return "\n".join(lines).strip()


@lru_cache(maxsize=64)
def read_work_document_by_signature(
    relative_path: str,
    file_path_text: str,
    file_mtime_ns: int,
    file_size: int,
) -> tuple[str, Path | None]:
    """缓存作品原文读取；文件更新后自动刷新。"""
    file_path = Path(file_path_text)
    if file_path.suffix.lower() == ".docx":
        return read_docx_preview_markdown(file_path), file_path
    if file_path.suffix.lower() == ".pdf":
        size_kb = max(1, file_size // 1024)
        return (
            f"# {file_path.stem}\n\n"
            "这是一个 PDF 作品文档。网页内不直接解析 PDF 排版，以避免出现乱码或格式错乱。\n\n"
            f"- 文件类型：PDF\n"
            f"- 文件大小：约 {size_kb} KB\n"
            "- 建议查看方式：点击上方“打开原文件”，使用本机 PDF 阅读器查看完整排版；也可以点击“下载原文件”保存后查看。",
            file_path,
        )

    return file_path.read_text(encoding="utf-8", errors="replace"), file_path


def read_file_bytes(file_path: Path) -> bytes:
    """缓存原文文件字节；用于下载按钮，减少预览区反复刷新时的磁盘读取。"""
    file_path_text, file_mtime_ns, file_size = get_file_signature(file_path)
    return read_file_bytes_by_signature(file_path_text, file_mtime_ns, file_size)


@lru_cache(maxsize=64)
def read_file_bytes_by_signature(file_path_text: str, file_mtime_ns: int, file_size: int) -> bytes:
    """按文件签名缓存文件字节；文件更新后自动失效。"""
    return Path(file_path_text).read_bytes()


@lru_cache(maxsize=64)
def extract_document_outline(text: str) -> list[tuple[int, str]]:
    """改动位置：从预览文本中提取大纲，帮助用户快速判断文档结构。"""
    outline: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        heading_match = OUTLINE_MARKDOWN_HEADING_RE.match(line)
        if heading_match:
            outline.append((len(heading_match.group(1)), heading_match.group(2).strip()))
            continue

        section_match = OUTLINE_SECTION_RE.match(line)
        if section_match:
            outline.append((2, f"{section_match.group(1)}{section_match.group(2).strip()}"))

        if len(outline) >= 80:
            break
    return outline


@lru_cache(maxsize=64)
def markdown_to_plain_text(text: str) -> str:
    """改动位置：作品预览正文按纯文本展示，去掉明显的 Markdown 标记。"""
    plain_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        line = re.sub(r"^#{1,6}\s+", "", line)
        line = re.sub(r"^>\s?", "", line)
        line = re.sub(r"^\s*[-*+]\s+", "• ", line)
        line = re.sub(r"`([^`]+)`", r"\1", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        line = re.sub(r"\*([^*]+)\*", r"\1", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        plain_lines.append(line)
    return "\n".join(plain_lines).strip()


def open_file_in_default_app(file_path: Path) -> None:
    """改动位置：在本机默认程序中打开作品原文件，保留 Word/PDF 原始排版与目录。"""
    if os.name == "nt":
        os.startfile(str(file_path))  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(file_path)])
        return
    subprocess.Popen(["xdg-open", str(file_path)])


def render_work_document_preview(relative_path: str) -> None:
    """改动位置：作品集文档预览统一使用全宽区域展示，并提供打开原文件操作。"""
    text, file_path = read_work_document(relative_path)
    if not file_path or not text.strip():
        st.info("原文文档尚未上传")
        return

    with st.container(border=True):
        is_directory = file_path.is_dir()
        preview_title = "项目文件夹预览" if is_directory else "文档预览"
        st.markdown(f"### {preview_title}：{file_path.name}")
        st.markdown(
            '<div class="document-preview-note">网页内预览会优先展示标题层级和重点内容，方便您快速扫读；如果想查看完整项目结构、Word 原始大纲或完整排版，可以点击下方按钮打开原文件或文件夹。</div>',
            unsafe_allow_html=True,
        )
        action_columns = st.columns([1, 1, 2])
        with action_columns[0]:
            open_label = "打开项目文件夹" if is_directory else "打开原文件"
            if st.button(open_label, key=f"open_native_{relative_path}", use_container_width=True):
                try:
                    open_file_in_default_app(file_path)
                    st.success("正在为您打开文件，请稍后")
                except Exception:
                    st.warning("暂时无法自动打开原文件或文件夹，您可以在 works/ 文件夹中手动查看")
        with action_columns[1]:
            if not is_directory:
                st.download_button(
                    "下载原文件",
                    data=read_file_bytes(file_path),
                    file_name=file_path.name,
                    mime="application/octet-stream",
                    key=f"download_work_{relative_path}",
                    use_container_width=True,
                )
            else:
                st.caption("项目文件夹请直接打开查看")

        outline = extract_document_outline(text)
        if outline:
            with st.expander("查看文档大纲", expanded=True):
                outline_lines = []
                for level, title in outline:
                    indent = "&nbsp;" * max(0, (level - 1) * 4)
                    outline_lines.append(f"{indent}- {title}")
                st.markdown('<div class="document-outline">' + "<br>".join(outline_lines) + "</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.text_area(
            "文档正文预览",
            value=markdown_to_plain_text(text),
            height=520,
            key=f"plain_work_preview_{relative_path}",
        )


def load_portfolio_config_items() -> list[dict[str, object]]:
    """改动位置：作品集卡片优先从 config/ui/portfolio.yaml 读取，便于后续增删作品。"""
    config_path = PROJECT_DIR / "config" / "ui" / "portfolio.yaml"
    config = config_loader.load_yaml_config(config_path)
    raw_items = config.get("items") if isinstance(config, dict) else None
    if not isinstance(raw_items, list):
        return []

    items: list[dict[str, object]] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        title = str(raw_item.get("title", "")).strip()
        path = str(raw_item.get("path", "")).strip()
        if not title or not path:
            continue
        tags = raw_item.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        items.append(
            {
                "title": title,
                "subtitle": str(raw_item.get("subtitle", "")).strip(),
                "desc": str(raw_item.get("desc", raw_item.get("description", ""))).strip(),
                "tags": [str(tag).strip() for tag in tags if str(tag).strip()],
                "path": path,
            }
        )
    return items


def get_portfolio_items() -> list[dict[str, object]]:
    """整理作品集卡片数据，文章作品会自动从 works/articles/ 读取。"""
    articles_dir = WORKS_DIR / "articles"
    articles_dir_mtime = articles_dir.stat().st_mtime_ns if articles_dir.exists() else 0
    portfolio_config_path = PROJECT_DIR / "config" / "ui" / "portfolio.yaml"
    portfolio_config_mtime = portfolio_config_path.stat().st_mtime_ns if portfolio_config_path.exists() else 0
    return get_portfolio_items_by_signature(articles_dir_mtime, portfolio_config_mtime)


@lru_cache(maxsize=8)
def get_portfolio_items_by_signature(articles_dir_mtime: int, portfolio_config_mtime: int) -> list[dict[str, object]]:
    """缓存作品集卡片列表；文章目录增删文件后自动刷新。"""
    hidden_article_titles = {
        "AI Music for Meditation A Complete Guide to Healing Frequencies and Binaural Beats with MakeBestMus",
    }
    items = load_portfolio_config_items()
    if not items:
        items = [
        {
            "title": "AI运营分身 Agent 设计与迭代记录",
            "desc": "本网站本身是完整作品：记录从基础问答、界面产品化、RAG、LangGraph，到运营路线图、Prompt按需加载、反馈可视化、演示模式、多职能协作和结果定位优化的完整迭代。",
            "path": "agent-design-iteration.md",
        },
        {
            "title": "SEO提示词工程迭代记录",
            "desc": "记录从 V0 到 V4 的问题诊断、迭代路径和验证要点，体现系统化优化 AI 内容管线的能力。",
            "path": "iteration-history.md",
        },
        {
            "title": "协同演进报告：提示词工程与Agent架构",
            "desc": "记录从指令优化到系统设计的方法论迁移，说明 SEO 提示词工程中的时序、分工、身份和校验经验如何指导 Agent 架构设计。",
            "path": "methodology-bridge.md",
        },
        {
            "title": "SEO提示词工程本体全集",
            "desc": "收录 V1 到 V4 的全部提示词工程本体，可结合迭代记录直观看到工程形式、模块结构和内容约束如何逐步改动。",
            "path": "prompt-engineering.md",
        },
        ]

    articles_dir = WORKS_DIR / "articles"
    if articles_dir.exists():
        for article_path in sorted(articles_dir.glob("*.docx")):
            if article_path.stem in hidden_article_titles:
                continue
            items.append(
                {
                    "title": article_path.stem,
                    "subtitle": "已发布 SEO / Blog 文章",
                    "desc": "已发布 SEO / Blog 文章作品，用于验证提示词工程在真实内容生产中的稳定产出能力。",
                    "tags": ["SEO文章", "内容生产验证"],
                    "path": f"articles/{article_path.name}",
                }
            )
    return items


def render_personal_chat_form() -> tuple[str, str]:
    st.markdown(
        """
        <div class="task-panel">
            <div class="task-kicker">面试预演</div>
            <div class="task-title">选择一个问题，快速了解我的经历</div>
            <div class="task-desc">这些问题按真实面试场景设计，适合查看实习、AI运营、游戏理解、活动统筹和作品集能力。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    preset_rows = [
        [
            "你做过什么实习？",
            "你怎么用AI做运营？",
            "介绍你的作品集，并说明它们分别验证哪些能力",
        ],
        [
            "你对哪款游戏理解最深？",
            "你策划过什么活动？",
            "能详细说说你的提示词工程吗？",
        ],
        [
            "请全面介绍本Agent所有功能并指引我进行操作",
            "提示词工程和Agent架构之间是什么关系？",
            "星铁战术引擎和这个Agent有什么关系？",
        ],
        [
            "你的战术引擎的数学思路是怎么样的？",
        ],
    ]

    if "personal_question" not in st.session_state:
        st.session_state.personal_question = ""
    if "pending_personal_question" in st.session_state:
        st.session_state.personal_question = st.session_state.pop("pending_personal_question")

    render_chat_history()

    st.markdown('<div class="preset-title">向我提问</div>', unsafe_allow_html=True)
    question = st.text_area(
        "你想让个人运营分身回答什么？",
        placeholder="例如：请帮我用面试口吻介绍这个作品集项目，突出我从音乐专业转向 AI/游戏运营的优势。",
        height=112,
        key="personal_question",
    )

    st.markdown(
        '<div class="faq-hint">还没想好问什么？您可以试试展开下面的提示，选择一个真实面试的高频问题。</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="portfolio-guide">想快速看项目成果？可以直接输入“介绍你的作品集”，我会优先介绍这个 AI 运营分身网站，再说明 SEO 提示词工程和文章作品分别验证的能力。</div>',
        unsafe_allow_html=True,
    )
    with st.expander("查看常见问题", expanded=False):
        for row_index, row in enumerate(preset_rows):
            columns = st.columns(len(row))
            for column, preset_question in zip(columns, row):
                with column:
                    if st.button(
                        preset_question,
                        key=f"preset_question_{row_index}_{preset_question}",
                        use_container_width=True,
                    ):
                        st.session_state.pending_personal_question = preset_question
                        st.session_state.auto_submit_personal = True
                        st.rerun()

    with st.expander("可选：让回答更贴近你的场景", expanded=False):
        extra = st.text_area(
            "如果您希望回答更加具有针对性，可以这样使用这个文本",
            help=(
                "这里不是必填项。你可以写下这次回答的具体用途、目标岗位或希望强调的方向。"
                "例如：请压缩成1分钟面试回答；请更突出AI音乐产品实习；"
                "请面向游戏运营岗位；请更强调项目管理和跨团队协作。"
            ),
            placeholder="例如：请面向游戏运营岗位，更突出AI音乐产品实习和项目统筹能力。",
            height=110,
        )
    return question, extra


def run_personal_chat(user_content: str, extra_context: str) -> None:
    """改动位置：关于我 Tab 内部处理聊天提交，保留原有 LangGraph 与兜底逻辑。"""
    if not user_content.strip():
        st.warning("请先输入你想了解的问题。")
        return

    start_time = time.perf_counter()
    if not has_available_model_access():
        result = build_personal_local_fallback(user_content)
        update_runtime_status(
            api_success=False,
            duration=time.perf_counter() - start_time,
            error="未检测到可用 API Key，了解我模式已使用本地兜底回答。",
            intent="fallback:personal-local",
        )
        st.session_state.last_report = result
        st.session_state.last_workflow = "personal"
        st.session_state.last_report_path = ""
        agent_input = build_agent_input("personal", user_content, extra_context)
        remember_agent_turn("personal", agent_input, result)
        remember_display_turn("personal", user_content, result)
        mark_result_ready()
        st.rerun()

    with st.spinner("请您稍等片刻，回答马上就到🚅"):
        try:
            agent_input = build_agent_input("personal", user_content, extra_context)
            agent_messages = get_agent_messages("personal", agent_input)
            result, detected_intent = run_agent_graph(agent_input, messages=agent_messages)
        except Exception as agent_exc:
            try:
                result = call_direct_deepseek_fallback("personal", user_content, extra_context)
                detected_intent = "fallback:personal"
            except Exception as exc:
                result = build_personal_local_fallback(user_content)
                detected_intent = "fallback:personal-local"
                update_runtime_status(
                    api_success=False,
                    duration=time.perf_counter() - start_time,
                    error=f"LangGraph：{agent_exc}\n\nDeepSeek 兜底：{exc}",
                    intent=get_agent_last_intent(),
                )

    if not result:
        result = build_personal_local_fallback(user_content)
        detected_intent = "fallback:personal-local"
        update_runtime_status(False, time.perf_counter() - start_time, "没有生成有效内容，已使用本地兜底回答。", detected_intent)
    else:
        update_runtime_status(True, time.perf_counter() - start_time, "", detected_intent)

    st.session_state.last_report = result
    st.session_state.last_workflow = "personal"
    st.session_state.last_report_path = ""
    remember_agent_turn("personal", agent_input, result)
    remember_display_turn("personal", user_content, result)
    mark_result_ready()
    st.rerun()


def render_portfolio_tab() -> None:
    """我的作品集 Tab：展示作品卡片，并按需加载 works/ 原文。"""
    st.markdown(
        """
        <div class="task-panel">
            <div class="task-kicker">我的作品集</div>
            <div class="task-title">这里展示的不只是文字材料，也包括这个 AI 运营分身项目本身</div>
            <div class="task-desc">您可以先看每个作品验证的能力，再点击“预览文档”查看网页预览；需要原始大纲和排版时，可以继续打开原文件。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="portfolio-guide">如果您对某份作品有疑问、想按岗位能力拆解，或者希望我进一步解释某个设计思路，也可以切回“了解我”和 AI 运营分身直接对话。</div>',
        unsafe_allow_html=True,
    )

    items = get_portfolio_items()
    selected_path = st.session_state.get("open_work_path", "")
    for index in range(0, len(items), 2):
        row_items = items[index : index + 2]
        columns = st.columns(2)
        for column, item in zip(columns, row_items):
            with column:
                with st.container(border=True):
                    item_path = str(item["path"])
                    source_text, source_path = read_work_document(item_path)
                    st.markdown(f"#### {item['title']}")
                    if item.get("subtitle"):
                        st.caption(str(item["subtitle"]))
                    st.write(str(item.get("desc", "")))
                    tags = item.get("tags", [])
                    if isinstance(tags, list) and tags:
                        st.caption("能力标签：" + "、".join(str(tag) for tag in tags))
                    st.caption(f"对应文档：works/{item_path}")
                    if source_path is None or not source_text.strip():
                        st.button("预览文档", key=f"open_work_{item_path}", use_container_width=True, disabled=True)
                        st.caption("原文文档尚未上传")
                    elif st.button("正在预览" if selected_path == item_path else "预览文档", key=f"open_work_{item_path}", use_container_width=True):
                        st.session_state.open_work_path = item_path
                        selected_path = item_path

        # 改动位置：当前行下方展示全宽预览，既靠近卡片，又保留足够阅读宽度。
        if selected_path and selected_path in {str(item["path"]) for item in row_items}:
            render_work_document_preview(selected_path)


def get_agent_limitations_preset() -> str:
    """开发者特殊预设：固定说明 Agent 当前局限性，不调用大模型随机生成。"""
    return """## 开发者特殊预设说明

以下内容为开发者特殊预设回答，并非 AI 随机生成结果。该内容用于面向 HR / 面试官坦诚说明本 Agent 当前边界、个人开发环境限制，以及进入生产环境后的可升级路径。

---

## Q1：分析报告的结论是实时验证过的吗？

A：目前不是。所有分析基于 AI 模型内嵌知识生成，虽然我加了全系统数据源预警机制（每份报告都会标注“未经实时数据校验”），但这仍是事后声明而非实时验证。

为什么个人做不了：实时数据校验需要接入多源官方 API，多数需要商业授权，个人无法持续维护。

进生产环境怎么做：引入 LangSmith 全链路追踪，记录每次 Agent 调用的完整链路，配置自动化评估器对输出进行“事实准确性”评分，逐步构建校验数据集。同时接入公司内部数据接口，实现生成前即比对官方数据源。

## Q2：多元数据融合分析目前能做到什么程度？

A：目前实现了多来源文本的整合分析——反馈清洗可同时处理多个来源的用户反馈，协作讨论可整合十个职能视角。但无法读取游戏内埋点数据、后台运营报表等结构化数据。

为什么个人做不了：真正的数据融合需要接入游戏后台数据库和埋点系统，这些是公司核心资产，个人无法获取。

进生产环境怎么做：已在架构上预留了标准化数据接入层。部署到公司内网后，通过内网 API 直连数据仓库，Agent 可同时读取实时运营数据和用户反馈文本，进行真正的交叉分析。

## Q3：Agent 会从使用中越变越聪明吗？

A：目前不会。每次调用都是独立的，Agent 不会记住用户偏好，反复使用同一个功能输出风格不会自动优化。

为什么个人做不了：反馈闭环需要大量真实用户的持续交互数据积累和模型微调能力，个人环境无法满足。

进生产环境怎么做：引入 LangSmith 记录每次交互和用户反馈，构建评估数据集。积累足够高质量反馈后，用这些数据对模型进行监督微调，让 Agent 输出逐步对齐团队的使用偏好。

## Q4：竞品雷达的数据是最新的吗？

A：不是。竞品分析完全基于 AI 模型训练数据中的旧有信息，无法获取竞品最新版本动态。

为什么个人做不了：实时竞品监控需要持续爬取多个竞品的官方渠道，涉及法律合规风险和技术维护成本，个人无法独立承担。

进生产环境怎么做：在公司内网搭建自动化信息采集系统，定期从竞品官方渠道抓取版本公告存入本地数据库。Agent 分析时从数据库读取最新信息，结合 RAG 检索内部运营文档进行对比分析。所有数据采集在公司内网完成，确保合规。

## Q5：所有功能模块的深度一样吗？

A：不一样。版本决策和反馈清洗是我实习中实践过的领域，Prompt 经过了多轮迭代打磨；其他模块（如问卷工坊、访谈助手）是功能完整的初版框架，但深度优化需要真实业务场景中的反复测试和反馈。

为什么个人做不完全：Prompt 的深度优化需要大量真实业务案例来验证，个人开发者只能基于假设设计，难以达到生产级别精准度。

进生产环境怎么做：入职后在实际业务中持续迭代。框架已搭好，优化方向明确——只需要真实的业务需求和团队反馈作为参照。
"""


def render_self_diagnosis_tab() -> None:
    """自我诊断 Tab：生成能力诊断，并引导面试官继续追问。"""
    st.markdown(
        """
        <div class="task-panel">
            <div class="task-kicker">自我诊断</div>
            <div class="task-title">把我的经历拆成优势、风险和可继续追问的问题</div>
            <div class="task-desc">适合面试官快速判断我的匹配度，也适合继续深入某一段经历。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # 改动位置：自我诊断增加三个可直接使用的预设方向，帮助面试官快速发起诊断。
    diagnosis_presets = [
        "请判断我和游戏运营岗位的匹配度，重点说明优势、风险和可追问问题。",
        "请诊断我的 AI 运营能力，重点看提示词工程、RAG/Agent 项目和内容生产能力。",
        "你的作品集内容如何体现你的数据思维？",
    ]
    if "pending_diagnosis_focus" in st.session_state:
        st.session_state.diagnosis_focus = st.session_state.pop("pending_diagnosis_focus")

    st.markdown('<div class="preset-title">常用诊断问题</div>', unsafe_allow_html=True)
    preset_columns = st.columns(3)
    for preset_index, preset_text in enumerate(diagnosis_presets):
        with preset_columns[preset_index]:
            if st.button(preset_text, key=f"diagnosis_preset_{preset_index}", use_container_width=True):
                st.session_state.pending_diagnosis_focus = preset_text
                st.rerun()

    # 改动位置：增加开发者特殊预设折叠项，说明 Agent 的现实边界与生产化升级路径。
    with st.expander("这个 Agent 的局限性具体在哪？"):
        st.caption("该内容为开发者特殊预设回答，不会调用模型随机生成。")
        if st.button("查看局限性说明", key="agent_limitations_preset", use_container_width=True):
            st.session_state.self_diagnosis_result = get_agent_limitations_preset()
            update_runtime_status(True, 0, "", "personal:diagnosis:preset")
            mark_result_ready()
            st.rerun()

    focus = st.text_area(
        "你希望我重点诊断什么？（可选）",
        placeholder="例如：面向游戏运营岗位；重点看AI工具能力；重点看项目统筹与沟通能力。",
        height=120,
        key="diagnosis_focus",
    )
    if st.button("生成自我诊断", type="primary", use_container_width=True, key="diagnosis_submit"):
        user_content = f"请生成一份面向 HR / 面试官阅读的自我诊断报告。报告可以说明由本 AI 运营分身撰写，但不要写成给候选人本人的建议。\n重点关注：{focus.strip() or '没有指定重点，请按游戏运营和AI运营岗位综合诊断。'}"
        system_prompt, _ = prompt_loader.compose_prompt(user_content, "chat")
        start_time = time.perf_counter()
        with st.spinner("请您稍等片刻，诊断报告马上就到🚅"):
            try:
                result = call_deepseek_with_system_prompt(system_prompt, user_content)
            except Exception as exc:
                update_runtime_status(False, time.perf_counter() - start_time, str(exc), "personal:diagnosis")
                st.warning("非常抱歉！分析引擎暂时遇到点小问题，请您稍后再试")
                return

        if "推荐你接下来可以问我什么" not in result:
            result = (
                f"{result.strip()}\n\n---\n\n"
                "## 推荐你接下来可以问我什么问题\n"
                "你可以继续问我：“能不能用一个具体案例说明你如何把 AI 工具用进运营流程？”也可以问：“这个作品集网站本身验证了你哪些能力？”"
            )
        st.session_state.self_diagnosis_result = result
        update_runtime_status(True, time.perf_counter() - start_time, "", "personal:diagnosis")
        mark_result_ready()
        st.rerun()

    result = st.session_state.get("self_diagnosis_result", "")
    if result:
        render_result_anchor()
        st.markdown('<div class="report-box">', unsafe_allow_html=True)
        st.markdown(format_self_diagnosis_markdown(result))
        st.text_area("复制诊断报告", value=result, height=220, key="self_diagnosis_copy")
        st.markdown("</div>", unsafe_allow_html=True)


def render_about_mode() -> None:
    """关于我模式：了解我、我的作品集、自我诊断三个可持久切换的页签。"""
    about_options = ["💬 了解我", "📁 我的作品集", "🔍 自我诊断"]
    selected_about_tab = st.radio(
        "选择关于我页面",
        about_options,
        horizontal=True,
        key="about_workspace_tab",
        label_visibility="collapsed",
    )

    if selected_about_tab == "💬 了解我":
        question, extra = render_personal_chat_form()
        button_slot = st.empty()
        submitted = button_slot.button("生成回答", type="primary", use_container_width=True, key="personal_submit")
        auto_submitted = bool(st.session_state.pop("auto_submit_personal", False))
        if submitted or auto_submitted:
            button_slot.button("正在生成中...", disabled=True, use_container_width=True, key="personal_submit_disabled")
            run_personal_chat(question, extra)

    if selected_about_tab == "📁 我的作品集":
        render_portfolio_tab()

    if selected_about_tab == "🔍 自我诊断":
        render_self_diagnosis_tab()


def render_personal() -> tuple[str, str, str]:
    question, extra = render_personal_chat_form()
    return question, extra, "生成回答"


def switch_to_workspace(main_mode: str, insight_tab: str = "", version_tab: str = "") -> None:
    """改动位置：决策看板按钮在当前页面内切换到指定模式和子功能。"""
    st.session_state.main_mode = main_mode
    if insight_tab:
        st.session_state.target_insight_tab = insight_tab
    if version_tab:
        st.session_state.target_version_tab = version_tab
        if version_tab == "🤝 协作讨论":
            st.session_state.collaboration_prefill_from_baseline = True
    st.rerun()


def render_decision_dashboard() -> None:
    """决策看板：首页按运营生命周期组织入口。"""
    st.markdown(
        """
        <div class="decision-hero">
            <div class="decision-title">运营路线图</div>
            <div class="decision-subtitle">从研发到长线运营的完整决策流程</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_data_source_config()

    active_stage = st.session_state.get("active_roadmap_stage", None)
    stages = [
        {
            "number": "①",
            "title": "🔬 研发期",
            "desc": "用户需求洞察与市场验证",
            "goal": "在版本开发阶段，明确目标用户画像、核心卖点和竞品差异化定位。",
            "output": "用户需求洞察报告、竞品市场分析、初步版本定位文档。",
            "next_hint": "↓ 需求明确后，进入测试期进行版本质量验证",
            "actions": [
                ("进入用户洞察 → 访谈助手、问卷工坊", "通过玩家访谈和问卷调研，获取一手用户需求。", "insight", "📋 访谈助手", ""),
                ("进入竞品分析 → 竞品雷达", "分析竞品最新动态，识别市场机会和差异化空间。", "work", "", "📡 竞品雷达"),
            ],
        },
        {
            "number": "②",
            "title": "🧪 测试期",
            "desc": "版本质量评估与反馈清洗",
            "goal": "在测试阶段快速识别体验问题、负面反馈集中点和版本质量风险。",
            "output": "玩家反馈清洗报告、优先级问题清单、版本质量调整建议。",
            "next_hint": "↓ 版本稳定后，进入上线前制定宣发策略和活动方案",
            "actions": [
                ("进入反馈清洗 → 反馈清洗工作台", "清洗玩家测试反馈，判断问题类型、情绪强度和处理优先级。", "insight", "🧹 反馈清洗", ""),
            ],
        },
        {
            "number": "③",
            "title": "🚀 上线前",
            "desc": "卖点提炼、宣发策略与活动方案制定",
            "goal": "在上线前完成版本卖点包装、宣发节奏规划和活动承接方案设计。",
            "output": "版本分析报告、宣发决策建议、活动策划方案。",
            "next_hint": "↓ 版本上线后，持续监控版本表现和竞品动态",
            "actions": [
                ("进入版本分析 → 版本分析", "拆解版本公告，提炼卖点、传播风险和上线节奏。", "work", "", "🔍 版本分析"),
                ("进入活动策划 → 活动工坊", "围绕版本目标生成活动主题、用户路径、奖励梯度和复盘指标。", "activity", "", ""),
            ],
        },
        {
            "number": "④",
            "title": "📈 上线后",
            "desc": "版本表现监控与竞品动态追踪",
            "goal": "在版本上线后持续监控玩家反馈、传播表现和竞品动作，及时调整运营策略。",
            "output": "竞品对比报告、上线反馈清洗结果、风险预警与行动建议。",
            "next_hint": "↓ 进入长线运营，基于数据持续优化迭代",
            "actions": [
                ("进入竞品雷达 → 竞品对比", "将自家版本与竞品公告对比，判断外部竞争风险。", "work", "", "📡 竞品雷达"),
                ("进入反馈清洗 → 玩家反馈整理", "整理上线后的玩家反馈，识别高频问题和情绪风险。", "insight", "🧹 反馈清洗", ""),
            ],
        },
        {
            "number": "⑤",
            "title": "🔄 长线运营",
            "desc": "持续优化迭代与活动运营",
            "goal": "基于长期反馈和阶段复盘，持续优化活动节奏、用户关系和版本迭代方向。",
            "output": "长线活动方案、用户洞察追问提纲、下一轮运营优化建议。",
            "next_hint": "",
            "actions": [
                ("进入活动策划 → 长线活动方案", "生成可持续复用的活动方案和阶段复盘指标。", "activity", "", ""),
                ("进入用户洞察 → 持续调研", "通过访谈和问卷持续追踪玩家需求变化。", "insight", "📋 访谈助手", ""),
            ],
        },
    ]

    chain_parts = []
    for index, stage in enumerate(stages):
        dot_class = "roadmap-dot roadmap-dot-active" if active_stage == index else "roadmap-dot"
        chain_parts.append(f'<div class="{dot_class}">{index + 1}</div>')
        if index < len(stages) - 1:
            line_class = "roadmap-line roadmap-line-active" if active_stage is not None and index < active_stage else "roadmap-line"
            chain_parts.append(f'<div class="{line_class}"></div>')
    overview_hint = "点击下方卡片开始" if active_stage is None else f"当前展开：{stages[active_stage]['title']}"
    st.markdown(
        f"""
        <div class="roadmap-overview">
            <div class="roadmap-chain">{''.join(chain_parts)}</div>
            <div class="roadmap-hint">{overview_hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for stage_index, stage in enumerate(stages):
        is_active = active_stage == stage_index
        card_class = "roadmap-card roadmap-card-active" if is_active else "roadmap-card"
        display_title = f'{stage["title"]}——{stage["desc"]}' if is_active else stage["title"]
        st.markdown(
            f"""
            <div class="{card_class}">
                <div class="roadmap-number">{stage["number"]}</div>
                <div>
                    <div class="roadmap-title">{display_title}</div>
                    <div class="roadmap-desc">{stage["desc"]}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        expand_label = "收起该阶段工作台" if is_active else "展开该阶段工作台"
        if st.button(expand_label, use_container_width=True, key=f"roadmap_expand_{stage_index}"):
            st.session_state.active_roadmap_stage = None if is_active else stage_index
            st.rerun()

        if is_active:
            left_col, right_col = st.columns([1.05, 0.95], gap="large")
            with left_col:
                st.markdown(
                    f"""
                    <div class="roadmap-info-title">运营目标</div>
                    <div class="roadmap-info-text">{stage["goal"]}</div>
                    <div class="roadmap-info-title">关键产出</div>
                    <div class="roadmap-info-text">{stage["output"]}</div>
                    """,
                    unsafe_allow_html=True,
                )
            with right_col:
                st.markdown('<div class="roadmap-action-title">功能入口</div>', unsafe_allow_html=True)
                for action_index, (label, description, main_mode, insight_tab, version_tab) in enumerate(stage["actions"]):
                    if st.button(label, use_container_width=True, key=f"dashboard_{stage_index}_{action_index}"):
                        switch_to_workspace(main_mode, insight_tab=insight_tab, version_tab=version_tab)
                    st.markdown(f'<div class="roadmap-action-desc">{description}</div>', unsafe_allow_html=True)
            if stage["next_hint"] and active_stage != stage_index + 1:
                st.markdown(f'<div class="roadmap-next-hint">{stage["next_hint"]}</div>', unsafe_allow_html=True)

        if stage_index < len(stages) - 1:
            st.markdown(
                '<div class="roadmap-connector"><div class="roadmap-connector-inner"><span class="roadmap-arrow">↓</span></div></div>',
                unsafe_allow_html=True,
            )
    st.caption("所有Agent分析结果均基于AI推理与用户输入生成，建议在关键决策前进行交叉验证。")


def render_version() -> tuple[str, str, str]:
    st.markdown(
        """
        <div class="task-panel">
            <div class="task-kicker">工作能力测试</div>
            <div class="task-title">把版本公告交给我，我会输出宣发决策报告</div>
            <div class="task-desc">适合测试版本内容拆解、玩家分层、卖点提炼、渠道判断和风险预警。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-title">请粘贴游戏版本公告，我将为你生成宣发决策报告</div>', unsafe_allow_html=True)
    announcement = st.text_area(
        "游戏版本公告",
        placeholder='示例：新版本「XXX」上线，新增角色「XXX」...',
        height=260,
        label_visibility="collapsed",
    )
    extra = st.text_area(
        "补充分析重点",
        placeholder="例如：更关注宣发卖点、玩家召回、社区争议、商业化风险等。",
        height=120,
    )
    return announcement, extra, "生成分析报告"


def render_feedback() -> tuple[str, str, str]:
    st.markdown('<div class="section-title">粘贴反馈</div>', unsafe_allow_html=True)
    feedback = st.text_area(
        "粘贴玩家评论、客服反馈或社区讨论",
        placeholder="可以一次粘贴多条评论，每条评论单独换行。",
        height=260,
    )
    extra = st.text_area(
        "产品背景",
        placeholder="例如：版本刚上线、活动奖励调整、玩家来自某个平台等。",
        height=120,
    )
    return feedback, extra, "生成归因报告"


def render_bilingual() -> tuple[str, str, str]:
    st.markdown('<div class="section-title">宣发信息</div>', unsafe_allow_html=True)
    campaign = st.text_area(
        "输入活动信息或版本亮点",
        placeholder="例如：活动主题、核心奖励、目标玩家、上线时间、希望传达的情绪。",
        height=240,
    )
    extra = st.text_area(
        "渠道与语气",
        placeholder="例如：适合 X/Twitter、TapTap、游戏官网；语气可活泼、克制、二次元、正式等。",
        height=120,
    )
    return campaign, extra, "生成双语文案"


def render_prompt() -> tuple[str, str, str]:
    st.markdown('<div class="section-title">原始需求</div>', unsafe_allow_html=True)
    prompt_text = st.text_area(
        "粘贴你想优化的工作指令或一句粗略需求",
        placeholder="例如：帮我分析玩家评论，找出问题并给建议。",
        height=220,
    )
    extra = st.text_area(
        "使用场景",
        placeholder="例如：用于客服日报、版本复盘、宣发文案生成、AI 运营助手等。",
        height=120,
    )
    return prompt_text, extra, "优化指令"


def run_insight_generation(
    result_key: str,
    prompt_id: str,
    fallback_prompt: str,
    user_content: str,
    empty_warning: str,
    intent_label: str,
) -> None:
    """用户洞察模式的通用生成逻辑。"""
    if not user_content.strip():
        st.warning(empty_warning)
        return

    system_prompt = read_prompt_file(prompt_id, fallback_prompt)
    start_time = time.perf_counter()
    with st.spinner("请您稍等片刻，洞察内容马上就到🚅"):
        try:
            result = run_agent_task(intent_label, user_content, system_prompt)
        except Exception as exc:
            update_runtime_status(
                api_success=False,
                duration=time.perf_counter() - start_time,
                error=str(exc),
                intent=intent_label,
            )
            st.warning("非常抱歉！分析引擎暂时遇到点小问题，请您稍后再试")
            return

    source_type = infer_analysis_source_type(result_key)
    st.session_state[f"{result_key}_warning_enabled"] = is_data_source_warning_enabled()
    report_to_save = prepare_analysis_report_for_save(
        result,
        source_type,
        include_warning=is_data_source_warning_enabled(),
    )
    st.session_state[result_key] = result
    st.session_state[f"{result_key}_path"] = ""
    update_runtime_status(
        api_success=True,
        duration=time.perf_counter() - start_time,
        error="",
        intent=intent_label,
    )
    mark_result_ready()
    st.rerun()


def render_insight_result(result_key: str, note: str, source_type: str | None = None) -> str:
    """展示用户洞察结果，并提供可复制文本框和报告文件入口。"""
    result = st.session_state.get(result_key, "")
    if not result:
        return ""

    display_result = ensure_data_source_declaration(result)
    analysis_source_type = source_type or infer_analysis_source_type(result_key)
    render_result_anchor()
    st.markdown('<div class="report-box">', unsafe_allow_html=True)
    st.markdown(f'<div class="result-note">{note}</div>', unsafe_allow_html=True)
    render_first_analysis_notice(analysis_source_type)
    if st.session_state.get(f"{result_key}_warning_enabled", is_data_source_warning_enabled()):
        render_data_source_warning(analysis_source_type)

    report_path = st.session_state.get(f"{result_key}_path", "")
    if report_path:
        st.success("内容已保存到 reports/ 文件夹")
        st.markdown(f"[前往 reports 文件夹]({reports_folder_link()})")

    st.markdown(format_report_markdown(display_result))
    if result_key == "clean_result":
        render_feedback_clean_charts(display_result)

    st.text_area(
        "\u590d\u5236\u7ed3\u679c",
        value=display_result,
        height=220,
        key=f"{result_key}_copy",
    )
    st.caption(f"\u4fdd\u5b58\u4e3a Markdown \u65f6\u4f1a\u5199\u5165\uff1a{REPORT_DIR}\uff1bJSON \u9644\u52a0\u6587\u4ef6\uff1a{'\u5f00\u542f' if ENABLE_JSON_SIDECAR else '\u5173\u95ed'}\u3002")
    if st.button("\u6570\u636e\u4fdd\u7559\u7b56\u7565", use_container_width=True, key=f"{result_key}_save_button"):
        try:
            report_to_save = prepare_analysis_report_for_save(
                result,
                analysis_source_type,
                include_warning=st.session_state.get(f"{result_key}_warning_enabled", is_data_source_warning_enabled()),
            )
            saved_path = save_report(report_to_save, "insight")
            st.session_state[f"{result_key}_path"] = str(saved_path)
            st.success(f"\u5df2\u4fdd\u5b58\u5230\uff1a{saved_path}")
        except Exception as exc:
            st.warning(str(exc))
    st.markdown("</div>", unsafe_allow_html=True)
    return display_result


def parse_distribution_from_report(report_text: str, items: list[dict[str, str]]) -> tuple[dict[str, float], bool]:
    """从清洗报告中提取分布数据；有百分比优先用百分比，否则按标签出现次数估算。"""
    values: dict[str, float] = {}
    used_estimate = False
    lines = [line.strip() for line in report_text.splitlines() if line.strip()]

    for item in items:
        explicit_value = 0.0
        for line in lines:
            if not any(alias in line for alias in item["aliases"]):
                continue
            percent_match = DISTRIBUTION_PERCENT_RE.search(line)
            count_match = DISTRIBUTION_COUNT_RE.search(line)
            if percent_match:
                explicit_value += float(percent_match.group(1))
            elif count_match:
                explicit_value += float(count_match.group(1))
        if explicit_value:
            values[item["label"]] = explicit_value

    if values:
        return values, used_estimate

    used_estimate = True
    for item in items:
        count = 0
        for line in lines:
            # 优先统计逐条反馈输出行，避免把统计标题反复算进去。
            if any(alias in line for alias in item["aliases"]) and ("|" in line or "：" in line or ":" in line):
                count += 1
        if count:
            values[item["label"]] = float(count)

    return values, used_estimate


def make_dark_figure(plt_module) -> tuple:
    """创建与页面风格接近的深色 matplotlib 图表。"""
    fig, ax = plt_module.subplots(figsize=(5.6, 3.8), dpi=130)
    fig.patch.set_facecolor("#101828")
    ax.set_facecolor("#101828")
    return fig, ax


def get_chart_font_properties():
    """为 matplotlib 图表加载中文字体，避免中文显示为空心方框。"""
    return get_chart_font_properties_cached()


@lru_cache(maxsize=1)
def get_chart_font_properties_cached():
    """缓存 matplotlib 中文字体配置，避免每次生成图表都重复扫描和注册字体。"""
    try:
        from matplotlib import font_manager
    except ImportError:
        return None

    font_candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
    ]
    for font_path in font_candidates:
        if font_path.exists():
            font_manager.fontManager.addfont(str(font_path))
            return font_manager.FontProperties(fname=str(font_path))
    return None


def render_feedback_clean_charts(report_text: str) -> None:
    """在反馈清洗报告下方生成情绪分布和发言动机分布图表。"""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        st.info("请先安装 matplotlib 后再生成图表")
        return

    chart_font = get_chart_font_properties()
    plt.rcParams["axes.unicode_minus"] = False

    emotion_items = [
        {"label": "愤怒", "aliases": ["😡", "愤怒"], "color": "#ef4444"},
        {"label": "失望", "aliases": ["😞", "失望"], "color": "#8b5cf6"},
        {"label": "困惑", "aliases": ["😕", "困惑"], "color": "#38bdf8"},
        {"label": "焦虑", "aliases": ["😰", "焦虑"], "color": "#f97316"},
        {"label": "中性", "aliases": ["😐", "中性"], "color": "#94a3b8"},
        {"label": "满意", "aliases": ["😊", "满意"], "color": "#22c55e"},
        {"label": "期待", "aliases": ["🎯", "期待"], "color": "#eab308"},
        {"label": "调侃", "aliases": ["😂", "调侃"], "color": "#ec4899"},
    ]
    motive_items = [
        {"label": "建设性意见", "aliases": ["💡", "建设性意见型", "建设性意见"], "color": "#22c55e"},
        {"label": "情绪发泄", "aliases": ["😤", "情绪发泄型", "情绪发泄"], "color": "#f97316"},
        {"label": "乐子型", "aliases": ["🏴", "乐子型发言", "乐子型"], "color": "#94a3b8"},
        {"label": "竞品拉踩", "aliases": ["⚔️", "竞品拉踩型发言", "竞品拉踩型", "竞品拉踩"], "color": "#ef4444"},
        {"label": "思维发散", "aliases": ["🔮", "思维发散型", "思维发散"], "color": "#8b5cf6"},
        {"label": "无特殊动机", "aliases": ["无特殊动机", "无动机", "普通反馈"], "color": "#38bdf8"},
    ]

    emotion_values, emotion_estimated = parse_distribution_from_report(report_text, emotion_items)
    motive_values, motive_estimated = parse_distribution_from_report(report_text, motive_items)
    if not emotion_values or not motive_values:
        st.info("数据不足，无法生成图表")
        return

    st.markdown('<div class="section-title">反馈数据可视化</div>', unsafe_allow_html=True)
    left_col, right_col = st.columns(2)

    with left_col:
        fig, ax = make_dark_figure(plt)
        labels = list(emotion_values.keys())
        values = list(emotion_values.values())
        colors = [next(item["color"] for item in emotion_items if item["label"] == label) for label in labels]
        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            startangle=90,
            textprops={"color": "#e5e7eb", "fontsize": 8, "fontproperties": chart_font},
            wedgeprops={"linewidth": 1, "edgecolor": "#101828"},
        )
        for text in texts:
            if chart_font:
                text.set_fontproperties(chart_font)
        for text in autotexts:
            text.set_color("#ffffff")
            text.set_fontweight("bold")
            if chart_font:
                text.set_fontproperties(chart_font)
        ax.set_title("基础情绪分布", color="#f8fafc", fontsize=12, pad=10, fontproperties=chart_font)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    with right_col:
        fig, ax = make_dark_figure(plt)
        sorted_motives = sorted(motive_values.items(), key=lambda item: item[1], reverse=True)
        labels = [item[0] for item in sorted_motives]
        values = [item[1] for item in sorted_motives]
        colors = [next(item["color"] for item in motive_items if item["label"] == label) for label in labels]
        ax.bar(labels, values, color=colors)
        ax.set_title("发言动机分布", color="#f8fafc", fontsize=12, pad=10, fontproperties=chart_font)
        ax.tick_params(axis="x", colors="#e5e7eb", labelrotation=25, labelsize=8)
        ax.tick_params(axis="y", colors="#e5e7eb", labelsize=8)
        for label in ax.get_xticklabels():
            if chart_font:
                label.set_fontproperties(chart_font)
        for label in ax.get_yticklabels():
            if chart_font:
                label.set_fontproperties(chart_font)
        ax.grid(axis="y", color="#344054", linewidth=0.8, alpha=0.65)
        for spine in ax.spines.values():
            spine.set_color("#344054")
        for index, value in enumerate(values):
            ax.text(index, value, f"{value:g}", ha="center", va="bottom", color="#f8fafc", fontsize=8)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    if emotion_estimated or motive_estimated:
        st.caption("基于AI分析结果估算，仅供参考")


def render_user_insight() -> None:
    """用户洞察模式：访谈助手、问卷工坊、反馈清洗三个子功能。"""
    st.markdown(
        """
        <div class="task-panel">
            <div class="task-kicker">用户洞察</div>
            <div class="task-title">把玩家研究流程拆成访谈、问卷和反馈清洗</div>
            <div class="task-desc">适合快速搭建调研提纲、问卷框架，或把大量玩家反馈整理成可行动的问题清单。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 改动位置：用可预设的横向选择控件替代原生 Tab，支持决策看板按钮直接跳转。
    insight_options = ["📋 访谈助手", "📋 问卷工坊", "🧹 反馈清洗"]
    target_insight_tab = st.session_state.pop("target_insight_tab", "")
    if target_insight_tab in insight_options:
        st.session_state.insight_workspace_tab = target_insight_tab
    selected_insight_tab = st.radio(
        "选择用户洞察工具",
        insight_options,
        horizontal=True,
        key="insight_workspace_tab",
        label_visibility="collapsed",
    )

    if selected_insight_tab == "📋 访谈助手":
        st.markdown('<div class="section-title">访谈目标</div>', unsafe_allow_html=True)
        render_prompt_feature_guide(
            "这个模块已内置用户研究 Prompt，可尝试把目标写得更具体",
            ["五层用户画像", "追问预案", "对象筛选", "观察记录表"],
            "建议写清楚：想研究什么问题、是哪类玩家、处于哪个版本阶段。这样我会输出更像真实访谈执行工具的提纲。",
        )
        col_a, col_b, col_c = st.columns(3)
        if col_a.button("填入退坑访谈示例", use_container_width=True):
            st.session_state.interview_goal = "了解近30天流失玩家的退坑原因，重点关注版本节奏、养成压力、剧情吸引力和竞品分流。希望筛选死忠用户、回流失败用户、竞品死忠和社区重度用户分别访谈。"
        if col_b.button("填入剧情满意度示例", use_container_width=True):
            st.session_state.interview_goal = "了解新版本主线剧情满意度，重点观察剧情党、轻度玩家、云玩家和社区讨论用户对角色塑造、节奏、演出和争议点的真实感受。"
        if col_c.button("填入付费压力示例", use_container_width=True):
            st.session_state.interview_goal = "了解中小额付费玩家对新卡池和礼包设计的压力感，重点追问付费动机、放弃付费节点、可接受福利和继续留存条件。"
        default_goal = st.session_state.pop("insight_to_interview", "")
        interview_goal = st.text_area(
            "输入你想通过访谈了解的问题",
            value=default_goal,
            placeholder="例如：了解玩家退坑原因；新版本剧情满意度；核心玩家对抽卡压力的真实感受。",
            height=150,
            key="interview_goal",
        )
        if st.button("生成访谈提纲", type="primary", use_container_width=True):
            fallback_prompt = """
你是一名游戏用户研究访谈助手。请基于访谈目标输出可直接执行的访谈提纲，必须包含：访谈开场白、5-8个核心问题及追问策略、访谈对象筛选建议、结束语和致谢模板。模块之间用分隔线分开，语言自然、具体、可执行。
"""
            run_insight_generation(
                "interview_result",
                "tasks/interview",
                fallback_prompt,
                interview_goal,
                "请先输入访谈目标。",
                "insight:interview",
            )
        render_insight_result("interview_result", "以下为访谈助手生成的访谈提纲。")

    if selected_insight_tab == "📋 问卷工坊":
        st.markdown('<div class="section-title">调研目标与目标用户</div>', unsafe_allow_html=True)
        render_prompt_feature_guide(
            "这个模块已升级为量化研究问卷，不只是生成题目",
            ["投放版+分析师版", "反向计分", "信效度检验", "预测试方案", "无效样本剔除"],
            "建议写清楚：调研目标、目标玩家、要验证的假设。这样我会把质控题、预测试表和量化分析框架一起生成。",
        )
        col_a, col_b, col_c = st.columns(3)
        if col_a.button("填入满意度问卷示例", use_container_width=True):
            st.session_state.survey_goal = "调研4.2版本主线剧情满意度。目标用户：已完成主线剧情的中重度玩家。希望验证剧情评价、角色喜爱度、继续游玩意愿和付费意愿之间的关系。"
        if col_b.button("填入回流问卷示例", use_container_width=True):
            st.session_state.survey_goal = "调研回流玩家对版本回归活动的体验。目标用户：近90天未登录、本版本回归且完成至少3天任务的玩家。重点验证奖励吸引力、任务压力、回流留存意愿。"
        if col_c.button("填入活动问卷示例", use_container_width=True):
            st.session_state.survey_goal = "调研限时活动参与体验。目标用户：参与活动但完成进度不同的玩家。希望判断活动入口、任务链、奖励梯度、社交分享意愿和疲劳感。"
        survey_reference = st.session_state.get("feedback_to_survey_reference", "")
        survey_goal = st.text_area(
            "输入调研目标 + 目标用户描述",
            value=survey_reference,
            placeholder="例如：调研新版本剧情满意度；目标用户为完成主线剧情的中重度玩家。",
            height=170,
            key="survey_goal",
        )
        if st.button("生成问卷", type="primary", use_container_width=True):
            fallback_prompt = """
你是一名游戏用户研究问卷设计助手。请基于调研目标和目标用户描述输出结构化问卷，必须包含：问卷标题和简介、10-15道混合题型题目、每题测量目的、题型分布说明、投放建议。模块之间用分隔线分开。
"""
            run_insight_generation(
                "survey_result",
                "tasks/survey",
                fallback_prompt,
                survey_goal,
                "请先输入调研目标和目标用户描述。",
                "insight:survey",
            )
        survey_result = render_insight_result("survey_result", "以下为问卷工坊生成的调研问卷。")
        if survey_result and st.button("将问卷结论发送到反馈清洗作为分析参考", use_container_width=True):
            st.session_state.survey_to_clean_reference = survey_result
            st.success("已发送到反馈清洗，可切换到反馈清洗 Tab 查看。")

    if selected_insight_tab == "🧹 反馈清洗":
        st.markdown('<div class="section-title">玩家反馈文本</div>', unsafe_allow_html=True)
        render_prompt_feature_guide(
            "这个模块会把玩家反馈拆成可行动的问题清单",
            ["8类基础情绪", "1-5分情绪强度", "发言动机标签", "优先级TOP问题", "情绪图表"],
            "建议一条反馈一行，并尽量保留原话。混入调侃、竞品拉踩、建设性建议也没关系，我会分开标注。",
        )
        uploaded_file = st.file_uploader("上传 txt 文件作为输入源", type=["txt"])
        uploaded_text = ""
        if uploaded_file is not None:
            uploaded_text = uploaded_file.read().decode("utf-8", errors="replace")

        reference = st.session_state.get("survey_to_clean_reference", "")
        default_feedback = uploaded_text or ""
        feedback_text = st.text_area(
            "粘贴大量玩家反馈（一条一行，或自由文本）",
            value=default_feedback,
            placeholder="例如：活动太肝了；礼包价格不合理；新角色强度太高；服务器卡顿影响体验。",
            height=260,
            key="clean_feedback_text",
        )
        if reference:
            st.info("已收到问卷工坊发送来的参考内容，本次清洗会一并参考。")

        if st.button("开始清洗", type="primary", use_container_width=True):
            fallback_prompt = """
你是一名游戏玩家反馈清洗助手。请基于玩家反馈输出：自动分类表、每条反馈情感极性、去重合并后的同类反馈组、优先级TOP N清单、每个高优问题的处理建议和回复话术模板。结果用表格和文字混合展示，模块之间用分隔线分开。
"""
            combined_feedback = f"分析参考：\n{reference}\n\n玩家反馈：\n{feedback_text}".strip()
            run_insight_generation(
                "clean_result",
                "tasks/feedback_clean",
                fallback_prompt,
                combined_feedback,
                "请先粘贴玩家反馈，或上传 txt 文件。",
                "insight:clean",
            )
        clean_result = render_insight_result("clean_result", "以下为反馈清洗生成的玩家反馈整理结果。")
        if clean_result and st.button("将反馈洞察发送到访谈助手生成追问提纲", use_container_width=True):
            st.session_state.insight_to_interview = f"基于以下反馈洞察，生成后续玩家访谈追问提纲：\n\n{clean_result}"
            st.success("已发送到访谈助手，可切换到访谈助手 Tab 查看。")


def list_competitor_files() -> list[Path]:
    """读取 works/competitor/ 下可作为竞品公告输入的文件。"""
    competitor_dir = PROJECT_DIR / "works" / "competitor"
    if not competitor_dir.exists():
        return []
    dir_stat = competitor_dir.stat()
    return list_competitor_files_by_signature(str(competitor_dir), dir_stat.st_mtime_ns)


@lru_cache(maxsize=8)
def list_competitor_files_by_signature(competitor_dir_text: str, dir_mtime_ns: int) -> list[Path]:
    """缓存竞品文件列表；目录新增/删除文件时目录签名变化，缓存自动失效。"""
    competitor_dir = Path(competitor_dir_text)
    return sorted(
        [
            file_path
            for file_path in competitor_dir.rglob("*")
            if file_path.is_file() and file_path.suffix.lower() in {".txt", ".md"}
        ]
    )


def read_competitor_file(file_path: Path) -> str:
    """读取竞品公告文件内容。"""
    file_path_text, file_mtime_ns, file_size = get_file_signature(file_path)
    return read_competitor_file_by_signature(file_path_text, file_mtime_ns, file_size)


@lru_cache(maxsize=32)
def read_competitor_file_by_signature(file_path_text: str, file_mtime_ns: int, file_size: int) -> str:
    """缓存竞品公告文件内容；文件更新后自动重新读取。"""
    return Path(file_path_text).read_text(encoding="utf-8", errors="replace")


def render_collaboration_discussion() -> None:
    """版本决策子功能：多职能协作讨论模式。"""
    st.markdown('<div class="section-title">多职能协作讨论</div>', unsafe_allow_html=True)
    baseline = st.session_state.get("version_to_competitor_baseline", "")
    default_announcement = baseline if baseline else st.session_state.get("version_decision_announcement", "")
    if baseline:
        st.info("已检测到竞品雷达中的自家版本基准，可直接作为本次协作讨论输入。")

    announcement = st.text_area(
        "版本公告或自家版本分析基准",
        value=default_announcement,
        placeholder="粘贴版本公告、更新日志，或使用从版本分析/竞品雷达带来的自家版本基准。",
        height=260,
        key="collaboration_announcement",
    )
    role_names = get_collaboration_role_names()
    selected_role_names = st.multiselect(
        "选择参与讨论的职能角色",
        role_names,
        default=role_names,
        key="collaboration_roles",
    )
    selected_goal = st.selectbox(
        "🎯 本次协作的运营目标（可选）",
        COLLABORATION_GOALS,
        key="collaboration_goal",
    )
    custom_goal = ""
    if selected_goal == "用户自定义":
        custom_goal = st.text_input(
            "请输入本次协作目标",
            placeholder="例如：降低新版本争议并提升回流用户留存",
            key="collaboration_custom_goal",
        )
    final_goal = custom_goal.strip() if selected_goal == "用户自定义" and custom_goal.strip() else selected_goal

    if st.button("开始协作分析", type="primary", use_container_width=True, key="collaboration_submit"):
        if not announcement.strip():
            st.warning("请先输入版本公告或自家版本分析基准。")
            return
        selected_roles = [get_collaboration_role_by_name(name) for name in selected_role_names]
        selected_roles = [role for role in selected_roles if role]
        if not selected_roles:
            st.warning("请至少选择一个参与讨论的职能角色。")
            return

        start_time = time.perf_counter()
        progress_slot = st.empty()
        progress_bar = st.progress(0)
        total_count = len(selected_roles)
        progress_slot.info(f"各职能角色正在从各自视角分析中...共 {total_count} 个角色")
        try:
            collaboration_payload = ORCHESTRATOR.run_collaboration(announcement, selected_roles, final_goal)
        except Exception as exc:
            update_runtime_status(False, time.perf_counter() - start_time, str(exc), "version:collaboration")
            st.warning("非常抱歉！分析引擎暂时遇到点小问题，请您稍后再试")
            return

        progress_bar.progress(1.0)
        progress_slot.info(f"协调者已根据 {final_goal} 整合各职能观点")
        role_results = collaboration_payload.get("role_results", [])
        coordinator_result = collaboration_payload.get("coordinator_result", "")
        coordinator_error = collaboration_payload.get("coordinator_error", "")
        total_count = len(role_results) or total_count
        fail_count = sum(1 for item in role_results if not item.get("success"))
        raw_report = build_collaboration_markdown(role_results, coordinator_result, final_goal)
        st.session_state.collaboration_results = role_results
        st.session_state.collaboration_goal_final = final_goal
        st.session_state.collaboration_coordinator_result = coordinator_result
        st.session_state.collaboration_coordinator_error = coordinator_error
        st.session_state.collaboration_warning_enabled = is_data_source_warning_enabled()
        st.session_state.collaboration_report_path = ""
        update_runtime_status(
            api_success=fail_count == 0 and not coordinator_error,
            duration=time.perf_counter() - start_time,
            error=coordinator_error,
            intent="version:collaboration",
        )
        mark_result_ready()
        st.rerun()

    role_results = st.session_state.get("collaboration_results", [])
    coordinator_result = st.session_state.get("collaboration_coordinator_result", "")
    goal_text = st.session_state.get("collaboration_goal_final", final_goal)
    if not role_results and not coordinator_result:
        return

    render_result_anchor()
    st.markdown('<div class="report-box">', unsafe_allow_html=True)
    st.markdown('<div class="result-note">以下为多职能协作讨论结果。</div>', unsafe_allow_html=True)
    render_first_analysis_notice("collaboration")
    if st.session_state.get("collaboration_warning_enabled", is_data_source_warning_enabled()):
        render_data_source_warning("collaboration")

    report_path = st.session_state.get("collaboration_report_path", "")
    if report_path:
        st.success("协作讨论报告已保存到 reports/collaboration/ 文件夹")
        st.markdown(f"[前往 reports 文件夹]({reports_folder_link()})")

    for item in role_results:
        role = item["role"]
        suffix = "（视角建议）" if item.get("is_suggestion") else ""
        if not item.get("success"):
            suffix = "（生成失败）"
        with st.expander(f"{role['emoji']} {role['name']}{suffix}", expanded=False):
            if item.get("is_suggestion"):
                st.caption("该角色认为公告信息不足，因此以下内容作为视角建议参考。")
                escaped_content = html.escape(item.get("content", "该视角分析生成失败")).replace("\n", "<br>")
                st.markdown(
                    f'<div style="border:1px dashed #f59e0b;border-radius:8px;padding:0.85rem;background:#fffbeb;line-height:1.7;">{escaped_content}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(format_report_markdown(item.get("content", "该视角分析生成失败")))

    st.markdown(f"### ⚖️ 协调者综合建议（目标：{goal_text}）")
    st.markdown(format_report_markdown(ensure_data_source_declaration(coordinator_result)))
    full_report = build_collaboration_markdown(role_results, coordinator_result, goal_text)
    if st.button("保存协作报告", type="primary", use_container_width=True, key="save_collaboration_report"):
        with st.spinner("正在保存协作报告..."):
            report_to_save = prepare_analysis_report_for_save(
                full_report,
                "collaboration",
                include_warning=st.session_state.get("collaboration_warning_enabled", is_data_source_warning_enabled()),
            )
            report_path = save_collaboration_report(
                report_to_save,
                goal_text,
                role_results,
                coordinator_result,
            )
            st.session_state.collaboration_report_path = str(report_path)
        st.success("报告已保存到 reports/collaboration/")
    st.text_area(
        "复制协作讨论报告",
        value=ensure_data_source_declaration(full_report),
        height=260,
        key="collaboration_copy",
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_version_decision() -> None:
    """版本决策模式：版本分析与竞品雷达。"""
    st.markdown(
        """
        <div class="task-panel">
            <div class="task-kicker">版本决策</div>
            <div class="task-title">从自家版本拆解到竞品对比，形成可执行运营判断</div>
            <div class="task-desc">先分析自家版本公告，再把结论发送到竞品雷达，辅助判断竞品动作、风险和应对策略。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 改动位置：用可预设的横向选择控件替代原生 Tab，支持决策看板跳转到指定子功能。
    version_options = ["🔍 版本分析", "📡 竞品雷达", "🤝 协作讨论"]
    target_version_tab = st.session_state.pop("target_version_tab", "")
    if target_version_tab in version_options:
        st.session_state.version_workspace_tab = target_version_tab
    selected_version_tab = st.radio(
        "选择版本决策工具",
        version_options,
        horizontal=True,
        key="version_workspace_tab",
        label_visibility="collapsed",
    )

    if selected_version_tab == "🔍 版本分析":
        st.markdown('<div class="section-title">请粘贴游戏版本公告，我将为你生成宣发决策报告</div>', unsafe_allow_html=True)
        render_prompt_feature_guide(
            "这个模块已强化数据敏感度，适合测试运营判断能力",
            ["玩家分层卖点", "爆点推理逻辑", "风险类比依据", "平台传播钩子", "后续追踪指标"],
            "建议粘贴完整公告，尤其保留角色、活动、福利、商业化、PV/音乐等信息。我会把判断写成“依据→结论→行动建议”。",
        )
        announcement = st.text_area(
            "版本公告",
            placeholder='示例：新版本「XXX」上线，新增角色「XXX」...',
            height=280,
            label_visibility="collapsed",
            key="version_decision_announcement",
        )
        if st.button("生成分析报告", type="primary", use_container_width=True, key="version_decision_submit"):
            if not announcement.strip():
                st.warning("请先粘贴版本公告。")
            else:
                start_time = time.perf_counter()
                with st.spinner("请您稍等片刻，报告马上就到🚅"):
                    try:
                        system_prompt = """
你是一名游戏版本运营决策分析助手。请基于用户粘贴的版本公告，输出六模块分析报告。
必须包含：
1. 版本内容拆解：提炼核心更新、活动、角色、系统、福利和商业化信息。
2. 卖点矩阵：按核心玩家、回流玩家、泛用户、付费玩家拆分传播卖点。
3. 宣发文案：给出可直接使用的短文案、长文案和社区话题方向。
4. 内容效果预判：判断可能带来的拉新、回流、付费、讨论热度和争议风险。每个判断都必须附带推理逻辑：
   - 爆点预测：说明是基于哪类玩家的什么行为规律得出的，禁止使用“可能会火”“大概率受欢迎”等无依据的模糊判断。
   - 风险预警：说明是基于哪个历史版本的什么数据趋势类比得出的；如果输入中没有历史数据，要明确写“需要补充历史版本数据验证”。
   - 传播建议：说明是基于哪个平台的什么传播规律选择的钩子类型。
   正确示例：“根据过往版本，剧情高光角色PV上线后72小时内B站二创投稿量通常增长40%以上，本次PV的2分15秒处角色台词可作为传播钩子，建议优先投放B站。”
5. 音乐专业分析：如公告涉及音乐、角色PV、版本PV、场景氛围或音频体验，请从音乐与情绪传达角度分析；如果没有明显音乐信息，也要说明可如何补充音乐宣发角度。
6. 宣发节奏建议：给出预热期、上线期、发酵期、复盘期的行动安排。
7. 后续追踪建议：作为报告末尾的独立区块，必须紧扣本次版本公告和前文建议，说明方案落地后应该关注哪些指标、在什么时间节点做复盘、用什么信号判断是否需要调整。不要另起新方案，不要脱离本次版本内容泛泛而谈；如果缺少历史基准或投放数据，请明确写出需要补充哪些数据，不要编造具体内部数值。
模块之间用分隔线分开，结论要具体，不要空泛。
"""
                        result = run_agent_task("version:analysis", announcement, system_prompt)
                    except Exception as exc:
                        update_runtime_status(False, time.perf_counter() - start_time, str(exc), "version:analysis")
                        st.warning("非常抱歉！分析引擎暂时遇到点小问题，请您稍后再试")
                    else:
                        result = append_ai_knowledge_notice(result)
                        st.session_state.version_analysis_result_warning_enabled = is_data_source_warning_enabled()
                        report_to_save = prepare_analysis_report_for_save(
                            result,
                            "version",
                            include_warning=is_data_source_warning_enabled(),
                        )
                        st.session_state.version_analysis_result = result
                        st.session_state.version_analysis_path = ""
                        update_runtime_status(True, time.perf_counter() - start_time, "", "version:analysis")
                        mark_result_ready()
                        st.rerun()

        version_result = render_insight_result("version_analysis_result", "以下为 AI 生成的版本分析报告，仅供参考。")
        if version_result and st.button("将此版本分析结果发送到竞品雷达作为对比基准", use_container_width=True):
            st.session_state.version_to_competitor_baseline = version_result
            st.session_state.target_version_tab = "📡 竞品雷达"
            st.session_state.version_baseline_notice = True
            st.rerun()

    if selected_version_tab == "📡 竞品雷达":
        st.markdown('<div class="section-title">竞品版本公告</div>', unsafe_allow_html=True)
        render_prompt_feature_guide(
            "这个模块会先判断竞品类型，再把竞品动作转成策略选项",
            ["竞品分类", "拆解-模仿-超越", "2x2优先级矩阵", "高风险陷阱", "借鉴风险自查"],
            "建议先选择竞品分类；如果你有竞品连续两个版本公告，可以一起粘贴，我会额外分析活动力度、付费节奏和宣发方向的变化。",
        )
        competitor_files = list_competitor_files()
        selected_text = ""
        if competitor_files:
            file_labels = ["手动粘贴"] + [file_path.relative_to(PROJECT_DIR).as_posix() for file_path in competitor_files]
            selected_label = st.selectbox("选择竞品分析专用文件", file_labels)
            if selected_label != "手动粘贴":
                selected_path = PROJECT_DIR / selected_label
                selected_text = read_competitor_file(selected_path)
                st.info(f"已加载：{selected_label}")
        else:
            st.caption("未发现 works/competitor/ 文件夹或可读取文件，可直接手动粘贴竞品公告。")

        competitor_category = st.selectbox(
            "选择竞品分类",
            [
                "未分类/通用分析",
                "同玩法同生态位竞品",
                "同生态位不同玩法竞品",
                "同玩法不同生态位竞品",
            ],
            help="不同竞品类型会影响分析权重：同玩法同生态位侧重攻防，跨玩法同生态位侧重运营方法论迁移，同玩法不同生态位侧重玩法细节拆解。",
            key="competitor_category",
        )

        competitor_text = st.text_area(
            "手动粘贴竞品版本公告",
            value=selected_text,
            placeholder="粘贴竞品版本公告、活动说明、更新日志或社区公告。",
            height=260,
            key="competitor_announcement",
        )
        baseline = st.session_state.get("version_to_competitor_baseline", "")
        if baseline:
            notice_text = "已加载自家版本数据，将作为本次竞品对比基准。"
            if st.session_state.pop("version_baseline_notice", False):
                st.success(notice_text)
            else:
                st.info(notice_text)

        if st.button("开始竞品分析", type="primary", use_container_width=True, key="competitor_submit"):
            if not competitor_text.strip():
                st.warning("请先选择或粘贴竞品版本公告。")
            else:
                fallback_prompt = """
你是一名游戏竞品运营分析助手。请基于竞品版本公告和可选的自家版本分析基准，输出竞品雷达报告。
必须包含：竞品版本核心更新摘要；与自家版本的对比分析，维度包括活动设计、福利投放、商业化节奏、宣发策略；可借鉴策略点2-3条；风险预警；综合策略建议1-2条。
报告末尾必须增加“后续追踪建议”独立区块，紧扣本次竞品动作和前文策略建议，说明后续应该关注哪些指标、在什么时间节点复盘、用什么信号判断竞品动作是否正在影响自家版本表现。不要另起新方案，不要脱离竞品公告泛泛而谈；如果没有自家版本基准，请只写竞品侧可观察指标和需要补充的自家数据，不要编造自家信息。
模块之间用分隔线分开，结论要清晰、具体、可执行。
"""
                system_prompt = read_prompt_file("tasks/competitor", fallback_prompt)
                user_content = (
                    f"竞品分类：\n{competitor_category}\n\n"
                    f"自家版本分析基准：\n{baseline}\n\n"
                    f"竞品版本公告：\n{competitor_text}"
                ).strip()
                start_time = time.perf_counter()
                with st.spinner("请您稍等片刻，竞品雷达正在扫描🚅"):
                    try:
                        result = run_agent_task("version:competitor", user_content, system_prompt)
                    except Exception as exc:
                        update_runtime_status(False, time.perf_counter() - start_time, str(exc), "version:competitor")
                        st.warning("非常抱歉！分析引擎暂时遇到点小问题，请您稍后再试")
                    else:
                        result = append_ai_knowledge_notice(result)
                        competitor_dir = REPORT_DIR / "competitor"
                        st.session_state.competitor_result_warning_enabled = is_data_source_warning_enabled()
                        report_to_save = prepare_analysis_report_for_save(
                            result,
                            "competitor",
                            include_warning=is_data_source_warning_enabled(),
                        )
                        st.session_state.competitor_result = result
                        st.session_state.competitor_result_path = ""
                        update_runtime_status(True, time.perf_counter() - start_time, "", "version:competitor")
                        mark_result_ready()
                        st.rerun()

        render_insight_result("competitor_result", "以下为竞品雷达生成的对比分析报告。")

    if selected_version_tab == "🤝 协作讨论":
        render_collaboration_discussion()


def render_activity_workshop() -> None:
    """活动策划模式：根据活动目标和活动背景生成可导出的活动方案。"""
    st.markdown(
        """
        <div class="task-panel">
            <div class="task-kicker">活动策划</div>
            <div class="task-title">把活动目标交给我，我会整理成一份可落地的运营方案</div>
            <div class="task-desc">适合快速拆解活动主题、用户路径、奖励梯度、数值范围、风险预案和宣发节奏。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">活动需求</div>', unsafe_allow_html=True)
    activity_goal = st.text_area(
        "请描述你想策划的活动目标",
        placeholder="例如：为新角色上线设计一个7天登录+任务活动，希望提升回流、分享和轻付费转化。",
        height=210,
        key="activity_goal",
    )
    activity_background = st.text_area(
        "活动背景（可选）",
        placeholder="例如：当前版本刚上线主线剧情，竞品同期发放大量福利，社区玩家对资源缺口比较敏感。",
        height=130,
        key="activity_background",
    )

    if st.button("生成活动方案", type="primary", use_container_width=True, key="activity_submit"):
        if not activity_goal.strip():
            st.warning("请先输入活动目标或活动需求。")
            return

        fallback_prompt = """
你是一名游戏运营活动策划助手。请基于用户提供的活动目标和可选活动背景，生成一份可执行、可复盘的活动方案。
输出必须包含以下模块，并用分隔线隔开：
1. 活动主题与核心玩法概述：说明活动主题、核心循环和用户为什么愿意参与。
2. 用户参与路径图：用文字描述“入口→任务链→奖励节点→最终目标”。
3. 奖励梯度设计：分基础、进阶、顶端三层，每层标注获得条件和奖励内容。
4. 数值设计参考：只给数值范围建议，例如签到天数5-7天、抽奖概率控制在某范围以内、积分门槛区间等。
5. 风险预判与应急预案：列出可能负面反馈、触发原因和应对措施。
6. 宣发节奏建议：分预热期、上线期、收尾期给出动作安排。
7. 成功指标建议：包含DAU、参与率、分享率、付费转化率等可观察指标。
8. 一句话卖点提炼：给出可用于宣发Banner的一句话。
9. 后续追踪建议：作为方案末尾的独立区块，必须紧扣前文活动主题、用户参与路径、奖励梯度和风险预案，说明活动落地后应该关注哪些指标、在什么时间节点做复盘、用什么信号判断是否需要调整。至少覆盖上线首日、活动中期、活动结束后复盘三个节点。不要另起新方案，不要脱离本活动泛泛而谈；如果缺少历史基准，请明确写出需要补充哪些数据，不要编造具体内部数值。
要求：语言具体、面向执行，不要写空泛口号；如果信息不足，请基于常见游戏运营场景给出合理假设，并标明是假设。
"""
        system_prompt = read_prompt_file("tasks/activity_workshop", fallback_prompt)
        user_content = (
            f"活动目标：\n{activity_goal.strip()}\n\n"
            f"活动背景（可选）：\n{activity_background.strip() or '用户没有补充活动背景，请根据活动目标合理假设。'}"
        )

        start_time = time.perf_counter()
        with st.spinner("请您稍等片刻，活动方案马上就到🚅"):
            try:
                # 改动位置：活动策划模式从 YAML 配置读取系统提示词，并把活动背景作为约束传入。
                result = run_agent_task("activity:workshop", user_content, system_prompt)
            except Exception as exc:
                update_runtime_status(
                    api_success=False,
                    duration=time.perf_counter() - start_time,
                    error=str(exc),
                    intent="activity:workshop",
                )
                st.warning("非常抱歉！分析引擎暂时遇到点小问题，请您稍后再试")
                return

        st.session_state.activity_plan_result = result
        st.session_state.activity_plan_result_warning_enabled = is_data_source_warning_enabled()
        st.session_state.activity_plan_path = ""
        update_runtime_status(
            api_success=True,
            duration=time.perf_counter() - start_time,
            error="",
            intent="activity:workshop",
        )
        mark_result_ready()
        st.rerun()

    result = st.session_state.get("activity_plan_result", "")
    if not result:
        return
    display_result = ensure_data_source_declaration(result)

    render_result_anchor()
    st.markdown('<div class="report-box">', unsafe_allow_html=True)
    st.markdown('<div class="result-note">以下为 AI 生成的活动策划方案，仅供参考。</div>', unsafe_allow_html=True)
    render_first_analysis_notice("activity")
    if st.session_state.get("activity_plan_result_warning_enabled", is_data_source_warning_enabled()):
        render_data_source_warning("activity")
    st.markdown(format_report_markdown(display_result))
    st.text_area(
        "复制活动方案",
        value=display_result,
        height=220,
        key="activity_plan_copy",
    )

    if st.button("导出为Markdown", use_container_width=True, key="activity_export_markdown"):
        # 改动位置：活动方案导出到独立的 activity_plans/ 文件夹，便于和分析报告区分。
        export_text = prepare_analysis_report_for_save(
            display_result,
            "activity",
            include_warning=is_data_source_warning_enabled(),
        )
        exported_path = save_activity_markdown(export_text)
        st.session_state.activity_plan_path = str(exported_path)
        st.rerun()

    exported_path = st.session_state.get("activity_plan_path", "")
    if exported_path:
        st.success("活动方案已保存到 activity_plans/ 文件夹")
        st.markdown(f"[前往 activity_plans 文件夹]({activity_folder_link()})")

    st.markdown("</div>", unsafe_allow_html=True)


def render_workflow(workflow_key: str) -> tuple[str, str, str]:
    renderers = {
        "personal": render_personal,
        "version": render_version,
        "feedback": render_feedback,
        "bilingual": render_bilingual,
        "prompt": render_prompt,
    }
    return renderers[workflow_key]()


@lru_cache(maxsize=128)
def format_report_markdown(report_text: str) -> str:
    return report_utils.format_report_markdown_cached(
        report_text,
        REPORT_HEADING_RE,
        REPORT_NUMBERED_RE,
    )


@lru_cache(maxsize=64)
def format_self_diagnosis_markdown(report_text: str) -> str:
    """格式化自我诊断 Markdown，避免纯标题被拆成异常字号。"""
    return report_utils.format_heading_only_markdown_cached(report_text, REPORT_HEADING_RE)


def reports_folder_link() -> str:
    return report_utils.folder_uri(REPORT_DIR)


def activity_folder_link() -> str:
    return report_utils.folder_uri(ACTIVITY_PLAN_DIR)


def is_admin_ready() -> bool:
    """Return whether the admin area has been initialized with a password hash."""
    return security_utils.is_admin_initialized()


def get_folder_file_count(folder: Path) -> int:
    """Count files under a folder, returning zero when the folder is missing."""
    if not folder.exists():
        return 0
    return sum(1 for item in folder.rglob("*") if item.is_file())


def get_folder_size(folder: Path) -> int:
    """Return total folder size in bytes."""
    if not folder.exists():
        return 0
    return sum(item.stat().st_size for item in folder.rglob("*") if item.is_file())


def get_report_type_counts() -> dict[str, int]:
    """Summarize report counts by folder/type for the admin overview."""
    counts: dict[str, int] = {}
    if not REPORT_DIR.exists():
        return counts
    for report_path in REPORT_DIR.rglob("*.md"):
        if "json" in report_path.parts:
            continue
        key = report_path.parent.name if report_path.parent != REPORT_DIR else "reports"
        counts[key] = counts.get(key, 0) + 1
    return counts


def get_config_yaml_files() -> list[Path]:
    """List YAML config files currently present in config/."""
    config_dir = PROJECT_DIR / "config"
    if not config_dir.exists():
        return []
    return sorted(list(config_dir.rglob("*.yaml")) + list(config_dir.rglob("*.yml")))


def get_expected_config_files() -> list[Path]:
    """Expected config files shown in the admin loading-status area."""
    agent_files = [PROJECT_DIR / "config" / "agents" / f"{role['key']}_ops.yaml" for role in COLLABORATION_ROLES]
    prompt_files = [
        config_loader.get_prompt_config_path(prompt_id)
        for prompt_id in [
            "prompt_background",
            "tasks/interview",
            "tasks/survey",
            "tasks/feedback_clean",
            "tasks/competitor",
            "tasks/activity_workshop",
            "tasks/comment_analysis",
            "tasks/collaboration_coordinator",
            "modules/base_identity",
            "modules/profile_core",
            "modules/internships",
            "modules/projects",
            "modules/game_understanding",
            "modules/portfolio",
            "modules/prompt_engineering",
            "modules/version_analysis",
            "modules/diagnosis",
        ]
    ]
    return [PROJECT_DIR / "config" / "app.yaml", *agent_files, *prompt_files]


def get_config_status(file_path: Path) -> tuple[str, str]:
    """Return a display icon and status text for a YAML file."""
    if not file_path.exists():
        return "🔴", "缺失：使用默认配置"
    if config_loader.load_yaml_config(file_path) is None:
        return "🟡", "格式异常"
    return "🟢", "已加载"


def get_streamlit_version_text() -> str:
    """读取 Streamlit 版本。"""
    try:
        return importlib_metadata.version("streamlit")
    except Exception:
        return "未检测到"


def get_memory_status_text() -> str:
    """读取可用内存；psutil 不可用时给出友好提示。"""
    try:
        import psutil

        memory = psutil.virtual_memory()
        return f"可用 {memory.available / (1024 ** 3):.2f} GB / 总计 {memory.total / (1024 ** 3):.2f} GB"
    except Exception:
        return "当前环境暂时无法读取"


def get_runtime_config_status_text() -> str:
    """读取配置目录状态。"""
    config_dir = PROJECT_DIR / "config"
    app_config_file = config_dir / "app.yaml"
    if not config_dir.exists():
        return "config 文件夹缺失"
    if not app_config_file.exists():
        return "缺少 config/app.yaml"
    return "配置正常"


def render_admin_system_info() -> None:
    """渲染管理后台系统信息。"""
    st.markdown("### 系统信息")
    api_config = get_effective_api_config()
    chroma_dir = runtime_paths.data_path("chroma_db")
    info_rows = {
        "Python版本": platform.python_version(),
        "Streamlit版本": get_streamlit_version_text(),
        "操作系统": f"{platform.system()} {platform.release()}",
        "可用内存": get_memory_status_text(),
        "知识库索引状态": "已构建" if chroma_dir.exists() else "未构建",
        "配置状态": get_runtime_config_status_text(),
        "API Key状态": mask_api_key(api_config.get("api_key", "")),
    }
    for label, value in info_rows.items():
        st.caption(f"{label}：{value}")


def render_admin_mode() -> None:
    """Lightweight admin area for system overview, knowledge base and config checks."""
    st.markdown('<div class="section-title">管理后台</div>', unsafe_allow_html=True)
    if not is_admin_ready():
        st.warning("\u7ba1\u7406\u540e\u53f0\u5c1a\u672a\u5b8c\u6210\u5b89\u5168\u521d\u59cb\u5316\u3002\u8bf7\u5148\u8bbe\u7f6e\u540e\u53f0\u5bc6\u7801\uff0c\u5bc6\u7801\u53ea\u4f1a\u4ee5\u5e26\u76d0\u54c8\u5e0c\u5f62\u5f0f\u4fdd\u5b58\u5728\u7528\u6237\u6570\u636e\u76ee\u5f55\u3002")
        new_password = st.text_input("\u8bbe\u7f6e\u7ba1\u7406\u540e\u53f0\u5bc6\u7801", type="password", key="admin_init_password")
        confirm_password = st.text_input("\u518d\u6b21\u8f93\u5165\u5bc6\u7801", type="password", key="admin_init_password_confirm")
        if st.button("\u5b8c\u6210\u540e\u53f0\u521d\u59cb\u5316", type="primary", use_container_width=True, key="admin_init_submit"):
            if len(new_password) < 8:
                st.warning("\u5bc6\u7801\u81f3\u5c11\u9700\u8981 8 \u4f4d\u3002")
            elif new_password != confirm_password:
                st.warning("\u4e24\u6b21\u8f93\u5165\u7684\u5bc6\u7801\u4e0d\u4e00\u81f4\u3002")
            else:
                security_utils.set_admin_password(new_password)
                st.session_state.admin_unlocked = True
                st.success("\u540e\u53f0\u5bc6\u7801\u5df2\u8bbe\u7f6e\u3002")
                st.rerun()
        return

    if not st.session_state.get("admin_unlocked", False):
        password = st.text_input("\u8bf7\u8f93\u5165\u7ba1\u7406\u540e\u53f0\u5bc6\u7801", type="password", key="admin_password_input")
        if st.button("\u8fdb\u5165\u7ba1\u7406\u540e\u53f0", type="primary", use_container_width=True, key="admin_login"):
            if security_utils.verify_admin_password(password):
                st.session_state.admin_unlocked = True
                st.rerun()
            st.warning("\u5bc6\u7801\u4e0d\u6b63\u786e\uff0c\u8bf7\u91cd\u65b0\u8f93\u5165\u3002")
        return

    st.markdown("### 系统概览仪表盘")
    render_admin_system_info()
    with st.expander("\u6570\u636e\u4fdd\u7559\u7b56\u7565", expanded=False):
        st.write("\u804a\u5929\u548c\u5206\u6790\u7ed3\u679c\u9ed8\u8ba4\u53ea\u5728\u9875\u9762\u5c55\u793a\u3002\u53ea\u6709\u70b9\u51fb\u4fdd\u5b58\u6216\u5bfc\u51fa\u65f6\uff0c\u624d\u4f1a\u5199\u5165\u7528\u6237\u6570\u636e\u76ee\u5f55\u3002")
        st.caption(f"\u7528\u6237\u6570\u636e\u76ee\u5f55\uff1a{runtime_paths.USER_DATA_DIR}")
        st.caption(f"\u672c\u5730\u4fdd\u5b58\uff1a{'\u5f00\u542f' if ENABLE_LOCAL_SAVE else '\u5173\u95ed'}\uff1bJSON \u9644\u52a0\u6587\u4ef6\uff1a{'\u5f00\u542f' if ENABLE_JSON_SIDECAR else '\u5173\u95ed'}")
        if st.button("\u6e05\u7406\u672c\u5730\u62a5\u544a\u4e0e\u6d3b\u52a8\u65b9\u6848", key="clear_local_saved_reports"):
            deleted = 0
            for folder in [REPORT_DIR, ACTIVITY_PLAN_DIR]:
                resolved_folder = folder.resolve()
                if folder.exists() and runtime_paths.USER_DATA_DIR.resolve() in resolved_folder.parents:
                    for item in folder.rglob("*"):
                        if item.is_file():
                            item.unlink()
                            deleted += 1
            st.success(f"\u5df2\u6e05\u7406 {deleted} \u4e2a\u672c\u5730\u4fdd\u5b58\u6587\u4ef6\u3002")


    counts = get_report_type_counts()
    if counts:
        cols = st.columns(min(len(counts), 4))
        for index, (report_type, count) in enumerate(sorted(counts.items())):
            cols[index % len(cols)].metric(report_type, count)
    else:
        st.info("reports/ 文件夹中暂未发现 Markdown 报告。")

    chroma_dir = runtime_paths.data_path("chroma_db")
    chroma_size_mb = get_folder_size(chroma_dir) / (1024 * 1024)
    st.write(f"知识库状态：{'已存在' if chroma_dir.exists() else '未构建'}，索引文件大小约 {chroma_size_mb:.2f} MB")

    st.markdown("配置加载状态：")
    for file_path in get_expected_config_files():
        icon, status = get_config_status(file_path)
        st.caption(f"{icon} {file_path.relative_to(PROJECT_DIR)}：{status}")

    st.markdown("### 知识库管理")
    if st.button("重新构建索引", use_container_width=True, key="admin_rebuild_index"):
        with st.spinner("正在重新构建知识库索引..."):
            log_buffer = io.StringIO()
            try:
                import build_index

                with contextlib.redirect_stdout(log_buffer), contextlib.redirect_stderr(log_buffer):
                    build_index.main()
                st.code(log_buffer.getvalue() or "索引构建完成。", language="text")
                st.success("知识库索引已更新")
            except Exception as exc:
                st.code(log_buffer.getvalue(), language="text")
                st.warning(f"知识库索引更新失败：{exc}")

    st.write(f"索引文件夹：{'存在' if chroma_dir.exists() else '不存在'}；文件数量：{get_folder_file_count(chroma_dir)}")

    st.markdown("### 配置检查器")
    yaml_files = sorted(set(get_config_yaml_files()) | set(get_expected_config_files()))
    if not yaml_files:
        st.info("尚未发现 YAML 配置文件。")
    for file_path in yaml_files:
        icon, status = get_config_status(file_path)
        with st.expander(f"{icon} {file_path.relative_to(PROJECT_DIR)} - {status}", expanded=False):
            if file_path.exists():
                st.code(file_path.read_text(encoding="utf-8", errors="replace"), language="yaml")
            else:
                st.caption("该 YAML 配置文件不存在，当前运行时会使用代码内置默认配置。")

    st.markdown("### 缓存管理")
    if st.button("清除对话缓存", use_container_width=True, key="admin_clear_chat_cache"):
        cache_keys = [
            "personal_messages",
            "personal_display_messages",
            "last_report",
            "last_report_path",
            "last_workflow",
            "self_diagnosis_result",
            "collaboration_results",
            "collaboration_coordinator_result",
            "collaboration_report_path",
        ]
        for key in cache_keys:
            st.session_state.pop(key, None)
        st.success("对话缓存已清除")


def save_activity_markdown(plan_text: str) -> Path:
    """保存活动方案 Markdown 文件。"""
    if not ENABLE_LOCAL_SAVE:
        raise RuntimeError("\u672c\u5730\u4fdd\u5b58\u5df2\u5173\u95ed\uff0c\u8bf7\u5728\u914d\u7f6e\u4e2d\u5f00\u542f AI_OPS_ENABLE_LOCAL_SAVE \u540e\u518d\u4fdd\u5b58\u3002")
    report_path = report_utils.save_markdown_file(plan_text, ACTIVITY_PLAN_DIR, "活动方案")
    save_report_json(report_path, plan_text, "activity")
    return report_path


def render_output(report_text: str, workflow_key: str, report_path: str = "") -> None:
    render_result_anchor()
    st.markdown('<div class="report-box">', unsafe_allow_html=True)
    if report_path:
        st.success("报告已保存到 reports/ 文件夹")
        st.markdown(f"[前往 reports 文件夹]({reports_folder_link()})")

    if workflow_key == "personal":
        st.markdown('<div class="result-note">以下为我根据个人经历整理的回答</div>', unsafe_allow_html=True)
        render_markdown_with_math(report_text)
    else:
        st.markdown('<div class="result-note">以下为 AI 生成的宣发决策报告，仅供参考</div>', unsafe_allow_html=True)
        render_first_analysis_notice("version")
        if st.session_state.get("last_report_warning_enabled", is_data_source_warning_enabled()):
            render_data_source_warning("version")
        st.markdown(format_report_markdown(ensure_data_source_declaration(report_text)))

    download_label = "下载回答" if workflow_key == "personal" else "下载报告"
    download_text = report_text if workflow_key == "personal" else prepare_analysis_report_for_save(
        report_text,
        "version",
        include_warning=is_data_source_warning_enabled(),
    )
    st.download_button(
        download_label,
        data=download_text,
        file_name=f"{WORKFLOWS[workflow_key]['label']}.txt",
        mime="text/plain",
        use_container_width=True,
    )
    st.caption(f"\u5982\u9700\u672c\u5730\u4fdd\u5b58\uff0c\u8bf7\u70b9\u51fb\u4e0b\u65b9\u6309\u94ae\u3002\u4fdd\u5b58\u4f4d\u7f6e\uff1a{REPORT_DIR}\uff1bJSON \u9644\u52a0\u6587\u4ef6\uff1a{'\u5f00\u542f' if ENABLE_JSON_SIDECAR else '\u5173\u95ed'}\u3002")
    if st.button("\u4fdd\u5b58\u5230\u672c\u5730\u62a5\u544a\u6587\u4ef6\u5939", use_container_width=True, key=f"save_last_report_{workflow_key}"):
        try:
            saved_path = save_report(download_text, workflow_key)
            st.session_state.last_report_path = str(saved_path)
            st.success(f"\u5df2\u4fdd\u5b58\u5230\uff1a{saved_path}")
        except Exception as exc:
            st.warning(str(exc))

    st.markdown("</div>", unsafe_allow_html=True)


def render_chat_history() -> None:
    """改动位置：使用 Streamlit 原生聊天气泡，避免 HTML 代码被页面露出。"""
    messages = st.session_state.get("personal_display_messages", [])

    if not messages:
        st.markdown(
            '<div class="chat-empty">这里会保留您和 AI 运营分身的对话记录。您可以从下方输入问题，或展开常见问题快速开始。</div>',
            unsafe_allow_html=True,
        )
        return

    render_result_anchor()
    with st.container(height=460, border=True):
        for message in messages:
            role = message.get("role", "assistant")
            content = message.get("content", "")
            if role == "user":
                with st.chat_message("user", avatar="🧑"):
                    st.markdown(content)
            else:
                with st.chat_message("assistant", avatar="🎧"):
                    render_markdown_with_math(content)


def build_agent_input(workflow_key: str, user_content: str, extra_context: str = "") -> str:
    """改动位置：为 LangGraph 生成更明确的用户输入，帮助它稳定识别意图。"""
    extra_block = f"\n\n补充背景：\n{extra_context.strip()}" if extra_context.strip() else ""
    if workflow_key == "personal":
        return f"{user_content.strip()}{extra_block}"

    workflow_label = WORKFLOWS.get(workflow_key, WORKFLOWS["version"])["label"]
    return (
        f"请基于以下内容生成版本公告分析报告，并测试工作能力。"
        f"\n当前工作流：{workflow_label}\n\n"
        f"{user_content.strip()}{extra_block}"
    )


def get_agent_messages(workflow_key: str, agent_input: str) -> list[dict[str, str]]:
    """改动位置：为了解我模式保留多轮上下文，工作测试保持单轮避免报告互相污染。"""
    if workflow_key != "personal":
        return [{"role": "user", "content": agent_input}]

    if "personal_messages" not in st.session_state:
        st.session_state.personal_messages = []

    return [*st.session_state.personal_messages, {"role": "user", "content": agent_input}]


def remember_agent_turn(workflow_key: str, agent_input: str, result: str) -> None:
    """改动位置：记录了解我模式的问答历史，最多保留最近 8 轮。"""
    if workflow_key != "personal":
        return

    if "personal_messages" not in st.session_state:
        st.session_state.personal_messages = []

    st.session_state.personal_messages.extend(
        [
            {"role": "user", "content": agent_input},
            {"role": "assistant", "content": result},
        ]
    )
    st.session_state.personal_messages = st.session_state.personal_messages[-16:]


def remember_display_turn(workflow_key: str, user_content: str, result: str) -> None:
    """改动位置：记录用于页面展示的气泡消息，不展示隐藏的补充背景文本。"""
    if workflow_key != "personal":
        return

    if "personal_display_messages" not in st.session_state:
        st.session_state.personal_display_messages = []

    st.session_state.personal_display_messages.extend(
        [
            {"role": "user", "content": user_content.strip()},
            {"role": "assistant", "content": result},
        ]
    )
    st.session_state.personal_display_messages = st.session_state.personal_display_messages[-16:]


def call_direct_deepseek_fallback(workflow_key: str, user_content: str, extra_context: str = "") -> str:
    """改动位置：LangGraph 失败时回退到原有 DeepSeek 直连逻辑。"""
    messages = build_messages(workflow_key, user_content, extra_context)
    return call_deepseek_api(messages)


def main() -> None:
    if ensure_default_config_files():
        st.session_state.default_config_generated = True

    if not st.session_state.get("skip_first_use_config") and not has_available_model_access():
        render_first_use_config_page()
        st.stop()

    if "entry_confirmed" not in st.session_state:
        st.session_state.entry_confirmed = False

    if not st.session_state.entry_confirmed:
        setup_entry_page()
        render_entry_dialog()
        st.stop()

    setup_page()
    init_runtime_status()
    workflow_key = render_sidebar()

    if workflow_key == "dashboard":
        render_decision_dashboard()
        render_footer()
        return

    if workflow_key == "admin":
        render_header()
        render_admin_mode()
        render_footer()
        return

    render_header()
    render_data_source_config()
    render_mode_context(workflow_key)

    if workflow_key == "personal":
        render_about_mode()
        render_footer()
        return

    if workflow_key == "version":
        render_version_decision()
        render_footer()
        return

    if workflow_key == "insight":
        render_user_insight()
        render_footer()
        return

    if workflow_key == "activity":
        render_activity_workshop()
        render_footer()
        return

    user_content, extra_context, button_label = render_workflow(workflow_key)

    if "last_report" not in st.session_state:
        st.session_state.last_report = ""
    if "last_workflow" not in st.session_state:
        st.session_state.last_workflow = workflow_key
    if "last_report_path" not in st.session_state:
        st.session_state.last_report_path = ""
    current_prompt_signature = get_prompt_signature()
    if "prompt_signature" not in st.session_state:
        st.session_state.prompt_signature = current_prompt_signature
    elif st.session_state.prompt_signature != current_prompt_signature:
        st.session_state.prompt_signature = current_prompt_signature
        st.session_state.last_report = ""
        st.session_state.last_report_path = ""
        st.session_state.last_workflow = workflow_key

    button_slot = st.empty()
    submitted = button_slot.button(button_label, type="primary", use_container_width=True)
    auto_submitted = bool(st.session_state.pop("auto_submit_personal", False))

    if submitted or auto_submitted:
        if not user_content.strip():
            st.warning("请先输入要处理的内容。")
            render_footer()
            return

        button_slot.button("正在分析中...", disabled=True, use_container_width=True)
        with st.spinner("请您稍等片刻，报告马上就到🚅"):
            start_time = time.perf_counter()
            try:
                # 改动位置：所有模式统一交给 LangGraph 完成意图识别、检索增强和回复生成。
                agent_input = build_agent_input(workflow_key, user_content, extra_context)
                agent_messages = get_agent_messages(workflow_key, agent_input)
                result, detected_intent = run_agent_graph(agent_input, messages=agent_messages)
            except Exception as agent_exc:
                try:
                    # 改动位置：如果 LangGraph 调用失败，保留原有 DeepSeek 直连兜底。
                    result = call_direct_deepseek_fallback(workflow_key, user_content, extra_context)
                    detected_intent = f"fallback:{workflow_key}"
                except Exception as exc:
                    update_runtime_status(
                        api_success=False,
                        duration=time.perf_counter() - start_time,
                        error=f"LangGraph：{agent_exc}\n\nDeepSeek 兜底：{exc}",
                        intent=get_agent_last_intent(),
                    )
                    st.warning("非常抱歉！分析引擎暂时遇到点小问题，请您稍后再试")
                    render_footer()
                    return

            if not result:
                update_runtime_status(
                    api_success=False,
                    duration=time.perf_counter() - start_time,
                    error="没有生成有效内容。",
                    intent=detected_intent,
                )
                st.warning("非常抱歉！分析引擎暂时遇到点小问题，请您稍后再试")
                render_footer()
                return

        if workflow_key == "personal":
            report_to_save = result
        else:
            st.session_state.last_report_warning_enabled = is_data_source_warning_enabled()
            report_to_save = prepare_analysis_report_for_save(
                result,
                "version",
                include_warning=is_data_source_warning_enabled(),
            )
        update_runtime_status(
            api_success=True,
            duration=time.perf_counter() - start_time,
            error="",
            intent=detected_intent,
        )
        st.session_state.last_report = result
        st.session_state.last_workflow = workflow_key
        st.session_state.last_report_path = ""
        remember_agent_turn(workflow_key, agent_input, result)
        remember_display_turn(workflow_key, user_content, result)
        mark_result_ready()
        # 改动位置：生成完成后立即刷新页面，避免按钮继续停留在“正在分析中...”状态。
        st.rerun()

    if workflow_key != "personal" and st.session_state.last_report and st.session_state.last_workflow == workflow_key:
        render_output(st.session_state.last_report, workflow_key, st.session_state.last_report_path)

    render_footer()


if __name__ == "__main__":
    main()
