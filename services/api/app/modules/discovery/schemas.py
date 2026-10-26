# 发现（只读查询层）· 出入参
"""只读视图的返回结构。写操作不在这里，也没有自己的表。"""

from __future__ import annotations

# ===== 待实现：下面是示意（已注释，抄下来改成真实现） =====
#   class RouteCard(BaseModel):
#       id: UUID
#       title: str
#       theme: str
#       days: int
#       budget_min: int | None
#       cover_url: str | None
