# PL-05：异步生成（任务表 + worker 轮询）的测试
"""钉住三件事：

1. 提交规划只排队、不干活——请求必须立刻返回，重活交给 worker；
2. worker 领活、跑完、收尾（DONE / 重试 / 判死）三种结局都正确；
3. 详情接口能把"跑到第几步"如实说出来，别人看不到我的行程。

数据库用 SQLite 内存库：本机不保证有 Postgres，而这里要验的是任务状态机与接口行为，
换数据库不该改变这些结论。`FOR UPDATE SKIP LOCKED` 是 PG 行锁，SQLite 方言会忽略，
所以"两个 worker 不抢同一条"由 PG 上的行为保证，这里验的是领活逻辑本身。
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.core.deps import create_access_token
from app.main import create_app
from app.modules.planner.models import (
    AgentName,
    AgentStep,
    Itinerary,
    JobState,
    PlanJob,
    PlanState,
)
from app.modules.planner.service import JOB_BACKOFF_SECONDS, MAX_JOB_ATTEMPTS
from app.modules.planner.worker import claim_and_run

API = "/api/v1/plans"
AGENT_FLOW = ["researcher", "planner", "critic", "verifier"]


@pytest.fixture()
def session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _headers(user_id: str | None = None, key: str | None = None) -> dict[str, str]:
    token = create_access_token(
        user_id=user_id or str(uuid.uuid4()), username="feral0702", role="user"
    )
    return {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": key or str(uuid.uuid4()),
    }


def _auth_headers(user_id: str) -> dict[str, str]:
    """只带身份、不带幂等键：查详情不需要幂等。"""
    token = create_access_token(user_id=user_id, username="feral0702", role="user")
    return {"Authorization": f"Bearer {token}"}


def _payload(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "city": "长沙",
        "days": 2,
        "people": 2,
        "budget_total": 80000,
        "pace": "relaxed",
    }
    data.update(overrides)
    return data


def _submit(client: TestClient, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    response = client.post(API, json=_payload(**overrides), headers=headers)
    assert response.status_code == 202, response.text
    return response.json()


def _only_job(db: Session) -> PlanJob:
    db.expire_all()
    return db.scalars(select(PlanJob)).one()


def _naive(value: datetime) -> datetime:
    """SQLite 拿回来的时间不带时区，比较前统一去掉，免得 naive/aware 直接 TypeError。"""
    return value.replace(tzinfo=None) if value.tzinfo is not None else value


class _BoomPlanner:
    """顶替 PlannerAgent：一进 run 就抛，用来验失败与重试路径。"""

    name = AgentName.PLANNER

    def run(self, ctx: Any) -> Any:  # noqa: ARG002 - 签名要与 Agent 协议一致
        raise RuntimeError("模型服务挂了")


# ----- 提交：只排队，不干活 ------------------------------------------------


def test_submit_returns_run_id_and_queues_a_job(client: TestClient, db: Session) -> None:
    body = _submit(client, _headers())

    assert body["state"] == PlanState.GENERATING.value
    assert body["run_id"], "202 必须带本次生成编号，前端靠它判断等的是不是同一份"

    job = _only_job(db)
    assert job.state is JobState.PENDING
    assert job.attempts == 0
    assert str(job.run_id) == body["run_id"]
    assert str(job.itinerary_id) == body["id"]


def test_submit_does_not_run_agents_in_the_request(client: TestClient, db: Session) -> None:
    body = _submit(client, _headers())

    itinerary = db.get(Itinerary, uuid.UUID(body["id"]))
    assert itinerary is not None
    # 请求线程里一步都没跑：跑一次要十几秒，挂在这里用户会以为页面卡死。
    assert itinerary.state is PlanState.GENERATING
    assert db.scalar(select(func.count()).select_from(AgentStep)) == 0


def test_submit_replay_returns_the_same_run(client: TestClient, db: Session) -> None:
    headers = _headers()
    first = _submit(client, headers)
    second = _submit(client, headers)

    assert second["id"] == first["id"]
    assert second["run_id"] == first["run_id"]
    assert db.scalar(select(func.count()).select_from(PlanJob)) == 1


# ----- worker：领活、跑完、收尾 --------------------------------------------


def test_worker_runs_the_queued_job_to_ready(client: TestClient, db: Session) -> None:
    body = _submit(client, _headers())

    assert claim_and_run(db) is True

    job = _only_job(db)
    itinerary = db.get(Itinerary, uuid.UUID(body["id"]))
    assert job.state is JobState.DONE
    assert job.attempts == 1
    assert job.claimed_by, "要记下是谁领的活，否则排障时不知道任务卡在哪个进程"
    assert job.lease_until is None
    assert itinerary is not None and itinerary.state is PlanState.READY

    db.expire_all()
    steps = list(db.scalars(select(AgentStep).order_by(AgentStep.step_index)))
    assert [step.agent.value for step in steps] == AGENT_FLOW
    assert all(step.status.value == "done" for step in steps)


def test_worker_returns_false_when_the_queue_is_empty(db: Session) -> None:
    assert claim_and_run(db) is False


def test_failed_job_is_requeued_with_backoff(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.modules.planner.orchestrator.PlannerAgent", _BoomPlanner)
    body = _submit(client, _headers())

    assert claim_and_run(db) is True

    job = _only_job(db)
    itinerary = db.get(Itinerary, uuid.UUID(body["id"]))
    assert job.state is JobState.PENDING, "没到次数上限就该回到队列，交给下一个 worker"
    assert job.attempts == 1
    assert job.lease_until is None
    assert "模型服务挂了" in (job.last_error or "")
    earliest = datetime.now(UTC) + timedelta(seconds=JOB_BACKOFF_SECONDS[0] - 1)
    assert _naive(job.available_at) >= _naive(earliest)
    # 行程先判失败：前端能立刻看到原因，而不是一直转圈等重试。
    assert itinerary is not None and itinerary.state is PlanState.FAILED


def test_job_is_given_up_after_max_attempts(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.modules.planner.orchestrator.PlannerAgent", _BoomPlanner)
    _submit(client, _headers())

    now = datetime.now(UTC)
    for attempt in range(1, MAX_JOB_ATTEMPTS + 1):
        assert claim_and_run(db, now=now) is True
        job = _only_job(db)
        assert job.attempts == attempt
        if attempt < MAX_JOB_ATTEMPTS:
            assert job.state is JobState.PENDING
            # 退避到未来：这一次立刻再领，应该是领不到的
            assert claim_and_run(db, now=now) is False
            now = job.available_at + timedelta(seconds=1)

    job = _only_job(db)
    assert job.state is JobState.FAILED
    assert claim_and_run(db, now=datetime.now(UTC) + timedelta(days=1)) is False


def test_expired_lease_is_reclaimed(client: TestClient, db: Session) -> None:
    body = _submit(client, _headers())
    job = _only_job(db)
    # 模拟「worker 领了活然后崩了」：状态停在 RUNNING，租约已经过期
    job.state = JobState.RUNNING
    job.attempts = 1
    job.claimed_by = "dead-worker:1"
    job.lease_until = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()

    assert claim_and_run(db) is True

    job = _only_job(db)
    itinerary = db.get(Itinerary, uuid.UUID(body["id"]))
    assert job.state is JobState.DONE
    assert job.attempts == 2
    assert itinerary is not None and itinerary.state is PlanState.READY


def test_retry_replaces_half_finished_steps(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _submit(client, _headers())
    monkeypatch.setattr("app.modules.planner.orchestrator.PlannerAgent", _BoomPlanner)
    assert claim_and_run(db) is True
    # 第一次只留了两条：researcher done、planner failed
    assert db.scalar(select(func.count()).select_from(AgentStep)) == 2

    monkeypatch.undo()
    job = _only_job(db)
    assert claim_and_run(db, now=job.available_at + timedelta(seconds=1)) is True

    db.expire_all()
    steps = list(db.scalars(select(AgentStep).order_by(AgentStep.step_index)))
    assert [step.agent.value for step in steps] == AGENT_FLOW, "重试要把上一次的半截留痕清掉"


# ----- 详情接口：前端轮询的就是它 ------------------------------------------


def test_detail_shows_generating_before_the_worker_runs(client: TestClient, db: Session) -> None:
    user_id = str(uuid.uuid4())
    body = _submit(client, _headers(user_id))

    response = client.get(f"{API}/{body['id']}", headers=_auth_headers(user_id))

    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["state"] == PlanState.GENERATING.value
    assert detail["steps"] == []
    assert detail["run_id"] == body["run_id"]


def test_detail_shows_ready_with_steps_after_the_worker_runs(
    client: TestClient, db: Session
) -> None:
    user_id = str(uuid.uuid4())
    headers = _headers(user_id)
    body = _submit(client, headers)
    assert claim_and_run(db) is True

    detail = client.get(f"{API}/{body['id']}", headers=_auth_headers(user_id)).json()

    assert detail["state"] == PlanState.READY.value
    assert [step["agent"] for step in detail["steps"]] == AGENT_FLOW
    assert all(isinstance(step["duration_ms"], int) for step in detail["steps"])


def test_detail_of_someone_elses_plan_is_forbidden(client: TestClient) -> None:
    body = _submit(client, _headers())

    response = client.get(f"{API}/{body['id']}", headers=_auth_headers(str(uuid.uuid4())))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_detail_of_unknown_plan_is_404(client: TestClient) -> None:
    response = client.get(f"{API}/{uuid.uuid4()}", headers=_headers())

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_detail_requires_login(client: TestClient) -> None:
    assert client.get(f"{API}/{uuid.uuid4()}").status_code == 401
