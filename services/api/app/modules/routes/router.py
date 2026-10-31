# 路线与版本 · HTTP 入口
"""只做编解码与依赖注入。业务规则一律写进 service.py。

契约以 docs/api/openapi.yaml 为准，本文件只负责把端点挂上去。
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Header, Query, Response

from app.core.db import DbDep
from app.core.deps import CurrentUser, CurrentUserDep
from app.core.errors import Unauthorized
from app.modules.routes.schemas import (
    RouteDraftCreate,
    RouteDraftDetailOut,
    RouteDraftOut,
    RouteDraftPageOut,
    RouteDraftPatch,
)
from app.modules.routes.service import DEFAULT_LIMIT, MAX_LIMIT, RoutesService

router = APIRouter(prefix="/route-drafts", tags=["drafts"])


# 令牌里的 user.id 是字符串，进库要 UUID；转不动说明令牌是伪造或历史遗留的，
# 当未登录处理（Unauthorized），别让它变成 500。
def _user_uuid(user: CurrentUser) -> uuid.UUID:
    try:
        return uuid.UUID(user.id)
    except ValueError as exc:
        raise Unauthorized("登录信息已失效，请重新登录") from exc


# 本卡以后要补的端点（属 RT-02 / RT-03，现在不挂空 stub）：
#   PUT    /route-drafts/{draft_id}/nodes      整表替换节点顺序
#   POST   /route-drafts/{draft_id}/submit     提交审核（冻结版本，单事务）
#   POST   /route-drafts/{draft_id}/withdraw   撤回投稿


@router.get("", response_model=RouteDraftPageOut)
def list_route_drafts(
    db: DbDep,
    user: CurrentUserDep,
    cursor: Annotated[str | None, Query(description="不透明游标，取上一页的 next_cursor")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> RouteDraftPageOut:
    """我的草稿列表（只含自己的）。"""
    return RoutesService(db).list_drafts(owner_id=_user_uuid(user), cursor=cursor, limit=limit)


@router.post("", response_model=RouteDraftOut, status_code=201)
def create_route_draft(
    db: DbDep,
    user: CurrentUserDep,
    payload: RouteDraftCreate,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=64)],
) -> RouteDraftOut:
    """新建草稿。同 key 同 body 重放首次结果，同 key 不同 body 回 409。"""
    return RoutesService(db).create_draft(
        owner_id=_user_uuid(user), payload=payload, idempotency_key=idempotency_key
    )


@router.get("/{draft_id}", response_model=RouteDraftDetailOut, response_model_exclude_none=True)
def get_route_draft(
    db: DbDep,
    user: CurrentUserDep,
    draft_id: uuid.UUID,
) -> RouteDraftDetailOut:
    """草稿详情。cost 此刻还没算，用 exclude_none 让它整个不出现。"""
    return RoutesService(db).get_detail(owner_id=_user_uuid(user), draft_id=draft_id)


@router.patch("/{draft_id}", response_model=RouteDraftOut)
def update_route_draft(
    db: DbDep,
    user: CurrentUserDep,
    draft_id: uuid.UUID,
    payload: RouteDraftPatch,
    response: Response,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=64)],
    if_match: Annotated[int, Header(alias="If-Match", ge=1, description="草稿当前的 lock_version")],
) -> RouteDraftOut:
    """更新草稿。If-Match 必须等于当前 lock_version，成功后回新的 ETag。"""
    draft = RoutesService(db).update_draft(
        owner_id=_user_uuid(user),
        draft_id=draft_id,
        payload=payload,
        lock_version=if_match,
    )
    # PATCH 后的新版本号必须回给客户端，否则它下一次改还得先 GET 一趟。
    response.headers["ETag"] = f'"{draft.lock_version}"'
    return draft


@router.delete("/{draft_id}", status_code=204)
def delete_route_draft(
    db: DbDep,
    user: CurrentUserDep,
    draft_id: uuid.UUID,
) -> Response:
    """删除草稿。只有 EDITING 且从未发布过的能删。"""
    RoutesService(db).delete_draft(owner_id=_user_uuid(user), draft_id=draft_id)
    return Response(status_code=204)
