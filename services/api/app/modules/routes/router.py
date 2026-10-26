# 路线与版本 · HTTP 入口
"""只做编解码与依赖注入。业务规则一律写进 service.py。

契约以 docs/api/openapi.yaml 为准，本文件只负责把端点挂上去。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/route-drafts", tags=["drafts"])


# ===== 待实现端点（认领任务卡后逐条填） =====
#   GET    /route-drafts                                    我的草稿列表
#   POST   /route-drafts                                    新建草稿
#   GET    /route-drafts/{draft_id}                         草稿详情
#   PATCH  /route-drafts/{draft_id}                         更新草稿（If-Match）
#   DELETE /route-drafts/{draft_id}                         删除草稿（仅 EDITING）
#   PUT    /route-drafts/{draft_id}/nodes                   整表替换节点顺序
#   POST   /route-drafts/{draft_id}/submit                  提交审核（冻结版本，单事务）
#   POST   /route-drafts/{draft_id}/withdraw                撤回投稿
