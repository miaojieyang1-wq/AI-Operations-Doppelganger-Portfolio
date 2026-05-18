"""
这个模块是 AI 运营分身的流程编排引擎，使用 LangGraph 定义 Agent 的处理流程。

工作流程：
意图识别 → 检索增强 → 生成回复

三个意图类型：
- chat：普通了解我 / 面试问答场景，回答个人经历、能力与背景。
- works：作品集查询场景，重点回答提示词工程、SEO文章、方法论和作品集验证能力。
- analysis：运营决策分析场景，适合版本公告、测试工作能力和宣发决策报告。
"""

from contextvars import ContextVar
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

import prompt_loader
import rag_engine
import api_runtime
import config_loader


PROJECT_DIR = Path(__file__).parent
WORKS_DIR = PROJECT_DIR / "works"
MATH_FULL_FILE = WORKS_DIR / "mathematics-full.md"
MATH_SEGMENT_DIR = WORKS_DIR / "math-segments"
LAST_INTENT: ContextVar[str] = ContextVar("LAST_INTENT", default="")
LAST_PROMPT_MODULES: ContextVar[list[str]] = ContextVar("LAST_PROMPT_MODULES", default=[])

MATH_FULL_TRIGGERS = ["展示完整公式组", "你的数学骨架是什么", "整套数学体系", "完整公式组", "完整数学体系"]
MATH_FOLLOWUP_TRIGGERS = ["公式", "公式组", "数学公式", "展开公式", "给我公式"]
MATH_CONTEXT_KEYWORDS = [
    "战术引擎",
    "星铁",
    "星穹铁道",
    "排轴",
    "战斗模拟",
    "数学思路",
    "数学体系",
    "数学骨架",
    "状态空间",
    "状态转移函数",
    "目标泛函",
    "模块写入权",
    "剪枝条件",
    "受击分支",
]
MATH_SEGMENT_KEYWORDS = {
    "mathematics-01-state-space.md": ["战斗状态空间", "状态空间", "七元组", "各分量", "值域定义"],
    "mathematics-02-transfer-function.md": ["状态转移函数", "转移函数", "操作与事件空间", "复合"],
    "mathematics-03-module-isolation.md": ["模块写入权", "写入权", "写入权隔离", "独占变量"],
    "mathematics-04-constraints.md": ["约束条件", "资源约束", "韧性约束", "状态约束"],
    "mathematics-05-search-space.md": ["搜索空间", "搜索树", "窗口提取", "合法操作集"],
    "mathematics-06-objective-functional.md": ["目标泛函", "惩罚项", "能量惩罚", "战技点惩罚", "J("],
    "mathematics-07-pruning.md": ["剪枝条件", "硬剪枝", "启发式剪枝", "容忍度加速"],
    "mathematics-08-hit-branches.md": ["受击分支", "受击回能", "分支生成", "剩余窗口"],
    "mathematics-09-algorithm.md": ["求解算法", "伪代码", "深度优先搜索", "DFS"],
    "mathematics-10-correctness.md": ["模块自洽性定理", "自洽性", "定理", "证明概要"],
}


class State(TypedDict):
    """LangGraph 状态对象，记录一次用户问题的处理过程。"""

    messages: list[dict[str, str]]
    intent: str
    retrieved_context: str
    final_response: str
    prompt_modules: list[str]


class TaskState(TypedDict):
    """任务型 LangGraph 状态：用于固定工具类功能，不做作品集 RAG 检索。"""

    task_key: str
    user_content: str
    system_prompt: str
    final_response: str
    prompt_modules: list[str]


def read_prompt_background() -> str:
    """从 YAML 配置读取基础背景提示词。"""
    return config_loader.get_system_prompt("prompt_background")

def get_latest_user_input(state: State) -> str:
    """从对话历史中取出最后一条用户输入。"""
    for message in reversed(state["messages"]):
        if message.get("role") == "user":
            return message.get("content", "")
    return ""


