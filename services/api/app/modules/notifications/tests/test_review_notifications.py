"""NT-02 验收测试：审核通过/退回时写入通知，退回通知必须带理由。

调用姿势模拟 moderation 模块：只经 NotificationsService.notify() 写入，
再用 HTTP GET /notifications（NT-01 的出口）确认用户真能看见。
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.deps import create_access_token
from app.core.errors import ValidationFailed
from app.modules.notifications.service import (
    REVIEW_APPROVED,
    REVIEW_REJECTED,
    REVIEW_REQUEST_CHANGES,
    NotificationsService,
)

ENDPOINT = "/api/v1/notifications"


def _auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(user_id=str(user_id), username="p2-owner", role="user")
    return {"Authorization": f"Bearer {token}"}


def _notify(
    session_factory: sessionmaker[Session],
    user_id: uuid.UUID,
    notif_type: str,
    payload: dict[str, Any] | None = None,
) -> uuid.UUID:
    """像 moderation 那样调一次写入，返回通知 id。"""
    with session_factory() as db:
        notification = NotificationsService(db).notify(user_id, notif_type, payload)
        notification_id = notification.id
        db.commit()
    return notification_id


def _items(client: TestClient, user_id: uuid.UUID) -> list[dict[str, Any]]:
    response = client.get(ENDPOINT, headers=_auth_headers(user_id))
    assert response.status_code == 200
    return response.json()["items"]


def test_approved_writes_notification_user_can_see(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """验收条件：审核通过时写入，作者能在列表里看到这条通知。"""
    me, route_id = uuid.uuid4(), uuid.uuid4()

    created = _notify(session_factory, me, REVIEW_APPROVED, {"route_id": str(route_id)})
    items = _items(client, me)

    assert len(items) == 1
    assert items[0]["id"] == str(created)
    assert items[0]["type"] == REVIEW_APPROVED
    assert items[0]["payload"] == {"route_id": str(route_id)}
    assert items[0]["read_at"] is None


def test_request_changes_carries_reason(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """验收条件：退回通知带理由（理由原样落到 payload，首尾空格去掉）。"""
    me = uuid.uuid4()

    _notify(session_factory, me, REVIEW_REQUEST_CHANGES, {"reason": "  图片太少，请补 3 张  "})

    payload = _items(client, me)[0]["payload"]
    assert payload["reason"] == "图片太少，请补 3 张"


@pytest.mark.parametrize("notif_type", [REVIEW_REQUEST_CHANGES, REVIEW_REJECTED])
@pytest.mark.parametrize("bad_payload", [None, {}, {"reason": ""}, {"reason": "   "}])
def test_reject_without_reason_fails_and_writes_nothing(
    client: TestClient,
    session_factory: sessionmaker[Session],
    notif_type: str,
    bad_payload: dict[str, Any] | None,
) -> None:
    """负例：退回类没有理由必须报错，且不能留下半条脏数据。"""
    me = uuid.uuid4()

    with pytest.raises(ValidationFailed) as exc_info:
        _notify(session_factory, me, notif_type, bad_payload)

    assert exc_info.value.code == "REVIEW_REASON_REQUIRED"
    assert exc_info.value.http_status == 422
    assert _items(client, me) == []


def test_notification_goes_only_to_decided_user(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """写入不串号：给 A 的通知，B 看不到。"""
    author, someone_else = uuid.uuid4(), uuid.uuid4()

    _notify(session_factory, author, REVIEW_APPROVED, {"route_id": str(uuid.uuid4())})

    assert len(_items(client, author)) == 1
    assert _items(client, someone_else) == []
