# 身份与会话 · 数据访问
"""只写查询和落库，不写权限判断、不写业务流程。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.identity.models import Session as LoginSession
from app.modules.identity.models import User


class IdentityRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_username(self, username: str) -> User | None:
        """按小写比较，正好命中 uq_users_username_lower 这个函数唯一索引。"""
        stmt = select(User).where(func.lower(User.username) == username.lower())
        return self.db.scalar(stmt)

    def get_user(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def add_user(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def add_session(self, session: LoginSession) -> LoginSession:
        self.db.add(session)
        self.db.flush()
        return session

    def get_session(self, session_id: uuid.UUID) -> LoginSession | None:
        return self.db.get(LoginSession, session_id)

    def revoke(self, session: LoginSession, when: datetime) -> None:
        session.revoked_at = when
        self.db.flush()

    def revoke_all_for_user(self, user_id: uuid.UUID, when: datetime) -> int:
        """只动未撤销的会话，重复调用是幂等的（已撤销的时间戳不被覆盖）。"""
        stmt = select(LoginSession).where(
            LoginSession.user_id == user_id, LoginSession.revoked_at.is_(None)
        )
        sessions = list(self.db.scalars(stmt))
        for row in sessions:
            row.revoked_at = when
        self.db.flush()
        return len(sessions)
