"""PL-01 行程模型与状态机的正/负用例。

不连数据库：状态机是纯函数，用 transient 对象就能完整覆盖；
真正落库的用例要等 Postgres service 起来（CI 里由 pytest 的 DB 夹具负责）。
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Enum as SAEnum
from sqlalchemy import UniqueConstraint

from app.core.errors import Conflict
from app.modules.planner.models import (
    AgentName,
    AgentStep,
    AgentStepStatus,
    Itinerary,
    ItineraryDay,
    ItineraryItem,
    PlanRun,
    PlanState,
)
from app.modules.planner.service import (
    PlannerService,
    allowed_targets,
    apply_transition,
    ensure_transition,
)


class FakeSession:
    """只记录 add()，不碰真实数据库。"""

    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)


def make_itinerary(state: PlanState = PlanState.DRAFT) -> Itinerary:
    return Itinerary(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        city="长沙",
        days=2,
        people=2,
        budget_total=80000,
        state=state,
    )


def make_run(state: PlanState) -> PlanRun:
    return PlanRun(itinerary_id=uuid.uuid4(), state=state, input_hash="a" * 64)


# --------------------------------------------------------------------------
# 状态机：只有文档里那三条边能走
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("source", "target", "action"),
    [
        (PlanState.DRAFT, PlanState.GENERATING, "enqueue"),
        (PlanState.GENERATING, PlanState.READY, "succeed"),
        (PlanState.GENERATING, PlanState.FAILED, "fail"),
    ],
)
def test_legal_transitions(source: PlanState, target: PlanState, action: str) -> None:
    assert ensure_transition(source, target) == action


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (PlanState.DRAFT, PlanState.READY),  # 没生成就想 ready
        (PlanState.DRAFT, PlanState.FAILED),  # 没开始就失败
        (PlanState.GENERATING, PlanState.DRAFT),  # 生成中退回草稿
        (PlanState.READY, PlanState.GENERATING),  # ready 之后想重跑
        (PlanState.FAILED, PlanState.DRAFT),  # 失败后原地复活
        (PlanState.FAILED, PlanState.READY),
        (PlanState.DRAFT, PlanState.DRAFT),  # 原地打转
        (PlanState.READY, PlanState.READY),
    ],
)
def test_illegal_transitions_raise_conflict(source: PlanState, target: PlanState) -> None:
    with pytest.raises(Conflict) as excinfo:
        ensure_transition(source, target)
    err = excinfo.value
    assert err.code == "CONFLICT"
    assert err.http_status == 409
    # 详情里要能看出是哪一步被拦的、还能去哪，前端据此提示用户
    detail = err.details[0]
    assert detail["from"] == str(source)
    assert detail["to"] == str(target)
    assert detail["allowed"] == [str(item) for item in allowed_targets(source)]


def test_allowed_targets_matches_state_machine() -> None:
    assert allowed_targets(PlanState.DRAFT) == [PlanState.GENERATING]
    assert set(allowed_targets(PlanState.GENERATING)) == {PlanState.READY, PlanState.FAILED}
    assert allowed_targets(PlanState.READY) == []
    assert allowed_targets(PlanState.FAILED) == []


def test_apply_transition_writes_state_and_error_code() -> None:
    itinerary = make_itinerary()
    assert apply_transition(itinerary, PlanState.GENERATING) == "enqueue"
    assert itinerary.state is PlanState.GENERATING
    assert itinerary.error_code is None

    # 失败时原因要跟着写；成功时要清掉上一次留下的原因
    apply_transition(itinerary, PlanState.FAILED, error_code="LLM_TIMEOUT")
    assert itinerary.state is PlanState.FAILED
    assert itinerary.error_code == "LLM_TIMEOUT"

    run = make_run(PlanState.GENERATING)
    apply_transition(run, PlanState.READY, error_code=None)
    assert run.state is PlanState.READY
    assert run.error_code is None


# --------------------------------------------------------------------------
# service：生成一次成功 / 失败 / 重复提交
# --------------------------------------------------------------------------
def test_start_run_moves_itinerary_to_generating() -> None:
    db = FakeSession()
    itinerary = make_itinerary()
    run = PlannerService(db).start_run(itinerary, input_hash="b" * 64, model="m1")  # type: ignore[arg-type]

    assert itinerary.state is PlanState.GENERATING
    assert run.state is PlanState.GENERATING
    assert run.input_hash == "b" * 64
    assert run.model == "m1"
    assert db.added == [run], "本次生成记录必须入会话，否则失败原因留不下来"


def test_start_run_twice_is_rejected() -> None:
    db = FakeSession()
    service = PlannerService(db)  # type: ignore[arg-type]
    itinerary = make_itinerary()

    service.start_run(itinerary, input_hash="c" * 64)
    with pytest.raises(Conflict):
        service.start_run(itinerary, input_hash="c" * 64)


def test_finish_ready_updates_both_entities() -> None:
    db = FakeSession()
    service = PlannerService(db)  # type: ignore[arg-type]
    itinerary = make_itinerary()
    run = service.start_run(itinerary, input_hash="d" * 64)

    service.finish_ready(itinerary, run)
    assert itinerary.state is PlanState.READY
    assert run.state is PlanState.READY


def test_finish_failed_keeps_error_code() -> None:
    db = FakeSession()
    service = PlannerService(db)  # type: ignore[arg-type]
    itinerary = make_itinerary()
    run = service.start_run(itinerary, input_hash="e" * 64)

    service.finish_failed(itinerary, run, error_code="AGENT_CRASHED")
    assert itinerary.state is PlanState.FAILED
    assert itinerary.error_code == "AGENT_CRASHED"
    assert run.state is PlanState.FAILED
    assert run.error_code == "AGENT_CRASHED"


# --------------------------------------------------------------------------
# 表结构：字段、约束、以及"跨模块不建外键"这条硬规矩
# --------------------------------------------------------------------------
def test_tables_and_columns_are_declared() -> None:
    assert set(Itinerary.metadata.tables) >= {
        "itineraries",
        "itinerary_days",
        "itinerary_items",
        "plan_runs",
        "agent_steps",
    }
    itinerary_cols = set(Itinerary.__table__.c.keys())
    assert {"user_id", "city", "days", "people", "budget_total", "state"} <= itinerary_cols
    item_cols = set(ItineraryItem.__table__.c.keys())
    assert {"order", "place_id", "source_ids", "confidence"} <= item_cols


def test_new_itinerary_defaults_to_draft() -> None:
    assert Itinerary.__table__.c.state.default.arg is PlanState.DRAFT


def test_enum_stored_as_value_not_name() -> None:
    col_type = Itinerary.__table__.c.state.type
    assert isinstance(col_type, SAEnum)
    assert col_type.native_enum is False, "要存 VARCHAR，不然加状态就得写迁移"
    assert col_type.enums == ["DRAFT", "GENERATING", "READY", "FAILED"]
    assert AgentStep.__table__.c.agent.type.enums == [
        AgentName.RESEARCHER.value,
        AgentName.PLANNER.value,
        AgentName.CRITIC.value,
        AgentName.VERIFIER.value,
    ]
    assert AgentStep.__table__.c.status.type.enums == [item.value for item in AgentStepStatus]


def test_no_cross_module_foreign_keys() -> None:
    # users 表属于 identity 模块、目前还不存在；categories/places 属于 catalog 模块。
    # 约定：跨模块只存 ID，不建物理外键。
    assert not Itinerary.__table__.c.user_id.foreign_keys
    assert not ItineraryItem.__table__.c.place_id.foreign_keys
    # 模块内部的父子关系才建外键
    assert {fk.target_fullname for fk in ItineraryDay.__table__.c.itinerary_id.foreign_keys} == {
        "itineraries.id"
    }


def test_share_token_is_unique() -> None:
    uniques = {
        tuple(sorted(constraint.columns.keys()))
        for constraint in Itinerary.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("share_token",) in uniques
