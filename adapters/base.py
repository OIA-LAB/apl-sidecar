# SPDX-License-Identifier: FSL-1.1-ALv2
"""Provider adapter contract shared by offline and future network providers."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ProviderCapabilities:
    network: bool
    streaming: bool = False


@dataclass(frozen=True)
class ProviderRequest:
    prompt: str
    model: str
    fixture_dir: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    provider_id: str
    model: str
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ProviderAdapter(Protocol):
    provider_id: str
    capabilities: ProviderCapabilities

    def complete(self, request: ProviderRequest) -> ProviderResponse: ...

