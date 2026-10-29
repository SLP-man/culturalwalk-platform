"""PL-03 多 Agent 编排骨架的正/负用例。

验收（docs/01 示例三）：四个 step 都被记录且顺序固定；某步抛异常后 run 失败、
已完成的 step 保留；假数据下全流程 < 1 秒。这里用固定候选清单当"假 LLM"，
不连数据库也不联网，跑一次几十毫秒。
"""

from __future__ import annotations

import uuid
from time import perf_counter

import pytest

from app.modules.planner.agents import (
    Candidate,
    CriticAgent,
    PlanContext,
    PlannerAgent,
    ResearcherAgent,
    VerifierAgent,
)
from app.modules.planner.models import (
    AgentName,
    AgentStep,
    AgentStepStatus,
    Itinerary,
    PlanRun,
    PlanState,
)
from app.modules.planner.orchestrator import (
    AGENT_FAILED_CODE,
    AGENT_ORDER,
    Orchestrator,
    build_default_agents,
)
from app.modules.planner.service import PlannerService


class FakeSession:
    """只记录 add()，不碰真实数据库。"""

    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)


def make_candidates() -> list[Candidate]:
    return [
        Candidate(
            place_id="p1",
            name="太平老街",
            category="street",
            lat=28.1941,
            lon=112.9711,
            price_max=3000,
            source_ids=["src-1"],
        ),
        Candidate(
            place_id="p2",
            name="火宫殿",
            category="food",
            lat=28.1893,
            lon=112.9742,
            price_max=8000,
            source_ids=["src-2"],
        ),
        Candidate(place_id="p3", name="随便一条巷子", category="street", lat=28.1900, lon=112.9800),
        Candidate(place_id="p4", name="湖南省博物馆", category="museum", lat=28.2100, lon=112.9940),
    ]


def make_context(*, days: int = 2, pace: str = "normal", budget_total: int = 80000) -> PlanContext:
    return PlanContext(
        city="长沙",
        days=days,
        people=2,
        budget_total=budget_total,
        preferences={"pace": pace, "transport": "walk"},
    )


def fake_source(ctx: PlanContext) -> list[Candidate]:
    return make_candidates()


def make_itinerary(state: PlanState = PlanState.GENERATING) -> Itinerary:
    return Itinerary(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        city="长沙",
        days=2,
        people=2,
        budget_total=80000,
        preferences={"pace": "normal"},
        state=state,
    )


def make_run(state: PlanState = PlanState.GENERATING) -> PlanRun:
    return PlanRun(id=uuid.uuid4(), itinerary_id=uuid.uuid4(), state=state, input_hash="a" * 64)


def schedule_item(
    place_id: str, *, order: int, name: str = "某地", day: int = 1
) -> dict[str, object]:
    parts = {1: ("morning", "09:00"), 2: ("afternoon", "14:00"), 3: ("evening", "19:00")}
    part, start = parts[order]
    return {
        "day_index": day,
        "order": order,
        "part": part,
        "start_time": start,
        "place_id": place_id,
        "name": name,
        "stay_minutes": 90,
        "transport": "walk",
    }


# --------------------------------------------------------------------------
# 1. 四步都留痕，顺序固定
# --------------------------------------------------------------------------


def test_four_steps_recorded_in_fixed_order() -> None:
    result = Orchestrator(place_source=fake_source).run(make_context())

    assert result.ok is True
    assert [step.agent for step in result.steps] == list(AGENT_ORDER)
    assert [step.status for step in result.steps] == [AgentStepStatus.DONE] * 4
    # 每一步都给了摘要，且摘要是 64 位十六进制
    assert all(step.output_digest and len(step.output_digest) == 64 for step in result.steps)
    # 上下文被四步依次填满
    assert len(result.context.candidates) == 4
    assert len(result.context.schedule) == 4
    assert len(result.context.verified) == 4
    assert result.failed_agent is None


