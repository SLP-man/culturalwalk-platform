# 行程规划（多 Agent） · 数据访问
"""只写查询和落库，不写权限判断、不写业务流程。"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.planner.models import AgentStep, Itinerary, JobState, PlanJob, PlanRun


class PlannerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_idempotency_key(
        self, *, user_id: uuid.UUID, idempotency_key: str
    ) -> Itinerary | None:
        """按 (用户, 幂等键) 找已有的行程。

        带 deleted_at 过滤：用户删掉行程后重新提交同一个 key，应该当新请求处理，
        而不是把一张已删除的行程还回去。
        """
        stmt = select(Itinerary).where(
            Itinerary.user_id == user_id,
            Itinerary.idempotency_key == idempotency_key,
            Itinerary.deleted_at.is_(None),
        )
        return self.db.scalars(stmt).first()

    def add(self, itinerary: Itinerary) -> Itinerary:
        self.db.add(itinerary)
        return itinerary

    def get_itinerary(self, itinerary_id: uuid.UUID) -> Itinerary | None:
        stmt = select(Itinerary).where(Itinerary.id == itinerary_id, Itinerary.deleted_at.is_(None))
        return self.db.scalars(stmt).first()

    def latest_run(self, itinerary_id: uuid.UUID) -> PlanRun | None:
        """最近一次生成记录。

        一张行程可能被重新生成多次，详情页关心的是"这一次"，
        所以按时间倒序取第一条，而不是把所有 run 都返回。
        """
        stmt = (
            select(PlanRun)
            .where(PlanRun.itinerary_id == itinerary_id)
            .order_by(PlanRun.created_at.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def steps_for_run(self, run_id: uuid.UUID) -> list[AgentStep]:
        """按执行顺序取某个 run 的步骤留痕。

        按 step_index 排，不按 id：id 是随机 UUID，按它排出来的顺序是随机的。
        """
        stmt = (
            select(AgentStep)
            .where(AgentStep.run_id == run_id)
            .order_by(AgentStep.step_index, AgentStep.created_at)
        )
        return list(self.db.scalars(stmt).all())

    # ----- 后台任务（PL-05） -------------------------------------------------

    def add_job(self, job: PlanJob) -> PlanJob:
        self.db.add(job)
        return job

    def get_job_by_run(self, run_id: uuid.UUID) -> PlanJob | None:
        stmt = select(PlanJob).where(PlanJob.run_id == run_id)
        return self.db.scalars(stmt).first()

    def claim_next_job(
        self,
        *,
        now: datetime,
        lease_seconds: int,
        max_attempts: int,
        worker: str,
    ) -> PlanJob | None:
        """领一条最该干的任务，领不到就返回 None。

        `FOR UPDATE SKIP LOCKED`：两个 worker 同时轮询时，一个锁住这行，
        另一个直接跳过、去拿下一条，而不是排队等——排队会让多开 worker 变成
        负优化。SQLite 不支持行锁，方言会忽略这段，单进程测试仍然正确。
        """
        stmt = (
            select(PlanJob)
            .where(
                PlanJob.state == JobState.PENDING,
                PlanJob.available_at <= now,
                PlanJob.attempts < max_attempts,
            )
            .order_by(PlanJob.available_at, PlanJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = self.db.scalars(stmt).first()
        if job is None:
            return None

        job.state = JobState.RUNNING
        job.attempts += 1
        job.claimed_at = now
        job.claimed_by = worker
        job.lease_until = now + timedelta(seconds=lease_seconds)
        return job

    def recover_expired_leases(self, *, now: datetime) -> int:
        """把租约过期的 RUNNING 任务放回队列（worker 崩了没人收尸）。

        只改状态不改 attempts：崩掉那次的尝试次数已经算过，这里不重复扣。
        """
        stmt = (
            update(PlanJob)
            .where(
                PlanJob.state == JobState.RUNNING,
                PlanJob.lease_until.is_not(None),
                PlanJob.lease_until < now,
            )
            .values(
                state=JobState.PENDING,
                claimed_at=None,
                claimed_by=None,
                lease_until=None,
                available_at=now,
            )
        )
        result = self.db.execute(stmt)
        return int(result.rowcount or 0)
