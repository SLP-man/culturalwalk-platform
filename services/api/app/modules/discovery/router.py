# 发现（只读查询层）· HTTP 入口
"""只做编解码与依赖注入。所有查询都落到 routes/catalog 的 service，本模块不碰表。

契约以 docs/api/openapi.yaml 为准。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["public"])


# ===== 待实现端点（认领 DS-01 ~ DS-04 后逐条填） =====
#   GET /routes                 公开路线列表（只返回已发布；?status= 一律忽略）
#   GET /routes/{route_id}      公开路线详情（节点、来源、费用区间、作者）
#   GET /home                   首页聚合（编辑精选 + 最新 + 主题入口）
