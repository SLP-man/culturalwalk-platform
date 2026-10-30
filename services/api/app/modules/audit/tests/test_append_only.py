"""MD-05 负例与不变量：审计只追加，改不了也删不掉。

对应 docs/必读1「八条高压线」中的审计不可篡改，以及 docs/02 §2.6 audit_logs。
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService


def _row(db: Session) -> AuditLog:
    row = AuditService(db).write(
        action="route.publish",
        object_type="route",
        object_id="33333333-3333-3333-3333-333333333333",
        actor_id="11111111-1111-1111-1111-111111111111",
        actor_username="boss",
        after_hash="a" * 64,
    )
    db.commit()
    return row


def test_repository_has_no_update_or_delete() -> None:
    """数据访问层不许提供 update/delete 入口。"""
    for forbidden in ("update", "delete", "remove", "modify"):
        assert not hasattr(AuditRepository, forbidden), f"AuditRepository 不许有 {forbidden}"


def test_update_is_forbidden(db_session: Session) -> None:
    row = _row(db_session)
    row.reason = "偷偷改一下"
    with pytest.raises(RuntimeError, match="append-only"):
        db_session.commit()
    db_session.rollback()


def test_delete_is_forbidden(db_session: Session) -> None:
    row = _row(db_session)
    db_session.delete(row)
    with pytest.raises(RuntimeError, match="append-only"):
        db_session.commit()
    db_session.rollback()


def test_write_requires_action_and_object(db_session: Session) -> None:
    """字段不全会直接炸，不允许写入半条审计。"""
    service = AuditService(db_session)
    with pytest.raises(ValueError):
        service.write(action="", object_type="route", object_id="x")
    with pytest.raises(ValueError):
        service.write(action="route.publish", object_type="", object_id="x")


def test_digest_is_stable() -> None:
    """同一个对象多次摘要必须一致；字段顺序不影响结果。"""
    assert AuditService.digest({"a": 1, "b": 2}) == AuditService.digest({"b": 2, "a": 1})
    assert AuditService.digest({"a": 1}) != AuditService.digest({"a": 2})


def test_ip_is_hashed_not_plain(db_session: Session) -> None:
    row = AuditService(db_session).write(
        action="auth.login",
        object_type="user",
        object_id="11111111-1111-1111-1111-111111111111",
        actor_id="11111111-1111-1111-1111-111111111111",
        ip_hash=AuditService.hash_ip("10.1.2.3"),
    )
    db_session.commit()
    assert row.ip_hash is not None
    assert "10.1.2.3" not in row.ip_hash
    assert len(row.ip_hash) == 64
