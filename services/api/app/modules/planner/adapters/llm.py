"""LLM 适配层：把「谁来思考」收敛到一个可替换的插头里。

两种插头：

- ``fake``：返回一段固定的 JSON。没有网、没有 key 也能把整条流水线跑完，
  CI 与演示默认走它 —— 演示当天断网不该等于产品挂了。
- ``openai-compatible``：DeepSeek、通义千问、智谱、本地 Ollama 共用同一套
  ``/chat/completions`` 协议，换供应商只改 ``.env`` 里的几个变量，代码不动。

一条硬规矩：**complete() 永不抛异常**。超时、报错、返回非 JSON，一律退回 fake 的
固定结果，并带上 ``degraded=True``。上层据此知道这份结果是兜底来的，而不是模型
真算出来的 —— 交一份标明来路的兜底，好过让整条流水线因为一次网络抖动全挂。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from time import perf_counter
from typing import Final, Protocol

import httpx

from app.core.config import Settings, get_settings

# 兜底结果的形制：一个 JSON 对象。真实模型经常先来一句「好的，我来帮你规划」
# 再给 JSON，所以这里也顺手当「是不是结构化输出」的判据用。
FIXED_PLAN_JSON: Final[str] = json.dumps(
    {
        "days": [
            {"day_index": 1, "items": ["岳麓山", "橘子洲"]},
            {"day_index": 2, "items": ["太平老街", "天心阁"]},
        ],
        "source": "fake",
    },
    ensure_ascii=False,
    sort_keys=True,
)

LLM_TIMEOUT_SECONDS: Final[float] = 20.0
ERROR_PREVIEW_CHARS: Final[int] = 200


@dataclass(frozen=True)
class LLMResult:
    """一次补全的结果。

    ``degraded=True`` 表示正文是兜底出来的，不是模型这次真给的；
    ``error`` 留着降级的原因，方便排查「为什么这批行程都是一样的」。
    """

    text: str
    provider: str
    model: str = ""
    degraded: bool = False
    error: str | None = None
    latency_ms: int = 0

    def data(self) -> dict[str, object]:
        """把正文解析成 JSON 对象；不是对象就抛 ValueError。"""
        try:
            payload = json.loads(self.text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"模型输出不是合法 JSON：{exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("模型输出必须是 JSON 对象")
        return payload


class LLMClient(Protocol):
    """所有插头共用的方法：吃一段提示词，还一段文本。"""

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResult: ...


class FakeLLM:
    """固定答案的插头：无 key、无网、可重复。"""

    provider = "fake"

    def __init__(self, fixed_text: str = FIXED_PLAN_JSON) -> None:
        self._fixed_text = fixed_text
        self.calls: list[str] = []  # 测试用来确认提示词真的传下来了

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResult:
        self.calls.append(prompt)
        return LLMResult(text=self._fixed_text, provider=self.provider, model="fake")


class OpenAICompatibleLLM:
    """走 OpenAI 兼容协议的插头，失败自动降级到 fallback。"""

    provider = "openai-compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = LLM_TIMEOUT_SECONDS,
        fallback: LLMClient | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._url = _chat_completions_url(base_url)
        self._api_key = api_key
        self.model = model
        self._timeout_seconds = timeout_seconds
        self._fallback = fallback or FakeLLM()
        # 测试注入 MockTransport，线上留 None 让 httpx 自己建连接池
        self._transport = transport

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResult:
        started = perf_counter()
        try:
            content = self._request(prompt, system)
        except Exception as exc:  # noqa: BLE001 - 网络与协议异常统一收口成降级
            return self._degraded(prompt, exc, started)
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            payload = None
        if not isinstance(payload, dict):
            return self._degraded(prompt, ValueError("模型输出不是 JSON 对象"), started)
        return LLMResult(
            text=content,
            provider=self.provider,
            model=self.model,
            latency_ms=_elapsed_ms(started),
        )

    def _request(self, prompt: str, system: str | None) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        with httpx.Client(timeout=self._timeout_seconds, transport=self._transport) as client:
            response = client.post(
                self._url,
                json={"model": self.model, "messages": messages},
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            response.raise_for_status()
            body = response.json()
        content = body["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("模型返回了空内容")
        return content

    def _degraded(self, prompt: str, exc: Exception, started: float) -> LLMResult:
        """把这次失败写成 error，正文换成 fallback 的结果，并打上 degraded。"""
        fallback_result = self._fallback.complete(prompt)
        return LLMResult(
            text=fallback_result.text,
            provider=fallback_result.provider,
            model=fallback_result.model,
            degraded=True,
            error=f"{type(exc).__name__}: {exc}"[:ERROR_PREVIEW_CHARS],
            latency_ms=_elapsed_ms(started),
        )


def build_llm(settings: Settings | None = None, *, fallback: LLMClient | None = None) -> LLMClient:
    """按配置挑插头。provider 不认识、或配置只填了一半，一律退回 fake。

    半套配置比没有配置更危险：拿空 key 去请求，线上要么 401，要么被当成攻击。
    """
    config = settings or get_settings()
    provider = (config.llm_provider or "fake").strip().lower()
    if provider != "openai-compatible":
        return fallback or FakeLLM()
    has_config = (
        config.llm_base_url.strip() and config.llm_api_key.strip() and config.llm_model.strip()
    )
    if not has_config:
        return fallback or FakeLLM()
    return OpenAICompatibleLLM(
        base_url=config.llm_base_url,
        api_key=config.llm_api_key,
        model=config.llm_model,
        fallback=fallback or FakeLLM(),
    )


def _chat_completions_url(base_url: str) -> str:
    """`https://api.deepseek.com` 与 `https://api.deepseek.com/chat/completions` 都接受。"""
    trimmed = base_url.strip().rstrip("/")
    if trimmed.endswith("/chat/completions"):
        return trimmed
    return f"{trimmed}/chat/completions"


def _elapsed_ms(started: float) -> int:
    return int(round((perf_counter() - started) * 1000))
