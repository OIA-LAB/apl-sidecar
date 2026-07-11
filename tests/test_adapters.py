from pathlib import Path

import pytest

from adapters.base import ProviderAdapter, ProviderRequest
from adapters.mock import MockProviderAdapter, default_registry
from adapters.registry import ProviderRegistry


def test_registry_and_protocol():
    adapter = MockProviderAdapter("example", "answer.txt", "example-model")
    registry = ProviderRegistry()
    registry.register(adapter)
    assert isinstance(adapter, ProviderAdapter)
    assert registry.get("example") is adapter
    with pytest.raises(ValueError, match="already registered"):
        registry.register(adapter)


def test_default_registry_is_explicit_and_offline():
    registry = default_registry()
    assert registry.ids() == ("mock_provider_a", "mock_provider_b")
    assert all(not registry.get(item).capabilities.network for item in registry.ids())


def test_mock_adapter_reads_fixture(tmp_path: Path):
    (tmp_path / "answer.txt").write_text("fixture answer", encoding="utf-8")
    adapter = MockProviderAdapter("test", "answer.txt", "test-model")
    response = adapter.complete(ProviderRequest("secret", "test-model", tmp_path))
    assert response.text == "fixture answer"
    assert response.provider_id == "test"
