# 审计 · 数据访问
"""只写查询和落库，不写权限判断、不写业务流程。

**没有任何 update / delete 方法**——审计表只追加，这是契约不是习惯。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, select, tuple_
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: AuditLog) -> AuditLog:
        """落一行。调用方负责 commit（通常和业务写入同一个事务）。"""
        self.db.add(row)
        self.db.flush()
        return row

    def page(
        self,
        *,
        object_type: str | None = None,
        object_id: str | None = None,
        actor_id: str | None = None,
        after: tuple[datetime, str] | None = None,
        limit: int = 20,
    ) -> tuple[list[AuditLog], bool]:
        """按 (created_at, id) 倒序取一页，返回 (行, 是否还有下一页)。"""
        stmt: Select[tuple[AuditLog]] = select(AuditLog)

        if object_type:
            stmt = stmt.where(AuditLog.object_type == object_type)
        if object_id:
            stmt = stmt.where(AuditLog.object_id == object_id)
        if actor_id:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        if after is not None:
            stmt = stmt.where(tuple_(AuditLog.created_at, AuditLog.id) < tuple_(*after))

        stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit + 1)
        rows = list(self.db.scalars(stmt).all())
        return rows[:limit], len(rows) > limit
