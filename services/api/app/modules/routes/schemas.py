# 路线与版本 · DTO
"""请求/响应模型。字段与 docs/api/openapi.yaml 保持一致，改 yaml 再改这里。

本卡覆盖 RouteDraftCreate / RouteDraftPatch / RouteDraft / RouteDraftDetail 四个
schema；节点与费用属 RT-02，字段留着、值留空，别让前端此刻就拿到假数据。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.routes.models import DraftState


class RouteDraftCreate(BaseModel):
    """POST /route-drafts 的请求体（契约 RouteDraftCreate）。

    extra="forbid"：拼错字段名要报错，而不是悄悄忽略——用户以为设置了时长，
    实际被丢掉却照样返回 201，这种错比直接报错难查得多。
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=60)
    summary: str | None = Field(default=None, max_length=300)
    theme_tags: list[str] = Field(default_factory=list)
    duration_minutes: int | None = None


class RouteDraftPatch(BaseModel):
    """PATCH /route-drafts/{draft_id} 的请求体（契约 RouteDraftPatch）：同名字段全部可选。

    只改"传了的"字段：service 用 model_dump(exclude_unset=True) 分辨"没传"和
    "显式传 null"，否则一次只想改标题的请求会把 summary 一起清空。
    """

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=60)
    summary: str | None = Field(default=None, max_length=300)
    theme_tags: list[str] | None = None
    duration_minutes: int | None = None


class RouteDraftOut(BaseModel):
    """契约 RouteDraft。title / summary 来自 routes 行，其余来自 route_drafts 行。"""

    id: uuid.UUID
    route_id: uuid.UUID
    title: str
    summary: str | None = None
    state: DraftState
    lock_version: int
    base_version_id: uuid.UUID | None = None
    updated_at: datetime


class CostSummaryOut(BaseModel):
    """契约 CostSummary。RT-02 把节点费用算出来之后才会填它，现在恒为 None。"""

    min_total: int
    max_total: int
    currency: str = "CNY"
    unknown_count: int = 0


class RouteDraftDetailOut(RouteDraftOut):
    """契约 RouteDraftDetail：RouteDraft + nodes + cost。

    nodes 恒为 []（节点属 RT-02）；cost 留 None 并配合 response_model_exclude_none，
    让这个键整个不出现——返回 {} 会让前端以为"算过了，是 0 元"。
    """

    nodes: list[Any] = Field(default_factory=list)
    cost: CostSummaryOut | None = None


class RouteDraftPageOut(BaseModel):
    """GET /route-drafts 的响应体：一页草稿 + 不透明游标。"""

    items: list[RouteDraftOut]
    next_cursor: str | None = None
