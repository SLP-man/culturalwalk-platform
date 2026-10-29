# PL-02：POST /plans 的接口测试
"""用 SQLite 内存库跑真实请求链路（router → service → repository → 数据库）。

为什么不连 Postgres：本机开发机不一定有库，CI 里已经有 Postgres job 跑迁移；
这里要钉住的是"接口层的行为"——状态码、错误信封、幂等、入库内容，
换一个数据库实现也不该变，所以 SQLite 够用而且快。
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.core.deps import create_access_token
from app.main import create_app
from app.modules.planner.models import Itinerary, PlanRun, PlanState

API = "/api/v1/plans"


@pytest.fixture()
def session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        # 内存库默认每个连接一个独立的库，StaticPool 让所有连接共用同一个，建的表才在
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        db = session_factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth() -> tuple[dict[str, str], str]:
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id=user_id, username="feral0702", role="user")
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": str(uuid.uuid4())}
    return headers, user_id


def _payload(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "city": "长沙",
        "days": 3,
        "people": 2,
        "budget_total": 150000,  # 1500 元，单位是分
        "day_parts": ["morning", "evening"],
        "themes": ["老街", "夜宵"],
        "transport": ["metro", "walk"],
        "pace": "relaxed",
    }
    data.update(overrides)
    return data


def _error_details(response) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
    return response.json()["error"]["details"]


# ===== 正常路径 =====


def test_提交规划返回202且进入生成中(
    client: TestClient, auth: tuple[dict[str, str], str], session_factory: sessionmaker[Session]
) -> None:
    headers, _ = auth
    response = client.post(API, json=_payload(), headers=headers)

    assert response.status_code == 202
    body = response.json()
    assert body["state"] == "GENERATING"
    assert body["city"] == "长沙"
    assert body["days"] == 3
    assert body["people"] == 2
    assert body["budget_total"] == 150000
    assert uuid.UUID(body["id"])  # 契约要求 uuid
    assert body["created_at"]  # 由数据库默认值生成，必须回填

    # 库里应该正好一张行程、一条生成记录，且两者状态一致
    with session_factory() as db:
        itineraries = db.scalars(select(Itinerary)).all()
        assert len(itineraries) == 1
        runs = db.scalars(select(PlanRun)).all()
        assert len(runs) == 1
        assert itineraries[0].state is PlanState.GENERATING
        assert runs[0].state is PlanState.GENERATING
        assert runs[0].input_hash == itineraries[0].input_hash


def test_软条件原样存进preferences(
    client: TestClient, auth: tuple[dict[str, str], str], session_factory: sessionmaker[Session]
) -> None:
    headers, _ = auth
    client.post(API, json=_payload(), headers=headers)

    with session_factory() as db:
        itinerary = db.scalars(select(Itinerary)).one()
    assert itinerary.preferences["day_parts"] == ["morning", "evening"]
    assert itinerary.preferences["themes"] == ["老街", "夜宵"]
    assert itinerary.preferences["transport"] == ["metro", "walk"]
    assert itinerary.preferences["pace"] == "relaxed"
    assert itinerary.preferences["include_lodging"] is False


def test_只传必填字段也能过(client: TestClient, auth: tuple[dict[str, str], str]) -> None:
    headers, _ = auth
    response = client.post(
        API,
        json={"city": "长沙", "days": 1, "people": 1, "budget_total": 0},
        headers=headers,
    )
    assert response.status_code == 202
    assert response.json()["state"] == "GENERATING"


def test_缺天数返回422并指明字段(client: TestClient, auth: tuple[dict[str, str], str]) -> None:
    """卡片的验收标准：缺天数返回 422 且指明缺哪个字段。"""
    headers, _ = auth
    payload = _payload()
    del payload["days"]

    response = client.post(API, json=payload, headers=headers)

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"error"}  # 不能是 FastAPI 默认的 {"detail": [...]}
    assert body["error"]["code"] == "VALIDATION_FAILED"
    assert {"field": "days", "reason": "缺少必填字段"} in _error_details(response)
    assert "days" in body["error"]["message"]
    assert body["error"]["request_id"]


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("days", 0, "数值太小"),
        ("days", 8, "数值太大"),
        ("people", 0, "数值太小"),
        ("people", 13, "数值太大"),
        ("budget_total", -1, "数值太小"),
        ("city", "", "内容太短"),
    ],
)
def test_取值越界返回422(
    client: TestClient,
    auth: tuple[dict[str, str], str],
    field: str,
    value: Any,
    reason: str,
) -> None:
    headers, _ = auth
    response = client.post(API, json=_payload(**{field: value}), headers=headers)

    assert response.status_code == 422
    details = _error_details(response)
    assert details[0]["field"] == field
    assert details[0]["reason"] == reason


def test_枚举以外的取值返回422并带允许值(
    client: TestClient, auth: tuple[dict[str, str], str]
) -> None:
    headers, _ = auth
    response = client.post(API, json=_payload(transport=["metro", "火箭"]), headers=headers)

    assert response.status_code == 422
    detail = _error_details(response)[0]
    assert detail["field"] == "transport.1"
    assert detail["reason"] == "不在允许的取值范围内"
    assert set(detail["expected"]) == {"walk", "metro", "bus", "taxi", "bike"}


def test_多余字段被拒绝而不是悄悄忽略(client: TestClient, auth: tuple[dict[str, str], str]) -> None:
    headers, _ = auth
    response = client.post(API, json=_payload(must_see="岳麓山"), headers=headers)

    assert response.status_code == 422
    detail = _error_details(response)[0]
    assert detail["field"] == "must_see"
    assert detail["reason"] == "不支持这个字段"


# ===== 幂等 =====


def test_同一个key重复提交返回同一张行程(
    client: TestClient, auth: tuple[dict[str, str], str], session_factory: sessionmaker[Session]
) -> None:
    headers, _ = auth
    first = client.post(API, json=_payload(), headers=headers)
    second = client.post(API, json=_payload(), headers=headers)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    with session_factory() as db:
        assert len(db.scalars(select(Itinerary)).all()) == 1
        assert len(db.scalars(select(PlanRun)).all()) == 1  # 没有重复烧一次生成


def test_同一个key换了内容返回409(client: TestClient, auth: tuple[dict[str, str], str]) -> None:
    headers, _ = auth
    client.post(API, json=_payload(), headers=headers)

    response = client.post(API, json=_payload(days=5), headers=headers)

    assert response.status_code == 409
    body = response.json()["error"]
    assert body["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert body["details"][0]["field"] == "Idempotency-Key"


def test_不同key各自建一张行程(
    client: TestClient, auth: tuple[dict[str, str], str], session_factory: sessionmaker[Session]
) -> None:
    headers, _ = auth
    first = client.post(API, json=_payload(), headers=headers)
    second = client.post(
        API,
        json=_payload(),
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
    )

    assert first.json()["id"] != second.json()["id"]
    with session_factory() as db:
        assert len(db.scalars(select(Itinerary)).all()) == 2


def test_不同用户的相同的key互不影响(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    key = str(uuid.uuid4())
    ids = []
    for _ in range(2):
        token = create_access_token(user_id=str(uuid.uuid4()), username="u", role="user")
        response = client.post(
            API,
            json=_payload(),
            headers={"Authorization": f"Bearer {token}", "Idempotency-Key": key},
        )
        assert response.status_code == 202
        ids.append(response.json()["id"])

    assert ids[0] != ids[1]
    with session_factory() as db:
        assert len(db.scalars(select(Itinerary)).all()) == 2


def test_缺幂等键返回422(client: TestClient, auth: tuple[dict[str, str], str]) -> None:
    headers, _ = auth
    headers.pop("Idempotency-Key")

    response = client.post(API, json=_payload(), headers=headers)

    assert response.status_code == 422
    detail = _error_details(response)[0]
    assert str(detail["field"]).lower() == "idempotency-key"
    assert detail["reason"] == "缺少必填字段"


# ===== 鉴权 =====


def test_未登录返回401(client: TestClient) -> None:
    response = client.post(API, json=_payload(), headers={"Idempotency-Key": str(uuid.uuid4())})

    assert response.status_code == 401
    body = response.json()["error"]
    assert body["code"] == "UNAUTHORIZED"


def test_令牌里的用户不是uuid时按未登录处理(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    token = create_access_token(user_id="not-a-uuid", username="u", role="user")
    response = client.post(
        API,
        json=_payload(),
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": str(uuid.uuid4())},
    )

    assert response.status_code == 401
    with session_factory() as db:
        assert db.scalars(select(Itinerary)).all() == []
