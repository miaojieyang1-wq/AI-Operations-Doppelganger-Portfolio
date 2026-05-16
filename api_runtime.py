"""AI 服务调用运行层。

这个模块只处理和外部大模型服务有关的通用逻辑：
- 读取当前进程环境中的 API Key、接口地址和模型名
- 创建 OpenAI 兼容客户端
- 在演示模式下读取本地演示结果
- 发起普通 Chat Completions 调用

网页里的 API 输入框仍由 app.py 负责；app.py 会把用户输入同步到 os.environ，
本模块再从 os.environ 读取即可。这样 app.py、rag_engine.py 和 agent_graph.py
共享同一套调用逻辑。
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

import config_loader
import demo_engine
import runtime_paths


APP_CONFIG = config_loader.load_app_config()
DEFAULT_MODEL = APP_CONFIG["model"]["default_model"]
DEFAULT_BASE_URL = APP_CONFIG["model"]["default_base_url"]
DEFAULT_TEMPERATURE = float(APP_CONFIG["model"]["default_temperature"])
CONNECT_TIMEOUT_SECONDS = float(APP_CONFIG["model"].get("connect_timeout_seconds", 5))
READ_TIMEOUT_SECONDS = float(APP_CONFIG["model"].get("read_timeout_seconds", 30))
MAX_RETRIES = int(APP_CONFIG["model"].get("max_retries", 2))


def create_api_timeout():
    """创建外部 API 超时配置，避免模型调用长时间卡住。"""
    import httpx

    return httpx.Timeout(
        timeout=READ_TIMEOUT_SECONDS,
        connect=CONNECT_TIMEOUT_SECONDS,
        read=READ_TIMEOUT_SECONDS,
        write=READ_TIMEOUT_SECONDS,
        pool=CONNECT_TIMEOUT_SECONDS,
    )


@lru_cache(maxsize=1)
def ensure_env_loaded() -> None:
    """只加载一次 .env；网页内 API 配置会直接写入 os.environ，不受缓存影响。"""
    runtime_paths.load_runtime_env()
    load_dotenv(override=False)


def get_api_config() -> dict[str, str]:
    """读取当前实际会使用的 API 配置。"""
    ensure_env_loaded()
    return {
        "api_key": os.getenv("DEEPSEEK_API_KEY", "").strip(),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/"),
        "model": os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
    }


def create_client():
    """创建 OpenAI 兼容客户端。"""
    config = get_api_config()
    if not config["api_key"]:
        raise ValueError("还没有可用的 API Key，请先在首次配置页或侧边栏 API 设置中填写。")

    from openai import OpenAI

    return OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
        timeout=create_api_timeout(),
        max_retries=MAX_RETRIES,
    )


def call_chat_completion(messages: list[dict[str, str]], temperature: float | None = None) -> str:
    """统一发起聊天模型调用；演示模式下直接返回本地预设结果。"""
    if demo_engine.is_demo_mode():
        system_prompt = "\n".join(message.get("content", "") for message in messages if message.get("role") == "system")
        user_content = "\n".join(message.get("content", "") for message in messages if message.get("role") == "user")
        return demo_engine.get_demo_response(system_prompt, user_content)

    client = create_client()
    response = client.chat.completions.create(
        model=get_api_config()["model"],
        messages=messages,
        temperature=DEFAULT_TEMPERATURE if temperature is None else temperature,
        stream=False,
    )
    return response.choices[0].message.content or ""


def test_connection(api_key: str, base_url: str, model_name: str) -> tuple[bool, str]:
    """用指定配置发起一次极短连接测试。"""
    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        timeout=create_api_timeout(),
        max_retries=MAX_RETRIES,
    )
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "你只需要回复：连接成功"},
            {"role": "user", "content": "请回复连接成功"},
        ],
        temperature=float(APP_CONFIG["model"]["connection_test_temperature"]),
        max_tokens=12,
        stream=False,
    )
    content = response.choices[0].message.content or ""
    return True, content.strip() or "连接成功"
