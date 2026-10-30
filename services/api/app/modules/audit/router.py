# 审计 · HTTP 入口
"""只做编解码与依赖注入。业务规则一律写进 service.py。

契约以 docs/api/openapi.yaml 为准，本文件只负责把端点挂上去。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.db import DbDep
from app.core.deps import AdminDep
from app.modules.audit.schemas import AuditPageOut
from app.modules.audit.service import DEFAULT_LIMIT, MAX_LIMIT, AuditService

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=AuditPageOut, summary="审计查询（管理员）")
def list_audit_logs(
    _admin: AdminDep,
    db: DbDep,
    object_type: str | None = None,
    object_id: str | None = None,
    actor_id: str | None = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> AuditPageOut:
    """管理员按对象/操作者翻审计。普通用户调用一律 403（负例见 tests）。"""
    return AuditService(db).page(
        object_type=object_type,
        object_id=object_id,
        actor_id=actor_id,
        cursor=cursor,
        limit=limit,
    )


# 调用方约定：审计由业务模块在同一个事务里显式调用 `audit.service.write(...)`，
# 不做隐式事件钩子——出了问题必须能在代码里一眼看到"谁记了这条审计"。
