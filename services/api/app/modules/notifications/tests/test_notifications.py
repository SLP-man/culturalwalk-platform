"""NT-01 验收测试：GET /notifications 只看自己的 + 游标分页 + 负例。

测试自带内存 SQLite，不依赖本机/CI 的 PostgreSQL（表用 create_all 现建）。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session, sessionmaker

from app.core.deps import create_access_token
from app.modules.notifications.models import Notification

ENDPOINT = "/api/v1/notifications"


def _auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(user_id=str(user_id), username="p2-owner", role="user")
    return {"Authorization": f"Bearer {token}"}


def _seed(
    session_factory: sessionmaker[Session],
    user_id: uuid.UUID,
    count: int,
    *,
    base_time: datetime | None = None,
) -> list[uuid.UUID]:
    """按时间递增造 count 条通知，返回按创建顺序排列的 id。"""
    start = base_time or datetime(2026, 10, 28, 8, 0, tzinfo=UTC)
    with session_factory() as db:
        rows = [
            Notification(
                user_id=user_id,
                type="review_request_changes",
                payload={"index": index},
                created_at=start + timedelta(minutes=index),
            )
            for index in range(count)
        ]
        db.add_all(rows)
        db.commit()
        return [row.id for row in rows]


def _items(response: Response) -> list[dict]:
    return response.json()["items"]


def test_requires_login(client: TestClient) -> None:
    """负例：未登录必须 401，且错误包结构符合契约。"""
    response = client.get(ENDPOINT)

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert set(body["error"]) == {"code", "message", "request_id", "details"}


def test_only_returns_own_notifications(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """验收条件：只能看自己的。"""
    me, other = uuid.uuid4(), uuid.uuid4()
    mine = _seed(session_factory, me, 3)
    theirs = _seed(session_factory, other, 2, base_time=datetime(2026, 10, 28, 9, 0, tzinfo=UTC))

    response = client.get(ENDPOINT, headers=_auth_headers(me))

    assert response.status_code == 200
    returned = {item["id"] for item in _items(response)}
    assert returned == {str(item_id) for item_id in mine}
    assert returned.isdisjoint({str(item_id) for item_id in theirs})
    assert response.json()["next_cursor"] is None


def test_ignores_user_id_query_param(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """负例：想用 query 参数偷看别人的通知 —— 参数被忽略，仍只返回自己的。"""
    me, other = uuid.uuid4(), uuid.uuid4()
    mine = _seed(session_factory, me, 1)
    _seed(session_factory, other, 1)

    response = client.get(ENDPOINT, params={"user_id": str(other)}, headers=_auth_headers(me))

    assert response.status_code == 200
    assert [item["id"] for item in _items(response)] == [str(mine[0])]


def test_order_is_newest_first(client: TestClient, session_factory: sessionmaker[Session]) -> None:
    me = uuid.uuid4()
    created = _seed(session_factory, me, 3)

    response = client.get(ENDPOINT, headers=_auth_headers(me))

    assert [item["id"] for item in _items(response)] == [str(i) for i in reversed(created)]


def test_cursor_pagination_walks_all_pages(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    me = uuid.uuid4()
    created = _seed(session_factory, me, 5)
    headers = _auth_headers(me)

    collected: list[str] = []
    cursor: str | None = None
    for _ in range(3):  # 5 条 / 每页 2 条 = 3 页
        params = {"limit": 2} | ({"cursor": cursor} if cursor else {})
        response = client.get(ENDPOINT, params=params, headers=headers)
        assert response.status_code == 200
        collected += [item["id"] for item in _items(response)]
        cursor = response.json()["next_cursor"]
        if cursor is None:
            break

    assert collected == [str(i) for i in reversed(created)]
    assert cursor is None


def test_empty_list(client: TestClient) -> None:
    me = uuid.uuid4()

    response = client.get(ENDPOINT, headers=_auth_headers(me))

    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


def test_invalid_cursor_is_rejected(client: TestClient) -> None:
    """负例：游标乱传 → 400 + 固定错误码（不是 500）。"""
    response = client.get(
        ENDPOINT, params={"cursor": "not-a-cursor"}, headers=_auth_headers(uuid.uuid4())
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CURSOR"


def test_limit_out_of_range_is_rejected(client: TestClient) -> None:
    """负例：limit 超上限 50 → 422。"""
    headers = _auth_headers(uuid.uuid4())

    assert client.get(ENDPOINT, params={"limit": 51}, headers=headers).status_code == 422
    assert client.get(ENDPOINT, params={"limit": 0}, headers=headers).status_code == 422


def test_payload_and_timestamps_shape(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """契约形状：id/type/payload/read_at/created_at，时间带时区，read_at 可空。"""
    me = uuid.uuid4()
    _seed(session_factory, me, 1)

    response = client.get(ENDPOINT, headers=_auth_headers(me))

    item = _items(response)[0]
    assert set(item) == {"id", "type", "payload", "read_at", "created_at"}
    assert item["type"] == "review_request_changes"
    assert item["payload"] == {"index": 0}
    assert item["read_at"] is None
    created_at = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
    assert created_at.tzinfo is not None
