"""调研员：把地点库里的候选搬进上下文，仅此而已。

PL-03 只要求「流程跑得通」，所以这里刻意不做排序打分 —— 一旦开始按热度排序，
就得先定义"热度"是什么，那是 catalog 侧的活（CA 卡）。等真有检索服务，
换掉注入的 place_source 即可，四个岗位的接口都不用动。
"""

from __future__ import annotations

from app.modules.planner.agents.base import Candidate, PlaceSource, PlanContext
from app.modules.planner.models import AgentName

# 一天最多带回来 4 个候选：再多也排不进一天，只会让挑刺员的报告变长。
MAX_CANDIDATES_PER_DAY = 4


class ResearcherAgent:
    """取候选点位并去重。"""

    name = AgentName.RESEARCHER

    def __init__(self, place_source: PlaceSource | None = None) -> None:
        self._place_source = place_source or _empty_source

    def run(self, ctx: PlanContext) -> PlanContext:
        raw = self._place_source(ctx)
        ctx.candidates = _dedupe(raw, limit=ctx.days * MAX_CANDIDATES_PER_DAY)
        return ctx


def _empty_source(ctx: PlanContext) -> list[Candidate]:
    """没接地点库时返回空清单而不是报错。

    调用方（service）在 PL-05 里接上 catalog；这条路径留空也能让整条流水线
    保持"能跑完但没内容"，比抛异常更利于灰度发布时先通管道。
    """
    return []


def _dedupe(candidates: list[Candidate], *, limit: int) -> list[Candidate]:
    """按到达顺序保序去重：同一个地点被检索出两次只排一次。"""
    seen: set[str] = set()
    picked: list[Candidate] = []
    for candidate in candidates:
        if candidate.place_id in seen:
            continue
        seen.add(candidate.place_id)
        picked.append(candidate)
        if len(picked) >= limit:
            break
    return picked
