# 行程规划（多 Agent） · HTTP 入口
"""只做编解码与依赖注入。业务规则一律写进 service.py。

契约以 docs/api/openapi.yaml 为准，本文件只负责把端点挂上去。
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, CurrentUserDep
from app.core.errors import Unauthorized
from app.modules.planner.schemas import PlanIn, PlanOut
from app.modules.planner.service import PlannerService

router = APIRouter(prefix="/plans", tags=["plans"])


def _user_uuid(user: CurrentUser) -> uuid.UUID:
    """把令牌里的 sub 转成 UUID。

    契约里所有 id 都是 uuid，但令牌是历史遗留的字符串字段；
    转不动说明令牌是手搓的或旧格式，一律当未登录处理，别让它变成 500。
    """
    try:
        return uuid.UUID(user.id)
    except ValueError as exc:
        raise Unauthorized("登录信息已失效，请重新登录") from exc


@router.post(
    "",
    response_model=PlanOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="提交规划条件（异步生成）",
)
def create_plan(
    payload: PlanIn,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=64)],
    user: CurrentUserDep,
    db: Annotated[Session, Depends(get_db)],
) -> PlanOut:
    """收下条件，建行程并开始生成，立刻返回 202 回执。

    真正生成要十几秒，不能挂在这次请求里等——用户会以为页面卡死，
    所以这里只回"已接受 + 行程编号"，前端凭 id 轮询 GET /plans/{id}。
    """
    itinerary = PlannerService(db).create_plan(
        user_id=_user_uuid(user),
        payload=payload,
        idempotency_key=idempotency_key,
    )
    return PlanOut.model_validate(itinerary)


# ===== 待实现端点（认领任务卡后逐条填） =====
#   GET    /plans                                           我的行程列表
#   GET    /plans/{plan_id}                                 行程详情（含步骤进度）
#   DELETE /plans/{plan_id}                                 删除行程
#   POST   /plans/{plan_id}/to-draft                        行程转路线草稿

# --- 多 Agent 编排契约（实现见 agents/） -------------------------------------
# 每个 Agent 只做一件事，输入输出都是 PlanContext，禁止互相 import 具体实现：
#
#   class Agent(Protocol):
#       name: Literal["researcher", "planner", "critic", "verifier"]
#       def run(self, ctx: PlanContext) -> PlanContext: ...
#
# researcher: 从 catalog 检索候选地点与事实（只读）
# planner   : 按时间/地理邻近/预算组排，产出日程骨架
# critic    : 检查超预算、赶路、闭馆、重复点位，回写 issues[]
# verifier  : 逐条核对来源，无来源的项标 confidence=unverified
#
# 失败策略：任一步抛异常 -> run.state=FAILED，已完成步骤与输出保留，不整体丢弃。
