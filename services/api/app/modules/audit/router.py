# 审计 · HTTP 入口
"""只做编解码与依赖注入。业务规则一律写进 service.py。

契约以 docs/api/openapi.yaml 为准，本文件只负责把端点挂上去。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/audit-logs", tags=["audit"])


# ===== 待实现端点（认领任务卡后逐条填） =====
#   GET    /audit-logs                                      审计查询（管理员）

# 调用方约定：审计由业务模块在同一个事务里显式调用 audit.service.write()，
# 不做隐式事件钩子——出了问题必须能在代码里一眼看到"谁记了这条审计"。
