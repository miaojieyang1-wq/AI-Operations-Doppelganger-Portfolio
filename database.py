"""
数据库接口层。

默认使用本地 SQLite 演示数据库：sqlite:///./local_demo.db
未来接入公司统一数据库时，只需要在环境变量 DATABASE_URL 中配置
正式数据库连接地址，API 层代码无需重写。
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Generator

import runtime_paths
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


runtime_paths.load_runtime_env()
DATABASE_URL = os.getenv("DATABASE_URL", runtime_paths.default_database_url())

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy 模型基类。"""


class User(Base):
    """接口调用用户。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    reports: Mapped[list["AnalysisReport"]] = relationship(
        back_populates="creator",
        cascade="all, delete-orphan",
    )


class AnalysisReport(Base):
    """AI 分析报告记录。"""

    __tablename__ = "analysis_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    json_data: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    creator: Mapped[User] = relationship(back_populates="reports")


def init_db() -> None:
    """创建数据库表。"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """管理一次数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
