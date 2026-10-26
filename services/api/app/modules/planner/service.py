# 行程规划（多 Agent） · 业务规则
"""本模块唯一允许写业务判断的地方。router 不许写 if/else 业务逻辑。

拥有数据：Itinerary, ItineraryDay, ItineraryItem, PlanRun, AgentStep
明确不做：路线投稿、发布
"""

from __future__ import annotations

from sqlalchemy.orm import Session

# ===== 待实现：下面是签名示意（已注释，抄下来改成真实现） =====
#   def enqueue_plan(db: Session, payload: PlanInput, user: CurrentUser) -> PlanRun: ...
#   def run_agents(run_id: UUID) -> None:  # researcher -> planner -> critic -> verifier


class PlannerService:
    """依赖注入的官方入口；外部模块只能通过它访问本模块能力。"""

    def __init__(self, db: Session) -> None:
        self.db = db
