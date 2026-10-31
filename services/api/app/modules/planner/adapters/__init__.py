"""规划模块的外接适配层。

目前只有 LLM 一个插头；以后接地图（map_provider）也放这里，
让「换供应商」永远只改一次配置、不改业务代码。
"""

from __future__ import annotations

from app.modules.planner.adapters.llm import (
    FIXED_PLAN_JSON,
    FakeLLM,
    LLMClient,
    LLMResult,
    OpenAICompatibleLLM,
    build_llm,
)

__all__ = [
    "FIXED_PLAN_JSON",
    "FakeLLM",
    "LLMClient",
    "LLMResult",
    "OpenAICompatibleLLM",
    "build_llm",
]
