# 媒体资源 · HTTP 入口
"""只做编解码与依赖注入。业务规则一律写进 service.py。

契约以 docs/api/openapi.yaml 为准，本文件只负责把端点挂上去。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/media", tags=["media"])


# ===== 待实现端点（认领任务卡后逐条填） =====
#   POST   /media/intent                                    申请上传（返回预签名，zone=quarantine）
#   POST   /media/{media_id}/complete                       通知上传完成（入队扫描）
#   GET    /media/{media_id}                                媒体状态（CLEAN 才有公开 URL）
