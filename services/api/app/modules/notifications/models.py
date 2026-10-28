# 站内通知 · ORM 模型
"""表结构以 docs/02-数据模型与状态机.md 为准。

迁移只由 P3 一人生成：alembic revision --autogenerate -m "<动词>_<对象>"
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# 线上用 JSONB（可索引），测试用 SQLite 时自动退回普通 JSON
JsonPayload = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


class Notification(Base):
    """一条站内通知。

    user_id 是指向 users.id 的引用，但不建物理外键：users 表属于 identity 模块，
    跨模块只认 ID（见 docs/必读1 §7）。
    """

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonPayload, nullable=False, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
