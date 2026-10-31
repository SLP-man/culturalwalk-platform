# 路线与版本 · 业务规则
"""本模块唯一允许写业务判断的地方，router 只做编解码与依赖注入。

拥有数据：routes、route_drafts（RT-01）、route_nodes（RT-02）；
route_versions 属 RT-03。明确不做：审核、发布、AI 生成——只到"草稿能增删改查"为止。

存储归属（docs/02 §2.3）：草稿的 title / summary / theme_tags / duration_minutes 落在
routes 行，route_drafts 只管 state / lock_version / 所有权。所以每次改内容都要顺手
更新两条行，且必须在同一个事务里，否则会出现"标题改了但版本号没涨"的半截状态。
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Final

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import (
    Conflict,
    Forbidden,
    NotFound,
    PreconditionFailed,
    ValidationFailed,
)
from app.modules.routes.models import (
    DraftState,
    Route,
    RouteChannel,
    RouteDraft,
    RouteNode,
    RouteStatus,
)
from app.modules.routes.repository import RoutesRepository
from app.modules.routes.schemas import (
    RouteDraftCreate,
    RouteDraftDetailOut,
    RouteDraftOut,
    RouteDraftPageOut,
    RouteDraftPatch,
    RouteNodeInput,
    RouteNodeOut,
    RouteNodesPut,
)

DEFAULT_LIMIT: Final[int] = 20
MAX_LIMIT: Final[int] = 50

# PATCH 里允许落到 routes 行的内容列。state / lock_version 不在其中：它们只能由
# 状态机与乐观锁自己的入口改，绝不能从请求体采纳，否则客户端能自己"解锁"。
_PATCHABLE_FIELDS: Final[tuple[str, ...]] = ("title", "summary", "theme_tags", "duration_minutes")

# 传 null 等于"清空"的列（允许为空）；其余列传 null 视为"不改"，因为 NOT NULL。
_NULLABLE_FIELDS: Final[frozenset[str]] = frozenset({"summary", "duration_minutes"})

# 文案集中在这里：测试要断言"是锁定态导致的 409"，两处说法不一致就没法查了。
_LOCKED_MESSAGE: Final[str] = "草稿已锁定（当前状态：{state}），解锁前不能编辑或删除"


# ---------- 纯函数 ----------


def canonical_input_hash(payload: BaseModel) -> str:
    """把请求体压成稳定指纹（sha256）。

    sort_keys 让字段顺序不影响结果；ensure_ascii=False + 固定分隔符避免同一个
    对象因为序列化选项不同算出两个指纹，把幂等判成"不同 body"。
    """
    raw = json.dumps(
        payload.model_dump(mode="json"),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def make_slug(title: str) -> str:
    """标题归一化成 slug 前缀，再接 8 位短 uuid 保唯一（docs/02 §2.3 要求 slug 唯一）。

    中文标题归一化后是空串，用 route 兜底：slug 只是可读前缀，不承担语义，
    没必要为它引入拼音库（本卡不许加依赖）。
    """
    ascii_part = re.sub(r"[^a-z0-9]+", "-", title.strip().lower()).strip("-")[:40]
    return f"{ascii_part or 'route'}-{uuid.uuid4().hex[:8]}"


def _as_utc(value: datetime) -> datetime:
    """SQLite 取回来是 naive，统一按 UTC 解释，否则和带时区的游标比不了。"""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def encode_cursor(draft: RouteDraft) -> str:
    """把"这一页的最后一行"压成不透明游标。

    只放排序用到的两列（updated_at、id）：多放一列就等于把内部结构泄露出去，
    前端一旦依赖它，以后换排序键就成了破坏性变更。
    """
    raw = f"{_as_utc(draft.updated_at).isoformat()}|{draft.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """解游标。格式不对就抛 ValueError，由调用方翻成 422 引导用户从头翻页。"""
    padded = cursor + "=" * (-len(cursor) % 4)
    raw = base64.urlsafe_b64decode(padded.encode()).decode()
    ts_text, _, row_id = raw.partition("|")
    if not ts_text or not row_id:
        raise ValueError("游标格式错误")
    return datetime.fromisoformat(ts_text), uuid.UUID(row_id)


def _to_out(draft: RouteDraft, route: Route) -> RouteDraftOut:
    """把 route_drafts 行 + routes 行拼成契约 RouteDraft。"""
    return RouteDraftOut(
        id=draft.id,
        route_id=draft.route_id,
        title=route.title,
        summary=route.summary,
        state=draft.state,
        lock_version=draft.lock_version,
        base_version_id=draft.base_version_id,
        # SQLite 取回来是 naive，统一补 UTC：否则 POST 响应的 updated_at 带 Z、
        # GET 回来的却不带，前端同一个字段要写两套解析。
        updated_at=_as_utc(draft.updated_at),
    )


def _to_node_out(node: RouteNode) -> RouteNodeOut:
    """把 route_nodes 行拼成契约里的节点。

    place 恒传 None：places 表（CA-01/CA-03）还不存在，编 name/lat/lon 出来就是
    造假数据。router 上的 response_model_exclude_none 会让这个键整个不出现，
    客户端此刻只拿 place_id。
    """
    return RouteNodeOut(
        position=node.position,
        place_id=node.place_id,
        place=None,
        stay_minutes=node.stay_minutes,
        transport=node.transport,
        note=node.note,
        price_min=node.price_min,
        price_max=node.price_max,
    )


def _build_node(
    draft_id: uuid.UUID, position: int, item: RouteNodeInput, now: datetime
) -> RouteNode:
    """按"请求数组下标 = position"建一行。

    media_asset_ids 故意不落库（媒体绑定属 RT-05）：现在存下来只会变成一批
    指向不存在资产的悬空 UUID。它仍然在输入模型里，所以客户端多传不会被 422。
    """
    return RouteNode(
        draft_id=draft_id,
        place_id=item.place_id,
        position=position,
        stay_minutes=item.stay_minutes,
        transport=item.transport,
        note=item.note,
        price_min=item.price_min,
        price_max=item.price_max,
        created_at=now,
        updated_at=now,
    )


# ---------- service ----------


class RoutesService:
    def __init__(self, db: Session, repo: RoutesRepository | None = None) -> None:
        self.db = db
        self.repo = repo or RoutesRepository(db)

    # ---------- 写 ----------

    def create_draft(
        self,
        *,
        owner_id: uuid.UUID,
        payload: RouteDraftCreate,
        idempotency_key: str,
    ) -> RouteDraftOut:
        """建草稿。同 owner 同 Idempotency-Key 重复提交返回首次结果，不重复建行。

        做法与 planner 一致：先查，查不到才写，写的时候靠唯一约束兜住并发，
        撞车就回滚再回查赢家——不靠"先查后写"这种有窗口的检查。
        """
        request_hash = canonical_input_hash(payload)
        existing = self.repo.get_by_idempotency_key(
            owner_id=owner_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            return self._replay(existing, request_hash)

        now = datetime.now(UTC)
        route = Route(
            slug=make_slug(payload.title),
            author_id=owner_id,
            channel=RouteChannel.USER,
            title=payload.title,
            summary=payload.summary,
            theme_tags=list(payload.theme_tags),
            duration_minutes=payload.duration_minutes,
            status=RouteStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )
        self.repo.add_route(route)
        draft = RouteDraft(
            route_id=route.id,
            owner_id=owner_id,
            state=DraftState.EDITING,
            lock_version=1,
            base_version_id=None,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            created_at=now,
            updated_at=now,
        )
        try:
            self.repo.add_draft(draft)
        except IntegrityError:
            self.db.rollback()
            winner = self.repo.get_by_idempotency_key(
                owner_id=owner_id, idempotency_key=idempotency_key
            )
            if winner is None:
                raise
            return self._replay(winner, request_hash)
        return self._to_out_loaded(draft)

    def update_draft(
        self,
        *,
        owner_id: uuid.UUID,
        draft_id: uuid.UUID,
        payload: RouteDraftPatch,
        lock_version: int,
    ) -> RouteDraftOut:
        """改草稿内容。If-Match 必须等于当前 lock_version，成功后版本号 +1。"""
        draft, route = self._load_owned(owner_id=owner_id, draft_id=draft_id)
        # 先判状态再判版本：锁定态即使客户端刷新到最新版本号也改不了，
        # 这时候回 412 只会诱使客户端"再取一次版本号重试"，白跑一轮。
        self._ensure_editing(draft)
        if lock_version != draft.lock_version:
            raise PreconditionFailed(
                f"草稿版本已变化（当前 {draft.lock_version}，请求 {lock_version}），请刷新后重试"
            )
        changes = payload.model_dump(exclude_unset=True)
        self._apply_content(route, changes)
        draft.lock_version += 1
        draft.updated_at = datetime.now(UTC)
        route.updated_at = draft.updated_at
        self.db.flush()
        return _to_out(draft, route)

    def replace_nodes(
        self,
        *,
        owner_id: uuid.UUID,
        draft_id: uuid.UUID,
        payload: RouteNodesPut,
        lock_version: int,
    ) -> RouteDraftDetailOut:
        """整表替换草稿的节点顺序：删光旧行，再按请求数组下标重写 position=0..n-1。

        为什么是整表替换而不是逐条 diff：节点没有稳定身份——同一个 place_id 可以
        合法地出现两次（一趟走两遍同一个地点）。没有身份就没法回答"这条是不是原来
        那条"，diff 出来的结果与整表替换完全等价，代码却多一倍，还多一处可能算错
        的地方。

        校验顺序按契约固定为 404 → 403 → 409 → 412：先确认这份草稿存在且是你的，
        再确认它当前能改，最后才比版本号。锁定态下即使版本号是最新的也改不了，
        这时回 412 只会诱使客户端"再取一次版本号重试"，白跑一轮。
        """
        draft, route = self._load_owned(owner_id=owner_id, draft_id=draft_id)
        self._ensure_editing(draft)
        if lock_version != draft.lock_version:
            raise PreconditionFailed(
                f"草稿版本已变化（当前 {draft.lock_version}，请求 {lock_version}），请刷新后重试"
            )
        now = datetime.now(UTC)
        # 先删后写，中间不要 flush 别的东西：整表替换要么整份生效要么一行都不动。
        self.repo.delete_nodes(draft.id)
        self.repo.add_nodes(
            [
                _build_node(draft.id, position, item, now)
                for position, item in enumerate(payload.nodes)
            ]
        )
        draft.lock_version += 1
        draft.updated_at = now
        route.updated_at = now
        self.db.flush()
        return self._to_detail(draft, route)

    def delete_draft(self, *, owner_id: uuid.UUID, draft_id: uuid.UUID) -> None:
        """删草稿。只有 EDITING 且从未发布过的草稿能删（docs/02 §3.1）。"""
        draft, route = self._load_owned(owner_id=owner_id, draft_id=draft_id)
        self._ensure_editing(draft)
        # 先删草稿再删路线：即使外键没开级联，顺序也不会留下悬空的 route_drafts 行。
        self.repo.delete_draft(draft)
        self.repo.delete_route(route)
        self.db.flush()

    # ---------- 读 ----------

    def list_drafts(
        self, *, owner_id: uuid.UUID, cursor: str | None, limit: int
    ) -> RouteDraftPageOut:
        """只返回自己的草稿，按 updated_at DESC, id DESC 走 keyset 分页。"""
        after: tuple[datetime, uuid.UUID] | None = None
        if cursor:
            try:
                after = decode_cursor(cursor)
            except ValueError as exc:
                raise ValidationFailed("游标无效，请从头翻页") from exc
        rows, has_more = self.repo.page_by_owner(owner_id=owner_id, after=after, limit=limit)
        items = [_to_out(draft, route) for draft, route in rows]
        return RouteDraftPageOut(
            items=items,
            next_cursor=encode_cursor(rows[-1][0]) if has_more and rows else None,
        )

    def get_detail(self, *, owner_id: uuid.UUID, draft_id: uuid.UUID) -> RouteDraftDetailOut:
        """详情。nodes 按 position 升序真实返回（RT-02），cost 属 RT-04 仍留空不下发。"""
        draft, route = self._load_owned(owner_id=owner_id, draft_id=draft_id)
        return self._to_detail(draft, route)

    # ---------- 内部 ----------

    def _load_owned(self, *, owner_id: uuid.UUID, draft_id: uuid.UUID) -> tuple[RouteDraft, Route]:
        """取草稿并顺手做存在性与所有权判断。

        不存在与不属于当前用户分两个错误码回：草稿是私有资源，但按契约要能区分
        "这份已经被删了"（404，可以重建）和"这不是你的"（403，别再试）。
        """
        draft = self.repo.get_draft(draft_id)
        if draft is None:
            raise NotFound("草稿不存在")
        if draft.owner_id != owner_id:
            raise Forbidden("只有作者本人可以查看或修改这份草稿")
        route = self.repo.get_route(draft.route_id)
        if route is None:
            raise NotFound("草稿不存在")
        return draft, route

    def _ensure_editing(self, draft: RouteDraft) -> None:
        if draft.state is not DraftState.EDITING:
            raise Conflict(_LOCKED_MESSAGE.format(state=DraftState(draft.state).value))

    def _apply_content(self, route: Route, changes: dict[str, Any]) -> None:
        """把 PATCH 里的内容字段写到 routes 行。

        显式传 null 时：可空列（summary / duration_minutes）视为清空；
        非空列（title / theme_tags）视为"不改"——写 null 会撞 NOT NULL，
        而客户端把整个对象序列化过来时本来就会带一堆 null。
        """
        for field in _PATCHABLE_FIELDS:
            if field not in changes:
                continue
            value = changes[field]
            if value is None and field not in _NULLABLE_FIELDS:
                continue
            setattr(route, field, list(value) if field == "theme_tags" else value)

    def _to_detail(self, draft: RouteDraft, route: Route) -> RouteDraftDetailOut:
        """GET 详情与 PUT 节点共用：一条查询取回全部节点，按 position 升序。"""
        base = _to_out(draft, route)
        nodes = [_to_node_out(node) for node in self.repo.list_nodes(draft.id)]
        return RouteDraftDetailOut(**base.model_dump(), nodes=nodes, cost=None)

    def _to_out_loaded(self, draft: RouteDraft) -> RouteDraftOut:
        """刚建好的草稿：routes 行在同一个事务里，直接按 id 取回来拼响应。"""
        route = self.repo.get_route(draft.route_id)
        if route is None:
            raise NotFound("草稿不存在")
        return _to_out(draft, route)

    def _replay(self, draft: RouteDraft, request_hash: str) -> RouteDraftOut:
        """同 key 重放：body 一样就回首次结果，不一样就 409 让客户端换 key。"""
        if draft.request_hash != request_hash:
            raise Conflict(
                "这个 Idempotency-Key 已经用于另一个请求体，请换一个 key",
                code="IDEMPOTENCY_KEY_REUSED",
                details=[
                    {"field": "Idempotency-Key", "reason": "already_used_with_different_body"}
                ],
            )
        return self._to_out_loaded(draft)
