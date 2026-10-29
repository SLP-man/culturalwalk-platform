"""PL-01：建行程 5 张表（itineraries / days / items / plan_runs / agent_steps）

Revision ID: 0001_planner
Revises:
Create Date: 2026-10-29 16:59:31.734470

说明：
- 表结构以 docs/02-数据模型与状态机.md §2.5 为准，字段取值与 docs/api/openapi.yaml 对齐。
- 这是仓库第一份迁移，因此 down_revision 为空。
- 本文件由 PL-01 手写提交（卡片明确要求带迁移）；`migrations/env.py` 未做任何改动，
  后续迁移仍由 P3 统一用 autogenerate 生成。
- itineraries.user_id 暂不建外键：users 表属于 identity 模块、目前还不存在，
  等 ID-01 落地后再单独补一份外键迁移（跨模块也不允许直接引用别人的表）。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_planner"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "itineraries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("city", sa.String(length=64), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("people", sa.Integer(), nullable=False),
        sa.Column("budget_total", sa.Integer(), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=False),
        # 枚举存 VARCHAR + CHECK（native_enum=False），不用 PG 原生 ENUM：
        # 以后加一个状态只是改 CHECK，不必写一节 CREATE TYPE 的迁移。
        sa.Column(
            "state",
            sa.Enum(
                "DRAFT",
                "GENERATING",
                "READY",
                "FAILED",
                name="planstate",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("visibility", sa.String(length=16), nullable=False),
        sa.Column("share_token", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_token"),
    )
    op.create_index(op.f("ix_itineraries_user_id"), "itineraries", ["user_id"], unique=False)

    op.create_table(
        "itinerary_days",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("itinerary_id", sa.Uuid(), nullable=False),
        sa.Column("day_index", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("itinerary_id", "day_index", name="uq_itinerary_days_itinerary_day"),
    )
    op.create_index(
        op.f("ix_itinerary_days_itinerary_id"), "itinerary_days", ["itinerary_id"], unique=False
    )

    op.create_table(
        "plan_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("itinerary_id", sa.Uuid(), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "DRAFT",
                "GENERATING",
                "READY",
                "FAILED",
                name="planstate",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("prompt_version", sa.String(length=32), nullable=True),
        sa.Column("cost", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plan_runs_itinerary_id"), "plan_runs", ["itinerary_id"], unique=False)

    op.create_table(
        "agent_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column(
            "agent",
            sa.Enum(
                "researcher",
                "planner",
                "critic",
                "verifier",
                name="agentname",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "done",
                "failed",
                name="agentstepstatus",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("output_digest", sa.String(length=64), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["plan_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_steps_run_id"), "agent_steps", ["run_id"], unique=False)

    op.create_table(
        "itinerary_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("day_id", sa.Uuid(), nullable=False),
        # 列名就是 order（与文档一致）；它是 SQL 关键字，SQLAlchemy 建表时会自动加引号。
        sa.Column("order", sa.Integer(), nullable=False),
        # place_id 指向 catalog 模块的地点，跨模块不建物理外键，只存 ID。
        sa.Column("place_id", sa.Uuid(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("stay_minutes", sa.Integer(), nullable=False),
        sa.Column("transport", sa.String(length=16), nullable=True),
        sa.Column("price_min", sa.Integer(), nullable=True),
        sa.Column("price_max", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.String(length=16), nullable=True),
        sa.Column("source_ids", sa.JSON(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["day_id"], ["itinerary_days.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_itinerary_items_day_order", "itinerary_items", ["day_id", "order"], unique=False
    )


def downgrade() -> None:
    # 与 upgrade 完全相反的次序：先删子表再删父表，否则外键会拦住。
    op.drop_index("ix_itinerary_items_day_order", table_name="itinerary_items")
    op.drop_table("itinerary_items")
    op.drop_index(op.f("ix_agent_steps_run_id"), table_name="agent_steps")
    op.drop_table("agent_steps")
    op.drop_index(op.f("ix_plan_runs_itinerary_id"), table_name="plan_runs")
    op.drop_table("plan_runs")
    op.drop_index(op.f("ix_itinerary_days_itinerary_id"), table_name="itinerary_days")
    op.drop_table("itinerary_days")
    op.drop_index(op.f("ix_itineraries_user_id"), table_name="itineraries")
    op.drop_table("itineraries")
