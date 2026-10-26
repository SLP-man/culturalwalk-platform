# 社区互动 · HTTP 入口
"""只做编解码与依赖注入。业务规则一律写进 service.py。

契约以 docs/api/openapi.yaml 为准，本文件只负责把端点挂上去。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/routes", tags=["community"])


# ===== 待实现端点（认领任务卡后逐条填） =====
#   GET    /routes/{route_id}/comments                      评论列表（公开，置顶优先）
#   POST   /routes/{route_id}/comments                      发表评论
#   POST   /comments/{comment_id}/pin                       作者置顶一条
#   POST   /routes/{route_id}/favorite                      收藏
#   DELETE /routes/{route_id}/favorite                      取消收藏
