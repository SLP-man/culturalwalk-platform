"""核对员：给每一条安排盖「有出处 / 待核实」的章。

判断标准只有一条：这条点位在数据源里有没有引用（source_ids 非空）。
没有引用的一律标 unverified —— 宁可标黄让人复核，也不能把编出来的地点说成查证过的。
这条对应文化合格线的第一关「有据可查」，也是以后内容审核（MD 卡）的输入。
"""

from __future__ import annotations

from app.modules.planner.agents.base import PlanContext
from app.modules.planner.models import AgentName

VERIFIED = "verified"
UNVERIFIED = "unverified"


class VerifierAgent:
    """给排班结果逐条标注可信度与出处。"""

    name = AgentName.VERIFIER

    def run(self, ctx: PlanContext) -> PlanContext:
        sources = {candidate.place_id: list(candidate.source_ids) for candidate in ctx.candidates}
        ctx.verified = [
            {
                **item,
                "confidence": VERIFIED if sources.get(str(item["place_id"])) else UNVERIFIED,
                "source_ids": sources.get(str(item["place_id"]), []),
            }
            for item in ctx.schedule
        ]
        return ctx
