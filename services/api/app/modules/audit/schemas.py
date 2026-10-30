# 审计 · DTO
"""请求/响应模型。字段与 docs/api/openapi.yaml 的 AuditLog 保持一致，改 yaml 再改这里。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ActorOut(BaseModel):
    id: str | None = None
    username: str | None = None


class AuditLogOut(BaseModel):
    """一条审计记录（对外）。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    actor: ActorOut
    action: str
    object_type: str
    object_id: str
    before_hash: str | None = None
    after_hash: str | None = None
    reason: str | None = None
    created_at: datetime


class AuditPageOut(BaseModel):
    """游标分页结果。"""

    items: list[AuditLogOut]
    next_cursor: str | None = None
