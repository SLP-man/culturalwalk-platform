"""挑刺员：只看不修。

发现问题写成 issues（规则名 + 严重级别 + 涉及哪天哪个点），由后续卡决定怎么处置：
重排、追问用户、还是照发但标黄。PL-03 不产生任何分支动作 —— 骨架一旦开始"超预算就砍景点"，
它就变成了半个产品经理，而"砍哪个"恰恰是最需要人（和真模型）判断的部分。
"""

from __future__ import annotations

import math
from typing import Final

from app.modules.planner.agents.base import Candidate, PlanContext
from app.modules.planner.models import AgentName

# 同一段行程两站之间能接受的最长距离（米），按交通方式放宽。
# 数值是拍出来的经验值，注释在此是为了以后有人改它时知道它原本为什么是这些数。
MAX_LEG_METERS: Final[dict[str, int]] = {"walk": 3000, "bike": 6000}
MAX_LEG_METERS_DEFAULT = 12000
# 一天在路上的总时长上限（分钟），超过就是「排得太满」。
MAX_DAY_MINUTES = 600


class CriticAgent:
    """按四条规则检查排班结果，只记录问题不修改排班。"""

    name = AgentName.CRITIC

    def run(self, ctx: PlanContext) -> PlanContext:
        by_place = {candidate.place_id: candidate for candidate in ctx.candidates}
        issues: list[dict[str, object]] = []
        issues += _budget_issue(ctx, by_place)
        issues += _duplicate_issues(ctx)
        issues += _distance_issues(ctx, by_place)
        issues += _day_load_issues(ctx)
        if not ctx.schedule:
            issues.append(
                {
                    "rule": "no_schedule",
                    "severity": "warn",
                    "day_index": None,
                    "place_id": None,
                    "message": "一份行程都没排出来，可能是候选点位为空",
                }
            )
        ctx.issues = issues
        return ctx


def _price_of(candidate: Candidate | None) -> int:
    if candidate is None:
        return 0
    return candidate.price_max or candidate.price_min or 0


def _budget_issue(ctx: PlanContext, by_place: dict[str, Candidate]) -> list[dict[str, object]]:
    """总花费（按最高价估）超过用户预算就报一条。"""
    total = sum(
        _price_of(by_place.get(str(item["place_id"]))) * ctx.people for item in ctx.schedule
    )
    if total <= ctx.budget_total:
        return []
    return [
        {
            "rule": "over_budget",
            "severity": "error",
            "day_index": None,
            "place_id": None,
            "message": f"估算总花费 {total} 分，超出预算 {ctx.budget_total} 分",
        }
    ]


def _duplicate_issues(ctx: PlanContext) -> list[dict[str, object]]:
    """同一个地点排了两次：要么是取数重复，要么是排班回绕了。"""
    seen: dict[str, int] = {}
    issues: list[dict[str, object]] = []
    for item in ctx.schedule:
        place_id = str(item["place_id"])
        seen[place_id] = seen.get(place_id, 0) + 1
        if seen[place_id] == 2:
            issues.append(
                {
                    "rule": "duplicate_place",
                    "severity": "error",
                    "day_index": item["day_index"],
                    "place_id": place_id,
                    "message": f"地点 {item['name']} 被排了不止一次",
                }
            )
    return issues


def _distance_issues(ctx: PlanContext, by_place: dict[str, Candidate]) -> list[dict[str, object]]:
    """同一天相邻两站走不过去就报一条，附上实际距离方便判断要不要打车。"""
    transport = str(ctx.preferences.get("transport", "walk"))
    threshold = MAX_LEG_METERS.get(transport, MAX_LEG_METERS_DEFAULT)
    issues: list[dict[str, object]] = []
    previous: dict[str, object] | None = None
    for item in ctx.schedule:
        if previous is not None and previous["day_index"] == item["day_index"]:
            start = by_place.get(str(previous["place_id"]))
            end = by_place.get(str(item["place_id"]))
            meters = _leg_meters(start, end)
            if meters is not None and meters > threshold:
                issues.append(
                    {
                        "rule": "too_far",
                        "severity": "warn",
                        "day_index": item["day_index"],
                        "place_id": item["place_id"],
                        "message": f"与上一站相距约 {meters} 米，超过 {threshold} 米",
                    }
                )
        previous = item
    return issues


def _day_load_issues(ctx: PlanContext) -> list[dict[str, object]]:
    """按天累加停留时长，排得太满就报一条。"""
    totals: dict[int, int] = {}
    for item in ctx.schedule:
        day = int(str(item["day_index"]))
        totals[day] = totals.get(day, 0) + int(str(item["stay_minutes"]))
    return [
        {
            "rule": "day_overload",
            "severity": "warn",
            "day_index": day,
            "place_id": None,
            "message": f"第 {day} 天安排了 {minutes} 分钟停留，超过 {MAX_DAY_MINUTES} 分钟",
        }
        for day, minutes in sorted(totals.items())
        if minutes > MAX_DAY_MINUTES
    ]


def _leg_meters(start: Candidate | None, end: Candidate | None) -> int | None:
    """两点球面距离（米）；任一点缺坐标就返回 None，而不是当成 0 米。"""
    if start is None or end is None:
        return None
    if start.lat is None or start.lon is None or end.lat is None or end.lon is None:
        return None
    return int(round(_haversine(start.lat, start.lon, end.lat, end.lon)))


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))
