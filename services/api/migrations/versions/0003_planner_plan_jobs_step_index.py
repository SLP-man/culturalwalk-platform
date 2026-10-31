"""PL-05：建后台任务表 plan_jobs（异步生成用）+ agent_steps 补顺序列

Revision ID: 0003_planner
Revises: 0002_planner
Create Date: 2026-10-31 23:58:00.000000

说明：
- plan_jobs：一次生成（plan_runs 一行）对应一条任务，`run_id` 唯一，重复入队等于让同一份行程跑两遍。
- worker 用 `state = 'PENDING' AND available_at <= now()` 取活，靠
  `FOR UPDATE SKIP LOCKED` 保证两个 worker 不会抢到同一条。
- `lease_until` 是租约：worker 干到一半崩了，租约过期后任务能被别人捡走，
  不然一条毒任务会把整条流水线永远堵住。
- 与 0001/0002 一样手写：本机 Windows 下 `alembic revision` 读 alembic.ini 会因
  GBK 编码炸掉（详见 PR #70 的待确认第 4 条），`migrations/env.py` 未改动。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_planner"
down_revision: str | None = "0002_planner"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plan_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("itinerary_id", sa.Uuid(), nullable=False),
        # 手写枚举 + CHECK，理由同 0001：以后多一个状态只改 CHECK，不必写 CREATE TYPE。
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by", sa.String(length=64), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=200), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["plan_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("run_id", name="uq_plan_jobs_run"),
        sa.CheckConstraint("state IN ('PENDING', 'RUNNING', 'DONE', 'FAILED')", name="jobstate"),
    )
    op.create_index(op.f("ix_plan_jobs_run_id"), "plan_jobs", ["run_id"], unique=False)
    op.create_index(op.f("ix_plan_jobs_itinerary_id"), "plan_jobs", ["itinerary_id"], unique=False)
    op.create_index(
        "ix_plan_jobs_state_available", "plan_jobs", ["state", "available_at"], unique=False
    )

    # agent_steps 原本没有顺序列：id 是随机 UUID、created_at 只到秒，
    # 想要稳定还原"先调研、再排班、再挑刺、最后核对"就得显式记序号。
    # 老行填 0（此前没跑过几次生成），新行由 service 按执行顺序写入。
    with op.batch_alter_table("agent_steps") as batch_op:
        batch_op.add_column(
            sa.Column("step_index", sa.Integer(), nullable=False, server_default=sa.text("0"))
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_steps") as batch_op:
        batch_op.drop_column("step_index")
    op.drop_index("ix_plan_jobs_state_available", table_name="plan_jobs")
    op.drop_index(op.f("ix_plan_jobs_itinerary_id"), table_name="plan_jobs")
    op.drop_index(op.f("ix_plan_jobs_run_id"), table_name="plan_jobs")
    op.drop_table("plan_jobs")
