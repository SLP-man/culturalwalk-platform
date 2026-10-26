# 审核与发布 · 业务规则
"""本模块唯一允许写业务判断的地方。router 不许写 if/else 业务逻辑。

拥有数据：Submission, ReviewTask, ReviewAction, Publication
明确不做：编辑内容本身
"""

from __future__ import annotations

from sqlalchemy.orm import Session

# ===== 待实现：下面是签名示意（已注释，抄下来改成真实现） =====
#   def claim_task(db: Session, task_id: UUID, reviewer: CurrentUser) -> ReviewTask: ...
#   def publish(db: Session, submission_id: UUID, version_id: UUID, content_hash: str) ->
#       Publication: ...


class ModerationService:
    """依赖注入的官方入口；外部模块只能通过它访问本模块能力。"""

    def __init__(self, db: Session) -> None:
        self.db = db
