# 站内通知 · 业务规则
"""本模块唯一允许写业务判断的地方。router 不许写 if/else 业务逻辑。

拥有数据：Notification
明确不做：短信、邮件、推送
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError, ValidationFailed
from app.modules.notifications.models import Notification
from app.modules.notifications.repository import NotificationsRepository

DEFAULT_LIMIT = 20
MAX_LIMIT = 50

# 审核结果的三种通知类型：moderation 模块 import 这些常量，别自己拼字符串
REVIEW_APPROVED = "review_approved"
REVIEW_REQUEST_CHANGES = "review_request_changes"
REVIEW_REJECTED = "review_rejected"

# 退回类通知必须带理由（验收条件：退回通知带理由）
REJECT_TYPES = frozenset({REVIEW_REQUEST_CHANGES, REVIEW_REJECTED})


def encode_cursor(created_at: datetime, notification_id: uuid.UUID) -> str:
    """游标对前端不透明，内部就是「上一页最后一条」的位置。"""
    raw = json.dumps(
        {"c": created_at.isoformat(), "i": str(notification_id)}, separators=(",", ":")
    )
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    padded = cursor + "=" * (-len(cursor) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(padded))
        return datetime.fromisoformat(data["c"]), uuid.UUID(data["i"])
    except (KeyError, TypeError, ValueError) as exc:  # base64 错、JSON 错、时间/ID 格式错
        raise AppError("分页游标无效", code="INVALID_CURSOR") from exc


class NotificationsService:
    """依赖注入的官方入口；外部模块只能通过它访问本模块能力。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = NotificationsRepository(db)

    def list_mine(
        self,
        user_id: uuid.UUID,
        *,
        cursor: str | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> tuple[list[Notification], str | None]:
        """只返回本人通知（user_id 由登录态决定，调用方无权指定别人）。"""
        limit = max(1, min(limit, MAX_LIMIT))
        after = decode_cursor(cursor) if cursor else None
        rows = self.repo.list_for_user(user_id, after=after, limit=limit + 1)
        items = rows[:limit]
        has_more = len(rows) > limit
        next_cursor = encode_cursor(items[-1].created_at, items[-1].id) if has_more else None
        return items, next_cursor

    def notify(
        self,
        user_id: uuid.UUID,
        notif_type: str,
        payload: dict[str, Any] | None = None,
    ) -> Notification:
        """写入一条站内通知：审核通过/退回时由 moderation 调用本方法。

        退回类（request_changes / rejected）必须带非空 reason；缺理由直接报错，
        整条通知不会落库。写完由调用方的同一个事务提交。
        """
        data = dict(payload or {})
        if notif_type in REJECT_TYPES:
            data["reason"] = _require_reason(data.get("reason"))
        return self.repo.add(Notification(user_id=user_id, type=notif_type, payload=data))


def _require_reason(value: Any) -> str:
    reason = str(value).strip() if value is not None else ""
    if not reason:
        raise ValidationFailed(
            "退回通知必须写明理由",
            code="REVIEW_REASON_REQUIRED",
            details=[{"field": "reason", "message": "退回必须带理由"}],
        )
    return reason