def has_math_context(text: str) -> bool:
    """判断文本是否处在战术引擎数学语境中。"""
    return any(keyword in text for keyword in MATH_CONTEXT_KEYWORDS)


def get_recent_user_context(messages: list[dict[str, str]] | None, latest_input: str) -> str:
    """提取最近用户上下文，用于识别“公式”等短追问。"""
    if not messages:
        return latest_input
    user_messages = [
        message.get("content", "")
        for message in messages
        if message.get("role") == "user"
    ]
    if not user_messages or user_messages[-1] != latest_input:
        user_messages.append(latest_input)
    return "\n".join(user_messages[-4:])


def is_math_full_display_request(user_input: str, messages: list[dict[str, str]] | None = None) -> bool:
    """判断是否需要完整展示公式组；该路径直接读文件，不走 RAG 和模型生成。"""
    if any(trigger in user_input for trigger in MATH_FULL_TRIGGERS):
        return True
    if "公式" in user_input and has_math_context(user_input):
        return True
    compact_input = user_input.strip()
    if compact_input in MATH_FOLLOWUP_TRIGGERS and has_math_context(get_recent_user_context(messages, user_input)):
        return True
    return False


def read_math_full_for_display() -> str:
    """读取完整公式组，并用页面公式渲染标记包裹。"""
    if not MATH_FULL_FILE.exists():
        return "完整公式组文件暂未找到，请先确认 works/mathematics-full.md 是否存在。"
    return f"$$$LATEX_START$$$\n{MATH_FULL_FILE.read_text(encoding='utf-8')}\n$$$LATEX_END$$$"