def test_planner_fills_days_in_order_and_respects_pace() -> None:
    ctx = make_context(days=1, pace="relaxed")
    ctx = ResearcherAgent(fake_source).run(ctx)
    ctx = PlannerAgent().run(ctx)

    # relaxed = 一天 2 个点；第 3 个候选本该进第 2 天，但只排 1 天，直接丢掉
    assert [item["day_index"] for item in ctx.schedule] == [1, 1]
    assert [item["part"] for item in ctx.schedule] == ["morning", "afternoon"]
    assert [item["start_time"] for item in ctx.schedule] == ["09:00", "14:00"]


def test_researcher_dedupes_and_caps_candidates() -> None:
    duplicated = [make_candidates()[0], make_candidates()[0], *make_candidates()[1:]]
    ctx = ResearcherAgent(lambda _: duplicated).run(make_context(days=1))

    assert [candidate.place_id for candidate in ctx.candidates] == ["p1", "p2", "p3", "p4"]
    # 一天最多 4 个候选，days=1 时上限就是 4
    assert len(ctx.candidates) == 4


# --------------------------------------------------------------------------
# 2. 挑刺员只记录问题，不改排班
# --------------------------------------------------------------------------


def test_critic_flags_over_budget_duplicate_and_far_leg() -> None:
    ctx = PlanContext(
        city="长沙",
        days=1,
        people=1,
        budget_total=1000,  # 1000 分 = 10 元，必然超
        preferences={"transport": "walk"},
        candidates=[
            Candidate(place_id="p1", name="A", lat=28.1900, lon=112.9700, price_max=5000),
            Candidate(place_id="p2", name="B", lat=28.3000, lon=112.9700, price_max=5000),
        ],
        schedule=[
            schedule_item("p1", order=1, name="A"),
            schedule_item("p1", order=2, name="A"),
            schedule_item("p2", order=3, name="B"),
        ],
    )
    before = [dict(item) for item in ctx.schedule]

    ctx = CriticAgent().run(ctx)

    rules = [issue["rule"] for issue in ctx.issues]
    assert "over_budget" in rules
    assert "duplicate_place" in rules
    assert "too_far" in rules
    # 只看不修：排班表一个字都不许动
    assert ctx.schedule == before


def test_critic_reports_no_schedule_when_candidates_empty() -> None:
    ctx = CriticAgent().run(make_context())
    assert [issue["rule"] for issue in ctx.issues] == ["no_schedule"]


# --------------------------------------------------------------------------
# 3. 核对员按出处盖章
# --------------------------------------------------------------------------


def test_verifier_marks_items_without_sources() -> None:
    ctx = make_context()
    ctx = ResearcherAgent(fake_source).run(ctx)
    ctx = PlannerAgent().run(ctx)
    ctx = VerifierAgent().run(ctx)

    by_place = {item["place_id"]: item for item in ctx.verified}
    assert by_place["p1"]["confidence"] == "verified"
    assert by_place["p1"]["source_ids"] == ["src-1"]
    # p3 没有 source_ids，必须标待核实
    assert by_place["p3"]["confidence"] == "unverified"
    assert by_place["p3"]["source_ids"] == []


# --------------------------------------------------------------------------
# 4. 失败语义：已完成步骤保留、后续步骤不再跑
# --------------------------------------------------------------------------


class ExplodingCritic(CriticAgent):
    """模拟挑刺员这一站崩掉。"""

    name = AgentName.CRITIC

    def run(self, ctx: PlanContext) -> PlanContext:
        raise RuntimeError("挑刺员炸了")


