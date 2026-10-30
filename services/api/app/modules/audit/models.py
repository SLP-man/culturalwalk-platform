# 审计 · ORM 模型
"""表结构以 docs/02-数据模型与状态机.md 为准：audit_logs。

两条硬约束：
1. **只追加**：本表没有 update / delete 的业务路径，ORM 层直接把这两种操作打死。
2. **不建跨模块外键**：actor 只存 id + 用户名快照，不 import identity 的模型（模块边界）。

迁移由 P3 统一生成：alembic revision --autogenerate -m "create_audit_logs"
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class AuditLog(Base):
    """一条审计记录。写入即定稿，之后只读。"""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # 操作者：id 可为空（系统动作）；用户名存快照，避免跨模块 join
    actor_id: Mapped[str | None] = mapped_column(String(36), index=True)
    actor_username: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64), index=True)
    object_type: Mapped[str] = mapped_column(String(40), index=True)
    object_id: Mapped[str] = mapped_column(String(36), index=True)
    before_hash: Mapped[str | None] = mapped_column(String(64))
    after_hash: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


@event.listens_for(AuditLog, "before_update")
def _forbid_update(_mapper: object, _connection: object, _target: object) -> None:
    raise RuntimeError("审计记录不可修改（append-only）")


@event.listens_for(AuditLog, "before_delete")
def _forbid_delete(_mapper: object, _connection: object, _target: object) -> None:
    raise RuntimeError("审计记录不可删除（append-only）")
