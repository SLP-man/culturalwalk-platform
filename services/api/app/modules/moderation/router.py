# 审核与发布 · HTTP 入口
"""只做编解码与依赖注入。业务规则一律写进 service.py。

契约以 docs/api/openapi.yaml 为准，本文件只负责把端点挂上去。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/review", tags=["review"])


# ===== 待实现端点（认领任务卡后逐条填） =====
#   GET    /review/tasks                                    审核队列（管理员）
#   POST   /review/tasks/{task_id}/claim                    领取任务（租约）
#   POST   /review/tasks/{task_id}/release                  释放任务
#   POST   /review/tasks/{task_id}/decision                 审核决定 approve/request_changes/reject
#   GET    /submissions/{submission_id}                     投稿详情（含 diff 快照）
#   POST   /submissions/{submission_id}/publish             发布（校验 version_id + hash）
#   POST   /publications/{publication_id}/unpublish         下线（必须写原因）
