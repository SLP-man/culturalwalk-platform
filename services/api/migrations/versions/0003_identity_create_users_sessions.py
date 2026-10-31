"""ID-01：建身份与会话两张表（users / sessions）

Revision ID: 0003_identity
Revises: 0002_planner
Create Date: 2026-01-15 00:00:00.000000

说明：
- 表结构以 docs/02-数据模型与状态机.md §2.1 为准。
- username / email 的 citext 语义用「小写函数唯一索引」实现，不建扩展也不改列类型：
  CI 的 PostgreSQL 与单测的 SQLite 都支持表达式索引，down 时能干净删掉。
- sessions.user_id 指向 users.id 并带 ON DELETE CASCADE：同一模块内，可以建物理外键。
- downgrade 先删索引再删表，顺序与 upgrade 相反，删的是 sessions 与 users 两张表。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_identity"
down_revision: str | None = "0002_planner"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=24), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('user', 'editor', 'admin')", name="ck_users_role"),
        sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_users_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    # 表达式索引：Alembic 的 autogenerate 不认这种索引，所以文件名与列表达式都写死在这里，
    # 改索引请同时改 app/modules/identity/models.py 末尾的两行，别只改一边。
    op.create_index("uq_users_username_lower", "users", [sa.text("lower(username)")], unique=True)
    op.create_index("uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True)

    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sessions_refresh_hash"), "sessions", ["refresh_hash"], unique=False)
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)


def downgrade() -> None:
    # 先删子表 sessions 再删 users，否则外键会拦住。
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_index(op.f("ix_sessions_refresh_hash"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_index("uq_users_username_lower", table_name="users")
    op.drop_table("users")
