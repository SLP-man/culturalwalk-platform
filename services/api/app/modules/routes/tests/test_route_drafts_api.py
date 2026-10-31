# RT-01：路线草稿 CRUD 的接口测试
"""用 SQLite 内存库跑真实请求链路（router → service → repository → 数据库）。

为什么不连 Postgres：这里要钉住的是接口层的行为——状态码、错误信封、分页游标、
幂等、乐观锁；换一个数据库实现也不该变，所以用 conftest 的共享夹具就够。
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.routes.models import DraftState, Route, RouteChannel, RouteDraft, RouteStatus

API = "/api/v1/route-drafts"
# conftest 里种下的两个账号（user / admin），跨用户越权用例就靠这一对。
OWNER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
OTHER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _payload(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "title": "老城半日",
        "summary": "从城墙走到茶馆",
        "theme_tags": ["history", "walk"],
        "duration_minutes": 180,
    }
    body.update(overrides)
    return body


def _key() -> str:
    return str(uuid.uuid4())


def _create(
    client: TestClient,
    headers: dict[str, str],
    *,
    key: str | None = None,
    **overrides: Any,
) -> Any:
    return client.post(
        API,
        json=_payload(**overrides),
        headers={**headers, "Idempotency-Key": key or _key()},
    )


def _patch(
    client: TestClient,
    headers: dict[str, str],
    draft_id: str,
    *,
    if_match: str | None = "1",
    body: dict[str, Any] | None = None,
    key: str | None = None,
) -> Any:
    request_headers = {**headers, "Idempotency-Key": key or _key()}
    if if_match is not None:
        request_headers["If-Match"] = if_match
    return client.patch(
        f"{API}/{draft_id}", json=body or {"title": "改过的标题"}, headers=request_headers
    )


def _assert_error(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status, response.text
    error = response.json()["error"]
    assert error["code"] == code
    return error


def _create_draft(client: TestClient, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    response = _create(client, headers, **overrides)
    assert response.status_code == 201, response.text
    return response.json()


# ---------- 1. 匿名一律 401 ----------


def test_anonymous_requests_are_unauthorized(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    draft_id = _create_draft(client, user_headers)["id"]
    cases: list[tuple[str, str, dict[str, Any]]] = [
        ("get", API, {"params": {"limit": 20}}),
        (
            "post",
            API,
            {"json": _payload(), "headers": {"Idempotency-Key": _key()}},
        ),
        ("get", f"{API}/{draft_id}", {}),
        (
            "patch",
            f"{API}/{draft_id}",
            {
                "json": {"title": "匿名改"},
                "headers": {"Idempotency-Key": _key(), "If-Match": "1"},
            },
        ),
        ("delete", f"{API}/{draft_id}", {}),
    ]
    for method, path, kwargs in cases:
        response = getattr(client, method)(path, **kwargs)
        # 请求体是合法的，唯一缺的就是 Authorization：这样才证明 401 来自鉴权而不是参数校验。
        _assert_error(response, 401, "UNAUTHORIZED")


# ---------- 2. 新建 ----------


def test_create_draft_returns_201_and_writes_user_route(
    client: TestClient, db_session: Session, user_headers: dict[str, str]
) -> None:
    body = _create_draft(client, user_headers)

    assert body["state"] == "EDITING"
    assert body["lock_version"] == 1
    assert body["title"] == "老城半日"
    assert body["summary"] == "从城墙走到茶馆"
    assert body["updated_at"]
    uuid.UUID(body["id"])
    uuid.UUID(body["route_id"])

    route = db_session.get(Route, uuid.UUID(body["route_id"]))
    assert route is not None
    assert route.author_id == OWNER_ID
    assert route.channel is RouteChannel.USER
    assert route.status is RouteStatus.DRAFT
    assert route.theme_tags == ["history", "walk"]
    assert route.duration_minutes == 180
    # 中文标题归一化后是空串，slug 走 route 兜底前缀 + 短 uuid，不会撞唯一索引。
    assert route.slug.startswith("route-")


# ---------- 3. 列表：只看自己的 + 游标分页 ----------


def test_list_only_returns_own_drafts_and_paginates(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    for title in ("第一篇", "第二篇", "第三篇"):
        _create_draft(client, user_headers, title=title)
    other = _create_draft(client, admin_headers, title="别人的草稿")

    first = client.get(API, params={"limit": 2}, headers=user_headers)
    assert first.status_code == 200, first.text
    page1 = first.json()
    assert [item["title"] for item in page1["items"]] == ["第三篇", "第二篇"]
    assert page1["next_cursor"]
    assert all(item["id"] != other["id"] for item in page1["items"])

    second = client.get(
        API, params={"limit": 2, "cursor": page1["next_cursor"]}, headers=user_headers
    )
    assert second.status_code == 200, second.text
    page2 = second.json()
    assert [item["title"] for item in page2["items"]] == ["第一篇"]
    assert page2["next_cursor"] is None
    assert other["id"] not in {item["id"] for item in page2["items"]}


@pytest.mark.parametrize("limit", [0, 51])
def test_list_rejects_out_of_range_limit(
    client: TestClient, user_headers: dict[str, str], limit: int
) -> None:
    response = client.get(API, params={"limit": limit}, headers=user_headers)
    _assert_error(response, 422, "VALIDATION_FAILED")


# ---------- 4. 详情 ----------


def test_get_detail_returns_nodes_empty_and_no_cost(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    created = _create_draft(client, user_headers)
    response = client.get(f"{API}/{created['id']}", headers=user_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == created["id"]
    assert body["nodes"] == []
    # 节点与费用属 RT-02：此刻必须有 nodes、必须没有 cost，别给前端一个空对象假数据。
    assert "cost" not in body


def test_get_detail_forbidden_for_other_user(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    created = _create_draft(client, user_headers)
    response = client.get(f"{API}/{created['id']}", headers=admin_headers)
    _assert_error(response, 403, "FORBIDDEN")


def test_get_detail_not_found_for_unknown_draft(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    response = client.get(f"{API}/{uuid.uuid4()}", headers=user_headers)
    _assert_error(response, 404, "NOT_FOUND")


def test_get_detail_rejects_invalid_uuid(client: TestClient, user_headers: dict[str, str]) -> None:
    response = client.get(f"{API}/not-a-uuid", headers=user_headers)
    error = _assert_error(response, 422, "VALIDATION_FAILED")
    assert error["details"][0]["field"] == "draft_id"


# ---------- 5. 更新：If-Match 与所有权 ----------


def test_patch_requires_if_match(client: TestClient, user_headers: dict[str, str]) -> None:
    created = _create_draft(client, user_headers)
    response = _patch(client, user_headers, created["id"], if_match=None)
    error = _assert_error(response, 422, "VALIDATION_FAILED")
    assert error["details"][0]["field"] == "If-Match"


def test_patch_with_stale_version_is_412(client: TestClient, user_headers: dict[str, str]) -> None:
    created = _create_draft(client, user_headers)
    response = _patch(client, user_headers, created["id"], if_match="99")
    _assert_error(response, 412, "PRECONDITION_FAILED")


def test_patch_bumps_lock_version_and_updates_route(
    client: TestClient, db_session: Session, user_headers: dict[str, str]
) -> None:
    created = _create_draft(client, user_headers)
    response = _patch(
        client,
        user_headers,
        created["id"],
        body={"title": "改过的标题", "duration_minutes": 90},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["lock_version"] == 2
    assert body["title"] == "改过的标题"
    # PATCH 后必须把新版本号交回去，否则客户端下一次改还得先 GET 一趟。
    assert response.headers["etag"] == '"2"'

    route = db_session.get(Route, uuid.UUID(created["route_id"]))
    assert route is not None
    assert route.title == "改过的标题"
    assert route.duration_minutes == 90
    # 只传了 title 与 duration_minutes：没传的字段必须原样留着。
    assert route.summary == "从城墙走到茶馆"


def test_patch_forbidden_for_other_user(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    created = _create_draft(client, user_headers)
    response = _patch(client, admin_headers, created["id"], if_match="1")
    _assert_error(response, 403, "FORBIDDEN")


# ---------- 6. 幂等 ----------


def test_post_is_idempotent_with_same_key_and_body(
    client: TestClient, db_session: Session, user_headers: dict[str, str]
) -> None:
    key = _key()
    first = _create(client, user_headers, key=key)
    second = _create(client, user_headers, key=key)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    total = db_session.scalar(select(func.count()).select_from(RouteDraft))
    assert total == 1


def test_post_with_same_key_different_body_is_409(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    key = _key()
    assert _create(client, user_headers, key=key).status_code == 201
    response = _create(client, user_headers, key=key, title="换了个标题")
    error = _assert_error(response, 409, "IDEMPOTENCY_KEY_REUSED")
    assert error["details"][0]["field"] == "Idempotency-Key"


# ---------- 7. 删除 ----------


def test_delete_then_get_is_404(
    client: TestClient, db_session: Session, user_headers: dict[str, str]
) -> None:
    created = _create_draft(client, user_headers)
    response = client.delete(f"{API}/{created['id']}", headers=user_headers)
    assert response.status_code == 204, response.text
    assert response.content == b""
    _assert_error(client.get(f"{API}/{created['id']}", headers=user_headers), 404, "NOT_FOUND")
    # 草稿删掉后它指向的 routes 行也不能留着，否则列表 join 会捡到孤儿。
    assert db_session.get(Route, uuid.UUID(created["route_id"])) is None


def test_delete_forbidden_for_other_user(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    created = _create_draft(client, user_headers)
    _assert_error(client.delete(f"{API}/{created['id']}", headers=admin_headers), 403, "FORBIDDEN")
    assert client.get(f"{API}/{created['id']}", headers=user_headers).status_code == 200


# ---------- 8. 锁定态 ----------


def test_patch_locked_draft_is_409(
    client: TestClient, db_session: Session, user_headers: dict[str, str]
) -> None:
    created = _create_draft(client, user_headers)
    draft = db_session.get(RouteDraft, uuid.UUID(created["id"]))
    assert draft is not None
    draft.state = DraftState.SUBMITTED_LOCKED
    db_session.flush()

    response = _patch(client, user_headers, created["id"], if_match="1")
    error = _assert_error(response, 409, "CONFLICT")
    # 文案要点明是锁定态，否则客户端分不清 409 是该刷新版本号还是根本改不了。
    assert "锁定" in error["message"]
    assert "SUBMITTED_LOCKED" in error["message"]
