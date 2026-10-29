# 行程规划（多 Agent） · 业务规则
"""本模块唯一允许写业务判断的地方。router 不许写 if/else 业务逻辑。

拥有数据：Itinerary, ItineraryDay, ItineraryItem, PlanRun, AgentStep
明确不做：路线投稿、发布
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Final

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import Conflict
from app.modules.planner.models import Itinerary, PlanRun, PlanState
from app.modules.planner.repository import PlannerRepository
from app.modules.planner.schemas import PlanIn

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


def canonical_input_hash(payload: PlanIn) -> str:
    """把请求体压成一个稳定指纹（sha256 十六进制）。

    sort_keys + 紧凑分隔符：字段顺序不同、空格多少不同都得到同一个值，
    否则换个 JSON 序列化器就会误报"内容变了"。mode="json" 保证枚举落成值、
    UUID 落成字符串，与写进数据库的形态一致。
    """
    raw = json.dumps(
        payload.model_dump(mode="json"),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class PlannerService:
    """依赖注入的官方入口；外部模块只能通过它访问本模块能力。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PlannerRepository(db)

    def create_plan(
        self,
        *,
        user_id: uuid.UUID,
        payload: PlanIn,
        idempotency_key: str,
    ) -> Itinerary:
        """收下一份规划条件：建行程、转 GENERATING、落一条生成记录。

        幂等（docs/03 §1.2）：同一个 key 再进来直接返回首次的结果（含 202），
        不重复建行程、也不重复烧模型调用。并发下靠唯一约束兜底：
        两个请求同时通过"先查"这一步时，后到的那个会撞 IntegrityError，
        回滚后重新查一次，拿到先落库的那张。
        """
        request_hash = canonical_input_hash(payload)

        existing = self.repo.get_by_idempotency_key(
            user_id=user_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            return self._replay(existing, request_hash)

        itinerary = Itinerary(
            user_id=user_id,
            city=payload.city,
            days=payload.days,
            people=payload.people,
            budget_total=payload.budget_total,
            preferences=payload.preferences(),
            # 显式给 DRAFT：列默认值要等 INSERT 才生效，状态机此刻读不到 None。
            state=PlanState.DRAFT,
            idempotency_key=idempotency_key,
            input_hash=request_hash,
        )
        self.repo.add(itinerary)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            winner = self.repo.get_by_idempotency_key(
                user_id=user_id, idempotency_key=idempotency_key
            )
            if winner is None:  # 撞的是别的唯一约束，不是幂等键
                raise
            return self._replay(winner, request_hash)

        self.start_run(itinerary, input_hash=request_hash)
        self.db.flush()
        self.db.refresh(itinerary)  # created_at 由数据库默认值生成，刷一遍才拿得到
        return itinerary

    def _replay(self, itinerary: Itinerary, request_hash: str) -> Itinerary:
        """同一个 key 的重复请求：内容一致就还给原行程，不一致就报 409。

        不一致不能"将错就错"返回旧行程——前端会以为新条件生效了，
        用户看到的却是一份按旧条件生成的行程，这种错很难被用户发现。
        """
        if itinerary.input_hash != request_hash:
            raise Conflict(
                "这个 Idempotency-Key 已经用于另一份不同的规划条件，请换一个新的 key",
                code="IDEMPOTENCY_KEY_REUSED",
                details=[
                    {
                        "field": "Idempotency-Key",
                        "reason": "already_used_with_different_body",
                    }
                ],
            )
        return itinerary

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
