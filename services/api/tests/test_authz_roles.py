"""ID-03：角色依赖 require_role()。

负例优先：普通用户打管理端必须 403，且响应体走 app/core/errors.py 的统一信封
（docs/03 §1.4：前端按 error.code 分支，所以这里断言 code 而不是文案）。

探针路由单独用一个 FastAPI 应用挂载，不动全局 app——否则用例之间会互相污染路由表。
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.deps import AdminDep, CurrentUser, create_access_token, require_role
from app.core.errors import AppError, app_error_handler

EDITOR_ID = "33333333-3333-3333-3333-333333333333"


def _headers(*, user_id: str, username: str, role: str) -> dict[str, str]:
    token = create_access_token(user_id=user_id, username=username, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def editor_headers() -> dict[str, str]:
    return _headers(user_id=EDITOR_ID, username="nina", role="editor")


def _build_probe_app() -> FastAPI:
    """只用来验证依赖本身，所以一个业务路由都不挂。"""
    probe = FastAPI()
    probe.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]

    @probe.get("/probe/admin-only")
    def admin_only(user: Annotated[CurrentUser, Depends(require_role("admin"))]) -> dict[str, str]:
        return {"role": user.role}

    @probe.get("/probe/no-roles")
    def no_roles(user: Annotated[CurrentUser, Depends(require_role())]) -> dict[str, str]:
        return {"role": user.role}

    @probe.get("/probe/legacy-admin")
    def legacy_admin(user: AdminDep) -> dict[str, str]:
        return {"role": user.role}

    return probe


@pytest.fixture()
def probe_client() -> Iterator[TestClient]:
    with TestClient(_build_probe_app()) as test_client:
        yield test_client


# ===== 真实端点的负例（契约：/api/v1/audit-logs 只给管理员） =====


def test_user_role_token_gets_403_on_admin_endpoint(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/audit-logs", headers=user_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_missing_token_gets_401(client: TestClient) -> None:
    """没令牌是"你是谁"的问题，不能退化成 403。"""
    resp = client.get("/api/v1/audit-logs")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_admin_token_is_not_forbidden(client: TestClient, admin_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/audit-logs", headers=admin_headers)
    assert resp.status_code != 403
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_forbidden_body_keeps_error_envelope(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    body = client.get("/api/v1/audit-logs", headers=user_headers).json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "request_id", "details"}
    assert body["error"]["message"]
    assert body["error"]["details"] == []


# ===== 依赖本身的探针用例 =====


def test_require_role_rejects_user(probe_client: TestClient, user_headers: dict[str, str]) -> None:
    resp = probe_client.get("/probe/admin-only", headers=user_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_require_role_allows_admin(probe_client: TestClient, admin_headers: dict[str, str]) -> None:
    resp = probe_client.get("/probe/admin-only", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == {"role": "admin"}


def test_require_role_requires_login(probe_client: TestClient) -> None:
    resp = probe_client.get("/probe/admin-only")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_require_role_without_roles_denies_everyone(
    probe_client: TestClient, admin_headers: dict[str, str]
) -> None:
    """空参数固定为 fail-closed：漏写角色不许变成"谁都进得来"。"""
    resp = probe_client.get("/probe/no-roles", headers=admin_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_require_role_without_roles_still_401_for_anonymous(probe_client: TestClient) -> None:
    """空参数不放行任何人，但"没登录"仍然优先报 401。"""
    resp = probe_client.get("/probe/no-roles")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_require_admin_still_accepts_editor(
    probe_client: TestClient, editor_headers: dict[str, str]
) -> None:
    """require_admin 改成 require_role("admin", "editor") 后行为必须不变。"""
    resp = probe_client.get("/probe/legacy-admin", headers=editor_headers)
    assert resp.status_code == 200
    assert resp.json() == {"role": "editor"}


def test_require_admin_rejects_user(probe_client: TestClient, user_headers: dict[str, str]) -> None:
    resp = probe_client.get("/probe/legacy-admin", headers=user_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
