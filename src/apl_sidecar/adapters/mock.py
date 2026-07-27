# SPDX-License-Identifier: FSL-1.1-ALv2
"""Explicit, fixture-backed offline provider adapters."""
from __future__ import annotations

from dataclasses import dataclass

from .base import ProviderCapabilities, ProviderRequest, ProviderResponse


@dataclass(frozen=True)
class MockProviderAdapter:
    provider_id: str
    fixture_name: str
    model: str
    capabilities: ProviderCapabilities = ProviderCapabilities(network=False)

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        if request.fixture_dir is None:
            text = f"Offline mock completion from {self.provider_id}."
        else:
            text = (request.fixture_dir / self.fixture_name).read_text(encoding="utf-8")
        return ProviderResponse(text=text, provider_id=self.provider_id, model=request.model)


def default_registry():
    from .registry import ProviderRegistry

    registry = ProviderRegistry()
    registry.register(MockProviderAdapter("mock_provider_a", "mock_answer_a.txt", "apl-mock-a"))
    registry.register(MockProviderAdapter("mock_provider_b", "mock_answer_b.txt", "apl-mock-b"))
    return registry
