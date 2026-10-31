# RT-02：草稿节点增删改与顺序的接口测试
"""钉住 issue #17 的验收句：「调整顺序后重新 GET 顺序正确」。

与 RT-01 同一套夹具：内存 SQLite + 覆盖 get_db + 现成 token，跑真实请求链路
（router → service → repository → 数据库）。顺序这类东西最容易"看起来对"——
断言到具体 place_id 序列，而不是只断言 status_code 200。
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.routes.models import DraftState, RouteDraft, RouteNode

API = "/api/v1/route-drafts"

# 固定的三个地点 id：顺序断言要能一眼看出谁在第几位，随机 uuid 做不到。
PLACE_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1"
PLACE_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2"
PLACE_C = "cccccccc-cccc-4ccc-8ccc-ccccccccccc3"


def _key() -> str:
    return str(uuid.uuid4())


def _draft_payload(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"title": "老城半日", "summary": "从城墙走到茶馆"}
    body.update(overrides)
    return body


def _create_draft(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    response = client.post(
        API, json=_draft_payload(), headers={**headers, "Idempotency-Key": _key()}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _node(place_id: str, **overrides: Any) -> dict[str, Any]:
    node: dict[str, Any] = {"place_id": place_id, "stay_minutes": 45, "transport": "walk"}
    node.update(overrides)
    return node


def _put_nodes(
    client: TestClient,
    headers: dict[str, str],
    draft_id: str,
    nodes: list[dict[str, Any]],
    *,
    if_match: str | None = "1",
    omit_key: bool = False,
) -> Any:
    request_headers = dict(headers)
    if not omit_key:
        request_headers["Idempotency-Key"] = _key()
    if if_match is not None:
        request_headers["If-Match"] = if_match
    return client.put(f"{API}/{draft_id}/nodes", json={"nodes": nodes}, headers=request_headers)


def _assert_error(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status, response.text
    error = response.json()["error"]
    assert error["code"] == code
    return error


def _place_ids(body: dict[str, Any]) -> list[str]:
    return [node["place_id"] for node in body["nodes"]]


def _positions(body: dict[str, Any]) -> list[int]:
    return [node["position"] for node in body["nodes"]]


# ---------- 1. 匿名一律 401 ----------


def test_put_nodes_anonymous_is_401(client: TestClient, user_headers: dict[str, str]) -> None:
    draft_id = _create_draft(client, user_headers)["id"]
    # Idempotency-Key 与 If-Match 都带齐，唯一缺的是 Authorization：
    # 这样才证明 401 来自鉴权，而不是被缺头导致的 422 拦住。
    response = client.put(
        f"{API}/{draft_id}/nodes",
        json={"nodes": [_node(PLACE_A)]},
        headers={"Idempotency-Key": _key(), "If-Match": "1"},
    )
    _assert_error(response, 401, "UNAUTHORIZED")


# ---------- 2. 写入与版本号 ----------


def test_put_nodes_returns_positions_and_bumps_lock_version(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    created = _create_draft(client, user_headers)
    assert created["lock_version"] == 1

    response = _put_nodes(
        client,
        user_headers,
        created["id"],
        [_node(PLACE_A), _node(PLACE_B), _node(PLACE_C)],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["nodes"]) == 3
    # position 由服务端按数组下标写死，客户端不需要传。
    assert _positions(body) == [0, 1, 2]
    assert body["lock_version"] == 2
    # 与 PATCH 一致：新版本号必须回给客户端，否则下一次改还得先 GET 一趟。
    assert response.headers["etag"] == '"2"'


# ---------- 3. issue #17 的验收句：调序后 GET 顺序正确 ----------


def test_reordering_nodes_is_reflected_in_get_detail(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    draft_id = _create_draft(client, user_headers)["id"]
    first = _put_nodes(
        client, user_headers, draft_id, [_node(PLACE_A), _node(PLACE_B), _node(PLACE_C)]
    )
    assert first.status_code == 200, first.text
    assert _place_ids(first.json()) == [PLACE_A, PLACE_B, PLACE_C]

    # 同样三个节点换顺序：C 挪到最前。
    second = _put_nodes(
        client,
        user_headers,
        draft_id,
        [_node(PLACE_C), _node(PLACE_A), _node(PLACE_B)],
        if_match="2",
    )
    assert second.status_code == 200, second.text
    assert second.json()["lock_version"] == 3

    detail = client.get(f"{API}/{draft_id}", headers=user_headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    # 这一句就是 issue #17 的验收句：调完顺序，重新 GET 拿到的顺序与请求一致。
    assert _place_ids(body) == [PLACE_C, PLACE_A, PLACE_B]
    assert _positions(body) == [0, 1, 2]


# ---------- 4. 整表替换语义 ----------


def test_put_replaces_all_previous_nodes(
    client: TestClient, db_session: Session, user_headers: dict[str, str]
) -> None:
    draft_id = _create_draft(client, user_headers)["id"]
    assert (
        _put_nodes(
            client, user_headers, draft_id, [_node(PLACE_A), _node(PLACE_B), _node(PLACE_C)]
        ).status_code
        == 200
    )

    response = _put_nodes(client, user_headers, draft_id, [_node(PLACE_B)], if_match="2")
    assert response.status_code == 200, response.text

    body = client.get(f"{API}/{draft_id}", headers=user_headers).json()
    assert len(body["nodes"]) == 1
    assert body["nodes"][0]["position"] == 0
    assert body["nodes"][0]["place_id"] == PLACE_B
    # 旧行必须真的被删掉，而不是留着变成脏数据——直接数库里的行。
    total = db_session.scalar(
        select(func.count()).select_from(RouteNode).where(RouteNode.draft_id == uuid.UUID(draft_id))
    )
    assert total == 1


# ---------- 5. 清空 ----------


def test_put_empty_nodes_clears_draft(
    client: TestClient, db_session: Session, user_headers: dict[str, str]
) -> None:
    draft_id = _create_draft(client, user_headers)["id"]
    assert _put_nodes(client, user_headers, draft_id, [_node(PLACE_A)]).status_code == 200

    response = _put_nodes(client, user_headers, draft_id, [], if_match="2")
    assert response.status_code == 200, response.text
    assert response.json()["nodes"] == []

    body = client.get(f"{API}/{draft_id}", headers=user_headers).json()
    assert body["nodes"] == []
    total = db_session.scalar(select(func.count()).select_from(RouteNode))
    assert total == 0


# ---------- 6. 权限与存在性 ----------


def test_put_nodes_forbidden_for_other_user(
    client: TestClient,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    draft_id = _create_draft(client, user_headers)["id"]
    response = _put_nodes(client, admin_headers, draft_id, [_node(PLACE_A)])
    _assert_error(response, 403, "FORBIDDEN")


def test_put_nodes_not_found_for_unknown_draft(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    response = _put_nodes(client, user_headers, str(uuid.uuid4()), [_node(PLACE_A)])
    _assert_error(response, 404, "NOT_FOUND")


def test_put_nodes_rejects_invalid_uuid(client: TestClient, user_headers: dict[str, str]) -> None:
    response = client.put(
        f"{API}/not-a-uuid/nodes",
        json={"nodes": [_node(PLACE_A)]},
        headers={**user_headers, "Idempotency-Key": _key(), "If-Match": "1"},
    )
    error = _assert_error(response, 422, "VALIDATION_FAILED")
    assert error["details"][0]["field"] == "draft_id"


# ---------- 7. 乐观锁 ----------


def test_put_nodes_with_stale_if_match_is_412(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    draft_id = _create_draft(client, user_headers)["id"]
    response = _put_nodes(client, user_headers, draft_id, [_node(PLACE_A)], if_match="99")
    _assert_error(response, 412, "PRECONDITION_FAILED")


def test_put_nodes_requires_if_match(client: TestClient, user_headers: dict[str, str]) -> None:
    draft_id = _create_draft(client, user_headers)["id"]
    response = _put_nodes(client, user_headers, draft_id, [_node(PLACE_A)], if_match=None)
    error = _assert_error(response, 422, "VALIDATION_FAILED")
    assert error["details"][0]["field"] == "If-Match"


def test_put_nodes_requires_idempotency_key(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    draft_id = _create_draft(client, user_headers)["id"]
    response = _put_nodes(client, user_headers, draft_id, [_node(PLACE_A)], omit_key=True)
    error = _assert_error(response, 422, "VALIDATION_FAILED")
    assert error["details"][0]["field"] == "Idempotency-Key"


# ---------- 8. 锁定态 ----------


def test_put_nodes_locked_draft_is_409(
    client: TestClient, db_session: Session, user_headers: dict[str, str]
) -> None:
    draft_id = _create_draft(client, user_headers)["id"]
    draft = db_session.get(RouteDraft, uuid.UUID(draft_id))
    assert draft is not None
    draft.state = DraftState.SUBMITTED_LOCKED
    db_session.flush()

    # 版本号是最新的，仍然要 409：先判状态再判版本，文案要点明是锁定态。
    response = _put_nodes(client, user_headers, draft_id, [_node(PLACE_A)], if_match="1")
    error = _assert_error(response, 409, "CONFLICT")
    assert "锁定" in error["message"]
    assert "SUBMITTED_LOCKED" in error["message"]


# ---------- 9. 参数校验 ----------


@pytest.mark.parametrize(
    ("case", "node"),
    [
        ("stay_minutes 低于下限", _node(PLACE_A, stay_minutes=9)),
        ("stay_minutes 超过上限", _node(PLACE_A, stay_minutes=481)),
        ("transport 不在枚举里", _node(PLACE_A, transport="plane")),
        ("节点上多传了字段", {**_node(PLACE_A), "foo": 1}),
        ("position 不是客户端能传的", _node(PLACE_A, position=7)),
        ("price_min 大于 price_max", _node(PLACE_A, price_min=5000, price_max=1000)),
    ],
)
def test_put_nodes_validation_errors(
    client: TestClient, user_headers: dict[str, str], case: str, node: dict[str, Any]
) -> None:
    draft_id = _create_draft(client, user_headers)["id"]
    response = _put_nodes(client, user_headers, draft_id, [node])
    _assert_error(response, 422, "VALIDATION_FAILED")


def test_put_nodes_allows_repeated_place(client: TestClient, user_headers: dict[str, str]) -> None:
    # 一趟走两遍同一个地点是合理需求：位置不同即可，place_id 不去重。
    draft_id = _create_draft(client, user_headers)["id"]
    response = _put_nodes(
        client, user_headers, draft_id, [_node(PLACE_A), _node(PLACE_B), _node(PLACE_A)]
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert _place_ids(body) == [PLACE_A, PLACE_B, PLACE_A]
    assert _positions(body) == [0, 1, 2]


# ---------- 10. GET 详情的形状 ----------


def test_get_detail_omits_place_and_cost_but_keeps_place_id(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    draft_id = _create_draft(client, user_headers)["id"]
    assert (
        _put_nodes(
            client, user_headers, draft_id, [_node(PLACE_A, price_min=2500, price_max=3800)]
        ).status_code
        == 200
    )

    body = client.get(f"{API}/{draft_id}", headers=user_headers).json()
    # 费用汇总属 RT-04，此刻没算过就整个键不出现，而不是回 {}。
    assert "cost" not in body
    node = body["nodes"][0]
    # places 表还不存在，编 name/lat/lon 出来就是造假数据：整个 place 键不出现。
    assert "place" not in node
    assert node["place_id"] == PLACE_A
    assert node["stay_minutes"] == 45
    assert node["transport"] == "walk"
    assert node["price_min"] == 2500
    assert node["price_max"] == 3800
