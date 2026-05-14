"""AI 运营分身 FastAPI 后端。

默认用于本机开发与演示，建议只监听 127.0.0.1。
如果设置了 AI_OPS_API_TOKEN，所有业务接口都必须携带：
Authorization: Bearer <token>
"""

from __future__ import annotations

import json
import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import runtime_paths
import security_utils
from core import Orchestrator
from database import AnalysisReport, User, get_db, init_db


app = FastAPI(
    title="AI 运营分身 API",
    description="本地 API 服务。默认不持久化内容，默认不建议暴露到公网。",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()
init_db()


def verify_api_auth(authorization: str | None = Header(default=None)) -> dict[str, str]:
    """配置 Token 时强制鉴权；未配置时仅作为本机开发模式。"""
    token = security_utils.get_api_token()
    if not token:
        return {"mode": "local_dev_no_token"}
    if authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="未授权：请提供有效的 Bearer Token。")
    return {"mode": "token"}


def should_persist(payload: Any) -> bool:
    """只有显式请求且全局开关允许时才写数据库。"""
    return bool(getattr(payload, "persist", False)) and os.getenv("AI_OPS_API_PERSISTENCE", "0") == "1"


def get_or_create_api_user(db: Session, username: str) -> User:
    """获取或创建 API 调用用户。"""
    user = db.query(User).filter(User.username == username).first()
    if user:
        return user
    user = User(username=username)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def save_analysis_report(db: Session, report_type: str, result: dict[str, Any], username: str) -> int | None:
    """显式持久化 API 报告；失败不影响接口返回。"""
    try:
        user = get_or_create_api_user(db, username)
        content = result.get("content") or result.get("coordinator_result") or ""
        report = AnalysisReport(
            creator_id=user.id,
            report_type=report_type,
            markdown_content=str(content),
            json_data=json.dumps(result, ensure_ascii=False),
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report.id
    except Exception:
        db.rollback()
        return None


def attach_persistence_meta(result: dict[str, Any], report_id: int | None, persisted: bool) -> dict[str, Any]:
    """在接口返回中明确说明是否已落盘。"""
    response = dict(result)
    response["database_report_id"] = report_id
    response["persisted"] = persisted
    response["data_dir"] = str(runtime_paths.USER_DATA_DIR)
    return response


class BasePersistRequest(BaseModel):
    username: str = Field("api_demo_user", description="调用用户名称")
    persist: bool = Field(False, description="是否显式保存到 API 数据库")


class ChatRequest(BasePersistRequest):
    user_input: str = Field(..., description="用户问题")
    session_id: str = Field("default", description="会话 ID")
    messages: list[dict[str, str]] | None = Field(None, description="可选对话历史")


class TaskRequest(BasePersistRequest):
    user_content: str = Field(..., description="用户输入内容")
    system_prompt: str = Field("", description="可选系统提示词")


class VersionAnalysisRequest(BasePersistRequest):
    announcement_text: str = Field(..., description="版本公告文本")
    system_prompt: str = Field("", description="可选系统提示词")


class FeedbackCleanRequest(BasePersistRequest):
    feedback_list: str | list[str] = Field(..., description="玩家反馈文本或反馈列表")
    system_prompt: str = Field("", description="可选系统提示词")


class CollaborationRequest(BasePersistRequest):
    announcement_text: str = Field(..., description="版本公告文本")
    agents: list[str] | None = Field(None, description="参与协作的角色 key；为空则默认全选")
    goal: str = Field("无特定目标（综合评估）", description="本次协作的运营目标")


class RagRequest(BasePersistRequest):
    user_question: str = Field(..., description="用户问题")
    system_prompt: str = Field("", description="系统提示词")


@app.get("/health")
def health() -> dict[str, str]:
    """健康检查，不需要鉴权。"""
    return {
        "status": "ok",
        "service": "ai-ops-agent-api",
        "bind_hint": "请默认使用 127.0.0.1，本服务不建议直接公网暴露。",
        "auth": "token" if security_utils.get_api_token() else "local_dev_no_token",
    }


def maybe_save(db: Session, report_type: str, result: dict[str, Any], payload: BasePersistRequest) -> tuple[int | None, bool]:
    if not should_persist(payload):
        return None, False
    report_id = save_analysis_report(db, report_type, result, payload.username)
    return report_id, report_id is not None


@app.post("/chat", dependencies=[Depends(verify_api_auth)])
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    result = orchestrator.run_chat(payload.user_input, session_id=payload.session_id, messages=payload.messages)
    report_id, persisted = maybe_save(db, "chat", result, payload)
    return attach_persistence_meta(result, report_id, persisted)


@app.post("/version-analysis", dependencies=[Depends(verify_api_auth)])
def version_analysis(payload: VersionAnalysisRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    result = orchestrator.run_version_analysis(payload.announcement_text, system_prompt=payload.system_prompt)
    report_id, persisted = maybe_save(db, "version_analysis", result, payload)
    return attach_persistence_meta(result, report_id, persisted)


@app.post("/feedback-clean", dependencies=[Depends(verify_api_auth)])
def feedback_clean(payload: FeedbackCleanRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    result = orchestrator.run_feedback_clean(payload.feedback_list, system_prompt=payload.system_prompt)
    report_id, persisted = maybe_save(db, "feedback_clean", result, payload)
    return attach_persistence_meta(result, report_id, persisted)


@app.post("/collaboration", dependencies=[Depends(verify_api_auth)])
def collaboration(payload: CollaborationRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    result = orchestrator.run_collaboration(payload.announcement_text, agents=payload.agents, goal=payload.goal)
    report_id, persisted = maybe_save(db, "collaboration", result, payload)
    return attach_persistence_meta(result, report_id, persisted)


@app.post("/competitor-analysis", dependencies=[Depends(verify_api_auth)])
def competitor_analysis(payload: TaskRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    result = orchestrator.run_competitor_analysis(payload.user_content, system_prompt=payload.system_prompt)
    report_id, persisted = maybe_save(db, "competitor_analysis", result, payload)
    return attach_persistence_meta(result, report_id, persisted)


@app.post("/activity-workshop", dependencies=[Depends(verify_api_auth)])
def activity_workshop(payload: TaskRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    result = orchestrator.run_activity_workshop(payload.user_content, system_prompt=payload.system_prompt)
    report_id, persisted = maybe_save(db, "activity_workshop", result, payload)
    return attach_persistence_meta(result, report_id, persisted)


@app.post("/rag-query", dependencies=[Depends(verify_api_auth)])
def rag_query(payload: RagRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    result = orchestrator.query_rag(payload.user_question, payload.system_prompt)
    report_id, persisted = maybe_save(db, "rag_query", result, payload)
    return attach_persistence_meta(result, report_id, persisted)

