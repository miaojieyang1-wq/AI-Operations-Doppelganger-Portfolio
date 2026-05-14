"""
核心业务编排层。

这个文件不依赖 Streamlit，只负责调用 LangGraph、RAG、DeepSeek API
和多职能协作讨论等后台能力。app.py 只需要把用户输入传进来，
再把这里返回的普通 Python 字典展示到页面上。
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import api_runtime
import rag_engine
from collaboration_config import COLLABORATION_ROLES
from config_loader import get_agent_prompt, get_system_prompt


class Orchestrator:
    """AI 运营分身的核心业务编排器。"""

    def __init__(
        self,
        default_temperature: float | None = None,
        role_temperature: float | None = None,
        coordinator_temperature: float | None = None,
    ) -> None:
        self.default_temperature = default_temperature
        self.role_temperature = role_temperature
        self.coordinator_temperature = coordinator_temperature

    def call_chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
    ) -> str:
        """调用 DeepSeek/OpenAI 兼容聊天接口。"""
        return api_runtime.call_chat_completion(messages, temperature=temperature)

    def get_api_config(self) -> dict[str, str]:
        """读取当前会话实际使用的模型接口配置。"""
        return api_runtime.get_api_config()

    def create_client(self):
        """创建 OpenAI 兼容客户端。"""
        return api_runtime.create_client()

    def test_connection(self, api_key: str, base_url: str, model_name: str) -> tuple[bool, str]:
        """测试用户输入的模型接口配置是否可用。"""
        return api_runtime.test_connection(api_key, base_url, model_name)

    def call_with_system_prompt(
        self,
        system_prompt: str,
        user_content: str,
        temperature: float | None = None,
    ) -> str:
        """使用系统提示词和用户内容调用大模型。"""
        return self.call_chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=temperature,
        )

    def query_rag(self, user_question: str, system_prompt: str) -> dict[str, Any]:
        """调用本地知识库增强问答。"""
        try:
            content = rag_engine.query_rag(user_question, system_prompt)
            return {"success": True, "content": content, "error": ""}
        except Exception as exc:
            return {"success": False, "content": "", "error": str(exc)}

    def run_chat(
        self,
        user_input: str,
        session_id: str = "default",
        messages: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """用于“了解我”聊天，走 LangGraph 意图识别与生成流程。"""
        try:
            from agent_graph import get_last_intent, run as agent_run

            content = agent_run(user_input, messages=messages)
            return {
                "success": True,
                "content": content,
                "intent": get_last_intent(),
                "session_id": session_id,
                "error": "",
            }
        except Exception as exc:
            return {
                "success": False,
                "content": "",
                "intent": "",
                "session_id": session_id,
                "error": str(exc),
            }

    def run_task(
        self,
        task_key: str,
        user_content: str,
        system_prompt: str = "",
    ) -> dict[str, Any]:
        """调用 LangGraph 的指定任务入口。"""
        try:
            from agent_graph import run_task

            content = run_task(task_key, user_content, system_prompt=system_prompt)
            return {
                "success": True,
                "content": content,
                "intent": task_key,
                "error": "",
            }
        except Exception as exc:
            return {
                "success": False,
                "content": "",
                "intent": task_key,
                "error": str(exc),
            }

    def run_version_analysis(self, announcement_text: str, system_prompt: str = "") -> dict[str, Any]:
        """用于“版本分析”。"""
        return self.run_task("version:analysis", announcement_text, system_prompt)

    def run_feedback_clean(self, feedback_list: str | list[str], system_prompt: str = "") -> dict[str, Any]:
        """用于“反馈清洗”。"""
        if isinstance(feedback_list, list):
            user_content = "\n".join(str(item) for item in feedback_list)
        else:
            user_content = feedback_list
        return self.run_task("insight:feedback_clean", user_content, system_prompt)

    def run_competitor_analysis(self, user_content: str, system_prompt: str = "") -> dict[str, Any]:
        """用于“竞品雷达”。"""
        return self.run_task("version:competitor", user_content, system_prompt)

    def run_activity_workshop(self, user_content: str, system_prompt: str = "") -> dict[str, Any]:
        """用于“活动策划”。"""
        return self.run_task("activity:workshop", user_content, system_prompt)

    def build_role_user_content(self, announcement: str, goal: str) -> str:
        """构造单个职能角色的输入内容。"""
        return f"本次协作运营目标：{goal}\n\n版本公告：\n{announcement.strip()}"

    def run_collaboration_role(self, role: dict[str, Any], announcement: str, goal: str) -> dict[str, Any]:
        """独立调用单个职能角色；失败不影响其他角色。"""
        agent_id = f"{role['key']}_ops"
        system_prompt = get_agent_prompt(agent_id)
        user_content = self.build_role_user_content(announcement, goal)
        try:
            content = self.call_with_system_prompt(
                system_prompt,
                user_content,
                temperature=self.role_temperature,
            )
            missing_phrase = role.get("missing_phrase", "")
            is_suggestion = bool(missing_phrase and missing_phrase in content) or "视角建议" in content
            return {
                "role": role,
                "content": content,
                "success": True,
                "is_suggestion": is_suggestion,
                "error": "",
            }
        except Exception as exc:
            return {
                "role": role,
                "content": "该视角分析生成失败",
                "success": False,
                "is_suggestion": False,
                "error": str(exc),
            }

    def build_coordinator_prompt(self) -> str:
        """从 YAML 读取协作讨论协调者系统提示词。"""
        return get_system_prompt("tasks/collaboration_coordinator")

    def build_coordinator_user_content(self, role_results: list[dict[str, Any]], goal: str) -> str:
        """把所有角色观点拼接给协调者。"""
        blocks = [f"本次协作目标：{goal}", "以下是各职能专家观点："]
        for item in role_results:
            role = item["role"]
            status = "视角建议" if item.get("is_suggestion") else "正式意见"
            if not item.get("success"):
                status = "生成失败"
            blocks.append(f"\n## {role['emoji']} {role['name']}（{status}）\n{item.get('content', '').strip()}")
        return "\n".join(blocks)

    def run_collaboration(
        self,
        announcement_text: str,
        agents: list[dict[str, Any]] | list[str] | None = None,
        goal: str = "无特定目标（综合评估）",
    ) -> dict[str, Any]:
        """用于“协作讨论”，并发调用各角色后再调用协调者。"""
        selected_roles = self._normalize_roles(agents)
        role_results: list[dict[str, Any]] = []
        total_count = len(selected_roles)
        if total_count == 0:
            return {
                "success": False,
                "role_results": [],
                "coordinator_result": "",
                "coordinator_error": "",
                "error": "未选择参与讨论的职能角色",
            }

        with ThreadPoolExecutor(max_workers=min(total_count, 10)) as executor:
            future_map = {
                executor.submit(self.run_collaboration_role, role, announcement_text, goal): role
                for role in selected_roles
            }
            for future in as_completed(future_map):
                role_results.append(future.result())

        role_order = {role["key"]: index for index, role in enumerate(COLLABORATION_ROLES)}
        role_results.sort(key=lambda item: role_order.get(item["role"]["key"], 999))
        success_count = sum(1 for item in role_results if item.get("success"))
        fail_count = total_count - success_count

        coordinator_result = ""
        coordinator_error = ""
        if fail_count > total_count / 2:
            coordinator_result = "有效分析不足，无法生成综合建议"
        else:
            try:
                coordinator_result = self.call_with_system_prompt(
                    self.build_coordinator_prompt(),
                    self.build_coordinator_user_content(role_results, goal),
                    temperature=self.coordinator_temperature,
                )
            except Exception as exc:
                coordinator_error = str(exc)
                coordinator_result = "综合建议生成失败，请手动整合各职能观点"

        return {
            "success": fail_count == 0 and not coordinator_error,
            "role_results": role_results,
            "coordinator_result": coordinator_result,
            "coordinator_error": coordinator_error,
            "error": coordinator_error,
        }

    def _normalize_roles(self, agents: list[dict[str, Any]] | list[str] | None) -> list[dict[str, Any]]:
        """把角色名、角色 key 或角色 dict 统一成角色配置 dict。"""
        if agents is None:
            return list(COLLABORATION_ROLES)
        role_by_name = {role["name"]: role for role in COLLABORATION_ROLES}
        role_by_key = {role["key"]: role for role in COLLABORATION_ROLES}
        normalized = []
        for item in agents:
            if isinstance(item, dict):
                normalized.append(item)
            elif isinstance(item, str) and item in role_by_name:
                normalized.append(role_by_name[item])
            elif isinstance(item, str) and item in role_by_key:
                normalized.append(role_by_key[item])
        return normalized
