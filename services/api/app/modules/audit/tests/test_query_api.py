"""MD-05 + QA-01：审计查询的权限负例与游标分页。

契约：docs/api/openapi.yaml `/audit-logs`；规则：docs/03 §1 的十条硬约束。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.audit.service import AuditService

OBJECT_ID = "44444444-4444-4444-4444-444444444444"
BASE_TIME = datetime(2026, 10, 30, 8, 0, 0, tzinfo=UTC)


def _seed(db: Session, count: int = 3) -> None:
    """显式给时间戳：Windows 时钟精度约 15ms，连续写会撞同一微秒。"""
    service = AuditService(db)
    for i in range(count):
        service.write(
            action=f"route.update.{i}",
            object_type="route",
            object_id=OBJECT_ID,
            actor_id="11111111-1111-1111-1111-111111111111",
            actor_username="boss",
            reason=f"第 {i} 次修改",
            created_at=BASE_TIME + timedelta(minutes=i),
        )
        db.commit()


def test_requires_login(client: TestClient) -> None:
    resp = client.get("/api/v1/audit-logs")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_normal_user_forbidden(
    client: TestClient, db_session: Session, user_headers: dict[str, str]
) -> None:
    """普通用户查审计必须 403——负例优先于正例。"""
    _seed(db_session)
    resp = client.get("/api/v1/audit-logs", headers=user_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_admin_sees_newest_first(
    client: TestClient, db_session: Session, admin_headers: dict[str, str]
) -> None:
    _seed(db_session)
    resp = client.get("/api/v1/audit-logs", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 3
    assert body["next_cursor"] is None
    assert body["items"][0]["reason"] == "第 2 次修改"
    assert body["items"][0]["actor"]["username"] == "boss"


def test_filter_by_object_id(
    client: TestClient, db_session: Session, admin_headers: dict[str, str]
) -> None:
    _seed(db_session, count=2)
    AuditService(db_session).write(
        action="user.login",
        object_type="user",
        object_id="55555555-5555-5555-5555-555555555555",
    )
    db_session.commit()

    resp = client.get(
        "/api/v1/audit-logs",
        params={"object_type": "user"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert [item["object_type"] for item in resp.json()["items"]] == ["user"]


def test_cursor_pagination(
    client: TestClient, db_session: Session, admin_headers: dict[str, str]
) -> None:
    _seed(db_session, count=3)
    first = client.get("/api/v1/audit-logs", params={"limit": 2}, headers=admin_headers)
    assert first.status_code == 200
    page1 = first.json()
    assert len(page1["items"]) == 2
    assert page1["next_cursor"]

    second = client.get(
        "/api/v1/audit-logs",
        params={"limit": 2, "cursor": page1["next_cursor"]},
        headers=admin_headers,
    )
    assert second.status_code == 200
    page2 = second.json()
    assert len(page2["items"]) == 1
    assert page2["next_cursor"] is None
    assert page2["items"][0]["id"] not in {item["id"] for item in page1["items"]}


def test_bad_cursor_is_422(client: TestClient, admin_headers: dict[str, str]) -> None:
    resp = client.get(
        "/api/v1/audit-logs",
        params={"cursor": "not-a-cursor"},
        headers=admin_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_FAILED"


def test_limit_is_capped(client: TestClient, admin_headers: dict[str, str]) -> None:
    """limit 超过 50 直接被参数校验拦掉，不接受“多给点”。"""
    resp = client.get("/api/v1/audit-logs", params={"limit": 500}, headers=admin_headers)
    assert resp.status_code == 422
