"""四个 Agent 之间唯一的公共约定：上下文长什么样、每个岗位必须实现什么。

四步接力传递的是同一个 PlanContext，而不是各自拼一份 dataframe ——
好处是挑刺员能同时看到排班结果和候选点位，核对员也能顺着 place_id 找回出处；
测试里更是只拿一个上下文对象就能断言中间产物，不用起数据库。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.modules.planner.models import AgentName


@dataclass
class Candidate:
    """调研员带回来的一条候选点位（对应 catalog 里一条已发布地点）。

    价格是「分」、坐标可能是空 —— catalog 里不少老店没有门牌坐标，
    缺坐标时排班照排，只是挑刺员没法算距离。
    """

    place_id: str
    name: str
    category: str | None = None
    lat: float | None = None
    lon: float | None = None
    price_min: int | None = None
    price_max: int | None = None
    stay_minutes: int = 90
    source_ids: list[str] = field(default_factory=list)


@dataclass
class PlanContext:
    """一次生成的全部中间结果，按流水线顺序逐段填充。"""

    city: str
    days: int
    people: int
    budget_total: int
    preferences: dict[str, object] = field(default_factory=dict)
    # researcher 填 candidates，planner 填 schedule，critic 填 issues，verifier 填 verified。
    candidates: list[Candidate] = field(default_factory=list)
    schedule: list[dict[str, object]] = field(default_factory=list)
    issues: list[dict[str, object]] = field(default_factory=list)
    verified: list[dict[str, object]] = field(default_factory=list)
    # 有岗位用了「降级兜底」（LLM 连不上，退回固定结果）就置 True。
    # 由 orchestrator 抄进每一步记录，最终体现在 RunResult.degraded 上，
    # 让上层能区分「模型真算的」和「兜底给的」。
    llm_degraded: bool = False


@runtime_checkable
class Agent(Protocol):
    """每个岗位都要有名字和一个「吃上下文、还上下文」的 run。"""

    name: AgentName

    def run(self, ctx: PlanContext) -> PlanContext: ...


# 调研员取点位的方式由外部注入：测试给固定清单，线上接 catalog 的 service。
# 这样 PL-03 不依赖 P3 的检索卡就能跑通整条链。
PlaceSource = Callable[[PlanContext], list[Candidate]]
