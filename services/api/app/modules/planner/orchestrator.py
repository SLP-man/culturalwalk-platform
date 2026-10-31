"""把四个岗位按固定顺序串起来，并给每一步打上耗时与输出摘要。

两个刻意的设计：

1. 顺序是常量，不接受调用方重排。核对必须在排班之后才有意义，
   允许自由排序等于允许产出「核对完了但还没排班」这种没有意义的记录。
2. 任何一步抛异常就停下，**已完成的步骤照旧保留**，失败的那一步也落一条记录。
   线上排查时最怕只知道「失败了」，不知道死在哪一站、前面已经跑到哪里。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Final

from app.modules.planner.agents import (
    Agent,
    CriticAgent,
    PlaceSource,
    PlanContext,
    PlannerAgent,
    ResearcherAgent,
    VerifierAgent,
)
from app.modules.planner.models import AgentName, AgentStepStatus, Itinerary

# 流水线的唯一顺序：先把点位捞回来，才谈得上排班；排完才谈得上挑刺；挑完才核对。
AGENT_ORDER: Final[tuple[AgentName, ...]] = (
    AgentName.RESEARCHER,
    AgentName.PLANNER,
    AgentName.CRITIC,
    AgentName.VERIFIER,
)
# 落库的 error_code：PL-05 接异步任务后，前端按这个值决定要不要给「重试」按钮。
AGENT_FAILED_CODE = "AGENT_FAILED"

ERROR_PREVIEW_CHARS = 200


@dataclass(frozen=True)
class StepRecord:
    """一步的执行结果，字段与 agent_steps 表一一对应，方便 service 直接落库。"""

    agent: AgentName
    status: AgentStepStatus
    duration_ms: int
    output_digest: str | None = None
    error: str | None = None
    # 这一步是不是靠兜底完成的（LLM 不可用 → fake 的固定结果）。
    degraded: bool = False


@dataclass
class RunResult:
    """一次流水线运行的结果：跑没跑通、跑到哪、每一步怎么样。"""

    ok: bool
    context: PlanContext
    steps: list[StepRecord]
    failed_agent: AgentName | None = None
    error_code: str | None = None

    @property
    def failed_step(self) -> StepRecord | None:
        return next((step for step in self.steps if step.status is AgentStepStatus.FAILED), None)

    @property
    def degraded(self) -> bool:
        """整条流水线里有没有任何一步用了兜底结果。"""
        return any(step.degraded for step in self.steps)


class Orchestrator:
    """顺序执行四个岗位，记录每步的状态与耗时。"""

    def __init__(
        self,
        *,
        place_source: PlaceSource | None = None,
        agents: Sequence[Agent] | None = None,
    ) -> None:
        if agents is None:
            self.agents: list[Agent] = build_default_agents(place_source)
        else:
            self.agents = list(agents)
        self._assert_order()

    def _assert_order(self) -> None:
        names = [agent.name for agent in self.agents]
        if names != list(AGENT_ORDER):
            expected = [name.value for name in AGENT_ORDER]
            got = [name.value for name in names]
            raise ValueError(f"Agent 顺序必须严格是 {expected}，收到 {got}")

    def run(self, ctx: PlanContext) -> RunResult:
        steps: list[StepRecord] = []
        for agent in self.agents:
            started = perf_counter()
            try:
                ctx = agent.run(ctx)
            except Exception as exc:  # noqa: BLE001 - 任何岗位都可能炸，统一收口成一条失败记录
                steps.append(
                    StepRecord(
                        agent=agent.name,
                        status=AgentStepStatus.FAILED,
                        duration_ms=_elapsed_ms(started),
                        error=f"{type(exc).__name__}: {exc}"[:ERROR_PREVIEW_CHARS],
                        degraded=ctx.llm_degraded,
                    )
                )
                return RunResult(
                    ok=False,
                    context=ctx,
                    steps=steps,
                    failed_agent=agent.name,
                    error_code=AGENT_FAILED_CODE,
                )
            steps.append(
                StepRecord(
                    agent=agent.name,
                    status=AgentStepStatus.DONE,
                    duration_ms=_elapsed_ms(started),
                    output_digest=context_digest(ctx),
                    degraded=ctx.llm_degraded,
                )
            )
        return RunResult(ok=True, context=ctx, steps=steps)


def build_default_agents(place_source: PlaceSource | None = None) -> list[Agent]:
    """按 AGENT_ORDER 造一套默认的四个岗位。"""
    return [ResearcherAgent(place_source), PlannerAgent(), CriticAgent(), VerifierAgent()]


def context_from_itinerary(itinerary: Itinerary) -> PlanContext:
    """把库里的行程条件翻译成流水线上下文。

    只搬条件，不搬历史结果 —— 每次生成都是一次全新的运行，
    拿旧结果喂给模型会把上一轮的错再放大一遍。
    """
    preferences = dict(itinerary.preferences or {})
    return PlanContext(
        city=itinerary.city,
        days=itinerary.days,
        people=itinerary.people,
        budget_total=itinerary.budget_total,
        preferences=preferences,
    )


def context_digest(ctx: PlanContext) -> str:
    """整份上下文的指纹。

    只存摘要不存全文：一块模型输出动辄几十 KB，落库既脏又贵；
    要复现时按摘要去日志里捞，也够用了。
    """
    payload = json.dumps(asdict(ctx), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _elapsed_ms(started: float) -> int:
    return int(round((perf_counter() - started) * 1000))
