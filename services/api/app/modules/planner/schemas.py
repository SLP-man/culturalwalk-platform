# 行程规划（多 Agent） · DTO
"""请求/响应模型。字段与 docs/api/openapi.yaml 保持一致，改 yaml 再改这里。"""

from __future__ import annotations

from pydantic import BaseModel


class PlannerOut(BaseModel):
    """TODO: 按 openapi.yaml 的 schema 补齐字段。"""
