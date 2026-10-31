"""PL-04 LLM Adapter 的正/负用例。

验收（tasks/认领清单.md PL-04）：无 key 时用 fake 返回固定 JSON；真实调用失败
降级并标 degraded。这里用 httpx.MockTransport 造网络现场，不起服务、不联网、
不花一分钱，跑完一两百毫秒。
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import Settings
from app.modules.planner.adapters import (
    FIXED_PLAN_JSON,
    FakeLLM,
    LLMResult,
    OpenAICompatibleLLM,
    build_llm,
)
from app.modules.planner.agents import PlanContext
from app.modules.planner.models import AgentName, AgentStepStatus
from app.modules.planner.orchestrator import Orchestrator

BASE_URL = "https://api.deepseek.com"
API_KEY = "sk-test-key"


def _settings(**overrides: object) -> Settings:
    """只填和 LLM 相关的字段，避免 .env 里的真实配置影响断言。"""
    values: dict[str, object] = {
        "llm_provider": "fake",
        "llm_base_url": "",
        "llm_api_key": "",
        "llm_model": "",
    }
    values.update(overrides)
    return Settings(**values)


def _chat_ok(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": content}}]},
    )


def _client(handler, **kwargs: object) -> OpenAICompatibleLLM:
    return OpenAICompatibleLLM(
        base_url=BASE_URL,
        api_key=API_KEY,
        model="deepseek-chat",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def _context() -> PlanContext:
    return PlanContext(city="长沙", days=2, people=2, budget_total=100000)


# ---------------------------------------------------------------- fake 插头


def test_fake_returns_fixed_json_and_is_repeatable() -> None:
    client = FakeLLM()
    first = client.complete("给我排两天的行程")
    second = client.complete("再排一次")

    assert first.text == FIXED_PLAN_JSON
    assert first.text == second.text  # 同样输入必须给同样输出，CI 才不会飘
    assert first.degraded is False
    assert first.provider == "fake"
    assert isinstance(first.data(), dict)
    assert client.calls == ["给我排两天的行程", "再排一次"]


def test_fake_fixed_json_is_parseable() -> None:
    payload = FakeLLM().complete("x").data()
    assert payload["source"] == "fake"
    assert [day["day_index"] for day in payload["days"]] == [1, 2]


def test_result_data_rejects_non_json() -> None:
    with pytest.raises(ValueError, match="不是合法 JSON"):
        LLMResult(text="好的，我来帮你规划", provider="fake").data()


def test_result_data_rejects_non_object_json() -> None:
    with pytest.raises(ValueError, match="必须是 JSON 对象"):
        LLMResult(text="[1, 2, 3]", provider="fake").data()


# ---------------------------------------------------------------- 挑插头


def test_default_provider_is_fake() -> None:
    assert isinstance(build_llm(_settings()), FakeLLM)


def test_openai_provider_needs_full_config() -> None:
    full = _settings(
        llm_provider="openai-compatible",
        llm_base_url=BASE_URL,
        llm_api_key=API_KEY,
        llm_model="deepseek-chat",
    )
    assert isinstance(build_llm(full), OpenAICompatibleLLM)

    # 少任何一项都退回 fake：宁可走兜底，也不拿空 key 去请求
    for missing in ("llm_base_url", "llm_api_key", "llm_model"):
        partial = full.model_copy(update={missing: ""})
        assert isinstance(build_llm(partial), FakeLLM), missing


def test_unknown_provider_falls_back_to_fake() -> None:
    assert isinstance(build_llm(_settings(llm_provider="some-new-vendor")), FakeLLM)


def test_build_llm_honours_custom_fallback() -> None:
    fallback = FakeLLM(fixed_text='{"days": [], "source": "custom"}')
    built = build_llm(_settings(llm_provider="openai-compatible"), fallback=fallback)
    assert built is fallback


# ---------------------------------------------------------------- 真调用成功


def test_openai_compatible_success() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _chat_ok('{"days": [{"day_index": 1, "items": ["岳麓山"]}]}')

    result = _client(handler).complete("排一天", system="你是行程规划师")

    assert result.degraded is False
    assert result.provider == "openai-compatible"
    assert result.model == "deepseek-chat"
    assert result.error is None
    assert result.data()["days"][0]["day_index"] == 1

    request = seen[0]
    assert str(request.url) == f"{BASE_URL}/chat/completions"
    assert request.headers["Authorization"] == f"Bearer {API_KEY}"
    body = json.loads(request.content)
    assert body["model"] == "deepseek-chat"
    assert body["messages"] == [
        {"role": "system", "content": "你是行程规划师"},
        {"role": "user", "content": "排一天"},
    ]


def test_system_prompt_is_optional() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _chat_ok("{}")

    _client(handler).complete("只给用户消息")
    body = json.loads(seen[0].content)
    assert body["messages"] == [{"role": "user", "content": "只给用户消息"}]


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("https://api.deepseek.com", "https://api.deepseek.com/chat/completions"),
        ("https://api.deepseek.com/", "https://api.deepseek.com/chat/completions"),
        (
            "https://api.deepseek.com/chat/completions",
            "https://api.deepseek.com/chat/completions",
        ),
        ("http://localhost:11434/v1/", "http://localhost:11434/v1/chat/completions"),
    ],
)
def test_base_url_normalisation(base_url: str, expected: str) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return _chat_ok("{}")

    OpenAICompatibleLLM(
        base_url=base_url,
        api_key=API_KEY,
        model="m",
        transport=httpx.MockTransport(handler),
    ).complete("x")
    assert seen == [expected]


# ---------------------------------------------------------------- 真调用失败 → 降级


def test_connect_error_degrades_to_fake() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("拒绝连接", request=request)

    result = _client(handler).complete("排一天")

    assert result.degraded is True
    assert result.text == FIXED_PLAN_JSON
    assert result.provider == "fake"
    assert result.error is not None
    assert result.error.startswith("ConnectError")


def test_timeout_degrades_to_fake() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("超时", request=request)

    result = _client(handler, timeout_seconds=0.01).complete("排一天")

    assert result.degraded is True
    assert result.error is not None
    assert result.error.startswith("ReadTimeout")


def test_http_error_degrades_to_fake() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    result = _client(handler).complete("排一天")

    assert result.degraded is True
    assert result.error is not None
    assert "500" in result.error


def test_malformed_body_degrades_to_fake() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    result = _client(handler).complete("排一天")

    assert result.degraded is True
    assert result.error is not None


def test_non_json_content_degrades_to_fake() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _chat_ok("好的，我来帮你规划一天的行程：先去岳麓山……")

    result = _client(handler).complete("排一天")

    assert result.degraded is True
    assert result.error is not None
    assert "JSON" in result.error


def test_json_array_content_degrades_to_fake() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _chat_ok("[1, 2, 3]")

    result = _client(handler).complete("排一天")

    assert result.degraded is True


def test_empty_content_degrades_to_fake() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _chat_ok("   ")

    result = _client(handler).complete("排一天")

    assert result.degraded is True
    assert result.error is not None
    assert "空内容" in result.error


def test_degrade_uses_custom_fallback_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("拒绝连接", request=request)

    fallback = FakeLLM(fixed_text='{"days": [], "source": "custom"}')
    result = _client(handler, fallback=fallback).complete("排一天")

    assert result.degraded is True
    assert result.text == '{"days": [], "source": "custom"}'


def test_complete_never_raises_and_keeps_working() -> None:
    """接口契约：complete() 不抛异常；连续失败也要继续给兜底结果。"""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("拒绝连接", request=request)

    client = _client(handler)
    results = [client.complete(f"第 {i} 次") for i in range(3)]

    assert all(result.degraded for result in results)
    assert len({result.text for result in results}) == 1


# ---------------------------------------------------------------- degraded 传进流水线


class _StubAgent:
    """顺序合法的假岗位：可选地在上下文里打上「降级」标记。"""

    def __init__(self, name: AgentName, *, degraded: bool) -> None:
        self.name = name
        self._degraded = degraded

    def run(self, ctx: PlanContext) -> PlanContext:
        if self._degraded:
            ctx.llm_degraded = True
        return ctx


def _stub_agents(*, degraded_at: AgentName | None = None) -> list[_StubAgent]:
    order = (
        AgentName.RESEARCHER,
        AgentName.PLANNER,
        AgentName.CRITIC,
        AgentName.VERIFIER,
    )
    return [_StubAgent(name, degraded=(name is degraded_at)) for name in order]


def test_orchestrator_marks_degraded_step_and_run() -> None:
    result = Orchestrator(agents=_stub_agents(degraded_at=AgentName.PLANNER)).run(_context())

    assert result.ok is True
    assert result.degraded is True
    by_agent = {step.agent: step for step in result.steps}
    assert by_agent[AgentName.RESEARCHER].degraded is False
    assert by_agent[AgentName.PLANNER].degraded is True
    assert by_agent[AgentName.CRITIC].degraded is True  # 标记一旦打上，后续步骤同样受影响
    assert all(step.status is AgentStepStatus.DONE for step in result.steps)


def test_orchestrator_clean_run_is_not_degraded() -> None:
    result = Orchestrator(agents=_stub_agents()).run(_context())

    assert result.ok is True
    assert result.degraded is False
    assert all(step.degraded is False for step in result.steps)


def test_orchestrator_failed_step_keeps_degraded_mark() -> None:
    class _Boom(_StubAgent):
        def run(self, ctx: PlanContext) -> PlanContext:
            raise RuntimeError("模型返回了无法解析的东西")

    agents = _stub_agents(degraded_at=AgentName.RESEARCHER)
    agents[2] = _Boom(AgentName.CRITIC, degraded=True)

    result = Orchestrator(agents=agents).run(_context())

    assert result.ok is False
    assert result.degraded is True
    assert result.failed_step is not None
    assert result.failed_step.agent is AgentName.CRITIC
    assert result.failed_step.degraded is True
