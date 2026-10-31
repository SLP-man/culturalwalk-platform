# 行程规划（多 Agent） · 业务规则
"""本模块唯一允许写业务判断的地方。router 不许写 if/else 业务逻辑。

拥有数据：Itinerary, ItineraryDay, ItineraryItem, PlanRun, AgentStep
明确不做：路线投稿、发布
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import Conflict, Forbidden, NotFound
from app.modules.planner.agents.base import PlaceSource
from app.modules.planner.models import (
    AgentStep,
    Itinerary,
    JobState,
    PlanJob,
    PlanRun,
    PlanState,
)
from app.modules.planner.orchestrator import AGENT_FAILED_CODE, Orchestrator, RunResult
from app.modules.planner.orchestrator import context_from_itinerary as _context_from_itinerary
from app.modules.planner.repository import PlannerRepository
from app.modules.planner.schemas import PlanIn

logger = logging.getLogger(__name__)

# 任务租约：worker 领到活后最多干这么久。超过这个时间还没交卷，
# 认为它崩了（或卡死），任务会被别的 worker 捡走重做。
JOB_LEASE_SECONDS: Final[int] = 120
# 一条任务最多试几次。上限存在的理由：坏数据会让任务每次都在同一处炸，
# 不限次数就是让一个 worker 永远忙着重试它一个。
MAX_JOB_ATTEMPTS: Final[int] = 3
# 失败退避（秒）：第 1 次失败等 30 秒，第 2 次等 2 分钟，第 3 次判死。
# 不做退避的话，模型服务抖一下，三次重试会在两秒内烧完。
JOB_BACKOFF_SECONDS: Final[tuple[int, ...]] = (30, 120, 600)
# 库里只留能定位的一句，完整堆栈进日志。
ERROR_PREVIEW_CHARS: Final[int] = 200

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


@dataclass(frozen=True)
class CreatedPlan:
    """刚收下的那份规划：行程 + 本次生成记录。

    router 要的是两个 id（plan_id 给前端轮询，run_id 给排障），
    分开返回容易在调用点漏掉一个。
    """

    itinerary: Itinerary
    run: PlanRun


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
    ) -> CreatedPlan:
        """收下一份规划条件：建行程、转 GENERATING、落生成记录并排一条任务。

        幂等（docs/03 §1.2）：同一个 key 再进来直接返回首次的结果（含 202），
        不重复建行程、也不重复烧模型调用。并发下靠唯一约束兜底：
        两个请求同时通过"先查"这一步时，后到的那个会撞 IntegrityError，
        回滚后重新查一次，拿到先落库的那张。

        这里**不跑** Agent：真跑要十几秒，挂在请求里用户会以为页面卡死。
        只把活排进 plan_jobs，由 worker 领走（PL-05）。
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

        run = self.start_run(itinerary, input_hash=request_hash)
        self.db.flush()  # run.id 由数据库生成，入队前要先拿到
        self.enqueue(itinerary, run)
        self.db.flush()
        self.db.refresh(itinerary)  # created_at 由数据库默认值生成，刷一遍才拿得到
        return CreatedPlan(itinerary=itinerary, run=run)

    def _replay(self, itinerary: Itinerary, request_hash: str) -> CreatedPlan:
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
        run = self.repo.latest_run(itinerary.id)
        if run is None:  # 理论上不会有：建行程必带 run。真遇到就补一条，别让详情页 500。
            run = self.start_run(itinerary, input_hash=request_hash)
            self.db.flush()
        return CreatedPlan(itinerary=itinerary, run=run)

    def get_detail(
        self, *, user_id: uuid.UUID, plan_id: uuid.UUID
    ) -> tuple[Itinerary, PlanRun | None, list[AgentStep]]:
        """取一张行程的详情。

        别人的行程报 403 而不是 404：路径里的 id 本来就猜不到，
        但"存在但不是你的"和"根本不存在"对前端是两种不同的处理。
        """
        itinerary = self.repo.get_itinerary(plan_id)
        if itinerary is None:
            raise NotFound("行程不存在")
        if itinerary.user_id != user_id:
            raise Forbidden("这不是你的行程")
        run = self.repo.latest_run(itinerary.id)
        steps = self.repo.steps_for_run(run.id) if run is not None else []
        return itinerary, run, steps

    def enqueue(self, itinerary: Itinerary, run: PlanRun) -> PlanJob:
        """把这次生成排进任务表。

        available_at 显式给当前时间：列默认值的 now() 在 SQLite 上是不带时区的字符串，
        和 Python 传进来的 aware 时间比较会飘，索性统一由一个时钟说话。
        """
        job = PlanJob(
            run_id=run.id,
            itinerary_id=itinerary.id,
            state=JobState.PENDING,
            attempts=0,
            available_at=datetime.now(UTC),
        )
        self.repo.add_job(job)
        return job

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

    def run_agents(
        self,
        itinerary: Itinerary,
        run: PlanRun,
        *,
        place_source: PlaceSource | None = None,
    ) -> RunResult:
        """跑完整条流水线，把每一步落成 agent_steps，再给行程和生成记录收尾。

        由 worker 调用（PL-05 起不再挂在请求线程里），
        验收看的是「四步都留痕、失败能定位到哪一站」，不看吞吐。
        """
        result = Orchestrator(place_source=place_source).run(_context_from_itinerary(itinerary))
        for index, step in enumerate(result.steps):
            self.db.add(
                AgentStep(
                    run_id=run.id,
                    step_index=index,
                    agent=step.agent,
                    status=step.status,
                    output_digest=step.output_digest,
                    duration_ms=step.duration_ms,
                )
            )
        if result.ok:
            self.finish_ready(itinerary, run)
        else:
            failed = result.failed_step
            logger.warning(
                "行程 %s 生成失败，卡在 %s：%s",
                itinerary.id,
                result.failed_agent,
                failed.error if failed else "",
            )
            self.finish_failed(itinerary, run, error_code=result.error_code or AGENT_FAILED_CODE)
        return result

    # ----- 后台任务（PL-05） -------------------------------------------------

    def recover_expired_leases(self, *, now: datetime | None = None) -> int:
        return self.repo.recover_expired_leases(now=now or datetime.now(UTC))

    def claim_job(self, *, worker: str, now: datetime | None = None) -> PlanJob | None:
        """领一条任务并标成 RUNNING（不含执行）。

        领活和执行分成两步，是为了让"我领到了"尽快提交：如果领到之后还在同一个
        长事务里跑十几秒的模型调用，这行会被锁到任务结束，别的 worker 只能干等。
        """
        moment = now or datetime.now(UTC)
        self.recover_expired_leases(now=moment)
        return self.repo.claim_next_job(
            now=moment,
            lease_seconds=JOB_LEASE_SECONDS,
            max_attempts=MAX_JOB_ATTEMPTS,
            worker=worker,
        )

    def execute_job(
        self,
        job: PlanJob,
        *,
        place_source: PlaceSource | None = None,
    ) -> RunResult | None:
        """执行一条已领到的任务，并按结果给任务收尾。

        worker 半路崩了也不怕：租约到期后任务被重领，重领会把上一次留下的
        半截步骤清掉重跑——半截的留痕比没有留痕更容易误导人。
        """
        itinerary = self.repo.get_itinerary(job.itinerary_id)
        run = self.db.get(PlanRun, job.run_id)
        if itinerary is None or run is None:
            # 行程被用户删了，任务已经没有意义：直接判失败，别再重试。
            job.state = JobState.FAILED
            job.last_error = "行程或生成记录已被删除"
            job.lease_until = None
            return None

        for step in self.repo.steps_for_run(run.id):
            self.db.delete(step)
        self.db.flush()
        self._rearm(itinerary, run)

        result = self.run_agents(itinerary, run, place_source=place_source)
        if result.ok:
            job.state = JobState.DONE
            job.last_error = None
            job.lease_until = None
            return result

        failed = result.failed_step
        reason = failed.error if failed and failed.error else result.error_code or AGENT_FAILED_CODE
        job.last_error = reason[:ERROR_PREVIEW_CHARS]
        if job.attempts >= MAX_JOB_ATTEMPTS:
            job.state = JobState.FAILED
            job.lease_until = None
            logger.error("行程 %s 的任务已重试 %s 次仍失败，放弃", itinerary.id, job.attempts)
        else:
            # attempts 是"已经试过几次"，第 1 次失败用退避表第一档。
            backoff = JOB_BACKOFF_SECONDS[min(job.attempts - 1, len(JOB_BACKOFF_SECONDS) - 1)]
            job.state = JobState.PENDING
            job.available_at = datetime.now(UTC) + timedelta(seconds=backoff)
            job.lease_until = None
        return result

    def _rearm(self, itinerary: Itinerary, run: PlanRun) -> None:
        """重试前把上一次已经收尾的记录重新打开。

        不走 apply_transition：状态机描述的是用户可见的流转，
        「把失败的一次重新跑」是任务层的重试，硬套状态机会让 FAILED→GENERATING 变成合法边。
        """
        if run.state != PlanState.GENERATING:
            run.state = PlanState.GENERATING
            run.error_code = None
        if itinerary.state != PlanState.GENERATING:
            itinerary.state = PlanState.GENERATING
            itinerary.error_code = None
