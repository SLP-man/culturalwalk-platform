"""排班员：把候选点位排进「第几天 / 哪个时段 / 停留多久 / 怎么去」。

确定性贪心：按候选顺序填时段，填满当天就换下一天，超出天数的多余候选直接丢掉。
不做地理聚类或时长博弈 —— 那是挑刺员反馈之后的重排，属于后续卡，骨架里先保持可预测，
否则同一份输入跑两次排出两张不同的表，测试就没法钉住行为了。
"""

from __future__ import annotations

from typing import Final

from app.modules.planner.agents.base import PlanContext
from app.modules.planner.models import AgentName

# 一天能塞几个点，取决于用户选的节奏。数值来自 docs/02 §2.5 的默认建议。
PER_DAY_BY_PACE: Final[dict[str, int]] = {"relaxed": 2, "normal": 3, "packed": 4}
DEFAULT_DAY_PARTS: Final[tuple[str, ...]] = ("morning", "afternoon", "evening")
SLOT_START: Final[dict[str, str]] = {
    "morning": "09:00",
    "afternoon": "14:00",
    "evening": "19:00",
}


class PlannerAgent:
    """按时段表排出逐日的行程条目。"""

    name = AgentName.PLANNER

    def run(self, ctx: PlanContext) -> PlanContext:
        parts = _day_parts(ctx.preferences.get("day_parts"))
        pace_cap = PER_DAY_BY_PACE.get(str(ctx.preferences.get("pace", "normal")), 3)
        per_day = min(pace_cap, len(parts))
        transport = str(ctx.preferences.get("transport", "walk"))

        schedule: list[dict[str, object]] = []
        for index, candidate in enumerate(ctx.candidates):
            day_index = index // per_day + 1
            if day_index > ctx.days:
                break
            order = index % per_day + 1
            part = parts[order - 1]
            schedule.append(
                {
                    "day_index": day_index,
                    "order": order,
                    "part": part,
                    "start_time": SLOT_START[part],
                    "place_id": candidate.place_id,
                    "name": candidate.name,
                    "stay_minutes": candidate.stay_minutes,
                    "transport": transport,
                }
            )
        ctx.schedule = schedule
        return ctx


def _day_parts(raw: object) -> tuple[str, ...]:
    """用户想把一天出门的时段限定到哪几段。

    传了非法值时退回默认三段而不是 422：到这里请求早就校验过了，
    再报错只会让一次生成白等半天。空列表同样按默认处理（用户没表达意愿）。
    """
    if isinstance(raw, list):
        wanted = [str(part) for part in raw if str(part) in SLOT_START]
        if wanted:
            return tuple(sorted(wanted, key=DEFAULT_DAY_PARTS.index))
    return DEFAULT_DAY_PARTS
