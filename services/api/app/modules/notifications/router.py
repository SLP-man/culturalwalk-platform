# 站内通知 · HTTP 入口
"""只做编解码与依赖注入。业务规则一律写进 service.py。

契约以 docs/api/openapi.yaml 为准，本文件只负责把端点挂上去。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ===== 待实现端点（认领任务卡后逐条填） =====
#   GET    /notifications                                   我的通知
#   POST   /notifications/{notification_id}/read            标记已读
