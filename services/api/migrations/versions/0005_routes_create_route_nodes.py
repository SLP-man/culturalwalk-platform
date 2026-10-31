"""RT-02：建草稿节点表（route_nodes）

Revision ID: 0005_nodes
Revises: 0004_routes
Create Date: 2026-01-21 00:00:00.000000

说明：
- 表结构以 docs/02-数据模型与状态机.md §2.3 为准：draft_id / place_id / position /
  stay_minutes / transport / note / price_min / price_max。
- place_id 跨模块只存裸 UUID、不建物理外键：places 表属 #12 CA-01 / #14 CA-03，
  到现在还不存在，提前挂外键等于给一张还没定型的表结构上锁。
- (draft_id, position) 上同时建唯一约束与普通索引。唯一约束是必须的——position 是
  顺序的唯一真值，两个节点抢同一个位置必须是数据库层面的错误，不能靠写入顺序碰运气；
  普通索引是任务卡明确要求的取值路径索引，虽然唯一约束在多数库上已经建了等价索引。
- transport 用 VARCHAR + CHECK（native_enum=False），不建 PG 原生 ENUM，
  与 0004 的 channel / status 同一套做法。
- downgrade 先删索引再删表，顺序与 upgrade 相反。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_nodes"
down_revision: str | None = "0004_routes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "route_nodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("place_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("stay_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "transport",
            sa.Enum(
                "walk",
                "metro",
                "bus",
                "taxi",
                "bike",
                name="routetransport",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("price_min", sa.Integer(), nullable=True),
        sa.Column("price_max", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["draft_id"], ["route_drafts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # position 是顺序的唯一真值：同一次整表替换里两行抢同一个位置，
        # 说明写入逻辑算错了下标，这种错必须当场炸掉而不是留一份顺序不确定的草稿。
        sa.UniqueConstraint("draft_id", "position", name="uq_route_nodes_draft_position"),
    )
    op.create_index(
        "ix_route_nodes_draft_position", "route_nodes", ["draft_id", "position"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_route_nodes_draft_position", table_name="route_nodes")
    op.drop_table("route_nodes")
