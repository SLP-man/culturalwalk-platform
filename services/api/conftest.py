"""共享测试夹具：内存 SQLite + 覆盖 get_db + 现成的 token。

约定：
- 每个用例一套干净的表（sqlite 内存 + StaticPool，同一个连接）。
- 需要登录的用例直接用 admin_headers / user_headers，不要在用例里手搓 JWT。
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.core.deps import create_access_token
from app.main import app

# 触发所有模型 import，create_all 才看得见它们
from app.modules.audit import models as _audit_models  # noqa: F401

ADMIN_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "22222222-2222-2222-2222-222222222222"


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    def _override() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _headers(*, user_id: str, username: str, role: str) -> dict[str, str]:
    token = create_access_token(user_id=user_id, username=username, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    return _headers(user_id=ADMIN_ID, username="boss", role="admin")


@pytest.fixture()
def user_headers() -> dict[str, str]:
    return _headers(user_id=USER_ID, username="xiaoming", role="user")
