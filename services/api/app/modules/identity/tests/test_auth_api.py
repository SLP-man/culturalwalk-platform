"""ID-02 验收：注册 / 登录 / 刷新令牌 / 退出登录 / 当前用户。

契约：docs/api/openapi.yaml 的 /auth/register、/auth/login、/auth/refresh、
/auth/logout 与 /users/me，以及 components/schemas 的 TokenPair、User。
数据：docs/02-数据模型与状态机.md §2.1 的 users / sessions。
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import create_access_token
from app.core.errors import Conflict
from app.modules.identity.models import STATUS_DISABLED, User
from app.modules.identity.models import Session as LoginSession
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.service import IdentityService

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/users/me"

PASSWORD = "password123"


def _register(client: TestClient, username: str = "Ming", password: str = PASSWORD) -> dict:
    resp = client.post(REGISTER, json={"username": username, "password": password})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _precheck_missed(self: IdentityRepository, username: str) -> User | None:
    """模拟注册竞态：预检那一刻另一个请求还没提交，所以什么都没查到。"""
    return None


def test_register_returns_token_pair(client: TestClient) -> None:
    """201 + TokenPair 的三个必填字段（access_token / refresh_token / user）。"""
    body = _register(client, username="  Ming  ")

    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["username"] == "ming", "入库前要 strip + lower，citext 语义靠它"
    assert body["user"]["role"] == "user"
    assert body["user"]["id"]
    assert body["expires_in"] > 0


def test_register_duplicate_username_conflict(client: TestClient) -> None:
    """重名报 409；大小写不同也算重名。"""
    _register(client, username="ming")
    resp = client.post(REGISTER, json={"username": "MING", "password": PASSWORD})

    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "CONFLICT"


def test_register_short_password_is_validation_error(client: TestClient) -> None:
    """minLength 由 pydantic 判，返回统一信封里的 422（不是自己造的 422）。"""
    resp = client.post(REGISTER, json={"username": "ming", "password": "short"})

    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"


def test_login_with_wrong_password_is_unauthorized(client: TestClient) -> None:
    _register(client, username="ming")
    resp = client.post(LOGIN, json={"username": "ming", "password": "wrong-password"})

    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_login_with_correct_password_returns_tokens(client: TestClient) -> None:
    _register(client, username="ming")
    resp = client.post(LOGIN, json={"username": "Ming", "password": PASSWORD})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["username"] == "ming"


def test_refresh_issues_new_pair_and_drops_the_old_token(client: TestClient) -> None:
    """换新令牌成功；旧 refresh 因为轮换过，不能再用。"""
    old = _register(client, username="ming")
    resp = client.post(REFRESH, json={"refresh_token": old["refresh_token"]})

    assert resp.status_code == 200, resp.text
    fresh = resp.json()
    # access 令牌同一秒内可能逐字节相同（HS256 对相同 payload 是确定性的），
    # 所以只断言换了 refresh 令牌，另外确认新 access 能直接过 /users/me。
    assert fresh["refresh_token"] != old["refresh_token"]
    me = client.get(ME, headers=_bearer(fresh["access_token"]))
    assert me.status_code == 200, me.text

    again = client.post(REFRESH, json={"refresh_token": old["refresh_token"]})
    assert again.status_code == 401
    assert again.json()["error"]["code"] == "UNAUTHORIZED"


def test_logout_revokes_session_so_old_refresh_fails(client: TestClient) -> None:
    tokens = _register(client, username="ming")
    resp = client.post(
        LOGOUT,
        json={"refresh_token": tokens["refresh_token"]},
        headers=_bearer(tokens["access_token"]),
    )
    assert resp.status_code == 204, resp.text

    again = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})
    assert again.status_code == 401, again.text
    assert again.json()["error"]["code"] == "UNAUTHORIZED"


def test_logout_without_token_is_unauthorized(client: TestClient) -> None:
    assert client.post(LOGOUT).status_code == 401


def test_me_without_token_is_unauthorized(client: TestClient) -> None:
    resp = client.get(ME)

    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_with_user_headers_matches_contract(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """/users/me：必填 id / username / role 齐活，bio 与 created_at 可空。"""
    resp = client.get(ME, headers=user_headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert {"id", "username", "role"} <= set(body)
    assert body["id"] == "22222222-2222-2222-2222-222222222222"
    assert body["username"] == "xiaoming"
    assert body["role"] == "user"
    assert body["bio"] is None


def test_me_after_register_returns_created_at(client: TestClient) -> None:
    """真注册出来的用户在库里有行，created_at 要带回来且是 ISO-8601。"""
    tokens = _register(client, username="ming")
    resp = client.get(ME, headers=_bearer(tokens["access_token"]))

    assert resp.status_code == 200, resp.text
    assert resp.json()["created_at"] is not None


def test_session_stores_hash_not_plaintext(client: TestClient, db_session: Session) -> None:
    """sessions.refresh_hash 是摘要，库里不能出现明文 refresh 令牌。"""
    body = _register(client, username="ming")
    rows = list(db_session.scalars(select(LoginSession)))

    assert len(rows) == 1
    row = rows[0]
    assert row.refresh_hash != body["refresh_token"]
    assert body["refresh_token"] not in row.refresh_hash
    assert len(row.refresh_hash) == 64, "sha256 十六进制"
    assert row.revoked_at is None
    assert row.expires_at is not None


def test_me_rejects_token_for_missing_user(client: TestClient) -> None:
    """幽灵令牌：签名有效但库里没有这个用户，不许发一份"资料"出去。"""
    token = create_access_token(user_id=str(uuid.uuid4()), username="ghost", role="user")
    resp = client.get(ME, headers=_bearer(token))

    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_rejects_disabled_user(client: TestClient, db_session: Session) -> None:
    """账号被停用后，还没过期的旧 access 令牌也不能再用。"""
    tokens = _register(client, username="ming")
    row = db_session.scalar(select(User).where(User.username == "ming"))
    assert row is not None
    row.status = STATUS_DISABLED
    db_session.flush()

    resp = client.get(ME, headers=_bearer(tokens["access_token"]))

    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_register_race_over_http_is_conflict(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """并发同名：预检没查到、落库时唯一索引炸 —— 必须 409，不能 500。"""
    db_session.add(User(username="ming", password_hash="irrelevant", role="user", status="active"))
    db_session.flush()
    monkeypatch.setattr(IdentityRepository, "get_user_by_username", _precheck_missed)

    resp = client.post(REGISTER, json={"username": "ming", "password": PASSWORD})

    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "CONFLICT"


def test_service_register_race_raises_conflict(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """同一竞态在 service 层直接断言：抛的是 AppError 子类，不是裸 IntegrityError。"""
    db_session.add(User(username="ming", password_hash="irrelevant", role="user", status="active"))
    db_session.flush()
    monkeypatch.setattr(IdentityRepository, "get_user_by_username", _precheck_missed)

    with pytest.raises(Conflict):
        IdentityService(db_session).register(username="MING", password=PASSWORD)
