# 路线与版本 · 数据访问
"""只写查询和落库，不写权限判断、不写业务流程。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.modules.routes.models import Route, RouteDraft


class RoutesRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------- 写 ----------

    def add_route(self, route: Route) -> Route:
        """落一条路线。这里就 flush：下一句要拿它的 id 当 route_drafts.route_id。"""
        self.db.add(route)
        self.db.flush()
        return route

    def add_draft(self, draft: RouteDraft) -> RouteDraft:
        """落一份草稿。flush 放在调用方的事务里，幂等键撞车时由 service 决定回滚重查。"""
        self.db.add(draft)
        self.db.flush()
        return draft

    def delete_draft(self, draft: RouteDraft) -> None:
        self.db.delete(draft)

    def delete_route(self, route: Route) -> None:
        self.db.delete(route)

    # ---------- 读 ----------

    def get_draft(self, draft_id: uuid.UUID) -> RouteDraft | None:
        return self.db.get(RouteDraft, draft_id)

    def get_route(self, route_id: uuid.UUID) -> Route | None:
        return self.db.get(Route, route_id)

    def get_by_idempotency_key(
        self, *, owner_id: uuid.UUID, idempotency_key: str
    ) -> RouteDraft | None:
        stmt = select(RouteDraft).where(
            RouteDraft.owner_id == owner_id,
            RouteDraft.idempotency_key == idempotency_key,
        )
        return self.db.scalars(stmt).first()

    def page_by_owner(
        self,
        *,
        owner_id: uuid.UUID,
        after: tuple[datetime, uuid.UUID] | None,
        limit: int,
    ) -> tuple[list[tuple[RouteDraft, Route]], bool]:
        """按 (updated_at, id) 倒序取一页草稿，连同它指向的 routes 行。

        多取一行判断还有没有下一页：让"到底还有没有"由数据库回答，
        而不是靠 len(rows) == limit 猜（正好整页时这种猜法必然翻错）。
        """
        stmt = (
            select(RouteDraft, Route)
            .join(Route, RouteDraft.route_id == Route.id)
            .where(RouteDraft.owner_id == owner_id)
        )
        if after is not None:
            stmt = stmt.where(tuple_(RouteDraft.updated_at, RouteDraft.id) < tuple_(*after))
        stmt = stmt.order_by(RouteDraft.updated_at.desc(), RouteDraft.id.desc()).limit(limit + 1)
        # 两列一起取：草稿行只管状态，展示信息在 routes 行上，分两次查就白多一轮往返。
        pairs: list[tuple[RouteDraft, Route]] = [
            (draft, route) for draft, route in self.db.execute(stmt).all()
        ]
        return pairs[:limit], len(pairs) > limit
