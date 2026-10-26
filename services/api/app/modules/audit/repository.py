# 审计 · 数据访问
"""只写查询和落库，不写权限判断、不写业务流程。"""

from __future__ import annotations

from sqlalchemy.orm import Session


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db