def test_failure_keeps_finished_steps_and_stops_the_line() -> None:
    agents = [ResearcherAgent(fake_source), PlannerAgent(), ExplodingCritic(), VerifierAgent()]
    result = Orchestrator(agents=agents).run(make_context())

    assert result.ok is False
    assert result.failed_agent is AgentName.CRITIC
    assert result.error_code == AGENT_FAILED_CODE
    assert [step.agent for step in result.steps] == [
        AgentName.RESEARCHER,
        AgentName.PLANNER,
        AgentName.CRITIC,
    ]
    assert [step.status for step in result.steps] == [
        AgentStepStatus.DONE,
        AgentStepStatus.DONE,
        AgentStepStatus.FAILED,
    ]
    # 失败的这一步没有摘要，但留下了错误原文，方便定位
    failed = result.steps[-1]
    assert failed.output_digest is None
    assert "挑刺员炸了" in (failed.error or "")
    # 已完成的产出必须留着：能证明"死在第 3 站，前两站跑完了"
    assert len(result.context.schedule) == 4
    assert result.context.verified == []
    assert result.failed_step is failed


def test_orchestrator_rejects_reordered_agents() -> None:
    with pytest.raises(ValueError, match="顺序"):
        Orchestrator(agents=[PlannerAgent(), ResearcherAgent(fake_source)])


# --------------------------------------------------------------------------
# 5. 确定性 + 速度
# --------------------------------------------------------------------------


def test_same_input_produces_same_digests() -> None:
    first = Orchestrator(place_source=fake_source).run(make_context())
    second = Orchestrator(place_source=fake_source).run(make_context())

    first_digests = [step.output_digest for step in first.steps]
    second_digests = [step.output_digest for step in second.steps]

    assert first_digests == second_digests
    assert first.context.schedule == second.context.schedule


def test_full_run_is_fast() -> None:
    started = perf_counter()
    result = Orchestrator(place_source=fake_source).run(make_context())
    elapsed = perf_counter() - started

    assert result.ok is True
    assert elapsed < 1.0, f"假数据下不该超过 1 秒，实测 {elapsed:.3f}s"


# --------------------------------------------------------------------------
# 6. service 落库：app 层把 steps 写进 agent_steps 并给行程收尾
# --------------------------------------------------------------------------


def test_run_agents_persists_steps_and_marks_ready() -> None:
    db = FakeSession()
    service = PlannerService(db)  # type: ignore[arg-type]
    itinerary = make_itinerary()
    run = make_run()

    result = service.run_agents(itinerary, run, place_source=fake_source)

    steps = [obj for obj in db.added if isinstance(obj, AgentStep)]
    assert result.ok is True
    assert [step.agent for step in steps] == list(AGENT_ORDER)
    assert all(step.status is AgentStepStatus.DONE for step in steps)
    assert all(step.run_id == run.id for step in steps)
    assert all(isinstance(step.duration_ms, int) for step in steps)
    assert itinerary.state is PlanState.READY
    assert run.state is PlanState.READY


def test_run_agents_marks_failed_when_source_raises() -> None:
    def broken_source(ctx: PlanContext) -> list[Candidate]:
        raise RuntimeError("地点库连不上")

    db = FakeSession()
    service = PlannerService(db)  # type: ignore[arg-type]
    itinerary = make_itinerary()
    run = make_run()

    result = service.run_agents(itinerary, run, place_source=broken_source)

    steps = [obj for obj in db.added if isinstance(obj, AgentStep)]
    assert result.ok is False
    assert result.failed_agent is AgentName.RESEARCHER
    # 死在第 1 站：只有一条失败记录，后面的岗位一条都没有
    assert [step.agent for step in steps] == [AgentName.RESEARCHER]
    assert steps[0].status is AgentStepStatus.FAILED
    assert itinerary.state is PlanState.FAILED
    assert run.state is PlanState.FAILED
    assert run.error_code == AGENT_FAILED_CODE


def test_default_agents_follow_agent_order() -> None:
    agents = build_default_agents(fake_source)

    assert [agent.name for agent in agents] == list(AGENT_ORDER)
    assert isinstance(agents[0], ResearcherAgent)
    assert isinstance(agents[1], PlannerAgent)
    assert isinstance(agents[2], CriticAgent)
    assert isinstance(agents[3], VerifierAgent)
