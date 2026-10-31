# 路线与版本 · DTO
"""请求/响应模型。字段与 docs/api/openapi.yaml 保持一致，改 yaml 再改这里。

RT-01 覆盖 RouteDraftCreate / RouteDraftPatch / RouteDraft / RouteDraftDetail；
RT-02 补上 RouteNodeInput / RouteNodesPut / RouteNodeOut，把 detail.nodes 从恒为 []
换成真实节点。费用汇总（cost）属 RT-04，字段留着、值留空，别让前端此刻拿到假数据。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.routes.models import DraftState, RouteTransport


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


class PlaceOut(BaseModel):
    """契约 Place 的最小投影，当前没有任何地方填得出真实值。

    places 表属 #12 CA-01 / #14 CA-03，至今不存在（catalog 模块还是注释骨架），
    所以本卡没有 name / lat / lon 可填。结构先留在这里：等那张卡落地后由
    repository.load_places(ids) 一次性批量填充——一次一条地查会变成 N+1。
    """

    id: uuid.UUID
    name: str
    lat: float
    lon: float
    district: str | None = None
    summary: str | None = None
    culture_tags: list[str] = Field(default_factory=list)
    status: str | None = None


class RouteNodeInput(BaseModel):
    """PUT /route-drafts/{draft_id}/nodes 请求体里数组的一项（契约 RouteNodeInput）。

    故意没有 position：请求数组的下标就是最终顺序，客户端再传 position 会被
    extra="forbid" 挡成 422。两个来源同时指定顺序时，"下标说 0、position 说 2"
    这种请求谁都解释不了，与其挑一个忽略不如当场拒绝。

    media_asset_ids 只接受、不落库：媒体绑定属 RT-05，现在存下来只会变成一批
    指向不存在资产的悬空 UUID，还得再写一节迁移去清理。
    """

    model_config = ConfigDict(extra="forbid")

    place_id: uuid.UUID
    # 契约 minimum 10 / maximum 480：给 1 分钟等于标记走错了，给一整天等于不是一站。
    stay_minutes: int = Field(ge=10, le=480)
    # 契约里可选，列却是 NOT NULL，缺省走 walk。
    transport: RouteTransport = RouteTransport.WALK
    note: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    media_asset_ids: list[uuid.UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_price_range(self) -> RouteNodeInput:
        """两个价都给了才比大小；只给一个说明是"至少/至多"，不是矛盾。"""
        if (
            self.price_min is not None
            and self.price_max is not None
            and self.price_min > self.price_max
        ):
            raise ValueError("price_min 不能大于 price_max")
        return self


class RouteNodesPut(BaseModel):
    """PUT /route-drafts/{draft_id}/nodes 的请求体：整表替换，nodes 必填。

    [] 是合法值（清空这份草稿的节点），缺 nodes 键才 422。
    """

    model_config = ConfigDict(extra="forbid")

    nodes: list[RouteNodeInput]


class RouteNodeOut(BaseModel):
    """契约 RouteDraftDetail.nodes 的 item。

    place 恒为 None，配合 response_model_exclude_none 让整个键不出现：places 表还
    不存在，编一个 name/lat/lon 出来就是造假数据，前端会把它当成真的显示出去。
    客户端此刻只拿 place_id。等 CA-01/CA-03 落地后由 repository.load_places(ids)
    批量填 place，这里的类型已经准备好了。
    """

    position: int
    place_id: uuid.UUID
    place: PlaceOut | None = None
    stay_minutes: int
    transport: RouteTransport
    note: str | None = None
    price_min: int | None = None
    price_max: int | None = None


class RouteDraftDetailOut(RouteDraftOut):
    """契约 RouteDraftDetail：RouteDraft + nodes + cost。

    nodes 按 position 升序返回（RT-02）；cost 留 None 并配合 response_model_exclude_none，
    让这个键整个不出现——返回 {} 会让前端以为"算过了，是 0 元"。
    """

    nodes: list[RouteNodeOut] = Field(default_factory=list)
    cost: CostSummaryOut | None = None


class RouteDraftPageOut(BaseModel):
    """GET /route-drafts 的响应体：一页草稿 + 不透明游标。"""

    items: list[RouteDraftOut]
    next_cursor: str | None = None
