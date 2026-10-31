# 身份与会话 · ORM 模型
"""表结构以 docs/02-数据模型与状态机.md §2.1 为准。

- users：id / username / email / password_hash / role / bio / status
- sessions：id / user_id / refresh_hash / expires_at / revoked_at

迁移：migrations/versions/0003_identity_*.py（随本文件一起提交）。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# 取值与 docs/api/openapi.yaml#User.role 完全一致，前端不用做大小写转换
ROLE_USER = "user"
ROLE_EDITOR = "editor"
ROLE_ADMIN = "admin"
ROLES = (ROLE_USER, ROLE_EDITOR, ROLE_ADMIN)

STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    """一个账号。password_hash 只存 argon2id 摘要，明文密码在任何地方都不落库。"""

    __tablename__ = "users"
    __table_args__ = (
        # 取值约束写在库里而不是只写在代码里：脏值从别的入口进来时数据库也要拦住。
        CheckConstraint("role IN ('user', 'editor', 'admin')", name="ck_users_role"),
        CheckConstraint("status IN ('active', 'disabled')", name="ck_users_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # 长度取契约的 maxLength=24；citext 的语义见文件末尾的两个函数唯一索引
    username: Mapped[str] = mapped_column(String(24), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default=ROLE_USER)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_ACTIVE)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )


class Session(Base):
    """一次登录会话（refresh 令牌的载体）。

    refresh_token 本身是 JWT，库里只存它的 sha256：即使库被读走，
    也拿不到一枚能直接用的 refresh 令牌。
    """

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_user_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # 同模块内引用，可以建物理外键；用户注销时会话跟着删，不留孤儿行。
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# docs/02 §2.1 要求 username / email 是 citext（大小写不敏感唯一）。
# 这里不用 PG 的 citext 扩展：CI 的 PG 不一定装了扩展，单测跑的 SQLite 更是没有。
# 改用「小写函数唯一索引」，唯一性语义一致，且两种数据库都能建。
# 与之配套：service 入库前统一 strip + lower，索引才对得上。
Index("uq_users_username_lower", func.lower(User.username), unique=True)
Index("uq_users_email_lower", func.lower(User.email), unique=True)
