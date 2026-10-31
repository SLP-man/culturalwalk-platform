"""RT-01：建路线与草稿两张表（routes / route_drafts）

Revision ID: 0004_routes
Revises: 0003_identity
Create Date: 2026-01-20 00:00:00.000000

说明：
- 表结构以 docs/02-数据模型与状态机.md §2.3 为准。
- 本卡只建 routes 与 route_drafts：route_nodes 属 RT-02、route_versions 属 RT-03，
  由各自卡片的迁移补，这里不提前占位（先建空表等于先猜契约）。
- 草稿的展示信息（title/summary/theme_tags/duration_minutes）落在 routes 行上，
  route_drafts 只记状态与所有权，所以 PATCH 要同时改两张表。
- author_id / owner_id 指向 users.id，但跨模块只引用裸 UUID、不建物理外键，
  与 planner 的 itineraries.user_id 保持同一套约定。
- 枚举一律 VARCHAR + CHECK（native_enum=False），不建 PG 原生 ENUM：
  以后加一个状态只是改约束，不必写一节 CREATE TYPE。
- downgrade 先删索引再删表，顺序与 upgrade 相反，子表 route_drafts 先删。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_routes"
down_revision: str | None = "0003_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "routes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column(
            "channel",
            sa.Enum(
                "official",
                "user",
                name="routechannel",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=60), nullable=False),
        sa.Column("summary", sa.String(length=300), nullable=True),
        sa.Column("theme_tags", sa.JSON(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "published",
                "unpublished",
                "archived",
                name="routestatus",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
        ),
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
    )
    # slug 唯一靠唯一索引而不是 UniqueConstraint：模型里写的是 unique=True + index=True，
    # 两边名字必须一致，否则 autogenerate 会一直以为要再建一次。
    op.create_index("ix_routes_slug", "routes", ["slug"], unique=True)
    op.create_index("ix_routes_author_id", "routes", ["author_id"], unique=False)
    # docs/02 §5 的最低索引要求：列表页按 (状态, 渠道) 过滤。
    op.create_index("ix_routes_status_channel", "routes", ["status", "channel"], unique=False)

    op.create_table(
        "route_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("route_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "EDITING",
                "SUBMITTED_LOCKED",
                "APPROVED_LOCKED",
                "ARCHIVED",
                name="draftstate",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("lock_version", sa.Integer(), nullable=False),
        sa.Column("base_version_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("request_hash", sa.String(length=64), nullable=True),
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
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # 幂等（docs/03 §1.2）：同一作者同一个 Idempotency-Key 只能建出一份草稿。
        # 交给数据库兜底，而不是靠"先查再写"——并发时查是拦不住的。
        sa.UniqueConstraint(
            "owner_id", "idempotency_key", name="uq_route_drafts_owner_idempotency"
        ),
    )
    op.create_index(op.f("ix_route_drafts_route_id"), "route_drafts", ["route_id"], unique=False)
    op.create_index(op.f("ix_route_drafts_owner_id"), "route_drafts", ["owner_id"], unique=False)


def downgrade() -> None:
    # 先删子表 route_drafts 再删 routes，否则外键会拦住。
    op.drop_index(op.f("ix_route_drafts_owner_id"), table_name="route_drafts")
    op.drop_index(op.f("ix_route_drafts_route_id"), table_name="route_drafts")
    op.drop_table("route_drafts")
    op.drop_index("ix_routes_status_channel", table_name="routes")
    op.drop_index("ix_routes_author_id", table_name="routes")
    op.drop_index("ix_routes_slug", table_name="routes")
    op.drop_table("routes")
