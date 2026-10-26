# 地点与文化资料 · HTTP 入口
"""只做编解码与依赖注入。业务规则一律写进 service.py。

契约以 docs/api/openapi.yaml 为准，本文件只负责把端点挂上去。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/places", tags=["places"])


# ===== 待实现端点（认领任务卡后逐条填） =====
#   GET    /places                                          地点列表（公开，支持 q/district/tag）
#   GET    /places/{place_id}                               地点详情（含 facts 与 sources）
#   POST   /places                                          新增地点（编辑）
#   POST   /places/{place_id}/facts                         新增事实与来源（编辑）
