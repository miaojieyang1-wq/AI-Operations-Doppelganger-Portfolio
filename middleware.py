"""轻量可观测性工具。

本文件不依赖 Streamlit 或 FastAPI，可被脚本、API 或核心函数按需手动接入。
它提供 request_id 注入能力，方便把一次调用链路串起来排查问题。
"""

from __future__ import annotations

import functools
import logging
import uuid
from contextvars import ContextVar
from typing import Any, Callable, TypeVar


F = TypeVar("F", bound=Callable[..., Any])
REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """为日志记录增加 request_id 字段。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = REQUEST_ID.get()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """配置统一日志格式。"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s [request_id=%(request_id)s] %(message)s",
    )
    for handler in logging.getLogger().handlers:
        handler.addFilter(RequestIdFilter())


def with_request_id(func: F) -> F:
    """为函数调用自动生成 request_id。"""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        token = REQUEST_ID.set(str(uuid.uuid4()))
        try:
            return func(*args, **kwargs)
        finally:
            REQUEST_ID.reset(token)

    return wrapper  # type: ignore[return-value]
