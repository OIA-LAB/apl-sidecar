"""Mock provider A — offline fixture-backed. Never touches the network."""
from __future__ import annotations

from pathlib import Path

PROVIDER_ID = "mock_provider_a"


def respond(example_dir: Path | str) -> str:
    """Return the curated mock answer for this example. Zero network."""
    return (Path(example_dir) / "mock_answer_a.txt").read_text(encoding="utf-8")
