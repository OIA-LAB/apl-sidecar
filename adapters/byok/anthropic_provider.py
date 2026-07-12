"""BYOK adapter: Anthropic Messages API. Network, your key, off by default.

Configuration is environment-only — a key never appears on a command line
(shell history) or in a config file (accidental commit):

    ANTHROPIC_API_KEY          required
    APL_ANTHROPIC_MODEL        optional, default claude-sonnet-4-6
    APL_ANTHROPIC_MODEL_A/_B   optional per-seat override
    APL_ANTHROPIC_BASE_URL     optional, default https://api.anthropic.com
                               (corporate gateways / test harnesses)
    APL_ANTHROPIC_MAX_TOKENS   optional, default 1024

The adapter sends exactly one user message containing the approved provider
payload — no system prompt, no metadata, temperature 0. What is sent is what
the receipt hashes.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urlparse

from ..base import ProviderCapabilities, ProviderRequest, ProviderResponse
from . import _http
from ._http import ByokConfigError

ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_BASE_URL = "https://api.anthropic.com"
DEFAULT_MODEL = "claude-sonnet-4-6"

Transport = Callable[..., dict[str, Any]]


def _seat_env(name: str, seat: str | None) -> str | None:
    if seat:
        value = os.environ.get(f"{name}_{seat.upper()}")
        if value:
            return value
    return os.environ.get(name)


@dataclass(frozen=True)
class AnthropicAdapter:
    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    max_tokens: int = 1024
    timeout: float = _http.DEFAULT_TIMEOUT_S
    provider_id: str = "byok_anthropic"
    capabilities: ProviderCapabilities = ProviderCapabilities(network=True)
    transport: Transport = field(default=_http.post_json, repr=False)

    @classmethod
    def from_env(cls, seat: str | None = None, provider_id: str | None = None,
                 transport: Transport | None = None) -> "AnthropicAdapter":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ByokConfigError("ANTHROPIC_API_KEY is not set")
        return cls(
            api_key=api_key,
            model=_seat_env("APL_ANTHROPIC_MODEL", seat) or DEFAULT_MODEL,
            base_url=os.environ.get("APL_ANTHROPIC_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            max_tokens=int(os.environ.get("APL_ANTHROPIC_MAX_TOKENS", "1024")),
            provider_id=provider_id or "byok_anthropic",
            transport=transport or _http.post_json)

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/v1/messages"

    @property
    def endpoint_host(self) -> str:
        return urlparse(self.base_url).hostname or self.base_url

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        body = {"model": request.model or self.model,
                "max_tokens": self.max_tokens,
                "temperature": 0,
                "messages": [{"role": "user", "content": request.prompt}]}
        headers = {"x-api-key": self.api_key, "anthropic-version": ANTHROPIC_VERSION}
        data = self.transport(self.endpoint, headers, body,
                              timeout=self.timeout, secrets=(self.api_key,))
        blocks = data.get("content")
        if not isinstance(blocks, list):
            raise _http.TransportError("anthropic response missing content blocks")
        text = "\n".join(b.get("text", "") for b in blocks
                         if isinstance(b, dict) and b.get("type") == "text")
        stop_reason = data.get("stop_reason")
        return ProviderResponse(
            text=text, provider_id=self.provider_id, model=body["model"],
            metadata={"stop_reason": stop_reason,
                      "truncated": stop_reason == "max_tokens",
                      "usage": data.get("usage"),
                      "endpoint_host": self.endpoint_host})
