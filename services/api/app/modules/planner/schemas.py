# 行程规划（多 Agent） · DTO
"""请求/响应模型。字段与 docs/api/openapi.yaml 保持一致，改 yaml 再改这里。"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.planner.models import PlanState


class DayPart(StrEnum):
    """一天里想出门的时段，取值与契约 day_parts 的 enum 一致。"""

    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"


class TransportMode(StrEnum):
    """交通方式。只收契约里列的五种，前端多传一个词就该被挡回去。"""

    WALK = "walk"
    METRO = "metro"
    BUS = "bus"
    TAXI = "taxi"
    BIKE = "bike"


class Pace(StrEnum):
    """节奏：一天塞几个点。模糊的字眼交给 AI，接口只负责把选项限定死。"""

    RELAXED = "relaxed"
    NORMAL = "normal"
    PACKED = "packed"


class StartPoint(BaseModel):
    """出发地。坐标用 WGS84，和契约里的 lat/lon 一致。"""

    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    label: str | None = Field(default=None, max_length=128)


class PlanIn(BaseModel):
    """POST /plans 的请求体（契约 PlanInput）。

    extra="forbid"：拼错字段名要报错，而不是悄悄忽略——用户以为加了"想去岳麓山"，
    实际被丢掉却照样出结果，这比直接报错难查得多。
    """

    model_config = ConfigDict(extra="forbid")

    city: str = Field(min_length=1, max_length=64)
    days: int = Field(ge=1, le=7, description="天数，1-7")
    people: int = Field(ge=1, le=12, description="人数，1-12")
    budget_total: int = Field(ge=0, description="总预算，单位：分")
    include_lodging: bool = False
    day_parts: list[DayPart] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    transport: list[TransportMode] = Field(default_factory=list)
    pace: Pace = Pace.NORMAL
    start_point: StartPoint | None = None

    def preferences(self) -> dict[str, Any]:
        """把"软条件"原样存进 itineraries.preferences。

        这些条件不影响建表，只影响 AI 怎么排行程；存成 JSON 一是不用为每个新
        偏好都写一次迁移，二是生成时可以整块塞给模型。
        """
        return {
            "include_lodging": self.include_lodging,
            "day_parts": [part.value for part in self.day_parts],
            "themes": list(self.themes),
            "transport": [mode.value for mode in self.transport],
            "pace": self.pace.value,
            "start_point": self.start_point.model_dump() if self.start_point else None,
        }


class PlanOut(BaseModel):
    """POST /plans 的 202 响应（契约 Plan）。

    只回执"收了、开始生成了"，不含日程：此时 AI 还没跑，回内容只会是假的。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    state: PlanState
    city: str
    days: int
    people: int
    budget_total: int
    share_token: str | None = None
    error_code: str | None = None
    created_at: datetime
