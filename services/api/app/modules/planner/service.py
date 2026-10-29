# 行程规划（多 Agent） · 业务规则
"""本模块唯一允许写业务判断的地方。router 不许写 if/else 业务逻辑。

拥有数据：Itinerary, ItineraryDay, ItineraryItem, PlanRun, AgentStep
明确不做：路线投稿、发布
"""

from __future__ import annotations

from typing import Final

from sqlalchemy.orm import Session

from app.core.errors import Conflict
from app.modules.planner.models import Itinerary, PlanRun, PlanState

# 状态机（docs/02 §3.5）：只有这三条边合法，表外的一切组合都拒绝。
# 值那一列是"触发动作"，验收、审计日志、以后的事件名都复用它，
# 免得同一件事在三处各起一个名字。
_TRANSITIONS: Final[dict[tuple[PlanState, PlanState], str]] = {
    (PlanState.DRAFT, PlanState.GENERATING): "enqueue",
    (PlanState.GENERATING, PlanState.READY): "succeed",
    (PlanState.GENERATING, PlanState.FAILED): "fail",
}


def allowed_targets(state: PlanState) -> list[PlanState]:
    """当前状态还能去哪。错误详情里要列出来，调用方才知道下一步该干嘛。"""
    return [target for (source, target) in _TRANSITIONS if source == state]


def ensure_transition(current: PlanState, target: PlanState) -> str:
    """校验一次流转并返回动作名；非法流转抛 409 CONFLICT。"""
    action = _TRANSITIONS.get((current, target))
    if action is None:
        raise Conflict(
            f"行程状态不能从 {current} 变成 {target}",
            details=[
                {
                    "field": "state",
                    "from": str(current),
                    "to": str(target),
                    "allowed": [str(item) for item in allowed_targets(current)],
                }
            ],
        )
    return action


def apply_transition(
    entity: Itinerary | PlanRun,
    target: PlanState,
    *,
    error_code: str | None = None,
) -> str:
    """把一次流转落到实体上（只改内存，不 commit）。

    error_code 跟着一起写：READY 时清空，FAILED 时带上失败原因，
    免得出现"状态已经是 FAILED、原因还停在上一次"的脏数据。
    """
    action = ensure_transition(entity.state, target)
    entity.state = target
    entity.error_code = error_code
    return action


class PlannerService:
    """依赖注入的官方入口；外部模块只能通过它访问本模块能力。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def start_run(
        self,
        itinerary: Itinerary,
        *,
        input_hash: str,
        model: str | None = None,
        prompt_version: str | None = None,
    ) -> PlanRun:
        """行程转入 GENERATING，并落一条本次生成记录。

        PlanRun 的 state 显式传 DRAFT：列默认值要等 INSERT 才生效，
        不显式给的话此刻读到的还是 None，状态机没法校验。
        """
        apply_transition(itinerary, PlanState.GENERATING)
        run = PlanRun(
            itinerary_id=itinerary.id,
            state=PlanState.DRAFT,
            input_hash=input_hash,
            model=model,
            prompt_version=prompt_version,
        )
        apply_transition(run, PlanState.GENERATING)
        self.db.add(run)
        return run

    def finish_ready(self, itinerary: Itinerary, run: PlanRun) -> None:
        """本次生成成功：run 和行程一起进 READY。"""
        apply_transition(run, PlanState.READY)
        apply_transition(itinerary, PlanState.READY)

    def finish_failed(self, itinerary: Itinerary, run: PlanRun, *, error_code: str) -> None:
        """本次生成失败：两边都进 FAILED，并记下原因。

        不在这里回滚行程：已完成的步骤和输出要保留（见 router.py 的失败策略）。
        """
        apply_transition(run, PlanState.FAILED, error_code=error_code)
        apply_transition(itinerary, PlanState.FAILED, error_code=error_code)
