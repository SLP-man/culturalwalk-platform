# 发现（只读查询层）· 业务规则
"""只读聚合：只查已发布内容，不写任何表。

拥有数据：无（只读 routes / catalog / community 的公开投影）
明确不做：任何写操作；未发布内容对访客不可见
依赖方向：discovery -> routes, catalog, community（都只读）
"""

from __future__ import annotations

from sqlalchemy.orm import Session


class DiscoveryService:
    """依赖注入的官方入口；外部模块只能通过它访问本模块能力。"""

    def __init__(self, db: Session) -> None:
        self.db = db
