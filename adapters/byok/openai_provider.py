"""BYOK adapter: any OpenAI-compatible /v1/chat/completions endpoint.

This one seat covers three deployments with the same code path:
- OpenAI (or another hosted OpenAI-compatible vendor);
- a local model server (vLLM, Ollama, llama.cpp) on loopback — the
  customer-controlled "local seat" the enterprise docs describe;
- the repo's own offline mock proxy (`apl proxy`), which turns the entire
  live pipeline into an offline end-to-end rehearsal.

Configuration is environment-only:

    OPENAI_API_KEY           required, EXCEPT when the endpoint is loopback
    APL_OPENAI_BASE_URL      optional, default https://api.openai.com/v1
    APL_OPENAI_BASE_URL_A/_B optional per-seat override
    APL_OPENAI_MODEL         required (no default — "OpenAI-compatible"
                             does not imply any particular model exists)
    APL_OPENAI_MODEL_A/_B    optional per-seat override
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urlparse

from ..base import ProviderCapabilities, ProviderRequest, ProviderResponse
from . import _http
from ._http import ByokConfigError

DEFAULT_BASE_URL = "https://api.openai.com/v1"
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}

Transport = Callable[..., dict[str, Any]]


def _seat_env(name: str, seat: str | None) -> str | None:
    if seat:
        value = os.environ.get(f"{name}_{seat.upper()}")
        if value:
            return value
    return os.environ.get(name)


def is_loopback(base_url: str) -> bool:
    return (urlparse(base_url).hostname or "") in _LOOPBACK_HOSTS


@dataclass(frozen=True)
class OpenAICompatAdapter:
    model: str
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    timeout: float = _http.DEFAULT_TIMEOUT_S
    provider_id: str = "byok_openai"
    capabilities: ProviderCapabilities = ProviderCapabilities(network=True)
    transport: Transport = field(default=_http.post_json, repr=False)

    @classmethod
    def from_env(cls, seat: str | None = None, provider_id: str | None = None,
                 transport: Transport | None = None) -> "OpenAICompatAdapter":
        base_url = (_seat_env("APL_OPENAI_BASE_URL", seat) or DEFAULT_BASE_URL).rstrip("/")
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key and not is_loopback(base_url):
            raise ByokConfigError(
                "OPENAI_API_KEY is not set and the endpoint is not loopback")
        model = _seat_env("APL_OPENAI_MODEL", seat)
        if not model:
            raise ByokConfigError("APL_OPENAI_MODEL is not set")
        return cls(model=model, api_key=api_key, base_url=base_url,
                   provider_id=provider_id or "byok_openai",
                   transport=transport or _http.post_json)

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/v1/chat/completions" \
            if not self.base_url.endswith("/v1") else f"{self.base_url}/chat/completions"

    @property
    def endpoint_host(self) -> str:
        return urlparse(self.base_url).hostname or self.base_url

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        body = {"model": request.model or self.model,
                "temperature": 0,
                "stream": False,
                "messages": [{"role": "user", "content": request.prompt}]}
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        data = self.transport(self.endpoint, headers, body,
                              timeout=self.timeout, secrets=(self.api_key,))
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise _http.TransportError("openai-compatible response missing choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        text = message.get("content") if isinstance(message, dict) else None
        if not isinstance(text, str):
            raise _http.TransportError("openai-compatible response missing message content")
        return ProviderResponse(
            text=text, provider_id=self.provider_id, model=body["model"],
            metadata={"finish_reason": choices[0].get("finish_reason"),
                      "endpoint_host": self.endpoint_host})
