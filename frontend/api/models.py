"""SQLAlchemy ORM 模型。"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True)
    birth_date = Column(String(20), nullable=True)

    # 核心凭证
    session_id = Column(Text, nullable=True)
    tt_target_idc = Column(String(64), nullable=True)
    ms_token = Column(Text, nullable=True)

    # 完整 cookie JSON
    cookies_json = Column(Text, nullable=True)
    important_cookies = Column(Text, nullable=True)  # JSON 字符串

    # 设备/代理信息
    user_agent = Column(Text, nullable=True)
    proxy_used = Column(String(255), nullable=True)
    fingerprint_hash = Column(String(64), nullable=True)
    timezone = Column(String(64), nullable=True)
    locale = Column(String(32), nullable=True)
    viewport = Column(String(64), nullable=True)

    # 状态
    status = Column(String(16), nullable=False, index=True)  # success / failed
    error_msg = Column(Text, nullable=True)
    batch_id = Column(String(64), nullable=True, index=True)

    registered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_checked_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_status_created", "status", "created_at"),
    )
