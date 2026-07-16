# SPDX-License-Identifier: FSL-1.1-ALv2
"""Explicit provider registry; importing this module never discovers plugins."""
from __future__ import annotations

from .base import ProviderAdapter


class ProviderRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ProviderAdapter] = {}

    def register(self, adapter: ProviderAdapter) -> None:
        provider_id = adapter.provider_id
        if not provider_id:
            raise ValueError("provider_id must not be empty")
        if provider_id in self._adapters:
            raise ValueError(f"provider already registered: {provider_id}")
        self._adapters[provider_id] = adapter

    def get(self, provider_id: str) -> ProviderAdapter:
        try:
            return self._adapters[provider_id]
        except KeyError as exc:
            raise KeyError(f"unknown provider: {provider_id}") from exc

    def ids(self) -> tuple[str, ...]:
        return tuple(self._adapters)

