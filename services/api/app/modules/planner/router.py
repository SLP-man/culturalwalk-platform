# 行程规划（多 Agent） · HTTP 入口
"""只做编解码与依赖注入。业务规则一律写进 service.py。

契约以 docs/api/openapi.yaml 为准，本文件只负责把端点挂上去。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/plans", tags=["plans"])


# ===== 待实现端点（认领任务卡后逐条填） =====
#   GET    /plans                                           我的行程列表
#   POST   /plans                                           提交规划（异步 202）
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
