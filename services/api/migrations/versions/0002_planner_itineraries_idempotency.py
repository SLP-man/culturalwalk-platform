"""PL-02：itineraries 增加幂等两列（idempotency_key / input_hash）

Revision ID: 0002_planner
Revises: 0001_planner
Create Date: 2026-10-29 17:52:00.000000

说明：
- 契约要求所有 POST 带 Idempotency-Key（docs/03 §1.2），但没有任何卡认领"通用幂等表"。
  PL-02 只在行程这一侧做到位：同一个 key 只能建一张行程单，key 存在行程行上，
  不新建公共表，避免和 identity / audit 的归属打架。
- 用 batch_alter_table 是为了 SQLite：它不支持 ALTER TABLE ADD CONSTRAINT，
  批量模式会重建表；PostgreSQL 上批量模式仍走原生 ALTER，不会重建。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_planner"
down_revision: str | None = "0001_planner"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("itineraries") as batch:
        batch.add_column(sa.Column("idempotency_key", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("input_hash", sa.String(length=64), nullable=True))
        batch.create_unique_constraint(
            "uq_itineraries_user_idempotency", ["user_id", "idempotency_key"]
        )


def downgrade() -> None:
    with op.batch_alter_table("itineraries") as batch:
        batch.drop_constraint("uq_itineraries_user_idempotency", type_="unique")
        batch.drop_column("input_hash")
        batch.drop_column("idempotency_key")
