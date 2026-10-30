# 站内通知 · 数据访问
"""只写查询和落库，不写权限判断、不写业务流程。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.notifications.models import Notification


class NotificationsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, notification: Notification) -> Notification:
        """落一条通知；只负责写入，要不要写由 service 判断。"""
        self.db.add(notification)
        self.db.flush()
        return notification

    def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        after: tuple[datetime, uuid.UUID] | None,
        limit: int,
    ) -> list[Notification]:
        """按 (created_at, id) 倒序做游标分页；after 为上一页最后一条的位置。"""
        stmt = select(Notification).where(Notification.user_id == user_id)
        if after is not None:
            created_at, notification_id = after
            # 不用行值比较，保证 SQLite（本地/CI 测试）与 PostgreSQL 行为一致
            stmt = stmt.where(
                or_(
                    Notification.created_at < created_at,
                    (Notification.created_at == created_at) & (Notification.id < notification_id),
                )
            )
        stmt = stmt.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)
        return list(self.db.scalars(stmt))
