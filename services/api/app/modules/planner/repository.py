# 行程规划（多 Agent） · 数据访问
"""只写查询和落库，不写权限判断、不写业务流程。"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.planner.models import Itinerary


class PlannerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_idempotency_key(
        self, *, user_id: uuid.UUID, idempotency_key: str
    ) -> Itinerary | None:
        """按 (用户, 幂等键) 找已有的行程。

        带 deleted_at 过滤：用户删掉行程后重新提交同一个 key，应该当新请求处理，
        而不是把一张已删除的行程还回去。
        """
        stmt = select(Itinerary).where(
            Itinerary.user_id == user_id,
            Itinerary.idempotency_key == idempotency_key,
            Itinerary.deleted_at.is_(None),
        )
        return self.db.scalars(stmt).first()

    def add(self, itinerary: Itinerary) -> Itinerary:
        self.db.add(itinerary)
        return itinerary
