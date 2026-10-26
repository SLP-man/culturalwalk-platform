# 媒体资源 · 业务规则
"""本模块唯一允许写业务判断的地方。router 不许写 if/else 业务逻辑。

拥有数据：MediaAsset
明确不做：内容审核
"""

from __future__ import annotations

from sqlalchemy.orm import Session

# ===== 待实现：下面是签名示意（已注释，抄下来改成真实现） =====
#   def create_intent(db: Session, filename: str, mime: str, size: int, user: CurrentUser)
#       -> MediaIntentOut: ...


class MediaService:
    """依赖注入的官方入口；外部模块只能通过它访问本模块能力。"""

    def __init__(self, db: Session) -> None:
        self.db = db
