# SPDX-License-Identifier: FSL-1.1-ALv2
"""BYOK adapters: offline unit tests. No socket is ever opened here."""
import pytest

from adapters.base import ProviderAdapter, ProviderRequest
from adapters.byok._http import ByokConfigError, TransportError, _scrub
from adapters.byok.anthropic_provider import AnthropicAdapter
from adapters.byok.openai_provider import OpenAICompatAdapter, is_loopback

KEY = "test-key-not-real-1234567890abcdef"  # deliberately NOT sk- prefixed: repo secret-hygiene gate


class CapturingTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, url, headers, body, timeout=None, secrets=(), **_):
        self.calls.append({"url": url, "headers": headers, "body": body,
                           "secrets": secrets})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_anthropic_request_shape_and_parse(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    transport = CapturingTransport(
        {"content": [{"type": "text", "text": "hello"},
                     {"type": "text", "text": "world"}],
         "stop_reason": "end_turn",
         "usage": {"input_tokens": 3, "output_tokens": 5}})
    adapter = AnthropicAdapter.from_env(seat="a", transport=transport)
    assert isinstance(adapter, ProviderAdapter)
    assert adapter.capabilities.network is True
    response = adapter.complete(ProviderRequest(prompt="payload text", model=adapter.model))
    call = transport.calls[0]
    assert call["url"] == "https://api.anthropic.com/v1/messages"
    assert call["headers"]["x-api-key"] == KEY
    assert call["headers"]["anthropic-version"]
    assert call["body"]["temperature"] == 0
    assert call["body"]["messages"] == [{"role": "user", "content": "payload text"}]
    assert KEY in call["secrets"]  # transport is told what to scrub
    assert response.text == "hello\nworld"
    assert response.metadata["endpoint_host"] == "api.anthropic.com"
    assert response.metadata["truncated"] is False
    assert response.metadata["usage"]["output_tokens"] == 5


def test_anthropic_requires_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ByokConfigError):
        AnthropicAdapter.from_env()


def test_anthropic_seat_model_override(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    monkeypatch.setenv("APL_ANTHROPIC_MODEL", "base-model")
    monkeypatch.setenv("APL_ANTHROPIC_MODEL_B", "seat-b-model")
    assert AnthropicAdapter.from_env(seat="a").model == "base-model"
    assert AnthropicAdapter.from_env(seat="b").model == "seat-b-model"


def test_openai_loopback_needs_no_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("APL_OPENAI_BASE_URL", "http://127.0.0.1:8793/v1")
    monkeypatch.setenv("APL_OPENAI_MODEL", "apl-mock-a")
    transport = CapturingTransport(
        {"choices": [{"message": {"role": "assistant", "content": "ok"},
                      "finish_reason": "stop"}]})
    adapter = OpenAICompatAdapter.from_env(transport=transport)
    response = adapter.complete(ProviderRequest(prompt="p", model=adapter.model))
    assert response.text == "ok"
    assert "Authorization" not in transport.calls[0]["headers"]
    assert transport.calls[0]["url"] == "http://127.0.0.1:8793/v1/chat/completions"


def test_openai_remote_requires_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("APL_OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("APL_OPENAI_MODEL", "some-model")
    with pytest.raises(ByokConfigError):
        OpenAICompatAdapter.from_env()


def test_openai_model_is_mandatory(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    monkeypatch.delenv("APL_OPENAI_MODEL", raising=False)
    with pytest.raises(ByokConfigError):
        OpenAICompatAdapter.from_env()


def test_openai_bearer_header_present_when_key_set(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    monkeypatch.setenv("APL_OPENAI_MODEL", "m")
    transport = CapturingTransport(
        {"choices": [{"message": {"content": "x"}, "finish_reason": "stop"}]})
    adapter = OpenAICompatAdapter.from_env(transport=transport)
    adapter.complete(ProviderRequest(prompt="p", model="m"))
    assert transport.calls[0]["headers"]["Authorization"] == f"Bearer {KEY}"


def test_loopback_detection():
    assert is_loopback("http://127.0.0.1:8793/v1")
    assert is_loopback("http://localhost:11434/v1")
    assert not is_loopback("https://api.openai.com/v1")


def test_scrub_removes_secrets_from_errors():
    message = _scrub(f"HTTP 401: bad key {KEY} rejected", (KEY,))
    assert KEY not in message
    assert "[redacted]" in message


def test_transport_error_propagates_without_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    transport = CapturingTransport(TransportError("provider returned HTTP 500"))
    adapter = AnthropicAdapter.from_env(transport=transport)
    with pytest.raises(TransportError) as excinfo:
        adapter.complete(ProviderRequest(prompt="p", model=adapter.model))
    assert KEY not in str(excinfo.value)


def test_truncation_flags(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    monkeypatch.setenv("APL_OPENAI_MODEL", "m")
    cut_a = CapturingTransport({"content": [{"type": "text", "text": "half an ans"}],
                                "stop_reason": "max_tokens"})
    a = AnthropicAdapter.from_env(transport=cut_a)
    assert a.complete(ProviderRequest(prompt="p", model=a.model)).metadata["truncated"] is True
    cut_b = CapturingTransport({"choices": [{"message": {"content": "half"},
                                             "finish_reason": "length"}]})
    b = OpenAICompatAdapter.from_env(transport=cut_b)
    assert b.complete(ProviderRequest(prompt="p", model="m")).metadata["truncated"] is True
