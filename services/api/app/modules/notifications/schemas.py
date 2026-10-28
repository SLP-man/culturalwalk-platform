# 站内通知 · DTO
"""请求/响应模型。字段与 docs/api/openapi.yaml 保持一致，改 yaml 再改这里。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class NotificationOut(BaseModel):
    """GET /notifications 的单条通知，字段顺序对齐 openapi.yaml#Notification。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    payload: dict[str, Any]
    read_at: datetime | None = None
    created_at: datetime

    @field_validator("created_at", "read_at")
    @classmethod
    def _assume_utc(cls, value: datetime | None) -> datetime | None:
        # SQLite 会丢掉 tzinfo；出参一律补齐 UTC，保证前端拿到带时区的 ISO-8601
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class NotificationListOut(BaseModel):
    """游标分页外壳：{"items": [...], "next_cursor": null}。"""

    items: list[NotificationOut]
    next_cursor: str | None = None
