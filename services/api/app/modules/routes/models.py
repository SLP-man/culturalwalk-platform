# 路线与版本 · ORM 模型
"""表结构以 docs/02-数据模型与状态机.md §2.3 为准。

RT-01 只建 routes 与 route_drafts 两张表：route_nodes（RT-02）与 route_versions
（RT-03）不属于本卡，建在各自卡片的迁移里，这里不提前占位——先建空表等于先猜契约。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RouteChannel(StrEnum):
    """路线来源：平台精选（official）还是用户投稿（user）。"""

    OFFICIAL = "official"
    USER = "user"


class RouteStatus(StrEnum):
    """路线的可读状态缓存；真值由 publication 派生（RT-04 起才会改写它）。"""

    DRAFT = "draft"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    ARCHIVED = "archived"


class DraftState(StrEnum):
    """草稿状态机（docs/02 §3.1），取值与 openapi.yaml 的 RouteDraft.state 逐字一致。"""

    EDITING = "EDITING"
    SUBMITTED_LOCKED = "SUBMITTED_LOCKED"
    APPROVED_LOCKED = "APPROVED_LOCKED"
    ARCHIVED = "ARCHIVED"


def _enum_values(py_enum: type[StrEnum]) -> list[str]:
    """让数据库里存枚举的 value（原样大小写），而不是 Python 成员名。"""
    return [member.value for member in py_enum]


def _stored_enum(py_enum: type[StrEnum], *, length: int) -> Enum:
    """枚举一律存成 VARCHAR + CHECK 约束，不用 PG 原生 ENUM。

    与 planner/models.py 是同一套做法：原生 CREATE TYPE 想加一个状态就得写一节
    迁移，成本远大于收益；CHECK 一样挡得住脏值，还能在 SQLite 上跑单测。
    这里重复一份实现而不是去 import 隔壁模块的私有名，免得两个模块的实现被绑死。
    """
    return Enum(
        py_enum,
        native_enum=False,
        length=length,
        create_constraint=True,
        validate_strings=True,
        values_callable=_enum_values,
    )


class Route(Base):
    """一条路线的稳定身份（跨版本不变）。

    RT-01 阶段它由"新建草稿"顺带创建，展示信息（title/summary/theme_tags/
    duration_minutes）落在这里而不是 route_drafts 上——草稿只管要不要改，
    路线本身才是内容的归属（docs/02 §2.3 的两张表分工）。
    """

    __tablename__ = "routes"
    __table_args__ = (
        # docs/02 §5 的最低要求：列表页按 (状态, 渠道) 过滤。
        Index("ix_routes_status_channel", "status", "channel"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # 短链用的可读标识：标题归一化 + 短 uuid，唯一性靠数据库兜底。
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    # users 表属于 identity 模块，跨模块只引用 id，不建物理外键（同 planner 的约定）。
    author_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    channel: Mapped[RouteChannel] = mapped_column(
        _stored_enum(RouteChannel, length=16),
        nullable=False,
        default=RouteChannel.USER,
    )
    title: Mapped[str] = mapped_column(String(60), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(300), nullable=True)
    theme_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[RouteStatus] = mapped_column(
        _stored_enum(RouteStatus, length=16),
        nullable=False,
        default=RouteStatus.DRAFT,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RouteDraft(Base):
    """一份可编辑的草稿：只记"谁在改哪条路线、改到第几版、锁在什么状态"。

    内容列不在本表（见 Route 的注释）；这样同一份内容可以有多份草稿分别编辑，
    也正是 docs/02 §3.1 里 APPROVED_LOCKED 之后要 fork 新草稿的前提。
    """

    __tablename__ = "route_drafts"
    __table_args__ = (
        # 幂等（docs/03 §1.2）：同一作者拿同一个 Idempotency-Key 只能建出一份草稿。
        # 靠唯一约束兜底而不是"先查再写"——两个请求并发时只有查是拦不住的。
        UniqueConstraint("owner_id", "idempotency_key", name="uq_route_drafts_owner_idempotency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("routes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 同 author_id：跨模块只引用 users.id，不建物理外键。
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    state: Mapped[DraftState] = mapped_column(
        _stored_enum(DraftState, length=20),
        nullable=False,
        default=DraftState.EDITING,
    )
    # 乐观锁：每次 PATCH 走完 +1，客户端下次必须把新值放进 If-Match。
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # 从哪个版本 fork 出来的。route_versions 属 RT-03，本卡先存裸 ID。
    base_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    # 幂等相关两列。通用幂等表还没人认领，先按 (owner_id, key) 在草稿上去重；
    # request_hash 是首次请求体的指纹，同一个 key 换了内容要报 409 而不是悄悄重放。
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
