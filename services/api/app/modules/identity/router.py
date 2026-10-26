# 身份与会话 · HTTP 入口
"""只做编解码与依赖注入。业务规则一律写进 service.py。

契约以 docs/api/openapi.yaml 为准，本文件只负责把端点挂上去。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth", "users"])


# ===== 待实现端点（认领任务卡后逐条填） =====
#   POST   /auth/register                                   注册（公开）
#   POST   /auth/login                                      登录（公开）
#   POST   /auth/refresh                                    刷新令牌（公开）
#   POST   /auth/logout                                     退出登录
#   GET    /users/me                                        当前用户
#   GET    /users/{user_id}/profile                         用户公开主页（公开）
