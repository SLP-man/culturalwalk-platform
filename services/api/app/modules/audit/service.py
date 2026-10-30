# 审计 · 业务规则
"""本模块唯一允许写业务判断的地方。router 不许写 if/else 业务逻辑。

拥有数据：AuditLog
明确不做：业务状态变更

对外只有两个能力：
- `write(...)`：其他模块在**自己的事务里**显式记一条审计（不做隐式事件钩子，谁记的必须一眼可见）
- `page(...)`：管理员分页查询
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ValidationFailed
from app.modules.audit.models import AuditLog
from app.modules.audit.repository import AuditRepository
from app.modules.audit.schemas import ActorOut, AuditLogOut, AuditPageOut

DEFAULT_LIMIT = 20
MAX_LIMIT = 50


def _as_utc(value: datetime) -> datetime:
    """SQLite 取回来是 naive，统一按 UTC 解释，避免游标比较时炸。"""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def encode_cursor(row: AuditLog) -> str:
    raw = f"{_as_utc(row.created_at).isoformat()}|{row.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    padded = cursor + "=" * (-len(cursor) % 4)
    raw = base64.urlsafe_b64decode(padded.encode()).decode()
    ts_text, _, row_id = raw.partition("|")
    if not ts_text or not row_id:
        raise ValueError("游标格式错误")
    return datetime.fromisoformat(ts_text), row_id


class AuditService:
    """依赖注入的官方入口；外部模块只能通过它访问本模块能力。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AuditRepository(db)

    # ---------- 写 ----------

    def write(
        self,
        *,
        action: str,
        object_type: str,
        object_id: str,
        actor_id: str | None = None,
        actor_username: str | None = None,
        before_hash: str | None = None,
        after_hash: str | None = None,
        reason: str | None = None,
        request_id: str | None = None,
        ip_hash: str | None = None,
        created_at: datetime | None = None,
    ) -> AuditLog:
        """追加一条审计。不 commit，跟随调用方的事务一起提交或回滚。

        created_at 一般不传（默认取当前时间）；回放历史数据时才显式指定。
        """
        if not action or not object_type or not object_id:
            raise ValueError("action / object_type / object_id 不能为空")
        row = AuditLog(
            actor_id=actor_id,
            actor_username=actor_username,
            action=action,
            object_type=object_type,
            object_id=object_id,
            before_hash=before_hash,
            after_hash=after_hash,
            reason=reason,
            request_id=request_id,
            ip_hash=ip_hash,
            **({"created_at": created_at} if created_at else {}),
        )
        return self.repo.add(row)

    @staticmethod
    def digest(value: Any) -> str:
        """把任意 JSON 可序列化对象压成 sha256，用来填 before_hash / after_hash。"""
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def hash_ip(ip: str | None) -> str | None:
        """IP 不落明文，只落不可逆摘要。"""
        return hashlib.sha256(ip.encode()).hexdigest() if ip else None

    # ---------- 读 ----------

    def page(
        self,
        *,
        object_type: str | None = None,
        object_id: str | None = None,
        actor_id: str | None = None,
        cursor: str | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> AuditPageOut:
        limit = max(1, min(limit, MAX_LIMIT))
        try:
            after = decode_cursor(cursor) if cursor else None
        except ValueError as exc:
            raise ValidationFailed("游标无效，请从头翻页") from exc
        rows, has_more = self.repo.page(
            object_type=object_type,
            object_id=object_id,
            actor_id=actor_id,
            after=after,
            limit=limit,
        )
        items = [_to_out(row) for row in rows]
        next_cursor = encode_cursor(rows[-1]) if has_more and rows else None
        return AuditPageOut(items=items, next_cursor=next_cursor)


def _to_out(row: AuditLog) -> AuditLogOut:
    return AuditLogOut(
        id=row.id,
        actor=ActorOut(id=row.actor_id, username=row.actor_username),
        action=row.action,
        object_type=row.object_type,
        object_id=row.object_id,
        before_hash=row.before_hash,
        after_hash=row.after_hash,
        reason=row.reason,
        created_at=_as_utc(row.created_at),
    )


def write(db: Session, **kwargs: Any) -> AuditLog:
    """模块级快捷方式：其他模块写 `audit_service.write(db, ...)` 即可。"""
    return AuditService(db).write(**kwargs)
