"""ID-04 验收：GET /users/{user_id}/profile（公开的个人主页）。

契约：docs/api/openapi.yaml `/users/{user_id}/profile`（security: []，只有 200/404）
与 components/schemas 的 UserProfile / RouteSummary；数据：docs/02 §2.1 的 users。

用例里的账号自己种，不依赖 conftest 那两条固定用户：这里的重点之一是 role/bio 这类
主页字段与"账号状态"，固定夹具改一次就会连着别处一起碎。
"""

from __future__ import annotations

import typing
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.identity.models import (
    ROLE_USER,
    STATUS_ACTIVE,
    STATUS_DISABLED,
    User,
)
from app.modules.identity.schemas import RouteSummaryOut
from app.modules.identity.service import IdentityService, hash_password

PROFILE_URL = "/api/v1/users/{user_id}/profile"
UNKNOWN_ID = "99999999-9999-9999-9999-999999999999"
# argon2 只算一次，别让每个用例都等 50ms
_PASSWORD_HASH = hash_password("password123")


def _add_user(
    db: Session,
    *,
    username: str,
    status: str = STATUS_ACTIVE,
    bio: str | None = None,
) -> User:
    user = User(
        username=username,
        bio=bio,
        password_hash=_PASSWORD_HASH,
        role=ROLE_USER,
        status=status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get(client: TestClient, user_id: object, headers: dict[str, str] | None = None):
    return client.get(PROFILE_URL.format(user_id=user_id), headers=headers)


@pytest.fixture()
def author(db_session: Session) -> User:
    return _add_user(db_session, username="wanderer", bio="沿着运河走")


# ===== 200 的形状 =====


def test_profile_returns_user_and_published_routes(client: TestClient, author: User) -> None:
    resp = _get(client, author.id)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"user", "published_routes"}
    assert isinstance(body["published_routes"], list)
    assert body["published_routes"] == [], "上游 routes 表还没落地，必须是空数组而不是 null"
    assert body["user"]["id"] == str(author.id)
    assert body["user"]["username"] == "wanderer"
    assert body["user"]["role"] == "user"
    assert body["user"]["bio"] == "沿着运河走"


def test_profile_hides_unknown_comment_count(client: TestClient, author: User) -> None:
    """comment_count 拿不到真值时整个不出现：契约里它是 integer，不是 nullable。"""
    body = _get(client, author.id).json()
    assert "comment_count" not in body


# ===== 公开端点：不需要令牌 =====


def test_profile_is_anonymous(client: TestClient, author: User) -> None:
    resp = _get(client, author.id)
    assert resp.status_code == 200
    assert "authorization" not in {key.lower() for key in resp.request.headers}


def test_profile_ignores_garbage_token(client: TestClient, author: User) -> None:
    """security: [] 意味着"有没有令牌都不影响"，坏令牌不该把它变成 401。"""
    resp = _get(client, author.id, headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 200


# ===== 404：不存在与已停用对外一致 =====


def test_profile_unknown_user_is_404(client: TestClient) -> None:
    resp = _get(client, UNKNOWN_ID)

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_profile_disabled_user_is_404(client: TestClient, db_session: Session) -> None:
    """停用账号的公开主页按"不存在"处理，不泄露这个 id 存在过。"""
    disabled = _add_user(db_session, username="gone", status=STATUS_DISABLED)

    resp = _get(client, disabled.id)

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_disabled_and_unknown_look_identical(client: TestClient, db_session: Session) -> None:
    disabled = _add_user(db_session, username="gone2", status=STATUS_DISABLED)

    disabled_body = _get(client, disabled.id).json()["error"]
    unknown_body = _get(client, UNKNOWN_ID).json()["error"]

    assert disabled_body["code"] == unknown_body["code"]
    assert disabled_body["message"] == unknown_body["message"]


# ===== 422：非法 uuid =====


def test_profile_invalid_uuid_is_422(client: TestClient) -> None:
    resp = _get(client, "not-a-uuid")

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"


# ===== 数据通路的桩：签名与出参先定死 =====


def test_list_published_routes_stub_is_wired(db_session: Session, author: User) -> None:
    """表没落地之前也必须是一个"签名正确、只是还没数据"的函数，不是硬编码常量。"""
    routes = IdentityService(db_session).list_published_routes(author.id)

    assert isinstance(routes, list)
    assert routes == []
    hints = typing.get_type_hints(IdentityService.list_published_routes)
    assert hints["return"] == list[RouteSummaryOut]
    assert hints["user_id"] is uuid.UUID
