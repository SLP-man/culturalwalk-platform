# 行程规划（多 Agent） · ORM 模型
"""表结构以 docs/02-数据模型与状态机.md §2.5 为准。

迁移：PL-01 随卡片要求带了一份手写迁移（migrations/versions/0001_*.py），
`migrations/env.py` 未改动；之后的迁移仍由 P3 统一用 autogenerate 生成。
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class PlanState(StrEnum):
    """行程与生成任务共用的状态机，见 docs/02 §3.5。

    FAILED 是终点：要重试就新建一次 PlanRun，不把旧记录改回 GENERATING，
    这样"失败过几次、每次为什么失败"都能留在库里。
    """

    DRAFT = "DRAFT"
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"


class AgentName(StrEnum):
    """四个 Agent 的分工固定，见 planner/router.py 的编排契约。"""

    RESEARCHER = "researcher"
    PLANNER = "planner"
    CRITIC = "critic"
    VERIFIER = "verifier"


class AgentStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


def _enum_values(py_enum: type[StrEnum]) -> list[str]:
    """让数据库里存枚举的 value（小写英文），而不是 Python 成员名。

    值要与 docs/api/openapi.yaml 里的 enum 完全一致，前端才不用做大小写转换。
    """
    return [member.value for member in py_enum]


def _stored_enum(py_enum: type[StrEnum], *, length: int) -> Enum:
    """枚举一律存成 VARCHAR + CHECK 约束，不用 PG 原生 ENUM。

    原生的 `CREATE TYPE` 想加一个状态就得写一节迁移，成本远大于收益；
    CHECK 同样能挡住脏值，还能在 SQLite 上跑测试。
    """
    return Enum(
        py_enum,
        native_enum=False,
        length=length,
        create_constraint=True,
        validate_strings=True,
        values_callable=_enum_values,
    )


class Itinerary(Base):
    """一张行程单：用户提交的规划条件 + 当前状态。"""

    __tablename__ = "itineraries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # users 表属于 identity 模块，目前还没建（ID-01 未完成）。
    # 跨模块只允许引用 users.id，等那边建好表再单独补一个外键迁移，
    # 现在先存裸 ID，避免本迁移一执行就因为找不到 users 表而失败。
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(64), nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    people: Mapped[int] = mapped_column(Integer, nullable=False)
    budget_total: Mapped[int] = mapped_column(Integer, nullable=False)  # 单位：分，全队总额
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    state: Mapped[PlanState] = mapped_column(
        _stored_enum(PlanState, length=16), nullable=False, default=PlanState.DRAFT
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, default="private")
    share_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    days_plan: Mapped[list[ItineraryDay]] = relationship(
        back_populates="itinerary",
        cascade="all, delete-orphan",
        order_by="ItineraryDay.day_index",
    )
    runs: Mapped[list[PlanRun]] = relationship(
        back_populates="itinerary",
        cascade="all, delete-orphan",
        order_by="PlanRun.created_at",
    )


class ItineraryDay(Base):
    """行程里的一天。day_index 从 1 开始，与用户嘴里的"第二天"对齐。"""

    __tablename__ = "itinerary_days"
    __table_args__ = (
        UniqueConstraint("itinerary_id", "day_index", name="uq_itinerary_days_itinerary_day"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    itinerary_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date | None] = mapped_column(Date, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    itinerary: Mapped[Itinerary] = relationship(back_populates="days_plan")
    items: Mapped[list[ItineraryItem]] = relationship(
        back_populates="day",
        cascade="all, delete-orphan",
        order_by="ItineraryItem.order",
    )


class ItineraryItem(Base):
    """一个具体点位。门票、停留、交通、可信度都挂在这一行上。"""

    __tablename__ = "itinerary_items"
    __table_args__ = (
        # 查询永远是"按天取、按顺序排"，组合索引正好覆盖，不做唯一约束：
        # 调整顺序时中间态会短暂重复，唯一约束会把正常的换序也拦掉。
        Index("ix_itinerary_items_day_order", "day_id", "order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    day_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("itinerary_days.id", ondelete="CASCADE"), nullable=False
    )
    # 字段名按文档叫 order。它是 SQL 关键字，SQLAlchemy 建表时会自动加引号，
    # 这里不为了"好看"改名，否则迁移和文档对不上。
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    # 地点属于 catalog 模块：按约定跨模块关联不建物理外键，只存 ID，由 service 校验存在性。
    place_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    stay_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transport: Mapped[str | None] = mapped_column(String(16), nullable=True)
    price_min: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 分
    price_max: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 分
    # verified / unverified：取值和展示文案由 PL-06 定，这里只留位置。
    confidence: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # 来源属于 catalog/community：跨模块不建外键，存 ID 数组，前台按 ID 回查。
    source_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    day: Mapped[ItineraryDay] = relationship(back_populates="items")


class PlanRun(Base):
    """一次生成尝试。同一张行程可以生成多次，成功失败都留痕。"""

    __tablename__ = "plan_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    itinerary_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    state: Mapped[PlanState] = mapped_column(
        _stored_enum(PlanState, length=16), nullable=False, default=PlanState.DRAFT
    )
    # 输入指纹（sha256 十六进制）：同一套条件重复提交可以直接复用上次结果，不必再花一次模型调用。
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cost: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 分
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    itinerary: Mapped[Itinerary] = relationship(back_populates="runs")
    steps: Mapped[list[AgentStep]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentStep.created_at",
    )


class AgentStep(Base):
    """一个 Agent 在某次生成里的执行记录。"""

    __tablename__ = "agent_steps"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plan_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent: Mapped[AgentName] = mapped_column(_stored_enum(AgentName, length=16), nullable=False)
    status: Mapped[AgentStepStatus] = mapped_column(
        _stored_enum(AgentStepStatus, length=16), nullable=False, default=AgentStepStatus.PENDING
    )
    # 只存输出的 sha256，不存整段 JSON：库里留大块模型输出既脏又贵，
    # 需要复现时按摘要去日志/对象存储里找。
    output_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    run: Mapped[PlanRun] = relationship(back_populates="steps")
