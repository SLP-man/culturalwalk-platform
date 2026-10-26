# 路线与版本 · 业务规则
"""本模块唯一允许写业务判断的地方。router 不许写 if/else 业务逻辑。

拥有数据：Route, RouteDraft, RouteNode, RouteVersion
明确不做：审核、发布、AI 生成
"""

from __future__ import annotations

from sqlalchemy.orm import Session

# ===== 待实现：下面是签名示意（已注释，抄下来改成真实现） =====
#   def freeze_version(db: Session, draft: RouteDraft) -> RouteVersion: ...
#   def submit_for_review(db: Session, draft_id: UUID, user: CurrentUser) -> Submission: ...


class RoutesService:
    """依赖注入的官方入口；外部模块只能通过它访问本模块能力。"""

    def __init__(self, db: Session) -> None:
        self.db = db