def retrieve_math_segment_context(user_input: str) -> str:
    """按关键词读取对应公式分段，保证分段展示时公式块不被切碎。"""
    matched_segments: list[str] = []
    for filename, keywords in MATH_SEGMENT_KEYWORDS.items():
        if any(keyword in user_input for keyword in keywords):
            segment_path = MATH_SEGMENT_DIR / filename
            if segment_path.exists():
                matched_segments.append(segment_path.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(matched_segments)


def node_prepare_task_prompt(state: TaskState) -> TaskState:
    """任务图节点一：确认本次工具任务使用的系统提示词。"""
    if state.get("system_prompt", "").strip():
        state["prompt_modules"] = [f"task:{state['task_key']}", "external_prompt"]
        return state

    if state["task_key"] == "version:analysis":
        system_prompt, modules = prompt_loader.compose_prompt(state["user_content"], "analysis")
        state["system_prompt"] = system_prompt
        state["prompt_modules"] = modules
    else:
        state["system_prompt"] = read_prompt_background()
        state["prompt_modules"] = [f"task:{state['task_key']}", "prompt_background"]

    return state


def node_generate_task_response(state: TaskState) -> TaskState:
    """任务图节点二：调用模型生成工具类分析结果。"""
    state["final_response"] = rag_engine.call_deepseek_api(
        state["system_prompt"],
        state["user_content"],
    )
    return state


def build_task_graph():
    """构建固定任务型 LangGraph：准备提示词 → 生成结果。"""
    graph_builder = StateGraph(TaskState)
    graph_builder.add_node("node_prepare_task_prompt", node_prepare_task_prompt)
    graph_builder.add_node("node_generate_task_response", node_generate_task_response)

    graph_builder.add_edge(START, "node_prepare_task_prompt")
    graph_builder.add_edge("node_prepare_task_prompt", "node_generate_task_response")
    graph_builder.add_edge("node_generate_task_response", END)

    return graph_builder.compile()


def node_classify_intent(state: State) -> State:
    """节点一：根据用户输入识别意图类型。"""
    user_input = get_latest_user_input(state)

    analysis_keywords = ["版本公告", "分析报告", "测试工作", "宣发决策", "运营决策", "版本分析"]
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
    works_keywords = [
        "作品集",
        "提示词工程",
        "四层缝合",
        "SEO文章",
        "方法论",
        "完整公式组",
        "数学骨架",
        "整套数学体系",
        "状态转移函数",
        "目标泛函",
        "模块写入权",
        "剪枝条件",
        "受击分支",
        "迭代记录",
        "本Agent",
        "本 Agent",
        "这个Agent",
        "这个 Agent",
        "所有功能",
        "功能并指引",
        "如何操作",
        "运营路线图",
        "决策看板",
        "演示模式",
        "多职能协作",
    ]

    if any(keyword in user_input for keyword in feature_keywords) and any(keyword in user_input for keyword in usage_keywords):
        state["intent"] = "works"
    elif any(keyword in user_input for keyword in analysis_keywords):
        state["intent"] = "analysis"
    elif any(keyword in user_input for keyword in works_keywords):
        state["intent"] = "works"
    else:
        state["intent"] = "chat"

    return state


def retrieve_local_context(user_input: str) -> str:
    """调用 rag_engine 的本地知识库检索能力，返回相关文档内容。"""
    context_blocks: list[str] = []
    math_segment_context = retrieve_math_segment_context(user_input)
    if math_segment_context:
        context_blocks.append(
            "以下是从 works/math-segments/ 中直接读取的公式分段，请完整保留公式块，并结合自然语言解释其含义和设计逻辑：\n\n"
            f"{math_segment_context}"
        )

    if any(
        keyword in user_input
        for keyword in [
            "作品集",
            "完整公式组",
            "数学骨架",
            "整套数学体系",
            "状态转移函数",
            "目标泛函",
            "模块写入权",
            "剪枝条件",
            "受击分支",
            "本Agent",
            "本 Agent",
            "这个Agent",
            "这个 Agent",
            "所有功能",
            "运营路线图",
            "用户洞察",
            "版本决策",
            "竞品雷达",
            "反馈清洗",
            "活动策划模式",
            "演示模式",
            "多职能协作",
            "数据源真实性预警",
            "数据源预警",
        ]
    ):
        # 改动位置：作品集概览问题优先补充网站本身，避免只命中文档中段。
        context_blocks.append(
            """
AI运营分身作品集网站是当前作品集的核心综合作品。它基于 Streamlit 搭建，调用 DeepSeek API，
接入本地 RAG 知识库，并使用 LangGraph 加入“意图识别 → 检索增强 → 生成回复”的流程编排层。
当前功能包括：运营路线图、关于我、作品集原文预览、自我诊断、用户洞察、版本决策、竞品雷达、
多职能协作讨论、活动策划、演示模式、数据源真实性预警、结果区自动定位和首屏加载优化。
回答“本 Agent 功能 / 如何操作”时必须优先介绍这个网站本身和使用路径，不要回答成个人简历概览。
回答作品集时必须优先介绍这个网站本身，再介绍 SEO 提示词工程、迭代记录和文章成品。
""".strip()
        )

    vectorstore = rag_engine.load_vectorstore()
    if vectorstore is None:
        return "\n\n---\n\n".join(context_blocks)

    try:
        query_embedding = rag_engine.encode_query(user_input)
        chunks = rag_engine.retrieve_top_chunks(vectorstore, query_embedding, top_k=3)
    except Exception:
        return "\n\n---\n\n".join(context_blocks)

    context_blocks.extend(chunks)
    return "\n\n---\n\n".join(context_blocks)


def node_retrieve_context(state: State) -> State:
    """节点二：根据意图决定是否检索本地作品集知识库。"""
    user_input = get_latest_user_input(state)
    topic = prompt_loader.detect_topic(user_input, state["intent"])

    if api_runtime.demo_engine.is_demo_mode():
        state["retrieved_context"] = ""
        return state

    # 改动位置：只有作品集 / 提示词工程等需要材料支撑的问题才检索 works/，
    # 避免普通面试问题和工具型任务被无关文档稀释注意力。
    if state["intent"] == "works" or topic in {"portfolio", "prompt_engineering"}:
        state["retrieved_context"] = retrieve_local_context(user_input)
    else:
        state["retrieved_context"] = ""

    return state


def build_system_prompt(intent: str, retrieved_context: str = "") -> str:
    """保留旧函数签名，实际由 prompt_loader 按需组合。"""
    system_prompt, _ = prompt_loader.compose_prompt("", intent, retrieved_context)
    return system_prompt


def node_generate_response(state: State) -> State:
    """节点三：拼接系统提示词和检索上下文，调用 DeepSeek 生成最终回复。"""
    user_input = get_latest_user_input(state)
    system_prompt, modules = prompt_loader.compose_prompt(
        user_input,
        state["intent"],
        state["retrieved_context"],
    )
    state["prompt_modules"] = modules
    state["final_response"] = rag_engine.call_deepseek_api(system_prompt, user_input)
    return state


def build_graph():
    """构建 LangGraph 流程图。"""
    graph = StateGraph(State)
    graph.add_node("node_classify_intent", node_classify_intent)
    graph.add_node("node_retrieve_context", node_retrieve_context)
    graph.add_node("node_generate_response", node_generate_response)

    graph.add_edge(START, "node_classify_intent")
    graph.add_edge("node_classify_intent", "node_retrieve_context")
    graph.add_edge("node_retrieve_context", "node_generate_response")
    graph.add_edge("node_generate_response", END)

    return graph.compile()


AGENT_GRAPH = build_graph()
TASK_GRAPH = build_task_graph()

# 兼容外部查看工作流结构：app.py 会按 graph.get_graph() 读取流程图文本。
graph = AGENT_GRAPH


def run(user_input: str, messages: list[dict[str, str]] | None = None) -> str:
    """执行完整 Agent 流程，并返回最终回复。"""
    if is_math_full_display_request(user_input, messages):
        LAST_INTENT.set("works:math-full")
        LAST_PROMPT_MODULES.set(["direct:works/mathematics-full.md"])
        return read_math_full_for_display()

    graph_messages = messages[:] if messages else []
    if not graph_messages or graph_messages[-1].get("content") != user_input:
        graph_messages.append({"role": "user", "content": user_input})

    initial_state: State = {
        # 改动位置：支持传入历史消息，让 LangGraph 能理解多轮追问。
        "messages": graph_messages,
        "intent": "",
        "retrieved_context": "",
        "final_response": "",
        "prompt_modules": [],
    }
    final_state = AGENT_GRAPH.invoke(initial_state)
    LAST_INTENT.set(final_state.get("intent", ""))
    LAST_PROMPT_MODULES.set(final_state.get("prompt_modules", []))
    return final_state["final_response"]


def run_task(task_key: str, user_content: str, system_prompt: str = "") -> str:
    """执行固定工具类任务，让版本分析、用户洞察等功能也经过 LangGraph。"""
    initial_state: TaskState = {
        "task_key": task_key,
        "user_content": user_content,
        "system_prompt": system_prompt,
        "final_response": "",
        "prompt_modules": [],
    }
    final_state = TASK_GRAPH.invoke(initial_state)
    LAST_INTENT.set(task_key)
    LAST_PROMPT_MODULES.set(final_state.get("prompt_modules", []))
    return final_state["final_response"]


def get_last_intent() -> str:
    """返回最近一次 LangGraph 识别出的意图类型。"""
    return LAST_INTENT.get()


def get_last_prompt_modules() -> list[str]:
    """返回最近一次调用实际加载的 Prompt 模块，方便运行状态和自检。"""
    return LAST_PROMPT_MODULES.get()


if __name__ == "__main__":
    # 本地调试入口：用于手动测试 LangGraph 流程。
    question = input("请输入问题：").strip()
    if not question:
        raise SystemExit("没有输入问题，已退出。")
    print(run(question))
